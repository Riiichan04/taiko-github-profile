"""Drum geometry and alternating don/ka hit feedback."""
import math
from .config import SCALE, DON, KA

ROLL_VISUAL_RATE = 0.72


def roll_visual_feedback(roll, time, beat_seconds):
    """Visual-only hit frequency: 90% of original, reduced a further 20%."""
    start, end = roll['beat']*beat_seconds, roll['end']*beat_seconds
    if not start <= time < end:
        return None
    count = roll.get('hits', max(1, round((end-start)*16)))
    period = (end-start)/count/ROLL_VISUAL_RATE
    cycle = (time-start)/period
    age = (cycle-math.floor(cycle))*period
    return {'type': 'don', 'hand': 'left' if math.floor(cycle) % 2 == 0 else 'right'}, max(0, 1-age/.16)


def draw_drum(canvas, chart, time, loop, hits, pulse, cylindrical=False, latest=None):
    d = canvas.draw
    box, oval, line = canvas.box, canvas.oval, canvas.line
    visual = next((feedback for roll in chart.get('rolls', [])
                   if (feedback := roll_visual_feedback(roll, time, 60/chart['bpm'])) is not None), None)
    if visual is not None:
        pulse = visual[1]
    # Circular skin and circular red shell, offset vertically for depth.
    bounce = -2*pulse
    oval((29, 169, 125, 179), '#bf5138')
    if cylindrical:
        # Equal circular end caps, offset down by 23px, joined by straight walls.
        oval((28, 76+bounce, 126, 174+bounce), '#e55b43', '#302a30', 3)
        box((28, 102+bounce, 126, 125+bounce), '#e55b43')
        line([(28, 102+bounce), (28, 125+bounce)], '#302a30', 3)
        line([(126, 102+bounce), (126, 125+bounce)], '#302a30', 3)
    else:
        oval((29, 78+bounce, 125, 174+bounce), '#e55b43', '#302a30', 3)
        oval((33, 79+bounce, 121, 167+bounce), '#ed6749')
    oval((28, 60+bounce, 126, 158+bounce), '#cbd0dc', '#302a30', 3)
    oval((28, 53+bounce, 126, 151+bounce), '#faf9f5', '#302a30', 3)
    oval((36, 61+bounce, 118, 143+bounce), '#e9edf6', '#d3d9e5', 1)
    if latest is None:
        latest = min(range(len(hits)), key=lambda i: (time-hits[i]) % loop) if hits else None
    if latest is not None and pulse > 0:
        note = visual[0] if visual is not None else chart['notes'][latest]
        side = note.get('hand', 'left' if latest % 2 == 0 else 'right')
        start_angle, end_angle = (90, 270) if side == 'left' else (-90, 90)
        if note['type'] == 'don':
            bounds = (40, 65+bounce, 114, 139+bounce)
            d.pieslice(tuple(round(v*SCALE) for v in bounds), start_angle, end_angle, fill=DON)
        else:
            bounds = (31, 56+bounce, 123, 148+bounce)
            d.arc(tuple(round(v*SCALE) for v in bounds), start_angle, end_angle, fill=KA, width=6*SCALE)
    for angle in range(20, 170, 25):
        a = math.radians(angle)
        x, y = 77+46*math.cos(a), 109+bounce+46*math.sin(a)
        oval((x-1.2, y-1.2, x+1.2, y+1.2), '#66595d')
