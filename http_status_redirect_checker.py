#!/usr/bin/env python3
"""Inspect HTTP status codes and redirect chains for supplied URLs."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests


REDIRECT_CODES = {301, 302, 303, 307, 308}
DEFAULT_TIMEOUT = 10.0
DEFAULT_MAX_REDIRECTS = 10
DEFAULT_USER_AGENT = "http-status-redirect-checker/1.0"


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


def validate_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL must use http:// or https:// and include a host")
    return url


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
    session: Optional[requests.Session] = None,
) -> CheckResult:
    current = validate_url(url)
    result = CheckResult(
        input_url=url,
        final_url=None,
        final_status=None,
        redirect_count=0,
    )
    visited: set[str] = set()
    client = session or requests.Session()

    for _ in range(max_redirects + 1):
        if current in visited:
            result.findings.append("redirect-loop")
            result.error = "Redirect loop detected."
            result.final_url = current
            return result
        visited.add(current)

        try:
            response = client.get(
                current,
                allow_redirects=False,
                timeout=timeout,
                headers={"User-Agent": user_agent},
            )
        except requests.RequestException as exc:
            result.error = f"Request failed: {exc}"
            result.final_url = current
            result.chain.append(Hop(url=current, status=None, error=str(exc)))
            return result

        content_type = response.headers.get("Content-Type")
        location = response.headers.get("Location")
        result.chain.append(
            Hop(
                url=current,
                status=response.status_code,
                location=location,
                content_type=content_type,
            )
        )

        if response.status_code not in REDIRECT_CODES:
            result.final_url = current
            result.final_status = response.status_code
            category = classify_status(response.status_code)
            if category == "client-error":
                result.findings.append("client-error")
            elif category == "server-error":
                result.findings.append("server-error")
            return result

        if not location:
            result.final_url = current
            result.final_status = response.status_code
            result.findings.append("redirect-missing-location")
            result.error = "Redirect response has no Location header."
            return result

        target = urljoin(current, location)
        parsed = urlparse(target)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            result.final_url = current
            result.final_status = response.status_code
            result.findings.append("redirect-invalid-location")
            result.error = "Redirect Location does not resolve to a valid HTTP(S) URL."
            return result

        result.redirect_count += 1
        current = target

    result.final_url = current
    result.findings.append("redirect-limit-exceeded")
    result.error = f"Redirect limit of {max_redirects} exceeded."
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect HTTP status codes and redirect chains."
    )
    parser.add_argument("urls", nargs="+", help="HTTP(S) URLs to check")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Output JSON")
    parser.add_argument(
        "--timeout", type=float, default=DEFAULT_TIMEOUT, help="Request timeout in seconds"
    )
    parser.add_argument(
        "--max-redirects",
        type=int,
        default=DEFAULT_MAX_REDIRECTS,
        help="Maximum redirect hops to inspect",
    )
    parser.add_argument(
        "--user-agent", default=DEFAULT_USER_AGENT, help="HTTP User-Agent header"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.timeout <= 0:
        print("Error: --timeout must be greater than 0.", file=sys.stderr)
        return 2
    if args.max_redirects < 0:
        print("Error: --max-redirects cannot be negative.", file=sys.stderr)
        return 2

    results: list[CheckResult] = []
    for url in args.urls:
        try:
            results.append(
                check_url(
                    url,
                    timeout=args.timeout,
                    max_redirects=args.max_redirects,
                    user_agent=args.user_agent,
                )
            )
        except ValueError as exc:
            results.append(
                CheckResult(
                    input_url=url,
                    final_url=None,
                    final_status=None,
                    redirect_count=0,
                    error=str(exc),
                    findings=["invalid-url"],
                )
            )

    if args.as_json:
        print(json.dumps([asdict(item) for item in results], indent=2))
    else:
        for item in results:
            print(f"URL: {item.input_url}")
            print(f"Final URL: {item.final_url or '-'}")
            print(f"Final status: {item.final_status or '-'}")
            print(f"Redirects: {item.redirect_count}")
            print(f"Classification: {classify_status(item.final_status)}")
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

    return 2 if any(item.error or "client-error" in item.findings or "server-error" in item.findings for item in results) else 1 if any(item.findings for item in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
