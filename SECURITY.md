# Security

## Safe use

Use this tool only to inspect URLs and systems you are authorized to test. It sends requests to the supplied URL and to redirect targets returned by that server.

The checker rejects embedded credentials, malformed ports, whitespace, localhost names, and non-public IP literals. It manually follows redirects with a configurable hop limit, applies a finite request timeout, streams responses without downloading bodies, closes response objects, and closes sessions it creates.

These protections are not a complete SSRF boundary. Hostnames are not resolved and pinned to public IPs at connection time, so DNS rebinding, resolver manipulation, and network routing risks remain. Do not expose the CLI directly as a public server-side URL-fetching service without strict egress filtering, connection-time IP validation, and isolation.

## Reporting a security issue

Please report suspected vulnerabilities privately through GitHub's private vulnerability reporting feature when available. Avoid posting credentials, private URLs, personal data, or confidential response details in public issues.