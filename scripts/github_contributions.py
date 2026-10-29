"""GitHub GraphQL → dated snapshot → TJA/metadata → README GIF."""
import argparse
import math
from datetime import date
from pathlib import Path
import sys
from taiko.github import fetch_contributions, save_snapshot, GitHubError
from taiko.contributions import generate, Rules
from taiko.chart import load_chart
from taiko.spacing import auto_scroll_speed
from taiko.renderer import make_frame_renderer
from taiko.export import export_animation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('username')
    parser.add_argument('--days', type=int, default=365)
    parser.add_argument('--end-date', type=date.fromisoformat, help='Last UTC date, today or earlier (YYYY-MM-DD); defaults to today')
    parser.add_argument('--output-directory', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--bpm', type=int, default=120)
    parser.add_argument('--seed', default='default')
    parser.add_argument('--variant', choices=['classic','full'], default='full')
    parser.add_argument('--background', choices=['original','festival'], default='festival')
    parser.add_argument('--auto-spacing', action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument('--speed', type=float, default=190)
    parser.add_argument('--note-gap', type=float, default=0)
    parser.add_argument('--fps', type=int, default=25)
    parser.add_argument('--colors', type=int, default=96)
    parser.add_argument('--fetch-only', action='store_true')
    args = parser.parse_args()
    if not 30 <= args.bpm <= 300 or not 1 <= args.fps <= 50 or not 16 <= args.colors <= 256:
        parser.error('Expected BPM 30–300, FPS 1–50, colors 16–256')
    if not math.isfinite(args.speed) or not 50 <= args.speed <= 1000:
        parser.error('--speed must be 50–1000 px/s')
    if not math.isfinite(args.note_gap) or args.note_gap < 0:
        parser.error('--note-gap must be finite and non-negative')
    if not args.auto_spacing and args.note_gap:
        parser.error('--note-gap requires --auto-spacing')
    try:
        snapshot = fetch_contributions(args.username, args.days, args.end_date)
        directory = args.output_directory or Path('generated')/f'github-{snapshot["username"]}'
        save_snapshot(snapshot, directory/'snapshot.json')
        print(f'Fetched {len(snapshot["days"])} UTC calendar days for {snapshot["username"]}; '
              f'{sum(d["count"] for d in snapshot["days"])} contributions')
        if args.fetch_only:
            print(directory/'snapshot.json')
            return
        tja, metadata = generate(snapshot, directory, Rules(bpm=args.bpm, seed=args.seed))
        chart = load_chart(tja, speed=args.speed)
        if args.auto_spacing:
            chart['speed'] = auto_scroll_speed(chart, args.note_gap)
        output = args.output or directory/'taiko.gif'
        print(f'Chart: {metadata["duration_seconds"]:.2f}s; scroll {chart["speed"]:.2f}px/s')
        export_animation(chart, make_frame_renderer(chart, args.variant, args.background),
                         output, fps=args.fps, colors=args.colors)
    except (GitHubError, ValueError) as error:
        print(f'Error: {error}', file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
