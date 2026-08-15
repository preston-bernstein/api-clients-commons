"""`python -m api_clients_commons.ebay <query-or-url>` CLI entrypoint.

Thin argparse wrapper around the package's public API (imported from
`api_clients_commons.ebay`, per Python's `-m package` semantics — not from
`api_clients_commons.ebay.client` directly).

Contract:
- One positional arg, `query_or_url`. If it looks like an http(s) URL
  containing "ebay.com", it's parsed as a raw eBay URL via `fetch_url()`.
  Otherwise it's treated as a plain search query and passed to `search()`.
- Optional `--timeout-s` float arg, forwarded verbatim. Defaults to the
  library's own default (10.0) so omitting it is a no-op.
- Success: prints the response text to stdout only (no logging, no progress
  text), exits 0.
- Failure (any exception): prints `f"{type(exc).__name__}: {exc}"` to
  stderr, nothing to stdout, exits 1. Also prints the installed
  `api_clients_commons` package version/identifier to stderr only —
  best-effort, diagnostic-only, so a stale checkout running old code is
  distinguishable from a real bug at a glance. Never appears on stdout, and
  never crashes the CLI even if the lookup itself fails.
"""

from __future__ import annotations

import argparse
import sys

from api_clients_commons.ebay import fetch_url, search


def _print_version_diagnostic() -> None:
    """Best-effort, stderr-only print of the running package's
    version/identifier.

    Tries `importlib.metadata.version("api-clients-commons")` first (the
    pip-installed case); falls back to printing this module's `__file__`
    path (the PYTHONPATH-only case, not pip installed) if that raises
    `PackageNotFoundError` or anything else. Swallows any failure from
    either path silently — this is a diagnostic nicety, never allowed to
    crash the CLI on the failure path it's meant to help debug.
    """
    try:
        try:
            import importlib.metadata

            version = importlib.metadata.version("api-clients-commons")
            print(f"api-clients-commons version: {version}", file=sys.stderr)
        except Exception:  # noqa: BLE001
            print(f"running from: {__file__}", file=sys.stderr)
    except Exception:  # noqa: BLE001, S110
        pass


def _looks_like_ebay_url(value: str) -> bool:
    return value.startswith(("http://", "https://")) and "ebay.com" in value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m api_clients_commons.ebay",
        description=(
            "Query eBay's official Browse API and print the JSON response "
            "to stdout. Pass a plain search query, or a raw eBay search/item URL."
        ),
    )
    parser.add_argument(
        "query_or_url",
        help="a plain search query, or an eBay search/item URL",
    )
    parser.add_argument(
        "--timeout-s",
        type=float,
        default=10.0,
        help="seconds to allow the OAuth token request and the Browse API "
        "request each (default: 10.0)",
    )
    args = parser.parse_args(argv)

    try:
        if _looks_like_ebay_url(args.query_or_url):
            _status, text = fetch_url(args.query_or_url, timeout_s=args.timeout_s)
        else:
            _status, text = search(args.query_or_url, timeout_s=args.timeout_s)
    except Exception as exc:  # noqa: BLE001
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        _print_version_diagnostic()
        return 1

    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
