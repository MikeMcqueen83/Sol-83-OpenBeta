"""Provider panel: is each agent CLI installed, signed in, on which account and plan, and what
its limits are. Every check here is free: no model is called and no limit is used. A test that
does use a limit is a separate, explicit action (`probe`).

Failures are told apart instead of being lumped into "error": not signed in, expired session,
wrong account, no access to the model, subscription limit, rate limit, network, provider outage.
When the cause is not clear the class is 'unknown' and the panel says so.
"""
from __future__ import annotations

import json
import re
import subprocess
import time
from typing import Optional

from . import limits
from .paths import BIN, agent_path

CLASSES = ('not_logged_in', 'session_expired', 'wrong_account', 'no_model_access', 'plan_limit',
           'rate_limit', 'network', 'provider_outage', 'unknown')
_PATTERNS = (
    ('session_expired', r'session expired|token (has )?expired|refresh token|re-?authenticate|please log ?in again'),
    ('not_logged_in', r'not logged in|/login|please sign in|codex login|no credentials|unauthenticated|\b401\b'),
    ('wrong_account', r'organization .* (not|does not)|wrong account|account mismatch|workspace .* not allowed'),
    ('no_model_access', r'model .*(not (found|available|supported)|unavailable|does not exist)|no access to (the )?model'
                        r'|permission denied for model|\b404\b.*model'),
    ('plan_limit', r'individual quota|quota (reached|exceeded)|usage limit|hit your (\w+ )?limit|limit reached'
                   r'|out of (extra usage|codex messages)|upgrade (your )?(subscription|plan)|exhausted your'),
    ('rate_limit', r'rate.?limit|too many requests|\b429\b|slow down'),
    ('network', r'econnreset|etimedout|enotfound|network (error|is unreachable)|connection (reset|refused|error)'
                r'|getaddrinfo|could not resolve|stream disconnected|tls handshake'),
    ('provider_outage', r'overloaded|\b5(00|02|03|04)\b|internal server error|service unavailable|temporarily unavailable'),
)
_RESETS_IN = re.compile(r'resets? in\s+(?:(\d+)\s*d)?\s*(?:(\d+)\s*h)?\s*(?:(\d+)\s*m)?\s*(?:(\d+)\s*s)?', re.I)
LOGIN = {'claude': './bin/claude auth login', 'codex': 'codex login', 'gemini': 'agy -p "test"  (pierwsze uruchomienie otwiera logowanie Google)'}
STALE_S = 15 * 60


def diagnose(text: str) -> str:
    """The failure class of a CLI's error output. Order matters: an expired session also says
    "log in", a subscription limit also says 429."""
    for name, pattern in _PATTERNS:
        if re.search(pattern, text or '', re.I):
            return name
    return 'unknown'


def reset_from_message(text: str, now: Optional[float] = None) -> Optional[float]:
    """A reset time the provider itself stated in the error ("Resets in 144h11m44s")."""
    match = _RESETS_IN.search(text or '')
    if not match or not any(match.groups()):
        return None
    days, hours, minutes, seconds = (int(g or 0) for g in match.groups())
    return (time.time() if now is None else now) + days * 86400 + hours * 3600 + minutes * 60 + seconds


def _run(command: list, timeout: float = 30) -> tuple:
    try:
        done = subprocess.run(command, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL,
                              env={**limits._env(), 'PATH': agent_path()})
        return done.returncode, done.stdout, done.stderr
    except (OSError, subprocess.SubprocessError) as exc:
        return None, '', str(exc)


def _first_line(text: str) -> str:
    return (text or '').strip().splitlines()[0][:120] if (text or '').strip() else ''


def check_claude() -> dict:
    code, out, err = _run([str(BIN / 'claude'), '--version'])
    row = {'provider': 'claude', 'installed': code == 0, 'version': _first_line(out) or None}
    if code != 0:
        return {**row, 'auth': 'missing_cli', 'problem': _first_line(err or out) or 'brak CLI'}
    code, out, err = _run([str(BIN / 'claude'), 'auth', 'status'])
    try:
        auth = json.loads(out)
    except ValueError:
        return {**row, 'auth': 'unknown', 'problem': diagnose(err or out)}
    row.update(account=auth.get('email'), organization=auth.get('orgName'), method=auth.get('authMethod'))
    if not auth.get('loggedIn'):
        return {**row, 'auth': 'not_logged_in'}
    if 'api' in str(auth.get('authMethod', '')).lower():
        return {**row, 'auth': 'api_key', 'problem': 'logowanie kluczem API: Sol-83 tego nie używa'}
    # The CLI reports the subscription of the signed-in account: that is a reliable source.
    return {**row, 'auth': 'ok', 'plan': auth.get('subscriptionType'), 'plan_source': 'claude auth status'}


def check_codex() -> dict:
    code, out, err = _run(['codex', '--version'])
    row = {'provider': 'codex', 'installed': code == 0, 'version': _first_line(out) or None}
    if code != 0:
        return {**row, 'auth': 'missing_cli', 'problem': _first_line(err or out) or 'brak CLI'}
    code, out, err = _run(['codex', 'login', 'status'])
    if code != 0 or 'ChatGPT' not in out + err:
        return {**row, 'auth': diagnose(out + err) if 'API' not in out + err else 'api_key',
                'problem': _first_line(out or err)}
    try:
        account = (limits.codex_call('account/read').get('account') or {})
    except (OSError, ValueError, KeyError):
        account = {}
    return {**row, 'auth': 'ok', 'account': account.get('email'), 'organization': account.get('workspaceName'),
            'plan': account.get('planType'), 'plan_source': 'codex app-server account/read' if account else None}


def check_gemini() -> dict:
    binary = limits.gemini_binary()
    row = {'provider': 'gemini', 'installed': bool(binary), 'version': None}
    if not binary:
        return {**row, 'auth': 'missing_cli', 'problem': 'brak agy'}
    code, out, _ = _run([binary, '--version'])
    row['version'] = _first_line(out) if code == 0 else None
    code, out, err = _run([binary, 'models'], timeout=45)
    models = [line.split('\t', 1)[0] for line in out.splitlines() if '\t' in line]
    if code == 0 and models:
        # Listing models needs a signed-in account, but agy does not say which one or its plan.
        return {**row, 'auth': 'ok', 'account': None, 'plan': None, 'models': len(models),
                'note': 'agy nie ujawnia konta ani abonamentu; limity: brak danych'}
    return {**row, 'auth': diagnose(out + err), 'problem': _first_line(err or out)}


CHECKS = {'claude': check_claude, 'codex': check_codex, 'gemini': check_gemini}
_cache: dict = {}


def status(force: bool = False, now: Optional[float] = None) -> dict:
    """Panel rows, cached; `force` is the "Check connection" button. Limits come from the reader."""
    now = now or time.time()
    for name, check in CHECKS.items():
        cached = _cache.get(name)
        if force or not cached or now - cached['read_at'] > STALE_S:
            try:
                _cache[name] = {**check(), 'read_at': now}
            except Exception as exc:  # a broken CLI must not break the panel
                _cache[name] = {'provider': name, 'auth': 'unknown', 'problem': str(exc)[:200], 'read_at': now}
    return {name: {**row, 'stale': now - row['read_at'] > STALE_S, 'login': LOGIN[name]}
            for name, row in _cache.items()}
