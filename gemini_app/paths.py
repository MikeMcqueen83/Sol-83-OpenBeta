"""Filesystem layout. Code and data live apart: the code folder can be replaced by a newer
release without touching projects. SOL83_HOME moves the data (GEMINI_HOME is the older name)."""
import os
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DEFAULT_HOME = Path.home() / 'Sol-83-data'
HOME = Path(os.environ.get('SOL83_HOME') or os.environ.get('GEMINI_HOME') or DEFAULT_HOME).expanduser()
STATE = HOME / 'state'
RUNS = HOME / 'runs'
WORKTREES = HOME / 'worktrees'
PROJECTS = HOME / 'projects'
CONFIG = HOME / 'config'
BACKUPS = HOME / 'backups'
BIN = BASE / 'bin'
DUET = BASE / 'vendor/duet/duet.py'
WEB = BASE / 'gemini_app/web'


def agent_path() -> str:
    """PATH for agent CLIs. GEMINI_EXTRA_PATH lets tests put fake CLIs first."""
    parts = [os.environ.get('GEMINI_EXTRA_PATH'), str(BIN), str(Path.home() / '.local/bin'),
             os.environ.get('PATH', '')]
    return os.pathsep.join(p for p in parts if p)
