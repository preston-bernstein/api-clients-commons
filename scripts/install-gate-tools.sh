#!/usr/bin/env bash
# Install the pinned tools that the gate scripts need. CI and developers on Linux x86_64 run this same script.
# Python tools come from a hash-locked file, Node tools from a lockfile with integrity hashes, and binaries
# from a download that must match a pinned SHA-256. To upgrade a tool, edit the pin here or in ci/, then read the diff.
#
# Usage: install-gate-tools.sh [DIR]   Installs into DIR (default: $GATE_TOOLS_DIR or ~/.gate-tools).
#        Put DIR/bin on PATH afterward. In GitHub Actions the script does that through GITHUB_PATH.
set -euo pipefail

PROG="${0##*/}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CI_DIR="$HERE/../ci"
tmp=""

# name|version|archive file|url|sha256|path of the binary inside the archive ("-" if the download is the binary)
BINARIES=(
  "actionlint|1.7.12|actionlint_1.7.12_linux_amd64.tar.gz|https://github.com/rhysd/actionlint/releases/download/v1.7.12/actionlint_1.7.12_linux_amd64.tar.gz|8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8|actionlint"
  "shellcheck|0.11.0|shellcheck-v0.11.0.linux.x86_64.tar.xz|https://github.com/koalaman/shellcheck/releases/download/v0.11.0/shellcheck-v0.11.0.linux.x86_64.tar.xz|8c3be12b05d5c177a04c29e3c78ce89ac86f1595681cab149b65b97c4e227198|shellcheck-v0.11.0/shellcheck"
  "shfmt|3.14.1|shfmt_v3.14.1_linux_amd64|https://github.com/mvdan/sh/releases/download/v3.14.1/shfmt_v3.14.1_linux_amd64|76e77641faa025814b77f153b29796b8e6fa2fca03e0c76a691608b86c7ea7bf|-"
  "vale|3.27.0|vale_3.27.0_Linux_64-bit.tar.gz|https://github.com/vale-cli/vale/releases/download/v3.27.0/vale_3.27.0_Linux_64-bit.tar.gz|c80d62f6bce87b81843ac5b512a26e63213927b957adba0a64fc594570da2000|vale"
)

log() { printf '%s: %s\n' "$PROG" "$*" >&2; }
die() {
  log "error: $1"
  exit "${2:-1}"
}
usage() {
  cat <<USAGE
Usage: $PROG [--help] [DIR]
Install the pinned gate tools into DIR (default: \$GATE_TOOLS_DIR or ~/.gate-tools).
USAGE
}
need() { command -v "$1" >/dev/null 2>&1 || die "missing tool: $1" 127; }
cleanup() { [ -z "$tmp" ] || rm -rf "$tmp"; }

install_python_tools() {
  local dir="$1"
  python3 -m venv "$dir/venv"
  "$dir/venv/bin/python" -m pip install --quiet --require-hashes -r "$CI_DIR/gate-tools.txt"
  ln -sf "$dir/venv/bin/lizard" "$dir/bin/lizard"
  ln -sf "$dir/venv/bin/zizmor" "$dir/bin/zizmor"
}

install_node_tools() {
  local dir="$1"
  mkdir -p "$dir/node"
  cp "$CI_DIR/package.json" "$CI_DIR/package-lock.json" "$dir/node/"
  npm ci --silent --ignore-scripts --prefix "$dir/node"
  ln -sf "$dir/node/node_modules/.bin/jscpd" "$dir/bin/jscpd"
  ln -sf "$dir/node/node_modules/.bin/bats" "$dir/bin/bats"
}

install_binary() {
  local dir="$1" entry="$2"
  local name version archive url sha inner
  IFS='|' read -r name version archive url sha inner <<<"$entry"
  log "installing $name $version"
  curl --fail --silent --show-error --location --output "$tmp/$archive" "$url"
  printf '%s  %s\n' "$sha" "$tmp/$archive" | sha256sum --check --status \
    || die "checksum mismatch for $archive"
  if [ "$inner" = "-" ]; then
    install -m 0755 "$tmp/$archive" "$dir/bin/$name"
    return 0
  fi
  tar -xf "$tmp/$archive" -C "$tmp" "$inner"
  install -m 0755 "$tmp/$inner" "$dir/bin/$name"
}

main() {
  local dir=""
  while [ "$#" -gt 0 ]; do
    case "$1" in
      -h | --help)
        usage
        exit 0
        ;;
      -*)
        usage >&2
        die "unknown option: $1" 2
        ;;
      *) dir="$1" ;;
    esac
    shift
  done
  dir="${dir:-${GATE_TOOLS_DIR:-$HOME/.gate-tools}}"

  [ "$(uname -s)-$(uname -m)" = "Linux-x86_64" ] || die "the pinned binaries are for Linux x86_64 only" 2
  need python3
  need npm
  need curl
  need sha256sum
  need tar

  tmp="$(mktemp -d)"
  trap cleanup EXIT
  mkdir -p "$dir/bin"

  install_python_tools "$dir"
  install_node_tools "$dir"
  local entry
  for entry in "${BINARIES[@]}"; do
    install_binary "$dir" "$entry"
  done

  log "installed into $dir/bin"
  if [ -n "${GITHUB_PATH:-}" ]; then
    printf '%s\n' "$dir/bin" >>"$GITHUB_PATH"
  fi
}

main "$@"
