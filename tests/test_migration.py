"""Moving an old installation's data into the separate data folder (gemini_app/migrate.py)."""
import json
import os
import pathlib
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import unittest.mock

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMP = pathlib.Path(tempfile.mkdtemp(prefix='sol83-mig-')).resolve()
os.environ['GEMINI_NOTIFY'] = '0'
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _env  # noqa: E402,F401  (one data folder for all test modules)

from gemini_app import gitops, migrate  # noqa: E402
from gemini_app.store import Store  # noqa: E402


def tearDownModule():
    shutil.rmtree(TEMP, ignore_errors=True)


def old_installation(root: pathlib.Path) -> None:
    """A small installation in the old layout: data next to the code, absolute paths everywhere."""
    repo = root / 'projects/demo-p1'
    gitops.create_repo(repo)
    worktree = root / 'worktrees/p1'
    worktree.parent.mkdir(parents=True)
    gitops.add_worktree(str(repo), worktree, 'gemini/p1')
    (worktree / 'work.txt').write_text('uncommitted work')
    run = root / 'runs/p1/20261101-000000'
    run.mkdir(parents=True)
    (run / 'state.json').write_text(json.dumps({'cwd': str(worktree), 'transcript_path': str(run / 'transcript.md'),
                                                'finished_reason': 'force_stop'}))
    (root / 'config').mkdir()
    (root / 'config/run-p1.json').write_text(json.dumps({'cwd': str(worktree), 'runs_dir': str(root / 'runs/p1')}))
    store = Store(root / 'state/gemini.db')
    store.add_project(id='p1', title='Demo', task='Zadanie', status='stopped', repo_path=str(repo),
                      worktree=str(worktree), run_dir=str(run), meta=json.dumps({'agents': ['claude', 'codex']}))
    store.event('p1', 'verify', 'Testy', data={'log': str(run / 'verify.log')})
    store.event('p1', 'deliver', f'Wersja w {repo}')


class Migration(unittest.TestCase):
    def setUp(self):
        self.old = pathlib.Path(tempfile.mkdtemp(dir=TEMP)) / 'Sol83'
        (self.old / 'state').mkdir(parents=True)
        old_installation(self.old)
        self.new = pathlib.Path(tempfile.mkdtemp(dir=TEMP)) / 'data'
        self.code = ROOT

    def test_copies_rewrites_and_repairs(self):
        report = migrate.migrate(self.old, self.new, self.code)
        self.assertTrue(all(ok for _, ok, _ in report), report)
        db = sqlite3.connect(self.new / 'state/gemini.db')
        worktree, run_dir, repo = db.execute('SELECT worktree, run_dir, repo_path FROM projects').fetchone()
        self.assertEqual(worktree, str(self.new / 'worktrees/p1'))
        self.assertEqual(repo, str(self.new / 'projects/demo-p1'))
        self.assertTrue(run_dir.startswith(str(self.new / 'runs')))
        data, text = db.execute("SELECT data, text FROM events WHERE kind='verify'").fetchone()[0], None
        self.assertIn(str(self.new), data)
        history = db.execute("SELECT text FROM events WHERE kind='deliver'").fetchone()[0]
        self.assertIn(str(self.old), history, 'event texts stay as written')
        state = json.loads((self.new / 'runs/p1/20261101-000000/state.json').read_text())
        self.assertEqual(state['cwd'], str(self.new / 'worktrees/p1'))
        config = json.loads((self.new / 'config/run-p1.json').read_text())
        self.assertEqual(config['runs_dir'], str(self.new / 'runs/p1'))
        # The worktree is a working git checkout in the new place, uncommitted work included.
        head = subprocess.run(['git', 'rev-parse', '--show-toplevel'], cwd=self.new / 'worktrees/p1',
                              capture_output=True, text=True).stdout.strip()
        self.assertEqual(pathlib.Path(head).resolve(), (self.new / 'worktrees/p1').resolve())
        self.assertEqual((self.new / 'worktrees/p1/work.txt').read_text(), 'uncommitted work')
        listed = subprocess.run(['git', 'worktree', 'list'], cwd=self.new / 'projects/demo-p1',
                                capture_output=True, text=True).stdout
        self.assertIn(str(self.new / 'worktrees/p1'), listed)

    def test_source_is_not_changed(self):
        before = (self.old / 'worktrees/p1/.git').read_text()
        db_before = (self.old / 'state/gemini.db').read_bytes()
        migrate.migrate(self.old, self.new, self.code)
        self.assertEqual((self.old / 'worktrees/p1/.git').read_text(), before)
        self.assertEqual((self.old / 'state/gemini.db').read_bytes(), db_before)
        self.assertTrue(subprocess.run(['git', 'status'], cwd=self.old / 'worktrees/p1',
                                       capture_output=True).returncode == 0)

    def test_refuses_to_overwrite(self):
        self.new.mkdir(parents=True)
        (self.new / 'something').write_text('x')
        with self.assertRaises(migrate.MigrationError):
            migrate.migrate(self.old, self.new, self.code)

    def test_backup_read_from_elsewhere_keeps_original_paths_as_the_key(self):
        backup = pathlib.Path(tempfile.mkdtemp(dir=TEMP)) / 'backup'
        shutil.copytree(self.old, backup, symlinks=True)
        report = migrate.migrate(backup, self.new, self.code, touch_external=False)
        self.assertIn(('ścieżki zapisane w danych', True, str(self.old)), report)
        db = sqlite3.connect(self.new / 'state/gemini.db')
        self.assertEqual(db.execute('SELECT worktree FROM projects').fetchone()[0], str(self.new / 'worktrees/p1'))

    def test_rewrite_only_whole_components(self):
        pairs = [('/a/Sol', '/b/data')]
        self.assertEqual(migrate.rewrite('/a/Sol/x and /a/Solar/y', pairs), '/b/data/x and /a/Solar/y')

    def test_a_shell_mentioning_duet_is_not_an_engine(self):
        fake = f"123 /bin/zsh -c pgrep -f duet.py | grep {self.old}\n456 /usr/bin/python3 /x/vendor/duet/duet.py --config {self.old}/config/run-p1.json\n"
        with unittest.mock.patch.object(migrate.subprocess, 'run', return_value=unittest.mock.Mock(stdout=fake)):
            self.assertEqual(len(migrate.engines_running(self.old)), 1)

    def test_command_line(self):
        done = subprocess.run([sys.executable, str(ROOT / 'sol83'), 'migrate', '--from', str(self.old), '--to',
                               str(self.new), '--dry-run'], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn('skopiowałbym', done.stdout)
        self.assertFalse(self.new.exists())

    def test_dry_run_writes_nothing(self):
        migrate.migrate(self.old, self.new, self.code, dry_run=True)
        self.assertFalse(self.new.exists())


if __name__ == '__main__':
    unittest.main()
