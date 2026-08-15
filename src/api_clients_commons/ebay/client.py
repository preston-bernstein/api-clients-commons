"""eBay Browse API client.

Calls eBay's official, authenticated Browse API directly. This is NOT a
scraper and does not auto-detect eBay URLs from some other tool's input —
callers explicitly choose `search()` or `get_item()` (or, for a human pasting
a raw eBay URL at a CLI, `fetch_url()`).
"""

from __future__ import annotations

import os
import time
from urllib.parse import parse_qs, urlsplit

import requests

from api_clients_commons.ebay.errors import EbayApiRequestFailed, EbayCredentialsMissing

_TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
_SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
_ITEM_BY_LEGACY_ID_URL = "https://api.ebay.com/buy/browse/v1/item_summary/item_by_legacy_id"

# Single atomic cache object: (token, monotonic expiry) or None. Always
# reassigned in one statement to avoid interleaved-read races between a
# token and its expiry living in two separate module globals.
_token_cache: tuple[str, float] | None = None


def _extract_search_term(url: str) -> str | None:
    """Extract the search term from the `_nkw` query parameter.

    Args:
        url: An eBay URL, e.g. a search results page.

    Returns:
        The search term string if `_nkw` is present, else None.

    Examples:
        >>> _extract_search_term("https://www.ebay.com/sch/i.html?_nkw=corduroy+jacket")
        'corduroy jacket'
    """
    query = parse_qs(urlsplit(url).query)
    values = query.get("_nkw")
    if not values:
        return None
    return values[0]


def _extract_item_id(url: str) -> str | None:
    """Extract the item ID from the last path segment after `/itm/`.

    Handles both `ebay.com/itm/<id>` and `ebay.com/itm/<slug>/<id>` shapes.

    Args:
        url: An eBay URL, e.g. an item listing page.

    Returns:
        The numeric item ID string if `/itm/` is present and the trailing
        segment is non-empty and numeric, else None.

    Examples:
        >>> _extract_item_id("https://www.ebay.com/itm/123456789")
        '123456789'
        >>> _extract_item_id("https://www.ebay.com/itm/some-title-slug/123456789")
        '123456789'
    """
    path = urlsplit(url).path
    marker = "/itm/"
    index = path.find(marker)
    if index == -1:
        return None
    trailing = path[index + len(marker) :]
    segments = [segment for segment in trailing.split("/") if segment]
    if not segments:
        return None
    item_id = segments[-1]
    if not item_id.isdigit():
        return None
    return item_id


def _require_credentials() -> tuple[str, str]:
    """Read and validate eBay OAuth client credentials from the environment.

    Reads `EBAY_CLIENT_ID` and `EBAY_CLIENT_SECRET` fresh from `os.environ`
    on every call (never cached at import time). A value is treated as blank
    if it is empty or contains only whitespace after stripping.

    Returns:
        A `(client_id, client_secret)` tuple, both stripped.

    Raises:
        EbayCredentialsMissing: If either or both variables are unset or
            blank. The message names the exact missing variable name(s) but
            never includes either variable's actual value.
    """
    client_id = os.environ.get("EBAY_CLIENT_ID", "").strip()
    client_secret = os.environ.get("EBAY_CLIENT_SECRET", "").strip()
    missing = []
    if not client_id:
        missing.append("EBAY_CLIENT_ID")
    if not client_secret:
        missing.append("EBAY_CLIENT_SECRET")
    if missing:
        raise EbayCredentialsMissing(f"{' and '.join(missing)} is unset or blank"
                                      if len(missing) == 1
                                      else f"{' and '.join(missing)} are unset or blank")
    return client_id, client_secret


def _get_token(timeout_s: float) -> str:
    """Fetch a cached or fresh eBay OAuth2 client-credentials bearer token.

    Returns the cached token if it is still valid (with a 60-second
    early-refresh margin), otherwise requests a new one and caches it.
    Expiry is tracked with `time.monotonic()`, not wall-clock time.

    Args:
        timeout_s: Timeout in seconds for the token request.

    Returns:
        The bearer token string.

    Raises:
        EbayCredentialsMissing: If credentials are unset or blank.
        EbayApiRequestFailed: If the token request fails, either at the
            HTTP layer (connection error/timeout) or via a non-2xx response.
    """
    global _token_cache

    if _token_cache is not None and time.monotonic() < _token_cache[1]:
        return _token_cache[0]

    client_id, client_secret = _require_credentials()

    try:
        response = requests.post(
            _TOKEN_URL,
            timeout=timeout_s,
            auth=(client_id, client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "client_credentials",
                "scope": "https://api.ebay.com/oauth/api_scope",
            },
        )
    except requests.exceptions.RequestException as exc:
        raise EbayApiRequestFailed(
            "eBay OAuth token request failed", status=None, body=str(exc)
        ) from exc

    if not response.ok:
        raise EbayApiRequestFailed(
            f"eBay OAuth token request failed with status {response.status_code}",
            status=response.status_code,
            body=response.text,
        )

    payload = response.json()
    access_token = payload["access_token"]
    expires_in = payload["expires_in"]

    _token_cache = (access_token, time.monotonic() + expires_in - 60)

    return access_token


def _invalidate_token_cache() -> None:
    """Clear the module-level token cache.

    Called from two places: the 401-retry path in `_call_browse_api()` (a
    token eBay rejected before its stated expiry must not be reused on the
    retry) and `_reset_token_cache_for_tests()` below (test isolation). Kept
    as the single real implementation so the 401-retry path — production
    behavior — never depends on a function whose name/docstring promise
    "test isolation only", which would make it look like safe-to-delete test
    scaffolding to a future refactor.
    """
    global _token_cache
    _token_cache = None


def _reset_token_cache_for_tests() -> None:
    """Clear the module-level token cache. For test isolation only.

    Thin alias for `_invalidate_token_cache()`, kept under this name because
    `tests/test_ebay.py` refers to it this way.
    """
    _invalidate_token_cache()


def _call_browse_api(endpoint: str, params: dict, timeout_s: float) -> tuple[int, str]:
    """Call a Browse API endpoint, retrying once on a 401 with a fresh token.

    Shared by `search()` and `get_item()` — both are a single authenticated
    GET against a Browse API endpoint that only differs by URL and params.

    Args:
        endpoint: The full Browse API endpoint URL.
        params: Query parameters for the request.
        timeout_s: Timeout in seconds for both the OAuth token request (if
            needed) and the Browse API request.

    Returns:
        A `(status_code, response_text)` tuple from the successful response.

    Raises:
        EbayCredentialsMissing: If credentials are unset or blank.
        EbayApiRequestFailed: If the request fails, either at the HTTP
            layer, via a non-2xx response, or via a second consecutive 401
            after the one retry.
    """
    token = _get_token(timeout_s)

    def _call(bearer_token: str) -> requests.Response:
        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
        }
        try:
            return requests.get(
                endpoint, params=params, headers=headers, timeout=timeout_s
            )
        except requests.exceptions.RequestException as exc:
            raise EbayApiRequestFailed(
                "eBay Browse API request failed", status=None, body=str(exc)
            ) from exc

    response = _call(token)

    if response.status_code == 401:
        _invalidate_token_cache()
        token = _get_token(timeout_s)
        response = _call(token)

    if response.ok:
        return response.status_code, response.text

    raise EbayApiRequestFailed(
        f"eBay Browse API request failed with status {response.status_code}",
        status=response.status_code,
        body=response.text,
    )


def search(query: str, *, timeout_s: float = 10.0) -> tuple[int, str]:
    """Search eBay listings via the Browse API's `item_summary/search` endpoint.

    Args:
        query: The search term, e.g. "corduroy jacket".
        timeout_s: Timeout in seconds for both the OAuth token request and
            the Browse API request.

    Returns:
        A `(status_code, response_text)` tuple — `response_text` is the raw
        JSON body from the Browse API.

    Raises:
        EbayCredentialsMissing: If EBAY_CLIENT_ID/EBAY_CLIENT_SECRET are
            unset or blank.
        EbayApiRequestFailed: If the request fails at the HTTP layer, via a
            non-2xx response, or via a second consecutive 401 after one retry.
    """
    return _call_browse_api(_SEARCH_URL, {"q": query}, timeout_s)


def get_item(item_id: str, *, timeout_s: float = 10.0) -> tuple[int, str]:
    """Look up one eBay listing by its legacy numeric item ID.

    Args:
        item_id: The numeric item ID, e.g. "123456789012" (the ID that
            appears in a browser item URL, not the Browse API's composite
            `v1|<id>|0` item ID format).
        timeout_s: Timeout in seconds for both the OAuth token request and
            the Browse API request.

    Returns:
        A `(status_code, response_text)` tuple — `response_text` is the raw
        JSON body from the Browse API.

    Raises:
        EbayCredentialsMissing: If EBAY_CLIENT_ID/EBAY_CLIENT_SECRET are
            unset or blank.
        EbayApiRequestFailed: If the request fails at the HTTP layer, via a
            non-2xx response, or via a second consecutive 401 after one retry.
    """
    return _call_browse_api(
        _ITEM_BY_LEGACY_ID_URL, {"legacy_item_id": item_id}, timeout_s
    )


def fetch_url(url: str, *, timeout_s: float = 10.0) -> tuple[int, str]:
    """Convenience wrapper for the CLI/skill layer: parse a raw eBay URL and
    dispatch to `search()` or `get_item()`.

    This exists so a human can paste a raw eBay URL (a search results page
    or an item listing page) at a CLI. It is NOT the primary library entry
    point — library callers should call `search()` or `get_item()` directly
    with an explicit, already-known query or item ID.

    Args:
        url: An eBay search results or item listing URL.
        timeout_s: Timeout in seconds for both the OAuth token request and
            the Browse API request.

    Returns:
        A `(status_code, response_text)` tuple from the successful response.

    Raises:
        ValueError: If `url` matches neither the search (`_nkw` query param)
            nor item (`/itm/<id>`) shape.
        EbayCredentialsMissing: If credentials are unset or blank.
        EbayApiRequestFailed: If the underlying request fails.
    """
    search_term = _extract_search_term(url)
    if search_term is not None:
        return search(search_term, timeout_s=timeout_s)

    item_id = _extract_item_id(url)
    if item_id is not None:
        return get_item(item_id, timeout_s=timeout_s)

    raise ValueError(
        f"eBay URL {url!r} matches neither the search (_nkw) nor item (/itm/) shape"
    )
