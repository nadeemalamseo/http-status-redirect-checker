# Methodology

This checker evaluates observable HTTP responses and redirect behavior for URLs supplied by the user. It is a diagnostic aid, not a search-engine crawler or ranking simulator.

## Checks

1. Validate that each input is an HTTP(S) URL.
2. Request the URL without automatic redirect following so each hop can be inspected.
3. Record the HTTP status, response URL, content type, and redirect target when present.
4. Resolve relative `Location` headers against the current URL.
5. Track visited URLs to detect redirect loops.
6. Stop when a non-3xx response is reached, a redirect target is missing or invalid, a loop is detected, or the configured redirect limit is reached.
7. Report the full observed chain and classify common outcomes such as 2xx success, 3xx redirect, 4xx client error, and 5xx server error.

## Interpretation

A redirect chain is an HTTP behavior observed during the check. The tool does not determine how a particular search engine crawls, indexes, canonicalizes, or ranks a URL.

A 3xx response is not automatically an error. Whether a redirect is appropriate depends on the site's intended URL structure and implementation.

## Safety limits

- Only user-supplied URLs and their HTTP redirect targets are requested.
- A finite timeout is applied to every request.
- Redirects are bounded by a configurable maximum.
- The response body is not downloaded or parsed because the checker focuses on HTTP behavior.
- No domain-wide crawling is performed.
