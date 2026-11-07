# Installing Sol-83 step by step, from scratch

This guide goes from a clean system to your first project. Every step has a command to paste into a terminal and a way to check that it worked.

**Tested:** macOS 26 (Apple Silicon), Python 3.14, Git 2.55, Claude Code 2.1, Codex CLI 0.166, Antigravity CLI 1.5. **Linux** is supported in the code (bubblewrap sandbox, `notify-send`) but was not tested on a real machine. **Windows** is not supported (Sol-83 relies on `fcntl`, `ps` and Unix sandboxes); WSL 2 may work like Linux, without guarantee.

What you need besides the computer:
- a Claude subscription (Pro, Max or higher) for Claude Code,
- a ChatGPT account with a plan that includes Codex,
- optionally a Google account with Google AI Pro/Ultra for Gemini through Antigravity,
- about 2 GB for Sol-83 and its tools, plus room for projects.

Sol-83 uses subscriptions only. It needs no API keys and never uses paid extra usage.

---

## Step 1. Open a terminal

macOS: Finder → Applications → Utilities → Terminal (or Cmd+Space, type "Terminal").

## Step 2. Apple developer tools (Git)

```bash
xcode-select --install
```

Confirm the installer window. Check:

```bash
git --version
```

Linux (Debian/Ubuntu): `sudo apt install git curl`.

## Step 3. Homebrew (macOS package manager)

Skip if `brew --version` already works. The command from https://brew.sh:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

At the end the installer prints two commands that add Homebrew to your path: run them. Check: `brew --version`.

## Step 4. Python 3 and Node.js

```bash
brew install python node
```

```bash
python3 --version
```

Python 3.9 or newer is required (Sol-83 was tested on 3.14). Node.js is only needed to install Codex with npm.

Linux: `sudo apt install python3 nodejs npm bubblewrap` (bubblewrap is the sandbox; without it Sol-83 does not run code from repositories).

## Step 5. Claude Code

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

Alternative: `brew install --cask claude-code`. Open a new terminal window and check:

```bash
claude --version
```

Sign in with your subscription account: run `claude`, choose the claude.ai sign-in, finish in the browser, then leave with `/exit`. Do not set `ANTHROPIC_API_KEY`: Sol-83 refuses to work when it sees an API key.

If you have the Claude desktop app for Mac, Sol-83 also finds the copy of Claude Code bundled with it. `GEMINI_CLAUDE_BIN` points to any other location.

## Step 6. Codex CLI

```bash
npm install -g @openai/codex
```

Alternative: `brew install --cask codex`. Sign in: run `codex`, choose "Sign in with ChatGPT", finish in the browser, leave. Check:

```bash
codex login status
```

It should print `Logged in using ChatGPT`.

## Step 7 (optional). Gemini through Antigravity

```bash
curl -fsSL https://antigravity.google/cli/install.sh | bash
```

This is the command from Antigravity's documentation as of November 2026; if it has moved, use the current one from antigravity.google. The first prompt opens the Google sign-in:

```bash
agy -p "test"
```

That one short prompt uses a little of the Antigravity limit. A check that uses no limit:

```bash
agy models
```

Do not set `GEMINI_API_KEY` or `GOOGLE_API_KEY`: the adapter removes them anyway.

## Step 8 (optional). GitHub CLI

Only needed to publish versions to GitHub and for pull requests.

```bash
brew install gh
```

```bash
gh auth login
```

## Step 9 (optional). A local model through Ollama

The local model answers questions about a project's state without using subscriptions and helps derive the RUN plan. Sol-83 works without it; one of the subscription models can then be the message coordinator.

```bash
brew install ollama
```

```bash
ollama serve
```

In a second terminal window pull the model (the default `gemma4:31b` takes about 20 GB; `SOL83_LOCAL_MODEL` selects a smaller one):

```bash
ollama pull gemma4:31b
```

## Step 10. Get Sol-83

```bash
cd ~
```

```bash
git clone https://github.com/MikeMcqueen83/Sol-83-OpenBeta.git
```

```bash
cd Sol-83-OpenBeta
```

## Step 11. The Duet engine

Sol-83 uses the Duet engine (MIT license) at a pinned commit, with a patch from this repository:

```bash
./bin/setup
```

It should print `Duet gotowy`.

## Step 12. Check the environment

```bash
./sol83 doctor
```

Every line should say `[ok]`. Typical `[!!]`:
- **OS sandbox**: on Linux install `bubblewrap`,
- **Claude and Codex sign-in**: go back to step 5 or 6,
- **No API keys in the environment**: remove the listed variables from `~/.zshrc` or `~/.bashrc`.

`doctor` calls no model and uses no limit.

## Step 13. Start the panel

```bash
./sol83 serve
```

Open http://127.0.0.1:8765 in a browser. The panel is reachable from this computer only. Closing the terminal stops the panel; running projects finish their current turn, and after `./sol83 serve` again the coordinator reattaches to them.

Data (projects, runs, database) goes to `~/Sol-83-data`. `SOL83_HOME` selects another folder, e.g. `SOL83_HOME=/Volumes/Data/Sol83 ./sol83 serve`.

## Step 14. Your first project

1. Click **New project**.
2. Describe the task and the acceptance criteria. The page language at creation becomes the project's fixed language.
3. Enter the test command, e.g. `python3 -m unittest`. It runs in the sandbox, without network.
4. Choose models: manually, or **Auto — economy** / **Auto — power** per provider.
5. Keep the roles on **General** or assign specific ones.
6. Confirm. The project joins the queue and starts.

Progress is in **Activity**. Agents' questions and tests for you are in **Questions and tests**. Finished versions are in **Versions**: run one with **RUN**, open its folder and judge it.

## Updating Sol-83

```bash
cd ~/Sol-83-OpenBeta
```

```bash
git pull
```

```bash
rm -rf vendor/duet && ./bin/setup
```

The data in `~/Sol-83-data` is left alone. Make a backup first (see `docs/en/UPDATES.md`).

## Uninstalling

Stop the panel (Ctrl+C in its window), then move the code folder to the Trash, and the data folder `~/Sol-83-data` too if you no longer need it. Repositories you gave as a source are never deleted by Sol-83.
