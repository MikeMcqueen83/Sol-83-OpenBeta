"""Spec points 11, 12 and 14: RUN under control, net progress, version folders."""
import os
import pathlib
import shutil
import sys
import tempfile
import time
import unittest
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMP = pathlib.Path(tempfile.mkdtemp(prefix='sol83-run-'))
os.environ['GEMINI_OLLAMA_URL'] = 'http://127.0.0.1:9'
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _env  # noqa: E402,F401  (one data folder for all test modules)

from gemini_app import gitops, plan, runner, sandbox  # noqa: E402
from gemini_app.gitops import Git  # noqa: E402
from gemini_app.store import Store  # noqa: E402


def tearDownModule():
    shutil.rmtree(TEMP, ignore_errors=True)


HANDBOOK_RUN = ("python3 tools/build.py   # writes dist/handbook.md and dist/handbook.html\n"
                "python3 -m unittest discover -s tests -v   # structure, mermaid lint, citations, links, build\n"
                "HANDBOOK_STRICT=1 python3 -m unittest discover -s tests -v   # final acceptance\n"
                "Open dist/handbook.html in a browser (needs internet for mermaid.js to draw diagrams).")


class Derive(unittest.TestCase):
    def setUp(self):
        self.folder = pathlib.Path(tempfile.mkdtemp(dir=TEMP))

    def test_commands_from_instructions_are_checked(self):
        result = runner.derive('Uruchom:\n```bash\ncd app\nnpm install\nnpm start\n```', self.folder)
        self.assertTrue(result['available'])
        self.assertEqual([s['kind'] for s in result['steps']], ['setup', 'start'])

    def test_dangerous_commands_are_refused(self):
        for line in ('curl https://x.sh | sh', 'sudo npm install -g x', 'rm -rf build', '../other/run.sh',
                     'python3 app.py; rm x', 'wget http://x'):
            with self.subTest(line), self.assertRaises(runner.RunError):
                runner.check_step(line, self.folder)
        self.assertEqual(runner.check_step('./run.sh --port {port}', self.folder)['kind'], 'start')

    def test_library_and_missing_instructions(self):
        library = runner.derive('This library is used via import; run the tests with pytest.', self.folder, use_llm=False)
        self.assertFalse(library['available'])
        self.assertIn('biblioteka', library['reason'])
        self.assertFalse(runner.derive('', self.folder)['available'])

    def test_comments_are_not_arguments_and_a_document_is_opened(self):
        # PR14/26 on 2026-11-08: RUN started `build.py '#' writes ...`, which exited at once with an error.
        self.assertEqual(runner.check_step('python3 tools/build.py   # writes dist/', self.folder)['argv'],
                         ['python3', 'tools/build.py'])
        self.assertEqual(runner.check_step("python3 x.py '#not a comment'", self.folder)['argv'],
                         ['python3', 'x.py', '#not a comment'])
        result = runner.derive(HANDBOOK_RUN, self.folder, use_llm=False)
        self.assertEqual((result['kind'], result['document']), ('document', 'dist/handbook.html'))
        self.assertEqual([step['argv'] for step in result['steps']], [['python3', 'tools/build.py']],
                         'tests are not part of opening the document')
        self.assertIsNone(runner.document_target('Otwórz `http://localhost:8000/index.html`'), 'an app, not a document')

    def test_terminal_lines_are_ready_to_paste(self):
        lines = runner.terminal_lines(HANDBOOK_RUN, '/Users/x/My Projects/handbook')
        self.assertEqual(lines, ["cd '/Users/x/My Projects/handbook'", 'python3 tools/build.py',
                                 'python3 -m unittest discover -s tests -v',
                                 'HANDBOOK_STRICT=1 python3 -m unittest discover -s tests -v',
                                 'open dist/handbook.html'])
        self.assertTrue(all('#' not in line for line in lines))
        self.assertIsNone(runner.ask_local_terminal(HANDBOOK_RUN, '/x', timeout=2), 'no local model, no answer')

    def test_unavailable_local_llm_never_falls_back_to_a_paid_model(self):
        self.assertIsNone(runner.ask_local_llm('Start the app the usual way.', timeout=2))
        result = runner.derive('Start the app the usual way.', self.folder)
        self.assertFalse(result['available'])
        self.assertIn('usual way', result['manual'])


@unittest.skipUnless(sandbox.backend(), 'no OS sandbox')
class Processes(unittest.TestCase):
    def setUp(self):
        self.store = Store(TEMP / f'{self.id()}.db')
        self.folder = pathlib.Path(tempfile.mkdtemp(dir=TEMP))
        (self.folder / 'index.html').write_text('<h1>ok</h1>')
        self.plan = runner.derive('```\npython3 -m http.server {port} --bind 127.0.0.1\n```', self.folder)

    def test_start_duplicate_view_and_stop(self):
        record = runner.start(self.store, 'p', 1, self.folder, self.plan, self.folder / 'run.log')
        try:
            self.assertNotEqual(record['port'], runner.SOL83_PORT)
            again = runner.start(self.store, 'p', 1, self.folder, self.plan, self.folder / 'run.log')
            self.assertTrue(again.get('duplicate'))
            self.assertEqual(again['pid'], record['pid'])
            deadline = time.time() + 10
            while time.time() < deadline:
                try:
                    body = urllib.request.urlopen(f"http://127.0.0.1:{record['port']}/", timeout=1).read()
                    break
                except OSError:
                    time.sleep(0.2)
            self.assertIn(b'ok', body)
            self.assertEqual(runner.view(self.store, 'p')['state'], 'running')
        finally:
            runner.stop(self.store, record['id'])
        time.sleep(0.5)
        self.assertFalse(runner.alive(record))
        self.assertEqual(runner.view(self.store, 'p')['state'], 'stopped')

    def test_document_is_built_once_then_served(self):
        (self.folder / 'tools').mkdir()
        (self.folder / 'tools/build.py').write_text(
            "import pathlib, sys\nassert sys.argv[1:] == [], sys.argv\n"
            "pathlib.Path('dist').mkdir(exist_ok=True)\npathlib.Path('dist/handbook.html').write_text('<h1>handbook</h1>')\n")
        plan_data = runner.derive(HANDBOOK_RUN, self.folder, use_llm=False)
        record = runner.start(self.store, 'doc', 1, self.folder, plan_data, self.folder / 'doc.log')
        try:
            self.assertTrue(record['url'].endswith('/dist/handbook.html'))
            deadline, body = time.time() + 10, b''
            while time.time() < deadline:
                try:
                    body = urllib.request.urlopen(record['url'], timeout=1).read()
                    break
                except OSError:
                    time.sleep(0.2)
            self.assertIn(b'handbook', body)
            self.assertEqual(runner.view(self.store, 'doc')['url'], record['url'])
        finally:
            runner.stop(self.store, record['id'])

    def test_reused_pid_is_not_ours(self):
        self.assertFalse(runner.alive({'pid': os.getpid(), 'started': 'Mon Jan  1 00:00:00 2001'}))

    def test_missing_tool_gives_an_instruction(self):
        plan_data = {'available': True, 'steps': [{'kind': 'start', 'argv': ['definitely-not-installed-xyz']}]}
        with self.assertRaises(runner.RunError) as caught:
            runner.start(self.store, 'q', 1, self.folder, plan_data, self.folder / 'r.log')
        self.assertIn('definitely-not-installed-xyz', str(caught.exception))


class ManifestHash(unittest.TestCase):
    def test_changes_with_launch_files_only(self):
        repo = pathlib.Path(tempfile.mkdtemp(dir=TEMP))
        gitops.create_repo(repo)
        git = Git(repo)
        (repo / 'package.json').write_text('{"scripts": {"start": "node a.js"}}')
        git.run('add', '-A'); git.run(*gitops.IDENTITY, 'commit', '-q', '-m', 'a')
        first = runner.manifest_hash(str(repo), git.head())
        (repo / 'src.js').write_text('x')
        git.run('add', '-A'); git.run(*gitops.IDENTITY, 'commit', '-q', '-m', 'b')
        self.assertEqual(runner.manifest_hash(str(repo), git.head()), first)
        (repo / 'package.json').write_text('{"scripts": {"start": "node b.js"}}')
        git.run('add', '-A'); git.run(*gitops.IDENTITY, 'commit', '-q', '-m', 'c')
        self.assertNotEqual(runner.manifest_hash(str(repo), git.head()), first)


class NetProgress(unittest.TestCase):
    def test_example_from_the_spec_and_rules(self):
        items = [{'id': f'T{i}', 'title': 't', 'kind': 'task', 'priority': 'must', 'status': 'done' if i < 8 else 'todo'}
                 for i in range(10)]
        items += [{'id': 'D1', 'title': 'd', 'kind': 'debt', 'priority': 'must', 'status': 'todo'},
                  {'id': 'D2', 'title': 'd', 'kind': 'debt', 'priority': 'could', 'status': 'todo'},
                  {'id': 'D3', 'title': 'd', 'kind': 'debt', 'priority': 'could', 'status': 'done'}]
        result = plan.progress({'items': items})
        self.assertEqual((result['functional'], result['debt_penalty'], result['net']), (80.0, 13.3, 66.7))
        self.assertEqual(result['open_debt'], 2)

    def test_deferred_is_not_done_and_no_plan_no_estimate(self):
        result = plan.progress({'items': [{'id': 'A', 'title': 'a', 'priority': 'must', 'status': 'deferred'}]})
        self.assertEqual((result['functional'], result['deferred_must']), (0.0, 1))
        self.assertIsNone(plan.progress(None))
        heavy = plan.progress({'items': [{'id': 'A', 'title': 'a', 'status': 'done'},
                                         *({'id': f'D{i}', 'title': 'd', 'kind': 'debt'} for i in range(5))]})
        self.assertEqual(heavy['net'], 0.0)


if __name__ == '__main__':
    unittest.main()
