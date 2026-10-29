"""Strict single-course TJA reader (0/1/2 and measure changes)."""
from fractions import Fraction
import math


def load_chart(path, speed=190):
    if not math.isfinite(speed) or not 50 <= speed <= 1000:
        raise ValueError('Speed must be 50–1000 px/s')
    chart = {'speed': speed, 'notes': []}
    beat, measure, pending = Fraction(0), Fraction(4), []
    active = started = ended = False
    roll = None
    def fail(line, message):
        raise ValueError(f'{path}:{line}: {message}')
    for number, raw in enumerate(path.read_text(encoding='utf-8-sig').splitlines(), 1):
        text = raw.split('//', 1)[0].strip()
        if not text:
            continue
        if text == '#START':
            if started:
                fail(number, 'Only one course supported; use separate files')
            active = started = True
        elif text == '#END':
            if not active or pending:
                fail(number, 'Unexpected #END or missing measure comma')
            active, ended = False, True
        elif text.startswith('#'):
            command, _, value = text.partition(' ')
            if command != '#MEASURE' or not active or pending:
                fail(number, f'Unsupported command or position: {command}')
            try:
                measure = Fraction(value)*4
                if measure <= 0:
                    raise ValueError()
            except (ValueError, ZeroDivisionError):
                fail(number, 'Expected positive #MEASURE ratio, e.g. 4/4')
        elif active:
            for symbol in text:
                if symbol.isspace():
                    continue
                if symbol == ',':
                    for i, note in enumerate(pending):
                        position = float(beat+measure*i/len(pending))
                        if note == '5':
                            if roll is not None:
                                fail(number, 'Nested drumroll')
                            roll = {'beat': position, 'type': 'roll'}
                            chart['notes'].append(roll)
                        elif note == '8':
                            if roll is None:
                                fail(number, 'Drumroll end without start')
                            roll['end'] = position
                            roll = None
                        elif note != '0':
                            if roll is not None:
                                fail(number, 'Tap inside drumroll')
                            chart['notes'].append({'beat': position,
                                                   'type': 'don' if note == '1' else 'ka'})
                    beat += measure
                    pending.clear()
                elif symbol in '01258':
                    pending.append(symbol)
                else:
                    fail(number, f'Unsupported note {symbol!r}; use 0/1/2/5/8')
        else:
            if ended or ':' not in text:
                fail(number, 'Expected metadata before #START')
            key, value = text.split(':', 1)
            key, value = key.strip().upper(), value.strip()
            if key == 'BPM':
                try:
                    bpm = float(value)
                    if not math.isfinite(bpm) or not 30 <= bpm <= 300:
                        raise ValueError()
                    chart['bpm'] = bpm
                except ValueError:
                    fail(number, 'BPM must be 30–300')
            elif key in ('TITLE', 'SUBTITLE', 'COURSE', 'LEVEL', 'WAVE', 'OFFSET', 'DEMOSTART', 'SONGVOL', 'SEVOL', 'SCOREINIT', 'SCOREDIFF', 'GENRE'):
                chart[key.lower()] = value
            else:
                fail(number, f'Unsupported metadata: {key}')
    if not ended or 'bpm' not in chart:
        raise ValueError(f'{path}: required BPM, #START and #END')
    if roll is not None:
        raise ValueError(f'{path}: unclosed drumroll; expected 8')
    if not 0 < beat <= 4096:
        raise ValueError(f'{path}: loop must contain more than zero and at most 4096 beats')
    chart['beats'] = float(beat)
    from .metadata import apply_metadata
    return apply_metadata(chart, path)
