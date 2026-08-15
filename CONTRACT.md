# Contract: api-clients-commons

## Intended shape

One submodule per official, authenticated third-party API a home-lab project
needs to call directly — not by scraping. Each submodule wraps that API's own
auth flow (OAuth2, API key, whatever the provider requires) and exposes a
small, explicit function per operation. No submodule gets built until a real
project needs it; this repo does not speculatively pre-build clients for
APIs nothing uses yet.

This is the same YAGNI discipline `scraper-commons`' own `CONTRACT.md` uses
for its modules — the difference is what each repo's modules are *for*.
`scraper-commons` modules make a browser look like a human, for sites with
no official API. This repo's modules make a legitimate, credentialed API
call, for sites that offer one.

## Design rules every submodule follows

1. **Explicit operations, not URL-sniffing.** A submodule's primary public
   functions take an explicit, already-known argument (a query string, an
   ID) — never a raw URL that gets silently parsed and routed. A
   convenience `fetch_url()`-style wrapper may exist for a human at a CLI,
   but it is not the primary entry point and nothing else in this repo (or
   any other home-lab repo) is allowed to call a submodule automatically
   based on detecting a hostname. Every use of this repo is a deliberate,
   opt-in choice by the caller.
2. **Credentials come from the environment, validated eagerly.** A missing
   or blank credential raises immediately, naming the exact missing
   variable(s), never falling back to some other behavior and never
   including the credential's value in an error message.
3. **No shared code with `scraper-commons`.** Different repo, different
   purpose, different dependency footprint (no browser automation here at
   all). If a genuine need for shared plumbing between the two ever shows
   up, that's a new, explicit decision to make then — not a default.

## Status today

- **`ebay`** — implemented. eBay's Browse API: OAuth2 client-credentials
  token flow (cached, auto-refreshed, retried once on a 401), item search,
  and item lookup by legacy numeric ID. Extracted from a first attempt that
  wrongly built this inside `scraper-commons` — see that repo's git history
  and `internal-infra`'s repo-architecture conventions for why it moved here.
