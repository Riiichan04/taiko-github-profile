"""Note lane, target, scrolling notes and beat markers."""
import math
from bisect import bisect_left, bisect_right
from .config import WIDTH, TARGET, CENTER, INK, CREAM, DON, KA


def draw_lane(canvas):
    d = canvas.draw
    box, oval, line = canvas.box, canvas.oval, canvas.line
    box((150, 65, WIDTH, 173), INK, CREAM, 3)
    box((154, 69, WIDTH, 169), '#302b32')
    line([(155, CENTER), (WIDTH, CENTER)], '#504047', 1)

def draw_target(canvas, pulse):
    d = canvas.draw
    box, oval, line = canvas.box, canvas.oval, canvas.line
    if pulse:
        r = 31 + (1-pulse)*11
        oval((TARGET-r, CENTER-r, TARGET+r, CENTER+r), None, '#ffd87d', 2)
    oval((TARGET-28, CENTER-28, TARGET+28, CENTER+28), '#302b32', CREAM, 3)
    oval((TARGET-20, CENTER-20, TARGET+20, CENTER+20), None, '#78675f', 1)

def draw_notes(canvas, chart, time, beat_seconds, loop, scene=None):
    d = canvas.draw
    box, oval, line = canvas.box, canvas.oval, canvas.line
    # Don and ka are intentionally plain colored circles.
    horizon = (WIDTH-TARGET+30)/chart['speed']
    candidates = chart['notes']
    if scene is not None:
        visible = set()
        for repeat in range(-1, math.ceil(horizon/loop)+2):
            lo = bisect_left(scene['starts'], time-repeat*loop-scene['max_roll'])
            hi = bisect_right(scene['starts'], time-repeat*loop+horizon)
            visible.update(range(lo, hi))
        candidates = [scene['notes'][i] for i in sorted(visible)]
    for note in reversed(candidates):
        base = note['beat']*beat_seconds
        for repeat in range(-1, math.ceil(horizon/loop)+2):
            delta = base+repeat*loop-time
            if note['type'] == 'roll':
                tail = note['end']*beat_seconds+repeat*loop-time
                if tail < 0 or delta > horizon:
                    continue
                x = TARGET+max(0, delta)*chart['speed']
                end_x = TARGET+tail*chart['speed']
                box((x, CENTER-18, end_x, CENTER+18), '#f5c64d', INK, 2, 16)
                oval((x-20, CENTER-20, x+20, CENTER+20), '#ffd866', INK, 3)
                oval((x-15, CENTER-15, x+15, CENTER+15), None, CREAM, 2)
                continue
            if not 0 < delta <= horizon:
                continue
            x = TARGET+delta*chart['speed']
            color = DON if note['type']=='don' else KA
            oval((x-21, CENTER-21, x+21, CENTER+21), color, INK, 3)
            oval((x-17, CENTER-17, x+17, CENTER+17), None, CREAM, 2)

def draw_markers(canvas, time, loop):
    d = canvas.draw
    box, oval, line = canvas.box, canvas.oval, canvas.line
    # Avoid fonts entirely: beat markers and colored legend remain portable.
    for i in range(16):
        x = 183+i*34
        active = i == int(time/loop*16) % 16
        box((x, 185, x+19, 189), CREAM if active else '#a84e37', radius=2)
    oval((180, 28, 190, 38), DON, CREAM)
    oval((200, 28, 210, 38), KA, CREAM)
    line([(224, 33), (WIDTH-25, 33)], '#f5aa6f', 2)
