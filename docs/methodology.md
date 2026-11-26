# Methodology

This checker inspects observable HTTP response headers and redirect behavior for URLs supplied by the operator. It is a diagnostic aid, not a search-engine crawler or ranking simulator.

## Request and redirect process

1. Validate the supplied URL as HTTP(S), reject embedded credentials, whitespace, malformed ports, and missing hostnames.
2. Normalize scheme and hostname casing, remove fragments, and remove default ports for destination comparisons.
3. Reject localhost names and non-public IP address literals.
4. Send one request with automatic redirect following disabled and response streaming enabled.
5. Record the status, current URL, `Location` header, and content type; close the response without downloading its body.
6. Resolve relative `Location` values against the current URL, validate the resulting destination, and request the next hop.
7. Track visited normalized URLs to detect loops and stop at a non-redirect response, invalid/missing target, loop, request failure, or configured redirect limit.
8. Optionally compare the final normalized URL with an expected destination.

## Interpretation

A redirect chain is a sequence of multiple redirect responses. A 3xx response is not automatically an error: permanent and temporary redirects can be intentional. A 4xx or 5xx response is reported as a client/server error. Expected-destination comparison is a normalized URL comparison; it does not compare page content or establish that the destination is appropriate.

## Limits and security

- Default timeout: 10 seconds per request. The Requests timeout is not a strict end-to-end deadline for a multi-hop chain.
- Default maximum: 10 redirect hops per input URL.
- Response bodies are not downloaded or parsed.
- No domain-wide crawling, JavaScript rendering, or authentication is performed.
- Localhost names and non-public IP literals are rejected, including when encountered in a redirect.
- Hostnames are not resolved and pinned to public IPs at connection time. DNS rebinding and network routing risks remain; public server-side deployments require network-level egress controls and connection-time destination validation.

## Status classification

- 2xx: success
- 3xx: redirect
- 4xx: client error
- 5xx: server error
- Missing status: request error
- Other status values: other