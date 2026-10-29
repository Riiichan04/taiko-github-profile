from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from run_action import run
from taiko.publish import publish_file, PublishError


class ActionTests(unittest.TestCase):
    def setUp(self):
        qa=ROOT/'.qa';qa.mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=qa)
        self.root=Path(self.temp.name);self.ws=self.root/'caller';self.ws.mkdir()
        self.runtime=self.root/'runtime';self.runtime.mkdir()
        self.env=dict(os.environ,GITHUB_WORKSPACE=str(self.ws),RUNNER_TEMP=str(self.runtime),
                      GITHUB_OUTPUT=str(self.root/'outputs'),TAIKO_PUBLISH='false')
        shutil.copyfile(ROOT/'examples/contributions.json',self.ws/'snapshot.json')
    def tearDown(self):
        self.assertTrue(self.root.resolve().is_relative_to((ROOT/'.qa').resolve()))
        self.temp.cleanup()
    def test_multiple_outputs_share_chart_and_default_30fps(self):
        (self.ws/'custom.tja').write_text('BPM:120\n#START\n12,\n#END\n')
        from taiko.export import export_animation
        with patch('run_action.export_animation', wraps=export_animation) as gif:
            result=run(dict(self.env, TAIKO_CHART='custom.tja', TAIKO_OUTPUTS=
                'dist/plain.svg?background=original\ndist/festival.svg?variant=classic\ndist/test.gif'))
        files=json.loads(result['files'])
        self.assertEqual(len(files),3)
        self.assertTrue(all(Path(p).exists() for p in files))
        self.assertEqual(gif.call_args.kwargs['fps'],30)
        from xml.etree import ElementTree as ET
        self.assertEqual(ET.parse(files[1]).getroot().get('viewBox'),'0 0 800 220')
        from PIL import Image
        with Image.open(files[2]) as image:
            durations=[]
            for i in range(image.n_frames):
                image.seek(i); durations.append(image.info['duration'])
        self.assertEqual(sum(durations),2000)

    def test_bad_output_options_fail_before_fetch(self):
        for value in ('../escape.svg', 'a.svg?bogus=1', 'a.svg?fps=0',
                      'a.svg?speed=nan', 'a.svg?background=festival&background=original',
                      'a.svg\na.svg', 'a.svg?auto-spacing=false&note-gap=2'):
            with patch('run_action.fetch_contributions',side_effect=AssertionError('fetch')):
                with self.assertRaises(ValueError):
                    run(dict(self.env,TAIKO_OUTPUTS=value))

    def test_external_action_entrypoint_and_no_code_copied(self):
        env=dict(self.env,TAIKO_SNAPSHOT='snapshot.json')
        process=subprocess.run([sys.executable,str(ROOT/'scripts/run_action.py')],cwd=self.ws,
                               env=env,capture_output=True,text=True)
        self.assertEqual(process.returncode,0,process.stderr)
        self.assertTrue((self.ws/'dist/taiko.svg').exists())
        self.assertFalse((self.ws/'scripts').exists())
        self.assertFalse((self.ws/'requirements.txt').exists())
        outputs=dict(line.split('=',1) for line in (self.root/'outputs').read_text().splitlines())
        self.assertTrue(Path(outputs['metadata']).exists())
        self.assertEqual(outputs['published'],'false')
    def test_custom_tja_keeps_tempo_without_fetching(self):
        (self.ws/'custom.tja').write_text('BPM:150\n#START\n12,\n#END\n')
        with patch('run_action.fetch_contributions',side_effect=AssertionError('unexpected API call')):
            result=run(dict(self.env,TAIKO_CHART='custom.tja',TAIKO_BPM='200'))
        self.assertEqual(result['metadata'],'')
        from xml.etree import ElementTree as ET
        metadata=ET.parse(result['file']).getroot().find('{http://www.w3.org/2000/svg}metadata')
        self.assertEqual(json.loads(metadata.text)['bpm'],150)
    def test_snapshot_seed_deterministic(self):
        env=dict(self.env,TAIKO_SNAPSHOT='snapshot.json')
        a=Path(run(env)['file']).read_bytes()
        b=Path(run(env)['file']).read_bytes()
        self.assertEqual(a,b)
    def test_unsafe_paths_and_ambiguous_inputs(self):
        for extra in ({'TAIKO_OUTPUT':'../outside.svg'},
                      {'TAIKO_CHART':'../outside.tja'},
                      {'TAIKO_CHART':'one.tja','TAIKO_SNAPSHOT':'snapshot.json'}):
            with self.assertRaises(ValueError):run(dict(self.env,**extra))
    def test_failed_fetch_leaves_existing_svg(self):
        output=self.ws/'dist/taiko.svg';output.parent.mkdir();output.write_bytes(b'last-good')
        with patch('run_action.fetch_contributions',side_effect=ValueError('offline')):
            with self.assertRaises(ValueError):run(dict(self.env,TAIKO_USERNAME='tester'))
        self.assertEqual(output.read_bytes(),b'last-good')


class PublishTests(unittest.TestCase):
    def git(self,where,*args):
        p=subprocess.run(['git','-C',str(where),*args],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        return p.stdout.strip()
    def setUp(self):
        qa=ROOT/'.qa';qa.mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=qa);self.root=Path(self.temp.name)
        self.remote=self.root/'remote.git';self.remote.mkdir()
        self.git(self.remote,'init','--bare')
        self.ws=self.root/'profile';self.ws.mkdir();self.git(self.ws,'init','-b','main')
        self.git(self.ws,'config','user.name','Local test');self.git(self.ws,'config','user.email','test@example.invalid')
        (self.ws/'README.md').write_text('Profile stays here')
        self.git(self.ws,'add','README.md');self.git(self.ws,'commit','-m','Profile')
        self.git(self.ws,'remote','add','origin',str(self.remote.resolve()))
        self.git(self.ws,'push','-u','origin','main')
        self.original=self.git(self.ws,'rev-parse','HEAD')
        (self.ws/'dist').mkdir()
        self.file=self.ws/'dist/taiko.svg';self.file.write_text('<svg/>')
        self.runtime=self.root/'runtime';self.runtime.mkdir()
    def tearDown(self):
        self.assertTrue(self.root.resolve().is_relative_to((ROOT/'.qa').resolve()))
        self.temp.cleanup()
    def test_new_output_root_commit_unchanged_skip_and_update(self):
        self.assertTrue(publish_file(self.file,self.ws,self.runtime))
        self.assertEqual(self.git(self.remote,'ls-tree','-r','--name-only','output'),'taiko.svg')
        self.assertEqual(self.git(self.remote,'show','output:taiko.svg'),'<svg/>')
        self.assertEqual(self.git(self.ws,'rev-parse','HEAD'),self.original)
        self.assertEqual(self.git(self.remote,'rev-list','--count','output'),'1')
        self.assertFalse(publish_file(self.file,self.ws,self.runtime))
        self.file.write_text('<svg><circle/></svg>')
        self.assertTrue(publish_file(self.file,self.ws,self.runtime))
        self.assertEqual(self.git(self.remote,'rev-list','--count','output'),'2')
        self.assertEqual((self.ws/'README.md').read_text(),'Profile stays here')
    def test_existing_output_files_preserved(self):
        publish_file(self.file,self.ws,self.runtime)
        self.git(self.ws,'fetch','origin','output');self.git(self.ws,'checkout','-b','output','FETCH_HEAD')
        (self.ws/'snake.svg').write_text('<svg>snake</svg>')
        self.git(self.ws,'add','snake.svg');self.git(self.ws,'commit','-m','Existing snake')
        self.git(self.ws,'push','origin','output');self.git(self.ws,'checkout','main')
        self.file.write_text('<svg>new</svg>')
        self.assertTrue(publish_file(self.file,self.ws,self.runtime))
        self.assertEqual(self.git(self.remote,'show','output:snake.svg'),'<svg>snake</svg>')
    def test_reject_main_and_unsafe_output_names(self):
        with self.assertRaises(PublishError):publish_file(self.file,self.ws,self.runtime,branch='main')
        for name in ('../outside.svg','.git/config','/absolute.svg'):
            with self.assertRaises(PublishError):publish_file(self.file,self.ws,self.runtime,filename=name)


if __name__=='__main__':unittest.main()
