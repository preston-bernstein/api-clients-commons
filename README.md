# api-clients-commons

api-clients-commons is a shared Python library for the home lab's projects
(internal-monitor-app, internal-scraper-service, internal-inventory-app, and future ones). It holds
clients for official, authenticated third-party APIs — the kind of access
where you're a registered, credentialed developer, not a browser pretending
to be one.

## How this differs from scraper-commons

`scraper-commons` (a separate repo) holds stealth and anti-detection logic —
a Playwright-based browser that mimics a real human, used against sites with
no official API. This repo is the opposite: real, credentialed API clients
for sites that do offer one. The two repos never import from each other, and
a caller picks one or the other explicitly — there's no auto-detection that
routes a URL from one into the other.

If you're not sure which one you need: does the target have a documented,
authenticated API you can register for? Use this repo. Does it not, and does
the only way in look like a normal browser session? Use `scraper-commons`.

## Built when a real consumer needs it, not speculatively

`CONTRACT.md` defines the intended shape — one submodule per official API a
home-lab project needs — but each submodule is only built once a real project
needs it, same discipline `scraper-commons` uses for its own modules. Status
today:

- **`ebay`** — implemented. A client for eBay's official Browse API (OAuth2
  client-credentials flow, item search, and item lookup by ID).

## Using the eBay client

```python
from api_clients_commons.ebay import search, get_item

status, body = search("corduroy jacket")
status, body = get_item("123456789012")
```

`search(query, *, timeout_s=10.0)` and `get_item(item_id, *, timeout_s=10.0)`
both return a `(status_code, response_text)` tuple — `response_text` is the
raw JSON body eBay's Browse API returned. A third function,
`fetch_url(url, *, timeout_s=10.0)`, exists only for pasting a raw eBay URL
(a search results page or an item page) at a CLI — it parses the URL and
calls `search()` or `get_item()` for you. Library code should call
`search()`/`get_item()` directly with an already-known query or item ID, not
`fetch_url()`.

All three raise `EbayCredentialsMissing` if `EBAY_CLIENT_ID` or
`EBAY_CLIENT_SECRET` aren't set, or `EbayApiRequestFailed` if the request
fails for any other reason (bad status, timeout, connection error) — see
`src/api_clients_commons/ebay/errors.py`.

### Required environment variables

- `EBAY_CLIENT_ID` — client ID from a personal eBay developer app
- `EBAY_CLIENT_SECRET` — client secret from the same app

Get both from [developer.ebay.com](https://developer.ebay.com) (free tier,
5,000 calls/day). Set them wherever this library runs — a gitignored `.env`
or plain environment variables. Missing credentials raise
`EbayCredentialsMissing` naming the exact missing variable(s); they never
silently fall back to anything else.

### CLI

```bash
PYTHONPATH=/path/to/api-clients-commons/src python3 -m api_clients_commons.ebay "corduroy jacket"
PYTHONPATH=/path/to/api-clients-commons/src python3 -m api_clients_commons.ebay "https://www.ebay.com/itm/123456789012"
```

The first argument is either a plain search query or a raw eBay URL — the
CLI tells them apart by checking for `ebay.com` in the string. No `pip
install` or venv needed; this runs straight off the checked-out source with
`PYTHONPATH` set.

### As a Claude Code skill

`~/.claude/skills/ebay-fetch/` wraps this CLI the same way — see that
skill's `SKILL.md` for day-to-day usage from a Claude Code session.

## Stack

| Layer | Tech |
|---|---|
| Language | Python 3.11+ |
| HTTP | `requests` |
| Build | Hatchling |
| Tests | pytest 8+ |
| Lint | ruff |
| Secret scanning | gitleaks, via versioned `.githooks/` |

## Project layout

```
src/api_clients_commons/
├── __init__.py          # package version, scaffold note
└── ebay/
    ├── __init__.py       # public entry points: search(), get_item(), fetch_url()
    ├── client.py          # OAuth2 token caching, Browse API calls, 401-retry
    ├── errors.py          # EbayCredentialsMissing, EbayApiRequestFailed
    └── __main__.py         # CLI entrypoint
tests/                    # mocked HTTP tests, no live eBay calls
```

## Quick start

### Prerequisites

- Python 3.11+
- `gitleaks` (required by the commit/push hooks — `brew install gitleaks` on macOS)

```bash
git clone git@github.com:preston-bernstein/api-clients-commons.git
cd api-clients-commons
scripts/install-hooks.sh          # one-time: enables pre-commit/pre-push secret scanning
pip install -e ".[test,dev]"
```

## Running tests

```bash
pip install -e ".[test]"
pytest
```

## License

MIT — see [LICENSE](LICENSE).
