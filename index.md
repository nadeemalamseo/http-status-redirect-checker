# HTTP Status & Redirect Checker

A practical command-line checker for inspecting HTTP status codes, redirect chains, loops, broken URLs, and destination mismatches.

## Get the tool

This is a **command-line tool**, not a browser-based checker.

### Download the repository

[Download the latest source as a ZIP](https://github.com/nadeemalamseo/http-status-redirect-checker/archive/refs/heads/main.zip)

Or open the [GitHub repository](https://github.com/nadeemalamseo/http-status-redirect-checker) to view and download individual files.

### Quick start

After downloading and extracting the repository:

```bash
python -m pip install -r requirements.txt
python http_status_redirect_checker.py https://example.com/
python http_status_redirect_checker.py https://example.com/old-page
python http_status_redirect_checker.py https://example.com/old-page --json
```

For an expected final destination:

```bash
python http_status_redirect_checker.py https://example.com/old-page --expected-destination https://example.com/new-page
```

## What it checks

- HTTP status codes
- Redirect chains
- Redirect loops
- Missing or invalid `Location` headers
- Final destination URLs
- Destination mismatches
- 4xx and 5xx responses
- Request errors
- JSON output for scripts and CI workflows

## What the results mean

The checker reports observable HTTP behavior from the supplied URL and the redirect targets it encounters. It does not determine search-engine indexing, canonical selection, or rankings.

## Related resource

For a broader view of the technical tools used for crawl diagnostics and redirect analysis, see [MarketLatch's digital marketing tools](https://marketlatch.com/tools/).

## Documentation

See the [README](https://github.com/nadeemalamseo/http-status-redirect-checker#readme) for complete usage, exit codes, methodology, limitations, responsible-use guidance, and development instructions.
