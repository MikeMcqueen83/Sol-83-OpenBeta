"""Stage 1 (audit fixes): sandboxed execution of repository code, secret scanning, portability.

Unit-level and fast. The sandbox tests use the real OS sandbox of this machine (Seatbelt on
macOS, bubblewrap on Linux) and are skipped where there is none.
"""
import importlib.machinery
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMP = pathlib.Path(tempfile.mkdtemp(prefix='sol83-sec-'))
# Keep the data folder of a test module imported earlier: engines it starts read the same store.
os.environ.setdefault('GEMINI_HOME', str(TEMP))
os.environ['GEMINI_NOTIFY'] = '0'
sys.path.insert(0, str(ROOT))

from gemini_app import github, gitops, monitor, sandbox, secretscan  # noqa: E402
from gemini_app.gitops import Git  # noqa: E402
from gemini_app.store import Store  # noqa: E402

HAS_SANDBOX = sandbox.backend() is not None


def load_script(name):
    loader = importlib.machinery.SourceFileLoader(name.replace('/', '_'), str(ROOT / name))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def tearDownModule():
    shutil.rmtree(TEMP, ignore_errors=True)


def make_repo(files: dict, history: dict = None) -> pathlib.Path:
    repo = pathlib.Path(tempfile.mkdtemp(dir=TEMP))
    gitops.create_repo(repo)
    git = Git(repo)
    for content in (history or {}), files:
        for name, text in content.items():
            (repo / name).parent.mkdir(parents=True, exist_ok=True)
            (repo / name).write_text(text)
        if content:
            git.run('add', '-A')
            git.run(*gitops.IDENTITY, 'commit', '-q', '-m', 'x')
            for name in content:
                if name not in files:
                    (repo / name).unlink()
    if history:
        git.run('add', '-A')
        git.run(*gitops.IDENTITY, 'commit', '-q', '-m', 'remove', check=False)
    return repo


class SecretPatterns(unittest.TestCase):
    CASES = {
        'openai_project': 'OPENAI=sk-proj-AbCdEfGhIjKlMnOpQrStUvWx_1234',
        'stripe_live': 'key = sk_live_51HabcdefghijklmnOP',
        'slack_bot': 'xoxb-123456789012-abcdefghij',
        'github_oauth': 'gho_abcdefghijklmnopqrstuvwxyz0123456789',
        'gitlab': 'glpat-abcdefghijklmnopqrst',
        'password_assignment': 'password = "hunter2test"',
        'npmrc': '//registry.npmjs.org/:_authToken=npm_abcdefghijklmnop',
        'url_credentials': 'git clone https://bob:s3cretpass@example.com/repo.git',
        'google_oauth': 'ya29.a0AfB_byCabcdefghijklmnop',
        'private_key': '-----BEGIN OPENSSH PRIVATE KEY-----',
    }

    def test_audit_gaps_are_detected_and_redacted(self):
        for name, text in self.CASES.items():
            with self.subTest(name):
                self.assertTrue(secretscan.has_secret(text), text)
                self.assertNotIn(text.split('=')[-1].strip(' "'), secretscan.redact(text))

    def test_ordinary_text_is_left_alone(self):
        for text in ('password = os.environ["PW"]', 'the api key is read from the keychain',
                     'skip-worktree', 'sk-short'):
            self.assertFalse(secretscan.has_secret(text), text)
            self.assertEqual(secretscan.redact(text), text)

    def test_secret_files(self):
        for path in ('.npmrc', 'deploy/.pypirc', 'keys/server.key', 'gcp/service-account-prod.json', '.env.local'):
            self.assertTrue(secretscan.secret_file(path), path)
        for path in ('.env.example', 'src/keyboard.py', 'README.md'):
            self.assertFalse(secretscan.secret_file(path), path)


class PushScan(unittest.TestCase):
    def test_finds_token_in_tree_assignment_and_history(self):
        repo = make_repo({'app.py': 'password = "hunter2test"\n', 'ok.txt': 'nothing\n'},
                         history={'old.txt': 'token sk-proj-AbCdEfGhIjKlMnOpQrStUvWx_1234\n'})
        git = Git(repo)
        found = github.find_secrets(git, git.head())
        self.assertIn('app.py', found)
        # A secret removed later is still in the history that a push sends.
        self.assertTrue(any(item.startswith('commit ') for item in found), found)
        self.assertNotIn('ok.txt', found)

    def test_push_needs_confirmation_of_the_exact_findings(self):
        repo = make_repo({'.npmrc': '//r/:_authToken=abcdefghijkl\n'})
        git = Git(repo)
        with self.assertRaises(github.SecretsFound) as caught:
            github.check_secrets(git, git.head())
        token = caught.exception.token
        self.assertEqual(github.check_secrets(git, git.head(), token), ['.npmrc'])
        with self.assertRaises(github.SecretsFound):
            github.check_secrets(git, git.head(), 'other')

    def test_clean_repository_passes(self):
        repo = make_repo({'main.py': 'print(1)\n'})
        self.assertEqual(github.check_secrets(Git(repo), Git(repo).head()), [])

    def test_no_hardcoded_homebrew_path(self):
        with mock.patch('os.path.isdir', return_value=False), mock.patch.object(github, 'agent_path', return_value='/x'):
            self.assertEqual(github._path(), '/x')


@unittest.skipUnless(HAS_SANDBOX, 'no OS sandbox on this machine')
class Sandbox(unittest.TestCase):
    def setUp(self):
        self.work = pathlib.Path(tempfile.mkdtemp(dir=TEMP))
        self.outside = pathlib.Path(tempfile.mkdtemp(dir=TEMP))

    def test_writes_only_inside_the_project(self):
        target = self.outside / 'escape.txt'
        result = sandbox.run_shell(f'echo in > inside.txt; echo out > "{target}"', self.work)
        self.assertTrue((self.work / 'inside.txt').exists())
        self.assertFalse(target.exists())
        self.assertNotEqual(result.returncode, sandbox.REFUSED_EXIT)

    def test_credentials_are_not_readable(self):
        fake_home = pathlib.Path(tempfile.mkdtemp(dir=TEMP))
        (fake_home / '.ssh').mkdir()
        (fake_home / '.ssh/id_ed25519').write_text('secret-key-material')
        with mock.patch.object(sandbox, 'HOME', fake_home):
            result = sandbox.run_shell(f'cat "{fake_home}/.ssh/id_ed25519" || echo blocked', self.work)
        self.assertNotIn('secret-key-material', result.output)
        self.assertIn('blocked', result.output)

    def test_no_network_unless_asked(self):
        code = ('import socket\ntry:\n socket.create_connection(("1.1.1.1", 53), timeout=3)\n print("net")\n'
                'except OSError:\n print("blocked")\n')
        (self.work / 'net.py').write_text(code)
        result = sandbox.run([sys.executable, 'net.py'], self.work)
        self.assertIn('blocked', result.output)

    def test_output_is_redacted(self):
        result = sandbox.run_shell('echo sk-ant-abcdefghijklmnopqrstuvwx', self.work)
        self.assertNotIn('sk-ant-abc', result.output)

    def test_timeout(self):
        result = sandbox.run_shell('sleep 5', self.work, timeout=0.5)
        self.assertEqual(result.returncode, sandbox.TIMEOUT_EXIT)


class NoSandbox(unittest.TestCase):
    def test_refuses_without_explicit_permission(self):
        work = pathlib.Path(tempfile.mkdtemp(dir=TEMP))
        with mock.patch.dict(os.environ, {'SOL83_SANDBOX': 'off'}):
            refused = sandbox.run_shell('touch ran.txt', work)
            self.assertEqual(refused.returncode, sandbox.REFUSED_EXIT)
            self.assertFalse((work / 'ran.txt').exists())
            allowed = sandbox.run_shell('touch ran.txt', work, allow_unsandboxed=True)
            self.assertEqual(allowed.returncode, 0)

    def test_bwrap_arguments(self):
        work = pathlib.Path(tempfile.mkdtemp(dir=TEMP))
        args = sandbox.bwrap_args([work], [work / 'missing'], network=False)
        self.assertIn('--unshare-net', args)
        self.assertEqual(args[args.index('--bind') + 1], str(work))


@unittest.skipUnless(HAS_SANDBOX, 'no OS sandbox on this machine')
class SetupScript(unittest.TestCase):
    def setUp(self):
        self.repo = make_repo({gitops.SETUP_FILE: '#!/bin/sh\ntouch setup-ran\n'})
        os.chmod(self.repo / gitops.SETUP_FILE, 0o755)

    def test_runs_only_after_approval_of_this_content(self):
        work = pathlib.Path(tempfile.mkdtemp(dir=TEMP)) / 'wt'
        gitops.add_worktree(str(self.repo), work, 'sol83/test')
        self.assertFalse((work / 'setup-ran').exists(), 'setup must not run on worktree creation')
        self.assertEqual(gitops.run_setup(work, None), 'needs_approval')
        sha = gitops.setup_script(work)['sha']
        self.assertEqual(gitops.run_setup(work, sha), 'ran')
        self.assertTrue((work / 'setup-ran').exists())
        (work / gitops.SETUP_FILE).write_text('#!/bin/sh\ncurl evil\n')
        self.assertEqual(gitops.run_setup(work, sha), 'needs_approval')


class VerifyWrapper(unittest.TestCase):
    def test_duet_never_gets_the_raw_command(self):
        command = sandbox.verify_command()
        self.assertIn('gemini_app.sandbox verify', command)

    def test_refuses_outside_the_project_worktree(self):
        store = Store()
        work = pathlib.Path(tempfile.mkdtemp(dir=TEMP))
        store.add_project(id='p1', title='t', task='t', status='running', worktree=str(work),
                          verify_cmd='touch ran.txt')
        elsewhere = pathlib.Path(tempfile.mkdtemp(dir=TEMP))
        from gemini_app import paths
        # The store this process uses, whichever test module imported gemini_app first.
        env = {**os.environ, 'GEMINI_PROJECT_ID': 'p1', 'PYTHONPATH': str(ROOT), 'GEMINI_HOME': str(paths.HOME)}
        done = subprocess.run([sys.executable, '-m', 'gemini_app.sandbox', 'verify'], cwd=elsewhere,
                              env=env, capture_output=True, text=True)
        self.assertEqual(done.returncode, sandbox.REFUSED_EXIT)
        self.assertFalse((elsewhere / 'ran.txt').exists())
        if HAS_SANDBOX:
            done = subprocess.run([sys.executable, '-m', 'gemini_app.sandbox', 'verify'], cwd=work,
                                  env=env, capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            self.assertTrue((work / 'ran.txt').exists())


class Portability(unittest.TestCase):
    def test_notify_without_osascript_is_silent(self):
        with mock.patch.dict(os.environ, {'GEMINI_NOTIFY': '1'}), \
                mock.patch.object(monitor.sys, 'platform', 'linux'), \
                mock.patch.object(monitor.shutil, 'which', return_value=None):
            monitor.notify('hello')
        with mock.patch.dict(os.environ, {'GEMINI_NOTIFY': '1'}), \
                mock.patch.object(monitor.subprocess, 'run', side_effect=FileNotFoundError('osascript')):
            monitor.notify('hello')

    def test_gemini_skips_permissions_only_inside_the_os_sandbox(self):
        adapter = load_script('bin/gemini')
        plain = adapter.command('agy', {'-p': 'x'}, [], sandboxed=False)
        self.assertNotIn('--dangerously-skip-permissions', plain)
        self.assertIn('--sandbox', plain)
        self.assertIn('--dangerously-skip-permissions', adapter.command('agy', {'-p': 'x'}, [], sandboxed=True))
        planning = adapter.command('agy', {'-p': 'x', '--approval-mode': 'plan'}, [], sandboxed=True)
        self.assertNotIn('--dangerously-skip-permissions', planning)

    def test_pseudo_terminal_arguments_per_platform(self):
        adapter = load_script('bin/gemini')
        with mock.patch.object(adapter.sys, 'platform', 'linux'):
            self.assertEqual(adapter.with_terminal(['agy', '-p', 'a b']), ['script', '-q', '-c', "agy -p 'a b'", '/dev/null'])
        with mock.patch.object(adapter.sys, 'platform', 'darwin'):
            self.assertEqual(adapter.with_terminal(['agy']), ['script', '-q', '/dev/null', 'agy'])

    def test_claude_found_on_path(self):
        adapter = load_script('bin/claude')
        folder = pathlib.Path(tempfile.mkdtemp(dir=TEMP))
        (folder / 'claude').write_text('#!/bin/sh\n')
        os.chmod(folder / 'claude', 0o755)
        env = {key: value for key, value in os.environ.items() if key != 'GEMINI_CLAUDE_BIN'}
        env['PATH'] = f'{ROOT / "bin"}{os.pathsep}{folder}'
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(adapter.find_binary(), str(folder / 'claude'))

    def test_legacy_commands_are_gone(self):
        done = subprocess.run([sys.executable, str(ROOT / 'sol83'), 'start', 'x', 'y'], capture_output=True, text=True)
        self.assertNotEqual(done.returncode, 0)
        self.assertIn('invalid choice', done.stderr)


class EngineEnvironment(unittest.TestCase):
    def test_api_keys_never_reach_the_agents(self):
        from gemini_app.supervisor import Supervisor
        with mock.patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'x', 'OPENAI_API_KEY': 'y', 'GEMINI_API_KEY': 'z'}):
            env = Supervisor(Store())._engine_env('p')
        self.assertFalse({'ANTHROPIC_API_KEY', 'OPENAI_API_KEY', 'GEMINI_API_KEY'} & set(env))

    def test_events_are_redacted(self):
        store = Store()
        store.add_project(id='p2', title='t', task='t', status='queued')
        store.event('p2', 'turn_end', 'zrobione', body='export OPENAI_API_KEY=sk-proj-AbCdEfGhIjKlMnOpQrStUv_99')
        event = store.events('p2')[0]
        self.assertNotIn('sk-proj-', store.event_body('p2', event['id']))


if __name__ == '__main__':
    unittest.main()
