"""Is the work still paying for itself? Signals that tell the user when to step in.

Value is what the coordinator saw: new versions and changed lines. Cost is what the
limits showed: the points each turn moved its provider's 5 h and weekly windows.
"""
from __future__ import annotations

import collections
import json
import os
import shutil
import subprocess
import sys

from . import usage
from .gitops import Git
from .messages import Msg, en
from .store import Store

WARN_TURNS_WITHOUT_VERSION = 3
HALT_TURNS_WITHOUT_VERSION = 8
CHURN_RATIO = 4
CHURN_MIN_LINES = 200
EXPENSIVE_WEEKLY_POINTS = 10
GOAL_FLAT_TURNS = 4
GOAL_VERDICTS = 3
RECENT = 5
CHURN_WINDOW = 6
WEEK = 'seven_day'


def turn_records(store: Store, project_id: str) -> list:
    rows = [event for event in store.events(project_id, 5000) if event['kind'] == 'turn_end']
    return [dict(event, **(event['data'] or {})) for event in reversed(rows)]


def _cost_text(costs: dict) -> Msg:
    return Msg('mon_cost', claude=f"{costs.get('claude', 0):.0f}", codex=f"{costs.get('codex', 0):.0f}")


def assess(store: Store, project: dict, with_git: bool = True) -> dict:
    project_id = project['id']
    turns = turn_records(store, project_id)
    versions = store.versions(project_id)
    last_turn = versions[0]['turn'] if versions else 0
    since = [turn for turn in turns if (turn.get('turn') or 0) > last_turn]
    weekly = collections.Counter()
    weekly_since = collections.Counter()
    for turn in turns:
        points = (turn.get('cost') or {}).get(WEEK) or 0
        weekly[turn['agent']] += points
        if turn in since:
            weekly_since[turn['agent']] += points
    gross = sum(turn.get('lines') or 0 for turn in since)
    net = gross
    window = turns[-CHURN_WINDOW:]
    window_gross = sum(turn.get('lines') or 0 for turn in window)
    window_net = window_gross
    if with_git and project.get('worktree') and os.path.isdir(project['worktree']):
        git = Git(project['worktree'])
        base = versions[0]['commit_sha'] if versions else project['base_commit']
        net = git.changed_lines(base, 'HEAD')
        before = turns[-CHURN_WINDOW - 1].get('commit') if len(turns) > CHURN_WINDOW else project['base_commit']
        if before:
            window_net = git.changed_lines(before, 'HEAD')
    signals = []

    def signal(key, message):
        signals.append({'key': key, 'text': str(message), 'text_en': en(message)})

    if len(since) >= WARN_TURNS_WITHOUT_VERSION:
        signal('no_version', Msg('mon_no_version', count=len(since), cost=_cost_text(weekly_since)))
    if window_gross >= CHURN_MIN_LINES and window_gross >= CHURN_RATIO * max(window_net, 1):
        signal('churn', Msg('mon_churn', gross=window_gross, net=window_net, turns=len(window)))
    failed = sum(1 for turn in turns[-RECENT:] if turn.get('failed'))
    if failed >= 2:
        signal('failed', Msg('mon_failed', count=failed))
    verifies = [event for event in store.events(project_id, 60) if event['kind'] == 'verify'][:3]
    if len(verifies) == 3 and all((json.loads(event['data'] or '{}') if isinstance(event['data'], str)
                                   else event['data'] or {}).get('passed') is False for event in verifies) \
            and len({event['text'] for event in verifies}) == 1:
        signal('verify', Msg('mon_verify', count=3, tail=verifies[0]['text'][-160:]))
    if since and max(weekly_since.values() or [0]) >= EXPENSIVE_WEEKLY_POINTS:
        signal('expensive', Msg('mon_expensive', cost=_cost_text(weekly_since)))
    goals = [(turn['goal_done'], turn['goal_total']) for turn in turns if 'goal_done' in turn]
    verdicts = [turn['verdict'] for turn in turns if turn.get('verdict')]
    recent_goals = goals[-GOAL_FLAT_TURNS:]
    if len(recent_goals) == GOAL_FLAT_TURNS and len({done for done, _ in recent_goals}) == 1 \
            and recent_goals[-1][0] < recent_goals[-1][1]:
        signal('goal_flat', Msg('mon_goal_flat', done=recent_goals[-1][0], total=recent_goals[-1][1],
                                count=GOAL_FLAT_TURNS))
    if len(verdicts) >= GOAL_VERDICTS and all(v in ('not_closer', 'back') for v in verdicts[-GOAL_VERDICTS:]):
        signal('goal_verdicts', Msg('mon_goal_verdicts', count=GOAL_VERDICTS))
    if project.get('worktree') and os.path.isdir(project['worktree']):
        from . import plan as project_plan
        plan, _ = project_plan.load(project['worktree'])
        if plan is not None:
            recent = turns[-4:]
            missing = sum(1 for turn in recent if turn.get('asked_item') and not turn.get('item')
                          and not turn.get('failed'))
            if len(recent) == 4 and missing >= 2:
                signal('unassigned', Msg('mon_unassigned', count=missing, total=len(recent)))
            spent = project_plan.spend(turns)
            for item, used in project_plan.overruns(plan, turns):
                signal('overrun', Msg('mon_overrun', item=item['id'], turns=used,
                                      budget=project_plan.budget(item),
                                      week=round(spent[item['id']]['week'])))
    count = max(len(versions), 1)
    # Tokens from the normalized per-turn records (usage.py): deltas, never cumulative counters
    # added up, and None where a provider does not report a category.
    measured = usage.summary(store, project_id)
    tokens: dict = {}
    for row in measured['rows']:
        entry = tokens.setdefault(row['agent'], {'turns': 0, 'total': 0, 'input': None, 'output': None})
        entry['turns'] += row['turns']
        entry['total'] += row['total'] or 0
        for key in ('input', 'output'):
            if row[key] is not None:
                entry[key] = (entry[key] or 0) + row[key]
    token_turns = [{**row, 'session_turn': None, 'fresh': False} for row in measured['turns']][-10:]
    return {'tokens': tokens, 'token_turns': token_turns, 'usage': measured['rows'],
            'windows': usage.windows(turns),'goal': list(goals[-1]) if goals else None, 'goal_history': [done for done, _ in goals[-10:]],
            'verdicts': verdicts[-6:],'level': 'warn' if signals else 'ok', 'signals': signals, 'turns': len(turns),
            'versions': len(versions), 'since_version': len(since),
            'weekly_points': dict(weekly), 'weekly_since': dict(weekly_since),
            'weekly_per_version': {agent: round(points / count, 1) for agent, points in weekly.items()},
            'lines_since': gross, 'lines_net': net, 'failed_recent': failed}


def notify(text: str) -> None:
    """A desktop notification, so the user hears about it without the panel open. Best effort:
    a missing notifier (Linux without notify-send, a server without a desktop) is never an error."""
    if os.environ.get('GEMINI_NOTIFY', '1') == '0':
        return
    safe = text.replace('\\', '').replace('"', "'")[:220]
    if sys.platform == 'darwin':
        command = ['osascript', '-e', f'display notification "{safe}" with title "Sol-83"']
    elif shutil.which('notify-send'):
        command = ['notify-send', 'Sol-83', safe]
    else:
        return
    try:
        subprocess.run(command, capture_output=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        pass
