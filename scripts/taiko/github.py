"""Read dated contributions from GitHub GraphQL without persisting credentials."""
from datetime import date, datetime, timedelta, timezone
import json
import os
import re
import ssl
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler

ENDPOINT = 'https://api.github.com/graphql'
QUERY = '''query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    login
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}'''


class GitHubError(RuntimeError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def credentials():
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if not token or not token.strip():
        raise GitHubError('Set GH_TOKEN or GITHUB_TOKEN in your environment; never pass a token in command arguments')
    token = token.strip()
    if any(c.isspace() for c in token):
        raise GitHubError('Invalid token: whitespace is not allowed')
    return token


def _request(variables, token, opener, sleeper):
    payload = json.dumps({'query': QUERY, 'variables': variables}).encode()
    request = Request(ENDPOINT, data=payload, method='POST', headers={
        'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json',
        'Content-Type': 'application/json', 'User-Agent': 'tiny-taiko-contributions'})
    for attempt in range(3):
        try:
            with opener.open(request, timeout=30) as response:
                body = json.loads(response.read(8_000_000))
            if not isinstance(body, dict):
                raise GitHubError('GitHub returned an unexpected JSON response')
            if body.get('errors'):
                messages = '; '.join(str(e.get('message', 'GraphQL error')) if isinstance(e, dict)
                                     else 'GraphQL error' for e in body['errors'])
                raise GitHubError('GitHub GraphQL: '+messages.replace(token, '[redacted]')[:500])
            return body
        except HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 504) and attempt < 2:
                try:
                    delay = min(10, max(1, float(exc.headers.get('Retry-After', 2**attempt))))
                except (TypeError, ValueError):
                    delay = 2**attempt
                sleeper(delay)
                continue
            if exc.code == 401:
                raise GitHubError('GitHub authentication failed (401); check the environment token') from None
            if exc.code == 403:
                raise GitHubError('GitHub refused access (403); check token permissions and rate limits') from None
            raise GitHubError(f'GitHub request failed (HTTP {exc.code}); previous output was not replaced') from None
        except (URLError, TimeoutError) as exc:
            if isinstance(getattr(exc, 'reason', None), ssl.SSLCertVerificationError):
                raise GitHubError('TLS certificate verification failed; configure a trusted CA store for Python (verification is never disabled)') from None
            if attempt < 2:
                sleeper(2**attempt)
                continue
            raise GitHubError('Cannot reach GitHub after 3 attempts; previous output was not replaced') from None
        except (ValueError, UnicodeError):
            raise GitHubError('GitHub returned an invalid JSON response') from None


def fetch_contributions(username, days=365, end_date=None, *, token=None, opener=None, sleeper=time.sleep):
    if not isinstance(username, str) or not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?', username):
        raise ValueError('Expected a GitHub username, not a profile URL')
    if type(days) is not int or not 1 <= days <= 366:
        raise ValueError('Days must be 1–366')
    now = datetime.now(timezone.utc)
    today = now.date()
    end = end_date if end_date is not None else today
    if type(end) is not date or end > today:
        raise ValueError('End date must be today or an earlier UTC day')
    start = end-timedelta(days=days-1)
    token = token if token is not None else credentials()
    if not token or any(c.isspace() for c in token):
        raise GitHubError('Invalid token')
    opener = opener if opener is not None else build_opener(NoRedirect())
    collected, login = {}, None
    cursor = start
    # Small queries avoid resource-heavy full-year calendars and limit retries.
    while cursor <= end:
        chunk_end = min(cursor+timedelta(days=89), end)
        # Today's count is a snapshot at fetch time; never query a future time.
        until = (now.strftime('%Y-%m-%dT%H:%M:%SZ') if chunk_end == today
                 else chunk_end.isoformat()+'T23:59:59Z')
        body = _request({'login': username, 'from': cursor.isoformat()+'T00:00:00Z',
                         'to': until}, token, opener, sleeper)
        try:
            user = body['data']['user']
            if user is None:
                raise GitHubError(f'GitHub user {username} was not found')
            canonical = user['login']
            if not isinstance(canonical, str) or canonical.lower() != username.lower():
                raise ValueError()
            if login is not None and canonical.lower() != login.lower():
                raise ValueError()
            login = canonical
            chunk = {}
            for week in user['contributionsCollection']['contributionCalendar']['weeks']:
                for day in week['contributionDays']:
                    when = date.fromisoformat(day['date'])
                    count = day['contributionCount']
                    if type(count) is not int or count < 0:
                        raise ValueError()
                    if cursor <= when <= chunk_end:
                        if when in chunk:
                            raise ValueError()
                        chunk[when] = count
            expected = {cursor+timedelta(days=i) for i in range((chunk_end-cursor).days+1)}
            if set(chunk) != expected:
                raise GitHubError('GitHub returned an incomplete calendar; missing days were not treated as zero')
            collected.update(chunk)
        except (KeyError, TypeError, ValueError, AttributeError):
            raise GitHubError('GitHub returned an unexpected calendar response') from None
        cursor = chunk_end+timedelta(days=1)
    return {'username': login, 'source': 'GitHub GraphQL contributionCalendar',
            'window': {'from': start.isoformat(), 'to': end.isoformat(), 'timezone': 'UTC',
                       'days': days, 'includes_today': end == today},
            'visibility': 'Counts visible to the supplied token; private data depends on permissions and profile settings',
            'days': [{'date': day.isoformat(), 'count': collected[day]} for day in sorted(collected)]}


def save_snapshot(snapshot, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name+'.tmp')
    try:
        temporary.write_text(json.dumps(snapshot, indent=2)+'\n', encoding='utf-8')
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
