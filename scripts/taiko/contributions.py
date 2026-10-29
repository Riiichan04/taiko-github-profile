"""Offline, date-keyed contribution chart generation. No network access."""
from dataclasses import dataclass, asdict
from datetime import date, timedelta
from fractions import Fraction
from hashlib import sha256
from itertools import groupby
import json
import math
from statistics import median

VERSION = 'contributions-v2'
PATTERNS = ('12121', '11221', '12211', '11212', '12221', '21211')


@dataclass(frozen=True)
class Rules:
    bpm: int = 120
    seed: str = 'default'
    roll_minimum: int = 10
    roll_multiplier: int = 3
    roll_hits_per_second: int = 20
    roll_max_seconds: int = 2
    max_notes: int = 100_000


def normalize(snapshot):
    username = snapshot.get('username')
    if not isinstance(username, str) or not username.strip():
        raise ValueError('Snapshot requires a non-empty username')
    days = {}
    for item in snapshot.get('days', []):
        day = date.fromisoformat(item['date'])
        count = item['count']
        if type(count) is not int or count < 0 or day in days:
            raise ValueError('Dates must be unique; counts must be non-negative integers')
        days[day] = count
    if not days or (max(days)-min(days)).days >= 366:
        raise ValueError('Provide a window of 1–366 calendar days')
    # Fill gaps as real days of rest; never join streaks across missing dates.
    first, last = min(days), max(days)
    return username, [{'date': (first+timedelta(days=i)).isoformat(),
                       'count': days.get(first+timedelta(days=i), 0)}
                      for i in range((last-first).days+1)]


def thresholds(days, rules):
    active = sorted(d['count'] for d in days if d['count'] > 0)
    if not active:
        return {'median': 0, 'top10': None, 'top20': None}
    return {'median': median(active),
            'top10': active[math.ceil(len(active)*.9)-1],
            'top20': active[math.ceil(len(active)*.8)-1]}


def pattern(username, day, seed):
    digest = sha256(f'{VERSION}\0{username.lower()}\0{day}\0{seed}'.encode()).hexdigest()
    return PATTERNS[int(digest[:16], 16) % len(PATTERNS)], digest


def generate(snapshot, directory, rules=Rules(), name='contributions'):
    if type(rules.bpm) is not int or not 30 <= rules.bpm <= 300:
        raise ValueError('BPM must be an integer between 30 and 300')
    if min(rules.roll_minimum, rules.roll_multiplier, rules.roll_hits_per_second,
           rules.roll_max_seconds, rules.max_notes) <= 0:
        raise ValueError('Rule limits must be positive')
    username, days = normalize(snapshot)
    levels = thresholds(days, rules)
    candidates, high = set(), set()
    for i, day in enumerate(days):
        n = day['count']
        # Strictly above the median prevents uniform low/high years from
        # manufacturing percentile outliers. Equal boundary counts stay equal.
        if n > levels['median'] and n >= levels['top20']:
            high.add(i)
        if (n > levels['median'] and n >= levels['top10'] and
                n >= rules.roll_minimum and n >= levels['median']*rules.roll_multiplier):
            candidates.add(i)
    winners = set()
    for eligible, group in groupby(range(len(days)), key=lambda i: i in candidates):
        indices = list(group)
        if eligible:
            winners.add(max(indices, key=lambda i: (days[i]['count'], -i)))
    streaks = {}
    for active, group in groupby(range(len(days)), key=lambda i: days[i]['count'] > 0):
        indices = list(group)
        for i in indices:
            streaks[i] = (indices[0], len(indices), active)

    lines = [f'// {VERSION}; source: {snapshot.get("source", "offline snapshot")}',
             'TITLE:Contribution chart', f'BPM:{rules.bpm}', 'COURSE:Oni', 'LEVEL:7', '#START']
    segments, rolls, cursor, note_total = [], [], Fraction(0), 0
    tap_beats = Fraction(84, 190)
    beat_seconds = Fraction(60, rules.bpm)

    def measure(beats, symbols):
        nonlocal cursor
        ratio = beats/4
        lines.extend([f'#MEASURE {ratio.numerator}/{ratio.denominator}', symbols+','])
        cursor += beats

    for i, day in enumerate(days):
        n = day['count']
        start, length, active = streaks[i]
        if not active and i != start:
            continue
        beginning = cursor
        symbols, digest = pattern(username, day['date'], rules.seed)
        kind, count = 'normal', 1
        lines.append(f'// {day["date"]}: {n} contributions')
        if not active:
            kind, count = 'rest', 0
            beats = Fraction(length, 7)/beat_seconds if length >= 7 else length*tap_beats
            measure(beats, '0')
        elif i in winners:
            kind, count = 'roll', n
            if count > 100_000 or note_total+count > rules.max_notes:
                raise ValueError('Chart exceeds the roll strike or note budget')
            seconds = min(Fraction(n, rules.roll_hits_per_second), Fraction(rules.roll_max_seconds))
            roll_beats = seconds/beat_seconds
            measure(roll_beats, '5')
            rolls.append({'beat': float(beginning), 'end': float(cursor), 'hits': n})
            # End marker belongs to the same day; no extension across a rest.
            measure(tap_beats, '8')
        else:
            if i in high:
                kind, count = 'spike_stream', n
            elif length > 7:
                kind = 'streak_stream'
            if note_total+count > rules.max_notes:
                raise ValueError('Chart exceeds max_notes; no notes were silently truncated')
            sequence = (symbols*((count+len(symbols)-1)//len(symbols)))[:count]
            if kind == 'normal':
                sequence = '2' if n > levels['median'] else '1'
            measure(tap_beats*count, sequence)
        note_total += count
        segments.append({'date': day['date'], 'count': n, 'kind': kind,
                         'days': length if kind == 'rest' else 1, 'notes_or_hits': count,
                         'pattern_seed': digest, 'start_beat': float(beginning),
                         'end_beat': float(cursor), 'start_seconds': float(beginning*beat_seconds),
                         'duration_seconds': float((cursor-beginning)*beat_seconds)})
    lines.append('#END')
    if cursor > 4096:
        raise ValueError('Chart exceeds 4096 beats; reduce the input window or contribution counts')
    directory.mkdir(parents=True, exist_ok=True)
    tja = directory/f'{name}.tja'
    text = '\n'.join(lines)+'\n'
    metadata = {'schema_version': 1, 'generator_version': VERSION,
                'tja_sha256': sha256(text.encode()).hexdigest(), 'username': username,
                'source': snapshot.get('source', 'offline snapshot'),
                'rules': asdict(rules), 'thresholds': levels, 'days': days,
                'segments': segments, 'rolls': rolls, 'duration_seconds': float(cursor*beat_seconds)}
    tja.write_bytes(text.encode('utf-8'))
    tja.with_suffix('.meta.json').write_text(json.dumps(metadata, indent=2)+'\n', encoding='utf-8')
    return tja, metadata
