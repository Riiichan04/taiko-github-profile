import json
from pathlib import Path
import sys
import tempfile
import unittest
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from taiko.svg import export_svg


class SvgTests(unittest.TestCase):
    def test_short_loop_covers_visible_future_notes_throughout_cycle(self):
        """Compare exported copies to an independently repeated timeline."""
        qa=ROOT/'.qa';qa.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=qa) as directory:
            for variant in ('full', 'classic'):
                for duration in (42/190, 2, 8):
                    chart={'bpm':120,'beats':duration*2,'speed':190,
                           'notes':[{'beat':0,'type':'don'}]}
                    path=Path(directory)/'loop.svg'
                    export_svg(chart,path,variant=variant)
                    root=ET.parse(path).getroot()
                    ns={'s': 'http://www.w3.org/2000/svg'}
                    copies=root.findall(".//s:use[@href='#chart']",ns)
                    offsets=[float(e.get('transform')[10:-1].split()[0]) for e in copies]
                    distance=duration*190
                    for phase in (0, .01, .5, .99, 1-1e-8):
                        # Beat-zero primary is hidden after hitting; only future
                        # cycles are visible. Check edge entry and loop reset.
                        actual=[171+x-phase*distance for x in offsets
                                if 171+x-phase*distance-22.5 <= 766]
                        expected=[]
                        cycle=1
                        while True:
                            x=171+(cycle-phase)*distance
                            if x-22.5 > 766:
                                break
                            expected.append(x)
                            cycle+=1
                        self.assertEqual(len(actual),len(expected),(variant,duration,phase))
                        for a,b in zip(actual,expected):
                            self.assertAlmostEqual(a,b,places=4)

    def test_short_roll_repeats_bodies_with_heads(self):
        qa=ROOT/'.qa';qa.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=qa) as directory:
            path=Path(directory)/'roll.svg'
            export_svg({'bpm':120,'beats':.5,'speed':190,'notes':[
                {'beat':0,'end':.25,'type':'roll','hits':2}]},path)
            root=ET.parse(path).getroot();ns={'s':'http://www.w3.org/2000/svg'}
            heads=root.findall(".//s:use[@href='#chart']",ns)
            bodies=root.findall(".//s:use[@href='#roll-bodies']",ns)
            self.assertGreater(len(heads),1)
            self.assertEqual([e.get('transform') for e in heads],
                             [e.get('transform') for e in bodies])

    def test_vector_only_timing_and_valid_animation_schedules(self):
        qa=ROOT/'.qa';qa.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=qa) as directory:
            path=Path(directory)/'test.svg'
            chart={'bpm':120,'beats':8,'speed':190,'notes':[
                {'beat':0,'type':'don'},{'beat':1,'type':'ka'},
                {'beat':2,'end':4,'type':'roll','hits':20}]}
            export_svg(chart,path)
            root=ET.parse(path).getroot();ns={'s':'http://www.w3.org/2000/svg'}
            meta=json.loads(root.find('s:metadata',ns).text)
            self.assertEqual(meta['duration_seconds'],4)
            self.assertEqual(meta['notes'],3)
            self.assertFalse(root.findall('.//s:script',ns))
            self.assertFalse(root.findall('.//s:image',ns))
            body_clip=root.find(".//s:clipPath[@id='roll-body-lane']/s:rect",ns)
            self.assertEqual(body_clip.get('x'),'171')
            bodies=root.find(".//s:g[@id='roll-bodies']",ns)
            self.assertTrue(bodies.findall('.//s:rect',ns))
            self.assertFalse(bodies.findall('.//s:circle',ns))
            heads=root.find(".//s:g[@id='chart']",ns)
            self.assertFalse(heads.findall('.//s:rect',ns))
            for node in root.iter():
                if 'href' in node.attrib:self.assertTrue(node.attrib['href'].startswith('#'))
                if node.tag.rsplit('}',1)[-1] in ('animate','animateTransform'):
                    self.assertEqual(node.attrib['dur'],'4s')
                    if 'keyTimes' in node.attrib:
                        keys=[float(t) for t in node.attrib['keyTimes'].split(';')]
                        self.assertEqual(keys[0],0);self.assertEqual(keys[-1],1)
                        self.assertTrue(all(a<b for a,b in zip(keys,keys[1:])))
                        self.assertEqual(len(keys),len(node.attrib['values'].split(';')))
            self.assertTrue(Path(directory).resolve().is_relative_to(qa.resolve()))

    def test_empty_chart_exports_without_fake_events(self):
        qa=ROOT/'.qa';qa.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=qa) as directory:
            path=Path(directory)/'rest.svg'
            export_svg({'bpm':120,'beats':4,'speed':190,'notes':[]},path,background='original')
            text=path.read_text(encoding='utf-8')
            self.assertIn('"notes":0',text)
            self.assertTrue(Path(directory).resolve().is_relative_to(qa.resolve()))


if __name__=='__main__':unittest.main()
