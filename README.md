# http-status-redirect-checker

A practical HTTP status and redirect checker for identifying redirect chains, loops, broken URLs, unexpected status codes, and destination mismatches.

## What it does

This Python command-line utility inspects the HTTP behavior of supplied URLs without automatically following redirects. It records each observed hop so you can review:

- HTTP status codes
- redirect chains (multiple redirect hops)
- redirect loops
- missing or invalid `Location` headers
- final destination URLs
- optional expected-destination comparison
- 2xx, 3xx, 4xx, and 5xx classifications
- response content types
- request errors and redirect limits

It supports multiple URLs and JSON output for scripts or CI workflows.

## Requirements

- Python 3.10+
- `requests`

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Usage

Check one URL:

```bash
python http_status_redirect_checker.py https://example.com/
```

Check a redirect:

```bash
python http_status_redirect_checker.py https://example.com/old-page
```

Check multiple URLs:

```bash
python http_status_redirect_checker.py https://example.com/ https://example.com/about
```

JSON output:

```bash
python http_status_redirect_checker.py https://example.com/old-page --json
```

Set a timeout or redirect limit:

```bash
python http_status_redirect_checker.py https://example.com/old-page --timeout 15 --max-redirects 5
```

Compare the observed final destination with an expected URL:

```bash
python http_status_redirect_checker.py https://example.com/old-page --expected-destination https://example.com/new-page
```

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | No findings |
| 1 | Warnings/findings were observed |
| 2 | Request/validation error, 4xx/5xx result, or redirect error |

These codes describe observable HTTP behavior. They are not search-engine indexing or ranking results.

## Methodology

See [docs/methodology.md](docs/methodology.md) for redirect handling, loop detection, safety limits, and interpretation guidance.

## Development

```bash
python -m unittest discover -s tests -v
```

GitHub Actions runs the unit tests across Python 3.10, 3.11, and 3.12.

## Limitations

This checker does not crawl an entire website, render JavaScript, authenticate to private pages, or simulate a search engine. A redirect can be intentional, and a 3xx response is not automatically a problem. The tool reports what the HTTP exchange reveals so a person can evaluate the implementation in context.

## Responsible use

Only check URLs you are authorized to inspect. Avoid excessive automated requests and respect the target site's operational constraints.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

See [SECURITY.md](SECURITY.md).

## Project links

- [Project landing page](https://nadeemalamseo.github.io/http-status-redirect-checker/)
- [v0.1.0 release](https://github.com/nadeemalamseo/http-status-redirect-checker/releases/tag/v0.1.0)
- [Download v0.1.0 ZIP](https://github.com/nadeemalamseo/http-status-redirect-checker/archive/refs/tags/v0.1.0.zip)

## License

This repository is licensed under the MIT License. See [LICENSE](LICENSE).

