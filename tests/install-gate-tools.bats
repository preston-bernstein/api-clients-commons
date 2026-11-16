#!/usr/bin/env bats
# Behavior tests for scripts/install-gate-tools.sh. The real install needs the network, so these cover
# the argument and error paths only.

setup() {
  SCRIPT="$BATS_TEST_DIRNAME/../scripts/install-gate-tools.sh"
}

@test "--help prints usage and exits 0" {
  run "$SCRIPT" --help
  [ "$status" -eq 0 ]
  [[ "$output" == *Usage* ]]
}

@test "an unknown option exits 2 with a message" {
  run "$SCRIPT" --nope
  [ "$status" -eq 2 ]
  [[ "$output" == *"unknown option"* ]]
}

@test "every pinned download has a 64-digit SHA-256" {
  run grep -cE '^  "[a-z]+\|[0-9.]+\|[^|]+\|https://[^|]+\|[0-9a-f]{64}\|[^|]+"$' "$SCRIPT"
  [ "$status" -eq 0 ]
  [ "$output" -eq 4 ]
}
