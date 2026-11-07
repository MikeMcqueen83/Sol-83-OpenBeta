"""Moving an existing Sol-83 installation's data into this instance's data folder.

Reproducible and non-destructive: the source is only read. The copy uses APFS clones
where the file system has them (no extra space until a file changes), the database is
copied through SQLite's backup API, absolute paths are rewritten in the database, the
run configurations and Duet's run states, and git worktree links are repaired so each
worktree points at its repository in the new place. A report lists what was checked.

    sol83 migrate --from /path/to/old/installation [--to /path/to/new/data] [--dry-run]
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

DATA_DIRS = ('state', 'config', 'projects', 'runs', 'worktrees')
LEGACY_DIRS = {'demo': 'legacy/demo', 'reports': 'legacy/reports'}
# Columns that hold paths the program uses. Event texts stay as history.
PATH_COLUMNS = {'projects': ('repo_path', 'worktree', 'run_dir', 'meta'), 'events': ('data',)}


class MigrationError(RuntimeError):
    pass


def mapping(source: Path, target: Path, code: Path) -> list:
    """(old prefix, new prefix), longest first: data folders, legacy folders, then the old code root."""
    pairs = [(str(source / name), str(target / name)) for name in DATA_DIRS]
    pairs += [(str(source / old), str(target / new)) for old, new in LEGACY_DIRS.items()]
    pairs.append((str(source), str(code)))
    return sorted(pairs, key=lambda pair: -len(pair[0]))


def rewrite(text: str, pairs: list) -> str:
    """Replace path prefixes only where a whole path component follows."""
    if not isinstance(text, str):
        return text
    out, index = [], 0
    while index < len(text):
        for old, new in pairs:
            if text.startswith(old, index) and (index + len(old) == len(text)
                                                or text[index + len(old)] in '/"\'\n \t,}]\\'):
                out.append(new)
                index += len(old)
                break
        else:
            out.append(text[index])
            index += 1
    return ''.join(out)


def _clone(source: Path, target: Path) -> None:
    """APFS clone when possible (macOS `cp -c`), plain copy otherwise. Symlinks stay symlinks."""
    target.parent.mkdir(parents=True, exist_ok=True)
    if sys.platform == 'darwin':
        done = subprocess.run(['cp', '-cRp', str(source), str(target)], capture_output=True, text=True)
        if done.returncode == 0:
            return
        shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(source, target, symlinks=True)


def engines_running(source: Path) -> list:
    out = subprocess.run(['ps', '-axo', 'pid=,command='], capture_output=True, text=True,
                         env={**os.environ, 'LC_ALL': 'C'}).stdout
    found = []
    for line in out.splitlines():
        parts = line.split()
        # An engine runs duet.py as its script (argv[1]); a shell whose text mentions it is not one.
        if len(parts) > 2 and parts[2].endswith('duet.py') and str(source) in line:
            found.append(line.strip())
    return found


def _copy_database(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    src = sqlite3.connect(f'file:{source}?mode=ro', uri=True)
    dst = sqlite3.connect(str(target))
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()


def _rewrite_database(path: Path, pairs: list) -> int:
    changed = 0
    db = sqlite3.connect(str(path))
    try:
        with db:
            for table, columns in PATH_COLUMNS.items():
                existing = {row[1] for row in db.execute(f'PRAGMA table_info({table})')}
                for column in columns:
                    if column not in existing:
                        continue
                    rows = db.execute(f'SELECT rowid, {column} FROM {table} WHERE {column} IS NOT NULL').fetchall()
                    for rowid, value in rows:
                        new = rewrite(value, pairs)
                        if new != value:
                            db.execute(f'UPDATE {table} SET {column}=? WHERE rowid=?', (new, rowid))
                            changed += 1
    finally:
        db.close()
    return changed


def _rewrite_json_files(root: Path, pairs: list) -> int:
    changed = 0
    for path in list(root.rglob('*.json')) if root.exists() else []:
        if not path.is_file() or path.is_symlink():
            continue
        try:
            text = path.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        new = rewrite(text, pairs)
        if new != text:
            json.loads(new)  # never leave a broken file behind
            path.write_text(new)
            changed += 1
    return changed


def _repair_worktrees(worktrees: Path, pairs: list, report: list, target: Path, touch_external: bool) -> None:
    """Point each worktree at its repository's new place, then let git fix the link back. A repository
    outside the data folder (the user's own) is changed only with `touch_external`."""
    if not worktrees.exists():
        return
    for folder in sorted(worktrees.iterdir()):
        link = folder / '.git'
        if not link.is_file():
            continue
        text = link.read_text()
        new = rewrite(text, pairs)
        if new != text:
            link.write_text(new)
        admin = Path(new.split('gitdir:', 1)[-1].strip())
        if not admin.is_relative_to(target) and not touch_external:
            report.append((f'worktree {folder.name}', True, f'repozytorium poza katalogiem danych, '
                           f'link zwrotny bez zmian: {admin}'))
            continue
        done = subprocess.run(['git', 'worktree', 'repair'], cwd=folder, capture_output=True, text=True)
        head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=folder, capture_output=True, text=True)
        ok = done.returncode == 0 and head.returncode == 0
        report.append((f'worktree {folder.name}', ok, head.stdout.strip()[:12] if ok
                       else (done.stderr or head.stderr).strip()[:200]))


def _counts(db_path: Path) -> dict:
    db = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
    try:
        return {table: db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
                for (table,) in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        db.close()


def recorded_root(db_path: Path, fallback: Path) -> Path:
    """The installation folder the data was written in, from the projects' worktree paths. A backup
    read from elsewhere still holds the original paths."""
    db = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
    try:
        roots = {value.split('/worktrees/')[0] for (value,) in
                 db.execute("SELECT worktree FROM projects WHERE worktree LIKE '%/worktrees/%'")}
    finally:
        db.close()
    return Path(roots.pop()) if len(roots) == 1 else fallback


def migrate(source: Path, target: Path, code: Path, dry_run: bool = False,
            touch_external: bool = True) -> list:
    """Copy and adapt. Returns report rows (check, ok, detail). Raises MigrationError before
    touching anything when the move is not safe."""
    source, target = source.resolve(), target.resolve()
    if not (source / 'state/gemini.db').is_file():
        raise MigrationError(f'W {source} nie ma state/gemini.db: to nie jest instalacja Sol-83.')
    if target.exists() and any(target.iterdir()):
        raise MigrationError(f'Katalog docelowy {target} nie jest pusty. Migracja nie nadpisuje danych.')
    if source == target or target.is_relative_to(source) or source.is_relative_to(target):
        raise MigrationError('Źródło i cel nie mogą się zawierać.')
    root = recorded_root(source / 'state/gemini.db', source)
    running = engines_running(source) + (engines_running(root) if root != source else [])
    if running:
        raise MigrationError('Stara instancja ma działające silniki projektów. Zatrzymaj je przed migracją:\n'
                             + '\n'.join(running))
    pairs = mapping(root, target, code)
    report = [('źródło', True, str(source)), ('ścieżki zapisane w danych', True, str(root)),
              ('cel', True, str(target))]
    if dry_run:
        report += [(f'skopiowałbym {name}', True, str(source / name) if (source / name).exists() else 'brak, pominę')
                   for name in (*DATA_DIRS, *LEGACY_DIRS)]
        return report
    target.mkdir(parents=True, exist_ok=True)
    started = time.time()
    for name in DATA_DIRS:
        if name == 'state':
            continue
        if (source / name).exists():
            _clone(source / name, target / name)
    for old, new in LEGACY_DIRS.items():
        if (source / old).exists():
            _clone(source / old, target / new)
    (target / 'state').mkdir(parents=True, exist_ok=True)
    for item in (source / 'state').iterdir():
        if item.name.startswith('gemini.db'):
            continue
        if item.is_file():
            shutil.copy2(item, target / 'state' / item.name)
    _copy_database(source / 'state/gemini.db', target / 'state/gemini.db')
    report.append(('kopia danych', True, f'{time.time() - started:.1f} s'))
    report.append(('ścieżki w bazie', True, f"{_rewrite_database(target / 'state/gemini.db', pairs)} pól"))
    report.append(('ścieżki w plikach JSON', True,
                   f"{_rewrite_json_files(target / 'config', pairs) + _rewrite_json_files(target / 'runs', pairs)} plików"))
    _repair_worktrees(target / 'worktrees', pairs, report, target, touch_external)
    before, after = _counts(source / 'state/gemini.db'), _counts(target / 'state/gemini.db')
    for table, count in before.items():
        report.append((f'rekordy {table}', after.get(table) == count, f'{after.get(table)} / {count}'))
    leftovers = []
    db = sqlite3.connect(str(target / 'state/gemini.db'))
    try:
        for table, columns in PATH_COLUMNS.items():
            for column in columns:
                try:
                    hits = db.execute(f'SELECT COUNT(*) FROM {table} WHERE {column} LIKE ?',
                                      (f'%{root}/%',)).fetchone()[0]
                except sqlite3.OperationalError:
                    continue
                if hits:
                    leftovers.append(f'{table}.{column}: {hits}')
    finally:
        db.close()
    report.append(('stare ścieżki w bazie', not leftovers, ', '.join(leftovers) or 'brak'))
    (target / 'MIGRATION.json').write_text(json.dumps(
        {'from': str(source), 'to': str(target), 'code': str(code), 'at': time.time(),
         'report': [list(row) for row in report]}, ensure_ascii=False, indent=2))
    return report


def main(argv: Optional[list] = None) -> int:
    import argparse
    from .paths import BASE, HOME
    parser = argparse.ArgumentParser(prog='sol83 migrate')
    parser.add_argument('--from', dest='source', required=True, type=Path)
    parser.add_argument('--to', dest='target', type=Path, default=HOME)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--trial', action='store_true',
                        help='próba na kopii: nie zmienia repozytoriów poza katalogiem danych')
    args = parser.parse_args(argv)
    try:
        report = migrate(args.source, args.target, BASE, args.dry_run, touch_external=not args.trial)
    except MigrationError as exc:
        print(exc, file=sys.stderr)
        return 2
    failed = 0
    for name, ok, detail in report:
        failed += not ok
        print(f"[{'ok' if ok else '!!'}] {name}: {detail}")
    return 1 if failed else 0
