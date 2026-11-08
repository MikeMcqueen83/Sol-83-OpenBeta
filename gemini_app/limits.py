"""Subscription limits of Codex and Claude: reading, failure classes, availability.

Both readings are free: Codex answers `account/rateLimits/read` on its app-server
and `claude -p /usage` is served locally without a model call. Nothing here may
fall back to paid usage.
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

from .messages import Msg
from .paths import BIN, STATE, agent_path, clean_env

FIVE_HOUR = 'five_hour'
SEVEN_DAY = 'seven_day'
DEFAULT_THRESHOLD = 95.0
# How long a provider gets no new turn when nothing says when it comes back. These are guesses, and
# the panel labels them as such; the user can always lift a pause with "Try now". A reset the
# provider stated (in the error or in a reading) always wins over a guess.
UNKNOWN_RESET_S = 900          # an exhausted limit with no reset time: 15 min, doubling with each repeat
UNKNOWN_RESET_MAX_S = 7200     # ... up to 2 h
TRANSIENT_BLOCK_S = 300        # rate limit, network, outage, after the quick retries in place: 5 min
FAILURE_BLOCK_S = 600          # timeout or an unclassified agent error: 10 min
AUTH_BLOCK_S = 3600            # signing in again is the user's step; "Try now" after it
# `claude /usage` gives reset times to the minute and rounds down: a turn started at the shown
# minute was still rejected (2026-11-08: shown 2:59am, the provider's own resetsAt was 03:00:00).
USAGE_MINUTE_GRACE_S = 60
PROVIDERS = ('claude', 'codex')
API_ENV_KEYS = ('ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'OPENAI_API_KEY', 'CODEX_API_KEY',
                'CLAUDE_CODE_USE_BEDROCK', 'CLAUDE_CODE_USE_VERTEX', 'CLAUDE_CODE_USE_FOUNDRY')

_LIMIT = re.compile(r"hit your (\w+ )?limit|usage limit|limit reached|rate_limit_reached"
                    r"|out of (extra usage|codex messages)|credit balance (is )?too low"
                    r"|RESOURCE_EXHAUSTED|quota exceeded|exhausted your (daily )?quota", re.I)
GEMINI_KEY_ENV = ('GEMINI_API_KEY', 'GOOGLE_API_KEY', 'GOOGLE_GENAI_USE_VERTEXAI', 'GOOGLE_GENAI_USE_GCA',
                  'GOOGLE_APPLICATION_CREDENTIALS')
_AUTH = re.compile(r"/login|not logged in|session expired|oauth token|invalid api key"
                   r"|failed to authenticate|codex login|\b401\b|authori[sz]ation url|please sign in", re.I)
_TRANSIENT = re.compile(r"overloaded|\b5(00|02|03|04|29)\b|too many requests|\b429\b"
                        r"|stream disconnected|connection (reset|error|refused)|econnreset"
                        r"|etimedout|network error|temporarily unavailable", re.I)
_MONTHS = {m: i + 1 for i, m in enumerate(
    'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split())}
_RESET = re.compile(r'(?:(?P<mon>[A-Z][a-z]{2})\s+(?P<day>\d{1,2})(?:,\s*(?P<year>\d{4}))?\s+at\s+)?'
                    r'(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\s*(?P<ampm>am|pm)')


def _env() -> dict:
    return {**clean_env(), 'PATH': agent_path()}


def _codex_snapshot(result: dict, now: float) -> dict:
    limits = result.get('rateLimits') or {}
    windows = {}
    for window in (limits.get('primary'), limits.get('secondary')):
        if not window:
            continue
        minutes = window.get('windowDurationMins')
        key = {300: FIVE_HOUR, 10080: SEVEN_DAY}.get(minutes, f'{minutes}m')
        windows[key] = {'used': float(window.get('usedPercent') or 0),
                        'resets_at': window.get('resetsAt')}
    return {'provider': 'codex', 'source': 'codex app-server', 'read_at': now, 'windows': windows,
            'plan': limits.get('planType'), 'allowed': result.get('ordinaryUsageAllowed'),
            'overage': False}


def codex_call(method: str, params: Optional[dict] = None, timeout: float = 15) -> dict:
    """One JSON-RPC request on a short-lived app-server; raises OSError on failure."""
    proc = subprocess.Popen(['codex', 'app-server'], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            text=True, env=_env())
    replies: dict = {}
    arrived = threading.Event()

    def reader():
        for line in proc.stdout:
            try:
                message = json.loads(line)
            except ValueError:
                continue
            if 'id' in message:
                replies[message['id']] = message
                arrived.set()

    listener = threading.Thread(target=reader, daemon=True)
    listener.start()

    def request(payload, reply_id):
        proc.stdin.write(json.dumps(payload) + '\n')
        proc.stdin.flush()
        deadline = time.monotonic() + timeout
        while reply_id not in replies and time.monotonic() < deadline:
            arrived.wait(0.1)
            arrived.clear()
        return replies.get(reply_id)

    try:
        if not request({'id': 1, 'method': 'initialize',
                        'params': {'clientInfo': {'name': 'projectgemini', 'version': '1.0'}}}, 1):
            raise OSError('app-server nie odpowiada')
        proc.stdin.write(json.dumps({'method': 'initialized'}) + '\n')
        reply = request({'id': 2, 'method': method, 'params': params or {}}, 2)
        if not reply or 'result' not in reply:
            raise OSError(f'brak odpowiedzi na {method}')
        return reply['result']
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        listener.join(timeout=2)
        for pipe in (proc.stdin, proc.stdout):
            try:
                pipe.close()
            except (OSError, ValueError):
                pass


def read_codex(timeout: float = 15) -> dict:
    now = time.time()
    try:
        return _codex_snapshot(codex_call('account/rateLimits/read', timeout=timeout), now)
    except (OSError, ValueError) as exc:
        return {'provider': 'codex', 'read_at': now, 'error': str(exc), 'windows': {}}


def _parse_reset(text: str, tz_name: str, now: float) -> Optional[float]:
    """"Nov 2 at 2:49am" or "2:49am" in the given zone, as epoch seconds."""
    match = _RESET.search(text)
    if not match:
        return None
    try:
        zone = ZoneInfo(tz_name)
    except Exception:
        zone = None
    local_now = dt.datetime.fromtimestamp(now, zone)
    hour = int(match['hour']) % 12 + (12 if match['ampm'] == 'pm' else 0)
    minute = int(match['minute'] or 0)
    if match['mon']:
        year = int(match['year'] or local_now.year)
        moment = local_now.replace(year=year, month=_MONTHS[match['mon']], day=int(match['day']),
                                   hour=hour, minute=minute, second=0, microsecond=0)
        if moment < local_now - dt.timedelta(days=1):
            moment = moment.replace(year=year + 1)
    else:
        moment = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if moment < local_now:
            moment += dt.timedelta(days=1)
    return moment.timestamp()


def parse_claude_usage(text: str, now: float) -> Optional[dict]:
    """Parse the `/usage` report; None when its format is not recognized."""
    windows = {}
    for label, key in (('Current session', FIVE_HOUR), (r'Current week \(all models\)', SEVEN_DAY)):
        match = re.search(label + r':\s*([\d.]+)% used(?:\s*·\s*resets (.+?)\s*\((.+?)\))?', text)
        if match:
            reset = _parse_reset(match[2], match[3], now) if match[2] else None
            windows[key] = {'used': float(match[1]),
                            'resets_at': reset + USAGE_MINUTE_GRACE_S if reset else None}
    if not windows:
        return None
    return {'provider': 'claude', 'source': 'claude /usage', 'read_at': now, 'windows': windows,
            'overage': False}


def save_claude_event(info: dict) -> None:
    """Persist a `rate_limit_event` seen during a turn (written by bin/claude)."""
    now = time.time()
    windows = {key: {'used': round(float(value.get('utilization') or 0) * 100, 1),
                     'resets_at': value.get('resetsAt')}
               for key, value in (info.get('unifiedWindows') or {}).items()}
    snapshot = {'provider': 'claude', 'source': 'zdarzenie Claude', 'read_at': now,
                'windows': windows, 'status': info.get('status'),
                'resets_at': info.get('resetsAt'), 'overage': bool(info.get('isUsingOverage'))}
    STATE.mkdir(parents=True, exist_ok=True)
    temp = STATE / f'limits-claude.{os.getpid()}.tmp'
    temp.write_text(json.dumps(snapshot))
    temp.replace(STATE / 'limits-claude.json')


def token_counts(usage) -> Optional[dict]:
    """Tokens of one turn from a provider's usage record. Input counts the cache too,
    because that is the context the turn read."""
    if not isinstance(usage, dict):
        return None

    def pick(*keys):
        return sum(int(usage.get(key) or 0) for key in keys if isinstance(usage.get(key), (int, float)))
    # Claude counts cache reads apart from input_tokens; Antigravity's input_tokens already hold them.
    apart = pick('cache_read_input_tokens')
    inside = pick('cache_read_tokens', 'cached_tokens', 'cachedTokens')
    fresh = pick('input_tokens', 'prompt_tokens', 'inputTokens', 'promptTokens', 'cache_creation_input_tokens')
    output = pick('output_tokens', 'completion_tokens', 'outputTokens', 'candidatesTokens')
    if not fresh + apart + output:
        return None
    return {'input': fresh + apart, 'cached': apart + inside, 'output': output, 'total': fresh + apart + output}


def save_tokens(project_id: str, agent: str, usage, model: Optional[str] = None) -> None:
    """Written by an adapter at the end of a turn, read once by the scheduler. Keeps the provider's raw
    record and the model the CLI reported, so the scheduler can normalize and confirm the model."""
    counts = token_counts(usage)
    if not counts and not model:
        return
    STATE.mkdir(parents=True, exist_ok=True)
    temp = STATE / f'tokens-{project_id}.{os.getpid()}.tmp'
    temp.write_text(json.dumps({'agent': agent, 'tokens': counts, 'raw': usage if isinstance(usage, dict) else None,
                                'model': model}))
    temp.replace(STATE / f'tokens-{project_id}.json')


def take_tokens(project_id: str) -> Optional[dict]:
    path = STATE / f'tokens-{project_id}.json'
    try:
        saved = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    path.unlink(missing_ok=True)
    return saved


def read_claude_event() -> Optional[dict]:
    try:
        return json.loads((STATE / 'limits-claude.json').read_text())
    except (OSError, ValueError):
        return None


def read_claude(timeout: float = 30) -> dict:
    """Free `/usage` reading, then the last event seen during a turn."""
    now = time.time()
    event = read_claude_event()
    try:
        done = subprocess.run([str(BIN / 'claude'), '-p', '/usage', '--output-format', 'json',
                               '--no-session-persistence', '--model', 'haiku'],
                              capture_output=True, text=True, timeout=timeout,
                              stdin=subprocess.DEVNULL, env=_env())
        snapshot = parse_claude_usage(json.loads(done.stdout).get('result') or '', now)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        snapshot = None
    if snapshot:
        if event and event.get('status') == 'rejected' and event.get('read_at', 0) > now - 300:
            # The rejection carries the provider's own reset time: without it the pause was a guess
            # (a 30 min block at 02:59 for a limit the provider said resets at 03:00).
            snapshot['status'] = 'rejected'
            if (event.get('resets_at') or 0) > now:
                snapshot['resets_at'] = event['resets_at']
        return snapshot
    return event or {'provider': 'claude', 'read_at': now, 'error': 'brak odczytu limitów',
                     'windows': {}}


class Reader:
    """Cached readings for both providers."""

    def __init__(self, ttl: float = 45):
        self.ttl = ttl
        self.cached: dict = {}
        self.read_at = 0.0

    def read(self, force: bool = False) -> dict:
        if force or time.time() - self.read_at >= self.ttl or not self.cached:
            self.cached = {'claude': read_claude(), 'codex': read_codex()}
            self.read_at = time.time()
        return self.cached


@dataclasses.dataclass
class Availability:
    available: bool
    until: Optional[float] = None
    reason: str = ''
    # True when `until` is Sol-83's guess, not a time the provider gave: the panel says so.
    estimate: bool = False


@dataclasses.dataclass
class Choice:
    speaker: Optional[int]
    mode: str
    until: Optional[float] = None
    reason: str = ''
    # The model the project waits for (the one back soonest), when nobody can take the turn.
    waiting_for: Optional[int] = None


def failure_pause(kind: str, consecutive: int) -> float:
    """The pause after the n-th failure in a row of one provider that is not a limit: it doubles with each
    repeat, up to UNKNOWN_RESET_MAX_S, so a broken CLI or session is not retried every few minutes for hours."""
    base = AUTH_BLOCK_S if kind == 'auth' else TRANSIENT_BLOCK_S if kind == 'transient' else FAILURE_BLOCK_S
    return min(base * 2 ** max(0, consecutive - 1), max(base, UNKNOWN_RESET_MAX_S))


def unknown_reset_pause(strikes: int) -> float:
    """The guessed pause after an exhausted limit with no reset time, growing with repeats."""
    return min(UNKNOWN_RESET_S * 2 ** max(0, strikes), UNKNOWN_RESET_MAX_S)


def window_label(key: str):
    return Msg(f'window_{key}') if key in (FIVE_HOUR, SEVEN_DAY) else key


def availability(snapshot: Optional[dict], threshold=DEFAULT_THRESHOLD,
                 block: Optional[dict] = None, now: Optional[float] = None) -> Availability:
    """Can this provider start a new turn? Unknown state is allowed: a real
    rejection then blocks it with evidence, instead of guessing it is down.

    `threshold` is one percentage for every window, or {window: percentage}.
    Below 100% it is the user's own reserve, and the reason says so.
    """
    now = now or time.time()
    if block and block['until'] > now:
        return Availability(False, block['until'], block['reason'], estimate=block.get('source') == 'estimate')
    if not snapshot or snapshot.get('error'):
        return Availability(True, None, Msg('limit_unknown'))
    until = None
    reason = ''
    estimate = False
    for key, window in (snapshot.get('windows') or {}).items():
        resets_at = window.get('resets_at')
        if resets_at and resets_at <= now:
            continue
        limit = threshold.get(key, 100.0) if isinstance(threshold, dict) else threshold
        used = window.get('used', 0)
        if used >= limit:
            moment = resets_at or now + UNKNOWN_RESET_S
            if until is None or moment > until:
                percent = f'{used:.0f}'
                estimate = not resets_at
                until, reason = moment, (
                    Msg('reserve_reason', window=window_label(key), percent=percent,
                        threshold=f'{limit:.0f}') if used < 100
                    else Msg('window_reason', window=window_label(key), percent=percent))
    if until is None and (snapshot.get('status') == 'rejected' or snapshot.get('allowed') is False
                          or snapshot.get('overage')):
        fallback = snapshot.get('resets_at') or now + UNKNOWN_RESET_S
        until, reason, estimate = max(fallback, now + 60), Msg('provider_rejects'), not snapshot.get('resets_at')
    return Availability(until is None, until, reason, estimate)


def remaining(snapshot: Optional[dict], now: Optional[float] = None) -> float:
    """Percent still usable: the tighter of the live windows."""
    now = now or time.time()
    left = 100.0
    for window in ((snapshot or {}).get('windows') or {}).values():
        resets_at = window.get('resets_at')
        if not resets_at or resets_at > now:
            left = min(left, 100.0 - window.get('used', 0))
    return left


def choose_speaker(preferred: int, avail: list, accepted: list,
                   self_review: bool = False) -> Choice:
    """Two models: the next speaker, given who should go next by alternation."""
    return choose_among([preferred, 1 - preferred], avail, accepted, self_review)


def choose_among(order: list, avail: list, accepted: list, self_review: bool = False) -> Choice:
    """Next speaker from the models able to take this turn, best first.

    `accepted[i]` means model i has already accepted the current code: giving
    it another turn alone would only burn its limit, so it waits for review,
    unless Full Power (`self_review`) trades that limit for not waiting.
    'solo' means no other model is available right now; 'waiting_role' means
    one is, but this work is not its role.
    """
    ready = [i for i in order if avail[i].available]
    if not ready:
        mode = 'waiting_role' if any(item.available for item in avail) else 'waiting_limits'
        if not order:
            return Choice(None, mode)
        soonest = min(order, key=lambda i: avail[i].until or float('inf'))
        return Choice(None, mode, avail[soonest].until, avail[soonest].reason, soonest)
    first = order[0]
    # A model that already accepted the current code does not get a turn just for being first in line while a
    # partner that has not accepted yet is away (PR9/26: five "nothing changed" turns while Gemini was down):
    # that partner's review is awaited. With nobody to wait for, the first in line goes on as before.
    awaited = any(not avail[i].available and not accepted[i] for i in order)
    if first in ready and not (accepted[first] and awaited):
        speaker = first
    else:
        fresh = [i for i in ready if not accepted[i]]
        if fresh:
            speaker = fresh[0]
        elif self_review:
            return Choice(ready[0], 'self_review', reason=avail[first].reason)
        else:
            # The review comes from whichever reviewer is back first, not from the first in order:
            # 2026-11-08 a project showed Codex's weekly reset (two days) while Claude was back that night.
            pending = [i for i in order if not avail[i].available and not accepted[i]] or [first]
            soonest = min(pending, key=lambda i: avail[i].until or float('inf'))
            return Choice(None, 'waiting_partner', avail[soonest].until, avail[soonest].reason, soonest)
    partners = [i for i in range(len(avail)) if i != speaker]
    if any(avail[i].available for i in partners):
        return Choice(speaker, 'alternate', reason='' if speaker == first else avail[first].reason)
    down = first if speaker != first else next((i for i in partners if avail[i].until), partners[0])
    return Choice(speaker, 'solo', reason=avail[down].reason)


def classify_failure(text: str, finished_reason: str = '') -> str:
    if finished_reason == 'timeout':
        return 'timeout'
    if _LIMIT.search(text or ''):
        return 'limit'
    if _AUTH.search(text or ''):
        return 'auth'
    if _TRANSIENT.search(text or ''):
        return 'transient'
    return 'other'


def gemini_binary() -> Optional[str]:
    """Antigravity CLI `agy`, which runs Gemini for Sol-83's own adapter in bin/gemini."""
    override = os.environ.get('GEMINI_CLI_BIN')
    if override:
        return override if Path(override).exists() else None
    path = os.pathsep.join(part for part in agent_path().split(os.pathsep) if Path(part) != BIN)
    return shutil.which('agy', path=path)


def gemini_problem() -> Optional[str]:
    """Why Gemini cannot work. agy signs in on first use and keeps the login in the
    keychain, so a missing login shows up as a sign-in error on the first turn."""
    return None if gemini_binary() else Msg('auth_gemini_missing')


def check_auth(providers=PROVIDERS) -> Optional[str]:
    """Subscription-only guard. Returns a user message when the setup is unsafe.
    Only the providers that will work are checked: a model switched off needs no login."""
    if any(os.environ.get(key) for key in API_ENV_KEYS):
        return Msg('auth_api')
    if 'claude' in providers:
        problem = _check_claude()
        if problem:
            return problem
    if 'codex' in providers:
        codex = subprocess.run(['codex', 'login', 'status'], capture_output=True, text=True, env=_env())
        if codex.returncode or 'ChatGPT' not in codex.stdout + codex.stderr:
            return Msg('auth_codex')
    if 'gemini' in providers:
        return gemini_problem()
    return None


def _check_claude() -> Optional[str]:
    claude = subprocess.run([str(BIN / 'claude'), 'auth', 'status'], capture_output=True,
                            text=True, env=_env())
    try:
        auth = json.loads(claude.stdout)
    except ValueError:
        return Msg('auth_claude_check')
    if not auth.get('loggedIn'):
        return Msg('auth_claude_login', path=BIN)
    if 'api' in str(auth.get('authMethod', '')).lower():
        return Msg('auth_claude_api')
    return None
