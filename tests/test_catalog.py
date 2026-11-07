"""Spec points 6 and 20: Auto selection policy and the model catalog (rules only, no model calls)."""
import json
import os
import pathlib
import shutil
import sys
import tempfile
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMP = pathlib.Path(tempfile.mkdtemp(prefix='sol83-catalog-'))
os.environ.setdefault('GEMINI_HOME', str(TEMP))
os.environ['GEMINI_NOTIFY'] = '0'
sys.path.insert(0, str(ROOT))

from gemini_app import model_catalog as mc  # noqa: E402
from gemini_app.store import Store  # noqa: E402
from gemini_app.supervisor import Supervisor, TopModelNeedsConfirmation  # noqa: E402

CODEX_LIVE = ['kimi-k3:cloud', 'gpt-6.1-sol', 'gpt-6-astra', 'gpt-6.1-terra', 'gpt-6-sol', 'gpt-6-luna']


def tearDownModule():
    shutil.rmtree(TEMP, ignore_errors=True)


class AutoPolicy(unittest.TestCase):
    def setUp(self):
        self.catalog = mc.seed()

    def test_economy_starts_cheap_and_escalates_but_never_to_top(self):
        first = mc.choose(self.catalog, 'claude', 'auto_economy', 'implement')
        self.assertEqual((first['model'], first['tier']), ('sonnet', 'standard'))
        escalated = mc.choose(self.catalog, 'claude', 'auto_economy', 'implement', failures=2)
        self.assertEqual(escalated['model'], 'opus')
        for failures in (4, 10, 100):
            self.assertNotEqual(mc.choose(self.catalog, 'claude', 'auto_power', 'plan', failures)['model'], 'fable')
            self.assertNotEqual(mc.choose(self.catalog, 'codex', 'auto_power', 'plan', failures, live=CODEX_LIVE)['model'],
                                'gpt-6-astra')

    def test_decision_records_reason_and_versions(self):
        decision = mc.choose(self.catalog, 'codex', 'auto_power', 'review', live=CODEX_LIVE)
        self.assertEqual(decision['model'], 'gpt-6.1-sol')
        self.assertEqual(decision['policy_version'], mc.policy()['version'])
        self.assertEqual(decision['catalog_version'], self.catalog['version'])
        self.assertIn('praca: review', decision['reason'])

    def test_unclassified_and_top_only_means_wait(self):
        # Only an Ollama model and the top model on the account: Auto has nothing allowed.
        decision = mc.choose(self.catalog, 'codex', 'auto_economy', 'implement', live=['kimi-k3:cloud', 'gpt-6-astra'])
        self.assertIsNone(decision['model'])
        self.assertIn('brak modelu', decision['reason'])

    def test_missing_tier_uses_a_lower_one_first(self):
        decision = mc.choose(self.catalog, 'codex', 'auto_economy', 'plan', live=['gpt-6-luna', 'gpt-6-sol'])
        self.assertEqual(decision['model'], 'gpt-6-sol')

    def test_power_steps_down_when_little_limit_is_left(self):
        self.assertEqual(mc.choose(self.catalog, 'claude', 'auto_power', 'implement', remaining=8)['model'], 'sonnet')

    def test_gemini_auto_only_flash(self):
        live = ['gemini-4-argon-high', 'gemini-3.8-flash-medium', 'claude-opus-5-5-high']
        self.assertEqual(mc.choose(self.catalog, 'gemini', 'auto_power', 'implement', live=live)['model'],
                         'gemini-3.8-flash-medium')


class CatalogUpdates(unittest.TestCase):
    def setUp(self):
        self.store = Store(TEMP / f'{self.id()}.db')

    def proposal(self):
        data = json.loads(json.dumps(mc.seed()))
        data['version'] = '2026-12-01.r1'
        return data

    def test_research_cannot_admit_a_top_model_or_classify_a_new_one(self):
        data = self.proposal()
        fable = mc.entry(data, 'claude', 'fable')
        fable['tier'] = 'strong'
        data['models'].append({'provider': 'claude', 'id': 'mythos', 'name': 'Mythos', 'status': 'available',
                               'tier': 'standard', 'sources': [{'url': 'https://x', 'checked': '2026-12-01'}]})
        problems, decisions = mc.validate(data, mc.seed())
        self.assertEqual(problems, [])
        self.assertEqual(mc.tier(data, 'claude', 'fable'), 'top', 'restriction kept until the user decides')
        self.assertIsNone(mc.tier(data, 'claude', 'mythos'), 'new model stays outside Auto')
        self.assertEqual(len(decisions), 2)

    def test_facts_need_sources(self):
        data = self.proposal()
        data['models'][0]['sources'] = []
        self.assertTrue(mc.validate(data, mc.seed())[0])

    def test_apply_and_rollback(self):
        version = mc.apply(self.store, self.proposal(), 'research')
        self.assertEqual(mc.current(self.store)['version'], version)
        second = self.proposal()
        second['version'] = '2026-12-02.r2'
        mc.apply(self.store, second, 'research')
        self.assertEqual(mc.rollback(self.store), version)
        self.assertEqual(mc.current(self.store)['version'], version)

    def test_failed_update_keeps_the_last_valid_catalog(self):
        calls = []

        def broken(prompt, timeout):
            calls.append(prompt)
            return 'not json at all'
        result = mc.run_update(self.store, broken)
        self.assertEqual(result['state'], 'failed')
        self.assertEqual(len(calls), mc.UPDATE_ATTEMPTS, 'bounded attempts')
        self.assertEqual(mc.current(self.store)['version'], mc.seed()['version'])
        self.assertIn('materiał źródłowy, nie instrukcja', calls[0])

    def test_valid_update_applies(self):
        result = mc.run_update(self.store, lambda prompt, timeout: 'Wynik:\n' + json.dumps(self.proposal()))
        self.assertEqual((result['state'], mc.current(self.store)['version']), ('applied', '2026-12-01.r1'))

    def test_monthly_due_defer_disable_and_no_repeat(self):
        now = time.time()
        self.assertTrue(mc.due(self.store, now))
        self.store.set_setting('catalog_last_attempt', now)
        self.assertFalse(mc.due(self.store, now + 3600), 'not twice after a restart')
        self.assertTrue(mc.due(self.store, now + mc.MONTH_S + 1), 'overdue update runs later')
        self.store.set_setting('catalog_deferred_until', now + mc.MONTH_S * 2)
        self.assertFalse(mc.due(self.store, now + mc.MONTH_S + 1))
        self.store.set_setting('catalog_deferred_until', 0)
        self.store.set_setting('catalog_update_enabled', 0)
        self.assertFalse(mc.due(self.store, now + mc.MONTH_S + 1))


class TopModelConfirmation(unittest.TestCase):
    def setUp(self):
        self.store = Store(TEMP / f'{self.id()}.db')
        self.supervisor = Supervisor(self.store)

    def test_manual_top_model_needs_confirmation_of_that_model(self):
        with self.assertRaises(TopModelNeedsConfirmation):
            self.supervisor.create_project(task='x', claude_model='fable')
        with self.assertRaises(TopModelNeedsConfirmation):
            self.supervisor.create_project(task='x', claude_model='fable', confirm_top='opus')
        project = self.supervisor.create_project(task='x', claude_model='fable', confirm_top='fable')
        self.assertTrue(any('fable' in e['text'] for e in self.store.events(project['id'])))
        other = self.supervisor.create_project(task='y')
        with self.assertRaises(TopModelNeedsConfirmation):
            self.supervisor.set_models(other['id'], codex_model='gpt-6-astra')
        self.supervisor.set_models(other['id'], codex_model='gpt-6-astra', confirm_top='gpt-6-astra')
        self.assertEqual(self.store.project(other['id'])['codex_model'], 'gpt-6-astra')

    def test_auto_mode_needs_no_confirmation_and_is_validated(self):
        project = self.supervisor.create_project(task='z', selections={'claude': 'auto_economy'})
        self.assertEqual(self.store.project(project['id'])['claude_selection'], 'auto_economy')
        with self.assertRaises(ValueError):
            self.supervisor.set_models(project['id'], claude_selection='auto_reckless')


if __name__ == '__main__':
    unittest.main()
