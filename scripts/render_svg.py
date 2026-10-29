"""Export an experimental vector-only animated compact SVG from TJA."""
import argparse
from pathlib import Path
from taiko.chart import load_chart
from taiko.spacing import auto_scroll_speed
from taiko.svg import export_svg


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chart',type=Path,default=Path('charts/demo.tja'))
    parser.add_argument('--output',type=Path,default=Path('generated/renders/taiko.svg'))
    parser.add_argument('--background',choices=['original','festival'],default='festival')
    parser.add_argument('--speed',type=float,default=190)
    parser.add_argument('--auto-spacing',action='store_true')
    parser.add_argument('--note-gap',type=float,default=0)
    args=parser.parse_args()
    chart=load_chart(args.chart,speed=args.speed)
    if args.auto_spacing:chart['speed']=auto_scroll_speed(chart,args.note_gap)
    elif args.note_gap:parser.error('--note-gap requires --auto-spacing')
    export_svg(chart,args.output,args.background)


if __name__=='__main__':main()
