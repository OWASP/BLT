"""Tests for /api/leaderboard: rows from blt-api (stubbed), escaping, empty and error states.

Run with: python3 -m unittest discover -s tests
"""
import asyncio
import types
import unittest
from unittest import mock

from test_routing import FakeAssets, FakeRequest, main

XSS_NAME = '<script>alert(1)</script>'


def stub_api(status=200, payload=None, error=None):
    """Replace call_blt_api with a stub; returns (patcher, calls)."""
    calls = []

    async def fake_call_blt_api(env, method, path, payload_=None, client_ip=None):
        calls.append((method, path))
        if error:
            raise error
        return status, payload

    return mock.patch.object(main, 'call_blt_api', new=fake_call_blt_api), calls


def leaderboard(status=200, payload=None, error=None):
    env = types.SimpleNamespace(ASSETS=FakeAssets())
    request = FakeRequest('https://next.owaspblt.org/api/leaderboard', headers={'Origin': 'https://next.owaspblt.org'})
    patcher, calls = stub_api(status, payload, error)
    with patcher:
        response = asyncio.run(main.handle_leaderboard(request, env))
    return response, calls


class LeaderboardRowsTests(unittest.TestCase):
    def test_rows_are_rendered_from_blt_api(self):
        payload = {
            'data': [
                {'username': 'alice_smith', 'total_score': 4200},
                {'username': 'bob', 'total_score': 3100},
            ],
            'pagination': {'total': 250},
        }
        response, calls = leaderboard(payload=payload)
        self.assertEqual(response.status, 200)
        self.assertEqual(calls, [('GET', f'/leaderboard?per_page={main.LEADERBOARD_PAGE_SIZE}')])
        self.assertEqual(response.body.count('class="leaderboard-row'), 2)
        self.assertIn('alice_smith', response.body)
        self.assertIn('4,200', response.body)
        self.assertIn('3,100', response.body)
        self.assertIn('data-total="250"', response.body)
        self.assertIn('fa-crown', response.body)  # rank 1 gets the crown, rank 2 its number
        self.assertIn('>2</div>', response.body)

    def test_username_is_escaped(self):
        payload = {'data': [{'username': XSS_NAME, 'total_score': 10}], 'pagination': {'total': 1}}
        response, _ = leaderboard(payload=payload)
        self.assertNotIn('<script>', response.body)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', response.body)

    def test_missing_total_falls_back_to_the_number_of_rows(self):
        payload = {'data': [{'username': 'a', 'total_score': 1}, {'username': 'b', 'total_score': 2}]}
        response, _ = leaderboard(payload=payload)
        self.assertIn('data-total="2"', response.body)


class LeaderboardBadDataTests(unittest.TestCase):
    def test_non_numeric_values_do_not_raise(self):
        payload = {
            'data': [
                {'username': 'a', 'total_score': 'lots'},
                {'username': 'b', 'total_score': None},
                {'username': 'c', 'total_score': float('nan')},
            ],
            'pagination': {'total': 'n/a'},
        }
        response, _ = leaderboard(payload=payload)
        self.assertEqual(response.status, 200)
        self.assertEqual(response.body.count('class="leaderboard-row'), 3)
        self.assertIn('data-total="3"', response.body)  # falls back to len(entries)
        self.assertNotIn('lots', response.body)

    def test_entries_that_are_not_objects_are_skipped(self):
        payload = {'data': ['oops', 7, {'username': 'real', 'total_score': 5}], 'pagination': {'total': 1}}
        response, _ = leaderboard(payload=payload)
        self.assertEqual(response.body.count('class="leaderboard-row'), 1)
        self.assertIn('real', response.body)

    def test_missing_username_is_shown_as_unknown(self):
        response, _ = leaderboard(payload={'data': [{'total_score': 5}], 'pagination': {'total': 1}})
        self.assertIn('unknown', response.body)


class LeaderboardEmptyAndErrorTests(unittest.TestCase):
    def test_empty_list_shows_the_empty_message(self):
        response, _ = leaderboard(payload={'data': [], 'pagination': {'total': 0}})
        self.assertEqual(response.status, 200)
        self.assertIn('No researchers on the leaderboard yet.', response.body)
        self.assertNotIn('leaderboard-row', response.body)

    def test_non_200_shows_the_unable_to_load_message(self):
        for status in (401, 429, 500):
            with self.subTest(status=status):
                response, _ = leaderboard(status=status, payload={'error': True, 'message': 'nope'})
                self.assertEqual(response.status, 200)
                self.assertIn('Unable to load the leaderboard', response.body)
                self.assertNotIn('leaderboard-row', response.body)

    def test_unparseable_answer_shows_the_unable_to_load_message(self):
        response, _ = leaderboard(status=200, payload=None)
        self.assertIn('Unable to load the leaderboard', response.body)

    def test_unreachable_api_shows_the_unable_to_load_message(self):
        response, _ = leaderboard(error=RuntimeError('boom'))
        self.assertIn('Unable to load the leaderboard', response.body)


if __name__ == '__main__':
    unittest.main()
