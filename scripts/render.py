"""CLI entry point: render Taiko GIFs from a TJA chart."""
import argparse
from pathlib import Path
from taiko.chart import load_chart
from taiko.renderer import make_frame_renderer
from taiko.export import export_animation
from taiko.spacing import auto_scroll_speed

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chart', type=Path, default=ROOT/'charts/demo.tja')
    parser.add_argument('--variant', choices=['classic', 'full', 'festival'], default='classic')
    parser.add_argument('--background', choices=['original', 'festival'], default='original')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--speed', type=float, default=190, help='Visual speed: 50–1000 px/s')
    parser.add_argument('--auto-spacing', action='store_true', help='Override --speed to fit the tightest tap spacing without changing timing')
    parser.add_argument('--note-gap', type=float, default=0, help='Pixel gap between closest taps with --auto-spacing (default: touching)')
    parser.add_argument('--fps', type=int, default=25, help='GIF frame rate: 1–50')
    parser.add_argument('--colors', type=int, default=96, help='GIF palette: 16–256 colors')
    args = parser.parse_args()
    if args.variant == 'festival':
        args.variant, args.background = 'classic', 'festival'
    if args.output is None:
        name = 'taiko' + ('-full' if args.variant == 'full' else '')
        name += '-festival' if args.background == 'festival' else ''
        args.output = ROOT/'generated'/'renders'/f'{name}.gif'
    chart = load_chart(args.chart, speed=args.speed)
    if args.auto_spacing:
        chart['speed'] = auto_scroll_speed(chart, gap=args.note_gap)
        print(f"Auto spacing: {chart['speed']:.2f} px/s; chart timing unchanged")
    elif args.note_gap != 0:
        parser.error('--note-gap requires --auto-spacing')
    export_animation(chart, make_frame_renderer(chart, args.variant, args.background),
                     args.output, fps=args.fps, colors=args.colors)


if __name__ == "__main__":
    main()
