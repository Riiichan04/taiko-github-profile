"""Generate a reproducible TJA + metadata from an offline dated snapshot."""
import argparse
import json
from pathlib import Path
from taiko.contributions import generate, Rules


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', type=Path)
    parser.add_argument('--output-directory', type=Path, default=Path('generated/contributions'))
    parser.add_argument('--bpm', type=int, default=120)
    parser.add_argument('--seed', default='default')
    args = parser.parse_args()
    snapshot = json.loads(args.snapshot.read_text(encoding='utf-8'))
    path, meta = generate(snapshot, args.output_directory, Rules(bpm=args.bpm, seed=args.seed))
    print(f'{path}: {len(meta["days"])} days; {meta["duration_seconds"]:.2f}s; metadata saved')


if __name__ == '__main__':
    main()
