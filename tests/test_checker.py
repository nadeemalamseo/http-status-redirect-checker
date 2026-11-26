import unittest
from unittest.mock import Mock, patch

import requests

from http_status_redirect_checker import (
    check_url, classify_status, normalize_url, validate_url,
)


def response(status, url, headers=None):
    item = Mock()
    item.status_code = status
    item.url = url
    item.headers = headers or {}
    return item


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.closed = False

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        value = self.responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return value

    def close(self):
        self.closed = True


class CheckerTests(unittest.TestCase):
    def test_success(self):
        session = FakeSession([response(200, "https://example.com/")])
        result = check_url("https://example.com/", session=session)
        self.assertEqual(result.final_status, 200)
        self.assertEqual(result.redirect_count, 0)
        self.assertEqual(result.findings, [])
        self.assertTrue(session.calls[0][1]["stream"])

    def test_single_redirect(self):
        first = response(301, "https://example.com/old", {"Location": "/new"})
        second = response(200, "https://example.com/new")
        result = check_url("https://example.com/old", session=FakeSession([first, second]))
        self.assertEqual(result.final_status, 200)
        self.assertEqual(result.final_url, "https://example.com/new")
        self.assertEqual(result.redirect_count, 1)
        first.close.assert_called_once()
        second.close.assert_called_once()

    def test_redirect_chain_is_reported(self):
        session = FakeSession([
            response(301, "https://example.com/a", {"Location": "/b"}),
            response(302, "https://example.com/b", {"Location": "/c"}),
            response(200, "https://example.com/c"),
        ])
        result = check_url("https://example.com/a", session=session)
        self.assertIn("redirect-chain", result.findings)
        self.assertEqual(result.redirect_count, 2)

    def test_relative_location_is_resolved(self):
        session = FakeSession([
            response(302, "https://example.com/a", {"Location": "../b"}),
            response(200, "https://example.com/b"),
        ])
        check_url("https://example.com/a", session=session)
        self.assertEqual(session.calls[1][0], "https://example.com/b")

    def test_loop(self):
        session = FakeSession([
            response(301, "https://example.com/a", {"Location": "/b"}),
            response(302, "https://example.com/b", {"Location": "/a"}),
        ])
        result = check_url("https://example.com/a", session=session)
        self.assertIn("redirect-loop", result.findings)
        self.assertIsNotNone(result.error)

    def test_missing_location(self):
        result = check_url("https://example.com/a",
                           session=FakeSession([response(301, "https://example.com/a")]))
        self.assertIn("redirect-missing-location", result.findings)

    def test_client_error(self):
        result = check_url("https://example.com/missing",
                           session=FakeSession([response(404, "https://example.com/missing")]))
        self.assertIn("client-error", result.findings)
        self.assertEqual(classify_status(404), "client-error")

    def test_server_error(self):
        result = check_url("https://example.com/error",
                           session=FakeSession([response(500, "https://example.com/error")]))
        self.assertIn("server-error", result.findings)
        self.assertEqual(classify_status(500), "server-error")

    def test_request_error(self):
        result = check_url("https://example.com/",
                           session=FakeSession([requests.Timeout("timed out")]))
        self.assertIsNone(result.final_status)
        self.assertIn("Request failed", result.error)

    def test_expected_destination_matches(self):
        session = FakeSession([
            response(301, "https://example.com/old", {"Location": "/new"}),
            response(200, "https://example.com/new"),
        ])
        result = check_url("https://example.com/old",
                           expected_destination="https://EXAMPLE.com:443/new#fragment",
                           session=session)
        self.assertTrue(result.destination_matches)
        self.assertNotIn("destination-mismatch", result.findings)

    def test_expected_destination_mismatch(self):
        result = check_url("https://example.com/current",
                           expected_destination="https://example.com/other",
                           session=FakeSession([response(200, "https://example.com/current")]))
        self.assertFalse(result.destination_matches)
        self.assertIn("destination-mismatch", result.findings)

    def test_invalid_scheme(self):
        with self.assertRaises(ValueError):
            check_url("ftp://example.com/file")

    def test_rejects_credentials_bad_port_and_whitespace(self):
        for url in ("https://user:pass@example.com/", "https://example.com:99999/",
                    "https://example.com/a b", " https://example.com/"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_url(url)

    def test_rejects_localhost_and_private_ip(self):
        for url in ("http://localhost/", "http://127.0.0.1/",
                    "http://192.168.1.2/", "http://[::1]/"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                check_url(url, session=FakeSession([]))

    def test_rejects_redirect_to_private_ip(self):
        result = check_url("https://example.com/start",
                           session=FakeSession([response(302, "https://example.com/start",
                                                         {"Location": "http://127.0.0.1/admin"})]))
        self.assertIn("redirect-invalid-location", result.findings)
        self.assertEqual(len(result.chain), 1)

    def test_rejects_redirect_with_credentials(self):
        result = check_url("https://example.com/start",
                           session=FakeSession([response(302, "https://example.com/start",
                                                         {"Location": "https://user:pass@example.net/"})]))
        self.assertIn("redirect-invalid-location", result.findings)

    def test_redirect_limit_zero(self):
        result = check_url("https://example.com/start", max_redirects=0,
                           session=FakeSession([response(301, "https://example.com/start",
                                                         {"Location": "/next"})]))
        self.assertIn("redirect-limit-exceeded", result.findings)
        self.assertEqual(result.redirect_count, 0)

    def test_rejects_invalid_runtime_limits(self):
        for kwargs in ({"timeout": 0}, {"timeout": -1}, {"max_redirects": -1},
                       {"user_agent": "  "}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                check_url("https://example.com/", **kwargs)

    def test_normalization_removes_fragment_and_default_port(self):
        self.assertEqual(normalize_url("HTTPS://Example.COM:443/a#frag"),
                         "https://example.com/a")

    def test_owned_session_is_closed(self):
        session = FakeSession([response(200, "https://example.com/")])
        with patch("http_status_redirect_checker.requests.Session", return_value=session):
            check_url("https://example.com/")
        self.assertTrue(session.closed)

    def test_injected_session_is_not_closed(self):
        session = FakeSession([response(200, "https://example.com/")])
        check_url("https://example.com/", session=session)
        self.assertFalse(session.closed)


if __name__ == "__main__":
    unittest.main()
