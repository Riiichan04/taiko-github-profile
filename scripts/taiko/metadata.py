"""Hash-bound sidecar metadata; edited TJA cannot silently use stale roll data."""
from hashlib import sha256
import json
import math


def apply_metadata(chart, tja_path):
    sidecar = tja_path.with_suffix('.meta.json')
    if not sidecar.exists():
        return chart
    data = json.loads(sidecar.read_text(encoding='utf-8'))
    if data.get('schema_version') != 1:
        raise ValueError(f'{sidecar}: unsupported metadata schema')
    if data.get('tja_sha256') != sha256(tja_path.read_bytes()).hexdigest():
        raise ValueError(f'{sidecar}: TJA changed; regenerate metadata or remove the sidecar for custom playback')
    actual = [n for n in chart['notes'] if n['type'] == 'roll']
    saved = data.get('rolls', [])
    if len(actual) != len(saved):
        raise ValueError(f'{sidecar}: roll count mismatch')
    for note, roll in zip(actual, saved):
        if (not math.isclose(note['beat'], roll['beat'], abs_tol=1e-8) or
                not math.isclose(note['end'], roll['end'], abs_tol=1e-8) or
                type(roll.get('hits')) is not int or not 1 <= roll['hits'] <= 100_000):
            raise ValueError(f'{sidecar}: invalid roll timing or strike count')
        note['hits'] = roll['hits']
    return chart
