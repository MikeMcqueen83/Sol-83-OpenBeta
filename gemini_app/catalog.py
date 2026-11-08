"""What can be chosen on each side: models and thinking levels."""
from __future__ import annotations

import os
import re
import subprocess
import time

from . import limits
from .messages import en
from .paths import agent_path

MODEL_OFF = 'none'
CLAUDE_EFFORTS = ['low', 'medium', 'high', 'xhigh', 'max']
CLAUDE_MODELS = [{'id': model, 'label': label, 'efforts': CLAUDE_EFFORTS}
                 for model, label in (('fable', 'Fable 5.1'), ('opus', 'Opus 5.5'),
                                      ('sonnet', 'Sonnet 5.5'), ('haiku', 'Haiku 5.5'))]
GEMINI_EFFORTS = ['low', 'medium', 'high', 'xhigh', 'max']
GEMINI_DEFAULT = {'id': 'default', 'label': 'Domyślny w Antigravity (model wybiera agy, może być droższy)', 'efforts': GEMINI_EFFORTS}
_SLUG = re.compile(r'^[a-z][\w.\-:/]+$')
CACHE_S = 600
_cache: dict = {'at': 0.0, 'codex': [], 'gemini': [GEMINI_DEFAULT]}


def _codex_models() -> list:
    """Live list from the app-server, including levels each model really supports."""
    data = limits.codex_call('model/list').get('data') or []
    models = [{'id': item['model'], 'label': item.get('displayName') or item['model'],
               'efforts': [level['reasoningEffort']
                           for level in item.get('supportedReasoningEfforts') or []]}
              for item in data if not item.get('hidden')]
    return sorted(models, key=lambda model: not model['id'].startswith('gpt-'))


def _gemini_models() -> list:
    """`agy models` lists what the signed-in account may use; the default always works."""
    binary = limits.gemini_binary()
    if not binary:
        return [GEMINI_DEFAULT]
    done = subprocess.run([binary, 'models'], capture_output=True, text=True, timeout=30,
                          stdin=subprocess.DEVNULL, env={**os.environ, 'PATH': agent_path()})
    # One model per line: "gemini-4-argon-high<TAB>Gemini 4 Argon (High)". The name holds the level.
    rows = [line.split('\t', 1) for line in done.stdout.splitlines() if line.strip()]
    found = {row[0].strip(): (row[1].strip() if len(row) > 1 else row[0].strip())
             for row in rows if _SLUG.match(row[0].strip()) and row[0].strip() != 'default'}
    return [GEMINI_DEFAULT, *({'id': slug, 'label': name, 'efforts': []} for slug, name in list(found.items())[:30])]


def read(force: bool = False) -> dict:
    if force or time.time() - _cache['at'] > CACHE_S or not _cache['codex']:
        try:
            _cache.update(codex=_codex_models(), at=time.time())
        except (OSError, ValueError, KeyError):
            pass
        try:
            _cache.update(gemini=_gemini_models())
        except (OSError, subprocess.SubprocessError):
            pass
    return {'claude': CLAUDE_MODELS, 'codex': _cache['codex'], 'gemini': _cache['gemini'],
            'gemini_problem': limits.gemini_problem(), 'gemini_problem_en': en(limits.gemini_problem())}
