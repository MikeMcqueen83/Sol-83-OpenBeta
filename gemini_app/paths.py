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


# Variables of a host session (for example a Claude Code or agent SDK session that started the server)
# that must not leak into the agents Sol-83 starts: they can redirect the API endpoint, mark the agent as
# nested, or carry that session's tokens. The agents should see the environment of a plain terminal.
HOST_SESSION_PREFIXES = ('CLAUDECODE', 'CLAUDE_CODE_', 'CLAUDE_AGENT_SDK_', 'ANTHROPIC_BASE_URL', 'AI_AGENT', 'BAGGAGE',
                         'MCP_', 'USE_LOCAL_OAUTH', 'USE_STAGING_OAUTH', 'CLAUDE_PID', 'CLAUDE_EFFORT', 'API_TIMEOUT_MS',
                         'CLAUDE_PREVIEW_')


def clean_env(env=None) -> dict:
    """The environment without a host session's variables (see HOST_SESSION_PREFIXES)."""
    source = os.environ if env is None else env
    return {key: value for key, value in source.items() if not key.startswith(HOST_SESSION_PREFIXES)}


def agent_path() -> str:
    """PATH for agent CLIs. GEMINI_EXTRA_PATH lets tests put fake CLIs first."""
    parts = [os.environ.get('GEMINI_EXTRA_PATH'), str(BIN), str(Path.home() / '.local/bin'),
             os.environ.get('PATH', '')]
    return os.pathsep.join(p for p in parts if p)
