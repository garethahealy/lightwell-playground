# Shared repository path helpers for Lightwell skill scripts.
# Source this file; do not execute it. Requires Bash 5+.

# Print the git repo root containing start_dir (default: this file's skill tree).
# Falls back to walking up from start_dir when git is unavailable.
lightwell_repo_root() {
  local start="${1:-}"
  local root=""
  if [[ -z "$start" ]]; then
    start="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  fi
  root="$(git -C "${start}" rev-parse --show-toplevel 2>/dev/null || true)"
  if [[ -n "$root" ]]; then
    printf '%s\n' "$root"
    return 0
  fi
  # lightwell-shared/scripts → repo root is ../../../../ from scripts when nested
  # under .cursor/skills/lightwell-shared/scripts
  printf '%s\n' "$(cd "${start}/../../../.." && pwd)"
}

# Prefer Maven Daemon when available (override: LIGHTWELL_MVN).
lightwell_mvn_bin() {
  if [[ -n "${LIGHTWELL_MVN:-}" ]]; then
    printf '%s\n' "$LIGHTWELL_MVN"
    return
  fi
  if command -v mvnd >/dev/null 2>&1; then
    printf '%s\n' "mvnd"
    return
  fi
  printf '%s\n' "mvn"
}

# Resolve Maven settings.localRepository for a repo.
# Usage: lightwell_resolve_local_repo <repo_root> <settings_arg>
# settings_arg is passed to mvn --settings= (repo-relative or absolute).
# Prints the local repository path on stdout. Returns non-zero on failure.
#
# Note: do not use -q here. mvnd 1.0.x quiet mode swallows help:evaluate
# -DforceStdout output (plain mvn does not). Without -q, strip [LEVEL] log
# lines so both mvn and mvnd yield the path alone.
lightwell_resolve_local_repo() {
  local repo_root="$1"
  local settings_arg="$2"
  local out=""
  local mvn_bin
  mvn_bin="$(lightwell_mvn_bin)"
  out="$(
    (
      cd "$repo_root" || exit 1
      "$mvn_bin" --batch-mode --no-transfer-progress \
        --settings="${settings_arg}" \
        help:evaluate -Dexpression=settings.localRepository -DforceStdout
    ) 2>/dev/null \
      | grep -Ev '^\[|^[[:space:]]*$' \
      | tail -n 1 \
      | tr -d '\r'
  )" || return 1
  out="${out#"${out%%[![:space:]]*}"}"
  out="${out%"${out##*[![:space:]]}"}"
  if [[ -z "$out" || "$out" == *null* ]]; then
    return 1
  fi
  printf '%s\n' "$out"
}
