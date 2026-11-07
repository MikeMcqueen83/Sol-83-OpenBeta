# Sol-83 (OpenBeta)

[Polski](README.md)

Sol-83 is a local coordinator that makes coding agents take turns on one repository: **Claude Code**, **Codex** and optionally **Gemini through Antigravity**. They check each other, and when one runs out of subscription limit the other takes over. The coordinator is a plain program, not a model: it saves a Git checkpoint after every turn, runs the tests in a sandbox and numbers a version only when they pass. You get checked versions, questions only when they are really needed, and a web panel on `127.0.0.1:8765` in Polish and English.

Subscriptions only: no API keys, no paid extra usage.

> **Status:** OpenBeta, developed since November 2026. Tested on macOS (Apple Silicon). Linux is supported in the code but untested on real hardware; Windows is not supported. The status of every feature, with tests and limits: [docs/TRACEABILITY.md](docs/TRACEABILITY.md) (Polish).

## Quick start

Full installation from scratch, step by step: **[docs/en/INSTALL.md](docs/en/INSTALL.md)**.

```bash
git clone https://github.com/MikeMcqueen83/Sol-83-OpenBeta.git
```

```bash
cd Sol-83-OpenBeta && ./bin/setup && ./sol83 doctor
```

```bash
./sol83 serve
```

Open http://127.0.0.1:8765 and click **New project**.

## Documentation

[Install](docs/en/INSTALL.md) · [Guide](docs/en/GUIDE.md) · [Data, backups, updates, rollback](docs/en/UPDATES.md) · [Security](SECURITY.md) · [Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md)

## License

Sol-83 is **source-available**, not OSI open source: non-commercial use is allowed; commercial use needs the author's prior written consent; contributions go through forks or branches. The terms are a draft pending legal review: [LICENSE.md](LICENSE.md). Duet and other components keep their own licenses: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Projects you create with Sol-83 get the license you choose.

Author: Michał Werpachowski.
