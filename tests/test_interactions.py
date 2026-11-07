"""Spec points 7, 9, 10, 21: several roles per model, project language and keys, questions and manual tests."""
import os
import pathlib
import shutil
import sys
import tempfile
import threading
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMP = pathlib.Path(tempfile.mkdtemp(prefix='sol83-inter-'))
os.environ.setdefault('GEMINI_HOME', str(TEMP))
os.environ['GEMINI_NOTIFY'] = '0'
sys.path.insert(0, str(ROOT))

from gemini_app import interactions, plan, prompts  # noqa: E402
from gemini_app import roles as model_roles  # noqa: E402
from gemini_app.store import Store  # noqa: E402
from gemini_app.supervisor import Supervisor, detect_language  # noqa: E402


def tearDownModule():
    shutil.rmtree(TEMP, ignore_errors=True)


class Base(unittest.TestCase):
    def setUp(self):
        self.store = Store(TEMP / f'{self.id()}.db')
        self.supervisor = Supervisor(self.store)
        self.pid = self.supervisor.create_project(task='Zbuduj aplikację do notatek dla zespołu')['id']


class Roles(Base):
    def test_several_roles_and_old_single_values(self):
        self.assertEqual(model_roles.parse('tester'), ('tester',))
        self.assertEqual(model_roles.parse('analyst,tester'), ('tester', 'analyst'))
        self.assertEqual(model_roles.parse(''), ('general',))
        self.assertTrue(model_roles.covers('tester,architect', 'plan'))
        self.assertTrue(model_roles.covers(('tester', 'architect'), 'review'))
        self.assertFalse(model_roles.covers('tester,architect', 'implement'))

    def test_general_does_not_make_content(self):
        self.assertFalse(model_roles.covers('general', 'content'))
        self.assertTrue(model_roles.covers('general,content', 'content'))

    def test_coverage_is_checked_after_a_change(self):
        self.supervisor.set_models(self.pid, codex_role='implementer,tester', claude_role='architect')
        self.assertEqual(self.store.project(self.pid)['codex_role'], 'implementer,tester')
        with self.assertRaises(ValueError):
            self.supervisor.set_models(self.pid, codex_role='implementer', claude_role='architect')
        with self.assertRaises(ValueError):
            self.supervisor.set_models(self.pid, codex_role='implementer,wizard')


class LanguageAndKeys(Base):
    def test_language_fixed_at_creation(self):
        english = self.supervisor.create_project(task='Build a notes app', language='en')
        self.assertEqual(english['language'], 'en')
        self.assertEqual(self.store.project(self.pid)['language'], 'pl')
        self.assertIn('Answer in English', prompts.text('en', 'role_prompt'))
        self.assertNotIn('po polsku', prompts.text('en', 'role_prompt'))
        self.assertIn('Working with the plan', plan.text('en', 'rules'))

    def test_detection_for_old_projects(self):
        self.assertEqual(detect_language('Zbuduj grę RTS w przeglądarce, z mapą i jednostkami'), 'pl')
        self.assertEqual(detect_language('Build a browser RTS game with a map and units for the user'), 'en')
        self.assertEqual(detect_language('Facade360'), 'unknown')
        self.store.update_project(self.pid, language=None)
        Supervisor(self.store)
        self.assertEqual(self.store.project(self.pid)['language'], 'pl')

    def test_keys_are_global_per_year_unique_and_never_reused(self):
        key = self.store.project(self.pid)['key']
        self.assertRegex(key, r'^PR\d+/\d\d$')
        keys = []
        threads = [threading.Thread(target=lambda: keys.append(self.supervisor.create_project(task='x')['key']))
                   for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(len(set(keys)), 10)
        last = self.supervisor.create_project(task='y')
        self.supervisor.delete_project(last['id'])
        self.assertNotEqual(self.supervisor.create_project(task='z')['key'], last['key'])

    def test_rename_keeps_identity(self):
        before = self.store.project(self.pid)
        self.supervisor.rename(self.pid, 'Notatki zespołu')
        after = self.store.project(self.pid)
        self.assertEqual((after['title'], after['id'], after['key']), ('Notatki zespołu', before['id'], before['key']))


class Interactions(Base):
    def test_same_open_question_is_not_asked_twice(self):
        first = interactions.add(self.store, self.pid, 'clarification', 'Jaki serwer?', 'codex')
        again = interactions.add(self.store, self.pid, 'clarification', '  jaki   SERWER? ', 'claude')
        self.assertEqual((first['created'], again['created'], again['id']), (True, False, first['id']))

    def test_answer_is_idempotent_and_reaches_the_queue(self):
        added = interactions.add(self.store, self.pid, 'decision', 'SQLite czy Postgres?', 'codex',
                                 options=['SQLite', 'Postgres'], blocks=['F2'])
        self.assertIn(f"question:I{added['id']}", self.supervisor.close_blockers(self.pid))
        first = self.supervisor.answer_interaction(self.pid, added['id'], 'SQLite', request_key='k1')
        second = self.supervisor.answer_interaction(self.pid, added['id'], 'SQLite', request_key='k1')
        self.assertTrue(first['applied'])
        self.assertTrue(second['duplicate'])
        notes = [n for n in self.store.notes(self.pid) if n['kind'] == 'answer']
        self.assertEqual(len(notes), 1)
        self.assertIn('SQLite', notes[0]['text'])
        self.assertEqual(interactions.get(self.store, added['id'])['state'], 'answered')
        self.assertNotIn(f"question:I{added['id']}", self.supervisor.close_blockers(self.pid))

    def test_late_answers_are_kept_not_applied(self):
        added = interactions.add(self.store, self.pid, 'clarification', 'Stare pytanie', 'codex')
        interactions.set_state(self.store, added['id'], 'superseded')
        saved = self.supervisor.answer_interaction(self.pid, added['id'], 'odpowiedź')
        self.assertTrue(saved['late'])
        self.assertEqual(interactions.get(self.store, added['id'])['state'], 'superseded')
        self.assertFalse([n for n in self.store.notes(self.pid) if n['kind'] == 'answer'])

    def test_manual_test_for_another_version_and_failed_result(self):
        self.store.add_version(self.pid, tag_prefix='g', commit_sha='a' * 40, tree='t', level='tested', turn=1, agent='codex')
        added = interactions.add(self.store, self.pid, 'manual_test', 'Sprawdź PTT na telefonie', 'codex',
                                 mandatory=True, version_number=1, steps=[{'step': 'naciśnij', 'expected': 'nagrywa'}])
        self.assertIn(f"test:I{added['id']}", self.supervisor.close_blockers(self.pid))
        failed = self.supervisor.answer_interaction(self.pid, added['id'], result='fails', comment='cisza')
        self.supervisor.answer_interaction(self.pid, added['id'], result='fails', comment='cisza', request_key='again')
        bugs = [n for n in self.store.notes(self.pid) if n['kind'] == 'verdict']
        self.assertEqual(len(bugs), 1, 'one bug report per test and version')
        self.assertTrue(failed['applied'])
        self.store.add_version(self.pid, tag_prefix='g', commit_sha='b' * 40, tree='u', level='tested', turn=2, agent='codex')
        late = self.supervisor.answer_interaction(self.pid, added['id'], result='works')
        self.assertTrue(late['late'], 'a result for v2 does not settle the test of v1')
        self.assertIn(f"test:I{added['id']}", self.supervisor.close_blockers(self.pid))

    def test_no_answer_is_not_consent_and_deferring_keeps_the_gate(self):
        added = interactions.add(self.store, self.pid, 'manual_test', 'Test offline', 'codex', mandatory=True)
        self.supervisor.interaction_state(self.pid, added['id'], 'deferred')
        self.assertIn(f"test:I{added['id']}", self.supervisor.close_blockers(self.pid))

    def test_requests_file_is_ingested(self):
        worktree = pathlib.Path(tempfile.mkdtemp(dir=TEMP))
        (worktree / '.sol83').mkdir()
        (worktree / interactions.REQUESTS_FILE).write_text(
            '{"items": [{"id": "Q1", "type": "clarification", "text": "Który model telefonu?", "blocks": ["H1"]},'
            ' {"id": "X", "type": "nonsense", "text": "?"}]}')
        created = interactions.ingest(self.store, self.pid, worktree, 'claude', {'lang': 'pl'})
        self.assertEqual([(row['local_id'], row['blocks']) for row in created], [('Q1', ['H1'])])
        self.assertEqual(interactions.ingest(self.store, self.pid, worktree, 'claude', {}), [], 'not twice')
        lines = interactions.prompt_lines(self.store, self.pid, 'pl')
        self.assertIn('nie powtarzaj', lines[1])


if __name__ == '__main__':
    unittest.main()


class ProjectLicense(Base):
    def setUp(self):
        super().setUp()
        from gemini_app import gitops
        self.work = pathlib.Path(tempfile.mkdtemp(dir=TEMP))
        gitops.create_repo(self.work)
        self.store.update_project(self.pid, worktree=str(self.work), status='stopped')

    def test_standard_license_text_is_unmodified_and_committed(self):
        from gemini_app import licenses
        self.supervisor.set_license(self.pid, 'standard', 'MIT', 'Jan Kowalski')
        text = (self.work / 'LICENSE').read_text()
        original = (licenses.DATA / 'MIT.txt').read_text()
        self.assertEqual(text.replace('Jan Kowalski', '[fullname]').split('\n', 3)[3], original.split('\n', 3)[3])
        self.assertIn('Jan Kowalski', text)
        self.assertIn('licencja MIT', __import__('subprocess').run(['git', 'log', '-1', '--format=%s'], cwd=self.work,
                                                                   capture_output=True, text=True).stdout)
        self.assertTrue(any('LICENSE' in n['text'] for n in self.store.notes(self.pid)))

    def test_existing_license_needs_an_explicit_decision(self):
        (self.work / 'LICENSE').write_text('own terms\n')
        with self.assertRaises(ValueError):
            self.supervisor.set_license(self.pid, 'standard', 'Apache-2.0', 'X')
        self.assertEqual((self.work / 'LICENSE').read_text(), 'own terms\n')
        self.supervisor.set_license(self.pid, 'custom', custom='Source-available, see terms.', overwrite=True)
        self.assertIn('Source-available', (self.work / 'LICENSE').read_text())

    def test_none_and_unknown(self):
        self.supervisor.set_license(self.pid, 'none')
        self.assertFalse((self.work / 'LICENSE').exists())
        with self.assertRaises(ValueError):
            self.supervisor.set_license(self.pid, 'standard', 'WTFPL-ish')
