"""Composite Action adapter: action code stays separate from the caller workspace."""
from datetime import date
import filecmp
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile
from taiko.action_options import parse_outputs
from taiko.chart import load_chart
from taiko.contributions import generate, Rules
from taiko.export import export_animation
from taiko.github import fetch_contributions, save_snapshot, GitHubError
from taiko.publish import publish_file, PublishError
from taiko.renderer import make_frame_renderer
from taiko.spacing import auto_scroll_speed
from taiko.svg import export_svg


def workspace_path(value, workspace):
    if any(c in value for c in '\r\n'):
        raise ValueError('Workspace paths cannot contain line breaks')
    path = (workspace/Path(value)).resolve()
    if not path.is_relative_to(workspace):
        raise ValueError('Input and output paths must stay inside GITHUB_WORKSPACE')
    return path


def boolean(value):
    if value.lower() not in ('true', 'false'):
        raise ValueError('Boolean inputs must be true or false')
    return value.lower() == 'true'


def run(environment=None):
    env = dict(os.environ if environment is None else environment)
    def setting(key, default=''):
        return env.get('TAIKO_'+key, '') or default
    workspace = Path(env.get('GITHUB_WORKSPACE', os.getcwd())).resolve()
    kind = setting('FORMAT', 'svg')
    if kind not in ('svg', 'gif'):
        raise ValueError('Expected format svg/gif')
    defaults = {key: setting(key.upper().replace('-', '_'), value) for key, value in {
        'background': 'festival', 'variant': 'full', 'auto-spacing': 'true',
        'speed': '190', 'note-gap': '0', 'fps': '30', 'colors': '96'}.items()}
    multiple = bool(setting('OUTPUTS'))
    specs = parse_outputs(setting('OUTPUTS') if multiple else setting('OUTPUT', 'dist/taiko.'+kind),
                          defaults, lambda value: workspace_path(value, workspace))
    if not multiple and specs[0][1] != kind:
        raise ValueError('Output extension must match format')
    publish = boolean(setting('PUBLISH', 'false'))
    if multiple and publish:
        raise ValueError('Use an external publishing step with outputs; publish supports legacy single output only')
    chart_input, snapshot_input = setting('CHART'), setting('SNAPSHOT')
    if chart_input and snapshot_input:
        raise ValueError('Choose chart or snapshot, not both')
    bpm = int(setting('BPM', '120'))
    if not 30 <= bpm <= 300:
        raise ValueError('BPM out of range')
    temp_root = Path(env.get('RUNNER_TEMP', str(workspace/'.taiko-cache'))).resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='tiny-taiko-', dir=temp_root))
    snapshot_path = None
    if chart_input:
        chart_path = workspace_path(chart_input, workspace)
    else:
        if snapshot_input:
            snapshot_path = workspace_path(snapshot_input, workspace)
            snapshot = json.loads(snapshot_path.read_text(encoding='utf-8'))
        else:
            username = setting('USERNAME', env.get('GITHUB_REPOSITORY_OWNER', ''))
            end = date.fromisoformat(setting('END_DATE')) if setting('END_DATE') else None
            snapshot = fetch_contributions(username, int(setting('DAYS', '365')), end,
                                           token=setting('TOKEN') or env.get('GH_TOKEN') or env.get('GITHUB_TOKEN') or None)
            snapshot_path = temporary/'snapshot.json'
            save_snapshot(snapshot, snapshot_path)
        chart_path, _ = generate(snapshot, temporary, Rules(bpm=bpm, seed=setting('SEED', 'default')))
    for output, _, _ in specs:
        if output in (chart_path, snapshot_path, chart_path.with_suffix('.meta.json')):
            raise ValueError('Output cannot overwrite source input')
    source_chart = load_chart(chart_path)
    rendered = []
    for index, (output, kind, options) in enumerate(specs):
        chart = dict(source_chart)
        chart['speed'] = (auto_scroll_speed(chart, options['note-gap'])
                          if options['auto-spacing'] else options['speed'])
        result = temporary/(str(index)+'.'+kind)
        if kind == 'svg':
            export_svg(chart, result, options['background'], variant=options['variant'])
        else:
            export_animation(chart, make_frame_renderer(chart, options['variant'], options['background']),
                             result, fps=options['fps'], colors=options['colors'])
        rendered.append((output, result))
    # Finish all renders before replacing any existing caller files.
    for output, result in rendered:
        output.parent.mkdir(parents=True, exist_ok=True)
        if not output.exists() or not filecmp.cmp(output, result, shallow=False):
            staging = output.with_name(output.name+'.tmp')
            try:
                shutil.copyfile(result, staging)
                staging.replace(output)
            finally:
                staging.unlink(missing_ok=True)
    output, kind, _ = specs[0]
    published = False
    if publish:
        published = publish_file(output, workspace, temp_root,
                                 setting('OUTPUT_BRANCH', 'output'), setting('OUTPUT_NAME', 'taiko.'+kind))
    metadata = chart_path.with_suffix('.meta.json')
    outputs = {'file': str(output), 'files': json.dumps([str(p) for p, _ in rendered]), 'chart': str(chart_path),
               'metadata': str(metadata) if metadata.exists() else '',
               'snapshot': str(snapshot_path) if snapshot_path else '',
               'size-bytes': str(output.stat().st_size),
               'duration-seconds': format(chart['beats']*60/chart['bpm'], '.8g'),
               'published': str(published).lower()}
    if env.get('GITHUB_OUTPUT'):
        with Path(env['GITHUB_OUTPUT']).open('a', encoding='utf-8') as stream:
            for key, value in outputs.items():
                if any(c in value for c in '\r\n'):
                    raise ValueError('Invalid Action output value')
                stream.write(f'{key}={value}\n')
    print(f'Taiko: {output} ({output.stat().st_size/1024:.1f} KiB); published={published}')
    return outputs


if __name__ == '__main__':
    try:
        run()
    except (GitHubError, PublishError, ValueError, OSError) as error:
        print(f'Error: {error}', file=sys.stderr)
        raise SystemExit(1) from None
