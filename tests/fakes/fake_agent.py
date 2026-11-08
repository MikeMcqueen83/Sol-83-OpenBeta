"""Scripted stand-in for the `codex` and `claude` CLIs.

Speaks the real wire formats, including the exact limit message captured from
Codex on 2026-11-01, so tests exercise the whole engine without spending limits.
Reads $FAKE_DIR/scenario.json; each agent call consumes the next step of its script.
"""
import fcntl
import json
import os
import pathlib
import sys
import time
import uuid

FAKE_DIR = pathlib.Path(os.environ['FAKE_DIR'])
SCENARIO = FAKE_DIR / 'scenario.json'
LOCK = FAKE_DIR / 'lock'
SENTINEL = '<<<LGTM>>>'


def load():
    return json.loads(SCENARIO.read_text())


def save(scenario):
    temp = SCENARIO.with_suffix('.tmp')
    temp.write_text(json.dumps(scenario))
    temp.replace(SCENARIO)


def next_step(agent, prompt, resumed=False, argv=(), extra=None):
    with open(LOCK, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        scenario = load()
        script = scenario['script'].get(agent) or []
        step = script.pop(0) if script else {'reply': 'Nie mam już nic do zrobienia.'}
        with open(FAKE_DIR / 'calls.jsonl', 'a') as calls:
            calls.write(json.dumps({'agent': agent, 'prompt': prompt, 'resumed': resumed,
                                    'argv': list(argv)[:-1], 't': time.time(), **(extra or {})}) + '\n')
        if 'set_limits' in step:
            scenario['limits'].update(step['set_limits'])
        save(scenario)
    return step


def reply_text(step, agent):
    lines = [f"RECAP: {step.get('recap', agent + ' zrobił krok')}", 'FILES: x',
             f"STATUS: {step.get('status', 'reviewing')}",
             '', step.get('reply', 'Gotowe.')]
    if step.get('what_to_test'):
        lines += ['', 'CO TESTOWAĆ:', step['what_to_test']]
    if step.get('version_ok'):
        lines += ['', 'WERSJA OK']
    if step.get('lgtm'):
        lines += ['', 'LGTM rationale: sprawdziłem kod i uruchomiłem testy, cel zadania jest spełniony, '
                  'nie widzę otwartych problemów ani ryzyk blokujących odbiór.', SENTINEL]
    return '\n'.join(lines)


def perform(step):
    for name, content in (step.get('write') or {}).items():
        path = pathlib.Path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    time.sleep(step.get('sleep', 0))


def window(values, key):
    entry = values[key]
    return entry if isinstance(entry, dict) else {'used': entry, 'resets_at': time.time() + 3600}


def codex_app_server():
    for line in sys.stdin:
        message = json.loads(line)
        if message.get('method') == 'initialize':
            print(json.dumps({'id': message['id'], 'result': {}}), flush=True)
        elif message.get('method') == 'account/rateLimits/read':
            values = load()['limits']['codex']
            five, week = window(values, 'five_hour'), window(values, 'seven_day')
            result = {'ordinaryUsageAllowed': True, 'rateLimits': {
                'planType': 'plus',
                'primary': {'usedPercent': five['used'], 'windowDurationMins': 300,
                            'resetsAt': int(five['resets_at'])},
                'secondary': {'usedPercent': week['used'], 'windowDurationMins': 10080,
                              'resetsAt': int(week['resets_at'])}}}
            print(json.dumps({'id': message['id'], 'result': result}), flush=True)
        elif message.get('method') == 'model/list':
            models = [{'model': 'gpt-test', 'displayName': 'gpt-test', 'hidden': False,
                       'defaultReasoningEffort': 'medium',
                       'supportedReasoningEfforts': [{'reasoningEffort': 'low'},
                                                     {'reasoningEffort': 'ultra'}]},
                      {'model': 'ukryty', 'hidden': True, 'supportedReasoningEfforts': []}]
            print(json.dumps({'id': message['id'], 'result': {'data': models}}), flush=True)


def codex(args):
    if args[:2] == ['login', 'status']:
        print('Logged in using ChatGPT')
        return 0
    if args[:1] == ['app-server']:
        codex_app_server()
        return 0
    if args[:1] != ['exec']:
        print('codex-cli 0.0.0-fake')
        return 0
    if '--cd' in args:
        os.chdir(args[args.index('--cd') + 1])
    step = next_step('codex', args[-1], resumed='resume' in args, argv=args)
    print(f'session id: {uuid.uuid4()}', file=sys.stderr, flush=True)
    perform(step)
    if step.get('fail'):
        print(f"ERROR: {step['fail']}", file=sys.stderr)
        return 1
    print('tokens used\n12,345', file=sys.stderr)
    print(reply_text(step, 'codex'))
    return 0


def usage_report():
    values = load()['limits']['claude']
    five, week = window(values, 'five_hour'), window(values, 'seven_day')
    def stamp(moment):
        local = time.localtime(moment)
        return (time.strftime('%b %-d at %-I:%M', local) + time.strftime('%p', local).lower())

    zone = 'Europe/Warsaw'
    return (f"Current session: {five['used']:.0f}% used · resets {stamp(five['resets_at'])} ({zone})\n"
            f"Current week (all models): {week['used']:.0f}% used · resets "
            f"{stamp(week['resets_at'])} ({zone})\n")


def emit(payload):
    print(json.dumps(payload), flush=True)


def rate_event(overage=False, status='allowed', resets_at=None):
    """Claude's own event. A rejection carries the provider's reset time (`resetsAt`), as the real one did
    on 2026-11-08: status rejected, isUsingOverage true, resetsAt at the end of the 5 h window."""
    values = load()['limits']['claude']
    five, week = window(values, 'five_hour'), window(values, 'seven_day')
    return {'type': 'rate_limit_event', 'rate_limit_info': {
        'status': status, 'isUsingOverage': overage, **({'resetsAt': resets_at} if resets_at else {}),
        'unifiedWindows': {'five_hour': {'utilization': five['used'] / 100,
                                         'resetsAt': five['resets_at']},
                           'seven_day': {'utilization': week['used'] / 100,
                                         'resetsAt': week['resets_at']}}}}


def claude(args):
    if args[:2] == ['auth', 'status']:
        print(json.dumps({'loggedIn': True, 'authMethod': 'claude.ai'}))
        return 0
    if '-p' not in args:
        print('2.0.0 (fake)')
        return 0
    prompt = args[args.index('-p') + 1]
    session = str(uuid.uuid4())
    if prompt == '/usage':
        emit({'type': 'result', 'is_error': False, 'result': usage_report(), 'session_id': session})
        return 0
    step = next_step('claude', prompt, resumed='--resume' in args, argv=[*args, ''])
    perform(step)
    emit(rate_event(overage=bool(step.get('overage')), status=step.get('limit_status', 'allowed'),
                    resets_at=step.get('limit_resets_at')))
    if step.get('overage'):
        time.sleep(5)
    if step.get('fail'):
        emit({'type': 'result', 'is_error': True, 'result': step['fail'], 'session_id': session})
        return 1
    emit({'type': 'result', 'is_error': False, 'result': reply_text(step, 'claude'),
          'usage': {'input_tokens': 20, 'cache_creation_input_tokens': 1000, 'cache_read_input_tokens': 40000,
                    'output_tokens': 800},
          'session_id': session})
    return 0


def agy(args):
    """Antigravity CLI: `-p` with `--output-format json` gives `response` and `conversation_id`.
    A step with `tty_only` prints nothing unless stdout is a terminal, as some builds do."""
    if args[:1] == ['models']:
        print('Fetching available models...\ngemini-4-argon-high\tGemini 4 Argon (High)\n'
              'gemini-3.8-flash-low\tGemini 3.8 Flash (Low)')
        return 0
    if '-p' not in args:
        print('agy 0.0.0-fake')
        return 0
    upcoming = (load()['script'].get('gemini') or [{}])[0]
    if upcoming.get('tty_only') and not sys.stdout.isatty():
        return 0
    keys = ('GEMINI_API_KEY', 'GOOGLE_API_KEY')
    step = next_step('gemini', args[args.index('-p') + 1], resumed='--conversation' in args,
                     argv=[*args, ''], extra={'api_key': any(key in os.environ for key in keys),
                                              'cwd': os.getcwd()})
    perform(step)
    if step.get('fail'):
        print(step['fail'], file=sys.stderr)
        return 1
    print(json.dumps({'conversation_id': str(uuid.uuid4()), 'status': 'SUCCESS',
                      'response': reply_text(step, 'gemini'),
                      'usage': {'input_tokens': 1200, 'output_tokens': 300, 'thinking_tokens': 40,
                                'cache_read_tokens': 1000, 'total_tokens': 1500}}))
    return 0


if __name__ == '__main__':
    agent, *rest = sys.argv[1:]
    sys.exit({'codex': codex, 'agy': agy}.get(agent, claude)(rest))
