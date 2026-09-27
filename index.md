# HTTP Status & Redirect Checker

A practical command-line checker for inspecting HTTP status codes, redirect chains, loops, broken URLs, and destination mismatches.

## Quick start

```bash
python http_status_redirect_checker.py https://example.com/
python http_status_redirect_checker.py https://example.com/old-page
python http_status_redirect_checker.py https://example.com/old-page --json
```

## What the results mean

The checker reports observable HTTP behavior from the supplied URL and the redirect targets it encounters. It does not determine search-engine indexing, canonical selection, or rankings.

## Related resource

For broader technical SEO implementation and site-level diagnostics, see [MarketLatch SEO Services](https://marketlatch.com/seo-services/).
