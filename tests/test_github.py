from datetime import date, datetime, timedelta, timezone
from email.message import Message
import io
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from taiko.github import fetch_contributions, credentials, GitHubError


class CalendarOpener:
    def __init__(self, missing=False):
        self.calls=[];self.missing=missing
    def open(self,request,timeout):
        payload=json.loads(request.data);self.calls.append(payload)
        variables=payload['variables']
        first=date.fromisoformat(variables['from'][:10]);last=date.fromisoformat(variables['to'][:10])
        days=[{'date':(first+timedelta(days=i)).isoformat(),'contributionCount':i%4}
              for i in range((last-first).days+1)]
        if self.missing:days.pop()
        # Extra week-edge cells must not leak into the selected date window.
        days.append({'date':(first-timedelta(days=1)).isoformat(),'contributionCount':999})
        data={'data':{'user':{'login':variables['login'], 'contributionsCollection':{
            'contributionCalendar':{'weeks':[{'contributionDays':days}]}}}}}
        return io.BytesIO(json.dumps(data).encode())


class GitHubTests(unittest.TestCase):
    def test_default_window_includes_today_and_stops_at_fetch_time(self):
        now=datetime(2026,10,30,2,15,20,tzinfo=timezone.utc)
        with patch('taiko.github.datetime') as clock:
            clock.now.return_value=now
            for days in (1,365,366):
                opener=CalendarOpener()
                snapshot=fetch_contributions('tester',days,token='test',opener=opener)
                self.assertEqual(len(snapshot['days']),days)
                self.assertEqual(snapshot['days'][0]['date'],
                                 (now.date()-timedelta(days=days-1)).isoformat())
                self.assertEqual(snapshot['days'][-1]['date'],'2026-10-30')
                self.assertTrue(snapshot['window']['includes_today'])
                self.assertEqual(opener.calls[-1]['variables']['to'],'2026-10-30T02:15:20Z')

    def test_explicit_today_historical_and_future_dates(self):
        now=datetime(2026,10,30,0,0,0,tzinfo=timezone.utc)
        with patch('taiko.github.datetime') as clock:
            clock.now.return_value=now
            today=fetch_contributions('tester',1,now.date(),token='test',opener=CalendarOpener())
            self.assertTrue(today['window']['includes_today'])
            opener=CalendarOpener()
            historical=fetch_contributions('tester',1,date(2026,10,29),token='test',opener=opener)
            self.assertFalse(historical['window']['includes_today'])
            self.assertEqual(opener.calls[0]['variables']['to'],'2026-10-29T23:59:59Z')
            with self.assertRaises(ValueError):
                fetch_contributions('tester',1,date(2026,10,31),token='test',opener=CalendarOpener())

    def test_full_year_chunking_exact_dates_and_no_token_in_snapshot(self):
        opener=CalendarOpener()
        snapshot=fetch_contributions('Riiichan04',365,date(2025,12,31),token='test-secret',opener=opener)
        self.assertEqual(len(opener.calls),5)
        self.assertEqual(len(snapshot['days']),365)
        self.assertEqual(snapshot['days'][0]['date'],'2025-01-01')
        self.assertEqual(snapshot['days'][-1]['date'],'2025-12-31')
        self.assertNotIn('test-secret',json.dumps(snapshot))
        self.assertTrue(all(d['count']<999 for d in snapshot['days']))

    def test_partial_calendar_is_error_not_empty_activity(self):
        with self.assertRaisesRegex(GitHubError,'incomplete'):
            fetch_contributions('tester',7,date(2025,12,31),token='test',opener=CalendarOpener(missing=True))

    def test_graphql_error_redacts_token_and_rejects_partial_data(self):
        class Bad:
            def open(self,*args,**kwargs):
                return io.BytesIO(json.dumps({'errors':[{'message':'denied test-secret'}],'data':{}}).encode())
        with self.assertRaises(GitHubError) as error:
            fetch_contributions('tester',1,date(2025,12,31),token='test-secret',opener=Bad())
        self.assertNotIn('test-secret',str(error.exception))

    def test_unauthorized_not_retried(self):
        class Bad:
            calls=0
            def open(self,*args,**kwargs):
                self.calls+=1
                raise HTTPError('https://api.github.com/graphql',401,'Unauthorized',{},None)
        opener=Bad()
        with self.assertRaisesRegex(GitHubError,'401'):
            fetch_contributions('tester',1,date(2025,12,31),token='test',opener=opener)
        self.assertEqual(opener.calls,1)

    def test_retry_rate_limit(self):
        class Retry(CalendarOpener):
            tries=0
            def open(self,*args,**kwargs):
                self.tries+=1
                if self.tries==1:
                    headers=Message();headers['Retry-After']='2'
                    raise HTTPError('https://api.github.com/graphql',429,'Limited',headers,None)
                return super().open(*args,**kwargs)
        opener=Retry();delays=[]
        snapshot=fetch_contributions('tester',1,date(2025,12,31),token='test',opener=opener,sleeper=delays.append)
        self.assertEqual(len(snapshot['days']),1)
        self.assertEqual(delays,[2])

    def test_missing_user(self):
        class Missing:
            def open(self,*args,**kwargs):
                return io.BytesIO(b'{"data":{"user":null}}')
        with self.assertRaisesRegex(GitHubError,'not found'):
            fetch_contributions('tester',1,date(2025,12,31),token='test',opener=Missing())

    def test_invalid_json_shape(self):
        class Invalid:
            def open(self,*args,**kwargs):
                return io.BytesIO(b'[]')
        with self.assertRaisesRegex(GitHubError,'unexpected JSON'):
            fetch_contributions('tester',1,date(2025,12,31),token='test',opener=Invalid())

    def test_fetch_failure_preserves_existing_output(self):
        import tempfile
        from contextlib import redirect_stderr
        import github_contributions as cli
        root=Path(__file__).resolve().parents[1]
        qa=root/'.qa';qa.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=qa) as folder:
            output=Path(folder)/'last-good.gif';output.write_bytes(b'last-good-output')
            with patch.object(sys,'argv',['github_contributions.py','tester','--output',str(output)]):
                with patch.object(cli,'fetch_contributions',side_effect=GitHubError('offline')):
                    with redirect_stderr(io.StringIO()):
                        with self.assertRaises(SystemExit) as error:cli.main()
            self.assertEqual(error.exception.code,1)
            self.assertEqual(output.read_bytes(),b'last-good-output')
            self.assertTrue(Path(folder).resolve().is_relative_to(qa.resolve()))

    def test_missing_credentials_and_bad_inputs(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaisesRegex(GitHubError,'GH_TOKEN'):
                credentials()
        for username in ('https://github.com/tester','../tester','a b'):
            with self.assertRaises(ValueError):
                fetch_contributions(username,token='test')
        with self.assertRaises(ValueError):
            fetch_contributions('tester',367,token='test')
        with self.assertRaises(ValueError):
            fetch_contributions('tester',end_date=date(9999,1,1),token='test')


if __name__=='__main__':unittest.main()
