<p align="center">
  <img src="Assets/logo.jpeg" alt="Sol-83 OpenBeta: Your AI subscriptions. One collaborative team." width="760">
</p>

<p align="center">
  <b>Your AI subscriptions. One collaborative team.</b><br>
  Claude Code · Codex · Gemini (Antigravity) · local LLM
</p>

<p align="center">
  <a href="README.md">Polski</a> ·
  <a href="docs/en/INSTALL.md">Install</a> ·
  <a href="docs/en/GUIDE.md">Guide</a> ·
  <a href="#screenshots">Screenshots</a> ·
  <a href="#coffee">Buy me a coffee ☕</a>
</p>

# Sol-83 (OpenBeta)

### Thought → note → project → done.

Sol-83 is your desk for working with AI. Write an idea down as a note, turn it into a project with one click, and **Claude Code, Codex and Gemini** take turns on it: one does the work, another checks it. You get verified versions, and questions only when the decision is truly yours.

All of it runs on **the subscriptions you already have**: no API keys, no paid extra credits. Sol-83 keeps an eye on the limits, saves tokens and hands the work to the model that still has room.

> **Status:** OpenBeta, developed since November 2026. Tested on macOS (Apple Silicon). Linux is supported in the code but untested on real hardware; Windows is not supported. The status of every feature, with tests and limits: [docs/TRACEABILITY.md](docs/TRACEABILITY.md) (Polish).

## In 30 seconds

- 📝 **Notes instead of prompts.** Write what you want the way you think it. A note with a title sits on the Canvas until you decide it's time.
- ▶️ **One click and it's a project.** "Create project" turns the note into a project, picks the available models in economy mode and queues it. From then on the note shows the project's number and state.
- 🗺️ **Every project has a plan.** The models break the task into features and steps with priorities, and you see the progress in percent and what is left.
- 🤝 **A team, not one model.** The roles you give the models (architect, implementer, tester, content creator…) decide who gets which work. Before every turn Sol-83 picks who does it.
- 💸 **Tokens under control.** 5-hour and weekly limits, handover at a threshold, a cheaper model where it is enough, a short context instead of the whole history.
- 🐙 **GitHub built in.** Work on your repositories or publish finished versions as new repositories, with a secret scan before every push.
- 🧠 **Optionally, a local model.** An LLM on your own machine (e.g. via Ollama) takes over the light coordination without touching your subscription limits.

## A project can be anything

Sol-83 is not just "for code". If it can be described and checked, it can be a project:

| Note | What you get |
|---|---|
| "An app to manage a currency portfolio: rates, a chart, transaction history" | a working app with instructions and a RUN button |
| "A simple tower-defense browser game" | a game you launch with one click and test |
| "Chapter 3 of the novel: she comes back to town after years" | the chapter, checked by a second model for consistency and style |
| "A scientific review of how sleep affects memory, with sources" | a document with chapters, a bibliography and an assessment of the sources |
| "Research: compare three payment providers for an online shop" | a report with the comparison, conclusions and open questions |
| "Analyse the contract with my business partner" | a list of risks, unclear clauses and questions to negotiate |
| "Review the code of my repository" | a review with a list of fixes and, if you want, the fixes on a separate branch |
| "A gluten-free cheesecake recipe for 12, with a shopping list" | the recipe, the proportions and the shopping list |
| "A new version of my household budget Excel workbook" | the workbook with new formulas and a description of the changes |

For documents and research Sol-83 does not build programming scaffolding (tests, scripts). The models check the content and the sources, so no tokens go to things the project does not need.

## The Canvas: your space for thinking and doing

The **Pro** look (the default) is a Canvas: a board you pan and zoom like a map, with everything you work on.

- **Notes** are fixed blocks with a title and scrolling text. They save by themselves. Below the text you see which models the project would get, before you create it. Once created, the note glows in the colour of the project's state: a dashed frame while queued, bright while working, orange when stopped, green when finished.
- **The active project** is the one someone is working on now. You see it with its model windows, joined by lines (the line to the model that is working is animated).
- **The project picked from the stack** sits below the active one, with a "Running it" section: where the finished version is, the terminal commands and a RUN button.
- **The project stack** shows every project as a folded bar: number, name, progress, tokens used ("2.3M"), a GitHub icon and a state light that glows instead of blinking. Drag to reorder the queue, group projects in your own folders ("Analyses", "Games", "Work") and put finished ones into the archive.
- **RUN in sight.** Projects with a running app carry a blinking ▶ RUN tag, and the status bar says how many apps are running. Nothing keeps running "silently".
- **Notifications.** Questions and test requests appear in the corner with answer buttons and, if you want, as a system notification that stays until you close it.

The **Focus** view shows one project in full detail: the turns, the plan, questions and tests, versions, content, efficiency, settings, the task. Prefer a simpler panel? The **CLASSIC** button switches to the classic look with the same functions.

## A plan for every project

A project is not one long prompt. At the start, a model in the architect role turns it into a plan:

- **features and steps** with a priority (must / should / could) and a turn budget,
- **net progress**: how many features are done, minus debt (shortcuts that need fixing),
- **acceptance gates**: a project does not close with an open mandatory question, test or a deferred "must",
- **where the limit went**: how much of the weekly limit each step used.

The plan lives with the project: the models update the status of the steps, and you can order any step at any time with the "Order" button.

## You keep the helm during the project

A project does not have to run from A to Z without you. You can steer it at any moment:

- **❯ message to the coordinator**: ask about the state ("what works already?") or give an order ("add a dark mode"). The coordinator tells a question from work for the models. An urgent change can interrupt the current turn.
- **Change the team on the fly**: another model, thinking level, roles or Auto mode. It applies from the next turn; the current one finishes as it started.
- **"Does not work"** on a version, with a comment, goes back to the models as a concrete fix.
- **Stop, resume, run next**, or drag to reorder the queue.
- **Questions and tests for you** appear only when needed: decisions with ready answers to click, and a manual test by default only for the final version.

## A team of models: roles assigned as needed

Give each model roles (several at once if you like):

| Role | What it does |
|---|---|
| **General** | everything: plan, implementation and review |
| **Architect** | the plan, plan rebuilds and research |
| **Implementer** | the next steps of the plan |
| **Tester** | reviews the changes and tests |
| **Systems analyst** | finds gaps and plans their fixes as debt |
| **Content creator** | ordered graphics, texts and story (after your approval) |

Before every turn the coordinator checks what work is needed now (plan, implementation, review, content) and gives it to a model with a matching role that still has limit left. If a model with the role is unavailable, a model with the General role takes over (or the project waits, if you prefer). For example: Claude as architect and tester, Codex as implementer, Gemini as content creator. Each does what it is best at, and nobody reviews its own work.

**Model choice**, separately for each provider:
- **Manual**: exactly the model you pick,
- **Auto — economy**: the cheapest model that is enough for the work, a stronger one only after repeated failures,
- **Auto — power**: a stronger model from the allowed pool, still within the limits.

A provider's most expensive models are never picked automatically; manually only with your confirmation. Every Auto decision goes into the project's history with its reason.

## Tokens and limits: managed, not a lottery

Subscriptions have limits (a 5-hour window and a weekly one). Sol-83 treats them as a budget:

- **Live limit readings.** The panel shows Claude and Codex usage, when the windows reset and Gemini's pauses. Waiting for a limit costs not a single token.
- **Handover at a threshold.** You set the threshold (e.g. 95% of the 5-hour window, 80% of the week). When a model reaches it, another takes over, and the first comes back after the reset.
- **A short context instead of the whole history.** Every turn starts a fresh session with a compact handover: the task, the plan and the changes since that model's last turn (up to 4,000 characters). The agent does not re-read everything from the start again and again.
- **Reviews with sense.** The second model checks the work when a plan stage closes, on a big change (500+ lines), when the work is declared ready, or at the latest every 3 turns, not after every turn. It gets the diff (up to 30,000 characters), not whole files.
- **Thrifty work in the instructions.** Models write a file in one go instead of many small edits, run the tests once at the end of a turn and keep command output short.
- **No paid surprises.** Antigravity (Gemini) always without paid credits, with a turn time limit; the fast and cheap Gemini Flash by default.
- **Everything counted.** The Efficiency tab shows tokens per model and turn, and how much of each limit window the project used. The stack shows each project's token total.

**Full Power** is for the impatient: while the second model waits for a reset, the same model reviews in a fresh session instead of waiting. Faster, but it uses limits faster too, so it is off by default.

## A local model as a booster

Sol-83 works without a local model, but if you have **Ollama** (e.g. with a Gemma model), you can use it as the message coordinator:

- it answers questions about a project's state without using your subscription limits,
- it tells whether your message is a question or work for the models,
- it prepares ready-to-paste terminal commands to run a version.

You can pick another coordinator (Claude, Codex, Gemini) or none. When the chosen one cannot answer, the local model steps in.

## GitHub integration

- **Start from your repository.** The panel lists your GitHub repositories; a click opens a new project on the one you pick.
- **Or from an existing folder.** The models work on their own branch in a separate working folder. Your main branch stays untouched.
- **Delivery your way**: local only, push the branch, or push with a pull request, with separate permissions for push and PR. No force push, no history rewriting.
- **Publish a finished version** as a new private or public repository; new versions can go there by themselves (for private ones).
- **A secret scan before every push**, private ones too. An API key in the code does not leave without your explicit confirmation.
- The GitHub icon on a project's bar opens the repository in a new tab.

## You decide, Sol-83 keeps watch

- **A version gets a number only after the tests** in the OS sandbox: code from the repository can write only in the project folder and has no network by default.
- **Nothing leaves without your decision**: not to GitHub, not anywhere.
- **The panel is local only** (`127.0.0.1`) and guarded against requests from other sites.
- **A durable order queue**: nothing is lost on a restart, a double click or closing a project.
- **The project language (PL or EN)** is fixed in every instruction to the models; you switch the interface separately.

<a id="screenshots"></a>
## What it looks like

<p align="center">
  <img width="100%" src="Assets/sc11.png" alt="Sol-83 Pro, Focus view with the CYAN palette: the new project form with models, thinking level and roles"><br>
  <sub>Pro, Focus view (CYAN palette): a new project with models, thinking level and roles.</sub>
</p>

<p align="center">
  <img src="Assets/sc5.png" alt="Sol-83 in English, the Classic look with the SAKURA skin: model settings, several roles, Auto mode" width="100%"><br>
  <sub>Classic, SAKURA skin, in English: subscription limits, project cards, models with several roles and Auto mode.</sub>
</p>

<table>
  <tr>
    <td width="50%" align="center" valign="top">
      <img src="Assets/sc2.png" alt="Project plan in the TERMINAL skin"><br>
      <sub>The plan with priorities, turn budgets and an "Order" button on every item (Polish interface).</sub>
    </td>
    <td width="50%" align="center" valign="top">
      <img src="Assets/sc3.png" alt="Model and role settings in the TERMINAL skin"><br>
      <sub>Settings: the current turn's snapshot, several roles per model, Auto mode (Polish interface).</sub>
    </td>
  </tr>
</table>

<details>
  <summary><b>More screenshots</b></summary>
  <p align="center">
    <img src="Assets/sc4.png" alt="Sol-83 with the SAKURA skin: limits, project cards, the plan with net progress" width="100%"><br>
    <sub>Limits, project cards and the plan with net progress (Polish interface).</sub>
  </p>
  <p align="center">
    <img src="Assets/sc1.png" alt="Turns in the TERMINAL skin" width="100%"><br>
    <sub>Activity: clear turn headers (who, model, kind of work) and the local coordinator's answer (Polish interface).</sub>
  </p>
</details>

## Who it is for

For anyone with **at least two AI subscriptions** (e.g. Claude and ChatGPT/Codex, optionally Gemini) who wants them to finally work together: developers, people who vibe code, and people who don't write code at all but have an idea for a text, an analysis or research. You don't need to know Git or configure models: start from a note, Sol-83 sets up the rest, and you can change it whenever you like.

## Quick start

Full install from scratch, step by step: **[docs/en/INSTALL.md](docs/en/INSTALL.md)**.

```bash
git clone https://github.com/MikeMcqueen83/Sol-83-OpenBeta.git
```

```bash
cd Sol-83-OpenBeta && ./bin/setup && ./sol83 doctor
```

```bash
./sol83 serve
```

Then open http://127.0.0.1:8765, click **+ Note** in the project stack, describe your idea and click **▶ Create project**.

## Documentation

[Install](docs/en/INSTALL.md) · [Guide](docs/en/GUIDE.md) (notes and the Canvas, projects, the plan, models and roles, Auto, limits and tokens, versions and RUN, questions, content, language, Git and GitHub, licences, Classic and Pro looks) · [Data, backups, updates, rollback](docs/en/UPDATES.md) · [Security](SECURITY.md) · [Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md)

<a id="coffee"></a>
## ☕ Buy me a coffee

I develop Sol-83 on my own and share it free for non-commercial use. If it saved you time or subscription limits, if you like the idea, or you would simply like new features to land sooner, you can buy me a coffee. It genuinely helps keep the project going, and every bit of support is hugely motivating. Thank you! 🌸

<p align="center">
  <a href="https://buycoffee.to/evvil" target="_blank"><img src="https://buycoffee.to/static/img/share/share-button-dark--en.png" width="406" height="92" style="width: 406px; height: 92px" alt="Buy a coffee for Evvil at buycoffee.to"></a>
</p>

## License

Sol-83 is **source-available**, not OSI open source: non-commercial use by individuals is allowed; any commercial use, including use by companies (internal too) and putting the code or any part of it into monetized products or services, needs the author's prior written consent; contributions go through forks or branches. The terms are a draft pending legal review: [LICENSE.md](LICENSE.md). Duet and other components keep their own licenses: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Projects you create with Sol-83 get the license you choose.

Author: Michał Werpachowski.
