import unittest
from unittest.mock import Mock

import requests

from http_status_redirect_checker import check_url, classify_status


def response(status, url, headers=None):
    item = Mock()
    item.status_code = status
    item.url = url
    item.headers = headers or {}
    return item


class FakeSession:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        value = self.responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


class CheckerTests(unittest.TestCase):
    def test_success(self):
        session = FakeSession([response(200, "https://example.com/")])
        result = check_url("https://example.com/", session=session)
        self.assertEqual(result.final_status, 200)
        self.assertEqual(result.redirect_count, 0)
        self.assertEqual(result.findings, [])

    def test_single_redirect(self):
        session = FakeSession(
            [
                response(301, "https://example.com/old", {"Location": "/new"}),
                response(200, "https://example.com/new"),
            ]
        )
        result = check_url("https://example.com/old", session=session)
        self.assertEqual(result.final_status, 200)
        self.assertEqual(result.final_url, "https://example.com/new")
        self.assertEqual(result.redirect_count, 1)

    def test_redirect_chain_is_reported(self):
        session = FakeSession(
            [
                response(301, "https://example.com/a", {"Location": "/b"}),
                response(302, "https://example.com/b", {"Location": "/c"}),
                response(200, "https://example.com/c"),
            ]
        )
        result = check_url("https://example.com/a", session=session)
        self.assertIn("redirect-chain", result.findings)
        self.assertEqual(result.redirect_count, 2)

    def test_relative_location_is_resolved(self):
        session = FakeSession(
            [
                response(302, "https://example.com/a", {"Location": "../b"}),
                response(200, "https://example.com/b"),
            ]
        )
        result = check_url("https://example.com/a", session=session)
        self.assertEqual(session.calls[1][0], "https://example.com/b")

    def test_loop(self):
        session = FakeSession(
            [
                response(301, "https://example.com/a", {"Location": "/b"}),
                response(302, "https://example.com/b", {"Location": "/a"}),
            ]
        )
        result = check_url("https://example.com/a", session=session)
        self.assertIn("redirect-loop", result.findings)
        self.assertIsNotNone(result.error)

    def test_missing_location(self):
        session = FakeSession([response(301, "https://example.com/a")])
        result = check_url("https://example.com/a", session=session)
        self.assertIn("redirect-missing-location", result.findings)

    def test_client_error(self):
        session = FakeSession([response(404, "https://example.com/missing")])
        result = check_url("https://example.com/missing", session=session)
        self.assertIn("client-error", result.findings)
        self.assertEqual(classify_status(404), "client-error")

    def test_server_error(self):
        session = FakeSession([response(500, "https://example.com/error")])
        result = check_url("https://example.com/error", session=session)
        self.assertIn("server-error", result.findings)
        self.assertEqual(classify_status(500), "server-error")

    def test_request_error(self):
        session = FakeSession([requests.Timeout("timed out")])
        result = check_url("https://example.com/", session=session)
        self.assertEqual(result.final_status, None)
        self.assertIn("Request failed", result.error)

    def test_expected_destination_matches(self):
        session = FakeSession(
            [
                response(301, "https://example.com/old", {"Location": "/new"}),
                response(200, "https://example.com/new"),
            ]
        )
        result = check_url(
            "https://example.com/old",
            expected_destination="https://example.com/new#fragment",
            session=session,
        )
        self.assertTrue(result.destination_matches)
        self.assertNotIn("destination-mismatch", result.findings)

    def test_expected_destination_mismatch(self):
        session = FakeSession([response(200, "https://example.com/current")])
        result = check_url(
            "https://example.com/current",
            expected_destination="https://example.com/other",
            session=session,
        )
        self.assertFalse(result.destination_matches)
        self.assertIn("destination-mismatch", result.findings)

    def test_invalid_url(self):
        with self.assertRaises(ValueError):
            check_url("ftp://example.com/file")


if __name__ == "__main__":
    unittest.main()
