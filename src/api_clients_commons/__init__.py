"""api-clients-commons: shared, authenticated official-API clients for
home-lab projects.

This is a scaffold, not a finished library. Each submodule (one per official,
authenticated third-party API a home-lab project needs to call directly) gets
implemented only when a real consumer needs it, extracted from that real use.
See CONTRACT.md for the intended shape.

Distinct from `scraper-commons`: that repo is for stealth/anti-detection
scraping of sites with no official API. This repo is the opposite kind of
access — legitimate, credentialed API calls. The two repos never import from
each other and are chosen explicitly per use, never auto-detected.

Implemented today: `api_clients_commons.ebay`.
"""

__version__ = "0.0.0"
