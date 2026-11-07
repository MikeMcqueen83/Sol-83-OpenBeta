"""Turn scheduler plugged into Duet: who works next, handoffs, takeovers, versions.

Decisions live here and not in the models on purpose: an agent that ran out of
limit cannot decide anything, so the coordinator notices it and wakes the partner.
"""
from __future__ import annotations

import collections
import dataclasses
import json
import os
import re
import time
from pathlib import Path
from typing import Optional

from . import assets as content
from . import limits, monitor, providers, sandbox
from . import interactions, licenses, orders, prompts, usage
from . import plan as project_plan
from . import roles as model_roles
from . import catalog, model_catalog
from .catalog import MODEL_OFF
from .gitops import Checkpoint, Git
from .messages import Msg, in_language
from .store import Store

MAX_IDLE_TURNS = 6
NO_VERSION_HALT = 8
NO_GOAL_HALT = 4
ITEM_HALT_FACTOR = 2
ROTATE_AFTER = int(os.environ.get('GEMINI_ROTATE_AFTER', 6))
MAX_TREE_REPEATS = 3
MAX_FAILURES = 3
MAX_RETRIES = 2
MAX_SELF_REVIEWS = 5
VERIFY_TIMEOUT = 1800
VERIFY_TAIL_LINES = 25
AUTH_BLOCK_S = 3600
FAILURE_BLOCK_S = 600
AGENT_LABEL = {'claude': 'Claude', 'codex': 'Codex', 'gemini': 'Gemini', 'local': 'Lokalny LLM'}
TURN_START = {'solo': 'turn_start_solo', 'self_review': 'turn_start_review', 'single': 'turn_start_single'}
_RECAP = re.compile(r'^RECAP:\s*(.+)$', re.M)
# Reply markers in Polish and English (prompts.MARKERS); the parsers accept both in any project.
_LABELS_AFTER = (r'(?=^[#*\s]*(?:LGTM|<<<|\[duet\]|---|WERSJA OK|VERSION OK|CEL\s*:|GOAL\s*:|OCENA POPRZEDNIEGO'
                 r'|PREVIOUS STEP|PRACA\s*:|WORK\s*:|PODSUMOWANIE|SUMMARY|ODPOWIED|REPLY TO NOTES|CO TESTOWA'
                 r'|WHAT TO TEST|JAK URUCHOM|HOW TO RUN)|\Z)')
_WHAT_TO_TEST = re.compile(r'^[#*\s]*(?:CO TESTOWA[ĆC]|WHAT TO TEST)[*\s]*:?[*\s]*(.*?)' + _LABELS_AFTER, re.M | re.S | re.I)
_HOW_TO_RUN = re.compile(r'^[#*\s]*(?:JAK URUCHOMI[ĆC]|HOW TO RUN)[*\s]*:?[*\s]*(.*?)' + _LABELS_AFTER, re.M | re.S | re.I)
_VERSION_OK = re.compile(r'^\s*(?:WERSJA OK|VERSION OK)\b', re.M)
_CODEX_MODEL = re.compile(r'^model:\s*(\S+)', re.M)
_REQUESTS_CHANGES = re.compile(r'^STATUS:\s*requesting-changes', re.M)
_GOAL = re.compile(r'^[#*\s]*(?:CEL|GOAL)[*\s]*:[*\s]*(\d+)\s*/\s*(\d+)', re.M | re.I)
_ITEM = re.compile(r'^[#*\s]*(?:PRACA|WORK)[*\s]*:[*\s]*([\w.\-]+)', re.M | re.I)
_VERDICT = re.compile(r'^[#*\s]*(?:OCENA POPRZEDNIEGO KROKU|PREVIOUS STEP)[*\s]*:[*\s]*'
                      r'(nie przybli\w*|przybli\w*|cofn\w*|brak|not closer|closer|back|none)', re.M | re.I)
VERDICTS = {'przybli': 'closer', 'nie przybli': 'not_closer', 'cofn': 'back', 'brak': None,
            'closer': 'closer', 'not closer': 'not_closer', 'back': 'back', 'none': None}


def goal_report(reply: str) -> dict:
    """The agent's own count of met acceptance criteria and its verdict on the previous step."""
    report = {}
    item = _ITEM.search(reply or '')
    if item:
        report['item'] = item[1]
    goal = _GOAL.search(reply or '')
    if goal:
        report.update(goal_done=int(goal[1]), goal_total=int(goal[2]))
    verdict = _VERDICT.search(reply or '')
    if verdict:
        word = verdict[1].lower()
        report['verdict'] = next(value for key, value in VERDICTS.items()
                                 if word.startswith(key) and not (key == 'przybli' and word.startswith('nie'))
                                 and not (key == 'closer' and word.startswith('not')))
    return report
_SECTION_END = (r'(?=^\s*(?:LGTM|<<<|\[duet\]|WERSJA OK|VERSION OK|CO TESTOWA|WHAT TO TEST|JAK URUCHOM|HOW TO RUN'
                r'|PODSUMOWANIE|SUMMARY|ODPOWIED|REPLY TO NOTES)|\Z)')
_LABEL_END = r'[* \t]*:?[* \t]*\n?'
_NOTE_REPLY = re.compile(r'^[#* \t]*(?:ODPOWIED[ŹZ] NA UWAGI|REPLY TO NOTES)' + _LABEL_END + r'(.*?)' + _SECTION_END, re.M | re.S | re.I)
_SUMMARY = re.compile(r'^[#* \t]*(?:PODSUMOWANIE|SUMMARY)' + _LABEL_END + r'(.*?)' + _SECTION_END, re.M | re.S | re.I)


@dataclasses.dataclass
class Outcome:
    converged: bool = False
    halt: bool = False
    message: Optional[str] = None


def label(agent: str) -> str:
    return AGENT_LABEL.get(agent, agent)


def clock(moment: Optional[float]) -> str:
    return time.strftime('%H:%M', time.localtime(moment)) if moment else '--:--'


def section(pattern, reply: str) -> str:
    """A labelled part of the reply, or the whole reply when the agent skipped the label."""
    match = pattern.search(reply or '')
    return (match[1].strip() if match else '') or (reply or '').strip()


def what_to_test(reply: str) -> Optional[str]:
    match = _WHAT_TO_TEST.search(reply or '')
    return match[1].strip()[:2000] or None if match else None


def how_to_run(reply: str) -> Optional[str]:
    """Commands that start the finished project from scratch, as the agent gave them."""
    match = _HOW_TO_RUN.search(reply or '')
    return match[1].strip()[:2000] or None if match else None


class GeminiScheduler:
    def __init__(self, cfg, run_dir: Path, store: Store, project_id: str):
        self.cfg = cfg
        self.run_dir = run_dir
        self.store = store
        self.pid = project_id
        self.project = store.project(project_id)
        self.names = [agent.name for agent in cfg.agents]
        self.git = Git(cfg.cwd)
        self.reader = limits.Reader(ttl=float(os.environ.get('GEMINI_LIMITS_TTL', 45)))
        self.poll = float(os.environ.get('GEMINI_WAIT_POLL', 120))
        self.retry_delay = float(os.environ.get('GEMINI_RETRY_DELAY', 60))
        self.force_next: Optional[int] = None
        self.current_message = ''
        self.failures = 0
        self.retries: collections.Counter = collections.Counter()
        self.idle_turns = 0
        self.tree_counts: collections.Counter = collections.Counter()
        self.verified: dict = {}
        self.last_verify = 'jeszcze nie uruchamiano'
        self.waiting_key = None
        self.session_turns: collections.Counter = collections.Counter()
        self.rotated = False
        self.asked_item = False
        self.handoff_announced = False
        self.idle_agent: Optional[str] = None
        self.in_self_review = False
        self.self_review_rounds = 0
        self.self_reviewed_tree: Optional[str] = None
        last = store.last_event(project_id, 'turn_end')
        data = json.loads(last['data']) if last and last['data'] else {}
        self.last_speaker = last['agent'] if last else None
        self.turns_before = data.get('turn', 0)
        self.last_changed = bool(data.get('changed'))
        self.last_work = data.get('work')
        self.work = 'implement'
        self.roles = [(model_roles.GENERAL,)] * len(self.names)
        self.spoke = {record['agent']: record.get('turn', 0)
                      for record in monitor.turn_records(store, project_id)}
        self.accepted = set(store.meta(project_id).get('lgtm', []))
        self.accepted_tree = store.meta(project_id).get('lgtm_tree')
        self.opened = last is not None
        self.reset_source = None
        self.lang = prompts.language(self.project)
        self.decision = None
        self.verify_raw = self.project.get('verify_cmd') or None
        self.inherited_instructed = False

    # ---- Availability -------------------------------------------------

    def _enabled(self) -> list:
        """The user may switch a model off at any time: it then gets no turns."""
        project = self.store.project(self.pid)
        return [project.get(f'{name}_model') not in (None, MODEL_OFF) for name in self.names]

    def _roles(self) -> list:
        project = self.store.project(self.pid)
        return [model_roles.of(project, name) for name in self.names]

    def _converged(self, enabled: list, roles: list) -> bool:
        """Two models that review accepted the same code, or the only one there is."""
        reviewers = model_roles.reviewers(self.names, roles, enabled)
        done = [name for name in reviewers if name in self.accepted]
        return bool(reviewers) and len(done) >= min(2, len(reviewers))

    def _work_kind(self, enabled: list, roles: list) -> str:
        """What this turn is for: the plan, a task from it, or a review of the last change."""
        plan, problem = project_plan.load(self.cfg.cwd)
        # New work waiting in the queue rebuilds the plan first; so does a plan inherited from an
        # earlier project on the same repository.
        if (plan is None and not problem) or self.store.meta(self.pid).get('replan') == 'inherited' \
                or orders.pending_orders(self.store, self.pid):
            return 'plan'
        if model_roles.creates_content(roles, enabled) and self.last_work != 'content' \
                and content.pending(self.cfg.cwd):
            return 'content'
        # A change or a claim of done gets a review; an accepting review asks the next reviewer.
        done = (self.last_changed and self.last_work == 'implement') or self.last_speaker in self.accepted
        if done and not self._converged(enabled, roles):
            return 'review'
        return 'implement'

    def _take_user_orders(self) -> None:
        """Orders the user placed in the panel, and decisions on the agents' proposals, go into the file
        between turns, when no agent writes it."""
        if self.store.meta(self.pid).get('license_request'):
            try:
                licenses.apply_pending(self.store, self.pid)
            except licenses.LicenseError as exc:
                self.store.event(self.pid, 'attention', Msg('license_kept', detail=str(exc)))
        decisions = self.store.meta(self.pid).get('asset_decisions') or []
        if decisions:
            content.apply_decisions(self.cfg.cwd, decisions)
            self.store.update_meta(self.pid, lambda meta: meta.__setitem__(
                'asset_decisions', (meta.get('asset_decisions') or [])[len(decisions):]))
        waiting = self.store.meta(self.pid).get('asset_orders') or []
        if not waiting:
            return
        content.add(self.cfg.cwd, waiting)
        # Remove exactly what was written: an order the server added meanwhile stays for the next turn.
        self.store.update_meta(self.pid, lambda meta: meta.__setitem__(
            'asset_orders', (meta.get('asset_orders') or [])[len(waiting):]))

    def _order(self, work: str, enabled: list, roles: list, hint: int, forced: bool) -> list:
        """Who should take this work, best first: a model with this very role, then a general
        one; among equals, whoever worked least recently, so a review goes to someone else."""
        able = [i for i, (on, role) in enumerate(zip(enabled, roles))
                if on and model_roles.covers(role, work)]
        experts = [i for i in able if not model_roles.is_general(roles[i])]
        if experts and (self.store.project(self.pid).get('role_fallback') or 'general') == 'wait':
            able = experts
        return sorted(able, key=lambda i: (forced and i != hint, i not in experts,
                                           self.spoke.get(self.names[i], 0), i != hint))

    def _availability(self, force: bool = False) -> list:
        """A side in Auto with no allowed model is unavailable: it waits, it never falls back to a
        top or unclassified model."""
        snapshots = self.reader.read(force=force)
        result = []
        for index, (name, on) in enumerate(zip(self.names, self._enabled())):
            if not on:
                result.append(limits.Availability(False, None, Msg('model_off_reason')))
                continue
            decision = self._auto_decision(index, snapshots)
            if decision is not None and not decision['model']:
                result.append(limits.Availability(False, None, Msg('auto_no_model', reason=decision['reason'])))
                continue
            result.append(limits.availability(snapshots.get(name), self.store.threshold(name), self.store.block(name)))
        return result

    def _auto_decision(self, index: int, snapshots: Optional[dict] = None) -> Optional[dict]:
        """The Auto choice for this side and the current work, or None in manual mode."""
        name = self.names[index]
        mode = self.store.project(self.pid).get(f'{name}_selection') or 'manual'
        if mode == 'manual':
            return None
        snapshot = (snapshots or {}).get(name)
        remaining = limits.remaining(snapshot) if snapshot else None
        live = None
        if name in ('codex', 'gemini'):
            listed = catalog.read().get(name) or []
            live = [model['id'] for model in listed] or None
        failures = self._steps_not_closer() + self._recent_verify_failures()
        return model_catalog.choose(model_catalog.current(self.store), name, mode, self.work, failures,
                                    remaining, live)

    def _recent_verify_failures(self) -> int:
        """Failed test runs in a row, newest first, since the last passing one."""
        count = 0
        for event in self.store.events(self.pid, 60):
            if event['kind'] != 'verify':
                continue
            if (event['data'] or {}).get('passed'):
                break
            count += 1
        return count

    def _apply_models(self, index: int) -> str:
        """Read the user's choice every turn, so a change applies from the next one. In Auto the
        policy picks the model and level by rules, and the decision is recorded with its reason."""
        agent = self.cfg.agents[index]
        project = self.store.project(self.pid)
        previous = agent.model
        self.decision = self._auto_decision(index, self.reader.read())
        if self.decision and self.decision['model']:
            agent.model, effort = self.decision['model'], self.decision.get('effort')
            self.store.event(self.pid, 'models', Msg('auto_choice', mode=self.decision['mode'],
                                                     model=agent.model, effort=effort or '-',
                                                     reason=self.decision['reason']),
                             agent=agent.name, data=self.decision)
        else:
            agent.model = project[f'{agent.name}_model'] or agent.model
            effort = project[f'{agent.name}_reasoning'] or None
        if previous and agent.model != previous and agent.session_id and self.spoke.get(agent.name):
            # A resumed session keeps the old model's context; a model change starts a new session
            # and the handoff (task, plan, changes, notes) carries the verified state.
            agent.session_id = None
            self.session_turns[agent.name] = 0
            self.rotated = True
            self.store.event(self.pid, 'models', Msg('model_session_fresh', who=label(agent.name)), agent=agent.name)
        if agent.backend == 'gemini':
            # Duet only nudges Gemini in the prompt; agy takes a real --effort through the adapter.
            # It travels in the environment: Duet refuses to resume a run with saved extra_args.
            os.environ['SOL83_GEMINI_EFFORT'] = effort or ''
            agent.extra_args = []
            agent.reasoning_effort = None
        else:
            agent.reasoning_effort = effort
        return ', '.join(part for part in (agent.model, effort) if part)

    def _usage(self, name: str) -> dict:
        snapshot = self.reader.read(force=True).get(name) or {}
        return {key: (window.get('used', 0), window.get('resets_at'))
                for key, window in (snapshot.get('windows') or {}).items()}

    def _turn_cost(self, name: str) -> dict:
        """Limit points this turn moved: the readings are free, so every turn is measured.
        Other work on the same account in the meantime counts too."""
        before = getattr(self, 'usage_before', {}) or {}
        cost = {}
        for key, (used, resets_at) in self._usage(name).items():
            was, was_resets = before.get(key, (used, resets_at))
            cost[key] = round(used if resets_at != was_resets and used < was else max(0.0, used - was), 1)
        return cost

    def _may_self_review(self) -> bool:
        """Full Power lets the same model review in a new session while the partner is away, at most
        MAX_SELF_REVIEWS times in a row. After that the project waits, and says why, once."""
        if not self.store.full_power() or self.self_reviewed_tree == self.git.tree():
            return False
        if self.self_review_rounds >= MAX_SELF_REVIEWS:
            if not getattr(self, 'self_review_limit_announced', False):
                self.self_review_limit_announced = True
                self.store.event(self.pid, 'attention', Msg('self_review_limit', count=MAX_SELF_REVIEWS))
            return False
        self.self_review_limit_announced = False
        return True

    def _opening(self, order: list, roles: list) -> list:
        """The opening turn is the expensive one: among equally suited models with a limit
        reading, give it to whoever has more left."""
        if not order:
            return order
        snapshots = self.reader.read()
        tier = [i for i in order if model_roles.is_general(roles[i]) == model_roles.is_general(roles[order[0]])
                and snapshots.get(self.names[i])]
        if len(tier) < 2:
            return order
        best = max(tier, key=lambda i: (limits.remaining(snapshots.get(self.names[i])), i == order[0]))
        return [best] + [i for i in order if i != best]

    def _wait(self, seconds: float, stop) -> None:
        deadline = time.monotonic() + seconds
        full_power = self.store.full_power()
        while time.monotonic() < deadline and not stop.requested:
            time.sleep(min(1.0, max(0.05, deadline - time.monotonic())))
            if self.store.full_power() != full_power:
                return

    def _wait_seconds(self, until: Optional[float]) -> float:
        if not until:
            return self.poll
        return max(1.0, min(self.poll, until - time.time()))

    # ---- Hooks called by Duet -----------------------------------------

    def before_turn(self, *, turn: int, speaker_idx: int, message: str, stop):
        turn += self.turns_before
        forced = self.force_next is not None
        hint = self.force_next if forced else speaker_idx
        self.force_next = None
        self._take_user_orders()
        while True:
            if stop.requested:
                return None
            enabled, roles = self._enabled(), self._roles()
            self.work = self._work_kind(enabled, roles)
            order = self._order(self.work, enabled, roles, hint, forced)
            if not self.opened:
                order = self._opening(order, roles)
            avail = self._availability()
            several = sum(enabled) > 1
            # A pending note is new work: nobody counts as done until a turn has received it.
            waits = several and not self.store.pending_notes(self.pid)
            accepted = [waits and (name in self.accepted or name == self.idle_agent) for name in self.names]
            choice = limits.choose_among(order, avail, accepted, waits and self._may_self_review())
            if choice.speaker is not None:
                break
            self._announce_wait(choice)
            self._wait(self._wait_seconds(choice.until), stop)
        self.opened = True
        self.waiting_key = None
        index = choice.speaker
        name = self.names[index]
        preferred = order[0]
        if not several:
            choice.mode, choice.reason = 'single', ''
        if index != preferred and enabled[preferred] and not self.handoff_announced:
            self.handoff_announced = True
            skipped = self.names[preferred]
            self.store.event(self.pid, 'handoff',
                             Msg('handoff', to=label(name), who=label(skipped), reason=choice.reason,
                                 until=clock(avail[preferred].until)),
                             agent=name, data={'from': skipped})
        self.rotated = False
        chosen = self._apply_models(index)
        limits.take_tokens(self.pid)
        if model_roles.specialized(roles):
            chosen = Msg('models_role', models=chosen, role=model_roles.label(roles[index]),
                         work=Msg(f'work_{self.work}'))
        self.roles = roles
        self.usage_before = self._usage(name)
        if choice.mode == 'self_review':
            self.session_turns[name] = 0
        elif self.session_turns[name] >= ROTATE_AFTER:
            # A resumed session re-reads its whole history every turn: start a new one now and
            # then, and let the plan, the handoff and the repository carry the context.
            self.cfg.agents[index].session_id = None
            self.session_turns[name] = 0
            self.rotated = True
        self.session_turns[name] += 1
        self.in_self_review = choice.mode == 'self_review'
        if self.in_self_review:
            self.self_review_rounds += 1
            self.cfg.agents[index].session_id = None
        elif choice.mode == 'alternate':
            self.self_review_rounds = 0
            self.handoff_announced = False
        if choice.mode == 'single' and self.work == 'review' and not self.rotated:
            # One model only: the review runs in a new session, without the memory of the work it
            # reviews. Its independence is still limited, and the version level says so.
            self.cfg.agents[index].session_id = None
            self.session_turns[name] = 1
        self.current_message = message
        # The snapshot this turn keeps whatever the user changes meanwhile: changes apply from the next.
        agent = self.cfg.agents[index]
        config = {'agent': name, 'model': agent.model,
                  'effort': (os.environ.get('SOL83_GEMINI_EFFORT') if agent.backend == 'gemini'
                             else agent.reasoning_effort) or None,
                  'role': list(roles[index]), 'work': self.work, 'mode': choice.mode,
                  'selection': self.decision['mode'] if self.decision else 'manual',
                  'decision': self.decision,
                  'roles': {other: list(role) for other, role, on in zip(self.names, roles, enabled) if on},
                  'fresh_session': agent.session_id is None}
        self.store.set_live(self.pid, phase='turn_running', speaker=name, turn=turn,
                            mode=choice.mode, until=None, reason=choice.reason,
                            started_at=time.time(), config=json.dumps(config))
        self.store.event(self.pid, 'turn_start',
                         Msg(TURN_START.get(choice.mode, 'turn_start'), turn=turn, who=label(name),
                             models=chosen),
                         agent=name, data={'turn': turn, 'mode': choice.mode, 'work': self.work,
                                           'config': config})
        return index, self._compose(turn, index, message, choice)

    def after_turn(self, *, turn: int, speaker_idx: int, result, history: list,
                   stopping: bool) -> Outcome:
        turn += self.turns_before
        name = self.names[speaker_idx]
        entry = history[-1]
        # The user may set or change the test command while the project runs. Duet itself only ever
        # gets the sandboxed wrapper, which reads this command from the store.
        self.verify_raw = self.store.project(self.pid)['verify_cmd'] or None
        self.cfg.verify_cmd = sandbox.verify_command()
        failed = result.failure_reason is not None
        suffix = ' [niedokończona]' if failed else ''
        checkpoint = self.git.checkpoint(f'gemini: tura {turn} ({name}){suffix}')
        recap = self._recap(result, failed)
        lines = self.git.changed_lines('HEAD~1', 'HEAD') if checkpoint.changed else 0
        self.store.event(self.pid, 'turn_end', Msg('turn_end', turn=turn, who=label(name),
                                                   recap=recap), agent=name,
                         data={'turn': turn, 'elapsed_s': entry.get('elapsed_s'),
                               'commit': checkpoint.head, 'changed': checkpoint.changed,
                               'failed': failed, 'lines': lines, 'cost': self._turn_cost(name),
                               'asked_item': self.asked_item, 'fresh_session': self.rotated,
                               'work': self.work,
                               'tokens': self._tokens(name, entry, turn - self.turns_before, turn, speaker_idx),
                               'overlap': self._overlapping(name),
                               'session_turn': self.session_turns[name],
                               **({} if failed else goal_report(result.reply))},
                         body=result.reply)
        self.store.update_project(self.pid, status_detail=None)
        self.spoke[name] = turn
        if failed:
            self.store.requeue_notes(self.pid, turn)
            if not stopping:
                return self._on_failure(turn, speaker_idx, result, entry, checkpoint)
            self.last_speaker = name
            return Outcome()
        self.last_speaker = name
        self.last_changed, self.last_work = checkpoint.changed, self.work
        if self.store.setting(f'strikes_{name}', 0):
            self.store.set_setting(f'strikes_{name}', 0)
        self.failures = 0
        self.retries.clear()
        reply = section(_NOTE_REPLY, result.reply)
        if self.store.answer_notes(self.pid, turn, reply):
            self.store.event(self.pid, 'note_reply', Msg('note_reply', who=label(name)), agent=name,
                             body=reply)
        if self.inherited_instructed:
            self.inherited_instructed = False
            self.store.update_meta(self.pid, lambda meta: meta.pop('replan', None))
        self._record_plan(turn, checkpoint)
        self._take_requests(turn, name, speaker_idx)
        outcome = self._on_success(turn, name, result, checkpoint, recap)
        if outcome.converged and orders.open_work_count(self.store, self.pid):
            # Work arrived during this turn: a late acceptance of the old state cannot close the project.
            self.accepted.clear()
            self.store.event(self.pid, 'note', Msg('converge_deferred'))
            outcome = Outcome(converged=False)
        if outcome.converged:
            latest = self.store.latest_version(self.pid)
            if latest:
                orders.mark_done(self.store, self.pid, latest['number'], turn)
            self.store.event(self.pid, 'final', Msg('final_answer', who=label(name)), agent=name,
                             body=section(_SUMMARY, result.reply))
        return outcome

    def _take_requests(self, turn: int, name: str, index: int) -> None:
        """What the turn asked of the user: content proposals and questions or tests. Answers this
        turn received are now applied."""
        known = set(self.store.meta(self.pid).get('asset_known') or [])
        proposed = content.review_new(self.cfg.cwd, known, name)
        if proposed:
            self.store.update_meta(self.pid, lambda meta: meta.__setitem__(
                'asset_known', sorted({*(meta.get('asset_known') or []), *(item['id'] for item in proposed)})))
            for item in proposed:
                self.store.event(self.pid, 'asset', Msg('asset_proposed', who=label(name), id=item['id'],
                                                        path=item.get('path') or '?', status=item.get('status')),
                                 agent=name, data={'asset': item['id']})
        latest = self.store.latest_version(self.pid)
        revision = self.store.plan_revision(self.pid)
        context = {'model': self.cfg.agents[index].model, 'role': ','.join(self.roles[index]),
                   'version_number': latest['number'] if latest else None,
                   'commit_sha': self.git.head(), 'plan_revision': revision['revision'] if revision else None,
                   'lang': self.lang}
        for row in interactions.ingest(self.store, self.pid, self.cfg.cwd, name, context):
            self.store.event(self.pid, 'interaction', Msg(f"interaction_{row['type']}", who=label(name),
                                                          ref=row['ref'], text=row['text'][:160]),
                             agent=name, data={'interaction': row['id']})
        applied = [int(note['ref'][1:]) for note in self.store.notes(self.pid)
                   if note['kind'] == 'answer' and note['delivered_turn'] == turn and note['status'] == 'answered'
                   and str(note.get('ref') or '').startswith('I')]
        if applied:
            interactions.mark_applied(self.store, self.pid, applied)

    def _record_plan(self, turn: int, checkpoint: Checkpoint) -> None:
        """Keep the last valid plan as a revision; after too many failed repairs restore it."""
        state = project_plan.record(self.store, self.pid, self.cfg.cwd, turn)
        if state['state'] == 'valid' and state['revision']:
            text = Msg('plan_revision', revision=state['revision'],
                       corrections='; '.join(state['corrections'][:5]) or '-')
            self.store.event(self.pid, 'plan', text, data={'revision': state['revision'],
                                                           'corrections': state['corrections']})
        elif state['state'] == 'invalid':
            self.store.event(self.pid, 'plan', Msg('plan_invalid', problems='; '.join(state['problems'][:3]),
                                                   attempt=state['repairs'], limit=project_plan.plan_contract.MAX_REPAIRS))
        elif state['state'] == 'restored':
            self.git.checkpoint(f"sol83: przywrócono poprawny plan (rewizja {state['revision']})")
            self.store.event(self.pid, 'attention', Msg('plan_restored', revision=state['revision'],
                                                        problems='; '.join(state['problems'][:3])))

    # ---- Turn results -------------------------------------------------

    def _tokens(self, name: str, entry: dict, duet_turn: int, turn: int, index: int) -> Optional[dict]:
        """What the turn cost in tokens, as a per-turn delta (see usage.py): Claude reports the turn,
        Codex and Antigravity report their whole session so far."""
        saved = limits.take_tokens(self.pid)
        saved = saved if saved and saved.get('agent') == name else None
        raw, confirmed = (saved or {}).get('raw'), (saved or {}).get('model')
        log = entry.get('stderr_log_path') or self.run_dir / f'turn-{duet_turn:02d}-{name}.stderr.log'
        if name == 'codex' and Path(log).exists():
            text = Path(log).read_text(errors='replace')
            raw = usage.parse_codex_total(text[-4000:])
            found = _CODEX_MODEL.search(text)
            confirmed = found[1] if found else None
        agent = self.cfg.agents[index]
        per_turn = usage.record(self.store, self.pid, turn, name, raw, agent.session_id, agent.model, confirmed)
        if not per_turn:
            return None
        return {key: per_turn[key] for key in ('total', 'input', 'output', 'cache_read') if per_turn.get(key) is not None}

    def _overlapping(self, name: str) -> list:
        """Other projects with a turn of the same provider running now: the account's limit readings
        moved for both, so this turn's cost is not this project's alone."""
        return [row['project_id'] for row in self.store._rows(
            "SELECT project_id FROM live WHERE phase='turn_running' AND speaker=? AND project_id<>?",
            (name, self.pid))]

    def _recap(self, result, failed: bool) -> str:
        if failed:
            return Msg('turn_interrupted')
        match = _RECAP.search(result.recap_block or '')
        return match[1].strip() if match else Msg('turn_finished')

    def _on_success(self, turn: int, name: str, result, checkpoint: Checkpoint,
                    recap: str) -> Outcome:
        if self.accepted_tree != checkpoint.tree:
            self.accepted.clear()
            self.accepted_tree = checkpoint.tree
        wants_changes = _REQUESTS_CHANGES.search(result.reply or '')
        self.idle_agent = None if checkpoint.changed or wants_changes else name
        if self.in_self_review and not checkpoint.changed:
            if wants_changes:
                self.accepted.discard(name)
            else:
                self.self_reviewed_tree = checkpoint.tree
        version_ok = bool(_VERSION_OK.search(result.reply or ''))
        version = self._version_for(turn, name, result, checkpoint, recap, version_ok)
        steps = how_to_run(result.reply)
        if version and steps and version.get('how_to_run') != steps:
            self.store.update_version(self.pid, version['number'], how_to_run=steps)
        if result.convergence_hit:
            self.accepted.add(name)
        if version and (result.convergence_hit or version_ok) and not checkpoint.changed:
            if self.in_self_review:
                self._mark_self_reviewed(version, name)
            else:
                self._add_reviewer(version, name)
        meta = self.store.meta(self.pid)
        meta.update(lgtm=sorted(self.accepted), lgtm_tree=self.accepted_tree)
        self.store.save_meta(self.pid, meta)
        # Only models that are on and review may end the work: nobody waits for one that is off.
        # Ordered content holds the end back while a content creator is there to make it.
        enabled, roles = self._enabled(), self._roles()
        converged = self._converged(enabled, roles) and not (
            model_roles.creates_content(roles, enabled) and content.pending(self.cfg.cwd))
        if converged and version and version['tree'] == checkpoint.tree:
            self._mark_single(version, name)
        return Outcome(converged=converged, halt=not converged and self._stalled(checkpoint))

    def _version_for(self, turn, name, result, checkpoint, recap, version_ok) -> Optional[dict]:
        """Numbered versions exist only where the coordinator saw it work."""
        latest = self.store.latest_version(self.pid)
        if latest and latest['tree'] == checkpoint.tree:
            return latest
        verify_cmd = self.verify_raw
        if verify_cmd:
            if result.convergence_hit:
                self.verified[checkpoint.tree] = True
                self.last_verify = f'przeszły ({verify_cmd})'
            if not self._verify(turn, checkpoint.tree):
                return None
            level = 'tested'
            summary = Msg('summary_tests', command=verify_cmd)
        elif result.convergence_hit or version_ok:
            level = 'proposed'
            summary = Msg('summary_no_tests')
        else:
            return None
        prefix = f"gemini/{self.pid}"
        number = (latest['number'] if latest else 0) + 1
        self.git.tag(f'{prefix}/v{number}', checkpoint.head)
        version = self.store.add_version(
            self.pid, tag_prefix=prefix, commit_sha=checkpoint.head, tree=checkpoint.tree,
            level=level, turn=turn, agent=name, summary=recap,
            what_to_test=what_to_test(result.reply), how_to_run=how_to_run(result.reply),
            verify_summary=summary, accepted_by=[name])
        self.store.event(self.pid, 'version', Msg('version_new', number=version['number'],
                                                  sha=checkpoint.head[:7], summary=summary),
                         agent=name, data={'number': version['number']})
        # "What to check in this version" is a manual test record of this version (spec 13.6 and 21).
        if version.get('what_to_test'):
            interactions.supersede_version_checks(self.store, self.pid, version['number'])
            interactions.add(self.store, self.pid, 'manual_test', version['what_to_test'], 'version',
                             version_number=version['number'], commit_sha=checkpoint.head, lang=self.lang,
                             why=f"v{version['number']}")
        return version

    def _add_reviewer(self, version: dict, name: str) -> None:
        accepted_by = sorted({*version['accepted_by'], name})
        level = 'approved' if len(accepted_by) >= 2 else version['level']
        self.store.update_version(self.pid, version['number'], accepted_by=accepted_by, level=level)
        if level == 'approved' and version['level'] != 'approved':
            self.store.event(self.pid, 'version', Msg('version_approved', number=version['number']),
                             agent=name, data={'number': version['number']})

    def _mark_self_reviewed(self, version: dict, name: str) -> None:
        """Recorded apart from approval: one model never counts as two."""
        if version['level'] == 'approved':
            return
        self.store.update_version(self.pid, version['number'], level='self_reviewed')
        self.store.event(self.pid, 'version', Msg('version_self_reviewed', number=version['number'],
                                                  who=label(name)),
                         agent=name, data={'number': version['number']})

    def _mark_single(self, version: dict, name: str) -> None:
        """One model's acceptance, apart from the cross-check of two."""
        current = self.store.version(self.pid, version['number'])
        if current['level'] in ('approved', 'single') or len(current['accepted_by']) >= 2:
            return
        self.store.update_version(self.pid, version['number'], level='single')
        self.store.event(self.pid, 'version', Msg('version_single', number=version['number'],
                                                  who=label(name)),
                         agent=name, data={'number': version['number']})

    def _verify(self, turn: int, tree: str) -> bool:
        if tree in self.verified:
            return self.verified[tree]
        command = self.verify_raw
        log_path = self.run_dir / f'gemini-verify-{turn:02d}.log'
        # Tests are code the agents wrote: they run in the OS sandbox, never with the user's full rights.
        done = sandbox.run_shell(command, self.cfg.cwd, timeout=VERIFY_TIMEOUT,
                                 network=bool(self.store.setting('test_network', 0)),
                                 allow_unsandboxed=bool(self.store.setting('allow_unsandboxed', 0)))
        passed, output = done.returncode == 0, done.output
        log_path.write_text(output)
        self.verified[tree] = passed
        tail = output.strip().splitlines()[-1][:160] if output.strip() else ''
        self.last_verify = f"{'przeszły' if passed else 'NIE przeszły'} ({command}): {tail}"
        if not passed:
            lines = output.strip().splitlines()[-VERIFY_TAIL_LINES:]
            self.last_verify += f'\nPełny log: {log_path}\n' + '\n'.join(lines)
        self.store.event(self.pid, 'verify',
                         Msg('verify_passed' if passed else 'verify_failed', command=command, tail=tail),
                         data={'passed': passed, 'log': str(log_path)})
        return passed

    def _plan_lines(self, meta: dict, notes: list) -> list:
        """Where the work stands in the plan, and what the agent must decide now. Instructions that
        come from queued work (rebuild the plan, take an item first) follow the notes this turn took:
        if the turn dies, the notes go back to the queue and the next turn gets them again."""
        project = self.store.project(self.pid)
        plan, problem = project_plan.effective(self.store, project)
        file_plan, _ = project_plan.load(self.cfg.cwd)
        turns = monitor.turn_records(self.store, self.pid)
        self.asked_item = plan is not None
        if plan is None and not problem:
            return ['', project_plan.text(self.lang, 'create'), project_plan.text(self.lang, 'rules')]
        if meta.get('replan') == 'inherited':
            # A plan from an earlier project on this repository: no summary of it, a new plan first.
            self.inherited_instructed = True
            return ['', project_plan.text(self.lang, 'inherited'), project_plan.text(self.lang, 'rules')]
        focus = next((note['ref'] for note in notes if note.get('kind') == 'item' and note.get('ref')), None)
        lines = ['']
        if plan is not None:
            lines.append(project_plan.summary(plan, turns, focus, self.lang))
        if problem:
            repairs = meta.get('plan_repairs', 0)
            lines.append(project_plan.text(self.lang, 'problem', problem=problem, attempt=repairs + 1,
                                           limit=project_plan.plan_contract.MAX_REPAIRS)
                         + (project_plan.text(self.lang, 'stale') if file_plan is None and plan is not None else ''))
        for item, used in project_plan.overruns(plan, turns):
            lines.append(project_plan.text(self.lang, 'overrun', item=item['id'], used=used,
                                           budget=project_plan.budget(item)))
        if any(note.get('kind') == 'order' for note in notes):
            lines.append(project_plan.text(self.lang, 'replan'))
        lines.append(project_plan.text(self.lang, 'rules'))
        return lines

    def _item_over_halt(self):
        plan, _ = project_plan.load(self.cfg.cwd)
        for item, used in project_plan.overruns(plan, monitor.turn_records(self.store, self.pid)):
            if used > ITEM_HALT_FACTOR * project_plan.budget(item):
                return item, used
        return None

    def _steps_not_closer(self) -> int:
        """How many judged steps in a row the partner found not moving towards the goal."""
        count = 0
        for event in self.store.events(self.pid, 200):
            if event['kind'] != 'turn_end' or 'verdict' not in (event['data'] or {}):
                continue
            if event['data']['verdict'] not in ('not_closer', 'back'):
                break
            count += 1
        return count

    def _stalled(self, checkpoint: Checkpoint) -> bool:
        """Stop spending limits when the agents stopped making progress."""
        self.idle_turns = 0 if checkpoint.changed else self.idle_turns + 1
        if checkpoint.changed:
            self.tree_counts[checkpoint.tree] += 1
        latest = self.store.latest_version(self.pid)
        since_version = sum(1 for event in self.store.events(self.pid, 500)
                            if event['kind'] == 'turn_end'
                            and (event['data'] or {}).get('turn', 0) > (latest['turn'] if latest else 0))
        waiting_user = [row for row in interactions.open_items(self.store, self.pid)
                        if row['state'] == 'open' and (row['blocks'] or row['mandatory'])]
        if not checkpoint.changed and waiting_user:
            # Nothing moved and the work waits for the user: no more turns just to repeat the question.
            reason = Msg('stall_waiting_user', items=', '.join(row['ref'] for row in waiting_user[:6]))
        elif self.idle_turns >= MAX_IDLE_TURNS:
            reason = Msg('stall_idle', count=MAX_IDLE_TURNS)
        elif self.verify_raw and since_version >= NO_VERSION_HALT:
            reason = Msg('stall_no_version', count=since_version)
        elif self._steps_not_closer() >= NO_GOAL_HALT:
            reason = Msg('stall_goal', count=NO_GOAL_HALT)
        elif self._item_over_halt():
            item, used = self._item_over_halt()
            reason = Msg('stall_item', item=item['id'], turns=used, budget=project_plan.budget(item))
        elif self.tree_counts[checkpoint.tree] >= MAX_TREE_REPEATS:
            reason = Msg('stall_cycle')
        else:
            return False
        self.store.update_project(self.pid, status_detail=Msg('halted_detail', reason=reason))
        self.store.event(self.pid, 'attention', Msg('halted', reason=reason))
        return True

    # ---- Failures and takeover ----------------------------------------

    def _failure_text(self, entry: dict) -> str:
        text = entry.get('error') or ''
        log_path = entry.get('stderr_log_path')
        if log_path and Path(log_path).exists():
            text += '\n' + Path(log_path).read_text(errors='replace')[-4000:]
        return text

    def _on_failure(self, turn, index, result, entry, checkpoint: Checkpoint) -> Outcome:
        name = self.names[index]
        text = self._failure_text(entry)
        kind = limits.classify_failure(text, result.failure_reason)
        diagnosis = providers.diagnose(text)
        if kind == 'transient' and self.retries[name] < MAX_RETRIES:
            self.retries[name] += 1
            self.store.event(self.pid, 'retry', Msg('retry', who=label(name),
                                                    attempt=self.retries[name]), agent=name)
            time.sleep(self.retry_delay * self.retries[name])
            self.force_next = index
            return Outcome(message=self.current_message)
        until = self._block_failed_agent(name, kind, text)
        if kind != 'limit':
            self.failures += 1
            if self.failures >= MAX_FAILURES:
                self.store.event(self.pid, 'attention',
                                 Msg('failures_stop', reason=Msg(f'fail_{kind}')), agent=name)
                return Outcome()
        data = {'from': name, 'kind': kind, 'until': until, 'commit': checkpoint.head, 'diagnosis': diagnosis,
                'reset_source': self.reset_source}
        enabled = self._enabled()
        order = [i for i in self._order(self.work, enabled, self.roles, index, False) if i != index] \
            or [i for i, on in enumerate(enabled) if on and i != index]
        if not order:
            self.store.event(self.pid, 'takeover', Msg('turn_lost_single', who=label(name), turn=turn,
                                                       reason=Msg(f'fail_{kind}'), until=clock(until)),
                             agent=name, data=data)
            self.force_next = index
            return Outcome(message=self._takeover_message(turn, name, kind, checkpoint))
        avail = self._availability()
        successor = next((i for i in order if avail[i].available), order[0])
        partner = self.names[successor]
        self.store.event(self.pid, 'takeover',
                         Msg('takeover', who=label(name), turn=turn, reason=Msg(f'fail_{kind}'),
                             until=clock(until), to=label(partner)),
                         agent=partner, data=data)
        self.force_next = successor
        return Outcome(message=self._takeover_message(turn, name, kind, checkpoint))

    def _block_failed_agent(self, name: str, kind: str, text: str = '') -> float:
        """How long a failed provider gets no turns. A reset the provider stated in its error (Antigravity:
        "Resets in 144h11m44s") is used as it is; otherwise a reading, otherwise a growing estimate."""
        now = time.time()
        self.reset_source = None
        if kind == 'auth':
            until, reason = now + AUTH_BLOCK_S, Msg('needs_login')
        elif kind == 'limit':
            snapshot = self.reader.read(force=True).get(name)
            found = limits.availability(snapshot, self.store.threshold(name))
            stated = providers.reset_from_message(text, now)
            # Without a reading (Gemini has none) the pause doubles with each exhausted limit in a row.
            strikes = int(self.store.setting(f'strikes_{name}', 0))
            until = found.until or stated or now + limits.UNKNOWN_RESET_S * 2 ** min(strikes, 4)
            self.reset_source = 'reading' if found.until else 'provider_message' if stated else 'estimate'
            if not found.until and not stated:
                self.store.set_setting(f'strikes_{name}', strikes + 1)
            reason = found.reason or Msg('provider_limit')
        else:
            until, reason = now + FAILURE_BLOCK_S, Msg(f'fail_{kind}')
        self.store.set_block(name, until, reason)
        return until

    def _takeover_message(self, turn: int, name: str, kind: str, checkpoint: Checkpoint) -> str:
        lang = self.lang
        saved = (prompts.text(lang, 'takeover_saved', sha=checkpoint.head[:7]) if checkpoint.changed
                 else prompts.text(lang, 'takeover_nothing'))
        return prompts.text(lang, 'takeover', who=label(name), turn=turn,
                            reason=in_language(Msg(f'fail_{kind}'), lang), saved=saved)

    # ---- Handoff packet -----------------------------------------------

    def _announce_wait(self, choice: limits.Choice) -> None:
        self.store.set_live(self.pid, phase=choice.mode, speaker=None, until=choice.until,
                            reason=choice.reason, mode=choice.mode, started_at=None)
        key = (choice.mode, choice.reason, choice.until)
        if key == self.waiting_key:
            return
        self.waiting_key = key
        if choice.mode == 'waiting_partner':
            text = Msg('wait_partner', reason=choice.reason, until=clock(choice.until))
        elif choice.mode == 'waiting_role':
            text = Msg('wait_role', work=Msg(f'work_{self.work}'), reason=choice.reason,
                       until=clock(choice.until))
        elif sum(self._enabled()) == 1:
            text = Msg('wait_single', reason=choice.reason, until=clock(choice.until))
        else:
            text = Msg('wait_limits', reason=choice.reason, until=clock(choice.until))
        self.store.event(self.pid, 'waiting', text, data={'until': choice.until})

    def _limits_line(self) -> str:
        parts = []
        snapshots = self.reader.read()
        for name in self.names:
            if name not in limits.PROVIDERS:
                parts.append(f"{label(name)}: {in_language(Msg('no_reading'), self.lang)}")
                continue
            windows = (snapshots.get(name) or {}).get('windows') or {}
            read = ', '.join(f"{limits.window_label(key)} {value.get('used', 0):.0f}%"
                             for key, value in windows.items())
            parts.append(f"{label(name)}: {read or prompts.text(self.lang, 'no_reading')}")
        return '; '.join(parts)

    def _compose(self, turn: int, index: int, message: str, choice: limits.Choice) -> str:
        """The coordinator's context block for this turn, in the project's language."""
        lang = self.lang
        T = lambda key, **values: prompts.text(lang, key, **values)  # noqa: E731
        name = self.names[index]
        enabled = self._enabled()
        others = [label(other) for i, other in enumerate(self.names) if i != index and enabled[i]]
        partner = T('and').join(others) if others else T('other_model')
        meta = self.store.meta(self.pid)
        seen = meta.setdefault('seen', {})
        if choice.mode == 'single':
            team = T('team_single')
        else:
            team = T('team_partner' if len(others) == 1 else 'team_others', names=partner)
        lines = [T('header', turn=turn), T('you_are', who=label(name), team=team)]
        if lang != 'pl':
            lines.append(T('language_rule'))
        if model_roles.specialized(self.roles):
            roles = ', '.join(f'{label(other)}: {in_language(model_roles.label(role), lang)}' for other, role, on
                              in zip(self.names, self.roles, enabled) if on)
            lines += [model_roles.prompt(self.roles[index], lang), T('team_roles', roles=roles),
                      model_roles.WORK_LINES[self.work][lang]]
        if model_roles.creates_content(self.roles, enabled):
            if self.work == 'content':
                lines += [T('content_now'), content.summary(content.pending(self.cfg.cwd))]
            elif model_roles.CONTENT not in self.roles[index]:
                lines.append(content.rules(lang))
        fresh = choice.mode == 'self_review' or self.rotated
        if name not in seen or fresh:
            lines += ['', T('task'), self.cfg.task or self.project['task'], '', T('requests_rules')]
        if self.rotated:
            lines.append(T('rotated'))
        if choice.mode == 'self_review':
            lines.append(T('self_review', partner=partner, reason=in_language(choice.reason, lang)))
        if choice.mode == 'single':
            lines.append(T('single'))
        if choice.mode == 'solo':
            lines.append(T('solo', partner=partner, reason=in_language(choice.reason, lang)))
        lines.append(T('limits', line=self._limits_line()))
        latest = self.store.latest_version(self.pid)
        if latest:
            lines.append(T('latest', number=latest['number'], sha=latest['commit_sha'][:7], turn=latest['turn']))
        lines.append(T('tests', result=self.last_verify))
        head = self.git.head()
        changes = self.git.changes_since(
            self.project['base_commit'] if fresh else seen.get(name) or self.project['base_commit'])
        if changes:
            lines += [T('changes'), changes]
        status = self.git.dirty()
        if status:
            lines += [T('unsaved'), status]
        notes = self.store.take_notes(self.pid, name, turn)
        lines += self._plan_lines(meta, notes)
        lines += interactions.prompt_lines(self.store, self.pid, lang)
        if notes:
            self.accepted.clear()
            self.idle_agent = None
            lines += ['', T('notes')]
            lines += [f"- {note['text']}" for note in notes]
            lines.append(T('notes_reply'))
            self.store.event(self.pid, 'note_delivered',
                             Msg('note_delivered', who=label(name), count=len(notes)), agent=name)
        lines.append(T('summary_rule'))
        lines.append(T('goal_rule'))
        lines.append(T('end'))
        seen[name] = head
        self.store.save_meta(self.pid, meta)
        if choice.mode == 'self_review':
            message = T('start_review')
        elif self.last_speaker == name:
            message = T('continue_own')
        return '\n'.join(lines) + '\n\n' + message


def build(cfg, run_dir):
    project_id = os.environ.get('GEMINI_PROJECT_ID')
    if not project_id:
        return None
    return GeminiScheduler(cfg, Path(run_dir), Store(), project_id)
