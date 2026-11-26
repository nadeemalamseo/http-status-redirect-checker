#!/usr/bin/env python3
"""Inspect HTTP status codes and redirect chains for supplied URLs."""
from __future__ import annotations

import argparse
import ipaddress
import json
import sys
from dataclasses import asdict, dataclass, field
from typing import Optional
from urllib.parse import urljoin, urlparse, urlunparse

import requests

REDIRECT_CODES = {301, 302, 303, 307, 308}
DEFAULT_TIMEOUT = 10.0
DEFAULT_MAX_REDIRECTS = 10
DEFAULT_USER_AGENT = "http-status-redirect-checker/1.1"


@dataclass
class Hop:
    url: str
    status: Optional[int]
    location: Optional[str] = None
    content_type: Optional[str] = None
    error: Optional[str] = None


@dataclass
class CheckResult:
    input_url: str
    final_url: Optional[str]
    final_status: Optional[int]
    redirect_count: int
    chain: list[Hop] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)
    error: Optional[str] = None
    expected_destination: Optional[str] = None
    destination_matches: Optional[bool] = None


def validate_url(url: str) -> str:
    if not isinstance(url, str) or not url or url != url.strip():
        raise ValueError("URL must be a non-empty string without surrounding whitespace.")
    if any(ch.isspace() or ord(ch) < 32 for ch in url):
        raise ValueError("URL must not contain whitespace or control characters.")
    parsed = urlparse(url)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL must use http:// or https:// and include a host.")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("URLs containing embedded credentials are not supported.")
    try:
        parsed.port
    except ValueError as exc:
        raise ValueError("URL contains an invalid port.") from exc
    if not parsed.hostname:
        raise ValueError("URL must include a valid hostname.")
    return url


def normalize_url(url: str) -> str:
    parsed = urlparse(validate_url(url))
    host = parsed.hostname.lower()
    if ":" in host:
        host = f"[{host}]"
    port = parsed.port
    is_default = (parsed.scheme.lower() == "http" and port == 80) or (
        parsed.scheme.lower() == "https" and port == 443
    )
    netloc = host if port is None or is_default else f"{host}:{port}"
    return urlunparse((
        parsed.scheme.lower(), netloc, parsed.path or "/", parsed.params,
        parsed.query, ""
    ))


def _validate_destination(url: str) -> str:
    """Reject obvious local destinations; DNS names need network-level egress controls."""
    normalized = normalize_url(url)
    host = urlparse(normalized).hostname or ""
    if host.lower() == "localhost" or host.lower().endswith(".localhost"):
        raise ValueError("Requests to localhost are not allowed.")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return normalized
    if not address.is_global:
        raise ValueError("Requests to non-public IP addresses are not allowed.")
    return normalized


def classify_status(status: Optional[int]) -> str:
    if status is None:
        return "request-error"
    if 200 <= status < 300:
        return "success"
    if 300 <= status < 400:
        return "redirect"
    if 400 <= status < 500:
        return "client-error"
    if 500 <= status < 600:
        return "server-error"
    return "other"


def check_url(
    url: str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    max_redirects: int = DEFAULT_MAX_REDIRECTS,
    user_agent: str = DEFAULT_USER_AGENT,
    expected_destination: Optional[str] = None,
    session: Optional[requests.Session] = None,
) -> CheckResult:
    if timeout <= 0:
        raise ValueError("timeout must be greater than 0.")
    if max_redirects < 0:
        raise ValueError("max_redirects cannot be negative.")
    if not isinstance(user_agent, str) or not user_agent.strip():
        raise ValueError("user_agent must be a non-empty string.")

    current = _validate_destination(url)
    expected = _validate_destination(expected_destination) if expected_destination else None
    result = CheckResult(
        input_url=url, final_url=None, final_status=None, redirect_count=0,
        expected_destination=expected,
    )
    visited: set[str] = set()
    owns_session = session is None
    client = session if session is not None else requests.Session()

    try:
        while True:
            if current in visited:
                result.findings.append("redirect-loop")
                result.error = "Redirect loop detected."
                result.final_url = current
                break
            visited.add(current)

            response = None
            try:
                response = client.get(
                    current,
                    allow_redirects=False,
                    timeout=timeout,
                    headers={"User-Agent": user_agent},
                    stream=True,
                )
                status = response.status_code
                location = response.headers.get("Location")
                content_type = response.headers.get("Content-Type")
                result.chain.append(Hop(
                    url=current, status=status, location=location,
                    content_type=content_type,
                ))
            except requests.RequestException as exc:
                result.error = f"Request failed: {exc}"
                result.final_url = current
                result.chain.append(Hop(url=current, status=None, error=str(exc)))
                break
            finally:
                if response is not None:
                    response.close()

            if status not in REDIRECT_CODES:
                result.final_url = current
                result.final_status = status
                category = classify_status(status)
                if category == "client-error":
                    result.findings.append("client-error")
                elif category == "server-error":
                    result.findings.append("server-error")
                break

            if not location:
                result.final_url = current
                result.final_status = status
                result.findings.append("redirect-missing-location")
                result.error = "Redirect response has no Location header."
                break

            try:
                target = _validate_destination(urljoin(current, location))
            except ValueError:
                result.final_url = current
                result.final_status = status
                result.findings.append("redirect-invalid-location")
                result.error = "Redirect Location is not an allowed HTTP(S) destination."
                break

            if result.redirect_count >= max_redirects:
                result.final_url = current
                result.final_status = status
                result.findings.append("redirect-limit-exceeded")
                result.error = f"Redirect limit of {max_redirects} exceeded."
                break

            result.redirect_count += 1
            current = target

        if result.redirect_count > 1 and "redirect-loop" not in result.findings:
            result.findings.append("redirect-chain")

        if expected and result.final_url:
            result.destination_matches = normalize_url(result.final_url) == expected
            if not result.destination_matches:
                result.findings.append("destination-mismatch")
        return result
    finally:
        if owns_session:
            client.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect HTTP status codes and redirect chains."
    )
    parser.add_argument("urls", nargs="+", help="HTTP(S) URLs to check")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Output JSON")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT,
                        help="Request timeout in seconds")
    parser.add_argument("--max-redirects", type=int, default=DEFAULT_MAX_REDIRECTS,
                        help="Maximum redirect hops to inspect")
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT,
                        help="HTTP User-Agent header")
    parser.add_argument("--expected-destination",
                        help="Expected final HTTP(S) URL for destination comparison")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.timeout <= 0:
        print("Error: --timeout must be greater than 0.", file=sys.stderr)
        return 2
    if args.max_redirects < 0:
        print("Error: --max-redirects cannot be negative.", file=sys.stderr)
        return 2
    if not args.user_agent.strip():
        print("Error: --user-agent cannot be empty.", file=sys.stderr)
        return 2
    if args.expected_destination:
        try:
            _validate_destination(args.expected_destination)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2

    results: list[CheckResult] = []
    for url in args.urls:
        try:
            results.append(check_url(
                url, timeout=args.timeout, max_redirects=args.max_redirects,
                user_agent=args.user_agent,
                expected_destination=args.expected_destination,
            ))
        except ValueError as exc:
            results.append(CheckResult(
                input_url=url, final_url=None, final_status=None,
                redirect_count=0, error=str(exc), findings=["invalid-url"],
            ))

    if args.as_json:
        print(json.dumps([asdict(item) for item in results], indent=2))
    else:
        for item in results:
            print(f"URL: {item.input_url}")
            print(f"Final URL: {item.final_url or '-'}")
            print(f"Final status: {item.final_status if item.final_status is not None else '-'}")
            print(f"Redirects: {item.redirect_count}")
            print(f"Classification: {classify_status(item.final_status)}")
            if item.expected_destination:
                print(f"Expected destination: {item.expected_destination}")
                print(f"Destination matches: {item.destination_matches}")
            if item.findings:
                print("Findings: " + ", ".join(item.findings))
            if item.error:
                print("Error: " + item.error)
            print("Chain:")
            for hop in item.chain:
                location = f" -> {hop.location}" if hop.location else ""
                status = str(hop.status) if hop.status is not None else "ERROR"
                print(f"  {status} {hop.url}{location}")
            print()

    return 2 if any(
        item.error or "client-error" in item.findings
        or "server-error" in item.findings
        or "destination-mismatch" in item.findings
        for item in results
    ) else 1 if any(item.findings for item in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
