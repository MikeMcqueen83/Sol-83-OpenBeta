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
os.environ['GEMINI_NOTIFY'] = '0'
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _env  # noqa: E402,F401  (one data folder for all test modules)

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


class Queue(Base):
    def test_run_next_moves_a_project_to_the_front_and_queues_a_stopped_one(self):
        second = self.supervisor.create_project(task='Drugi')['id']
        third = self.supervisor.create_project(task='Trzeci')['id']
        self.assertEqual([p['id'] for p in self.supervisor.queue_order()], [self.pid, second, third])
        self.supervisor.run_next(third)
        self.assertEqual([p['id'] for p in self.supervisor.queue_order()][0], third)
        self.store.update_project(second, status='stopped')
        self.supervisor.run_next(second)
        self.assertEqual([p['id'] for p in self.supervisor.queue_order()][:2], [second, third])
        from gemini_app.server import overview
        rows = {p['id']: p['queue_position'] for p in overview(self.supervisor)['projects']}
        self.assertEqual((rows[second], rows[third], rows[self.pid]), (1, 2, 3))


class Recommended(Base):
    def test_newest_checked_version_wins_over_an_older_two_model_one(self):
        # PR17/26: v3 approved by both models, v6 accepted by Claude alone at the end: RUN must offer v6.
        from gemini_app.supervisor import recommended_version
        rows = [{'number': 6, 'level': 'single'}, {'number': 5, 'level': 'proposed'}, {'number': 3, 'level': 'approved'}]
        self.assertEqual(recommended_version(rows)['number'], 6)
        self.assertEqual(recommended_version(rows[1:])['number'], 3, 'an unchecked claim does not beat a checked version')
        self.assertEqual(recommended_version([{'number': 6, 'level': 'single', 'user_verdict': 'bad'}] + rows[1:])['number'], 3)


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
        # A pass on the newer version settles the test: the gate asks for a pass on the current version.
        # (Until 2026-11-08 it was "late", and the panel always sends the newest version: such a test could
        # never be settled and its notification came back after every confirmation.)
        newer = self.supervisor.answer_interaction(self.pid, added['id'], result='works')
        self.assertFalse(newer['late'])
        self.assertNotIn(f"test:I{added['id']}", self.supervisor.close_blockers(self.pid))
        recorded_v2 = interactions.add(self.store, self.pid, 'manual_test', 'Sprawdź eksport', 'codex', version_number=2)
        older = interactions.answer(self.store, recorded_v2['id'], result='works', version=1)
        self.assertTrue(older['late'], 'a result for an older version does not settle a test of a newer one')
        self.assertEqual(interactions.get(self.store, recorded_v2['id'])['state'], 'open')

    def test_confirmed_test_is_done_for_the_user_and_does_not_come_back(self):
        # PR10/26 on 2026-11-08: test I3 recorded at v1, confirmed "works" while v2 was the newest.
        self.store.add_version(self.pid, tag_prefix='g', commit_sha='a' * 40, tree='t', level='tested', turn=1, agent='codex')
        added = interactions.add(self.store, self.pid, 'manual_test', 'Serwer działa stabilnie', 'gemini', version_number=1)
        self.store.add_version(self.pid, tag_prefix='g', commit_sha='b' * 40, tree='u', level='tested', turn=2, agent='codex')
        self.supervisor.answer_interaction(self.pid, added['id'], result='works', request_key='click-1')
        from gemini_app.server import overview
        row = next(p for p in overview(self.supervisor)['projects'] if p['id'] == self.pid)
        self.assertEqual(row['questions_open'], 0)
        self.assertEqual(interactions.get(self.store, added['id'])['state'], 'applied')
        self.assertEqual(interactions.prompt_lines(self.store, self.pid, 'pl'), [], 'agents are not asked again either')

    def test_works_on_the_final_version_closes_it_and_does_not_reopen_the_project(self):
        # PR15/26 on 2026-11-08: two "works" answers reopened the finished project for two more rounds.
        self.store.add_version(self.pid, tag_prefix='g', commit_sha='a' * 40, tree='t', level='approved', turn=3,
                               agent='claude', what_to_test='Przejrzyj rozdział 6')
        self.store.update_project(self.pid, status='done')
        self.supervisor._final_check(self.pid)
        check = next(row for row in interactions.listing(self.store, self.pid) if row['author'] == 'version')
        saved = self.supervisor.answer_interaction(self.pid, check['id'], result='works', request_key='ok')
        self.assertTrue(saved['closed'])
        self.assertEqual(self.store.project(self.pid)['status'], 'done')
        self.assertEqual(self.store.pending_notes(self.pid), [])
        self.assertEqual(interactions.get(self.store, check['id'])['state'], 'applied')
        self.assertEqual(self.store.version(self.pid, 1)['user_verdict'], 'ok')
        self.supervisor.interaction_state(self.pid, check['id'], 'open')
        self.supervisor.answer_interaction(self.pid, check['id'], result='fails', comment='brak diagramu 6.4',
                                           request_key='bad')
        self.assertEqual(self.store.project(self.pid)['status'], 'queued', '"does not work" asks for fixes')
        self.assertEqual(len(self.store.pending_notes(self.pid)), 1)

    def test_records_left_open_by_the_old_rule_are_repaired_once(self):
        import json
        self.store.add_version(self.pid, tag_prefix='g', commit_sha='a' * 40, tree='t', level='tested', turn=1, agent='codex')
        added = interactions.add(self.store, self.pid, 'manual_test', 'Interfejs w przeglądarce', 'gemini', version_number=1)
        old_answer = [{'ts': 1.0, 'value': '', 'comment': '', 'result': 'works', 'evidence': 'declaration', 'version': 2,
                       'request_key': 'k', 'late': True}]
        with self.store.tx() as db:
            db.execute('UPDATE interactions SET answers=? WHERE id=?', (json.dumps(old_answer), added['id']))
        ref = f"I{added['id']}"
        for key in ('n1', 'n2'):
            self.supervisor.add_note(self.pid, f'Wynik testu {key}', kind='answer', ref=ref, request_key=key)
        Supervisor(self.store)
        row = interactions.get(self.store, added['id'])
        self.assertEqual(row['state'], 'answered')
        self.assertEqual((row['answers'][0]['late'], row['answers'][0]['repaired']), (False, True))
        pending = [n for n in self.store.pending_notes(self.pid) if n['ref'] == ref]
        self.assertEqual([n['text'] for n in pending], ['Wynik testu n2'], 'one answer reaches the agents, the newest')
        self.assertEqual(interactions.repair_late_answers(self.store), [], 'nothing to do the second time')

    def test_user_is_asked_to_test_the_final_version_only_by_default(self):
        # 2026-11-08, PR14/26: six "what to check" requests in eight minutes of a research project.
        for number, sha in ((1, 'a'), (2, 'b')):
            self.store.add_version(self.pid, tag_prefix='g', commit_sha=sha * 40, tree=sha, level='proposed', turn=number,
                                   agent='codex', what_to_test=f'Przejrzyj rozdział {number}')
        self.supervisor._final_check(self.pid)
        self.supervisor._final_check(self.pid)
        checks = [row for row in interactions.listing(self.store, self.pid) if row['author'] == 'version']
        self.assertEqual([(row['version_number'], row['state']) for row in checks], [(2, 'open')])
        other = self.supervisor.create_project(task='Aplikacja')['id']
        self.supervisor.set_options(other, user_tests='none', web_fetch=True)
        self.assertEqual((self.store.project(other)['user_tests'], self.store.project(other)['web_fetch']), ('none', 1))
        self.store.add_version(other, tag_prefix='g', commit_sha='c' * 40, tree='c', level='proposed', turn=1,
                               agent='codex', what_to_test='Sprawdź')
        self.supervisor._final_check(other)
        self.assertEqual(interactions.listing(self.store, other), [])
        with self.assertRaises(ValueError):
            self.supervisor.set_options(other, user_tests='sometimes')

    def test_changed_answer_replaces_the_waiting_note(self):
        added = interactions.add(self.store, self.pid, 'decision', 'Jaki kolor?', 'codex', options=['zielony', 'niebieski'])
        self.supervisor.answer_interaction(self.pid, added['id'], 'zielony', request_key='a')
        self.supervisor.interaction_state(self.pid, added['id'], 'open')
        self.supervisor.answer_interaction(self.pid, added['id'], 'niebieski', request_key='b')
        pending = [n for n in self.store.pending_notes(self.pid) if n['ref'] == f"I{added['id']}"]
        self.assertEqual(len(pending), 1)
        self.assertIn('niebieski', pending[0]['text'])

    def test_works_in_the_version_card_after_the_same_test_answer_is_not_recorded_twice(self):
        self.store.add_version(self.pid, tag_prefix='g', commit_sha='a' * 40, tree='t', level='tested', turn=1,
                               agent='codex', what_to_test='1. Otwórz aplikację')
        added = interactions.add(self.store, self.pid, 'manual_test', '1. Otwórz aplikację', 'version', version_number=1)
        self.supervisor.answer_interaction(self.pid, added['id'], result='works', request_key='tab')
        self.supervisor.set_verdict(self.pid, 1, True)
        self.assertEqual(len(interactions.get(self.store, added['id'])['answers']), 1)
        self.assertEqual(self.store.version(self.pid, 1)['user_verdict'], 'ok')

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
