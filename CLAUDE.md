# api-clients-commons

This is a scaffold, not a finished library. api-clients-commons is meant to
be **imported** by home-lab projects, not run on its own. Each submodule
(one per official, authenticated third-party API) gets implemented only
when the first real project needs it, extracted from that real use, never
written ahead of time on spec. See `CONTRACT.md` for the intended shape.

This repo is deliberately separate from `scraper-commons`: that repo holds
stealth/anti-detection scraping logic for sites with no official API; this
repo holds real, credentialed API clients for sites that do offer one.
Never import one from the other, and never auto-detect which one a caller
needs from a URL — the caller picks explicitly.

Cross-cutting home-lab conventions that apply here too — service users,
secrets, the split between a shared library and a shared service — live in
`internal-infra/CONVENTIONS.md`. The pattern this repo follows (dedicated lib
repo, dual-remote push, pinned-commit consumption) is the same one
`internal-infra/docs/adr/0015-shared-scraper-library.md` and
`internal-infra/docs/adr/0023-dedicated-lib-repos-for-fleet-logging-and-ollama-client.md`
already establish for `scraper-commons`, `fleet-logging`, and `ollama-client`.

## Remotes

A single `git push` to `origin` writes to two remotes: the NAS (primary,
`ssh://nas.example.internal/.../api-clients-commons.git`) first, then GitHub (offsite
mirror, `preston-bernstein/api-clients-commons`, private) second. `git fetch`
only reads from the NAS.

## Secret-scan gate — run once per clone

Git hooks that scan for secrets live in `.githooks/` and are checked into
the repo, but git does not turn them on automatically. On any fresh clone,
run **`scripts/install-hooks.sh`** once. It points git at that hooks folder
(`core.hooksPath`) and checks that `gitleaks` is installed.

Once enabled, the pre-commit hook blocks any commit that stages a secret or
a real `.env` file, and the pre-push hook scans outgoing commits before they
can reach the GitHub mirror. This fails closed: if the `gitleaks` binary
isn't installed, commits and pushes are refused rather than let through
unscanned. Install it with `brew install gitleaks`. The scan rules and
allowlist live in `.gitleaks.toml`.
