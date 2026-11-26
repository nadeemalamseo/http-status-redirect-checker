# HTTP Status & Redirect Checker

A Python command-line utility for inspecting HTTP response codes, redirect chains, loops, broken destinations, and expected final URLs.

## What it checks

- HTTP status codes and 2xx/3xx/4xx/5xx classifications
- Each observed redirect hop and its `Location` header
- Relative redirect destinations
- Redirect loops, missing or invalid `Location` headers, and redirect limits
- Expected final-destination comparison
- Response content type, request failures, and JSON output

## Requirements

- Python 3.10+
- `requests`

Install:

```bash
python -m pip install -r requirements.txt
```

## Usage

```bash
python http_status_redirect_checker.py https://example.com/
python http_status_redirect_checker.py https://example.com/old-page
python http_status_redirect_checker.py https://example.com/ https://example.com/about
python http_status_redirect_checker.py https://example.com/old-page --json
python http_status_redirect_checker.py https://example.com/old-page --timeout 15 --max-redirects 5
python http_status_redirect_checker.py https://example.com/old-page --expected-destination https://example.com/new-page
```

The checker does not automatically follow redirects. It requests each hop separately so it can record the chain and validate each destination before requesting it.

## Safety and resource behavior

- HTTP(S) URLs only; embedded credentials, whitespace, malformed ports, localhost names, and non-public IP literals are rejected.
- Redirects are followed manually and limited to 10 by default (`--max-redirects`).
- Each request uses a finite timeout (`--timeout`, default 10 seconds). Requests' timeout is not a strict total wall-clock deadline for the entire chain.
- Response bodies are not downloaded (`stream=True`); each response is closed after headers are inspected.
- Internally created sessions are closed; caller-supplied sessions remain caller-owned.

These checks are defense in depth, not a complete SSRF boundary. DNS names are not resolved and pinned to public IPs at connection time, so DNS rebinding and network-level routing risks remain. Do not expose this CLI as a public server-side URL-fetching service without network egress restrictions and connection-time destination validation. See [SECURITY.md](SECURITY.md).

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | No findings |
| 1 | Non-fatal findings were observed |
| 2 | Request/validation error, 4xx/5xx result, or redirect error |

Exit codes describe observable HTTP behavior. They do not indicate search-engine indexing, canonical selection, or rankings.

## Methodology and limitations

See [docs/methodology.md](docs/methodology.md). The checker does not crawl a domain, render JavaScript, authenticate to private pages, download page bodies, or simulate a search engine. A 3xx response is not automatically a problem; assess each redirect against the intended site architecture.

## Development

```bash
python -m unittest discover -s tests -v
```

GitHub Actions runs the tests on Python 3.10, 3.11, and 3.12.

## Project links

- [Live project landing page](https://nadeemalamseo.github.io/http-status-redirect-checker/)
- [Download latest main-branch source ZIP](https://github.com/nadeemalamseo/http-status-redirect-checker/archive/refs/heads/main.zip)
- [GitHub repository](https://github.com/nadeemalamseo/http-status-redirect-checker)
- [Historical v0.1.0 release](https://github.com/nadeemalamseo/http-status-redirect-checker/releases/tag/v0.1.0) — the tag may not include current main-branch changes.

## License

MIT. See [LICENSE](LICENSE).