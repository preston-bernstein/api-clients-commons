"""Public API for the eBay Browse API client.

Three entry points: `search(query)` and `get_item(item_id)` are the primary
ones — call them with an explicit, already-known query or item ID. `fetch_url(url)`
is a convenience wrapper for a human pasting a raw eBay URL at a CLI; it parses
the URL and dispatches to `search()` or `get_item()`.

Raises `EbayCredentialsMissing` if `EBAY_CLIENT_ID`/`EBAY_CLIENT_SECRET` are
unset or blank, or `EbayApiRequestFailed` on any other request failure — see
`errors.py` for semantics.
"""

from __future__ import annotations

from api_clients_commons.ebay.client import fetch_url as fetch_url
from api_clients_commons.ebay.client import get_item as get_item
from api_clients_commons.ebay.client import search as search
from api_clients_commons.ebay.errors import EbayApiRequestFailed as EbayApiRequestFailed
from api_clients_commons.ebay.errors import (
    EbayCredentialsMissing as EbayCredentialsMissing,
)
