"""Spec points 1-3: durable queue, atomic closing, plan contract and revisions (no engine)."""
import json
import os
import pathlib
import shutil
import sys
import tempfile
import threading
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMP = pathlib.Path(tempfile.mkdtemp(prefix='sol83-queue-'))
os.environ.setdefault('GEMINI_HOME', str(TEMP))
os.environ['GEMINI_NOTIFY'] = '0'
sys.path.insert(0, str(ROOT))

from gemini_app import orders, plan, plan_contract  # noqa: E402
from gemini_app.store import Store  # noqa: E402
from gemini_app.supervisor import Supervisor  # noqa: E402


def tearDownModule():
    shutil.rmtree(TEMP, ignore_errors=True)


class QueueBase(unittest.TestCase):
    def setUp(self):
        self.store = Store(TEMP / f'{self.id()}.db')
        self.supervisor = Supervisor(self.store)
        self.pid = 'p' + str(abs(hash(self.id())))[:8]
        self.store.add_project(id=self.pid, title='T', task='Zadanie', status='running',
                               claude_model='opus', codex_model='gpt', gemini_model='none')


class DurableQueue(QueueBase):
    def test_retransmitted_request_creates_one_entry(self):
        first = self.supervisor.add_note(self.pid, 'Dodaj eksport', request_key='k-1')
        second = self.supervisor.add_note(self.pid, 'Dodaj eksport', request_key='k-1')
        self.assertTrue(first['created'])
        self.assertFalse(second['created'])
        self.assertEqual(first['id'], second['id'])
        self.assertEqual(len(self.store.notes(self.pid)), 1)
        # A deliberate new request for similar work is still possible.
        self.assertTrue(self.supervisor.add_note(self.pid, 'Dodaj eksport', request_key='k-2')['created'])

    def test_concurrent_identical_requests(self):
        results = []
        threads = [threading.Thread(target=lambda: results.append(
            self.supervisor.add_note(self.pid, 'Równocześnie', request_key='same'))) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sum(r['created'] for r in results), 1)
        self.assertEqual(len(self.store.notes(self.pid)), 1)

    def test_closing_with_queued_work_keeps_the_project_open(self):
        self.supervisor.add_note(self.pid, 'Nowe zlecenie w trakcie finalizacji')
        self.assertEqual(orders.finish(self.store, self.pid), 'queued')
        self.assertEqual(self.store.project(self.pid)['status'], 'queued')

    def test_work_added_right_after_closing_reopens(self):
        self.assertEqual(orders.finish(self.store, self.pid), 'done')
        added = self.supervisor.add_note(self.pid, 'Jeszcze jedno')
        self.assertEqual(added['status'], 'done')
        self.assertEqual(self.store.project(self.pid)['status'], 'queued')
        self.assertEqual(self.store.notes(self.pid)[0]['reopened'], 'done')

    def test_close_and_add_race_never_loses_work(self):
        for round_ in range(20):
            self.store.update_project(self.pid, status='running', finished_at=None)
            with self.store._db() as db:
                db.execute('DELETE FROM notes WHERE project_id=?', (self.pid,))
            closing = threading.Thread(target=lambda: orders.finish(self.store, self.pid))
            adding = threading.Thread(target=lambda: self.supervisor.add_note(self.pid, f'r{round_}'))
            closing.start(); adding.start(); closing.join(); adding.join()
            # Whatever the order, the note is open work and the project is not closed over it.
            self.assertNotEqual(self.store.project(self.pid)['status'], 'done', round_)
            self.assertEqual(len(self.store.pending_notes(self.pid)), 1)

    def test_interrupted_turn_gives_its_work_back(self):
        self.supervisor.add_note(self.pid, 'Popraw filtr')
        taken = self.store.take_notes(self.pid, 'codex', 3)
        self.assertEqual(len(taken), 1)
        self.assertEqual(self.store.pending_notes(self.pid), [])
        self.assertEqual(orders.requeue_unanswered(self.store, self.pid), 1)
        self.assertEqual(len(self.store.pending_notes(self.pid)), 1)

    def test_answered_then_done_with_an_accepted_version(self):
        self.supervisor.add_note(self.pid, 'Zrób X')
        self.store.take_notes(self.pid, 'codex', 4)
        self.store.answer_notes(self.pid, 4, 'Zrobione X')
        self.assertEqual(self.store.notes(self.pid)[0]['status'], 'answered')
        self.assertEqual(orders.requeue_unanswered(self.store, self.pid), 0)
        orders.mark_done(self.store, self.pid, 2, 5)
        row = self.store.notes(self.pid)[0]
        self.assertEqual((row['status'], row['done_version']), ('done', 2))

    def test_plan_items_enter_the_same_queue_first(self):
        self.supervisor.add_note(self.pid, 'zwykła uwaga')
        self.supervisor.add_note(self.pid, 'pozycja F2', kind='item', ref='F2', priority=1)
        taken = self.store.take_notes(self.pid, 'claude', 1)
        self.assertEqual([n['kind'] for n in taken], ['item', 'note'])
        self.assertEqual(taken[0]['ref'], 'F2')


class MetaMerge(QueueBase):
    def test_two_writers_keep_both_changes(self):
        server, engine = self.store.meta(self.pid), self.store.meta(self.pid)
        server['asset_orders'] = [{'path': 'a.png'}]
        self.store.save_meta(self.pid, server)
        engine['seen'] = {'codex': 'abc'}
        self.store.save_meta(self.pid, engine)
        meta = self.store.meta(self.pid)
        self.assertEqual(meta['asset_orders'], [{'path': 'a.png'}])
        self.assertEqual(meta['seen'], {'codex': 'abc'})

    def test_removal_is_kept(self):
        self.store.update_meta(self.pid, lambda m: m.update(replan='inherited', other=1))
        copy = self.store.meta(self.pid)
        copy.pop('replan')
        self.store.save_meta(self.pid, copy)
        self.assertEqual(dict(self.store.meta(self.pid)), {'other': 1})


class PlanContract(unittest.TestCase):
    def plan(self, *items):
        return {'items': [dict(id=f'F{i}', title='t', **item) for i, item in enumerate(items, 1)]}

    def test_polish_and_english_variants_are_normalized_and_logged(self):
        data = self.plan({'status': 'Zrobione'}, {'status': 'in-progress'}, {'status': 'odłożone'},
                         {'priority': 'MUST', 'kind': 'zadanie'})
        normalized, problems, corrections = plan_contract.normalize(data)
        self.assertEqual(problems, [])
        self.assertEqual([i['status'] for i in normalized['items']], ['done', 'doing', 'deferred', 'todo'])
        self.assertEqual(normalized['items'][3]['priority'], 'must')
        self.assertEqual(len(corrections), 5)
        self.assertEqual(data['items'][0]['status'], 'Zrobione', 'the input is not changed')

    def test_unknown_status_is_an_error_never_done(self):
        _, problems, _ = plan_contract.normalize(self.plan({'status': 'prawie gotowe'}, {'status': 'blocked'}))
        self.assertEqual(len(problems), 2)

    def test_broken_structure_ids_and_dependencies(self):
        self.assertTrue(plan_contract.normalize({'items': 'x'})[1])
        self.assertTrue(plan_contract.normalize([1, 2])[1])
        bad = {'items': [{'id': 'A', 'title': 't', 'depends_on': ['Z']}, {'id': 'A', 'title': 'u'},
                         {'id': 'B C', 'title': 'v'}, {'title': 'bez id'}]}
        problems = plan_contract.normalize(bad)[1]
        self.assertTrue(any('nieznana zależność Z' in p for p in problems))
        self.assertTrue(any('powtórzone id A' in p for p in problems))
        self.assertTrue(any('id ze spacją' in p for p in problems))
        cycle = {'items': [{'id': 'A', 'title': 't', 'depends_on': ['B']}, {'id': 'B', 'title': 'u', 'depends_on': ['A']}]}
        self.assertTrue(any('cykl' in p for p in plan_contract.normalize(cycle)[1]))

    def test_deferred_must_is_not_done(self):
        plan_data = plan_contract.normalize(self.plan({'priority': 'must', 'status': 'deferred'}))[0]
        self.assertEqual(len(plan_contract.must_deferred(plan_data)), 1)


class PlanRevisions(QueueBase):
    def setUp(self):
        super().setUp()
        self.worktree = pathlib.Path(tempfile.mkdtemp(dir=TEMP))
        (self.worktree / '.sol83').mkdir()
        self.store.update_project(self.pid, worktree=str(self.worktree))

    def write(self, data):
        (self.worktree / plan.PLAN_FILE).write_text(data if isinstance(data, str) else json.dumps(data))

    def test_valid_revisions_and_last_valid_plan_survives_a_bad_update(self):
        good = {'items': [{'id': 'F1', 'title': 'Import', 'status': 'gotowe'}]}
        self.write(good)
        self.assertEqual(plan.record(self.store, self.pid, self.worktree, 1)['revision'], 1)
        self.assertIsNone(plan.record(self.store, self.pid, self.worktree, 2)['revision'], 'same plan, no revision')
        self.write('{"items": [ broken')
        state = plan.record(self.store, self.pid, self.worktree, 3)
        self.assertEqual(state['state'], 'invalid')
        effective, problem = plan.effective(self.store, self.store.project(self.pid))
        self.assertEqual(effective['items'][0]['status'], 'done')
        self.assertIn('JSON', problem)

    def test_bounded_repair_restores_the_last_valid_plan(self):
        self.write({'items': [{'id': 'F1', 'title': 'Import'}]})
        plan.record(self.store, self.pid, self.worktree, 1)
        self.write({'items': [{'id': 'F1', 'title': 'Import', 'status': '???'}]})
        states = [plan.record(self.store, self.pid, self.worktree, turn)['state'] for turn in (2, 3, 4)]
        self.assertEqual(states, ['invalid', 'invalid', 'restored'])
        self.assertEqual(json.loads((self.worktree / plan.PLAN_FILE).read_text())['items'][0]['status'], 'todo')
        self.assertIn('???', (self.worktree / '.sol83/plan.invalid.json').read_text())

    def test_close_blocked_by_deferred_must(self):
        self.write({'items': [{'id': 'F1', 'title': 'Eksport', 'priority': 'must', 'status': 'deferred'}]})
        plan.record(self.store, self.pid, self.worktree, 1)
        blockers = self.supervisor.close_blockers(self.pid)
        self.assertEqual(blockers, ['must-deferred:F1'])
        # A gate only the user can settle: the project waits for them, it is not relaunched in a loop.
        self.assertEqual(orders.finish(self.store, self.pid, blockers), 'attention')


if __name__ == '__main__':
    unittest.main()
