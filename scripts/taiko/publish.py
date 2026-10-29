"""Publish one generated file through the caller's authenticated Git checkout."""
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tempfile


class PublishError(RuntimeError):
    pass


def git(workspace, *arguments, check=True, env=None):
    result = subprocess.run(['git', '-C', str(workspace), *arguments], capture_output=True,
                            text=True, env=env)
    if check and result.returncode:
        # Do not echo remote URLs, headers or credential-bearing diagnostics.
        raise PublishError(f'git {arguments[0]} failed (exit {result.returncode}); check checkout credentials, branch protection and contents: write')
    return result


def publish_file(source, workspace, runner_temp, branch='output', filename='taiko.svg'):
    workspace, runner_temp = Path(workspace).resolve(), Path(runner_temp).resolve()
    if branch in ('main', 'master'):
        raise PublishError('Use a dedicated output branch, not main/master')
    if git(workspace, 'check-ref-format', '--branch', branch, check=False).returncode:
        raise PublishError('Invalid output branch name')
    current = git(workspace, 'symbolic-ref', '--short', 'HEAD', check=False).stdout.strip()
    if branch == current:
        raise PublishError('Output branch must differ from the caller checkout branch')
    name = PurePosixPath(filename)
    if (not filename or not name.parts or '\\' in filename or name.is_absolute() or '..' in name.parts or
            any(part.lower() == '.git' for part in name.parts) or any(c in filename for c in '\r\n')):
        raise PublishError('output-name must be a relative path on the output branch')
    top = Path(git(workspace, 'rev-parse', '--show-toplevel').stdout.strip()).resolve()
    if top != workspace:
        raise PublishError('Checkout the caller repository at GITHUB_WORKSPACE before publishing')
    reference = git(workspace, 'ls-remote', '--exit-code', '--heads', 'origin', f'refs/heads/{branch}', check=False)
    if reference.returncode not in (0, 2):
        raise PublishError('Cannot read origin; previous output was not replaced')
    old = None
    if reference.returncode == 0:
        git(workspace, 'fetch', '--no-tags', 'origin', f'refs/heads/{branch}')
        old = git(workspace, 'rev-parse', 'FETCH_HEAD').stdout.strip()
    runner_temp.mkdir(parents=True, exist_ok=True)
    worktree = Path(tempfile.mkdtemp(prefix='tiny-taiko-publish-', dir=runner_temp)).resolve()
    registered = False
    try:
        git(workspace, 'worktree', 'add', '--detach', str(worktree), old or 'HEAD')
        registered = True
        if old is None:
            # Empty only this temporary worktree's index. No caller files are removed.
            git(worktree, 'read-tree', '--empty')
        destination = (worktree/filename).resolve()
        if not destination.is_relative_to(worktree):
            raise PublishError('Output destination escapes its temporary worktree')
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        git(worktree, 'add', '-f', '--', filename)
        tree = git(worktree, 'write-tree').stdout.strip()
        if old and tree == git(workspace, 'rev-parse', old+'^{tree}').stdout.strip():
            return False
        identity = dict(os.environ, GIT_AUTHOR_NAME='github-actions[bot]',
                        GIT_COMMITTER_NAME='github-actions[bot]',
                        GIT_AUTHOR_EMAIL='41898282+github-actions[bot]@users.noreply.github.com',
                        GIT_COMMITTER_EMAIL='41898282+github-actions[bot]@users.noreply.github.com')
        arguments = ['commit-tree', tree]
        if old:
            arguments += ['-p', old]
        commit = git(worktree, *arguments, '-m', 'Update Taiko animation', env=identity).stdout.strip()
        # Push from the original checkout so checkout@v6 authentication remains in scope.
        # No force push: a concurrent remote update fails rather than discarding changes.
        git(workspace, 'push', 'origin', f'{commit}:refs/heads/{branch}')
        return True
    finally:
        if not worktree.is_relative_to(runner_temp) or not worktree.name.startswith('tiny-taiko-publish-'):
            raise PublishError('Invalid temporary worktree cleanup path')
        if registered:
            git(workspace, 'worktree', 'remove', '--force', str(worktree), check=False)
        elif worktree.exists():
            worktree.rmdir()
