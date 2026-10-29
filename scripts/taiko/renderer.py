"""Frame composition and layout variants."""
from PIL import Image
from bisect import bisect_right
from .config import WIDTH, HEIGHT, SCALE
from .drawing import Canvas
from .backgrounds import draw_background
from .drum import draw_drum
from .highway import draw_lane, draw_target, draw_notes, draw_markers


def prepare_scene(chart):
    """Compute feedback and temporal indices once per export, not per frame."""
    beat_seconds = 60/chart['bpm']
    feedback = []
    for note in chart['notes']:
        if note['type'] == 'roll':
            count = note.get('hits', max(1, round((note['end']-note['beat'])*beat_seconds*16)))
            feedback.extend({'beat': note['beat']+(note['end']-note['beat'])*i/count,
                             'type': 'don'} for i in range(count))
        else:
            feedback.append(note)
    feedback.sort(key=lambda n: n['beat'])
    notes = sorted(chart['notes'], key=lambda n: n['beat'])
    return {'feedback': feedback, 'hits': [n['beat']*beat_seconds for n in feedback],
            'rolls': [n for n in notes if n['type'] == 'roll'],
            'notes': notes, 'starts': [n['beat']*beat_seconds for n in notes],
            'max_roll': max(((n['end']-n['beat'])*beat_seconds for n in notes if n['type']=='roll'), default=0)}


def render_frame(chart, time, cylindrical=False, festival=False, scene=None):
    # Normalize loop boundaries before floating-point note-position arithmetic.
    time %= chart['beats']*60/chart['bpm']
    image = Image.new('RGB', (WIDTH*SCALE, HEIGHT*SCALE), '#e66a42')
    canvas = Canvas(image)
    draw_background(canvas, festival)
    draw_lane(canvas)
    # Repeat the chart in time, so notes approaching across the seam stay continuous.
    beat_seconds = 60/chart['bpm']
    loop = chart['beats']*beat_seconds
    scene = scene if scene is not None else prepare_scene(chart)
    feedback, hits = scene['feedback'], scene['hits']
    latest = (bisect_right(hits, time)-1) % len(hits) if hits else None
    age = (time-hits[latest]) % loop if hits else loop
    pulse = max(0, 1-age/.16)
    draw_target(canvas, pulse)
    draw_drum(canvas, {**chart, 'notes': feedback,
                      'rolls': scene['rolls']},
              time, loop, hits, pulse, cylindrical, latest=latest)
    draw_notes(canvas, chart, time, beat_seconds, loop, scene=scene)
    draw_markers(canvas, time, loop)
    return image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)


def render_variant(chart, time, variant='classic', background='original', scene=None):
    # Keep the earlier experimental command working as an alias.
    if variant == 'festival':
        variant, background = 'classic', 'festival'
    frame = render_frame(chart, time, cylindrical=variant == 'full', festival=background == 'festival', scene=scene)
    if variant != 'full':
        return frame
    # Compact strip: native-sized highway, uniformly reduced drum panel.
    # Crop decorative space rather than stretching notes into large circles.
    panel_height = 140
    compact_height = 108
    panel_width = round(150*compact_height/panel_height)
    full = Image.new('RGB', (panel_width+WIDTH-150, compact_height), '#302b32')
    panel = frame.crop((0, 40, 150, 180)).resize(
        (panel_width, compact_height), Image.Resampling.LANCZOS)
    full.paste(panel, (0, 0))
    lane = frame.crop((150, 65, WIDTH, 173))
    full.paste(lane, (panel_width, 0))
    return full


def make_frame_renderer(chart, variant='classic', background='original'):
    scene = prepare_scene(chart)
    return lambda time: render_variant(chart, time, variant, background, scene=scene)


