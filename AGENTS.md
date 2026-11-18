# Agent rules for api-clients-commons

Read `CLAUDE.md` first for what this repo is and for the secret-scan hooks.

## Commands

- The core gate: `bash scripts/core-validate.sh` (file size, names, complexity, function length, parameters, nesting, duplication). Limits live in `.core-config`. No function is over a limit, so there is no baseline file. Do not add one.
- The Python gate: `bash scripts/py-validate.sh` (`uv run --locked` ruff check, ruff format --check, mypy, pytest).
- The GitHub Actions gate: `bash scripts/gha-validate.sh` (workflow-check.py, actionlint, zizmor).
- The shell gate: `bash scripts/shell-validate.sh` (bash -n, shell-check.py, shellcheck, shfmt, bats).
- The writing gate: `bash scripts/writing-validate.sh` (Vale on files changed against main).
- Install the gate tools on Linux x86_64: `bash scripts/install-gate-tools.sh`. Every tool is pinned and hash-locked or checksum-verified.
- Install the project: `uv sync`. Add a dependency with `uv add` or `uv add --dev`. Ask before adding a production dependency.
- Run once per clone: `scripts/install-hooks.sh`. The pre-commit hook runs the secret scan and then all five gates. CI runs the same gates once, in the `gates` job.

## Rules

- Never commit with `--no-verify`. Never edit a limit, a baseline, `.shellcheckrc` or a rule to make a gate pass. Fix the code, or waive it with a reason.
- The scripts named `*-validate.sh`, `core-*.py`, `shell-check.py` and `workflow-check.py` in `scripts/` are copied unchanged from the stack packs. Do not edit them.
- Pin every `uses:` to a full commit SHA with the version in a comment. Set `permissions: contents: read`, `timeout-minutes` and `persist-credentials: false`. A new action also needs an entry in `.github/zizmor.yml`.
- Never put `github.event.*` or `inputs.*` inside `run:`. Pass it through `env:`.
- Python: the ruff rule set is pinned in `pyproject.toml` with an empty ignore list. An exception is one line, `# noqa: CODE -- reason`. Catch the narrowest exception. Log through `logging.getLogger(__name__)`.
- Shell: `#!/usr/bin/env bash`, `set -euo pipefail`, quote every expansion, bash 3.2 portable, a `trap` for every `mktemp`. A behavior change ships with a bats test in `tests/`.
- Prose is short, plain, American English. Put the point first.
- Reuse before you write. Put variants in data, not in copies. Extract on the second real occurrence. No boolean flag arguments.
- A behavior change ships with a test that fails without it.
