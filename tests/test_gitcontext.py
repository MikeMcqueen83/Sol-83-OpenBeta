"""Spec point 22 on temporary repositories and a local bare remote (not a test of GitHub's API)."""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMP = pathlib.Path(tempfile.mkdtemp(prefix='sol83-git-')).resolve()
os.environ.setdefault('GEMINI_HOME', str(TEMP))
sys.path.insert(0, str(ROOT))

from gemini_app import gitcontext  # noqa: E402
from gemini_app.gitcontext import GitContextError, GitOps  # noqa: E402
from gemini_app.store import Store  # noqa: E402


def tearDownModule():
    shutil.rmtree(TEMP, ignore_errors=True)


def git(repo, *args):
    return subprocess.run(['git', *args], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()


def make(name, remote=None):
    repo = TEMP / name
    repo.mkdir(parents=True)
    git(repo, 'init', '-q', '-b', 'trunk')
    git(repo, 'config', 'user.name', 'Tester')
    git(repo, 'config', 'user.email', 't@example.com')
    (repo / 'README.md').write_text('# x\n')
    (repo / 'app.py').write_text('print(1)\n')
    git(repo, 'add', '-A')
    git(repo, 'commit', '-q', '-m', 'start')
    if remote:
        git(repo, 'remote', 'add', 'upstream', str(remote))
        git(repo, 'push', '-q', 'upstream', 'trunk')
    return repo


class GitContext(unittest.TestCase):
    def setUp(self):
        self.store = Store(TEMP / f'{self.id()}.db')
        self.ops = GitOps(self.store)
        self.tmp = pathlib.Path(tempfile.mkdtemp(dir=TEMP))
        self.remote = self.tmp / 'remote.git'
        git(self.tmp, 'init', '-q', '--bare', str(self.remote))
        self.repo = make(self.tmp.name + '/projekt-a', self.remote)
        self.similar = make(self.tmp.name + '/projekt-a2')

    def test_intents(self):
        cases = {'Popraw README': 'edit', 'Zapisz te zmiany w Git': 'commit', 'zrób commit': 'commit',
                 'Wyślij dokumentację na GitHub': 'push', 'Zaktualizuj na Git dokumentację': 'update',
                 'Pobierz najnowszą wersję': 'pull', 'open a pull request': 'pr'}
        for text, intent in cases.items():
            self.assertEqual(gitcontext.classify(text), intent, text)

    def test_state_custom_remote_branch_subdir_and_detached(self):
        (self.repo / 'pkg').mkdir()
        state = gitcontext.inspect(self.repo / 'pkg')
        self.assertEqual((state['branch'], state['subdir'], list(state['remotes'])), ('trunk', 'pkg', ['upstream']))
        git(self.repo, 'checkout', '-q', '--detach')
        self.assertTrue(gitcontext.inspect(self.repo)['detached'])

    def test_commit_only_the_listed_docs_and_keep_user_changes(self):
        (self.repo / 'app.py').write_text('print(2)\n')          # user's unstaged change
        (self.repo / 'notes.txt').write_text('mine')             # user's new file
        git(self.repo, 'add', 'notes.txt')                       # user's staged change
        (self.repo / 'README.md').write_text('# x\nDocs\n')      # the requested change
        (self.repo / 'docs').mkdir()
        (self.repo / 'docs/guide.md').write_text('guide')
        result = self.ops.commit('p', self.repo, ['README.md', 'docs/guide.md'], 'Docs', 'op-1')
        self.assertEqual(result['state'], 'committed')
        files = git(self.repo, 'show', '--name-only', '--format=', 'HEAD').split()
        self.assertEqual(sorted(files), ['README.md', 'docs/guide.md'])
        status = subprocess.run(['git', 'status', '--porcelain'], cwd=self.repo, capture_output=True, text=True).stdout
        self.assertIn('A  notes.txt', status, 'the user\'s staged file stays staged and uncommitted')
        self.assertIn(' M app.py', status, 'the user\'s unstaged change stays')
        again = self.ops.commit('p', self.repo, ['README.md', 'docs/guide.md'], 'Docs', 'op-1')
        self.assertEqual(again['commit_sha'], result['commit_sha'], 'same request after a restart: no second commit')
        self.assertEqual(git(self.repo, 'rev-list', '--count', 'HEAD'), '2')

    def test_push_no_remote_rejected_and_lost_answer(self):
        with self.assertRaises(GitContextError):
            self.ops.push('p', self.similar, 'origin', 'trunk', 'x')
        (self.repo / 'README.md').write_text('local\n')
        self.ops.commit('p', self.repo, ['README.md'], 'local', 'c1')
        other = TEMP / (self.tmp.name + '/clone')
        git(self.tmp, 'clone', '-q', '-b', 'trunk', str(self.remote), str(other))
        git(other, 'config', 'user.email', 'o@example.com'); git(other, 'config', 'user.name', 'O')
        (other / 'app.py').write_text('remote\n'); git(other, 'commit', '-qam', 'remote ahead'); git(other, 'push', '-q')
        rejected = self.ops.push('p', self.repo, 'upstream', 'trunk', 'push-1')
        self.assertEqual(rejected['state'], 'failed_remote_ahead')
        self.assertIn('istnieje lokalnie', rejected['detail'])
        git(self.repo, 'fetch', '-q', 'upstream')
        with self.assertRaises(GitContextError):
            self.ops.integrate(self.repo, 'upstream/trunk')     # diverged: needs a decision, nothing changed
        fresh = make(self.tmp.name + '/projekt-b', None)
        git(fresh, 'remote', 'add', 'upstream', str(self.remote))
        git(fresh, 'fetch', '-q', 'upstream'); git(fresh, 'checkout', '-q', '-B', 'feature', 'upstream/trunk')
        (fresh / 'README.md').write_text('feature\n')
        self.ops.commit('p', fresh, ['README.md'], 'feature', 'c2')
        pushed = self.ops.push('p', fresh, 'upstream', 'feature', 'push-2')
        self.assertEqual(pushed['state'], 'pushed')
        self.store._rows("DELETE FROM git_ops WHERE op_key='push-2'")
        with self.store._db() as db:
            db.execute("DELETE FROM git_ops WHERE op_key='push-2'")
        again = self.ops.push('p', fresh, 'upstream', 'feature', 'push-2')
        self.assertIn('już wskazuje', again['detail'], 'the remote is checked before repeating')

    def test_dirty_folder_blocks_integration_and_missing_identity(self):
        (self.repo / 'app.py').write_text('dirty\n')
        with self.assertRaises(GitContextError):
            self.ops.integrate(self.repo, 'upstream/trunk')
        git(self.similar, 'config', '--unset', 'user.email')
        (self.similar / 'README.md').write_text('y\n')
        env = {**os.environ, 'GIT_CONFIG_GLOBAL': '/dev/null', 'HOME': str(self.tmp)}
        old = dict(os.environ)
        os.environ.update(env)
        try:
            with self.assertRaises(GitContextError):
                self.ops.commit('p', self.similar, ['README.md'], 'x', 'c3')
        finally:
            os.environ.clear(); os.environ.update(old)

    def test_sol83_repository_is_never_a_target(self):
        with self.assertRaises(GitContextError):
            self.ops.commit('p', ROOT, ['README.md'], 'x', 'never')

    def test_concurrent_commits_are_serialized(self):
        for name in ('a.md', 'b.md', 'c.md', 'd.md'):
            (self.repo / name).write_text(name)
        errors = []

        def work(name):
            try:
                self.ops.commit('p', self.repo, [name], f'add {name}', f'k-{name}')
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)
        threads = [threading.Thread(target=work, args=(n,)) for n in ('a.md', 'b.md', 'c.md', 'd.md')]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        self.assertEqual(git(self.repo, 'rev-list', '--count', 'HEAD'), '5')

    def test_credentials_never_in_records(self):
        self.assertEqual(gitcontext.safe_url('https://user:tok123@github.com/x/y.git'), 'https://github.com/x/y.git')


if __name__ == '__main__':
    unittest.main()
