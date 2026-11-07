"""Credentials that must not leave the machine or show up in logs, prompts and the panel.

One list of patterns serves three jobs: scanning a commit before any push, scanning
text before it is stored or shown, and redacting what was found. The patterns are
POSIX ERE so `git grep -E` can use the same ones.
"""
from __future__ import annotations

import re

# Token formats that are secrets by their shape alone: matched case-sensitively.
TOKEN_PATTERNS = (
    r'sk-ant-[A-Za-z0-9_-]{16,}',                          # Anthropic
    r'sk-(proj|svcacct|admin)-[A-Za-z0-9_-]{20,}',          # OpenAI project / service keys
    r'sk-[A-Za-z0-9]{32,}',                                 # OpenAI legacy
    r'(sk|rk)_(live|test)_[A-Za-z0-9]{16,}',                # Stripe
    r'xox[abposr]-[A-Za-z0-9-]{10,}',                       # Slack tokens
    r'hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[A-Za-z0-9]+',
    r'gh[pousr]_[A-Za-z0-9]{30,}',                          # GitHub tokens
    r'github_pat_[A-Za-z0-9_]{30,}',
    r'glpat-[A-Za-z0-9_-]{20,}',                            # GitLab
    r'(AKIA|ASIA)[0-9A-Z]{16}',                             # AWS access key id
    r'AIza[0-9A-Za-z_-]{30,}',                              # Google API key
    r'ya29\.[0-9A-Za-z_-]{20,}',                            # Google OAuth access token
    r'GOCSPX-[A-Za-z0-9_-]{20,}',                           # Google OAuth client secret
    r'npm_[A-Za-z0-9]{36}',                                 # npm
    r'-----BEGIN [A-Z ]*PRIVATE KEY-----',
)
# Assignments that name a secret and give it a literal value: matched ignoring case.
ASSIGNMENT_PATTERNS = (
    r'(password|passwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret)'
    r'["\']?[ \t]*[:=][ \t]*["\'][^"\' \t]{8,}["\']',
    r'_authToken[ \t]*=[ \t]*[^ \t]{8,}',                   # .npmrc
    r'(https?|git)://[^/@ \t:]+:[^/@ \t]{6,}@',             # credentials inside a URL
)
SECRET_FILES = re.compile(
    r'(^|/)(\.env(\.[\w-]+)?|id_(rsa|ed25519|ecdsa|dsa)|[\w.-]+\.(pem|p12|pfx|key|keystore|jks)'
    r'|credentials(\.json)?|\.npmrc|\.pypirc|\.netrc|\.git-credentials|service[-_]account[\w.-]*\.json)$')
NOT_SECRETS = {'.env.example', '.env.sample', '.env.template', '.env.dist'}


def _ere(pattern: str) -> str:
    """POSIX ERE has no \\t inside brackets: use the [:blank:] class there."""
    return pattern.replace(r' \t', '[:blank:]')


TOKEN_ERE = '|'.join(f'({p})' for p in TOKEN_PATTERNS)
ASSIGNMENT_ERE = '|'.join(f'({_ere(p)})' for p in ASSIGNMENT_PATTERNS)
_TOKEN = re.compile(TOKEN_ERE)
_ASSIGNMENT = re.compile('|'.join(f'({p})' for p in ASSIGNMENT_PATTERNS), re.I)
MASK = '[ukryto sekret]'


def secret_file(path: str) -> bool:
    return bool(SECRET_FILES.search(path)) and path.rsplit('/', 1)[-1] not in NOT_SECRETS


def has_secret(text: str) -> bool:
    return bool(text) and bool(_TOKEN.search(text) or _ASSIGNMENT.search(text))


def redact(text):
    """The text with every credential-looking part replaced. Keeps None and non-strings as they are."""
    if not isinstance(text, str) or not text:
        return text
    text = _TOKEN.sub(MASK, text)

    def mask(match):
        found = match[0]
        if '://' in found:
            return found.split('://', 1)[0] + '://' + MASK + '@'
        return re.split(r'[ \t]*[:=]', found, maxsplit=1)[0] + '=' + MASK
    return _ASSIGNMENT.sub(mask, text)
