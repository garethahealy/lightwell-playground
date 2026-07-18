#!/usr/bin/env bash
# Fetch Lightwell maven-metadata.xml. Never prints credentials.
# Usage:
#   fetch-metadata.sh <remediated|validated> <groupId> <artifactId>
#   fetch-metadata.sh <remediated|validated> <groupId> <artifactId> --latest
#   fetch-metadata.sh <remediated|validated> <groupId> <artifactId> --release
# Run from anywhere; resolves repo root from this file's location.
set -euo pipefail

catalog="${1:-}"
group_id="${2:-}"
artifact_id="${3:-}"
mode="${4:-}"

if [[ -z "$catalog" || -z "$group_id" || -z "$artifact_id" ]]; then
  echo "usage: $0 <remediated|validated> <groupId> <artifactId> [--latest|--release]" >&2
  exit 2
fi

case "$catalog" in
  remediated|validated) ;;
  *)
    echo "catalog must be remediated or validated" >&2
    exit 2
    ;;
esac

case "$mode" in
  ""|--latest|--release) ;;
  *)
    echo "optional 4th arg must be --latest or --release" >&2
    exit 2
    ;;
esac

skill_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$skill_dir/../../.." && pwd)"
creds="$repo_root/scripts/_creds.sh"

if [[ ! -f "$creds" ]]; then
  echo "CREDS_FILE_MISSING" >&2
  exit 1
fi

# shellcheck disable=SC1090
set -a
source "$creds"
set +a

if [[ -z "${LIGHTWELL_TOKEN:-}" || -z "${LIGHTWELL_USERNAME:-}" ]]; then
  echo "CREDS_MISSING" >&2
  exit 1
fi

group_path="${group_id//.//}"
url="https://packages.redhat.com/lightwell/java/${catalog}/${group_path}/${artifact_id}/maven-metadata.xml"

xml="$(curl -sSL --fail --max-time 60 \
  -u "${LIGHTWELL_USERNAME}:${LIGHTWELL_TOKEN}" \
  "$url")"

if [[ -z "$mode" ]]; then
  printf '%s\n' "$xml"
  exit 0
fi

# Prefer python for reliable XML text extraction; fall back to sed.
extract_tag() {
  local tag="$1"
  if command -v python3 >/dev/null 2>&1; then
    LIGHTWELL_META_XML="$xml" LIGHTWELL_META_TAG="$tag" python3 - <<'PY'
import os, re, sys
xml = os.environ["LIGHTWELL_META_XML"]
tag = os.environ["LIGHTWELL_META_TAG"]
m = re.search(rf"<{tag}>([^<]+)</{tag}>", xml)
if not m:
    sys.exit(1)
print(m.group(1).strip())
PY
  else
    printf '%s\n' "$xml" | sed -n "s:.*<${tag}>\\([^<]*\\)</${tag}>.*:\\1:p" | head -n1
  fi
}

tag="latest"
[[ "$mode" == "--release" ]] && tag="release"

value="$(extract_tag "$tag")" || {
  echo "NO_${tag}" >&2
  exit 1
}
printf '%s\n' "$value"
