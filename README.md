# api-clients-commons

api-clients-commons is a shared Python library of clients for official, authenticated third-party APIs. Home-lab projects use it so each one does not write its own API code. Today it has one client, for eBay's Browse API.

## Pick this repo or scraper-commons

Use this repo if the target has a documented API that you can register for. Use `scraper-commons` (a separate repo) if the only way in is a normal browser session. `scraper-commons` holds browser-based scraping code for sites with no API.

The two repos never import from each other. The caller picks one. No code routes a URL from one to the other.

## Build a client only when a project needs it

`CONTRACT.md` defines the shape: one submodule per API. A submodule exists only after a real project needs it.

- `ebay`: built. It does OAuth2 client-credentials login, item search, and item lookup by ID.

## Install

Python 3.11 or newer is required.

1. `git clone git@github.com:preston-bernstein/api-clients-commons.git`
2. `cd api-clients-commons`
3. `scripts/install-hooks.sh` (turns on the secret-scan hooks; needs `gitleaks`, for example `brew install gitleaks`)
4. `uv sync` (installs the package and the dev tools from `uv.lock`)

## Set the eBay credentials

Set two environment variables where the library runs. A gitignored `.env` file works.

- `EBAY_CLIENT_ID`: client ID of your eBay developer app
- `EBAY_CLIENT_SECRET`: client secret of the same app

Get both at [developer.ebay.com](https://developer.ebay.com). If one is missing or blank, the client raises `EbayCredentialsMissing` and names it.

## Call the eBay client from Python

```python
from api_clients_commons.ebay import search, get_item

status, body = search("corduroy jacket")
status, body = get_item("123456789012")
```

Both functions take `timeout_s=10.0`. Both return a `(status_code, response_text)` tuple. `response_text` is the raw JSON from eBay.

`fetch_url(url, *, timeout_s=10.0)` takes a pasted eBay URL and calls one of the two for you. It is for people at a CLI. Library code calls `search()` or `get_item()` directly.

All three functions raise `EbayApiRequestFailed` if the request fails (bad status, timeout, connection error). The errors are in `src/api_clients_commons/ebay/errors.py`.

## Call the eBay client from a shell

```bash
PYTHONPATH=/path/to/api-clients-commons/src python3 -m api_clients_commons.ebay "corduroy jacket"
PYTHONPATH=/path/to/api-clients-commons/src python3 -m api_clients_commons.ebay "https://www.ebay.com/itm/123456789012"
```

The argument is a search query or an eBay URL. The CLI treats a string that starts with `http://` or `https://` and contains `ebay.com` as a URL. This needs no install, only `PYTHONPATH`.

The `ebay-fetch` Claude Code skill wraps this CLI. See its `SKILL.md`.

## Run the tests

1. `uv sync`
2. `uv run pytest`

Tests use mocked HTTP. They make no live eBay calls.

## Where things live

```
src/api_clients_commons/ebay/
    __init__.py   public functions: search, get_item, fetch_url
    client.py     token cache, Browse API calls, retry on 401
    errors.py     EbayCredentialsMissing, EbayApiRequestFailed
    __main__.py   CLI
tests/            mocked HTTP tests
```

Stack: Python, `requests`, Hatchling, pytest, ruff, and gitleaks hooks in `.githooks/`.

License: MIT. See [LICENSE](LICENSE).
