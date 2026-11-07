"""The license of each project made in Sol-83 (spec point 15). Independent of Sol-83's own license.

Three kinds: a standard open-source license (correct SPDX id, unmodified text from GitHub's license
API, only the copyright line filled in where the template has one), a custom or source-available
text written by the user, or no declared license. An existing LICENSE is never overwritten without
an explicit decision. Choosing a license for a project grants no right to relicense its dependencies
or anyone else's code, and no declared license does not mean anyone may use it freely.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

DATA = Path(__file__).resolve().parent / 'data/licenses'
STANDARD = {
    'MIT': {'pl': 'Bardzo liberalna: wolno prawie wszystko, z zachowaniem informacji o autorze i licencji.',
            'en': 'Very permissive: almost anything goes, keeping the copyright and license notice.'},
    'Apache-2.0': {'pl': 'Liberalna, z jawną licencją patentową i obowiązkiem oznaczania zmian.',
                   'en': 'Permissive, with an explicit patent license and a duty to mark changes.'},
    'BSD-3-Clause': {'pl': 'Liberalna; zakazuje używania nazwy autora do promocji bez zgody.',
                     'en': 'Permissive; forbids using the author\'s name for promotion without consent.'},
    'MPL-2.0': {'pl': 'Copyleft na poziomie plików: zmienione pliki zostają na MPL, reszta może mieć inną licencję.',
                'en': 'File-level copyleft: changed files stay under MPL, the rest may use another license.'},
    'GPL-3.0-only': {'pl': 'Silny copyleft: utwory pochodne rozpowszechniane z kodem źródłowym na tej samej licencji.',
                     'en': 'Strong copyleft: derivative works are distributed with source under the same license.'},
    'AGPL-3.0-only': {'pl': 'Jak GPL, a do tego obejmuje udostępnianie programu przez sieć.',
                      'en': 'Like GPL, and also covers offering the program over a network.'},
}
KINDS = ('standard', 'custom', 'none')
FILE = 'LICENSE'


class LicenseError(ValueError):
    pass


def text(spdx: str, holder: str, year: Optional[int] = None) -> str:
    """The unmodified license text; only the template's own [year] and [fullname] are filled in."""
    if spdx not in STANDARD:
        raise LicenseError(spdx)
    body = (DATA / f'{spdx}.txt').read_text()
    return body.replace('[year]', str(year or time.localtime().tm_year)).replace('[fullname]', holder.strip() or 'the authors')


def apply(folder, kind: str, spdx: str = '', holder: str = '', custom: str = '', overwrite: bool = False) -> dict:
    """Write the chosen license into the project's folder. Returns {'written': bool, 'file', 'existing'}."""
    if kind not in KINDS:
        raise LicenseError(kind)
    path = Path(folder) / FILE
    existing = path.exists()
    if kind == 'none':
        return {'written': False, 'file': None, 'existing': existing}
    if existing and not overwrite:
        raise LicenseError('W projekcie jest już plik LICENSE: zmiana licencji wymaga świadomej decyzji (nadpisz).')
    content = text(spdx, holder) if kind == 'standard' else custom.strip()
    if kind == 'custom' and not content:
        raise LicenseError('Pusta treść licencji własnej.')
    path.write_text(content + ('' if content.endswith('\n') else '\n'))
    return {'written': True, 'file': str(path), 'existing': existing}


def apply_pending(store, project_id: str) -> dict:
    """Write the license the user chose into the agents' folder, commit it as a coordinator checkpoint and
    tell the agents through the queue. Called between turns or while the project is idle."""
    import json as _json
    from . import orders, prompts
    from .gitops import Git
    project = store.project(project_id)
    choice = store.meta(project_id).get('license_request')
    if not choice or not project or not project.get('worktree'):
        return {'pending': bool(choice)}
    store.update_meta(project_id, lambda meta: meta.pop('license_request', None))
    written = apply(project['worktree'], choice['kind'], choice.get('spdx') or '', choice.get('holder') or '',
                    choice.get('custom') or '', choice.get('overwrite'))
    if written['written']:
        name = choice.get('spdx') or choice['kind']
        Git(project['worktree']).checkpoint(f'sol83: licencja {name}')
        orders.add(store, project_id, prompts.text(prompts.language(project), 'license_note', license=name),
                   'note', request_key=f"license-{choice.get('at')}")
    return {'pending': False, **written, 'choice': _json.loads(_json.dumps(choice))}
