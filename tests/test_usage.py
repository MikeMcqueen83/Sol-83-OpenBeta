"""Spec points 4 and 5: provider diagnosis and normalized token usage, on records taken from real runs."""
import os
import pathlib
import shutil
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMP = pathlib.Path(tempfile.mkdtemp(prefix='sol83-usage-'))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _env  # noqa: E402,F401  (one data folder for all test modules)

from gemini_app import providers, usage  # noqa: E402
from gemini_app.store import Store  # noqa: E402

# Verbatim from runs/4cd398528b/20261103-234021/turn-01-gemini.stderr.log (3 November 2026).
AGY_QUOTA = ('error: Individual quota reached. Please upgrade your subscription to increase your limits. '
             'Resets in 144h11m44s.\nAGY_ERROR: {"short_error":"RESOURCE_EXHAUSTED (code 429): Individual quota '
             'reached.","status":"RESOURCE_EXHAUSTED","error_code":429,"retryable":true}')


def tearDownModule():
    shutil.rmtree(TEMP, ignore_errors=True)


class CodexTotals(unittest.TestCase):
    def test_thousands_separator_on_the_next_line(self):
        # Real Codex 0.166 output: the number below the label, a space between thousands.
        self.assertEqual(usage.parse_codex_total('...\ntokens used\n192 753\n'), 192753)
        self.assertEqual(usage.parse_codex_total('tokens used: 1,234,567'), 1234567)
        self.assertEqual(usage.parse_codex_total('tokens used\n12 345'), 12345)
        self.assertIsNone(usage.parse_codex_total('no totals here'))


class Normalization(unittest.TestCase):
    def setUp(self):
        self.store = Store(TEMP / f'{self.id()}.db')

    def test_claude_categories_are_kept_apart(self):
        record = usage.normalize('claude', {'input_tokens': 20, 'cache_creation_input_tokens': 1000,
                                            'cache_read_input_tokens': 40000, 'output_tokens': 800})
        self.assertEqual((record['input'], record['cache_write'], record['cache_read'], record['output'],
                          record['total'], record['reasoning']), (20, 1000, 40000, 800, 41820, None))

    def test_missing_is_not_zero(self):
        self.assertEqual(usage.normalize('codex', 500)['input'], None)
        self.assertEqual(usage.normalize('gemini', {})['total'], None)

    def test_session_counters_become_per_turn_deltas(self):
        # Real cumulative Codex totals of one session (project 054750fcc5, 3 November 2026).
        totals = [105655, 192753, 274054]
        deltas = [usage.record(self.store, 'p', turn, 'codex', total, 'sess-1', 'gpt', 'gpt')['total']
                  for turn, total in enumerate(totals, 1)]
        self.assertEqual(deltas, [105655, 87098, 81301])
        # A new session starts its own counter; a repeated record of the same turn changes nothing.
        self.assertEqual(usage.record(self.store, 'p', 4, 'codex', 5000, 'sess-2', 'gpt', None)['total'], 5000)
        usage.record(self.store, 'p', 4, 'codex', 999999, 'sess-2', 'gpt', None)
        summary = usage.summary(self.store, 'p')
        self.assertEqual(sum(row['total'] for row in summary['rows']), 274054 + 5000)

    def test_gemini_cumulative_conversation(self):
        # Real Antigravity readings of one conversation (project 51a288b47f): input, cache, output grow.
        first = {'input_tokens': 284064, 'cached_tokens': 1743596, 'output_tokens': 40594}
        second = {'input_tokens': 365191, 'cached_tokens': 4683557, 'output_tokens': 59471}
        usage.record(self.store, 'g', 2, 'gemini', first, 'conv', 'default', None)
        turn = usage.record(self.store, 'g', 4, 'gemini', second, 'conv', 'default', None)
        self.assertEqual((turn['input'], turn['cache_read'], turn['output']), (81127, 2939961, 18877))

    def test_counter_reset_is_taken_as_is(self):
        usage.record(self.store, 'r', 1, 'codex', 400000, 's', 'gpt', None)
        turn = usage.record(self.store, 'r', 2, 'codex', 3000, 's', 'gpt', None)
        self.assertEqual((turn['total'], turn['note']), (3000, 'licznik zaczął się od nowa'))


class Windows(unittest.TestCase):
    def test_over_one_window_and_gaps(self):
        turns = [{'agent': 'claude', 'cost': {'five_hour': 120, 'seven_day': 12}},
                 {'agent': 'claude', 'cost': {'five_hour': 130, 'seven_day': 13}, 'overlap': ['other']},
                 {'agent': 'claude', 'cost': {}}, {'agent': 'gemini'}]
        result = usage.windows(turns)
        self.assertEqual((result['claude']['five_hour_percent'], result['claude']['window_equivalents'],
                          result['claude']['weekly_percent']), (250.0, 2.5, 25.0))
        self.assertEqual((result['claude']['unmeasured'], result['claude']['shared']), (1, 1))
        self.assertEqual(result['gemini']['unmeasured'], 1)


class Diagnosis(unittest.TestCase):
    def test_real_antigravity_quota_error(self):
        self.assertEqual(providers.diagnose(AGY_QUOTA), 'plan_limit')
        until = providers.reset_from_message(AGY_QUOTA, now=0)
        self.assertEqual(until, 144 * 3600 + 11 * 60 + 44)

    def test_classes(self):
        cases = {'Error: Not logged in. Please run /login': 'not_logged_in',
                 'OAuth token has expired, please log in again': 'session_expired',
                 'model gemini-9 is not available for this account': 'no_model_access',
                 '429 Too Many Requests: rate limit, slow down': 'rate_limit',
                 'stream disconnected before completion: ECONNRESET': 'network',
                 '503 Service Unavailable': 'provider_outage',
                 'something odd happened': 'unknown'}
        for text, expected in cases.items():
            self.assertEqual(providers.diagnose(text), expected, text)

    def test_no_reset_stated(self):
        self.assertIsNone(providers.reset_from_message('quota exceeded'))


if __name__ == '__main__':
    unittest.main()
