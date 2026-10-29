"""Choose one constant scroll speed without modifying a chart's timing."""
import math


def auto_scroll_speed(chart, gap=0, diameter=42):
    if not math.isfinite(gap) or gap < 0:
        raise ValueError('Note gap must be a finite non-negative pixel value')
    loop = chart['beats']*60/chart['bpm']
    times = sorted(n['beat']*60/chart['bpm'] for n in chart['notes'] if n['type'] != 'roll')
    if not times:
        return chart['speed']
    gaps = [b-a for a, b in zip(times, times[1:])]
    gaps.append(loop-times[-1]+times[0])
    minimum = min(gaps)
    if minimum <= 0:
        raise ValueError('Simultaneous taps cannot be separated by changing scroll speed')
    return (diameter+gap)/minimum
