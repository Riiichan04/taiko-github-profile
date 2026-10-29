import copy
from datetime import date, timedelta
import json
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from taiko.chart import load_chart
from taiko.contributions import Rules, generate
from taiko.export import export_animation
from taiko.renderer import make_frame_renderer, render_variant


def snapshot(values, first=date(2025, 1, 1)):
    return {'username': 'tester', 'days': [
        {'date': (first+timedelta(days=i)).isoformat(), 'count': n}
        for i, n in enumerate(values)]}


class PipelineTests(unittest.TestCase):
    def setUp(self):
        qa = ROOT/'.qa'
        qa.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=qa)
        self.directory = Path(self.temporary.name)

    def tearDown(self):
        self.assertTrue(self.directory.resolve().is_relative_to((ROOT/'.qa').resolve()))
        self.temporary.cleanup()

    def build(self, values, bpm=120, name='chart'):
        path, meta = generate(snapshot(values), self.directory, Rules(bpm=bpm), name)
        return path, load_chart(path), meta

    def test_uniform_year_has_no_roll_or_spike_stream(self):
        for count in (0, 1, 20):
            _, chart, meta = self.build([count]*365)
            self.assertFalse(any(n['type']=='roll' for n in chart['notes']))
            self.assertFalse(any(s['kind']=='spike_stream' for s in meta['segments']))
            self.assertEqual(len(chart['notes']), 365 if count else 0)

    def test_peak_groups_ties_and_exact_stream_count(self):
        _, chart, meta = self.build([1]*50+[37,20,0,20,20])
        self.assertEqual([r['hits'] for r in meta['rolls']], [37,20])
        self.assertEqual([s['count'] for s in meta['segments'] if s['kind']=='spike_stream'], [20,20])
        for segment in meta['segments']:
            if segment['kind']=='spike_stream':
                taps = [n for n in chart['notes'] if segment['start_beat']<=n['beat']<segment['end_beat']]
                self.assertEqual(len(taps), segment['count'])
        self.assertEqual([n['hits'] for n in chart['notes'] if n['type']=='roll'], [37,20])

    def test_low_percentile_outlier_not_roll(self):
        _, chart, meta = self.build([1]*50+[5])
        self.assertFalse(any(n['type']=='roll' for n in chart['notes']))
        self.assertEqual(meta['segments'][-1]['notes_or_hits'], 5)

    def test_long_rest_seconds_independent_of_bpm(self):
        for bpm in (120,150,200):
            _, _, meta = self.build([1]+[0]*30+[1], bpm)
            rest = next(s for s in meta['segments'] if s['kind']=='rest')
            self.assertAlmostEqual(rest['duration_seconds'],30/7)

    def test_streak_break_and_eight_day_rule(self):
        _, _, short = self.build([1]*7)
        self.assertTrue(all(s['kind']=='normal' for s in short['segments']))
        _, _, long = self.build([1]*8+[0]+[1]*7)
        self.assertTrue(all(s['kind']=='streak_stream' for s in long['segments'][:8]))
        self.assertTrue(all(s['kind']=='normal' for s in long['segments'][-7:]))

    def test_new_low_days_and_sliding_window_preserve_old_patterns(self):
        base=[1]*50+[37,20,0]+[1]*10
        _, _, a = self.build(base, name='a')
        _, _, b = self.build(base+[1,2], name='b')
        for day in a['segments']:
            other=next(s for s in b['segments'] if s['date']==day['date'])
            self.assertEqual(day['kind'],other['kind'])
            self.assertEqual(day['pattern_seed'],other['pattern_seed'])
        shifted=snapshot(base[1:]+[1], first=date(2025,1,2))
        _, c=generate(shifted,self.directory, name='shifted')
        peak=next(s for s in a['segments'] if s['count']==20)
        self.assertEqual(peak['pattern_seed'],next(s for s in c['segments'] if s['date']==peak['date'])['pattern_seed'])

    def test_metadata_roundtrip_and_tampering(self):
        path, chart, _=self.build([1]*50+[37,20])
        self.assertEqual(chart,load_chart(path))
        path.write_bytes(path.read_bytes()+b'\n// edited\n')
        with self.assertRaisesRegex(ValueError,'TJA changed'):
            load_chart(path)

    def test_missing_date_fills_rest_and_duplicates_fail(self):
        data=snapshot([1,1,1]);data['days'].pop(1)
        _,meta=generate(data,self.directory)
        self.assertEqual(meta['days'][1]['count'],0)
        data['days'].append(data['days'][0])
        with self.assertRaises(ValueError):generate(data,self.directory)

    def test_prepared_scene_pixels_and_seam(self):
        _,chart,_=self.build([1]*10+[37,20,0])
        original=copy.deepcopy(chart)
        for variant in ('classic','full'):
            for background in ('original','festival'):
                prepared=make_frame_renderer(chart,variant,background)
                for t in (0,.125,1.7,chart['beats']/2-.01):
                    self.assertEqual(prepared(t).tobytes(),render_variant(chart,t,variant,background).tobytes())
                self.assertEqual(prepared(0).tobytes(),prepared(chart['beats']/2).tobytes())
        self.assertEqual(chart,original)

    def test_export_timing_static_holds_and_no_trails(self):
        chart={'beats':4,'bpm':120,'notes':[]}
        def frame(t):
            im=Image.new('RGB',(64,24),'black')
            ImageDraw.Draw(im).rectangle((int(t*16),4,int(t*16)+6,10),fill='white')
            return im
        path=self.directory/'moving.gif'
        export_animation(chart,frame,path,fps=25)
        with Image.open(path) as im:
            duration=0
            for i in range(im.n_frames):
                im.seek(i)
                self.assertEqual(im.convert('RGB').tobytes(),frame(duration/1000).tobytes())
                duration+=im.info['duration']
            self.assertEqual(duration,2000)
        stats=export_animation(chart,lambda t:Image.new('RGB',(64,24),'black'),self.directory/'hold.gif',fps=15)
        self.assertEqual(stats['stored_frames'],1)
        with Image.open(self.directory/'hold.gif') as im:
            self.assertEqual(im.info['duration'],2000)

    def test_long_gif_holds_keep_duration_and_pixels(self):
        for seconds in (655.35, 700, 1400):
            for optimize in (False, True):
                path=self.directory/f'hold-{seconds}-{optimize}.gif'
                expected=Image.new('RGB',(4,4),'#123456')
                stats=export_animation({'beats':seconds*2,'bpm':120,'notes':[]},
                                       lambda t:expected.copy(),path,fps=1,optimize=optimize)
                with Image.open(path) as image:
                    elapsed=0
                    self.assertEqual(image.info['loop'],0)
                    self.assertEqual(image.n_frames,stats['stored_frames'])
                    for i in range(image.n_frames):
                        image.seek(i)
                        delay=image.info['duration']
                        self.assertLessEqual(delay,655350)
                        self.assertGreater(delay,0)
                        self.assertEqual(image.convert('RGB').tobytes(),expected.tobytes())
                        elapsed+=delay
                    self.assertEqual(elapsed,round(seconds*100)*10)

    def test_long_gif_hold_then_color_change_has_no_trails(self):
        def frame(t):
            return Image.new('RGB',(4,4),'black' if t<700 else 'white')
        path=self.directory/'long-transition.gif'
        export_animation({'beats':2800,'bpm':120,'notes':[]},frame,path,fps=1)
        with Image.open(path) as image:
            elapsed=0
            for i in range(image.n_frames):
                image.seek(i)
                self.assertEqual(image.convert('RGB').tobytes(),frame(elapsed/1000).tobytes())
                elapsed+=image.info['duration']
            self.assertEqual(elapsed,1400000)


if __name__=='__main__':unittest.main()
