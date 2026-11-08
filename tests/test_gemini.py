"""End-to-end tests: the real engine and coordinator against scripted CLIs."""
import json
import os
import pathlib
import re
import shutil
import signal
import string
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _env  # noqa: E402
TEMP = _env.HOME
FAKES = ROOT / 'tests/fakes'
os.environ.update({
    'GEMINI_NOTIFY': '0', 'GEMINI_GITHUB_URL': f'file://{TEMP}/github', 'GEMINI_HOME': str(TEMP), 'FAKE_DIR': str(TEMP), 'GEMINI_EXTRA_PATH': str(FAKES / 'bin'),
    'GEMINI_CLAUDE_BIN': str(FAKES / 'claude-binary'), 'GEMINI_WAIT_POLL': '0.2',
    'GEMINI_LIMITS_TTL': '0', 'GEMINI_RETRY_DELAY': '0', 'GEMINI_OLLAMA_URL': 'http://127.0.0.1:9',
    'GEMINI_CLI_BIN': str(FAKES / 'agy-binary'), 'GEMINI_LOCK_WAIT': '1',
    # The fake CLIs record their calls in TEMP, outside the sandboxed project folder.
    'SOL83_SANDBOX_WRITE': str(TEMP)})
for key in ('ANTHROPIC_API_KEY', 'OPENAI_API_KEY', 'CODEX_API_KEY'):
    os.environ.pop(key, None)
sys.path.insert(0, str(ROOT))

from gemini_app import catalog, gitops, limits, observer  # noqa: E402
from gemini_app import plan as plan_module  # noqa: E402
from gemini_app.gitops import Git  # noqa: E402
from gemini_app.messages import CATALOG, Msg  # noqa: E402
from gemini_app.paths import STATE  # noqa: E402
from gemini_app.scheduler import _NOTE_REPLY, goal_report, how_to_run, section, what_to_test  # noqa: E402
from gemini_app.server import Handler  # noqa: E402
from gemini_app.store import Store  # noqa: E402
from gemini_app.supervisor import Supervisor, engine_pids, recommended_version  # noqa: E402

LIMIT_MESSAGE = ('You’ve hit your usage limit. Upgrade to Pro (https://chatgpt.com/explore/pro), '
                 'visit https://chatgpt.com/settings/usage to purchase more credits or try again '
                 'at Nov 2nd, 2026 2:41 AM.')
FRESH = {'five_hour': 10, 'seven_day': 20}
VERIFY = 'python3 check.py'


def exhausted(seconds=3600):
    return {'five_hour': {'used': 100, 'resets_at': time.time() + seconds}, 'seven_day': 20}


def tearDownModule():
    pass  # the shared data folder is removed when the test process exits (tests/_env.py)


class Base(unittest.TestCase):
    def setUp(self):
        self.store = Store()
        with self.store._db() as db:
            db.execute('DELETE FROM blocks')
            db.execute('DELETE FROM settings')
        (STATE / 'limits-claude.json').unlink(missing_ok=True)
        (TEMP / 'calls.jsonl').unlink(missing_ok=True)
        self.supervisor = Supervisor(self.store)
        self.repo = pathlib.Path(tempfile.mkdtemp(dir=TEMP))
        gitops.create_repo(self.repo)
        (self.repo / 'check.py').write_text(
            "import pathlib,sys\n"
            "p=pathlib.Path('ok.txt')\n"
            "sys.exit(0 if p.exists() and p.read_text()=='ok' else 1)\n")
        git = Git(self.repo)
        git.run('add', '-A')
        git.run(*gitops.IDENTITY, 'commit', '-q', '-m', 'start')

    def tearDown(self):
        for project in self.store.projects('running', 'stopping', 'queued'):
            pid = project['engine_pid']
            if pid and project['id'] in self.supervisor.procs:
                os.kill(pid, signal.SIGKILL)
                self.supervisor.procs[project['id']].wait()
            self.store.update_project(project['id'], status='stopped')

    def scenario(self, claude=(), codex=(), claude_limits=None, codex_limits=None, gemini=()):
        (TEMP / 'scenario.json').write_text(json.dumps({
            'limits': {'claude': claude_limits or FRESH, 'codex': codex_limits or FRESH},
            'script': {'claude': list(claude), 'codex': list(codex), 'gemini': list(gemini)}}))

    def set_limits(self, **values):
        scenario = json.loads((TEMP / 'scenario.json').read_text())
        scenario['limits'].update(values)
        (TEMP / 'scenario.json').write_text(json.dumps(scenario))

    def calls(self):
        path = TEMP / 'calls.jsonl'
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def start(self, verify=VERIFY, turns=12):
        return self.supervisor.create_project(task='Zbuduj ok.txt', repo_path=str(self.repo),
                                              verify_cmd=verify or '', max_turns=turns)['id']

    def wait_for(self, condition, timeout=30, what='warunek'):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.supervisor.tick()
            value = condition()
            if value:
                return value
            time.sleep(0.05)
        project = self.store.projects()[0]
        self.fail(f"Nie spełniono: {what}. Status={project['status']} "
                  f"detail={project['status_detail']} "
                  f"events={[e['text'] for e in self.store.events(project['id'], 12)]}")

    def wait_status(self, project_id, *statuses, timeout=30):
        return self.wait_for(lambda: self.store.project(project_id)['status'] in statuses,
                             timeout, f'status {statuses}')

    def wait_phase(self, project_id, phase):
        return self.wait_for(lambda: (self.store.live(project_id) or {}).get('phase') == phase,
                             what=f'faza {phase}')

    def kinds(self, project_id):
        return [event['kind'] for event in self.store.events(project_id)]


class Alternation(Base):
    def test_build_then_cross_review_converges_and_approves_version(self):
        self.scenario(
            codex=[{'write': {'ok.txt': 'ok'}, 'what_to_test': '- otwórz ok.txt'},
                   {'lgtm': True}],
            claude=[{'lgtm': True}])
        project_id = self.start()
        self.wait_status(project_id, 'done')
        self.assertEqual([call['agent'] for call in self.calls()], ['codex', 'claude', 'codex'])
        version = self.store.latest_version(project_id)
        self.assertEqual(version['number'], 1)
        self.assertEqual(version['level'], 'approved')
        self.assertEqual(sorted(version['accepted_by']), ['claude', 'codex'])
        self.assertIn('otwórz ok.txt', version['what_to_test'])
        git = Git(self.store.project(project_id)['worktree'])
        self.assertEqual(git.run('rev-parse', version['tag']), version['commit_sha'])

    def test_partner_receives_task_on_first_turn(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}, {'lgtm': True}], claude=[{'lgtm': True}])
        self.wait_status(self.start(), 'done')
        claude_prompt = next(c['prompt'] for c in self.calls() if c['agent'] == 'claude')
        self.assertIn('Zbuduj ok.txt', claude_prompt)

    def test_lgtm_binds_to_exact_code_a_later_change_needs_new_review(self):
        self.scenario(
            codex=[{'write': {'ok.txt': 'ok'}, 'lgtm': True}, {'lgtm': True}],
            claude=[{'write': {'extra.txt': 'x'}, 'lgtm': True}])
        project_id = self.start()
        self.wait_status(project_id, 'done')
        self.assertEqual([call['agent'] for call in self.calls()], ['codex', 'claude', 'codex'])
        self.assertEqual(self.store.latest_version(project_id)['number'], 2)

    def test_opening_turn_goes_to_model_with_more_limit_left(self):
        self.scenario(claude=[{'write': {'ok.txt': 'ok'}}, {'lgtm': True}], codex=[{'lgtm': True}],
                      codex_limits={'five_hour': 70, 'seven_day': 20})
        self.wait_status(self.start(), 'done')
        self.assertEqual(self.calls()[0]['agent'], 'claude')


class LimitSwitching(Base):
    def test_proactive_handoff_then_partner_returns_for_review(self):
        near_limit = {'five_hour': {'used': 97, 'resets_at': time.time() + 3600}, 'seven_day': 20}
        self.scenario(
            codex=[{'write': {'ok.txt': 'ok'}, 'set_limits': {'codex': near_limit}},
                   {'lgtm': True}],
            claude=[{'write': {'a.txt': '1'}}, {'lgtm': True}])
        project_id = self.start()
        self.wait_phase(project_id, 'waiting_partner')
        self.assertEqual([c['agent'] for c in self.calls()], ['codex', 'claude', 'claude'])
        self.assertIn('handoff', self.kinds(project_id))
        self.assertIn('Tryb solo', self.calls()[-1]['prompt'])
        self.assertEqual(self.store.project(project_id)['status'], 'running')
        self.set_limits(codex=FRESH)
        self.wait_status(project_id, 'done')
        review = self.calls()[-1]
        self.assertEqual(review['agent'], 'codex')
        self.assertIn('a.txt', review['prompt'])
        self.assertEqual(self.store.latest_version(project_id)['level'], 'approved')

    def test_mid_turn_limit_saves_partial_work_and_partner_takes_over(self):
        self.scenario(
            codex=[{'write': {'polowa.txt': 'niegotowe'}, 'fail': LIMIT_MESSAGE,
                    'set_limits': {'codex': exhausted()}},
                   {'lgtm': True}],
            claude=[{'write': {'ok.txt': 'ok'}, 'lgtm': True}])
        project_id = self.start()
        self.wait_phase(project_id, 'waiting_partner')
        project = self.store.project(project_id)
        git = Git(project['worktree'])
        self.assertIn('[niedokończona]', git.run('log', '--format=%s'))
        self.assertTrue((pathlib.Path(project['worktree']) / 'polowa.txt').exists())
        self.assertIn('takeover', self.kinds(project_id))
        takeover = next(c for c in self.calls() if c['agent'] == 'claude')
        self.assertIn('stracił dostęp', takeover['prompt'])
        self.assertIn('Zbuduj ok.txt', takeover['prompt'])
        with self.store._db() as db:
            db.execute('DELETE FROM blocks')
        self.set_limits(codex=FRESH)
        self.wait_status(project_id, 'done')
        self.assertEqual(self.calls()[-1]['agent'], 'codex')

    def test_both_limited_waits_without_calling_any_model(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}, {'lgtm': True}], claude=[{'lgtm': True}],
                      claude_limits=exhausted(), codex_limits=exhausted())
        project_id = self.start()
        self.wait_phase(project_id, 'waiting_limits')
        time.sleep(0.5)
        self.assertEqual(self.calls(), [])
        self.assertIn('waiting', self.kinds(project_id))
        self.set_limits(claude=FRESH, codex=FRESH)
        self.wait_status(project_id, 'done')

    def test_stop_recorded_in_the_store_is_obeyed_even_if_the_signal_was_lost(self):
        # PR17/26: "stop now" reached the engine while it was starting, Duet lost it and began a turn.
        self.scenario(claude_limits=exhausted(), codex_limits=exhausted())
        project_id = self.start()
        self.wait_phase(project_id, 'waiting_limits')
        self.store.update_project(project_id, status='stopping', stop_requested='immediate')  # no signal sent
        self.wait_status(project_id, 'stopped')
        self.assertEqual(self.calls(), [])

    def test_stop_during_wait_and_reset_does_not_resume_it(self):
        self.scenario(claude_limits=exhausted(), codex_limits=exhausted())
        project_id = self.start()
        self.wait_phase(project_id, 'waiting_limits')
        self.supervisor.stop(project_id)
        self.wait_status(project_id, 'stopped')
        self.set_limits(claude=FRESH, codex=FRESH)
        for _ in range(10):
            self.supervisor.tick()
            time.sleep(0.05)
        self.assertEqual(self.store.project(project_id)['status'], 'stopped')
        self.assertEqual(self.calls(), [])

    def test_solo_does_not_burn_turns_when_nothing_changes(self):
        self.scenario(claude=[{'write': {'ok.txt': 'ok'}}, {}, {}, {}],
                      codex_limits=exhausted())
        project_id = self.start()
        self.wait_phase(project_id, 'waiting_partner')
        self.assertEqual(len(self.calls()), 2)

    def test_solo_keeps_working_after_review_that_requests_changes(self):
        self.scenario(claude=[{'status': 'requesting-changes'}, {'write': {'ok.txt': 'ok'},
                                                                 'lgtm': True}],
                      codex_limits=exhausted())
        project_id = self.start()
        self.wait_phase(project_id, 'waiting_partner')
        self.assertEqual(len(self.calls()), 2)
        self.assertEqual(self.store.latest_version(project_id)['number'], 1)

    def test_transient_error_retries_same_model(self):
        self.scenario(codex=[{'fail': 'stream disconnected: 503'},
                             {'write': {'ok.txt': 'ok'}}, {'lgtm': True}],
                      claude=[{'lgtm': True}])
        project_id = self.start()
        self.wait_status(project_id, 'done')
        self.assertEqual([c['agent'] for c in self.calls()][:2], ['codex', 'codex'])
        self.assertNotIn('takeover', self.kinds(project_id))

    def test_auth_failure_is_not_mistaken_for_limit(self):
        self.scenario(codex=[{'fail': 'Session expired. Please run /login'}],
                      claude=[{'write': {'ok.txt': 'ok'}, 'lgtm': True}])
        project_id = self.start()
        self.wait_phase(project_id, 'waiting_partner')
        self.assertEqual(self.store.block('codex')['reason'], 'wymaga ponownego logowania')

    def test_accept_without_partner(self):
        self.scenario(claude=[{'write': {'ok.txt': 'ok'}, 'lgtm': True}],
                      codex_limits=exhausted())
        project_id = self.start()
        self.wait_phase(project_id, 'waiting_partner')
        self.supervisor.accept(project_id)
        self.wait_status(project_id, 'done')
        self.assertEqual(self.store.latest_version(project_id)['level'], 'tested')


class FullPower(Base):
    def setUp(self):
        super().setUp()
        self.store.set_setting('full_power', 1)

    def test_same_model_reviews_in_fresh_session_instead_of_waiting(self):
        self.scenario(claude=[{'write': {'ok.txt': 'ok'}, 'lgtm': True}, {'lgtm': True}],
                      codex=[{'lgtm': True}], codex_limits=exhausted())
        project_id = self.start()
        self.wait_phase(project_id, 'waiting_partner')
        review = self.calls()[1]
        self.assertEqual(review['agent'], 'claude')
        self.assertFalse(review['resumed'])
        self.assertIn('Full Power', review['prompt'])
        self.assertIn('Zbuduj ok.txt', review['prompt'])
        version = self.store.latest_version(project_id)
        self.assertEqual(version['level'], 'self_reviewed')
        self.assertEqual(version['accepted_by'], ['claude'])
        self.assertEqual(self.store.project(project_id)['status'], 'running')
        self.set_limits(codex=FRESH)
        self.wait_status(project_id, 'done')
        self.assertEqual(self.store.latest_version(project_id)['level'], 'approved')

    def test_review_that_improves_code_is_reviewed_again(self):
        self.scenario(claude=[{'write': {'ok.txt': 'ok'}, 'lgtm': True},
                              {'write': {'lepsze.txt': '1'}, 'lgtm': True}, {'lgtm': True}],
                      codex_limits=exhausted())
        project_id = self.start()
        self.wait_phase(project_id, 'waiting_partner')
        self.assertEqual(len(self.calls()), 3)
        self.assertEqual(self.store.latest_version(project_id)['number'], 2)

    def test_refinement_rounds_are_bounded(self):
        polishing = [{'write': {f'p{i}.txt': 'x'}, 'lgtm': True} for i in range(12)]
        self.scenario(claude=[{'write': {'ok.txt': 'ok'}, 'lgtm': True}, *polishing],
                      codex_limits=exhausted())
        project_id = self.start(turns=20)
        self.wait_phase(project_id, 'waiting_partner')
        self.assertEqual(len(self.calls()), 6)

    def test_ignores_reserve_threshold(self):
        almost = {'five_hour': 97, 'seven_day': 20}
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}, {'lgtm': True}], claude=[{'lgtm': True}],
                      claude_limits=almost, codex_limits=almost)
        project_id = self.start()
        self.wait_status(project_id, 'done')
        self.assertEqual([c['agent'] for c in self.calls()], ['codex', 'claude', 'codex'])

    def test_can_be_switched_on_while_waiting(self):
        self.store.set_setting('full_power', 0)
        self.scenario(claude=[{'write': {'ok.txt': 'ok'}, 'lgtm': True}, {'lgtm': True}],
                      codex_limits=exhausted())
        project_id = self.start()
        self.wait_phase(project_id, 'waiting_partner')
        self.assertEqual(len(self.calls()), 1)
        self.store.set_setting('full_power', 1)
        self.wait_for(lambda: len(self.calls()) == 2, what='przegląd po włączeniu')

    def test_off_by_default_keeps_waiting(self):
        self.store.set_setting('full_power', 0)
        self.scenario(claude=[{'write': {'ok.txt': 'ok'}, 'lgtm': True}, {'lgtm': True}],
                      codex_limits=exhausted())
        project_id = self.start()
        self.wait_phase(project_id, 'waiting_partner')
        time.sleep(1)
        self.assertEqual(len(self.calls()), 1)


class ModelChoice(Base):
    def flag(self, call, name):
        argv = call['argv']
        return argv[argv.index(name) + 1]

    def test_each_side_runs_chosen_model_and_thinking_level(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}, {'lgtm': True}], claude=[{'lgtm': True}])
        project_id = self.supervisor.create_project(
            task='Zbuduj', repo_path=str(self.repo), verify_cmd=VERIFY, claude_model='opus',
            claude_reasoning='xhigh', codex_model='gpt-test', codex_reasoning='ultra')['id']
        self.wait_status(project_id, 'done')
        codex, claude = self.calls()[0], self.calls()[1]
        self.assertEqual(self.flag(codex, '--model'), 'gpt-test')
        self.assertIn('model_reasoning_effort=ultra', codex['argv'])
        self.assertEqual(self.flag(claude, '--model'), 'opus')
        self.assertEqual(self.flag(claude, '--effort'), 'xhigh')

    def test_change_applies_from_next_turn_of_running_project(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}, 'sleep': 1}, {'lgtm': True}],
                      claude=[{'lgtm': True}])
        project_id = self.start()
        self.wait_for(lambda: self.calls(), what='start agenta')
        self.supervisor.set_models(project_id, claude_model='haiku', claude_reasoning='low',
                                   codex_reasoning='max')
        self.wait_status(project_id, 'done')
        codex_first, claude, codex_next = self.calls()
        self.assertEqual(self.flag(claude, '--model'), 'haiku')
        self.assertEqual(self.flag(claude, '--effort'), 'low')
        self.assertIn('model_reasoning_effort=high', codex_first['argv'])
        self.assertEqual(self.store.project(project_id)['codex_model'], 'gpt-6.1-sol')
        self.assertIn('model_reasoning_effort=max', codex_next['argv'])

    def test_resume_after_ultra_level_works(self):
        self.scenario(codex=[{'sleep': 60}, {'write': {'ok.txt': 'ok'}}, {'lgtm': True}],
                      claude=[{}, {'lgtm': True}])
        project_id = self.supervisor.create_project(
            task='Zbuduj', repo_path=str(self.repo), verify_cmd=VERIFY,
            codex_reasoning='ultra')['id']
        self.wait_for(lambda: self.calls(), what='start agenta')
        self.supervisor.stop(project_id, immediate=True)
        self.wait_status(project_id, 'stopped', timeout=15)
        self.supervisor.resume(project_id)
        self.wait_status(project_id, 'done')

    def test_rejects_unsafe_choice(self):
        with self.assertRaises(ValueError):
            self.supervisor.create_project(task='x', claude_model='sonnet; rm -rf /')

    def test_catalog_lists_both_sides_from_real_sources(self):
        self.scenario()
        data = catalog.read(force=True)
        self.assertEqual([m['id'] for m in data['codex']], ['gpt-test'])
        self.assertEqual(data['codex'][0]['efforts'], ['low', 'ultra'])
        self.assertIn('sonnet', [m['id'] for m in data['claude']])


class SingleModel(Base):
    def test_one_model_does_all_the_work_and_its_acceptance_is_marked_apart(self):
        self.scenario(claude=[{'write': {'ok.txt': 'ok'}}, {'lgtm': True}])
        project_id = self.supervisor.create_project(task='Zbuduj ok.txt', repo_path=str(self.repo),
                                                    verify_cmd=VERIFY, codex_model='none')['id']
        self.wait_status(project_id, 'done')
        self.assertEqual([call['agent'] for call in self.calls()], ['claude', 'claude'])
        self.assertIn('Tryb jednego modelu', self.calls()[0]['prompt'])
        self.assertNotIn('handoff', self.kinds(project_id))
        self.assertEqual(self.store.latest_version(project_id)['level'], 'single')

    def test_switching_a_model_off_applies_after_the_current_turn(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}, 'sleep': 1}], claude=[{'lgtm': True}])
        project_id = self.start()
        self.wait_for(lambda: self.calls(), what='start agenta')
        self.supervisor.set_models(project_id, codex_model='none')
        self.wait_status(project_id, 'done')
        self.assertEqual([call['agent'] for call in self.calls()], ['codex', 'claude'])
        change = next(e for e in self.store.events(project_id) if e['kind'] == 'models')
        self.assertIn('Codex: wyłączony', change['text'])
        self.assertIn('Codex: off', change['text_en'])
        self.assertEqual(self.store.latest_version(project_id)['level'], 'approved')

    def test_at_least_one_model_must_stay_on(self):
        with self.assertRaises(ValueError):
            self.supervisor.create_project(task='x', claude_model='none', codex_model='none')
        project_id = self.supervisor.create_project(task='x', codex_model='none')['id']
        self.store.update_project(project_id, status='stopped')
        with self.assertRaises(ValueError):
            self.supervisor.set_models(project_id, claude_model='none')
        self.supervisor.set_models(project_id, claude_model='none', codex_model='gpt-test')
        self.assertEqual(self.store.project(project_id)['claude_model'], 'none')


class Roles(Base):
    def project(self, **roles):
        return self.supervisor.create_project(task='Zbuduj ok.txt', repo_path=str(self.repo),
                                              verify_cmd=VERIFY, **roles)['id']

    def test_architect_only_plans_and_the_general_model_does_the_rest(self):
        plan = json.dumps(Planning.PLAN)
        # The implementer marks its task done, which finishes stage F1: that change goes to review.
        finished = plan.replace('"status": "doing", "budget": 1', '"status": "done", "budget": 1')
        self.scenario(claude=[{'write': {'.sol83/plan.json': plan}, 'reply': 'PRACA: F1'},
                              {'write': {'.sol83/plan.json': plan.replace('Ozdoby', 'Eksport')}}],
                      codex=[{'write': {'ok.txt': 'ok', '.sol83/plan.json': finished}, 'reply': 'PRACA: F1.1'}, {'lgtm': True},
                             {'write': {'eksport.txt': '1'}}, {'lgtm': True}])
        project_id = self.project(claude_role='architect')
        self.wait_status(project_id, 'done')
        self.assertEqual([call['agent'] for call in self.calls()], ['claude', 'codex', 'codex'])
        self.assertIn('Twoja rola: Architekt', self.calls()[0]['prompt'])
        self.assertIn('Praca w tej turze: przegląd', self.calls()[2]['prompt'])
        self.assertEqual(self.store.latest_version(project_id)['level'], 'single')
        self.supervisor.add_note(project_id, 'Dodaj eksport', order=True)
        self.wait_status(project_id, 'done')
        self.assertEqual([call['agent'] for call in self.calls()][3:], ['claude', 'codex', 'codex'])

    def test_work_that_no_role_covers_is_refused(self):
        with self.assertRaises(ValueError) as caught:
            self.supervisor.create_project(task='x', claude_role='architect', codex_role='implementer')
        self.assertIn('przegląd', str(caught.exception))
        project_id = self.supervisor.create_project(task='x', claude_role='architect')['id']
        self.store.update_project(project_id, status='stopped')
        with self.assertRaises(ValueError):
            self.supervisor.set_models(project_id, codex_model='none')
        with self.assertRaises(ValueError):
            self.supervisor.set_models(project_id, codex_role='tester')
        self.supervisor.set_models(project_id, codex_role='implementer', claude_role='general')
        self.assertIn('Claude: Ogólna; Codex: Implementujący; Gemini: Ogólna', self.store.events(project_id)[0]['text'])

    def test_unavailable_specialist_waits_or_a_general_model_takes_over(self):
        self.scenario(codex=[{'write': {'.sol83/plan.json': json.dumps(Planning.PLAN), 'ok.txt': 'ok'}},
                             {'lgtm': True}], claude_limits=exhausted())
        project_id = self.project(claude_role='architect', role_fallback='wait')
        self.wait_phase(project_id, 'waiting_role')
        self.assertEqual(self.calls(), [])
        self.supervisor.set_models(project_id, role_fallback='general')
        self.wait_status(project_id, 'done')
        self.assertEqual([call['agent'] for call in self.calls()], ['codex', 'codex'])


class WaitsAndPauses(Base):
    """2026-11-08: projects waited "for a model with the needed role" until 03:29 while Claude's limit had
    reset at 03:00. The panel must name the model, the cause and the time, and say when the time is a guess."""

    def test_usage_minute_gets_a_grace_minute(self):
        # /usage showed "2:59am" while the provider's own resetsAt was 03:00:00: a turn started at 02:59 failed.
        now = time.mktime((2026, 11, 8, 2, 50, 0, 0, 0, -1))
        parsed = limits.parse_claude_usage('Current session: 100% used · resets 2:59am (Europe/Warsaw)\n', now)
        reset = parsed['windows']['five_hour']['resets_at']
        self.assertEqual(time.strftime('%H:%M:%S', time.localtime(reset)), '03:00:00')

    def test_rejection_uses_the_provider_reset_and_a_guess_is_marked(self):
        now = time.time()
        self.scenario(claude_limits={'five_hour': {'used': 100, 'resets_at': now - 120}, 'seven_day': 13})
        event = {'provider': 'claude', 'read_at': now, 'windows': {}, 'status': 'rejected', 'overage': True}
        (STATE / 'limits-claude.json').write_text(json.dumps({**event, 'resets_at': now + 600}))
        found = limits.availability(limits.read_claude(), 80.0)
        self.assertFalse(found.available)
        self.assertAlmostEqual(found.until, now + 600, delta=2)
        self.assertFalse(found.estimate)
        (STATE / 'limits-claude.json').write_text(json.dumps(event))
        guess = limits.availability(limits.read_claude(), 80.0)
        self.assertTrue(guess.estimate)
        self.assertAlmostEqual(guess.until - time.time(), limits.UNKNOWN_RESET_S, delta=5)

    def test_review_waits_for_the_reviewer_back_first(self):
        # Codex (first in order) is back in two days, Claude tonight: the wait shows Claude's time.
        now = time.time()
        avail = [limits.Availability(False, now + 2 * 86400, 'tydzień'),
                 limits.Availability(False, now + 1800, '5h', estimate=True),
                 limits.Availability(True)]
        choice = limits.choose_among([0, 1, 2], avail, [False, False, True])
        self.assertEqual((choice.mode, choice.waiting_for, choice.until), ('waiting_partner', 1, now + 1800))

    def test_overage_rejection_blocks_until_the_provider_reset_not_half_an_hour(self):
        reset = time.time() + 1500
        self.scenario(claude=[{'overage': True, 'limit_status': 'rejected', 'limit_resets_at': reset}],
                      codex=[{'write': {'ok.txt': 'ok'}}],
                      claude_limits={'five_hour': {'used': 100, 'resets_at': time.time() - 120}, 'seven_day': 13})
        project_id = self.start()
        self.wait_for(lambda: 'takeover' in self.kinds(project_id), timeout=40, what='przejęcie po limicie Claude')
        block = self.store.block('claude')
        self.assertAlmostEqual(block['until'], reset, delta=5)
        self.assertEqual(block['source'], 'reading')
        takeover = next(e for e in self.store.events(project_id) if e['kind'] == 'takeover')
        self.assertEqual(takeover['data']['reset_source'], 'reading')

    def test_role_wait_names_the_model_cause_and_time(self):
        self.scenario(codex=[{'write': {'.sol83/plan.json': json.dumps(Planning.PLAN), 'ok.txt': 'ok'}}],
                      claude_limits=exhausted(1800))
        project_id = self.supervisor.create_project(task='Zbuduj ok.txt', repo_path=str(self.repo), verify_cmd=VERIFY,
                                                    claude_role='architect', codex_role='implementer,tester')['id']
        self.wait_phase(project_id, 'waiting_role')
        self.assertEqual(self.calls(), [])
        live = self.store.live(project_id)
        self.assertIn('Pracę „plan” może wykonać tylko Claude', live['reason'])
        self.assertIn('Claude: limit 5h 100%, do ', live['reason'])
        self.assertIn('Codex: nie ma roli do pracy „plan”', live['reason'])
        self.assertNotIn('szacunek', live['reason'])
        self.assertIn('Only Claude can do the work "planning"', live['reason_en'])
        sides = {row['side']: row for row in json.loads(live['detail'])['sides']}
        self.assertEqual((sides['claude']['state'], sides['claude']['estimate'], sides['codex']['state']),
                         ('limit', False, 'role'))
        self.assertAlmostEqual(sides['claude']['until'], live['until'], delta=61)

    def test_try_now_lifts_a_guessed_pause_and_the_project_continues(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}, {'lgtm': True}], claude=[{'lgtm': True}])
        for side in ('claude', 'codex'):
            self.store.set_block(side, time.time() + 3600, Msg('provider_limit'), 'estimate')
        project_id = self.start()
        self.wait_phase(project_id, 'waiting_limits')
        self.assertIn('(szacunek', self.store.live(project_id)['reason'])
        self.assertEqual(self.calls(), [])
        self.assertTrue(self.supervisor.retry_now('codex')['lifted'])
        self.assertFalse(self.supervisor.retry_now('codex')['lifted'], 'nothing left to lift')
        self.wait_for(lambda: self.calls(), what='tura Codexa po „Spróbuj teraz”')
        self.assertEqual(self.calls()[0]['agent'], 'codex')
        self.assertIn('note', self.kinds(project_id))
        self.assertTrue(any('Spróbuj teraz' in e['text'] for e in self.store.events(project_id)))

    def test_waiting_wakes_at_once_on_try_now(self):
        import types
        from gemini_app.scheduler import GeminiScheduler
        self.scenario()
        project_id = self.supervisor.create_project(task='x', repo_path=str(self.repo))['id']
        cfg = types.SimpleNamespace(agents=[types.SimpleNamespace(name='claude'), types.SimpleNamespace(name='codex')],
                                    cwd=str(self.repo), task='x')
        scheduler = GeminiScheduler(cfg, pathlib.Path(tempfile.mkdtemp(dir=TEMP)), self.store, project_id)
        stop = types.SimpleNamespace(requested=False)
        threading.Timer(0.5, lambda: self.store.set_setting('retry_now', time.time())).start()
        started = time.monotonic()
        self.assertTrue(scheduler._wait(60, stop))
        self.assertLess(time.monotonic() - started, 5)


class ReviewCadence(Base):
    """2026-11-08 audit: a review after every implementation turn was half of all turns (PR9/26) and 76% of
    the tokens (PR14/26). A change is reviewed when its stage of the plan is finished, or after
    REVIEW_EVERY implementation turns in a row, or at once on a claim of done."""

    @staticmethod
    def plan(done=()):
        tasks = {'F1': ('F1.1', 'F1.2'), 'F2': ('F2.1', 'F2.2', 'F2.3', 'F2.4')}
        items = []
        for feature, children in tasks.items():
            items.append({'id': feature, 'title': feature, 'kind': 'feature', 'priority': 'must', 'status': 'todo'})
            items += [{'id': task, 'title': task, 'kind': 'task', 'parent': feature, 'priority': 'must',
                       'status': 'done' if task in done else 'todo', 'budget': 2} for task in children]
        return json.dumps({'architecture': 'Pliki tekstowe.', 'run': 'cat a.txt', 'items': items})

    def step(self, item, *done):
        return {'write': {f'{item}.txt': item, '.sol83/plan.json': self.plan(done)}, 'reply': f'PRACA: {item}'}

    def works(self, project_id):
        return [e['data']['work'] for e in reversed(self.store.events(project_id)) if e['kind'] == 'turn_start']

    def test_review_after_a_finished_stage_or_three_turns(self):
        self.scenario(codex=[{'write': {'.sol83/plan.json': self.plan()}, 'reply': 'PRACA: F1'},
                             self.step('F1.2', 'F1.1', 'F1.2'), self.step('F2.1', 'F1.1', 'F1.2', 'F2.1'),
                             self.step('F2.3', 'F1.1', 'F1.2', 'F2.1', 'F2.2', 'F2.3')],
                      claude=[self.step('F1.1', 'F1.1'), {'reply': 'Przegląd: etap F1 w porządku.'},
                              self.step('F2.2', 'F1.1', 'F1.2', 'F2.1', 'F2.2'), {'reply': 'Przegląd F2.1-F2.3.'}])
        project_id = self.start(verify='', turns=20)
        self.wait_for(lambda: len(self.works(project_id)) >= 8, timeout=60, what='osiem tur')
        self.supervisor.stop(project_id, immediate=True)
        self.assertEqual(self.works(project_id)[:8], ['plan', 'implement', 'implement', 'review',
                                                      'implement', 'implement', 'implement', 'review'])

    def test_every_change_is_reviewed_when_the_project_asks_for_it(self):
        self.scenario(codex=[{'write': {'.sol83/plan.json': self.plan()}, 'reply': 'PRACA: F1'}],
                      claude=[self.step('F1.1', 'F1.1')])
        project_id = self.start(verify='', turns=20)
        self.supervisor.set_options(project_id, review_mode='each')
        self.wait_for(lambda: len(self.works(project_id)) >= 3, timeout=60, what='trzy tury')
        self.supervisor.stop(project_id, immediate=True)
        self.assertEqual(self.works(project_id)[:3], ['plan', 'implement', 'review'])


class FailureFlow(Base):
    """PR9/26 on 2026-11-08: Gemini failed six times on a resumed broken session, each failure forced a turn on
    Claude, which had already accepted the same code, and the project halted for "6 turns without a change"."""

    def test_a_model_that_accepted_the_code_gets_no_empty_turn_after_a_failure(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}, {'fail': 'unexpected crash in the agent'}],
                      claude=[{'lgtm': True}, {'reply': 'nie powinienem dostać tej tury'}])
        project_id = self.start()
        self.wait_phase(project_id, 'waiting_partner')
        self.assertEqual([c['agent'] for c in self.calls()], ['codex', 'claude', 'codex'])
        takeover = next(e for e in self.store.events(project_id) if e['kind'] == 'takeover')
        self.assertIn('nie dostają pustej tury', takeover['text'])
        self.assertEqual(self.store.block('codex')['source'], 'failure')

    def test_an_accepted_model_waits_only_for_a_partner_back_soon(self):
        now = time.time()
        soon = [limits.Availability(True), limits.Availability(False, now + 600, 'błąd agenta')]
        away = [limits.Availability(True), limits.Availability(False, now + 2 * 86400, 'limit tygodniowy')]
        self.assertEqual(limits.choose_among([0, 1], soon, [True, False]).mode, 'waiting_partner')
        self.assertEqual(limits.choose_among([0, 1], away, [True, False]).speaker, 0)

    def test_repeated_failures_of_one_provider_get_growing_pauses(self):
        self.assertEqual([limits.failure_pause('other', n) for n in (1, 2, 3, 4, 5)],
                         [600, 1200, 2400, 4800, 7200])
        self.assertEqual(limits.failure_pause('transient', 1), limits.TRANSIENT_BLOCK_S)

    def test_document_projects_get_document_rules_and_apps_do_not(self):
        from gemini_app import prompts
        self.assertEqual(prompts.project_kind({'title': 'MC TAF vs VISA DAF', 'task': 'Przygotuj kompendium / handbook'}),
                         'document')
        self.assertEqual(prompts.project_kind({'title': 'Gra', 'task': 'Zbuduj grę RTS', 'project_kind': 'auto'}), 'app')
        self.assertEqual(prompts.project_kind({'title': 'Gra', 'task': 'handbook', 'project_kind': 'app'}), 'app')
        self.scenario(codex=[{'reply': 'plan'}], claude=[{'reply': 'x'}])
        project_id = self.supervisor.create_project(task='Przygotuj handbook o płatnościach agentowych',
                                                    repo_path=str(self.repo))['id']
        self.wait_for(lambda: self.calls(), what='pierwsza tura')
        self.supervisor.stop(project_id, immediate=True)
        self.assertIn('To projekt dokumentu lub researchu', self.calls()[0]['prompt'])
        self.assertIn('Pracuj oszczędnie', self.calls()[0]['prompt'])


class ThreeModels(Base):
    def project(self, **choices):
        return self.supervisor.create_project(task='Zbuduj ok.txt', repo_path=str(self.repo), verify_cmd=VERIFY,
                                              gemini_model='gemini-3-pro', **choices)['id']

    def test_three_models_take_turns_and_two_acceptances_end_the_work(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}], gemini=[{'lgtm': True}], claude=[{'lgtm': True}])
        project_id = self.project()
        self.wait_status(project_id, 'done')
        self.assertEqual([call['agent'] for call in self.calls()], ['codex', 'gemini', 'claude'])
        gemini = self.calls()[1]
        self.assertEqual(self.flag(gemini, '--model'), 'gemini-3-pro')
        self.assertNotIn('--effort', gemini['argv'])
        self.assertIn('Pozostałe modele: Claude i Codex', gemini['prompt'])
        self.assertEqual(self.store.latest_version(project_id)['level'], 'approved')

    def test_roles_spread_over_three_models(self):
        plan = json.dumps(Planning.PLAN)
        self.scenario(claude=[{'write': {'.sol83/plan.json': plan}}], codex=[{'write': {'ok.txt': 'ok'}}],
                      gemini=[{'lgtm': True}])
        project_id = self.project(claude_role='architect', codex_role='implementer', gemini_role='tester')
        self.wait_status(project_id, 'done')
        self.assertEqual([call['agent'] for call in self.calls()], ['claude', 'codex', 'gemini'])
        self.assertIn('Role w zespole: Claude: Architekt, Codex: Implementujący, Gemini: Tester',
                      self.calls()[0]['prompt'])
        self.assertIn('Twoja rola: Tester', self.calls()[2]['prompt'])
        self.assertEqual(self.store.latest_version(project_id)['level'], 'approved')

    def test_gemini_limit_error_pauses_it_without_a_reading(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}, {'lgtm': True}],
                      gemini=[{'fail': '429 RESOURCE_EXHAUSTED: Quota exceeded for this model.'}],
                      claude=[{'lgtm': True}])
        project_id = self.project()
        self.wait_status(project_id, 'done')
        self.assertEqual([call['agent'] for call in self.calls()], ['codex', 'gemini', 'claude', 'codex'])
        block = self.store.block('gemini')
        self.assertAlmostEqual(block['until'] - time.time(), limits.UNKNOWN_RESET_S, delta=120)
        self.assertEqual(self.store.setting('strikes_gemini', 0), 1)
        takeover = next(e for e in self.store.events(project_id) if e['kind'] == 'takeover')
        self.assertIn('Claude przejmuje', takeover['text'])

    def adapter(self, *args):
        env = {**os.environ, 'GEMINI_API_KEY': 'klucz'}
        done = subprocess.run([str(ROOT / 'bin/gemini'), *args], capture_output=True, text=True, env=env,
                              cwd=self.repo, timeout=30)
        return done, self.calls()[-1] if self.calls() else None

    def test_antigravity_runs_the_turn_in_its_sandbox_without_an_api_key(self):
        self.scenario(gemini=[{'reply': 'wynik'}, {'reply': 'dalej'}, {'reply': 'odpowiedź'},
                              {'reply': 'przez terminal', 'tty_only': True}])
        done, turn = self.adapter('-p', 'zadanie', '--output-format', 'json', '--approval-mode', 'auto_edit',
                                  '--model', 'gemini-3-pro', '--effort', 'high')
        reply = json.loads(done.stdout)
        self.assertIn('wynik', reply['response'])
        self.assertEqual(turn['api_key'], False)
        self.assertEqual((self.flag(turn, '--mode'), self.flag(turn, '--add-dir'), self.flag(turn, '--model')),
                         ('accept-edits', str(self.repo.resolve()), 'gemini-3-pro'))
        self.assertNotIn('--effort', turn['argv'])
        self.assertIn('--sandbox', turn['argv'])
        self.assertIn('--dangerously-skip-permissions', turn['argv'])
        _, resumed = self.adapter('-p', 'dalej', '--output-format', 'json', '--approval-mode', 'auto_edit',
                                  '--resume', reply['session_id'], '--model', 'default', '--effort', 'xhigh')
        self.assertEqual(self.flag(resumed, '--conversation'), reply['session_id'])
        self.assertNotIn('--model', resumed['argv'])
        self.assertEqual(self.flag(resumed, '--effort'), 'xhigh')
        _, question = self.adapter('-p', 'pytanie', '--output-format', 'json', '--approval-mode', 'plan')
        self.assertEqual(self.flag(question, '--mode'), 'plan')
        self.assertNotIn('--sandbox', question['argv'])
        done, _ = self.adapter('-p', 'cicho', '--output-format', 'json', '--approval-mode', 'auto_edit')
        self.assertIn('przez terminal', json.loads(done.stdout)['response'])
        self.assertIsNone(limits.check_auth(['gemini']))
        models = catalog.read(force=True)['gemini']
        self.assertEqual([(m['id'], m['label']) for m in models[1:]],
                         [('gemini-4-argon-high', 'Gemini 4 Argon (High)'), ('gemini-3.8-flash-low', 'Gemini 3.8 Flash (Low)')])

    def test_resume_after_a_gemini_turn_works_and_a_failed_launch_is_not_done(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}], gemini=[{'lgtm': True}], claude=[{'lgtm': True}])
        project_id = self.project()
        self.wait_status(project_id, 'done')
        self.scenario(codex=[{'write': {'b.txt': '1'}}], gemini=[{'lgtm': True}], claude=[{'lgtm': True}])
        self.supervisor.add_note(project_id, 'Dodaj b.txt', order=True)
        self.wait_status(project_id, 'done')
        self.assertTrue(any('Dodaj b.txt' in call['prompt'] for call in self.calls()))
        run = self.store.project(project_id)['run_dir']
        state = json.loads((pathlib.Path(run) / 'state.json').read_text())
        self.assertFalse(any(agent.get('extra_args') for agent in state['agents']))
        state['agents'][0]['extra_args'] = ['--effort', 'high']
        (pathlib.Path(run) / 'state.json').write_text(json.dumps(state))
        self.scenario(codex=[{'write': {'c.txt': '1'}}], gemini=[{'lgtm': True}], claude=[{'lgtm': True}])
        self.supervisor.add_note(project_id, 'Dodaj c.txt', order=True)
        self.wait_status(project_id, 'done')
        self.assertTrue(any('Dodaj c.txt' in call['prompt'] for call in self.calls()))
        meta = self.store.meta(project_id)
        meta['launched_after'] = self.store.project(project_id)['run_dir']
        self.store.save_meta(project_id, meta)
        self.store.update_project(project_id, status='running')
        self.supervisor._finish(self.store.project(project_id))
        self.assertEqual(self.store.project(project_id)['status'], 'attention')

    def older(self, **choices):
        """A project as created before Gemini: two agents in its engine, no Gemini settings."""
        project_id = self.supervisor.create_project(task='Zbuduj ok.txt', repo_path=str(self.repo),
                                                    verify_cmd=VERIFY, **choices)['id']
        self.store.save_meta(project_id, {})
        with self.store._db() as db:
            db.execute('UPDATE projects SET gemini_model=NULL WHERE id=?', (project_id,))
        return project_id

    def engine_agents(self, project_id):
        return [agent['name'] for agent in
                json.loads((pathlib.Path(os.environ['GEMINI_HOME']) / f'config/run-{project_id}.json').read_text())['agents']]

    def test_older_project_shows_gemini_off_and_adds_it_on_the_next_run(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}, {'lgtm': True}], claude=[{'lgtm': True}])
        project_id = self.older()
        self.wait_status(project_id, 'done')
        self.assertEqual(self.engine_agents(project_id), ['claude', 'codex'])
        self.supervisor.set_models(project_id, gemini_model='gemini-4-argon-high', confirm_top='gemini-4-argon-high')
        self.assertEqual(self.supervisor.sides(self.store.project(project_id)), ['claude', 'codex', 'gemini'])
        self.assertIn('Gemini dołączy przy następnym uruchomieniu', self.store.events(project_id)[0]['text'])
        self.scenario(gemini=[{'write': {'g.txt': '1'}, 'lgtm': True}], codex=[{'lgtm': True}],
                      claude=[{'lgtm': True}])
        self.supervisor.resume(project_id, note='Dodaj g.txt')
        self.wait_status(project_id, 'done')
        self.assertEqual(self.engine_agents(project_id), ['claude', 'codex', 'gemini'])
        gemini = next(call for call in self.calls() if call['agent'] == 'gemini')
        self.assertIn('Zbuduj ok.txt', gemini['prompt'])

    def test_switching_gemini_on_in_a_running_older_project_restarts_after_the_turn(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}, 'sleep': 1}], gemini=[{'lgtm': True}],
                      claude=[{'lgtm': True}])
        project_id = self.older()
        self.wait_for(lambda: self.calls(), what='start agenta')
        self.supervisor.set_models(project_id, gemini_model='default')
        self.assertEqual(self.store.project(project_id)['status'], 'stopping')
        self.wait_status(project_id, 'done')
        self.assertEqual([call['agent'] for call in self.calls()], ['codex', 'claude', 'gemini'])
        self.assertIn('dołączy po bieżącej turze', next(
            e['text'] for e in self.store.events(project_id) if 'dołączy' in e['text']))

    def flag(self, call, name):
        argv = call['argv']
        return argv[argv.index(name) + 1]


class ContentCreator(Base):
    @property
    def PLAN(self):
        return json.dumps(Planning.PLAN)

    def orders(self, *items):
        return json.dumps({'items': list(items)})

    def test_content_creator_makes_what_the_others_order_after_the_user_approves(self):
        # Spec 8.3: a model without the content role may propose an order, never approve or make it.
        order = {'id': 'A1', 'type': 'image', 'prompt': 'Logo z latarnią', 'path': 'assets/logo.png',
                 'size': '256x256', 'status': 'requested', 'why': 'ekran startowy'}
        self.scenario(codex=[{'write': {'.sol83/plan.json': self.PLAN, 'ok.txt': 'ok',
                                        '.sol83/assets.json': self.orders(order)}, 'lgtm': True},
                             {'lgtm': True}, {'lgtm': True}],
                      gemini=[{'write': {'assets/logo.png': 'PNG',
                                         '.sol83/assets.json': self.orders({**order, 'status': 'done'})}}])
        project_id = self.supervisor.create_project(
            task='Zbuduj ok.txt', repo_path=str(self.repo), verify_cmd=VERIFY, claude_model='none',
            gemini_model='default', gemini_role='content')['id']
        self.wait_status(project_id, 'done')
        self.assertNotIn('gemini', [call['agent'] for call in self.calls()])
        self.assertIn('zamawiaj w .sol83/assets.json', self.calls()[0]['prompt'])
        view = self.supervisor.detail(project_id)['assets']
        self.assertEqual([(row['id'], row['status'], row['by']) for row in view], [('A1', 'proposed', 'codex')])
        self.assertTrue(any(e['kind'] == 'asset' and 'A1' in e['text'] for e in self.store.events(project_id)))
        with self.assertRaises(ValueError):
            self.supervisor.decide_asset(project_id, 'A9', 'approve')
        self.supervisor.decide_asset(project_id, 'A1', 'approve')
        self.wait_status(project_id, 'done', timeout=60)
        agents = [call['agent'] for call in self.calls()]
        self.assertIn('gemini', agents)
        gemini = next(call['prompt'] for call in self.calls() if call['agent'] == 'gemini')
        self.assertIn('Twoja rola: Twórca treści', gemini)
        self.assertIn('generate_image', gemini)
        self.assertIn('A1 (image): Logo z latarnią -> assets/logo.png, 256x256', gemini)
        view = self.supervisor.detail(project_id)['assets']
        self.assertEqual([(row['id'], row['status'], row['image']) for row in view], [('A1', 'done', True)])
        self.assertEqual(self.supervisor.asset_file(project_id, 'assets/logo.png').read_text(), 'PNG')
        for bad in ('../check.py', 'ok.txt', '/etc/hosts'):
            with self.assertRaises(LookupError):
                self.supervisor.asset_file(project_id, bad)

    def test_mandatory_content_keeps_the_scope_open(self):
        order = {'id': 'A1', 'type': 'text', 'prompt': 'Fabuła', 'path': 'story.md', 'status': 'requested',
                 'mandatory': True}
        self.scenario(codex=[{'write': {'ok.txt': 'ok', '.sol83/assets.json': self.orders(order)}, 'lgtm': True}],
                      claude=[{'lgtm': True}])
        project_id = self.start()
        self.wait_status(project_id, 'attention', timeout=60)
        self.assertIn('content:A1', self.supervisor.close_blockers(project_id))
        self.supervisor.decide_scope(project_id, 'content:A1', 'wydanie bez fabuły, uzgodnione')
        self.assertEqual(self.supervisor.close_blockers(project_id), [])

    def test_user_orders_content_in_the_panel(self):
        self.scenario(codex=[{'write': {'.sol83/plan.json': self.PLAN, 'ok.txt': 'ok'}}, {'lgtm': True}],
                      claude=[{'lgtm': True}])
        project_id = self.supervisor.create_project(task='Zbuduj ok.txt', repo_path=str(self.repo),
                                                    verify_cmd=VERIFY, gemini_model='default',
                                                    gemini_role='content')['id']
        self.wait_status(project_id, 'done')
        with self.assertRaises(ValueError):
            self.supervisor.order_asset(project_id, 'image', 'Logo', '../poza.png')
        before = len(self.calls())
        self.supervisor.order_asset(project_id, 'image', 'Logo z latarnią', 'assets/logo.png', '256x256')
        self.assertEqual(self.store.project(project_id)['status'], 'queued')
        done = {'id': 'U1', 'type': 'image', 'prompt': 'Logo z latarnią', 'path': 'assets/logo.png',
                'status': 'done', 'by': 'user'}
        self.scenario(gemini=[{'write': {'assets/logo.png': 'PNG', '.sol83/assets.json': self.orders(done)}}],
                      claude=[{'lgtm': True}], codex=[{'lgtm': True}])
        self.wait_status(project_id, 'done')
        gemini = self.calls()[before]
        self.assertEqual(gemini['agent'], 'gemini')
        self.assertIn('U1 (image): Logo z latarnią -> assets/logo.png, 256x256', gemini['prompt'])
        self.assertIn('Użytkownik zamówił treść', gemini['prompt'])
        self.assertEqual([(row['id'], row['status']) for row in self.supervisor.detail(project_id)['assets']],
                         [('U1', 'done')])


class GitHub(Base):
    def setUp(self):
        super().setUp()
        (TEMP / 'gh_logged_out').unlink(missing_ok=True)
        self.name = f'repo-{time.time_ns()}'

    def built(self, *steps):
        """A finished project whose codex turns are `steps`, ending with a passing version."""
        self.scenario(codex=[*steps, {'lgtm': True}], claude=[{'lgtm': True}] * len(steps))
        project_id = self.start()
        self.wait_status(project_id, 'done')
        return project_id

    def remote(self, ref, repo=None):
        return Git(TEMP / f"github/{repo or 'tester/' + self.name}.git").run('rev-parse', ref,
                                                                             check=False)

    def test_private_publish_sends_the_version_not_work_in_progress(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}, {'write': {'ok.txt': 'zepsute'}}],
                      claude=[{'write': {'wip.txt': 'x'}}])
        project_id = self.start(turns=3)
        self.wait_status(project_id, 'attention')
        version = self.store.version(project_id, 1)
        result = self.supervisor.publish(project_id, 1, name=self.name)
        self.assertEqual(result['url'], f'https://github.com/tester/{self.name}')
        self.assertEqual(self.remote('refs/heads/main'), version['commit_sha'])
        self.assertEqual(self.remote('refs/tags/v1'), version['commit_sha'])
        worktree_head = Git(self.store.project(project_id)['worktree']).head()
        self.assertNotEqual(worktree_head, version['commit_sha'])
        project = self.store.project(project_id)
        self.assertEqual((project['github_visibility'], project['github_version']), ('private', 1))

    def test_next_version_extends_the_same_repository(self):
        project_id = self.built({'write': {'ok.txt': 'ok'}})
        self.supervisor.publish(project_id, 1, name=self.name)
        self.scenario(claude=[{'write': {'nowe.txt': '1'}, 'lgtm': True}], codex=[{'lgtm': True}])
        self.supervisor.resume(project_id, note='Jeszcze jedno')
        self.wait_status(project_id, 'done')
        self.supervisor.publish(project_id, 2)
        self.assertEqual(self.remote('refs/heads/main'), self.store.version(project_id, 2)['commit_sha'])
        self.assertTrue(self.remote('refs/tags/v2'))

    def test_older_version_cannot_overwrite_newer_remote(self):
        project_id = self.built({'write': {'ok.txt': 'ok'}})
        self.supervisor.publish(project_id, 1, name=self.name)
        self.scenario(claude=[{'write': {'nowe.txt': '1'}, 'lgtm': True}], codex=[{'lgtm': True}])
        self.supervisor.resume(project_id, note='Jeszcze jedno')
        self.wait_status(project_id, 'done')
        self.supervisor.publish(project_id, 2)
        with self.assertRaises(RuntimeError):
            self.supervisor.publish(project_id, 1)
        self.assertEqual(self.remote('refs/heads/main'), self.store.version(project_id, 2)['commit_sha'])

    def test_every_push_needs_confirmation_of_found_secrets(self):
        # Spec 22.4: private pushes are scanned too (a private repository can be made public later).
        project_id = self.built({'write': {'ok.txt': 'ok', 'cfg.py': 'K="ghp_' + 'a' * 36 + '"'}})
        with self.assertRaises(RuntimeError) as caught:
            self.supervisor.publish(project_id, 1, name=self.name, visibility='public')
        self.assertIn('cfg.py', str(caught.exception))
        self.assertIn('secrets', caught.exception.args[0].en())
        self.assertFalse((TEMP / f'github/tester/{self.name}.git').exists())
        with self.assertRaises(RuntimeError) as caught:
            self.supervisor.publish(project_id, 1, name=self.name, visibility='private')
        self.assertFalse((TEMP / f'github/tester/{self.name}.git').exists())
        self.supervisor.publish(project_id, 1, name=self.name, visibility='private',
                                confirmed_secrets=caught.exception.token)
        self.assertTrue((TEMP / f'github/tester/{self.name}.git').exists())
        with self.assertRaises(RuntimeError):
            self.supervisor.change_visibility(project_id, 'public')

    def test_secret_removed_later_still_blocks_public(self):
        project_id = self.built({'write': {'ok.txt': 'ok', 'a.txt': 'sk-ant-' + 'b' * 30}},
                                {'write': {'ok.txt': 'ok', 'a.txt': 'czysto'}})
        latest = self.store.latest_version(project_id)['number']
        with self.assertRaises(RuntimeError):
            self.supervisor.publish(project_id, latest, name=self.name, visibility='public')

    def test_env_file_blocks_public_but_example_does_not(self):
        project_id = self.built({'write': {'ok.txt': 'ok', '.env.example': 'X=1'}})
        self.supervisor.publish(project_id, 1, name=self.name, visibility='public')
        self.assertEqual((TEMP / f'github/tester/{self.name}.git/visibility').read_text(), 'PUBLIC')
        self.assertEqual(self.store.project(project_id)['github_visibility'], 'public')

    def test_visibility_can_change_both_ways(self):
        project_id = self.built({'write': {'ok.txt': 'ok'}})
        self.supervisor.publish(project_id, 1, name=self.name)
        marker = TEMP / f'github/tester/{self.name}.git/visibility'
        self.supervisor.change_visibility(project_id, 'public')
        self.assertEqual(marker.read_text(), 'PUBLIC')
        self.supervisor.change_visibility(project_id, 'private')
        self.assertEqual(marker.read_text(), 'PRIVATE')

    def test_rejected_version_is_not_published(self):
        project_id = self.built({'write': {'ok.txt': 'ok'}})
        self.store.update_version(project_id, 1, user_verdict='bad')
        with self.assertRaises(ValueError):
            self.supervisor.publish(project_id, 1, name=self.name)

    def test_project_with_github_origin_gets_a_branch_never_main(self):
        bare = TEMP / f'github/tester/{self.name}.git'
        subprocess.run(['git', 'init', '-q', '--bare', str(bare)], check=True)
        (bare / 'visibility').write_text('PRIVATE')
        Git(self.repo).run('remote', 'add', 'origin', f'https://github.com/tester/{self.name}.git')
        project_id = self.built({'write': {'ok.txt': 'ok'}})
        self.supervisor.publish(project_id, 1)
        branch = self.store.project(project_id)['branch']
        self.assertTrue(self.remote(f'refs/heads/{branch}'))
        self.assertEqual(self.remote('refs/heads/main'), 'refs/heads/main')

    def seeded_remote(self, visibility='PRIVATE'):
        """An existing GitHub repository holding this test's source code."""
        bare = TEMP / f'github/tester/{self.name}.git'
        subprocess.run(['git', 'init', '-q', '--bare', str(bare)], check=True)
        (bare / 'visibility').write_text(visibility)
        Git(bare).run('symbolic-ref', 'HEAD', 'refs/heads/main')
        head = Git(self.repo).head()
        Git(self.repo).run('push', '-q', f'file://{bare}', f'{head}:refs/heads/main')
        return head

    def test_work_ordered_on_private_repository_lands_on_its_branch(self):
        main = self.seeded_remote()
        repos = self.supervisor.github_repos()
        self.assertIn(f'tester/{self.name}', [r['nameWithOwner'] for r in repos])
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}, {'lgtm': True}], claude=[{'lgtm': True}])
        project_id = self.supervisor.create_project(task='Popraw', github_repo=f'tester/{self.name}',
                                                    verify_cmd=VERIFY)['id']
        self.wait_status(project_id, 'done')
        self.supervisor.tick()
        project = self.store.project(project_id)
        self.assertEqual(project['base_commit'], main)
        self.assertEqual(self.remote('refs/heads/main'), main)
        version = self.store.latest_version(project_id)
        self.assertEqual(self.remote(f"refs/heads/{project['branch']}"), version['commit_sha'])
        self.assertEqual(project['github_version'], version['number'])

    def test_second_project_on_same_repository_reuses_clone_and_sees_new_commits(self):
        self.seeded_remote()
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}, {'lgtm': True}], claude=[{'lgtm': True}])
        first = self.supervisor.create_project(task='A', github_repo=f'tester/{self.name}',
                                               verify_cmd=VERIFY)['id']
        self.wait_status(first, 'done')
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}, {'lgtm': True}], claude=[{'lgtm': True}])
        second = self.supervisor.create_project(task='B', github_repo=f'tester/{self.name}',
                                                verify_cmd=VERIFY)['id']
        self.wait_status(second, 'done')
        self.assertEqual(self.store.project(first)['repo_path'], self.store.project(second)['repo_path'])

    def test_public_repository_never_receives_versions_on_its_own(self):
        self.seeded_remote('PUBLIC')
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}, {'lgtm': True}], claude=[{'lgtm': True}])
        project_id = self.supervisor.create_project(task='Popraw', github_repo=f'tester/{self.name}',
                                                    verify_cmd=VERIFY)['id']
        self.wait_status(project_id, 'done')
        self.supervisor.tick()
        project = self.store.project(project_id)
        self.assertEqual(project['github_auto'], 0)
        self.assertEqual(self.remote(f"refs/heads/{project['branch']}"), f"refs/heads/{project['branch']}")

    def test_failed_automatic_upload_is_reported_once(self):
        project_id = self.built({'write': {'ok.txt': 'ok'}})
        self.supervisor.publish(project_id, 1, name=self.name)
        self.store.update_project(project_id, github_auto=1, github_version=0)
        (TEMP / 'gh_logged_out').write_text('')
        for _ in range(3):
            self.supervisor.tick()
        failures = [e for e in self.store.events(project_id) if e['kind'] == 'attention']
        self.assertEqual(len(failures), 1)
        self.assertIn('gh auth login', failures[0]['text'])
        self.store.update_project(project_id, github_auto=0)

    def test_bad_repository_name_is_refused(self):
        with self.assertRaises(ValueError):
            self.supervisor.create_project(task='x', github_repo='nie repo')

    def test_clear_message_when_not_logged_in(self):
        project_id = self.built({'write': {'ok.txt': 'ok'}})
        (TEMP / 'gh_logged_out').write_text('')
        with self.assertRaises(RuntimeError) as caught:
            self.supervisor.publish(project_id, 1, name=self.name)
        self.assertIn('gh auth login', str(caught.exception))

    def test_bad_name_is_refused(self):
        project_id = self.built({'write': {'ok.txt': 'ok'}})
        with self.assertRaises(ValueError):
            self.supervisor.publish(project_id, 1, name='zła nazwa; rm')


class Languages(Base):
    def test_both_languages_use_the_same_placeholders(self):
        for key, (polish, english) in CATALOG.items():
            fields = {field for _, field, _, _ in string.Formatter().parse(polish) if field}
            other = {field for _, field, _, _ in string.Formatter().parse(english) if field}
            self.assertEqual(fields, other, key)
            self.assertTrue(english.strip(), key)

    def test_nested_messages_translate(self):
        reason = Msg('window_reason', window=Msg('window_five_hour'), percent='97')
        message = Msg('handoff', to='Claude', who='Codex', reason=reason, until='02:41')
        self.assertIn('limit 5h 97%', message)
        self.assertEqual(message.en(), 'Claude takes over: Codex is at 5h limit 97% (until 02:41).')

    def test_interface_gets_both_languages_for_events_and_details(self):
        self.scenario(claude=[{'write': {'ok.txt': 'ok'}, 'lgtm': True}], codex_limits=exhausted())
        project_id = self.start()
        self.wait_phase(project_id, 'waiting_partner')
        live = self.store.live(project_id)
        self.assertIn('limit', live['reason'])
        self.assertIn('5h limit', live['reason_en'])
        events = self.store.events(project_id)
        self.assertTrue(all(event['text_en'] for event in events))
        self.assertTrue(any('waiting' in event['text_en'] for event in events))
        version = self.store.latest_version(project_id)
        self.assertIn('Tests passed', version['verify_summary_en'])
        self.supervisor.stop(project_id)
        self.wait_status(project_id, 'stopped')

    def test_coordinator_answers_in_english(self):
        self.scenario(claude_limits=exhausted(), codex_limits=exhausted())
        project_id = self.supervisor.create_project(task='Zadanie', title='Test')['id']
        question = self.store.add_question(project_id, 'Status?')
        observer.answer(self.supervisor, project_id, question, 'Status?', 'en')
        answer = self.store.questions(project_id)[0]
        self.assertIn('Project: Test. Status: queued.', answer['answer'])
        self.assertEqual(answer['answered_by'], 'koordynator')
        self.store.update_project(project_id, status='stopped')


class Notes(Base):
    def test_note_reaches_next_turn_and_is_marked_delivered(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}, 'sleep': 1}, {'lgtm': True}],
                      claude=[{'lgtm': True}])
        project_id = self.start()
        self.wait_for(lambda: self.calls(), what='start agenta')
        self.supervisor.add_note(project_id, 'Użyj nazwy pliku wielkimi literami')
        self.wait_status(project_id, 'done')
        claude_prompt = next(c['prompt'] for c in self.calls() if c['agent'] == 'claude')
        self.assertIn('Użyj nazwy pliku wielkimi literami', claude_prompt)
        note = self.store.notes(project_id)[0]
        # Delivered to Claude, answered in its turn, and done with the accepted version (spec 1).
        self.assertEqual((note['status'], note['delivered_to']), ('done', 'claude'))
        self.assertIsNotNone(note['done_version'])

    def test_note_clears_earlier_acceptance(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}, 'lgtm': True, 'sleep': 1},
                             {'lgtm': True}],
                      claude=[{'lgtm': True}, {'lgtm': True}])
        project_id = self.start()
        self.wait_for(lambda: self.calls(), what='start agenta')
        self.supervisor.add_note(project_id, 'Nowe wymaganie')
        self.wait_status(project_id, 'done')
        self.assertEqual(len(self.calls()), 3)

    def test_urgent_note_interrupts_and_work_continues_with_it(self):
        self.scenario(codex=[{'write': {'polowa.txt': 'x'}, 'sleep': 60}],
                      claude=[{'write': {'ok.txt': 'ok'}, 'lgtm': True}],
                      codex_limits={'five_hour': 5, 'seven_day': 5})
        project_id = self.start()
        self.wait_for(lambda: self.calls(), what='start agenta')
        self.set_limits(codex=exhausted())
        self.supervisor.add_note(project_id, 'Pilne: zmień kierunek', urgent=True)
        self.wait_phase(project_id, 'waiting_partner')
        self.assertIn('Pilne: zmień kierunek', self.calls()[-1]['prompt'])


class Activity(Base):
    def wait_turn(self):
        self.wait_for(lambda: self.calls(), what='start agenta')

    def event(self, project_id, kind):
        rows = [e for e in self.store.events(project_id) if e['kind'] == kind]
        return rows[0] if rows else None

    def test_note_is_visible_in_activity_and_reply_comes_back(self):
        reply = 'ODPOWIEDŹ NA UWAGI:\nZmieniłem kolor na czerwony.\n\nCO TESTOWAĆ:\n- otwórz'
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}, 'sleep': 1}, {'lgtm': True}],
                      claude=[{'reply': reply, 'lgtm': True}])
        project_id = self.start()
        self.wait_turn()
        self.supervisor.add_note(project_id, 'Zmień kolor na czerwony')
        self.wait_status(project_id, 'done')
        note = self.event(project_id, 'note')
        self.assertIn('Zmień kolor na czerwony', note['text'])
        answer = self.event(project_id, 'note_reply')
        self.assertTrue(answer['has_body'])
        body = self.store.event_body(project_id, answer['id'])
        self.assertEqual(body, 'Zmieniłem kolor na czerwony.')
        self.assertEqual(self.store.notes(project_id)[0]['response'], body)

    def test_reply_section_keeps_its_own_formatting(self):
        reply = '## ODPOWIEDŹ NA UWAGI\n\n**Uwaga:** gotowe.\n\nCO TESTOWAĆ:\n- x'
        self.assertEqual(section(_NOTE_REPLY, reply), '**Uwaga:** gotowe.')
        self.assertEqual(section(_NOTE_REPLY, '**ODPOWIEDŹ NA UWAGI:** krótko'), 'krótko')

    def test_what_to_test_stops_before_goal_lines(self):
        reply = 'CO TESTOWAĆ:\n- uruchom grę\n\nCEL: 6/6 - nic\nOCENA POPRZEDNIEGO KROKU: przybliżył - x\nPRACA: F1'
        self.assertEqual(what_to_test(reply), '- uruchom grę')

    def test_reply_without_label_still_reaches_the_user(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}, 'sleep': 1}, {'lgtm': True}],
                      claude=[{'reply': 'Zrobione po swojemu.', 'lgtm': True}])
        project_id = self.start()
        self.wait_turn()
        self.supervisor.add_note(project_id, 'Uwaga')
        self.wait_status(project_id, 'done')
        self.assertIn('Zrobione po swojemu.', self.store.notes(project_id)[0]['response'])

    def test_every_turn_keeps_the_full_reply(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}, 'reply': 'Długi opis pracy.'}, {'lgtm': True}],
                      claude=[{'lgtm': True}])
        project_id = self.start()
        self.wait_status(project_id, 'done')
        first = [e for e in self.store.events(project_id) if e['kind'] == 'turn_end'][-1]
        self.assertIn('Długi opis pracy.', self.store.event_body(project_id, first['id']))

    def test_final_answer_shows_the_summary(self):
        summary = 'PODSUMOWANIE:\nPowstał plik ok.txt, działa.'
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}, {'reply': summary, 'lgtm': True}],
                      claude=[{'lgtm': True}])
        project_id = self.start()
        self.wait_status(project_id, 'done')
        final = self.supervisor.detail(project_id)['final']
        self.assertEqual(final['agent'], 'codex')
        self.assertEqual(final['body'], 'Powstał plik ok.txt, działa.')
        self.assertIn('Final answer', final['text_en'])

    def test_note_on_finished_project_reopens_it_and_gets_answered(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}, {'lgtm': True}], claude=[{'lgtm': True}])
        project_id = self.start()
        self.wait_status(project_id, 'done')
        self.scenario(claude=[{'write': {'fix.txt': '1'}, 'reply': 'ODPOWIEDŹ NA UWAGI:\nGotowe.',
                               'lgtm': True}], codex=[{'lgtm': True}])
        self.supervisor.add_note(project_id, 'Popraw jeszcze to')
        self.assertEqual(self.store.project(project_id)['status'], 'queued')
        self.wait_status(project_id, 'done')
        self.assertEqual(self.store.notes(project_id)[0]['response'], 'Gotowe.')

    def test_observer_sees_that_the_project_finished(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}, {'lgtm': True}], claude=[{'lgtm': True}])
        project_id = self.start()
        self.wait_status(project_id, 'done')
        self.assertIn('Oba modele zaakceptowały', observer.facts(self.store, self.store.project(project_id)))

    def test_question_and_answer_are_in_activity(self):
        self.scenario(claude_limits=exhausted(), codex_limits=exhausted())
        project_id = self.supervisor.create_project(task='Zadanie', title='Test')['id']
        question = self.store.add_question(project_id, 'Co dalej?')
        observer.answer(self.supervisor, project_id, question, 'Co dalej?')
        answer = self.event(project_id, 'answer')
        self.assertIn('Koordynator', answer['text'])
        self.assertIn('Coordinator', answer['text_en'])
        self.assertTrue(self.store.event_body(project_id, answer['id']))
        self.store.update_project(project_id, status='stopped')


class FakeOllama(threading.Thread):
    """Ollama's two endpoints the coordinator uses, with a scripted reply."""

    def __init__(self, reply):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        super().__init__(daemon=True)
        fake = self
        self.reply, self.prompts = reply, []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def answer(self, payload):
                body = json.dumps(payload).encode()
                self.send_response(200)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                self.answer({'models': [{'name': 'gemma4:31b'}]})

            def do_POST(self):
                request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                fake.prompts.append((request['model'], request['messages'][0]['content']))
                self.answer({'message': {'role': 'assistant', 'content': fake.reply}})

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.url = f'http://127.0.0.1:{self.server.server_address[1]}'

    def run(self):
        self.server.serve_forever()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


class Coordinator(Base):
    def setUp(self):
        super().setUp()
        self.ollama = FakeOllama('TYP: ZLECENIE\nDodamy eksport.')
        self.ollama.start()
        os.environ['GEMINI_OLLAMA_URL'] = self.ollama.url
        observer._ollama['at'] = 0

    def tearDown(self):
        self.ollama.stop()
        os.environ['GEMINI_OLLAMA_URL'] = 'http://127.0.0.1:9'
        observer._ollama['at'] = 0
        super().tearDown()

    def stopped_project(self):
        project_id = self.supervisor.create_project(task='Zadanie', repo_path=str(self.repo))['id']
        self.store.update_project(project_id, status='stopped', worktree=str(self.repo))
        return project_id

    def ask(self, project_id, text):
        return observer.answer(self.supervisor, project_id, self.store.add_question(project_id, text), text)

    def test_local_model_answers_by_default_when_ollama_has_it(self):
        self.scenario()
        project_id = self.stopped_project()
        self.assertEqual(observer.coordinator(self.store), 'local')
        self.assertEqual(self.ask(project_id, 'Dodajcie eksport do CSV'), 'order')
        answer = self.store.questions(project_id)[0]
        self.assertEqual((answer['answer'], answer['answered_by']), ('Dodamy eksport.', 'local'))
        self.assertEqual(self.store.notes(project_id)[0]['text'], 'Dodajcie eksport do CSV')
        model, prompt = self.ollama.prompts[0]
        self.assertEqual(model, 'gemma4:31b')
        self.assertIn('Nie masz dostępu do plików', prompt)
        self.assertIn('Projekt: Zadanie', prompt)
        self.assertEqual(self.calls(), [])

    def test_chosen_model_falls_back_to_local_then_to_coordinator(self):
        self.scenario(claude_limits=exhausted())
        self.store.set_setting('coordinator', 'claude')
        project_id = self.stopped_project()
        self.ask(project_id, 'Jak idzie?')
        self.assertEqual(self.store.questions(project_id)[0]['answered_by'], 'local')
        self.ollama.stop()
        observer._ollama['at'] = 0
        self.assertEqual(self.ask(project_id, 'Jak idzie?'), 'question')
        self.assertEqual(self.store.questions(project_id)[0]['answered_by'], 'koordynator')
        self.ollama = FakeOllama('')
        self.ollama.start()
        self.assertEqual(self.calls(), [])
        self.store.set_setting('coordinator', 'codex')
        self.scenario(codex=[{'reply': 'TYP: PYTANIE\nIdzie dobrze.'}])
        self.ask(project_id, 'Jak idzie?')
        self.assertEqual(self.store.questions(project_id)[0]['answered_by'], 'codex')


class TakeBack(Base):
    def test_routed_message_can_be_taken_back_before_a_turn(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}, {'lgtm': True}], claude=[{'lgtm': True}])
        project_id = self.start()
        self.wait_status(project_id, 'done')
        self.scenario(claude=[{'reply': 'TYP: ZLECENIE\nDodamy eksport.'}])
        question = self.store.add_question(project_id, 'Dodajcie eksport')
        self.assertEqual(observer.answer(self.supervisor, project_id, question, 'Dodajcie eksport'), 'order')
        self.assertEqual(self.store.project(project_id)['status'], 'queued')
        self.supervisor.withdraw_note(project_id, question)
        self.assertEqual(self.store.project(project_id)['status'], 'done')
        self.assertEqual(self.store.notes(project_id)[0]['status'], 'withdrawn')
        self.assertNotIn('replan', self.store.meta(project_id))
        with self.assertRaises(ValueError):
            self.supervisor.withdraw_note(project_id, question)
        calls = len(self.calls())
        for _ in range(3):
            self.supervisor.tick()
        self.assertEqual((self.store.project(project_id)['status'], len(self.calls())), ('done', calls))
        self.assertIn('Cofnięto przekazanie', self.store.events(project_id)[0]['text'])

    def test_new_work_wakes_a_model_that_waits_for_review(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}, 'lgtm': True}, {'write': {'b.txt': '1'}}],
                      claude_limits=exhausted())
        project_id = self.start()
        self.wait_phase(project_id, 'waiting_partner')
        self.supervisor.add_note(project_id, 'Dodaj plik b.txt', order=True)
        self.wait_for(lambda: len(self.calls()) == 2, what='druga tura Codexa')
        self.assertIn('Dodaj plik b.txt', self.calls()[1]['prompt'])
        self.supervisor.stop(project_id, immediate=True)


class Monitoring(Base):
    def turn_ends(self, project_id):
        return [dict(e, **(e['data'] or {})) for e in reversed(self.store.events(project_id))
                if e['kind'] == 'turn_end']

    def test_each_turn_records_its_limit_cost_and_changed_lines(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok', 'a.txt': 'x\ny\n'},
                              'set_limits': {'codex': {'five_hour': 30, 'seven_day': 25}}},
                             {'lgtm': True}], claude=[{'lgtm': True}])
        project_id = self.start()
        self.wait_status(project_id, 'done')
        first = self.turn_ends(project_id)[0]
        self.assertEqual(first['cost'], {'five_hour': 20.0, 'seven_day': 5.0})
        self.assertEqual(first['lines'], 3)
        state = self.supervisor.detail(project_id)['monitor']
        self.assertEqual(state['weekly_points']['codex'], 5.0)
        self.assertEqual(state['level'], 'ok')

    def test_each_turn_records_its_tokens(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}], gemini=[{'lgtm': True}], claude=[{'lgtm': True}])
        project_id = self.supervisor.create_project(task='Zbuduj ok.txt', repo_path=str(self.repo),
                                                    verify_cmd=VERIFY, gemini_model='default')['id']
        self.wait_status(project_id, 'done')
        tokens = {turn['agent']: turn['tokens'] for turn in self.turn_ends(project_id)}
        # Normalized per-turn values (gemini_app/usage.py): fresh input, cache read and output apart.
        self.assertEqual(tokens['codex'], {'total': 12345})
        self.assertEqual(tokens['claude'], {'input': 20, 'cache_read': 40000, 'output': 800, 'total': 41820})
        self.assertEqual(tokens['gemini'], {'input': 1200, 'cache_read': 1000, 'output': 300, 'total': 2500})
        state = self.supervisor.detail(project_id)['monitor']
        self.assertEqual(state['tokens']['claude']['total'], 41820)
        self.assertEqual([row['agent'] for row in state['token_turns']], ['codex', 'gemini', 'claude'])
        codex = next(row for row in state['usage'] if row['agent'] == 'codex')
        self.assertEqual((codex['input'], codex['output']), (None, None), 'Codex reports no split: no data, not 0')
        self.assertEqual(codex['model'], 'gpt-6.1-sol')

    def test_turns_without_a_version_raise_a_signal_once_and_then_halt(self):
        broken = [{'write': {'ok.txt': f'zle {i}'}} for i in range(12)]
        self.scenario(codex=broken[:6], claude=broken[6:])
        project_id = self.start(turns=20)
        self.wait_status(project_id, 'attention', timeout=60)
        self.assertIn('bez nowej wersji', self.store.project(project_id)['status_detail'])
        self.assertEqual(len(self.calls()), 8)
        alerts = [e for e in self.store.events(project_id) if e['kind'] == 'monitor']
        self.assertEqual(sum('bez nowej wersji' in e['text'] for e in alerts), 1)
        self.assertTrue(any('Same' in (e['text_en'] or '') or 'turns without' in (e['text_en'] or '')
                            for e in alerts))
        self.assertIn('verify', [s['key'] for s in self.supervisor.detail(project_id)['monitor']['signals']])

    def test_going_in_circles_is_detected(self):
        lines = '\n'.join(f'wiersz {i}' for i in range(150))
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}, {'write': {'duzo.txt': lines}},
                             {'write': {'duzo.txt': ''}}],
                      claude=[{'write': {'duzo.txt': lines + '\nx'}}, {'write': {'duzo.txt': ''}}])
        project_id = self.start(turns=5)
        self.wait_status(project_id, 'attention', timeout=60)
        keys = [s['key'] for s in self.supervisor.detail(project_id)['monitor']['signals']]
        self.assertIn('churn', keys)


class GoalProgress(Base):
    @staticmethod
    def rated(goal, verdict, **step):
        return {**step, 'reply': f'Krok.\n\nCEL: {goal} - okna\nOCENA POPRZEDNIEGO KROKU: {verdict} - bo tak'}

    def test_goal_and_verdict_are_parsed(self):
        self.assertEqual(goal_report('x\n**CEL:** 3/6 - dach\nOCENA POPRZEDNIEGO KROKU: nie przybliżył - styl'),
                         {'goal_done': 3, 'goal_total': 6, 'verdict': 'not_closer'})
        self.assertEqual(goal_report('OCENA POPRZEDNIEGO KROKU: przybliżył - test')['verdict'], 'closer')
        self.assertEqual(goal_report('OCENA POPRZEDNIEGO KROKU: cofnął - zepsuł')['verdict'], 'back')
        self.assertEqual(goal_report('bez oceny'), {})

    def test_agents_are_asked_to_rate_the_goal(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}, {'lgtm': True}], claude=[{'lgtm': True}])
        self.wait_status(self.start(), 'done')
        self.assertIn('OCENA POPRZEDNIEGO KROKU', self.calls()[0]['prompt'])

    def test_steps_that_do_not_move_the_goal_halt_the_project(self):
        steps = [self.rated('2/5', 'nie przybliżył', write={'ok.txt': 'ok', f'p{i}.txt': str(i)})
                 for i in range(10)]
        self.scenario(codex=steps[:5], claude=steps[5:])
        project_id = self.start(turns=20)
        self.wait_status(project_id, 'attention', timeout=60)
        self.assertIn('nieprzybliżające do celu', self.store.project(project_id)['status_detail'])
        self.assertEqual(len(self.calls()), 4)
        keys = [s['key'] for s in self.supervisor.detail(project_id)['monitor']['signals']]
        self.assertIn('goal_verdicts', keys)
        self.assertIn('goal_flat', keys)
        self.assertEqual(self.supervisor.detail(project_id)['monitor']['goal'], [2, 5])

    def test_a_model_working_alone_does_not_halt_on_its_own_verdicts(self):
        # PR9/26: four "not closer" verdicts Codex gave its own steps while the partner was away stopped the project.
        steps = [self.rated('2/5', 'nie przybliżył', write={f'p{i}.txt': str(i)}) for i in range(5)]
        steps.append({'write': {'ok.txt': 'ok'}, 'lgtm': True})
        self.scenario(claude=steps)
        project_id = self.supervisor.create_project(task='Zbuduj ok.txt', repo_path=str(self.repo), verify_cmd=VERIFY,
                                                    codex_model='none', max_turns=20)['id']
        self.wait_status(project_id, 'done', 'attention', timeout=60)
        self.assertNotIn('nieprzybliżające', self.store.project(project_id)['status_detail'] or '')
        self.assertEqual(len(self.calls()), 6)
        keys = [s['key'] for s in self.supervisor.detail(project_id)['monitor']['signals']]
        self.assertNotIn('goal_verdicts', keys)

    def test_progressing_work_raises_no_goal_signal(self):
        self.scenario(codex=[self.rated('1/3', 'brak', write={'ok.txt': 'ok'}),
                             self.rated('3/3', 'przybliżył', lgtm=True)],
                      claude=[self.rated('2/3', 'przybliżył', write={'b.txt': '1'}),
                              self.rated('3/3', 'przybliżył', lgtm=True)])
        project_id = self.start()
        self.wait_status(project_id, 'done')
        state = self.supervisor.detail(project_id)['monitor']
        self.assertEqual(state['goal_history'], [1, 2, 3, 3])
        self.assertFalse([s for s in state['signals'] if s['key'].startswith('goal')])


class Planning(Base):
    PLAN = {'architecture': 'Moduł zapisu i moduł sprawdzania.', 'run': 'python3 check.py',
            'items': [{'id': 'F1', 'title': 'Plik ok', 'kind': 'feature', 'priority': 'must', 'status': 'doing'},
                      {'id': 'F1.1', 'title': 'Zapis ok.txt', 'kind': 'task', 'parent': 'F1',
                       'priority': 'must', 'status': 'doing', 'budget': 1},
                      {'id': 'F2', 'title': 'Ozdoby', 'kind': 'feature', 'priority': 'could', 'status': 'todo'},
                      {'id': 'D1', 'title': 'Literówka w README', 'kind': 'debt', 'parent': 'F1',
                       'priority': 'could', 'status': 'todo', 'category': 'ui', 'note': 'README, wiersz 3'}]}

    def plan_json(self):
        return json.dumps(self.PLAN)

    def test_plan_is_validated(self):
        self.assertEqual(plan_module.validate(self.PLAN), [])
        bad = {'items': [{'id': 'A', 'title': 'x', 'kind': 'epic'}, {'id': 'A', 'title': 'y', 'parent': 'Z'}]}
        problems = plan_module.validate(bad)
        # "epic" is a listed variant of "feature" (plan_contract.KIND_MAP): corrected, not an error.
        self.assertEqual(len(problems), 2)
        self.assertTrue(any('powtórzone id A' in p for p in problems))
        self.assertTrue(any('nieznany parent Z' in p for p in problems))

    def test_first_turn_asks_for_a_plan_then_each_turn_gets_its_summary(self):
        self.scenario(codex=[{'write': {'.sol83/plan.json': self.plan_json(), 'ok.txt': 'ok'},
                              'reply': 'Plan gotowy.\nPRACA: F1.1'}, {'lgtm': True}],
                      claude=[{'lgtm': True, 'reply': 'PRACA: F1.1'}])
        project_id = self.start()
        self.wait_status(project_id, 'done')
        first, second = self.calls()[0], self.calls()[1]
        self.assertIn('Nie ma jeszcze planu', first['prompt'])
        self.assertIn('F1.1 Zapis ok.txt', second['prompt'])
        self.assertIn('Architektura: Moduł zapisu', second['prompt'])
        view = self.supervisor.detail(project_id)['plan']
        self.assertEqual({r['id']: r['turns'] for r in view['rows']}['F1.1'], 2)
        self.assertEqual(view['run'], 'python3 check.py')

    def test_cost_is_assigned_to_items_in_whole_percent(self):
        self.scenario(codex=[{'write': {'.sol83/plan.json': self.plan_json(), 'ok.txt': 'ok'},
                              'reply': 'PRACA: F1.1', 'set_limits': {'codex': {'five_hour': 30, 'seven_day': 26}}},
                             {'lgtm': True}],
                      claude=[{'reply': 'PRACA: D1', 'write': {'README.md': 'x'},
                               'set_limits': {'claude': {'five_hour': 15, 'seven_day': 23}}},
                              {'lgtm': True}])
        project_id = self.start()
        self.wait_status(project_id, 'done')
        view = self.supervisor.detail(project_id)['plan']
        rows = {r['id']: r for r in view['rows']}
        self.assertEqual((rows['F1.1']['week'], rows['D1']['week']), (6, 3))
        self.assertEqual(view['breakdown']['must'], 6)
        self.assertEqual(view['breakdown']['debt'], 3)

    def test_over_budget_item_gets_a_decision_then_halts(self):
        plan = self.plan_json()
        stuck = [{'write': {'.sol83/plan.json': plan, 'ok.txt': f'zle {i}'}, 'reply': 'PRACA: F1.1'}
                 for i in range(6)]
        self.scenario(codex=stuck[:3], claude=stuck[3:])
        project_id = self.start(turns=12)
        self.wait_status(project_id, 'attention', timeout=60)
        self.assertEqual(len(self.calls()), 3)
        self.assertIn('przekroczyła budżet', self.calls()[2]['prompt'])
        self.assertIn('F1.1 zużyła 3 tur', self.store.project(project_id)['status_detail'])

    def test_order_rebuilds_the_plan_and_reopens_a_finished_project(self):
        self.scenario(codex=[{'write': {'.sol83/plan.json': self.plan_json(), 'ok.txt': 'ok'},
                              'reply': 'PRACA: F1.1'}, {'lgtm': True}],
                      claude=[{'lgtm': True, 'reply': 'PRACA: F1.1'}])
        project_id = self.start()
        self.wait_status(project_id, 'done')
        self.scenario(claude=[{'reply': 'TYP: ZLECENIE\nDodamy eksport.'},
                              {'write': {'eksport.txt': '1'}, 'lgtm': True, 'reply': 'PRACA: F3'}],
                      codex=[{'lgtm': True}])
        question = self.store.add_question(project_id, 'Dodajcie eksport do CSV')
        self.assertEqual(observer.answer(self.supervisor, project_id, question, 'Dodajcie eksport do CSV'), 'order')
        self.assertTrue(self.store.questions(project_id)[0]['answer'].endswith('Dodamy eksport.'))
        self.assertNotIn('TYP:', self.store.questions(project_id)[0]['answer'])
        self.wait_status(project_id, 'done')
        work = [c for c in self.calls() if 'Dodajcie eksport do CSV' in c['prompt']
                and 'kontekst od koordynatora' in c['prompt']]
        self.assertIn('Użytkownik zlecił nową pracę', work[0]['prompt'])

    def test_plan_left_by_an_earlier_project_is_rebuilt_for_the_new_task(self):
        (self.repo / '.sol83').mkdir()
        (self.repo / '.sol83/plan.json').write_text(self.plan_json())
        git = Git(self.repo)
        git.run('add', '-A')
        git.run(*gitops.IDENTITY, 'commit', '-q', '-m', 'stary plan')
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}, {'lgtm': True}], claude=[{'lgtm': True}])
        project_id = self.start()
        self.wait_status(project_id, 'done')
        first, second = self.calls()[0]['prompt'], self.calls()[1]['prompt']
        self.assertIn('Repozytorium ma .sol83/plan.json z poprzedniego projektu', first)
        self.assertNotIn('F1.1 Zapis ok.txt', first)
        self.assertIn('F1.1 Zapis ok.txt', second)
        start = next(e for e in self.store.events(project_id) if e['kind'] == 'turn_start' and e['data']['turn'] == 1)
        self.assertEqual(start['data']['work'], 'plan')

    def test_question_is_answered_and_not_sent_to_agents(self):
        self.scenario(claude=[{'reply': 'TYP: PYTANIE\nJest dobrze.'}])
        project_id = self.supervisor.create_project(task='Zadanie', repo_path=str(self.repo))['id']
        self.store.update_project(project_id, status='stopped', worktree=str(self.repo))
        question = self.store.add_question(project_id, 'Jak idzie?')
        self.assertEqual(observer.answer(self.supervisor, project_id, question, 'Jak idzie?'), 'question')
        self.assertEqual(self.store.notes(project_id), [])

    def test_without_a_model_a_request_still_becomes_work(self):
        self.assertEqual(observer.guess_kind('Co dalej?'), 'question')
        self.assertEqual(observer.guess_kind('Nie podejmujcie pracy, napiszcie raport'), 'question')
        self.assertEqual(observer.guess_kind('Dodajcie tryb ciemny'), 'note')

    def test_user_can_start_any_plan_item(self):
        self.scenario(codex=[{'write': {'.sol83/plan.json': self.plan_json(), 'ok.txt': 'ok'},
                              'reply': 'PRACA: F1.1'}, {'lgtm': True}],
                      claude=[{'lgtm': True, 'reply': 'PRACA: F1.1'}])
        project_id = self.start()
        self.wait_status(project_id, 'done')
        self.scenario(claude=[{'write': {'README.md': 'poprawione'}, 'lgtm': True, 'reply': 'PRACA: D1'}],
                      codex=[{'lgtm': True}])
        self.supervisor.start_item(project_id, 'D1')
        self.wait_status(project_id, 'done')
        prompt = [c for c in self.calls() if 'zleca pozycję planu D1' in c['prompt']][0]['prompt']
        self.assertIn('Priorytet użytkownika: pozycja D1', prompt)
        with self.assertRaises(ValueError):
            self.supervisor.start_item(project_id, 'NIE-MA')

    def test_only_passing_code_becomes_a_version(self):
        self.scenario(
            codex=[{'write': {'ok.txt': 'zle'}}, {'write': {'ok.txt': 'zepsute dalej'}}],
            claude=[{'write': {'ok.txt': 'ok'}, 'what_to_test': '- sprawdź start'}])
        project_id = self.start(turns=3)
        self.wait_status(project_id, 'attention')
        versions = self.store.versions(project_id)
        self.assertEqual([v['number'] for v in versions], [1])
        self.assertEqual(versions[0]['level'], 'tested')
        detail = self.supervisor.detail(project_id)
        self.assertEqual(detail['recommended']['number'], 1)
        self.assertGreater(detail['work']['commits_after_last_version'], 0)

    def test_test_copy_stays_on_chosen_version_while_agents_work(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}, {'write': {'ok.txt': 'zepsute'}}],
                      claude=[{'write': {'nowe.txt': 'x'}, 'sleep': 1}])
        project_id = self.start(turns=3)
        self.wait_for(lambda: self.store.latest_version(project_id), what='v1')
        path = pathlib.Path(self.supervisor.prepare_test_copy(project_id, 1))
        self.wait_status(project_id, 'attention')
        self.assertEqual((path / 'ok.txt').read_text(), 'ok')
        worktree = pathlib.Path(self.store.project(project_id)['worktree'])
        self.assertEqual((worktree / 'ok.txt').read_text(), 'zepsute')

    def test_user_rejection_reopens_project_and_skips_that_version(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}, {'lgtm': True}, {'lgtm': True}],
                      claude=[{'lgtm': True}, {'write': {'fix.txt': '1'}, 'lgtm': True}])
        project_id = self.start()
        self.wait_status(project_id, 'done')
        self.supervisor.set_verdict(project_id, 1, works=False, comment='nie startuje')
        self.assertEqual(self.store.project(project_id)['status'], 'queued')
        self.assertIsNone(recommended_version(self.store.versions(project_id)))
        self.wait_status(project_id, 'done')
        self.assertTrue(any('nie startuje' in call['prompt'] for call in self.calls()))
        self.assertEqual(self.store.latest_version(project_id)['number'], 2)

    def test_without_test_command_version_is_only_a_declaration(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}, 'lgtm': True}], claude=[{'lgtm': True}])
        project_id = self.start(verify='')
        self.wait_status(project_id, 'done')
        version = self.store.latest_version(project_id)
        self.assertIn('tylko deklaracja', version['verify_summary'])

    def test_test_command_set_later_applies_to_the_turn_that_ends_next(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}, 'sleep': 1}], claude=[{'write': {'b.txt': '1'}}])
        project_id = self.start(verify='', turns=2)
        self.wait_for(lambda: self.calls(), what='start agenta')
        self.supervisor.set_verify(project_id, VERIFY)
        self.wait_status(project_id, 'attention')
        self.assertEqual([v['level'] for v in self.store.versions(project_id)], ['tested', 'tested'])
        self.assertIn('Polecenie testów od końca bieżącej tury', next(
            e['text'] for e in self.store.events(project_id) if e['kind'] == 'models'))

    def test_rejected_version_stays_in_the_folder_until_a_newer_one(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}, {'lgtm': True}, {'lgtm': True}],
                      claude=[{'lgtm': True}, {'write': {'fix.txt': '1'}, 'lgtm': True}])
        project_id = self.start()
        self.wait_status(project_id, 'done')
        self.wait_for(lambda: self.store.project(project_id)['run_version'] == 1, what='v1 w folderze')
        self.supervisor.set_verdict(project_id, 1, works=False, comment='dodaj eksport')
        for _ in range(3):
            self.supervisor.tick()
        self.assertEqual(self.store.project(project_id)['run_version'], 1)
        self.wait_status(project_id, 'done')
        self.wait_for(lambda: self.store.project(project_id)['run_version'] == 2, what='v2 w folderze')

    def test_lock_left_by_a_stopped_agent_does_not_break_the_checkpoint(self):
        git = Git(self.repo)
        lock = self.repo / git.run('rev-parse', '--git-path', 'index.lock')
        lock.write_text('')
        os.utime(lock, (time.time() - 120, time.time() - 120))
        (self.repo / 'nowy.txt').write_text('x')
        self.assertTrue(git.checkpoint('po zatrzymaniu').changed)
        self.assertFalse(lock.exists())
        lock.write_text('')
        threading.Timer(0.3, lock.unlink).start()
        (self.repo / 'drugi.txt').write_text('y')
        self.assertTrue(git.checkpoint('narzędzie jeszcze kończy').changed)

    def test_test_artifacts_do_not_invalidate_acceptance(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok', '__pycache__/x.pyc': 'a'}}, {'lgtm': True}],
                      claude=[{'write': {'__pycache__/y.pyc': 'b'}, 'lgtm': True}])
        project_id = self.start()
        self.wait_status(project_id, 'done')
        self.assertEqual(len(self.store.versions(project_id)), 1)


class RunHere(Base):
    RUN = 'JAK URUCHOMIĆ:\npython3 check.py'

    def own_project(self, turns=12):
        return self.supervisor.create_project(task='Zbuduj ok.txt', verify_cmd='test -f ok.txt',
                                              max_turns=turns)['id']

    def run_version(self, project_id, number):
        self.wait_for(lambda: self.store.project(project_id)['run_version'] == number, what=f'v{number} w folderze')

    def test_project_created_by_sol83_gets_each_version_on_main(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}, {'lgtm': True, 'reply': self.RUN}],
                      claude=[{'lgtm': True}])
        project_id = self.own_project()
        self.wait_status(project_id, 'done')
        self.run_version(project_id, 1)
        repo = pathlib.Path(self.store.project(project_id)['repo_path'])
        version = self.store.latest_version(project_id)
        self.assertEqual(Git(repo).run('rev-parse', 'main'), version['commit_sha'])
        self.assertEqual((repo / 'ok.txt').read_text(), 'ok')
        here = self.supervisor.detail(project_id)['run_here']
        self.assertEqual((here['path'], here['version']), (str(repo), 1))
        self.assertEqual(here['steps'], f'cd {repo}\npython3 check.py')
        self.assertEqual([other['kind'] for other in here['others']], ['work'])
        self.assertIn('deliver', self.kinds(project_id))
        self.assertIn('JAK URUCHOMIĆ: polecenia od zera', self.calls()[0]['prompt'])

    def test_user_repository_keeps_main_and_test_folder_follows_versions(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}, {'lgtm': True}], claude=[{'lgtm': True}])
        main = Git(self.repo).head()
        project_id = self.start()
        self.wait_status(project_id, 'done')
        self.run_version(project_id, 1)
        here = self.supervisor.detail(project_id)['run_here']
        self.assertEqual(Git(self.repo).run('rev-parse', 'main'), main)
        self.assertTrue(here['path'].endswith(f'{project_id}-testy'))
        self.assertEqual((pathlib.Path(here['path']) / 'ok.txt').read_text(), 'ok')
        self.assertEqual(here['others'][0], {'kind': 'repo', 'path': str(self.repo),
                                             'branch': f'gemini/{project_id}'})
        self.assertTrue(here['steps'].startswith('cd '))

    def test_chosen_version_stays_until_a_newer_one(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}, {'write': {'c.txt': '1'}, 'sleep': 3}],
                      claude=[{'write': {'b.txt': '1'}}, {}])
        project_id = self.own_project(turns=4)
        self.run_version(project_id, 2)
        repo = pathlib.Path(self.store.project(project_id)['repo_path'])
        self.supervisor.prepare_test_copy(project_id, 1)
        self.assertFalse((repo / 'b.txt').exists())
        for _ in range(3):
            self.supervisor.tick()
        self.assertEqual(self.store.project(project_id)['run_version'], 1)
        self.run_version(project_id, 3)
        self.assertEqual(Git(repo).run('symbolic-ref', '--short', 'HEAD'), 'main')
        self.assertTrue((repo / 'c.txt').exists())

    def test_unsaved_changes_in_the_folder_are_kept_and_reported_once(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}], claude=[{'write': {'b.txt': '1'}, 'sleep': 2}])
        project_id = self.own_project(turns=2)
        self.run_version(project_id, 1)
        repo = pathlib.Path(self.store.project(project_id)['repo_path'])
        (repo / 'ok.txt').write_text('moje')
        self.wait_status(project_id, 'attention')
        for _ in range(3):
            self.supervisor.tick()
        failed = [e for e in self.store.events(project_id) if e['kind'] == 'deliver' and not e['data']['ok']]
        self.assertEqual(len(failed), 1)
        self.assertIn('niezapisane zmiany', failed[0]['text'])
        self.assertEqual((repo / 'ok.txt').read_text(), 'moje')

    def test_instructions_come_from_the_reply_then_the_plan_then_the_readme(self):
        self.assertEqual(how_to_run('CO TESTOWAĆ:\n- a\nJAK URUCHOMIĆ:\nmake run\nPODSUMOWANIE:\nx'), 'make run')
        self.assertEqual(what_to_test('CO TESTOWAĆ:\n- a\n\nJAK URUCHOMIĆ:\nmake run'), '- a')
        readme = '# App\nOpis\n## Uruchomienie\n```\nswift run\n```\n### Opcje\n-v\n## Licencja\nMIT'
        git = Git(self.repo)
        (self.repo / 'README.md').write_text(readme)
        git.run('add', '-A')
        git.run(*gitops.IDENTITY, 'commit', '-q', '-m', 'readme')
        git.run('tag', 'r1')
        (self.repo / '.sol83').mkdir()
        (self.repo / '.sol83/plan.json').write_text(json.dumps({'items': [], 'run': 'swift test'}))
        git.run('add', '-A')
        git.run(*gitops.IDENTITY, 'commit', '-q', '-m', 'plan')
        git.run('tag', 'r2')
        steps = self.supervisor._run_steps
        self.assertEqual(steps(str(self.repo), {'tag': 'r1', 'how_to_run': None}), '```\nswift run\n```\n### Opcje\n-v')
        self.assertEqual(steps(str(self.repo), {'tag': 'r2', 'how_to_run': None}), 'swift test')
        self.assertEqual(steps(str(self.repo), {'tag': 'r2', 'how_to_run': 'make'}), 'make')


class Deleting(Base):
    def leftovers(self, project_id):
        home = pathlib.Path(os.environ['GEMINI_HOME'])
        paths = [home / 'runs' / project_id, home / 'worktrees' / project_id,
                 home / 'worktrees' / f'{project_id}-testy', home / 'config' / f'run-{project_id}.json']
        return [str(path) for path in paths if path.exists()]

    def test_project_created_by_sol83_is_removed_entirely(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}, {'lgtm': True}], claude=[{'lgtm': True}])
        project_id = self.supervisor.create_project(task='Zbuduj ok.txt', verify_cmd='test -f ok.txt')['id']
        self.wait_status(project_id, 'done')
        repo = pathlib.Path(self.store.project(project_id)['repo_path'])
        self.assertTrue(repo.is_dir())
        self.supervisor.delete_project(project_id)
        self.assertIsNone(self.store.project(project_id))
        self.assertEqual(self.store.events(project_id), [])
        self.assertEqual(self.store.versions(project_id), [])
        self.assertFalse(repo.exists())
        self.assertEqual(self.leftovers(project_id), [])
        with self.assertRaises(LookupError):
            self.supervisor.delete_project(project_id)

    def test_user_repository_stays_without_sol83_traces(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}, {'lgtm': True}], claude=[{'lgtm': True}])
        main = Git(self.repo).head()
        project_id = self.start()
        self.wait_status(project_id, 'done')
        self.wait_for(lambda: self.store.project(project_id)['run_version'], what='folder testowy')
        self.supervisor.delete_project(project_id)
        git = Git(self.repo)
        self.assertEqual(git.run('rev-parse', 'main'), main)
        self.assertEqual(git.run('branch', '--list', f'gemini/{project_id}'), '')
        self.assertEqual(git.run('tag', '-l', f'gemini/{project_id}/*'), '')
        self.assertEqual(len(git.run('worktree', 'list').splitlines()), 1)
        self.assertEqual(self.leftovers(project_id), [])
        self.assertTrue((self.repo / 'check.py').exists())

    def test_running_project_is_stopped_then_removed(self):
        self.scenario(codex=[{'sleep': 60}])
        project_id = self.start()
        self.wait_for(lambda: self.calls(), what='start agenta')
        self.supervisor.delete_project(project_id)
        self.assertEqual(engine_pids(project_id), [])
        self.assertIsNone(self.store.project(project_id))
        self.assertEqual(subprocess.run(['pgrep', '-f', f'{FAKES}/fake_agent.py codex exec'],
                                        capture_output=True).stdout, b'')
        self.supervisor.tick()
        self.assertEqual(self.leftovers(project_id), [])


class Lifecycle(Base):
    def test_immediate_stop_kills_agent_and_resume_continues(self):
        self.scenario(codex=[{'write': {'polowa.txt': 'x'}, 'sleep': 60},
                             {'write': {'ok.txt': 'ok'}}, {'lgtm': True}],
                      claude=[{}, {'lgtm': True}])
        project_id = self.start()
        self.wait_for(lambda: self.calls(), what='start agenta')
        self.supervisor.stop(project_id, immediate=True)
        self.wait_status(project_id, 'stopped', timeout=15)
        self.assertEqual(subprocess.run(['pgrep', '-f', f'{FAKES}/fake_agent.py codex exec'],
                                        capture_output=True).stdout, b'')
        self.supervisor.resume(project_id, note='Dokończ')
        self.wait_status(project_id, 'done')
        self.assertTrue(any('Dokończ' in call['prompt'] for call in self.calls()))

    def test_turn_numbers_continue_after_resume(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}, 'sleep': 1}, {'lgtm': True}],
                      claude=[{'lgtm': True}])
        project_id = self.start()
        self.wait_for(lambda: self.calls(), what='start agenta')
        self.supervisor.stop(project_id)
        self.wait_status(project_id, 'stopped')
        self.supervisor.resume(project_id)
        self.wait_status(project_id, 'done')
        ended = [e['text'] for e in self.store.events(project_id) if e['kind'] == 'turn_end']
        self.assertTrue(ended[0].startswith('Tura 3'), ended)

    def test_weekly_reserve_set_from_the_panel_does_not_touch_five_hour(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}, {'lgtm': True}], claude=[{'lgtm': True}],
                      claude_limits={'five_hour': 10, 'seven_day': 85})
        self.store.set_setting('weekly_claude', 80)
        view = self.supervisor.limits_view(force=True)['claude']
        self.assertEqual((view['threshold'], view['weekly_threshold']), (95.0, 80.0))
        self.assertFalse(view['available'])
        self.store.set_setting('weekly_claude', 100)
        self.assertTrue(self.supervisor.limits_view(force=True)['claude']['available'])

    def test_engine_stopped_outside_the_panel_is_stopped_not_failed(self):
        self.scenario(codex=[{'sleep': 60}])
        project_id = self.start()
        self.wait_for(lambda: self.calls(), what='start agenta')
        os.kill(self.store.project(project_id)['engine_pid'], signal.SIGTERM)
        self.wait_status(project_id, 'stopped', timeout=15)
        self.assertIn('spoza panelu', self.store.events(project_id)[0]['text'])

    def test_restarted_server_keeps_engine_whatever_locale_recorded_it(self):
        self.scenario(codex=[{'sleep': 60}])
        project_id = self.start()
        self.wait_for(lambda: self.calls(), what='start agenta')
        self.store.update_project(project_id, engine_start='pon lis  2 17:24:20 2026')
        restarted = Supervisor(self.store)
        for _ in range(5):
            restarted.tick()
        self.assertEqual(self.store.project(project_id)['status'], 'running')
        restarted.stop(project_id, immediate=True)
        self.wait_status(project_id, 'stopped', timeout=15)

    def test_resume_never_starts_a_second_engine(self):
        self.scenario(codex=[{'sleep': 60}])
        project_id = self.start()
        self.wait_for(lambda: self.calls(), what='start agenta')
        self.store.update_project(project_id, status='attention')
        self.supervisor.resume(project_id)
        for _ in range(5):
            self.supervisor.tick()
            time.sleep(0.2)
        self.assertEqual(len(engine_pids(project_id)), 1)
        self.assertEqual(self.store.project(project_id)['status'], 'running')
        self.supervisor.stop(project_id, immediate=True)
        self.wait_status(project_id, 'stopped', timeout=15)

    def test_stop_reaches_every_engine_of_the_project(self):
        self.scenario(codex=[{'sleep': 60}])
        project_id = self.start()
        self.wait_for(lambda: self.calls(), what='start agenta')
        self.supervisor.procs.clear()
        self.store.update_project(project_id, engine_pid=1)
        self.supervisor.stop(project_id, immediate=True)
        self.wait_status(project_id, 'stopped', timeout=15)
        self.assertEqual(engine_pids(project_id), [])

    def test_agent_gets_a_fresh_session_every_turn_by_default(self):
        # 2026-11-08 audit: a resumed session re-reads its history on every step (PR9: the 6th turn of a Gemini
        # session cost 2.6 times the first). The handoff packet carries the context instead.
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}, {'write': {'b.txt': '1'}}, {'lgtm': True}],
                      claude=[{'lgtm': True}, {'lgtm': True}])
        project_id = self.start()
        self.wait_status(project_id, 'done')
        codex = [c for c in self.calls() if c['agent'] == 'codex']
        self.assertFalse(codex[1]['resumed'])
        self.assertIn('Nowa sesja', codex[1]['prompt'])

    def test_crash_is_reported_and_resume_recovers(self):
        self.scenario(codex=[{'sleep': 60}, {'write': {'ok.txt': 'ok'}}, {'lgtm': True}],
                      claude=[{'lgtm': True}])
        project_id = self.start()
        self.wait_for(lambda: self.calls(), what='start agenta')
        project = self.store.project(project_id)
        os.kill(project['engine_pid'], signal.SIGKILL)
        self.wait_status(project_id, 'attention')
        self.assertIn('nieoczekiwanie', self.store.project(project_id)['status_detail'])
        subprocess.run(['pkill', '-f', f'{FAKES}/fake_agent.py codex exec'])
        self.supervisor.resume(project_id)
        self.wait_status(project_id, 'done')

    def test_no_progress_stops_spending_limits(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}, *[{} for _ in range(5)]],
                      claude=[{} for _ in range(5)])
        project_id = self.start(turns=20)
        self.wait_status(project_id, 'attention')
        self.assertIn('bez żadnej zmiany', self.store.project(project_id)['status_detail'])
        self.assertLessEqual(len(self.calls()), 8)

    def test_queue_runs_one_project_at_a_time(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}, 'sleep': 0.5}, {'lgtm': True},
                             {'write': {'ok.txt': 'ok'}}, {'lgtm': True}],
                      claude=[{'lgtm': True}, {'lgtm': True}])
        first = self.start()
        self.wait_status(first, 'running')
        other = pathlib.Path(tempfile.mkdtemp(dir=TEMP))
        gitops.create_repo(other)
        shutil.copy(self.repo / 'check.py', other / 'check.py')
        Git(other).run('add', '-A')
        Git(other).run(*gitops.IDENTITY, 'commit', '-q', '-m', 'start')
        second = self.supervisor.create_project(task='Drugi', repo_path=str(other),
                                                verify_cmd=VERIFY)['id']
        self.supervisor.tick()
        self.assertEqual(self.store.project(second)['status'], 'queued')
        self.wait_status(second, 'done')
        self.assertEqual(self.store.project(first)['status'], 'done')

    def test_waiting_for_review_does_not_hold_up_the_queue(self):
        self.scenario(claude=[{'write': {'ok.txt': 'ok'}, 'lgtm': True},
                              {'write': {'app.py': 'x'}, 'lgtm': True}],
                      codex_limits=exhausted())
        first = self.start()
        self.wait_phase(first, 'waiting_partner')
        second = self.supervisor.create_project(task='Drugi projekt')['id']
        self.wait_phase(second, 'waiting_partner')
        self.assertEqual(self.store.project(first)['status'], 'running')
        self.assertEqual(len(self.calls()), 2)
        for project_id in (first, second):
            self.supervisor.stop(project_id)
        self.wait_status(second, 'stopped')

    def test_new_project_gets_its_own_repository(self):
        self.scenario(codex=[{'write': {'app.py': 'print(1)'}, 'lgtm': True}],
                      claude=[{'lgtm': True}])
        project_id = self.supervisor.create_project(task='# Moja aplikacja\nZrób coś')['id']
        self.wait_status(project_id, 'done')
        project = self.store.project(project_id)
        self.assertEqual(project['title'], 'Moja aplikacja')
        self.assertTrue(Git(project['repo_path']).is_repo())

    def test_project_setup_script_prepares_each_workspace(self):
        setup = self.repo / '.gemini-setup'
        setup.write_text('#!/bin/sh\nmkdir dane && echo gotowe > dane/plik.txt\n')
        setup.chmod(0o755)
        (self.repo / '.gitignore').write_text('dane/\n')
        git = Git(self.repo)
        git.run('add', '-A')
        git.run(*gitops.IDENTITY, 'commit', '-q', '-m', 'setup')
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}, {'lgtm': True}], claude=[{'lgtm': True}])
        project_id = self.start()
        self.wait_status(project_id, 'done')
        worktree = pathlib.Path(self.store.project(project_id)['worktree'])
        # Code from the repository: nothing runs before the user approved this exact content.
        self.assertFalse((worktree / 'dane').exists())
        setup = self.supervisor.detail(project_id)['setup']
        self.assertFalse(setup['approved'])
        self.assertIn('mkdir dane', setup['content'])
        with self.assertRaises(ValueError):
            self.supervisor.approve_setup(project_id, 'not-the-hash')
        self.supervisor.approve_setup(project_id, setup['sha'])
        self.wait_for(lambda: (worktree / 'dane/plik.txt').exists(), 10, 'setup ran')
        self.assertEqual((worktree / 'dane/plik.txt').read_text(), 'gotowe\n')
        copy = pathlib.Path(self.supervisor.prepare_test_copy(project_id, 1))
        self.assertTrue((copy / 'dane/plik.txt').exists())

    def test_dirty_source_is_refused(self):
        (self.repo / 'brud.txt').write_text('x')
        with self.assertRaises(ValueError):
            self.start()


class ClaudeAdapter(Base):
    def run_adapter(self, step):
        self.scenario(claude=[step])
        return subprocess.run([str(ROOT / 'bin/claude'), '-p', 'zadanie', '--output-format', 'json'],
                              capture_output=True, text=True, cwd=TEMP, timeout=20)

    def test_keeps_json_contract_and_records_limits(self):
        done = self.run_adapter({'reply': 'wynik'})
        self.assertEqual(done.returncode, 0)
        self.assertIn('wynik', json.loads(done.stdout)['result'])
        event = limits.read_claude_event()
        self.assertEqual(event['windows']['five_hour']['used'], 10.0)

    def test_agents_may_search_the_web_but_observers_may_not(self):
        self.run_adapter({'reply': 'wynik'})
        self.assertIn('WebSearch', self.calls()[-1]['argv'])
        self.scenario(claude=[{'reply': 'x'}])
        subprocess.run([str(ROOT / 'bin/claude'), '-p', 'pytanie', '--output-format', 'json',
                        '--tools', 'Read,Grep,Glob'], capture_output=True, text=True, cwd=TEMP, timeout=20)
        self.assertNotIn('WebSearch', self.calls()[-1]['argv'])

    def test_error_result_becomes_failure(self):
        done = self.run_adapter({'fail': "You've hit your limit · resets 3pm"})
        self.assertEqual(done.returncode, 1)
        self.assertEqual(limits.classify_failure(done.stderr), 'limit')

    def test_refuses_paid_overage(self):
        started = time.monotonic()
        done = self.run_adapter({'overage': True, 'reply': 'nie powinno dojść'})
        self.assertEqual(done.returncode, 1)
        self.assertLess(time.monotonic() - started, 4)
        self.assertEqual(limits.classify_failure(done.stderr), 'limit')


class Policy(unittest.TestCase):
    NOW = 1_800_000_000.0

    def test_availability(self):
        snapshot = {'windows': {'five_hour': {'used': 96, 'resets_at': self.NOW + 60}}}
        self.assertFalse(limits.availability(snapshot, 95, now=self.NOW).available)
        self.assertTrue(limits.availability(snapshot, 97, now=self.NOW).available)
        rolled = {'windows': {'five_hour': {'used': 100, 'resets_at': self.NOW - 1}}}
        self.assertTrue(limits.availability(rolled, 95, now=self.NOW).available)
        self.assertTrue(limits.availability(None, 95, now=self.NOW).available)
        weekly = {'windows': {'five_hour': {'used': 99, 'resets_at': self.NOW + 60},
                              'seven_day': {'used': 99, 'resets_at': self.NOW + 9000}}}
        self.assertEqual(limits.availability(weekly, 95, now=self.NOW).until, self.NOW + 9000)

    def test_weekly_reserve_is_separate_and_named(self):
        snapshot = {'windows': {'five_hour': {'used': 0, 'resets_at': None},
                                'seven_day': {'used': 81, 'resets_at': self.NOW + 9000}}}
        free = limits.availability(snapshot, {'five_hour': 80, 'seven_day': 100}, now=self.NOW)
        self.assertTrue(free.available)
        held = limits.availability(snapshot, {'five_hour': 95, 'seven_day': 80}, now=self.NOW)
        self.assertFalse(held.available)
        self.assertIn('Twój próg 80%', held.reason)
        self.assertIn('your threshold 80%', held.reason.en())
        exhausted = {'windows': {'seven_day': {'used': 100, 'resets_at': self.NOW + 9000}}}
        self.assertNotIn('próg', limits.availability(exhausted, 95, now=self.NOW).reason)

    def test_choose_speaker(self):
        up = limits.Availability(True)
        down = limits.Availability(False, self.NOW + 60, 'limit 5h 100%')
        later = limits.Availability(False, self.NOW + 90, 'limit 5h 100%')
        self.assertEqual(limits.choose_speaker(0, [up, up], [False, False]).mode, 'alternate')
        self.assertEqual(limits.choose_speaker(0, [down, up], [False, False]).speaker, 1)
        self.assertEqual(limits.choose_speaker(0, [up, down], [False, False]).mode, 'solo')
        waiting = limits.choose_speaker(0, [down, up], [False, True])
        self.assertEqual((waiting.speaker, waiting.mode), (None, 'waiting_partner'))
        both = limits.choose_speaker(0, [later, down], [False, False])
        self.assertEqual((both.mode, both.until), ('waiting_limits', self.NOW + 60))
        review = limits.choose_speaker(0, [down, up], [False, True], self_review=True)
        self.assertEqual((review.speaker, review.mode), (1, 'self_review'))

    def test_three_models_share_turns(self):
        up = limits.Availability(True)
        down = limits.Availability(False, self.NOW + 60, 'limit 5h 100%')
        pick = limits.choose_among([0, 1, 2], [up, up, up], [False] * 3)
        self.assertEqual((pick.speaker, pick.mode), (0, 'alternate'))
        pick = limits.choose_among([0, 1, 2], [down, up, down], [False] * 3)
        self.assertEqual((pick.speaker, pick.mode), (1, 'solo'))
        pick = limits.choose_among([0, 1, 2], [down, up, up], [False] * 3)
        self.assertEqual((pick.speaker, pick.mode, pick.reason), (1, 'alternate', 'limit 5h 100%'))
        wait = limits.choose_among([0, 1, 2], [down, up, up], [False, True, True])
        self.assertEqual(wait.mode, 'waiting_partner')
        role = limits.choose_among([0], [down, up, up], [False] * 3)
        self.assertEqual((role.speaker, role.mode, role.until), (None, 'waiting_role', self.NOW + 60))

    def test_failure_classes(self):
        self.assertEqual(limits.classify_failure(LIMIT_MESSAGE), 'limit')
        self.assertEqual(limits.classify_failure('API Error: 529 overloaded'), 'transient')
        self.assertEqual(limits.classify_failure('Please run /login'), 'auth')
        self.assertEqual(limits.classify_failure('', 'timeout'), 'timeout')
        self.assertEqual(limits.classify_failure('SyntaxError in foo.py'), 'other')

    def test_parses_real_usage_report(self):
        report = ('You are currently using your subscription to power your Claude Code usage\n\n'
                  'Current session: 16% used · resets Nov 2 at 2:49am (Europe/Warsaw)\n'
                  'Current week (all models): 49% used · resets Nov 7 at 9:59pm (Europe/Warsaw)\n')
        snapshot = limits.parse_claude_usage(report, 1793567000.0)
        self.assertEqual(snapshot['windows'][limits.FIVE_HOUR]['used'], 16)
        self.assertEqual(snapshot['windows'][limits.SEVEN_DAY]['used'], 49)
        # The report rounds down to the minute: the window counts until the end of that minute (2026-11-08).
        self.assertEqual(time.strftime('%d %H:%M:%S', time.localtime(
            snapshot['windows'][limits.FIVE_HOUR]['resets_at'])), '02 02:50:00')
        self.assertIsNone(limits.parse_claude_usage('inny format', 1793567000.0))


class WebGuard(Base):
    def setUp(self):
        super().setUp()
        from http.server import ThreadingHTTPServer
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), None)
        port = self.server.server_address[1]
        self.server.RequestHandlerClass = type('H', (Handler,), {
            'supervisor': self.supervisor, 'port': port})
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f'http://127.0.0.1:{port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        super().tearDown()

    def post(self, path, payload, headers=None):
        request = urllib.request.Request(self.url + path, data=json.dumps(payload).encode(),
                                         headers=headers or {'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def test_rejects_requests_from_other_sites(self):
        status, _ = self.post('/api/projects', {'task': 'x'},
                              {'Content-Type': 'application/json', 'Origin': 'https://evil.example'})
        self.assertEqual(status, 403)
        status, _ = self.post('/api/projects', {'task': 'x'}, {'Content-Type': 'text/plain'})
        self.assertEqual(status, 403)
        request = urllib.request.Request(self.url + '/api/overview',
                                         headers={'Host': 'evil.example'})
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request)
        self.assertEqual(caught.exception.code, 403)

    def test_message_with_interrupt_becomes_urgent_work(self):
        self.scenario(codex=[{'sleep': 60}],
                      claude=[{'reply': 'TYP: UWAGA\nPrzekażę.'}, {'reply': 'PRACA: F1'}])
        project_id = self.start()
        self.wait_for(lambda: self.calls(), what='start agenta')
        status, _ = self.post(f'/api/projects/{project_id}/message', {'text': 'Stop, zmiana planu', 'interrupt': True})
        self.assertEqual(status, 200)
        self.wait_for(lambda: self.store.notes(project_id), what='uwaga po rozpoznaniu')
        self.assertEqual(self.store.notes(project_id)[0]['text'], 'Stop, zmiana planu')
        self.wait_for(lambda: len(self.calls()) == 2, what='wznowienie z uwagą')
        self.assertIn('Stop, zmiana planu', self.calls()[1]['prompt'])
        self.supervisor.stop(project_id, immediate=True)

    def test_interrupting_question_stops_work_and_does_not_restart_it(self):
        self.scenario(codex=[{'sleep': 60}], claude=[{'reply': 'TYP: PYTANIE\nStan: tura 1.'}])
        project_id = self.start()
        self.wait_for(lambda: self.calls(), what='start agenta')
        self.post(f'/api/projects/{project_id}/message',
                  {'text': 'Nie podejmujcie pracy, napiszcie mi jak sie ma projekt', 'interrupt': True})
        self.wait_for(lambda: self.store.questions(project_id)[0]['status'] == 'answered', what='odpowiedź')
        self.wait_status(project_id, 'stopped', timeout=15)
        for _ in range(5):
            self.supervisor.tick()
        self.assertEqual(self.store.project(project_id)['status'], 'stopped')
        self.assertEqual(self.store.notes(project_id), [])

    def test_project_can_be_created_and_validation_errors_are_readable(self):
        self.scenario()
        status, body = self.post('/api/projects', {'task': ''})
        self.assertEqual((status, body['error']), (400, 'Podaj treść zadania.'))
        status, body = self.post('/api/projects', {'task': 'Zadanie', 'repo_path': 'wzgledna'})
        self.assertEqual(status, 400)
        status, body = self.post('/api/projects', {'task': 'Zadanie'})
        self.assertEqual(status, 200)
        self.store.update_project(body['id'], status='stopped')


if __name__ == '__main__':
    unittest.main()


class QueueFlow(Base):
    """Spec points 1 and 2 on the real engine with fake CLIs."""

    def test_order_during_the_final_turn_is_not_lost_or_closed_over(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}, {'lgtm': True, 'sleep': 3}, {'lgtm': True}],
                      claude=[{'lgtm': True}, {'lgtm': True}])
        project_id = self.start()
        # The third call has started (the fake records it before sleeping): its prompt is already built.
        self.wait_for(lambda: len(self.calls()) >= 3, 30, 'tura 3 w toku')
        added = self.supervisor.add_note(project_id, 'Dodaj jeszcze nagłówek', request_key='late-1')
        self.supervisor.add_note(project_id, 'Dodaj jeszcze nagłówek', request_key='late-1')
        self.wait_status(project_id, 'done', timeout=60)
        note = next(n for n in self.store.notes(project_id) if n['id'] == added['id'])
        self.assertEqual(len([n for n in self.store.notes(project_id) if n['text'] == note['text']]), 1)
        self.assertEqual(note['status'], 'done')
        self.assertGreater(note['delivered_turn'], 3)
        self.assertTrue(any('Dodaj jeszcze nagłówek' in call['prompt'] for call in self.calls()))
        kinds = [event['kind'] for event in self.store.events(project_id)]
        self.assertIn('final', kinds)

    def test_engine_lost_mid_turn_gives_the_note_back_after_restart(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}, 'sleep': 6}, {'write': {'ok.txt': 'ok'}}, {'lgtm': True}],
                      claude=[{'lgtm': True}, {'lgtm': True}])
        project_id = self.start()
        self.supervisor.add_note(project_id, 'Uwaga przed pierwszą turą')
        self.wait_for(lambda: any(n['status'] == 'delivered' for n in self.store.notes(project_id)), 30, 'doręczona')
        self.supervisor._kill_engines(project_id)
        self.wait_status(project_id, 'attention', 'stopped')
        self.assertEqual([n['status'] for n in self.store.notes(project_id)], ['pending'])
        self.supervisor.resume(project_id)
        self.wait_status(project_id, 'done', timeout=60)
        self.assertEqual(self.store.notes(project_id)[0]['status'], 'done')

    def test_turn_keeps_its_configuration_snapshot(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}, 'sleep': 2}, {'lgtm': True}],
                      claude=[{'lgtm': True}])
        project_id = self.start()
        self.wait_phase(project_id, 'turn_running')
        snapshot = self.supervisor.detail(project_id)['turn_config']
        self.supervisor.set_models(project_id, codex_reasoning='low')
        detail = self.supervisor.detail(project_id)
        self.assertEqual(detail['turn_config'], snapshot, 'the running turn keeps its snapshot')
        self.assertEqual(detail['next_config']['codex']['effort'], 'low')
        self.wait_status(project_id, 'done', timeout=60)
        starts = [e for e in reversed(self.store.events(project_id)) if e['kind'] == 'turn_start']
        self.assertEqual(starts[0]['data']['config']['agent'], 'codex')
        self.assertIn('roles', starts[0]['data']['config'])

    def test_auto_selection_picks_an_allowed_model_and_records_why(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}, {'lgtm': True}], claude=[{'lgtm': True}])
        project_id = self.supervisor.create_project(task='Zbuduj ok.txt', repo_path=str(self.repo), verify_cmd=VERIFY,
                                                    selections={'claude': 'auto_power'})['id']
        self.wait_status(project_id, 'done', timeout=60)
        starts = [e['data']['config'] for e in self.store.events(project_id) if e['kind'] == 'turn_start']
        claude = next(c for c in starts if c['agent'] == 'claude')
        self.assertEqual((claude['selection'], claude['model']), ('auto_power', 'opus'))
        self.assertIn('policy_version', claude['decision'])
        self.assertNotIn('fable', [c['model'] for c in starts])

    def test_auto_without_an_allowed_model_waits_instead_of_falling_back(self):
        # The fake Codex lists only gpt-test, which the catalog does not classify.
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}], claude=[{'write': {'ok.txt': 'ok'}}, {'lgtm': True}])
        project_id = self.supervisor.create_project(task='Zbuduj ok.txt', repo_path=str(self.repo), verify_cmd=VERIFY,
                                                    selections={'codex': 'auto_economy'})['id']
        self.wait_for(lambda: any('Auto: brak dozwolonego modelu' in e['text'] for e in self.store.events(project_id)),
                      30, 'Codex czeka')
        self.supervisor.stop(project_id, immediate=True)
        self.wait_status(project_id, 'stopped', 'attention')
        self.assertFalse([c for c in self.calls() if c['agent'] == 'codex'], 'Codex never ran with an unclassified model')


class UserInteractions(Base):
    """Spec 21 and 9 on the real engine with fake CLIs."""
    QUESTION = json.dumps({'items': [{'id': 'Q1', 'type': 'decision', 'text': 'Który format eksportu: CSV czy JSON?',
                                      'options': ['CSV', 'JSON'], 'recommendation': 'CSV', 'blocks': ['F2'],
                                      'why': 'zmienia format pliku'}]})

    def test_blocking_question_pauses_and_the_answer_resumes_the_work(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok', '.sol83/requests.json': self.QUESTION}}, {'write': {}}],
                      claude=[{'write': {}}, {'lgtm': True}], )
        project_id = self.start()
        self.wait_status(project_id, 'attention', timeout=60)
        project = self.store.project(project_id)
        self.assertIn('oczekiwanie na odpowiedź', project['status_detail'])
        from gemini_app.supervisor import state_kind
        self.assertEqual(state_kind(project, None), 'user')
        rows = self.supervisor.detail(project_id)['interactions']
        question = next(row for row in rows if row['type'] == 'decision')
        self.assertEqual((question['local_id'], question['author'], question['state']), ('Q1', 'codex', 'open'))
        before = len(self.calls())
        self.scenario(codex=[{'lgtm': True}], claude=[{'lgtm': True}])
        self.supervisor.answer_interaction(project_id, question['id'], 'CSV', request_key='a1')
        self.wait_status(project_id, 'done', timeout=60)
        prompt = self.calls()[before]['prompt']
        self.assertIn('Odpowiedź użytkownika na pytanie', prompt)
        self.assertIn('CSV', prompt)
        self.assertEqual(next(row for row in self.supervisor.detail(project_id)['interactions']
                              if row['id'] == question['id'])['state'], 'applied')

    def test_english_project_gets_english_instructions(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}}, {'lgtm': True}], claude=[{'lgtm': True}])
        project_id = self.supervisor.create_project(task='Build ok.txt', repo_path=str(self.repo), verify_cmd=VERIFY,
                                                    language='en')['id']
        self.wait_status(project_id, 'done', timeout=60)
        prompt = self.calls()[0]['prompt']
        self.assertIn('[GEMINI: context from the coordinator, turn 1]', prompt)
        self.assertIn('There is no project plan yet', prompt)
        self.assertIn('WHAT TO TEST', json.loads((TEMP / f"config/run-{project_id}.json").read_text())['agents'][0]['role_prompt'])
        self.assertNotIn('Zadanie użytkownika', prompt)

    def test_version_check_is_a_manual_test_record(self):
        self.scenario(codex=[{'write': {'ok.txt': 'ok'}, 'what_to_test': 'Otwórz ok.txt i sprawdź treść.'}, {'lgtm': True}],
                      claude=[{'lgtm': True}])
        project_id = self.start()
        self.wait_status(project_id, 'done', timeout=60)
        check = next(row for row in self.supervisor.detail(project_id)['interactions'] if row['author'] == 'version')
        self.assertEqual((check['type'], check['version_number']), ('manual_test', 1))
        self.supervisor.set_verdict(project_id, 1, True, 'działa', request_key='v1-ok')
        check = next(row for row in self.supervisor.detail(project_id)['interactions'] if row['author'] == 'version')
        self.assertEqual(check['answers'][-1]['result'], 'works')
