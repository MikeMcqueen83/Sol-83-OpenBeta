"""Project lifecycle: queue, engine processes, stop/resume, test copies."""
from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Optional

from . import assets as content
from . import github, gitops, limits, livelog, monitor, sandbox
from . import plan as project_plan
from . import roles as model_roles
from .catalog import MODEL_OFF
from .gitops import Git
from .messages import Msg, en
from .paths import BASE, CONFIG, DUET, PROJECTS, RUNS, STATE, WORKTREES, agent_path

AGENT_NAMES = {'claude': 'Claude', 'codex': 'Codex', 'gemini': 'Gemini'}
from .store import Store

DEFAULT_CLAUDE_MODEL = 'opus'
DEFAULT_CLAUDE_REASONING = 'xhigh'
DEFAULT_CODEX_MODEL = 'gpt-6.1-sol'
DEFAULT_CODEX_REASONING = 'high'
DEFAULT_GEMINI_REASONING = 'high'
DEFAULT_GEMINI_MODEL = 'default'
SIDES = ('claude', 'codex', 'gemini')
OLD_SIDES = ('claude', 'codex')
BACKENDS = {'claude': 'claude', 'codex': 'codex', 'gemini': 'gemini'}
MODEL_CHOICES = tuple(f'{side}_{kind}' for side in SIDES for kind in ('model', 'reasoning'))
ROLE_CHOICES = (*(f'{side}_role' for side in SIDES), 'role_fallback')
_SAFE_CHOICE = re.compile(r'^[\w.:\-\[\]]*$')
DEFAULT_TURNS = 30
DEFAULT_TURN_TIMEOUT = 3600
TICK_S = 2.0
REPOS_CACHE_S = 60
RUNNING = ('running', 'stopping')
ROLE_PROMPT = """Pracujesz na zmianę z innymi modelami nad zadaniem użytkownika. Koordynator decyduje, kto ma turę, i zapisuje checkpoint Git po każdej turze. Nie uruchamiaj innych modeli i nie twórz commitów. Użytkownik nie odpowiada w trakcie pracy: decyzje podejmuj sam, a wynik przekazuj innym modelom do sprawdzenia, nie użytkownikowi.

W każdej turze:
1. Przeczytaj blok GEMINI na początku wiadomości. Uwagi użytkownika mają pierwszeństwo przed wszystkim innym.
2. Sprawdź sam kod, diff i wyniki. Raport partnera to wskazówka, nie dowód.
3. Wykonaj jeden spójny krok: zbuduj, napraw albo przetestuj i opisz usterki. Trzymaj turę w granicach kilkunastu minut pracy.
4. Uruchom testy i podaj ich rzeczywisty wynik.

Nie osłabiaj testów, aby przeszły. Nie zmieniaj zadania ani instrukcji. Nie odwracaj decyzji partnera z powodów stylistycznych. Odpowiadaj po polsku.

Zakończ odpowiedź sekcją CO TESTOWAĆ: z krótką listą kroków, które człowiek może sprawdzić w tej wersji.
Jeśli sprawdziłeś pracę partnera, nic nie zmieniłeś, działa, ale cel nie jest jeszcze spełniony, napisz w osobnej linii: WERSJA OK.
Gdy cały cel jest spełniony i sprawdziłeś to samodzielnie, podaj LGTM rationale i {SENTINEL} w osobnej linii. Akceptacja dotyczy dokładnie bieżącego stanu kodu: każda Twoja zmiana wymaga ponownego sprawdzenia przez partnera."""


def slugify(text: str) -> str:
    table = str.maketrans('ąćęłńóśźżĄĆĘŁŃÓŚŹŻ', 'acelnoszzACELNOSZZ')
    slug = re.sub(r'[^a-z0-9]+', '-', text.translate(table).lower()).strip('-')
    return slug[:40] or 'projekt'


def title_from_task(task: str) -> str:
    for line in task.splitlines():
        line = line.strip().lstrip('#').strip()
        if line:
            return line[:80]
    return 'Nowy projekt'


def preview(text: str, limit: int = 90) -> str:
    line = text.strip().splitlines()[0] if text.strip() else ''
    return line if len(line) <= limit else line[:limit - 1] + '…'


def _ps(*args: str) -> str:
    """`ps` in a fixed locale: a server started from another terminal must read the same text."""
    return subprocess.run(['ps', *args], capture_output=True, text=True,
                          env={**os.environ, 'LC_ALL': 'C'}).stdout


def process_start(pid: int) -> Optional[str]:
    return _ps('-o', 'lstart=', '-p', str(pid)).strip() or None


def engine_pids(project_id: str) -> list:
    """Engines working on this project, found by their command line. This survives
    server restarts and never mistakes a reused process id for an engine."""
    markers = (f'run-{project_id}.json', f'{RUNS / project_id}/')
    pids = []
    for line in _ps('-axo', 'pid=,command=').splitlines():
        pid, _, command = line.strip().partition(' ')
        if 'duet.py' in command and any(marker in command for marker in markers):
            pids.append(int(pid))
    return pids


def recommended_version(versions: list) -> Optional[dict]:
    """What the user should test: the newest version both models checked,
    otherwise the newest one the coordinator saw passing. Never one they rejected."""
    usable = [version for version in versions if version.get('user_verdict') != 'bad']
    approved = [version for version in usable if version['level'] == 'approved']
    return (approved or usable or [None])[0]


def owns_repo(project: dict) -> bool:
    """Sol-83 created this repository: its main may follow the versions. A user's own
    repository, given as a folder or cloned from GitHub, keeps its main untouched."""
    repo = project.get('repo_path')
    if not repo or not Path(repo).is_dir() or Path(repo).resolve().parent != PROJECTS.resolve():
        return False
    if project.get('github_repo') and project.get('github_branch') != 'main':
        return False
    git = Git(repo)
    root = git.run('rev-list', '--max-parents=0', 'main', check=False).splitlines()
    return len(root) == 1 and git.run('log', '-1', '--format=%s', root[0], check=False) == gitops.START_SUBJECT


def test_folder(project_id: str) -> Path:
    return WORKTREES / f'{project_id}-testy'


class Supervisor:
    def __init__(self, store: Optional[Store] = None):
        self.store = store or Store()
        self.procs: dict = {}
        self.reader = limits.Reader(ttl=float(os.environ.get('GEMINI_LIMITS_TTL', 60)))
        self.lock = threading.RLock()
        self.running = False
        self.repos: list = []
        self.repos_read_at = 0.0
        self.upload_failed: dict = {}
        self.deliver_failed: dict = {}
        self.watched: dict = {}
        self.run_steps_cache: dict = {}

    # ---- Commands from the web interface ------------------------------

    def create_project(self, task: str, title: str = '', repo_path: str = '', verify_cmd: str = '',
                       max_turns: int = DEFAULT_TURNS, claude_model: str = '',
                       codex_model: str = '', claude_reasoning: str = '',
                       codex_reasoning: str = '', turn_timeout: int = DEFAULT_TURN_TIMEOUT,
                       github_repo: str = '', claude_role: str = '', codex_role: str = '',
                       role_fallback: str = '', gemini_model: str = '', gemini_reasoning: str = '',
                       gemini_role: str = '') -> dict:
        self._validate_models(claude_model, codex_model, claude_reasoning, codex_reasoning, gemini_model,
                              gemini_reasoning)
        team = self._validate_team({'claude_model': claude_model.strip(), 'codex_model': codex_model.strip(),
                                    'gemini_model': gemini_model.strip() or MODEL_OFF,
                                    'claude_role': claude_role.strip(), 'codex_role': codex_role.strip(),
                                    'gemini_role': gemini_role.strip(), 'role_fallback': role_fallback.strip()},
                                   SIDES)
        task = task.strip()
        if not task:
            raise ValueError(Msg('err_task'))
        if max_turns < 2:
            raise ValueError(Msg('err_turns'))
        repo_path = repo_path.strip()
        github_repo = github_repo.strip()
        if github_repo and not github.valid_repo(github_repo):
            raise ValueError(Msg('gh_bad_repo'))
        if repo_path:
            problem = gitops.validate_source(repo_path)
            if problem:
                raise ValueError(problem)
        project_id = uuid.uuid4().hex[:10]
        project = self.store.add_project(
            id=project_id, title=title.strip() or title_from_task(task), task=task, status='queued',
            repo_path=repo_path or None, verify_cmd=verify_cmd.strip() or None, max_turns=max_turns,
            github_repo=github_repo or None,
            github_url=f'https://github.com/{github_repo}' if github_repo else None,
            turn_timeout=turn_timeout, claude_model=claude_model.strip() or DEFAULT_CLAUDE_MODEL,
            codex_model=codex_model.strip() or DEFAULT_CODEX_MODEL,
            claude_reasoning=claude_reasoning.strip() or DEFAULT_CLAUDE_REASONING,
            codex_reasoning=codex_reasoning.strip() or DEFAULT_CODEX_REASONING,
            gemini_model=team['gemini_model'], gemini_reasoning=gemini_reasoning.strip() or DEFAULT_GEMINI_REASONING,
            meta=json.dumps({'agents': list(SIDES)}), **{key: team[key] for key in ROLE_CHOICES})
        self.store.event(project_id, 'created', Msg('created'))
        return project

    def _validate_models(self, *choices: str) -> None:
        if not all(_SAFE_CHOICE.match(choice) for choice in choices):
            raise ValueError(Msg('err_model'))

    def sides(self, project: dict) -> list:
        """The models this project's engine has: projects from before Gemini have two."""
        return self.store.meta(project['id']).get('agents') or list(OLD_SIDES)

    def _validate_team(self, team: dict, sides) -> dict:
        """At least one model on, known roles, and every kind of work taken by someone."""
        team = {**team, **{f'{side}_role': team.get(f'{side}_role') or model_roles.GENERAL for side in SIDES},
                'role_fallback': team.get('role_fallback') or 'general'}
        if any(team[f'{side}_role'] not in model_roles.ROLES for side in SIDES) \
                or team['role_fallback'] not in model_roles.FALLBACKS:
            raise ValueError(Msg('err_role'))
        enabled = [team.get(f'{side}_model') not in (None, MODEL_OFF) if side == 'gemini'
                   else team.get(f'{side}_model') != MODEL_OFF for side in sides]
        if not any(enabled):
            raise ValueError(Msg('err_all_off'))
        missing = model_roles.missing([team[f'{side}_role'] for side in sides], enabled)
        if missing:
            raise ValueError(Msg('err_roles', works=', '.join(Msg(f'work_{work}') for work in missing)))
        return team

    def set_models(self, project_id: str, **choices: str) -> None:
        """Change model or thinking level; the engine reads them before every turn."""
        project = self._require(project_id)
        sides = list(SIDES)
        chosen = {key: value.strip() for key, value in choices.items()
                  if key in (*MODEL_CHOICES, *ROLE_CHOICES) and value.strip()}
        self._validate_models(*chosen.values())
        self._validate_team({**project, **chosen}, sides)
        self.store.update_project(project_id, **chosen)
        before, project = project, self.store.project(project_id)

        def listing(text):
            parts = [Msg('role_of', who=AGENT_NAMES[side], role=text(side)) for side in sides]
            return Msg(f'join{len(parts)}', **dict(zip('abc', parts)))
        if any(model_roles.of(before, side) != model_roles.of(project, side) for side in sides) \
                or (before['role_fallback'] or 'general') != (project['role_fallback'] or 'general'):
            self.store.event(project_id, 'models', Msg(
                'roles_changed', roles=listing(lambda side: Msg(f'role_{model_roles.of(project, side)}')),
                fallback=Msg(f"fallback_{project['role_fallback'] or 'general'}")))
        if any(key in MODEL_CHOICES for key in chosen):
            self.store.event(project_id, 'models', Msg('models_changed', models=listing(
                lambda side: Msg('model_off') if project[f'{side}_model'] in (None, MODEL_OFF)
                else f"{project[f'{side}_model']}, {project[f'{side}_reasoning']}")))
        self._join_engine(project)

    def _join_engine(self, project: dict) -> None:
        """A model switched on that the project's engine does not have, such as Gemini in a project
        from before it existed, joins when the engine starts again: right after the current turn."""
        joining = [side for side in SIDES if side not in self.sides(project)
                   and project[f'{side}_model'] not in (None, MODEL_OFF)]
        if not joining:
            return
        meta = self.store.meta(project['id'])
        meta.update(agents=[side for side in SIDES if side in self.sides(project) or side in joining],
                    new_engine=True)
        self.store.save_meta(project['id'], meta)
        names = ', '.join(AGENT_NAMES[side] for side in joining)
        if project['status'] in RUNNING and self._alive(project):
            self.store.update_project(project['id'], resume_after_stop=1)
            self.stop(project['id'])
            self.store.event(project['id'], 'models', Msg('engine_join_now', names=names))
        else:
            self.store.event(project['id'], 'models', Msg('engine_join_next', names=names))

    def add_note(self, project_id: str, text: str, urgent: bool = False, order: bool = False) -> None:
        """A note reaches the next turn. An order of new work also rebuilds the plan."""
        project = self._require(project_id)
        text = text.strip()
        if not text:
            raise ValueError(Msg('err_note'))
        if order:
            meta = self.store.meta(project_id)
            meta['replan'] = True
            self.store.save_meta(project_id, meta)
        note_id = self.store.add_note(project_id, text, urgent, 'order' if order else 'note')
        self.store.event(project_id, 'note', Msg('note_urgent' if urgent else 'note_next',
                                                 preview=preview(text)), body=text)
        if urgent and project['status'] == 'running':
            self.store.update_project(project_id, resume_after_stop=1)
            self.stop(project_id, immediate=True)
        elif project['status'] == 'done':
            self.store.update_note(note_id, reopened='done')
            self.resume(project_id)

    def order_asset(self, project_id: str, kind: str, prompt: str, path: str, size: str = '',
                    style: str = '') -> None:
        """The user orders content in the panel. It enters .sol83/assets.json before the next turn,
        and the note wakes the project like any other work."""
        project = self._require(project_id)
        prompt, path = prompt.strip(), path.strip().lstrip('/')
        if kind not in content.TYPES or not prompt or not path or '..' in Path(path).parts:
            raise ValueError(Msg('err_asset'))
        meta = self.store.meta(project_id)
        meta.setdefault('asset_orders', []).append(
            {key: value for key, value in (('type', kind), ('prompt', prompt[:2000]), ('path', path),
                                           ('size', size.strip()), ('style', style.strip())) if value})
        self.store.save_meta(project_id, meta)
        if not any(model_roles.of(project, side) == model_roles.CONTENT
                   and project[f'{side}_model'] not in (None, MODEL_OFF) for side in SIDES):
            self.store.event(project_id, 'note', Msg('asset_no_creator'))
        self.add_note(project_id, f'Użytkownik zamówił treść ({kind}) do pliku {path}: {prompt[:300]}. '
                                  'Zamówienie jest w .sol83/assets.json.')

    def asset_file(self, project_id: str, path: str) -> Path:
        project = self._require(project_id)
        target = content.file_of(project['worktree'], path) if project.get('worktree') else None
        if not target or target.suffix.lower() not in content.IMAGE_TYPES:
            raise LookupError(Msg('err_not_found'))
        return target

    def delete_project(self, project_id: str) -> None:
        """Remove a project for good: records, runs, the agents' workshop, the test folder and a
        repository Sol-83 created. A user's own repository stays, without Sol-83's branch, version
        tags and worktrees. GitHub is never touched: it is the archive."""
        with self.lock:
            project = self._require(project_id)
            self._kill_engines(project_id)
            own = owns_repo(project)
            repo = project['repo_path']
            folders = [WORKTREES / project_id, test_folder(project_id), RUNS / project_id]
            if repo and Path(repo).is_dir() and not own:
                git = Git(repo)
                for folder in folders[:2]:
                    if folder.exists():
                        git.run('worktree', 'remove', '--force', str(folder), check=False)
                git.run('worktree', 'prune', check=False)
                if project['branch']:
                    git.run('branch', '-D', project['branch'], check=False)
                tags = git.run('tag', '-l', f'gemini/{project_id}/*', check=False).split()
                if tags:
                    git.run('tag', '-d', *tags, check=False)
            for folder in folders:
                shutil.rmtree(folder, ignore_errors=True)
            if own and Path(repo).name.endswith(project_id):
                shutil.rmtree(repo, ignore_errors=True)
            for leftover in (CONFIG / f'run-{project_id}.json', STATE / f'tokens-{project_id}.json'):
                leftover.unlink(missing_ok=True)
            self.store.delete_project(project_id)
            for cache in (self.upload_failed, self.deliver_failed, self.watched):
                cache.pop(project_id, None)

    def _kill_engines(self, project_id: str) -> None:
        """Stop the project's engine at once; its agents end with it."""
        proc = self.procs.pop(project_id, None)
        for pid in engine_pids(project_id):
            os.kill(pid, signal.SIGTERM)
        deadline = time.monotonic() + 15
        while engine_pids(project_id) and time.monotonic() < deadline:
            time.sleep(0.2)
        for pid in engine_pids(project_id):
            os.kill(pid, signal.SIGKILL)
        if proc is not None:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass

    def _setup(self, project_id: str, folder: Path) -> str:
        """The project's `.gemini-setup`, in the sandbox and only in the version the user approved.
        A failure is reported but does not stop the agents: their worktree is usable without it."""
        meta = self.store.meta(project_id)
        try:
            status = gitops.run_setup(folder, meta.get('setup_approved'),
                                      allow_unsandboxed=bool(self.store.setting('allow_unsandboxed', 0)))
        except gitops.GitError as exc:
            self.store.event(project_id, 'attention', Msg('setup_failed', path=str(folder), detail=exc.args[0]))
            return 'failed'
        if status == 'needs_approval':
            script = gitops.setup_script(folder)
            if meta.get('setup_announced') != script['sha']:
                meta['setup_announced'] = script['sha']
                self.store.save_meta(project_id, meta)
                self.store.event(project_id, 'attention', Msg('setup_needs_approval', path=script['path']),
                                 data={'sha': script['sha']})
        elif status == 'ran':
            self.store.event(project_id, 'setup', Msg('setup_ran', path=str(folder)))
        return status

    def approve_setup(self, project_id: str, sha: str) -> None:
        """The user read this exact `.gemini-setup` and lets it run, in the sandbox. Any later change
        to the script needs a new approval."""
        project = self._require(project_id)
        folder = project.get('worktree')
        script = gitops.setup_script(folder) if folder else None
        if not script or script['sha'] != sha:
            raise ValueError(Msg('err_setup_changed'))
        meta = self.store.meta(project_id)
        meta['setup_approved'] = sha
        self.store.save_meta(project_id, meta)
        self.store.event(project_id, 'setup', Msg('setup_approved', sha=sha[:12]))
        folders = [Path(folder)] + ([test_folder(project_id)] if project['test_version']
                                    and test_folder(project_id).is_dir() else [])
        threading.Thread(target=lambda: [self._setup(project_id, f) for f in folders], daemon=True).start()

    def set_verify(self, project_id: str, command: str) -> None:
        """The test command can be set or changed later: it applies to the turn that ends next."""
        self._require(project_id)
        command = command.strip()[:500]
        self.store.update_project(project_id, verify_cmd=command or None)
        self.store.event(project_id, 'models', Msg('verify_changed', command=command) if command
                         else Msg('verify_removed'))

    def withdraw_note(self, project_id: str, question_id: int) -> None:
        """Take back a message routed to the agents, as long as no turn has received it.
        A project it reopened goes back to where it was."""
        with self.lock:
            project = self._require(project_id)
            question = next((q for q in self.store.questions(project_id) if q['id'] == question_id), None)
            pending = self.store.pending_notes(project_id)
            note = next((n for n in reversed(pending) if question and n['text'] == question['question']), None)
            if not note:
                raise ValueError(Msg('err_withdraw'))
            self.store.update_note(note['id'], status='withdrawn')
            rest = [n for n in pending if n['id'] != note['id']]
            if note['kind'] == 'order' and not any(n['kind'] == 'order' for n in rest):
                meta = self.store.meta(project_id)
                meta.pop('replan', None)
                self.store.save_meta(project_id, meta)
            if note['reopened'] and project['status'] == 'queued' and not rest:
                self.store.update_project(project_id, status=note['reopened'],
                                          finished_at=time.time() if note['reopened'] == 'done' else None)
            elif project['status'] == 'stopping' and project['resume_after_stop'] and not rest:
                self.store.update_project(project_id, resume_after_stop=0)
            self.store.event(project_id, 'note', Msg('note_withdrawn', preview=preview(note['text'])))

    def start_item(self, project_id: str, item_id: str) -> None:
        """The user picks a plan item, debt included: it goes first in the next turn."""
        project = self._require(project_id)
        plan, _ = project_plan.load(project['worktree']) if project.get('worktree') else (None, None)
        item = next((item for item in project_plan.items(plan) if item['id'] == item_id), None)
        if not item:
            raise ValueError(Msg('err_item'))
        meta = self.store.meta(project_id)
        meta['focus'] = item_id
        self.store.save_meta(project_id, meta)
        self.store.event(project_id, 'note', Msg('item_ordered', item=item_id, title=item['title']))
        self.add_note(project_id, f"Użytkownik zleca pozycję planu {item_id}: {item['title']}. "
                                  'Zrób ją teraz, przed innymi pozycjami, i zaktualizuj jej status w planie.')

    def continue_after_interrupt(self, project_id: str) -> None:
        """An interrupting message turned out to be work: resume once the turn has stopped."""
        project = self._require(project_id)
        pending = self.store.pending_notes(project_id)
        if project['status'] == 'stopping':
            self.store.update_project(project_id, resume_after_stop=1)
        elif project['status'] in ('stopped', 'attention'):
            if pending:
                self.store.update_note(pending[-1]['id'], reopened=project['status'])
            self.resume(project_id)

    def live_log(self, project_id: str) -> dict:
        project = self._require(project_id)
        return livelog.live(project.get('worktree'), (self.store.live(project_id) or {}).get('speaker'))

    def stop(self, project_id: str, immediate: bool = False) -> None:
        with self.lock:
            project = self._require(project_id)
            if project['status'] == 'queued':
                self.store.update_project(project_id, status='stopped')
                self.store.event(project_id, 'stopped', Msg('stopped_queue'))
                return
            pids = engine_pids(project_id)
            if project['status'] not in RUNNING or not pids:
                return
            mode = 'immediate' if immediate else 'graceful'
            self.store.update_project(project_id, status='stopping', stop_requested=mode)
            self.store.event(project_id, 'stopping',
                             Msg('stopping_now' if immediate else 'stopping_turn'))
            for pid in pids:
                os.kill(pid, signal.SIGTERM if immediate else signal.SIGUSR1)

    def resume(self, project_id: str, note: str = '') -> None:
        with self.lock:
            project = self._require(project_id)
            if project['status'] in (*RUNNING, 'queued'):
                return
            if note.strip():
                self.store.add_note(project_id, note.strip())
            self.store.update_project(project_id, status='queued', stop_requested=None,
                                      status_detail=None, finished_at=None, accepted_solo=0)
            self.store.event(project_id, 'resumed', Msg('resumed'))

    def accept(self, project_id: str) -> None:
        """The user takes the result without waiting for the second model."""
        with self.lock:
            project = self._require(project_id)
            self.store.update_project(project_id, accepted_solo=1)
            self.store.event(project_id, 'accepted', Msg('accepted'))
            if project['status'] in RUNNING and self._alive(project):
                self.stop(project_id)
            else:
                self.store.update_project(project_id, status='done', finished_at=time.time())

    def set_verdict(self, project_id: str, number: int, works: bool, comment: str = '') -> None:
        """The user's own test result. "Does not work" goes back to the agents."""
        project = self._require(project_id)
        version = self.store.version(project_id, number)
        if not version:
            raise ValueError(Msg('err_version'))
        self.store.update_version(project_id, number, user_verdict='ok' if works else 'bad',
                                  user_verdict_at=time.time())
        if works:
            self.store.event(project_id, 'verdict', Msg('verdict_ok', number=number))
            return
        detail = comment.strip() or 'bez dodatkowego opisu'
        self.store.event(project_id, 'verdict', Msg('verdict_bad', number=number, detail=detail))
        self.store.add_note(project_id, f'Użytkownik przetestował v{number} '
                            f"(commit {version['commit_sha'][:7]}) i to NIE działa: {detail}")
        if project['status'] not in (*RUNNING, 'queued'):
            self.resume(project_id)

    def prepare_test_copy(self, project_id: str, number: int) -> str:
        """The user picks a version for the "Run from here" folder. It stays there until
        a newer recommended version arrives."""
        project = self._require(project_id)
        version = self.store.version(project_id, number)
        if not version:
            raise ValueError(Msg('err_version'))
        try:
            path = self._put_version(project, version)
        except gitops.GitError as exc:
            raise RuntimeError(exc.args[0])
        recommended = recommended_version(self.store.versions(project_id))
        self.store.update_project(project_id, delivered_version=max(
            recommended['number'] if recommended else 0, project['delivered_version'] or 0))
        self.store.event(project_id, 'test_copy', Msg('test_copy', number=number))
        return path

    def _put_version(self, project: dict, version: dict) -> str:
        if owns_repo(project):
            gitops.deliver(project['repo_path'], version['tag'])
            path = project['repo_path']
        else:
            path = str(test_folder(project['id']))
            gitops.checkout_test_copy(project['repo_path'], Path(path), version['tag'])
            self.store.update_project(project['id'], test_version=version['number'])
            self._setup(project['id'], Path(path))
        self.store.update_project(project['id'], run_version=version['number'])
        return path

    def _deliver(self) -> None:
        """Each new recommended version lands where the user runs the project: on main of
        a repository Sol-83 created, or in the test folder of the user's own repository."""
        for project in self.store.projects():
            if not project['repo_path'] or not project['worktree']:
                continue
            version = recommended_version(self.store.versions(project['id']))
            if not version:
                continue
            if project['delivered_version'] is None and project['test_version'] and not owns_repo(project):
                # Picked by hand before this existed: keep it until a newer version arrives.
                self.store.update_project(project['id'], delivered_version=version['number'],
                                          run_version=project['test_version'])
                continue
            # Only forward: a rejected version stays until a newer one, never an older one in its place.
            if version['number'] <= max(project['delivered_version'] or 0, project['run_version'] or 0):
                continue
            if self.deliver_failed.get(project['id']) == version['number']:
                continue
            try:
                path = self._put_version(project, version)
            except (gitops.GitError, OSError) as exc:
                self.deliver_failed[project['id']] = version['number']
                last = self.store.last_event(project['id'], 'deliver')
                if not last or json.loads(last['data'] or '{}') != {'number': version['number'], 'ok': False}:
                    detail = exc.args[0] if exc.args and isinstance(exc.args[0], str) else str(exc)
                    self.store.event(project['id'], 'deliver', Msg('deliver_failed', number=version['number'],
                                                                   detail=detail),
                                     data={'number': version['number'], 'ok': False})
                continue
            self.store.update_project(project['id'], delivered_version=version['number'])
            self.store.event(project['id'], 'deliver', Msg('deliver_done', number=version['number'], path=path),
                             data={'number': version['number'], 'ok': True})

    def publish(self, project_id: str, number: int, name: str = '',
                visibility: str = 'private', confirmed_secrets: str = '') -> dict:
        """Send one numbered version to GitHub. Work in progress never leaves this machine."""
        project = self._require(project_id)
        version = self.store.version(project_id, number)
        if not version:
            raise ValueError(Msg('err_version'))
        if version['user_verdict'] == 'bad':
            raise ValueError(Msg('gh_rejected_version'))
        if visibility not in ('private', 'public'):
            raise ValueError(Msg('gh_bad_visibility'))
        state = github.status()
        if not state['ready']:
            raise RuntimeError(state['problem'])
        git = Git(project['repo_path'])
        repo = project['github_repo'] or github.github_origin(git)
        shared_repo = bool(repo) and not project['github_repo']
        public = github.visibility_of(repo) == 'public' if repo else visibility == 'public'
        commit = version['commit_sha']
        oversized = github.find_oversized(git, commit)
        if oversized:
            raise RuntimeError(Msg('gh_too_large', items=', '.join(oversized[:5])))
        acknowledged = github.check_secrets(git, commit, confirmed_secrets)
        branch = project['github_branch'] or (project['branch'] if shared_repo else 'main')
        if not repo:
            name = name.strip() or slugify(project['title'])
            if not github.valid_name(name):
                raise ValueError(Msg('gh_bad_name'))
            repo = github.create_repo(name, public, project['title'])
        remote_tag = version['tag'] if branch != 'main' else f'v{number}'
        github.push(git, repo, commit, branch, version['tag'], remote_tag)
        shown = 'public' if public else 'private'
        self.store.update_project(project_id, github_repo=repo, github_url=f'https://github.com/{repo}',
                                  github_visibility=shown, github_version=number,
                                  github_branch=branch)
        self.store.event(project_id, 'github', Msg('gh_published', number=number, repo=repo,
                                                   visibility=Msg(f'visibility_{shown}')),
                         data={'acknowledged_secrets': acknowledged} if acknowledged else None)
        return {'url': f'https://github.com/{repo}'}

    def set_github_auto(self, project_id: str, enabled: bool) -> None:
        project = self._require(project_id)
        if not project['github_repo']:
            raise ValueError(Msg('gh_not_published'))
        self.store.update_project(project_id, github_auto=int(enabled))

    def github_repos(self) -> list:
        """Repositories of the signed-in account, cached because the panel polls."""
        if time.time() - self.repos_read_at > REPOS_CACHE_S:
            try:
                self.repos = github.list_repos()
            except (RuntimeError, ValueError):
                self.repos = []
            self.repos_read_at = time.time()
        return self.repos

    def _sync_github(self) -> None:
        """New versions of connected private repositories go up on their own.
        A public repository always waits for the user's click."""
        for project in self.store.projects():
            if not project['github_auto'] or project['github_visibility'] != 'private':
                continue
            version = recommended_version(self.store.versions(project['id']))
            if not version or version['number'] <= (project['github_version'] or 0):
                continue
            if self.upload_failed.get(project['id']) == version['number']:
                continue
            try:
                self.publish(project['id'], version['number'])
            except (RuntimeError, ValueError) as exc:
                self.upload_failed[project['id']] = version['number']
                self.store.event(project['id'], 'attention',
                                 Msg('gh_auto_failed', number=version['number'], detail=str(exc)[:200]))

    def _watch_efficiency(self) -> None:
        """After each finished turn, raise every new signal once: Activity and a notification."""
        for project in self.store.projects(*RUNNING):
            last = self.store.last_event(project['id'], 'turn_end')
            if not last or self.watched.get(project['id']) == last['id']:
                continue
            self.watched[project['id']] = last['id']
            meta = self.store.meta(project['id'])
            announced = set(meta.get('announced', []))
            latest = self.store.latest_version(project['id'])
            cycle = latest['number'] if latest else 0
            for item in monitor.assess(self.store, project)['signals']:
                key = item['key'] if item['key'] == 'unassigned' else f"{item['key']}:{cycle}"
                if key in announced:
                    continue
                announced.add(key)
                self.store.event(project['id'], 'monitor', item['text'],
                                 data={'en': item['text_en'], 'key': item['key']})
                with self.store._db() as db:
                    db.execute('UPDATE events SET text_en=? WHERE id=(SELECT MAX(id) FROM events '
                               'WHERE project_id=?)', (item['text_en'], project['id']))
                monitor.notify(f"{project['title']}: {item['text']}")
            meta['announced'] = sorted(announced)
            self.store.save_meta(project['id'], meta)

    def change_visibility(self, project_id: str, visibility: str, confirmed_secrets: str = '') -> None:
        project = self._require(project_id)
        if not project['github_repo']:
            raise ValueError(Msg('gh_not_published'))
        if visibility not in ('private', 'public'):
            raise ValueError(Msg('gh_bad_visibility'))
        public = visibility == 'public'
        if public and project['github_version']:
            version = self.store.version(project_id, project['github_version'])
            github.check_secrets(Git(project['repo_path']), version['commit_sha'], confirmed_secrets)
        github.set_visibility(project['github_repo'], public)
        self.store.update_project(project_id, github_visibility=visibility)
        self.store.event(project_id, 'github', Msg('gh_visibility', repo=project['github_repo'],
                                                   visibility=Msg(f'visibility_{visibility}')))

    def limits_view(self, force: bool = False) -> dict:
        snapshots = self.reader.read(force=force)
        view = {}
        for name in limits.PROVIDERS:
            threshold = self.store.threshold(name)
            found = limits.availability(snapshots.get(name), threshold, self.store.block(name))
            view[name] = {**(snapshots.get(name) or {}), 'threshold': threshold[limits.FIVE_HOUR],
                          'weekly_threshold': threshold[limits.SEVEN_DAY],
                          'reason_en': en(found.reason),
                          'configured': self.store.setting(f'threshold_{name}'),
                          'configured_weekly': self.store.setting(f'weekly_{name}', 100.0),
                          'available': found.available, 'until': found.until,
                          'reason': found.reason}
        problem = limits.gemini_problem()
        found = limits.availability(None, 100.0, self.store.block('gemini'))
        view['gemini'] = {'provider': 'gemini', 'no_reading': True, 'problem': problem, 'problem_en': en(problem),
                          'available': found.available and not problem, 'until': found.until,
                          'reason': found.reason if not found.available else '', 'reason_en': en(found.reason)}
        return view

    def _require(self, project_id: str) -> dict:
        project = self.store.project(project_id)
        if not project:
            raise LookupError(Msg('err_project'))
        return project

    # ---- Engine lifecycle ---------------------------------------------

    def _alive(self, project: dict) -> bool:
        proc = self.procs.get(project['id'])
        if proc is not None and proc.poll() is None:
            return True
        return bool(engine_pids(project['id']))

    def _engine_env(self, project_id: str) -> dict:
        # Subscription only: an API key in the server's environment never reaches the agents.
        env = {key: value for key, value in os.environ.items() if key not in limits.API_ENV_KEYS
               and key not in limits.GEMINI_KEY_ENV}
        env = {**env, 'PATH': agent_path(), 'DUET_METRICS': '0',
               'DUET_TURN_SCHEDULER': 'gemini_app.scheduler:build', 'PYTHONPATH': str(BASE),
               'GEMINI_PROJECT_ID': project_id}
        return env

    def _prepare_workspace(self, project: dict) -> dict:
        project_id = project['id']
        repo = project['repo_path']
        branch = f'gemini/{project_id}'
        start = 'HEAD'
        if not repo and project['github_repo']:
            clone = PROJECTS / 'github' / project['github_repo'].replace('/', '__')
            github.ensure_clone(project['github_repo'], clone)
            repo, start = str(clone), 'origin/HEAD'
            visibility = github.visibility_of(project['github_repo'])
            self.store.update_project(project_id, github_branch=branch, github_visibility=visibility,
                                      github_auto=int(visibility == 'private'))
        elif not repo:
            repo = str(PROJECTS / f"{slugify(project['title'])}-{project_id}")
            gitops.create_repo(Path(repo))
        worktree = WORKTREES / project_id
        worktree.parent.mkdir(parents=True, exist_ok=True)
        base = gitops.add_worktree(repo, worktree, branch, start)
        self._setup(project_id, worktree)
        if (worktree / project_plan.PLAN_FILE).exists():
            # The repository carries the plan of an earlier project: the first turn plans this task anew.
            meta = self.store.meta(project_id)
            meta['replan'] = 'inherited'
            self.store.save_meta(project_id, meta)
        self.store.update_project(project_id, repo_path=repo, worktree=str(worktree), branch=branch,
                                  base_commit=base)
        return self.store.project(project_id)

    def _write_config(self, project: dict) -> Path:
        agents = [{'name': side, 'backend': BACKENDS[side], 'role': 'coder',
                   'model': project[f'{side}_model'], 'role_prompt': ROLE_PROMPT}
                  for side in self.sides(project)]
        config = {'cwd': project['worktree'], 'task': project['task'],
                  'max_turns': project['max_turns'], 'per_turn_timeout': project['turn_timeout'],
                  'on_turn_timeout': 'stop', 'runs_dir': str(RUNS / project['id']),
                  'sandbox': 'workspace-write', 'permission_mode': 'acceptEdits',
                  'metrics_enabled': False, 'recap': True, 'agents': agents}
        # Duet runs the sandboxed wrapper, which reads the real command from the store.
        config['verify_cmd'] = sandbox.verify_command()
        CONFIG.mkdir(parents=True, exist_ok=True)
        path = CONFIG / f"run-{project['id']}.json"
        path.write_text(json.dumps(config, ensure_ascii=False, indent=2))
        return path

    def _launch(self, project: dict) -> None:
        project_id = project['id']
        running = engine_pids(project_id)
        if running:
            # Never a second engine on one worktree: adopt the one that is already there.
            self.store.update_project(project_id, status='running', engine_pid=running[0],
                                      engine_start=process_start(running[0]))
            return
        problem = limits.check_auth([name for name in self.sides(project)
                                     if project[f'{name}_model'] not in (None, MODEL_OFF)])
        if problem:
            self._attention(project_id, problem)
            return
        try:
            resuming = bool(project['run_dir'])
            meta = self.store.meta(project_id)
            meta['launched_after'] = project['run_dir']
            self.store.save_meta(project_id, meta)
            if meta.pop('new_engine', False) or (resuming and self._saved_extra_args(project['run_dir'])):
                # A new model joined: a fresh run with every agent, and everyone gets the task again.
                meta.pop('seen', None)
                self.store.save_meta(project_id, meta)
                resuming = False
            if not project['worktree']:
                project = self._prepare_workspace(project)
            runs = RUNS / project_id
            runs.mkdir(parents=True, exist_ok=True)
            if resuming:
                command = ['--continue', project['run_dir'], '--runs-dir', str(runs), '--task',
                           'Wznowienie przez koordynatora. Sprawdź stan i kontynuuj.', '--turns',
                           str(project['max_turns']), '--timeout', str(project['turn_timeout']),
                           '--no-metrics']
                # Always the sandboxed wrapper: otherwise Duet would trust the raw command saved in
                # an older run's state.json and run it with the user's full rights.
                command += ['--verify-cmd', sandbox.verify_command()]
            else:
                command = ['--config', str(self._write_config(project))]
            log = open(runs / 'engine.log', 'ab')
            proc = subprocess.Popen([sys.executable, str(DUET), *command], cwd=str(BASE),
                                    env=self._engine_env(project_id), stdin=subprocess.DEVNULL,
                                    stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            log.close()
        except (gitops.GitError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
            self._attention(project_id, Msg('launch_failed', detail=exc))
            return
        self.procs[project_id] = proc
        self.store.update_project(project_id, status='running', engine_pid=proc.pid,
                                  engine_start=process_start(proc.pid), stop_requested=None,
                                  resume_after_stop=0)
        self.store.set_live(project_id, phase='starting', speaker=None, turn=None, mode=None,
                            until=None, reason=None, started_at=time.time())
        self.store.event(project_id, 'started', Msg('engine_started'))

    def _attention(self, project_id: str, detail: str) -> None:
        self.store.clear_live(project_id)
        self.store.update_project(project_id, status='attention', status_detail=detail)
        self.store.event(project_id, 'attention', detail)

    def latest_run(self, project_id: str) -> Optional[Path]:
        root = RUNS / project_id
        runs = sorted(path for path in root.glob('*') if (path / 'state.json').exists()) \
            if root.exists() else []
        return runs[-1] if runs else None

    def _saved_extra_args(self, run_dir: str) -> bool:
        """Runs from v0.6.5 to v0.6.14 saved Gemini's level as extra_args, which Duet will not
        resume: such a project starts a fresh run instead."""
        try:
            state = json.loads((Path(run_dir) / 'state.json').read_text())
        except (OSError, ValueError):
            return False
        return any(agent.get('extra_args') for agent in state.get('agents') or [])

    def _finish(self, project: dict) -> None:
        """The engine process ended: read why, and decide what happens next."""
        project_id = project['id']
        proc = self.procs.pop(project_id, None)
        if proc is not None:
            proc.wait()
        run = self.latest_run(project_id)
        before = self.store.meta(project_id).get('launched_after')
        if before and run and str(run) == before:
            # No new run: the engine failed before its first turn. The previous run's state says
            # nothing about this launch, so it must not decide that the project is done.
            log = RUNS / project_id / 'engine.log'
            tail = log.read_text(errors='replace').strip().splitlines()[-1][:300] if log.exists() else ''
            self._attention(project_id, Msg('launch_failed', detail=tail))
            return
        state: dict = {}
        if run:
            self.store.update_project(project_id, run_dir=str(run))
            try:
                state = json.loads((run / 'state.json').read_text())
            except (OSError, ValueError):
                state = {}
        reason = state.get('finished_reason')
        self.store.clear_live(project_id)
        latest = self.store.latest_version(project_id)
        if project['accepted_solo']:
            self.store.update_project(project_id, status='done', finished_at=time.time())
        elif project['resume_after_stop']:
            self.store.update_project(project_id, status='queued', stop_requested=None,
                                      resume_after_stop=0)
        elif reason == 'converged':
            self.store.update_project(project_id, status='done', finished_at=time.time())
            self.store.event(project_id, 'done', Msg('done_version', number=latest['number'])
                             if latest else Msg('done'))
        elif project['stop_requested']:
            self.store.update_project(project_id, status='stopped', stop_requested=None)
            self.store.event(project_id, 'stopped', Msg('stopped'))
        elif reason == 'force_stop':
            current = self.store.project(project_id)
            if current['status_detail']:
                self.store.clear_live(project_id)
                self.store.update_project(project_id, status='attention')
            else:
                self.store.update_project(project_id, status='stopped')
                self.store.event(project_id, 'stopped', Msg('stopped_outside'))
        elif reason == 'max_turns':
            self._attention(project_id, Msg('max_turns', turns=project['max_turns']))
        elif reason:
            self._attention(project_id, Msg('run_broken', reason=reason))
        else:
            self._attention(project_id, Msg('engine_lost'))

    def tick(self) -> None:
        with self.lock:
            active = self.store.projects(*RUNNING)
            for project in active:
                if not self._alive(project):
                    self._finish(project)
            self._sync_github()
            self._deliver()
            self._watch_efficiency()
            if any((self.store.live(project['id']) or {}).get('phase') not in ('waiting_partner', 'waiting_role')
                   for project in self.store.projects(*RUNNING)):
                return
            queued = self.store.projects('queued')
            if queued:
                self._launch(queued[0])

    def run(self) -> None:
        self.running = True
        while self.running:
            try:
                self.tick()
            except Exception as exc:  # the loop must outlive one bad project
                print(f'[gemini] tick: {exc!r}', file=sys.stderr, flush=True)
            time.sleep(TICK_S)

    # ---- Read models for the interface --------------------------------

    def work_state(self, project: dict, versions: list) -> dict:
        worktree = project.get('worktree')
        if not worktree or not Path(worktree).is_dir():
            return {}
        git = Git(worktree)
        commit = versions[0]['commit_sha'] if versions else project['base_commit']
        return {'head': git.head()[:7], 'commits_after_last_version': git.commits_since(commit),
                'uncommitted': len(git.dirty().splitlines())}

    def detail(self, project_id: str) -> dict:
        project = self._require(project_id)
        versions = self.store.versions(project_id)
        confirmed = next((v for v in versions if v['user_verdict'] == 'ok'), None)
        return {'project': project, 'sides': self.sides(project), 'all_sides': list(SIDES),
                'own_repo': owns_repo(project),
                'live': self.store.live(project_id),
                'events': self.store.events(project_id), 'notes': self.store.notes(project_id),
                'questions': self.store.questions(project_id), 'versions': versions,
                'recommended': recommended_version(versions), 'confirmed': confirmed,
                'work': self.work_state(project, versions),
                'github_default_name': slugify(project['title']),
                'final': self.store.last_event(project_id, 'final'),
                'monitor': monitor.assess(self.store, project),
                'plan': self.plan_view(project), 'run_here': self.run_here(project, versions),
                'assets': content.view(project['worktree']) if project.get('worktree') else [],
                'setup': self.setup_view(project),
                'asset_orders': self.store.meta(project_id).get('asset_orders', []),
                'paths': {'repo': project['repo_path'], 'work': project['worktree'],
                          'test': str(test_folder(project_id)) if project['test_version'] else None},
                'test_path': str(test_folder(project_id)) if project['test_version'] else None}

    def setup_view(self, project: dict) -> Optional[dict]:
        script = gitops.setup_script(project['worktree']) if project.get('worktree') else None
        if not script:
            return None
        return {**script, 'approved': self.store.meta(project['id']).get('setup_approved') == script['sha'],
                'sandbox': sandbox.backend()}

    def run_here(self, project: dict, versions: list) -> dict:
        """Where the ready project is and how to start it, for the panel."""
        own = owns_repo(project)
        others = []
        if project['repo_path'] and not own:
            others.append({'kind': 'repo', 'path': project['repo_path'], 'branch': project['branch']})
        if project['worktree']:
            others.append({'kind': 'work', 'path': project['worktree']})
        if own and project['test_version'] and test_folder(project['id']).is_dir():
            others.append({'kind': 'test', 'path': str(test_folder(project['id'])),
                           'version': project['test_version']})
        version = next((v for v in versions if v['number'] == project['run_version']), None)
        if not version:
            return {'path': None, 'version': None, 'steps': None, 'others': others}
        folder = project['repo_path'] if own else str(test_folder(project['id']))
        key = (project['id'], version['tag'], version['how_to_run'])
        if key not in self.run_steps_cache:
            self.run_steps_cache[key] = self._run_steps(project['repo_path'], version)
        steps = self.run_steps_cache[key]
        return {'path': folder, 'version': version['number'], 'own': own, 'others': others,
                'steps': f'cd {shlex.quote(folder)}' + (f'\n{steps}' if steps else '')}

    def _run_steps(self, repo: str, version: dict) -> Optional[str]:
        """From the agents' JAK URUCHOMIĆ, else the plan's run line, else the README."""
        if version['how_to_run']:
            return version['how_to_run']
        try:
            plan = json.loads(gitops.show(repo, version['tag'], project_plan.PLAN_FILE) or '{}')
            if isinstance(plan, dict) and str(plan.get('run') or '').strip():
                return str(plan['run']).strip()
            return gitops.readme_run_section(gitops.show(repo, version['tag'], 'README.md'))
        except (gitops.GitError, ValueError):
            return None

    def plan_view(self, project: dict) -> dict:
        if not project.get('worktree'):
            return {'exists': False}
        plan, problem = project_plan.load(project['worktree'])
        turns = monitor.turn_records(self.store, project['id'])
        return {'exists': plan is not None, 'problem': problem,
                'architecture': (plan or {}).get('architecture'), 'run': (plan or {}).get('run'),
                'rows': project_plan.rows(plan, turns), 'breakdown': project_plan.breakdown(plan, turns),
                'path': str(Path(project['worktree']) / project_plan.PLAN_FILE)}

    def transcript(self, project_id: str, limit: int = 400_000) -> str:
        root = RUNS / project_id
        parts = [path.read_text(errors='replace') for path in sorted(root.glob('*/transcript.md'))] \
            if root.exists() else []
        return '\n\n'.join(parts)[-limit:]
