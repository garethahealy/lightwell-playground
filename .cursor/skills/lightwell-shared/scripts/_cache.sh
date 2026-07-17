# Shared cache path helpers for Lightwell skill scripts.
# Source this file; do not execute it. Never stores credentials.
# Requires Bash 5+.

lightwell_xdg_cache_home() {
  printf '%s\n' "${XDG_CACHE_HOME:-${HOME}/.cache}"
}

# Metadata cache root (maven-metadata.xml + etag + fetched_at).
# Never stores or consults HTTP Expires headers.
# Override: LIGHTWELL_METADATA_CACHE_DIR
# Disable:  LIGHTWELL_METADATA_NO_CACHE=1  (caller checks)
lightwell_metadata_cache_dir() {
  if [[ -n "${LIGHTWELL_METADATA_CACHE_DIR:-}" ]]; then
    printf '%s\n' "$LIGHTWELL_METADATA_CACHE_DIR"
    return
  fi
  printf '%s\n' "$(lightwell_xdg_cache_home)/lightwell-metadata"
}

# OSV cache root is owned by fetch_osv.py (LIGHTWELL_OSV_CACHE_DIR /
# LIGHTWELL_OSV_NO_CACHE). Bash no longer resolves that path.

# Provenance cache root (.provenance.sigstore.json bundles).
# Override: LIGHTWELL_PROVENANCE_CACHE_DIR
# Disable:  LIGHTWELL_PROVENANCE_NO_CACHE=1  → prints empty
lightwell_provenance_cache_dir() {
  if [[ "${LIGHTWELL_PROVENANCE_NO_CACHE:-}" == "1" ]]; then
    printf '\n'
    return
  fi
  if [[ -n "${LIGHTWELL_PROVENANCE_CACHE_DIR:-}" ]]; then
    printf '%s\n' "$LIGHTWELL_PROVENANCE_CACHE_DIR"
    return
  fi
  printf '%s\n' "$(lightwell_xdg_cache_home)/lightwell-provenance"
}
