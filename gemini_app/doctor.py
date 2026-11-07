"""`sol83 doctor`: what this machine has for Sol-83, without calling any model."""
from __future__ import annotations

import os
import shutil
import sys

from . import limits, sandbox
from .paths import BASE, DUET, HOME, HOST_SESSION_PREFIXES, agent_path


def checks() -> list:
    """(name, ok, detail) rows. Only free local checks: no model call, no limit spent."""
    rows = [('Python', sys.version_info >= (3, 10), sys.version.split()[0]),
            ('Duet (vendor/duet)', DUET.exists(), str(DUET) if DUET.exists() else 'uruchom bin/setup'),
            ('Katalog danych', True, str(HOME)),
            ('Piaskownica systemu', sandbox.backend() is not None,
             sandbox.backend() or 'brak: kod z repozytoriów nie będzie uruchamiany (zob. SECURITY.md)')]
    path = agent_path()
    for name in ('git', 'codex', 'gh', 'ollama'):
        found = shutil.which(name, path=path)
        rows.append((f'Polecenie {name}', bool(found) or name in ('gh', 'ollama'), found or 'nie znaleziono'))
    rows.append(('Antigravity agy', True, limits.gemini_binary() or 'nie znaleziono (Gemini opcjonalny)'))
    host = sorted(key for key in os.environ if key.startswith(HOST_SESSION_PREFIXES))
    rows.append(('Zmienne sesji nadrzędnej (nie trafią do agentów)', True, ', '.join(host[:6]) + ('…' if len(host) > 6 else '') if host else 'brak'))
    keys = [key for key in (*limits.API_ENV_KEYS, *limits.GEMINI_KEY_ENV) if os.environ.get(key)]
    rows.append(('Brak kluczy API w środowisku', not keys, ', '.join(keys) or 'ok'))
    problem = limits.check_auth()
    rows.append(('Logowanie Claude i Codex (abonament)', problem is None, problem or 'ok'))
    return rows


def main() -> int:
    print(f'Sol-83 w {BASE}')
    failed = 0
    for name, ok, detail in checks():
        failed += not ok
        print(f"[{'ok' if ok else '!!'}] {name}: {detail}")
    return 1 if failed else 0
