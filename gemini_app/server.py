"""Local web interface. Bound to loopback and guarded against cross-site requests,
because a POST here can start coding agents on this machine."""
from __future__ import annotations

import json
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import assets as content
from . import catalog, github, licenses, limits, model_catalog, monitor, observer, plan, providers, sandbox
from .messages import Msg, en
from .paths import WEB
from .scheduler import AGENT_LABEL
from .store import Store
from . import supervisor as supervisor_module
from .supervisor import Supervisor, preview, recommended_version, state_kind

MAX_BODY = 2_000_000
PROVIDER_THRESHOLDS = {f'{kind}_{name}' for name in limits.PROVIDERS
                       for kind in ('threshold', 'weekly')}


def overview(supervisor: Supervisor) -> dict:
    store = supervisor.store
    projects = []
    for project in store.projects():
        versions = store.versions(project['id'])
        live = store.live(project['id'])
        revision = store.plan_revision(project['id'])
        last = store.last_event(project['id'], 'turn_start')
        run = store._row("SELECT state, version, port FROM app_runs WHERE project_id=? ORDER BY id DESC LIMIT 1",
                         (project['id'],))
        recommended = recommended_version(versions)
        projects.append({**project, 'task': None, 'live': live, 'state_kind': state_kind(project, live),
                         'summary': (project['task'] or '').strip().splitlines()[0][:160] if project['task'] else '',
                         'recommended': recommended['number'] if recommended else None,
                         'progress': plan.progress(revision['data']) if revision else None,
                         'questions_open': store._row("SELECT COUNT(*) AS n FROM interactions WHERE project_id=? "
                                                      "AND state='open'", (project['id'],))['n'],
                         'last_config': (json.loads(last['data']).get('config') if last and last['data'] else None),
                         'run': run,
                         'monitor_level': monitor.assess(store, project, with_git=False)['level'],
                         'latest_version': versions[0]['number'] if versions else None,
                         'versions_count': len(versions)})
    return {'now': time.time(), 'limits': supervisor.limits_view(), 'projects': projects,
            'security': {'sandbox': sandbox.backend(), 'test_network': bool(store.setting('test_network', 0)),
                         'allow_unsandboxed': bool(store.setting('allow_unsandboxed', 0))},
            'agents': AGENT_LABEL, 'full_power': store.full_power(),
            'coordinator': observer.coordinator_view(store)}


class Handler(BaseHTTPRequestHandler):
    supervisor: Supervisor
    port: int

    def log_message(self, *args):
        pass

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(body)

    def _error(self, exc, status: int) -> None:
        self._json({'error': str(exc.args[0]) if exc.args else str(exc),
                    'error_en': en(exc.args[0]) if exc.args else None}, status)

    def _json(self, payload, status: int = 200) -> None:
        self._send(status, json.dumps(payload, ensure_ascii=False).encode(),
                   'application/json; charset=utf-8')

    def _trusted_host(self) -> bool:
        return self.headers.get('Host', '') in (f'127.0.0.1:{self.port}', f'localhost:{self.port}')

    def _trusted_post(self) -> bool:
        origin = self.headers.get('Origin')
        same_origin = origin in (None, f'http://127.0.0.1:{self.port}',
                                 f'http://localhost:{self.port}')
        kind = self.headers.get('Content-Type', '').split(';')[0].strip()
        return self._trusted_host() and same_origin and kind == 'application/json'

    def _body(self) -> dict:
        length = int(self.headers.get('Content-Length') or 0)
        if length > MAX_BODY:
            raise ValueError(Msg('err_too_big'))
        return json.loads(self.rfile.read(length) or b'{}')

    def do_GET(self):
        if not self._trusted_host():
            return self._error(ValueError(Msg('err_host')), 403)
        path = urllib.parse.urlparse(self.path).path
        try:
            if path == '/':
                return self._send(200, (WEB / 'index.html').read_bytes(),
                                  'text/html; charset=utf-8')
            if path == '/api/overview':
                return self._json(overview(self.supervisor))
            if path == '/api/catalog':
                store = self.supervisor.store
                return self._json({**catalog.read(), 'catalog': model_catalog.current(store),
                                   'policy': model_catalog.policy(),
                                   'catalog_due': model_catalog.due(store)})
            if path == '/api/licenses':
                return self._json({'standard': licenses.STANDARD, 'kinds': licenses.KINDS})
            if path == '/api/providers':
                return self._json(providers.status())
            if path == '/api/github/repos':
                return self._json({'repos': self.supervisor.github_repos()})
            if path == '/api/github':
                state = github.status()
                return self._json({**state, 'problem_en': en(state.get('problem'))})
            parts = path.strip('/').split('/')
            if len(parts) == 3 and parts[:2] == ['api', 'projects']:
                return self._json(self.supervisor.detail(parts[2]))
            if len(parts) == 5 and parts[:2] == ['api', 'projects'] and parts[3] == 'events':
                if not parts[4].isdigit():
                    return self._error(ValueError(Msg('err_bad_number')), 400)
                return self._json({'body': self.supervisor.store.event_body(parts[2], int(parts[4]))})
            if len(parts) == 4 and parts[:2] == ['api', 'projects'] and parts[3] == 'asset':
                query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                target = self.supervisor.asset_file(parts[2], (query.get('path') or [''])[0])
                return self._send(200, target.read_bytes(), content.IMAGE_TYPES[target.suffix.lower()])
            if len(parts) == 4 and parts[:2] == ['api', 'projects'] and parts[3] == 'transcript':
                return self._json({'text': self.supervisor.transcript(parts[2])})
            self._error(LookupError(Msg('err_not_found')), 404)
        except LookupError as exc:
            self._error(exc, 404)

    def do_POST(self):
        if not self._trusted_post():
            return self._error(ValueError(Msg('err_origin')), 403)
        path = urllib.parse.urlparse(self.path).path.strip('/').split('/')
        try:
            body = self._body()
            self._json(self._route(path, body))
        except supervisor_module.TopModelNeedsConfirmation as exc:
            self._json({'error': str(exc.args[0]), 'error_en': en(exc.args[0]), 'confirm_top': exc.model,
                        'side': exc.side}, 409)
        except (ValueError, TypeError, KeyError) as exc:
            self._error(exc if not isinstance(exc, KeyError) else ValueError(Msg('err_bad_number')), 400)
        except LookupError as exc:
            self._error(exc, 404)
        except github.SecretsFound as exc:
            self._json({'error': str(exc.args[0]), 'error_en': en(exc.args[0]), 'secrets': exc.findings,
                        'secrets_token': exc.token}, 409)
        except RuntimeError as exc:
            self._error(exc, 409)

    def _route(self, path: list, body: dict) -> dict:
        supervisor = self.supervisor
        if path == ['api', 'projects']:
            project = supervisor.create_project(
                task=str(body.get('task') or ''), title=str(body.get('title') or ''),
                repo_path=str(body.get('repo_path') or ''),
                verify_cmd=str(body.get('verify_cmd') or ''),
                max_turns=int(body.get('max_turns') or 30),
                claude_model=str(body.get('claude_model') or ''),
                codex_model=str(body.get('codex_model') or ''),
                claude_reasoning=str(body.get('claude_reasoning') or ''),
                codex_reasoning=str(body.get('codex_reasoning') or ''),
                github_repo=str(body.get('github_repo') or ''),
                claude_role=str(body.get('claude_role') or ''), codex_role=str(body.get('codex_role') or ''),
                role_fallback=str(body.get('role_fallback') or ''),
                gemini_model=str(body.get('gemini_model') or ''),
                gemini_reasoning=str(body.get('gemini_reasoning') or ''),
                gemini_role=str(body.get('gemini_role') or ''),
                selections={side: str(body.get(f'{side}_selection') or '') for side in ('claude', 'codex', 'gemini')},
                confirm_top=str(body.get('confirm_top') or ''),
                language='en' if body.get('lang') == 'en' else 'pl')
            return {'id': project['id']}
        if path == ['api', 'limits', 'refresh']:
            return {'limits': supervisor.limits_view(force=True)}
        if path == ['api', 'limits', 'retry']:
            return supervisor.retry_now(str(body.get('provider') or ''))
        if path == ['api', 'catalog', 'update']:
            threading.Thread(target=supervisor.update_catalog, daemon=True).start()
            return {'ok': True}
        if path == ['api', 'catalog', 'rollback']:
            return {'version': model_catalog.rollback(supervisor.store)}
        if path == ['api', 'catalog', 'settings']:
            if 'enabled' in body:
                supervisor.store.set_setting('catalog_update_enabled', 1 if body['enabled'] else 0)
            if body.get('defer_days'):
                supervisor.store.set_setting('catalog_deferred_until', time.time() + 86400 * float(body['defer_days']))
            return {'due': model_catalog.due(supervisor.store)}
        if path == ['api', 'providers', 'check']:
            # "Check connection": local CLI checks only, no model call and no limit used.
            return {'providers': providers.status(force=True), 'limits': supervisor.limits_view(force=True)}
        if path == ['api', 'settings']:
            for key, value in body.items():
                if key in PROVIDER_THRESHOLDS and 50 <= float(value) <= 100:
                    supervisor.store.set_setting(key, float(value))
            if 'full_power' in body:
                supervisor.store.set_setting('full_power', 1 if body['full_power'] else 0)
            for key in ('test_network', 'allow_unsandboxed'):
                if key in body:
                    supervisor.store.set_setting(key, 1 if body[key] else 0)
            if 'coordinator' in body:
                if body['coordinator'] not in observer.COORDINATORS:
                    raise ValueError(Msg('err_coordinator'))
                supervisor.store.set_setting('coordinator', body['coordinator'])
            return {'limits': supervisor.limits_view(), 'coordinator': observer.coordinator_view(supervisor.store)}
        if len(path) == 4 and path[:2] == ['api', 'projects']:
            return self._project_action(path[2], path[3], body)
        raise LookupError(Msg('err_not_found'))

    def _project_action(self, project_id: str, action: str, body: dict) -> dict:
        supervisor = self.supervisor
        if action == 'notes':
            added = supervisor.add_note(project_id, str(body.get('text') or ''), bool(body.get('urgent')),
                                        order=bool(body.get('order')), request_key=str(body.get('request_key') or ''))
            return {'ok': True, 'note': added['id'], 'duplicate': not added['created']}
        elif action == 'stop':
            supervisor.stop(project_id, immediate=bool(body.get('immediate')))
        elif action == 'resume':
            supervisor.resume(project_id, str(body.get('note') or ''))
        elif action == 'accept':
            supervisor.accept(project_id)
        elif action == 'models':
            supervisor.set_models(project_id, **{key: str(value) for key, value in body.items()})
        elif action == 'delete':
            supervisor.delete_project(project_id)
        elif action == 'verify':
            supervisor.set_verify(project_id, str(body.get('command') or ''))
        elif action == 'asset':
            supervisor.order_asset(project_id, str(body.get('type') or ''), str(body.get('prompt') or ''),
                                   str(body.get('path') or ''), str(body.get('size') or ''),
                                   str(body.get('style') or ''))
        elif action == 'answer':
            return supervisor.answer_interaction(
                project_id, int(body.get('interaction') or 0), str(body.get('value') or ''), str(body.get('comment') or ''),
                str(body.get('request_key') or ''), body.get('result') or None, str(body.get('evidence') or 'declaration'))
        elif action == 'interaction-state':
            supervisor.interaction_state(project_id, int(body.get('interaction') or 0), str(body.get('state') or ''))
        elif action == 'asset-decision':
            supervisor.decide_asset(project_id, str(body.get('id') or ''), str(body.get('decision') or ''),
                                    str(body.get('note') or ''))
        elif action == 'run':
            record = supervisor.run_app(project_id, int(body['number']))
            return {'run': record['id'], 'port': record['port'], 'duplicate': bool(record.get('duplicate'))}
        elif action == 'run-stop':
            supervisor.stop_app(project_id)
        elif action == 'run-plan':
            project = supervisor._require(project_id)
            version = supervisor.store.version(project_id, int(body['number']))
            if not version:
                raise ValueError(Msg('err_version'))
            return supervisor.run_plan(project, version, refresh=bool(body.get('refresh')))
        elif action == 'reveal':
            supervisor.reveal(project_id, str(body.get('path') or ''))
        elif action == 'git-context':
            supervisor.set_git_context(project_id, str(body.get('remote') or ''), str(body.get('base_branch') or ''),
                                       str(body.get('strategy') or 'local'), bool(body.get('allow_push')),
                                       bool(body.get('allow_pr')), str(body.get('subdir') or ''))
        elif action == 'git-deliver':
            return supervisor.git_deliver(project_id, str(body.get('request_key') or ''))
        elif action == 'license':
            return supervisor.set_license(project_id, str(body.get('kind') or ''), str(body.get('spdx') or ''),
                                          str(body.get('holder') or ''), str(body.get('custom') or ''),
                                          bool(body.get('overwrite')))
        elif action == 'language':
            supervisor.set_language(project_id, str(body.get('language') or ''))
        elif action == 'rename':
            supervisor.rename(project_id, str(body.get('title') or ''))
        elif action == 'scope':
            supervisor.decide_scope(project_id, str(body.get('blocker') or ''), str(body.get('note') or ''))
        elif action == 'withdraw':
            supervisor.withdraw_note(project_id, int(body.get('question') or 0))
        elif action == 'start-item':
            supervisor.start_item(project_id, str(body.get('item') or ''), str(body.get('request_key') or ''))
        elif action == 'message':
            text = str(body.get('text') or '').strip()
            if not text:
                raise ValueError(Msg('err_question'))
            interrupt = bool(body.get('interrupt'))
            if interrupt:
                supervisor.stop(project_id, immediate=True)
            supervisor._require(project_id)
            question_id = supervisor.store.add_question(project_id, text)
            supervisor.store.event(project_id, 'question', Msg('question_asked', preview=preview(text)),
                                   body=text)
            threading.Thread(target=observer.answer, daemon=True,
                             args=(supervisor, project_id, question_id, text,
                                   'en' if body.get('lang') == 'en' else 'pl', interrupt)).start()
        elif action == 'ask':
            question = str(body.get('question') or '').strip()
            if not question:
                raise ValueError(Msg('err_question'))
            supervisor._require(project_id)
            question_id = supervisor.store.add_question(project_id, question)
            supervisor.store.event(project_id, 'question', Msg('question_asked', preview=preview(question)),
                                   body=question)
            threading.Thread(target=observer.answer, daemon=True,
                             args=(supervisor, project_id, question_id, question,
                                   'en' if body.get('lang') == 'en' else 'pl')).start()
        elif action == 'verdict':
            supervisor.set_verdict(project_id, int(body['number']), bool(body.get('works')),
                                   str(body.get('comment') or ''), str(body.get('request_key') or ''))
        elif action == 'test-copy':
            return {'path': supervisor.prepare_test_copy(project_id, int(body['number']))}
        elif action == 'github':
            return supervisor.publish(project_id, int(body['number']), str(body.get('name') or ''),
                                      str(body.get('visibility') or 'private'),
                                      str(body.get('confirmed_secrets') or ''))
        elif action == 'github-auto':
            supervisor.set_github_auto(project_id, bool(body.get('enabled')))
        elif action == 'github-visibility':
            supervisor.change_visibility(project_id, str(body.get('visibility') or ''),
                                         str(body.get('confirmed_secrets') or ''))
        elif action == 'setup-approve':
            supervisor.approve_setup(project_id, str(body.get('sha') or ''))
        else:
            raise LookupError(Msg('err_not_found'))
        return {'ok': True}


def serve(port: int = 8765) -> None:
    supervisor = Supervisor(Store())
    handler = type('BoundHandler', (Handler,), {'supervisor': supervisor, 'port': port})
    server = ThreadingHTTPServer(('127.0.0.1', port), handler)
    threading.Thread(target=supervisor.run, daemon=True).start()
    print(f'Sol-83: http://127.0.0.1:{port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        supervisor.running = False
