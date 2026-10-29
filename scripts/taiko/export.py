"""Memory-conscious GIF export with one global palette and timed holds."""
import math
import time
from PIL import Image, ImageChops, GifImagePlugin
from .config import FPS


MAX_GIF_DELAY_MS = 65535*10


def write_long_holds(path, frames, durations):
    """Encode delay chunks directly so Pillow cannot merge identical frames again.

    Frames already share one opaque palette. Full-frame writes with disposal=1
    preserve the exact pixels, without introducing a blinking sentinel pixel.
    Ordinary animations keep Pillow's smaller delta-frame encoding below.
    """
    stored = 0
    with path.open('wb') as stream:
        header, _ = GifImagePlugin.getheader(frames[0].copy(), info={'loop': 0, 'optimize': False})
        for block in header:
            stream.write(block)
        for frame, duration in zip(frames, durations):
            while duration:
                delay = min(duration, MAX_GIF_DELAY_MS)
                for block in GifImagePlugin.getdata(frame, duration=delay, disposal=1):
                    stream.write(block)
                duration -= delay
                stored += 1
        stream.write(b';')
    return stored


def export_animation(chart, frame_at, output, fps=FPS, colors=96, optimize=True):
    if type(fps) is not int or not 1 <= fps <= 50:
        raise ValueError('FPS must be an integer from 1 to 50')
    if type(colors) is not int or not 16 <= colors <= 256:
        raise ValueError('Palette colors must be 16–256')
    started = time.perf_counter()
    seconds = chart['beats']*60/chart['bpm']
    total_ticks = max(1, round(seconds*100))
    count = max(1, math.ceil(total_ticks*fps/100))
    if count > 100_000:
        raise ValueError('Export exceeds 100,000 frames; reduce FPS or chart length')
    ticks = [round(i*100/fps) for i in range(count)] + [total_ticks]
    sample_times = [0, min(.1, seconds/2), seconds/3, seconds*2/3]
    # Sample actual note types too, so yellow rolls are present in the palette.
    for kind in ('don', 'ka', 'roll'):
        note = next((n for n in chart['notes'] if n['type'] == kind), None)
        if note:
            sample_times.append(note['beat']*60/chart['bpm']+.02)
    first = frame_at(0)
    width, height = first.size
    atlas = Image.new('RGB', (width, height*len(sample_times)))
    for i, timestamp in enumerate(sample_times):
        atlas.paste(frame_at(timestamp), (0, i*height))
    palette = atlas.quantize(colors=colors)
    del atlas
    frames, durations = [], []
    # Quantize immediately: never retain the full RGB animation in memory.
    for i in range(count):
        frame = frame_at(ticks[i]/100).quantize(palette=palette, dither=Image.Dither.NONE)
        delay = (ticks[i+1]-ticks[i])*10
        if frames and ImageChops.difference(frames[-1], frame).getbbox() is None:
            durations[-1] += delay
        else:
            frames.append(frame)
            durations.append(delay)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Write beside the destination, then replace only after encoding succeeds.
    temporary = output.with_name(output.name+'.tmp')
    stored_frames = len(frames)
    try:
        if any(delay > MAX_GIF_DELAY_MS for delay in durations):
            stored_frames = write_long_holds(temporary, frames, durations)
        else:
            frames[0].save(temporary, format='GIF', save_all=True, append_images=frames[1:],
                           duration=durations, loop=0, optimize=optimize, disposal=1)
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    frame_at(min(1.72, seconds/2)).save(output.with_suffix('.png'))
    stats = {'source_frames': count, 'stored_frames': stored_frames, 'fps': fps,
             'duration_seconds': total_ticks/100, 'size_bytes': output.stat().st_size,
             'elapsed_seconds': round(time.perf_counter()-started, 3),
             'estimated_frame_pixel_bytes': len(frames)*width*height}
    print(f'{output}: {count} source / {stored_frames} stored frames, {width}x{height}, '
          f'{stats["size_bytes"]/1024:.0f} KiB, {stats["elapsed_seconds"]:.2f}s')
    return stats
