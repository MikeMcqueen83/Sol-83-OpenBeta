# Sol-83 user guide

Installation from scratch: [INSTALL.md](INSTALL.md). The status and limits of every requirement are in [../TRACEABILITY.md](../TRACEABILITY.md) (Polish).

## 1. What Sol-83 is

A local coordinator that makes several coding agents take turns on one repository: Claude Code, Codex and optionally Gemini through Antigravity. The coordinator is a plain program, not a model: it decides who works next, saves a Git checkpoint after every turn, runs the tests in a sandbox and numbers a version only when they pass. It uses subscriptions, not API keys; when one agent runs out of limit, the other takes over.

It does not publish anything without your decision, never uses paid credits, never guesses a sign-in and does not replace your acceptance.

## 2. Projects, the queue and turns

Every request (the task, a note, new work, a plan item, a rejected version, an answer) is written to a durable queue **before** the panel acknowledges it, with an id, time, order and state: *pending → delivered to a turn → answered → done* (done = an accepted version exists after the answer). A double click or a retransmitted request creates no second entry. Closing a project and adding work happen in one database transaction, so work that arrives while a project finishes is always handled, and a late acceptance of the old state never closes a project with new work. Work handed to a turn that died (a restart, a crash) goes back to the queue. The project state says what it waits for: a turn, an executor, a limit, your decision or test, or an error.

## 3. Models, roles and selection modes

Per provider: **Manual**, **Auto — economy** (a sufficient model, escalating after failures) or **Auto — power** (a stronger model from the allowed pool, watching limits). Auto decides before each turn by kind of work, results and remaining limit, and records the reason with the policy and catalog versions. A provider's **top model** (today Claude Fable 5.1, GPT-6-Astra, Gemini 4 Argon) is never chosen automatically, not as a fallback and not as an escalation; a manual choice of it needs confirmation of that exact model. Unclassified models stay outside Auto; with no allowed model the side waits and says why.

Changes apply from the next turn; the running turn keeps its configuration snapshot, shown next to the next turn's settings. A model change gives the agent a new session with the state handed over.

**Roles** (several per model): General (plan, implementation, review), Architect, Implementer, Tester, Analyst, Content creator. General does not make ordered content. Coverage of every kind of work is checked after each change. With **one model only**, reviews run in a new session and versions are marked as of limited independence.

**Full Power**: while the other model waits for a limit reset, the same model reviews and fixes in a new session without memory of its own work. Handoff thresholds stop applying, so it uses limits fast. At most 5 such reviews in a row, then the project waits and says so. It does not bypass model limits, permissions, payments or acceptance gates, and it is not the "Auto — power" selection mode.

## 4. The model catalog

For each model: provider facts with source and check date, a tier (economy, standard, strong, top) and whether Auto may use it; availability on your account comes from the CLIs, and observations from your own projects are kept apart. Once a month (first a month after installation) the coordinator may ask an allowed model to propose an update; validation keeps top models out of Auto, leaves new models unclassified and holds tier changes for your decision. A failure keeps the previous catalog. The update can be disabled, deferred or rolled back.

## 5. Limits, tokens and comparisons

**Accounts and sign-in** shows each CLI's installation, sign-in, account and plan (only when the CLI reports them: Claude and Codex do, Antigravity does not), read time and staleness. **Check connection** calls no model. Failures are classified (not signed in, expired session, wrong account, no model access, plan limit, rate limit, network, outage, unknown). A reset the provider states in its error is used as stated.

**Tokens** are per-turn increases of the same session's counter: Claude reports a turn, Codex and Antigravity the whole session. Codex reports only a total, so input and output are "no data", not zero. Cache is shown apart. Providers' categories are not directly comparable. **Limit share** sums how the account's readings moved during the project's turns, per provider (250% of the 5 h window = 2.5 windows), as an estimate that includes other work on the account; turns without a reading and turns shared with another project are shown. It is not the current balance.

## 6. Plan, progress and debt

Canonical plan statuses are `todo`, `doing`, `done`, `deferred`, whatever the language; clear variants are normalized and logged, unknown values are errors, never "done". A broken plan never replaces the last valid one: numbered revisions are kept, and after 3 failed repairs the last valid one is restored. **Net progress** = max(0, functional − debt in percentage points), both on the same weighted basis (must 3, should 2, could 1). Deferred is not done. **Acceptance gates** are separate: a deferred must item, an unanswered blocking question, a mandatory test without a pass for the current version, missing mandatory content. Closing without a gate needs your recorded scope decision.

## 7. Questions and tests for you

Agents record questions, decisions and manual tests in `.sol83/requests.json`; Sol-83 keeps them as durable records. You answer in **Questions and tests**. Answers are saved before work resumes and reach the agents through the queue. Test results: works, does not work, partly, cannot run it; a negative result opens one bug per test and version. No answer is not consent: dependent work waits, independent work goes on; when nothing can move, the project pauses and resumes after your answer. Late answers (to superseded questions, or for another version) stay in the history and are not applied automatically. "What to check in this version" is that version's manual test record.

## 8. Content orders

A model without the Content creator role may propose an order; the Content creator makes it only after you approve that exact order (approval grants no role). Your own orders are approved at once. Duplicates are rejected. Size and style are hints; the real image size is shown afterwards. Rejecting or deferring a mandatory order does not remove it from scope.

## 9. Versions, testing and RUN

**Versions** shows for each version: date, summary, automatic tests, manual test, review, commit and tag, recommendation, the real folder (or "tag only" with a prepare button), how to run it and what to check. **RUN** starts a version from the user folder, never the agents' worktree, with a plan stored per version (commit + manifest hash). Only plain commands of known tools run, without a shell, in the sandbox; never `sudo`, `curl | sh` or administrator installs. Ports 8800–8899, never 8765 or a busy one; processes are recognised by start time; foreign processes are never killed; a second click shows the running instance. Libraries get an explanation instead.

## 10. Project language

Fixed at creation from the page language (PL or EN): every instruction to the agents, the plan, questions and summaries follow it; switching the page language changes only the interface. Older projects got a language read from their task; when unclear, the panel asks once.

## 11. Project Git

Agents work on their own branch `gemini/<id>` in a separate folder. Settings hold the project's Git context: remote, base branch, delivery (local, push the branch, push and PR) and separate permissions for push and PR. The real state is read before every operation; no force push, reset, stash or history rewrite, no change to branch protection or visibility. Every operation is recorded; after a restart or a lost answer the remote is checked first, so no second commit or PR appears. Sol-83's own repository is never a project target. Publishing a version to GitHub scans for secrets before every push, private ones too.

## 12. Project license

Standard (MIT, Apache-2.0, BSD-3-Clause, MPL-2.0, GPL-3.0-only, AGPL-3.0-only, unmodified texts), your own (e.g. source-available) or none. An existing LICENSE is never overwritten without a deliberate choice. It does not relicense dependencies; no license does not mean free use. Sol-83's own license is separate.

## 13. Security, data and updates

See [../../SECURITY.md](../../SECURITY.md) and [UPDATES.md](UPDATES.md).

## 14. Troubleshooting

| Symptom | What to do |
|---|---|
| `doctor`: no sandbox | Linux: install `bubblewrap`. Without it tests and RUN do not run. |
| Project needs attention, sign-in | Sign the CLI in again and click Resume. |
| Antigravity "Individual quota reached… Resets in …" | The Google account's weekly limit: Gemini waits until the stated reset; the other models work. |
| Tests pass for you but not in Sol-83 | Sandboxed tests have no network and write only in the project folder. Allow network for tests in Security, or adapt the tests. |
| `.gemini-setup` did not run | Read and approve it in the project Settings. |
| RUN: "unknown program" / "missing programs" | Install the tool (no administrator rights needed) or add run instructions to the project README. |

## 15. Architecture and tests

See the module table in [../pl/PRZEWODNIK.md](../pl/PRZEWODNIK.md#16-architektura-i-testy). Tests use fake CLIs speaking the real tools' formats and use no subscription:

```bash
python3 -m unittest discover -s tests
```

## 16. Panel looks: Classic and Pro

The panel has two looks with the same functions and data. The CLASSIC / PRO switch is in both (in Classic next to PL/EN, in Pro in the top right corner and in Settings); the choice is remembered in this browser. Pro is the default: `http://127.0.0.1:8765/` opens Pro (`/pro`) unless you choose Classic with the switch; `/?classic` always shows Classic. Both show the author and a link to the licence on a bar (Classic: bottom of the side panel; Pro: status bar and Settings).

Pro in short:

- **Views.** Focus: one project with every tab and button of Classic (activity, plan, questions and tests, versions, content, efficiency, settings, task, RUN, GitHub). Canvas: on the left the **active project** (the one that works; when several work, switch between them with the buttons above the window) with its model windows, below it **the project picked from the stack**, on the right **the project stack**, beside it your **notes**. Drag the three blocks by their header, move the background with the mouse or the trackpad, zoom with Ctrl/Cmd + wheel or the buttons in the bottom right corner; the layout is remembered. A double click on a window bar or ⤢ opens the project in Focus.
- **A project window** shows its key and title, "led by @model" (who has or had the last turn), the latest events, the state in words with an icon, the version and the questions waiting for you. The "❯" field sends a message to the coordinator, like "Message" in Focus (without interrupting the work). On the Canvas the selected project has child windows for its models (@claude, @gemini, @codex) with the role, limit usage and state; the line to the model that is working is animated.
- **The project stack** (Canvas, on the right): every project as a folded bar with its key and name, net plan progress, the tokens it used (e.g. "2.3M") and an icon of its GitHub repository (opens in a new tab when the repository exists). The light glows and never blinks: the palette colour while working, yellow while waiting, orange when stopped, green when finished, red on an error; the icon shape tells the state too. Sections: In progress, **Queue** (in a bracket; change the order by dragging the bars, or with the ⋯ menu; Alt + ↑ / ↓ on the keyboard), Needs attention, Stopped, Finished (in a green bracket), your **groups** ("+ Group", ✎ rename, ✕ delete) and the folded **Archive**. Move a project to a group or the archive by dragging its bar onto the group header or with the ⋯ menu; a project in progress or in the queue stays in its section. A click on the name shows the project in the lower slot. Groups and the archive are saved on the server and change nothing in the project.
- **Notes** (Canvas, "+ Note" in the stack header): a fixed block with a title and scrolling text that appears in the visible part of the Canvas (the view does not move) and saves by itself on the server, each note on its own; if a save fails, the note stays with a warning and the save is retried. Below the text you see which models the project would get. **▶ Create project** (no confirmation dialog) creates a project named after the note, with its text as the task, and queues it at once: every available model in Auto — economy, general role. A model whose weekly limit is used up (also past your weekly threshold) or that is unavailable is off; a used-up 5-hour window does not turn a model off. The note's header then shows the project number and state with its light, and the whole note glows in the state's colour: a dashed frame while queued, brighter while working, orange when stopped, green when finished.
- **Picked from the stack** (the lower slot) has a **Running it (RUN)** section: the "Run from here" folder, the terminal commands (with "Copy") and a RUN button for the recommended version; while the app runs, its link and "Stop RUN".
- **RUN**: a project whose app is running (RUN) has a blinking violet ▶ RUN tag in the stack, in the project window and next to its note, and the status bar says how many apps run (names in the tooltip). It is the only blinking element of the look.
- **Left rail:** projects (the same list as in Classic, with GitHub repositories), history (the latest events of all projects), questions and tests (everything waiting for you, with a counter), limits (the same settings as in Classic: thresholds, accounts, security, Full Power), look settings.
- **Notifications** in the top right corner: a question or a test request with answer buttons, a limit pause with "Try now", a setup script to approve (with its content). ✕ hides a notification in this browser; everything stays in the "Questions and tests" drawer.
- **Status bar:** the number of projects, how many work and wait (for a limit, a model, you), Claude and Codex limit usage with the 5-hour window reset date, Codex and Gemini pauses with their end date.
- **Palettes:** AMBER, PHOSPHOR (default), CYAN, SAKURA, LIGHT. **Effects:** scan lines (on/off, intensity, 60% by default) and panel transparency (45% by default); no animated background. With the system's "reduce motion" the lines are off, and animations stop while the tab is hidden. **System notifications** (Settings): a new question or test request appears as a system notification that stays until you close it; if it disappears after a moment, choose the "Persistent" style for the browser in System Settings → Notifications. Works while the panel is open in a tab.
- **Keyboard:** F, C (Focus and Canvas views), [ and ] (previous and next project), N (new project), +, −, 0 (zoom and fit on the Canvas), arrows (move the view), Alt + arrows (move the selected block), Alt + ↑ / ↓ on a queued project (the order), Enter on a window (Focus), Esc (close the side panel), ? (settings and the list of shortcuts). A state always has a word and an icon, not just a colour; in a narrow window the view buttons shrink to icons and the palettes to a list.

