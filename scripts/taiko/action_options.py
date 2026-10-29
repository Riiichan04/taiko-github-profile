"""Parse per-file Action options without treating query strings as filenames."""
import math
from urllib.parse import parse_qsl


def parse_outputs(value, defaults, resolve):
    specs = []
    seen = set()
    for line in value.splitlines():
        line = line.strip()
        if not line:
            continue
        name, _, query = line.partition('?')
        path = resolve(name)
        if path in seen:
            raise ValueError('Duplicate output path')
        seen.add(path)
        kind = path.suffix.lower().removeprefix('.')
        if kind not in ('svg', 'gif'):
            raise ValueError('Output must end in .svg or .gif')
        options = dict(defaults)
        keys = set()
        for key, val in parse_qsl(query, keep_blank_values=True, strict_parsing=True):
            if key not in options or key in keys:
                raise ValueError('Unknown or duplicate output option: '+key)
            keys.add(key)
            options[key] = val
        if options['background'] not in ('original', 'festival') or options['variant'] not in ('classic', 'full'):
            raise ValueError('Invalid background or variant')
        if options['auto-spacing'] not in ('true', 'false'):
            raise ValueError('auto-spacing must be true or false')
        options['auto-spacing'] = options['auto-spacing'] == 'true'
        for key in ('speed', 'note-gap'):
            options[key] = float(options[key])
            if not math.isfinite(options[key]):
                raise ValueError('Speed and note-gap must be finite')
        for key in ('fps', 'colors'):
            options[key] = int(options[key])
        if not 50 <= options['speed'] <= 1000 or options['note-gap'] < 0:
            raise ValueError('Invalid speed or note-gap')
        if not options['auto-spacing'] and options['note-gap']:
            raise ValueError('note-gap requires auto-spacing')
        if not 1 <= options['fps'] <= 50 or not 16 <= options['colors'] <= 256:
            raise ValueError('FPS/colors out of range')
        specs.append((path, kind, options))
    if not specs:
        raise ValueError('outputs must contain at least one file')
    return specs
