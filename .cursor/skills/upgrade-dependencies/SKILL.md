---
name: upgrade-dependencies
description: >-
  Upgrade Maven dependencies in pom.xml with preference for Red Hat Lightwell
  packages from packages.redhat.com (java/remediated and java/validated). Use
  when the user asks to upgrade dependencies, bump versions, update Maven
  artifacts, check for newer Lightwell packages, or mentions packages.redhat.com
  / Lightwell.
---

# Upgrade Dependencies

Upgrade managed Maven dependencies and plugins in this repo's `pom.xml`. 
Prefer Red Hat Lightwell artifacts from [packages.redhat.com](https://packages.redhat.com/) over Maven Central when Lightwell coverage exists.

**Scope:** `pom.xml` only (dependencies, plugins, version properties). Do not bump `.pre-commit-config.yaml` or other non-Maven manifests unless the user asks.

## Constraints

- Do **not** read or modify files listed in `.gitignore` or `.cursorignore` (includes `.m2/` and `scripts/`).
- Source Lightwell secrets from `scripts/_creds.sh` only inside shell commands (see [Credentials](#credentials)).
- Use `--settings=.m2/settings.xml` for Maven.
- Always pass `--batch-mode --no-transfer-progress` on `mvn` to keep transcripts small.
- Do not commit unless the user asks.

## Credentials

Auth file: `scripts/_creds.sh` (ignored). Exports `LIGHTWELL_USERNAME` and `LIGHTWELL_TOKEN`.

**Never send secrets to the LLM:**

- Do not open, Read, cat, type, or diff `scripts/_creds.sh`.
- Do not `echo`, `printenv`, or log `LIGHTWELL_USERNAME` / `LIGHTWELL_TOKEN`.
- Do not paste secret values into chat, commits, PR bodies, or tool args.
- Do not run `mvn -X` / `--debug`, `set -x`, `bash -x`, `zsh -x`, or any other xtrace/verbose mode that expands shell variables into the transcript.
- Do not run any command that expands those vars into stdout/stderr (e.g. `echo "$LIGHTWELL_TOKEN"`, `env | grep LIGHTWELL`, `declare -p LIGHTWELL_TOKEN`, `curl -v` with `-u` credentials visible).

Load creds only in the shell that runs Maven / metadata fetch:

```bash
set -a
# shellcheck disable=SC1091
source scripts/_creds.sh
set +a
[[ -n "${LIGHTWELL_TOKEN:-}" && -n "${LIGHTWELL_USERNAME:-}" ]] || { echo "CREDS_MISSING"; exit 1; }
echo "CREDS_OK"
```

If sourcing fails or auth fails, say credentials are missing/invalid **without** inspecting the file. Ask the user to fix `scripts/_creds.sh` locally.

**CI parity:** Local auth is `source scripts/_creds.sh`. CI (`.github/workflows/build.yaml`) sets the same env names from GitHub Actions secrets (`LIGHTWELL_USERNAME`, `LIGHTWELL_TOKEN`) without that file. 
Same Maven flags and `--settings=.m2/settings.xml` either way — do not invent a second auth or settings path.

## Workflow

```
Upgrade progress:
- [ ] 1. Inventory
- [ ] 2. Resolve (deps via Lightwell metadata; plugins via Central)
- [ ] 3. Apply pom updates
- [ ] 4. Verify build + download source
- [ ] 5. Summarize
```

### 1. Inventory

From `pom.xml`, split into two lists:

**Dependencies** (and BOM/imported coords if any):

| Coordinate | Current version | Catalog | Target |
|------------|-----------------|---------|--------|
| `g:a` | `x.y.z` | remediated / validated / unknown | TBD |

**Plugins** (and plugin version properties):

| Plugin | Current version | Target |
|--------|-----------------|--------|
| `g:a` | `x.y.z` | TBD |

Catalog from HTML comments when present (prefer the `Source:` form used in this repo's `pom.xml`):

- `<!-- Source: https://packages.redhat.com/lightwell/java/remediated/ -->` → remediated
- `<!-- Source: https://packages.redhat.com/lightwell/java/validated/ -->` → validated

Legacy console comments (if still present) map the same way:

- `…/lightwell/java-remediated/…` → remediated
- `…/lightwell/java-validated/…` → validated

If no comment, **infer**:

1. Version matches `*.rhlw-*` → remediated
2. Else try validated metadata (helper); if 404 / missing → unknown (Central fallback)

Do not scrape packages.redhat.com or console.redhat.com HTML for versions — use `fetch-metadata.sh` only.

### 2. Resolve

#### Dependencies (Lightwell first)

For **each inventoried** dependency coordinate (do not hardcode GAVs from examples), resolve in parallel in one shell. 
Prefer `--latest` so only a version string is printed:

```bash
helper=".cursor/skills/upgrade-dependencies/fetch-metadata.sh"
fetch_one() {
  local catalog="$1" g="$2" a="$3"
  local ver
  if ver=$(bash "$helper" "$catalog" "$g" "$a" --latest 2>/dev/null); then
    echo "$catalog $g:$a -> $ver"
  else
    echo "$catalog $g:$a -> MISSING"
  fi
}
# One background job per inventoried dep, then wait — substitute real catalog/g/a from inventory:
# fetch_one <catalog> <groupId> <artifactId> &
# ...
wait
```

Version selection:

- **remediated:** newest `.rhlw-*` on the **same upstream base** as the current pin (unless the user asks to move upstream). If `--latest` is a different upstream base, inspect full metadata (`fetch-metadata.sh` without `--latest`) and pick the highest `rhlw` on the current base.
- **validated:** Lightwell `--latest` within the same major by default. **Ask first** before:
  - any **major** bump, or
  - a **minor** bump when the `groupId` is in a breaking-minors ecosystem (see below).
- **unknown / no Lightwell:** compatible Central latest; label **upstream**. Same ask rules for major / sensitive minors.

**Breaking-minors ecosystems** (ask before minor or major unless the user already approved “take latest”):

- `com.fasterxml.jackson` (and `com.fasterxml.jackson.*`)
- `com.google.guava`
- `org.springframework` (and `org.springframework.*`)

Patch bumps (`x.y.Z` → `x.y.Z'`) within the same minor may apply without asking.

Do **not** trust `versions:display-dependency-updates` alone for Lightwell-backed deps (merges Central). Never invent `.rhlw-*` versions.

#### Plugins (Central / versions plugin)

Plugins are **not** upgraded via Lightwell metadata. Use:

```bash
set -a && source scripts/_creds.sh && set +a
mvn --batch-mode --no-transfer-progress versions:display-plugin-updates --settings=.m2/settings.xml
```

Take the newest stable plugin version for the project's Maven line (ignore Maven 4-only betas unless the user asks). Label source **upstream**.

### 3. Apply pom updates

1. Update `<version>` or the owning property.
2. Keep or add the matching `Source:` package comment for Lightwell deps:
   - remediated: `<!-- Source: https://packages.redhat.com/lightwell/java/remediated/ -->`
   - validated: `<!-- Source: https://packages.redhat.com/lightwell/java/validated/ -->`
   When upgrading a dep that still has a legacy console.redhat.com comment, replace it with the matching `Source:` form above.
3. Prefer property-managed versions when shared.
4. Do not change coordinates unless Lightwell documents a remap.
5. Leave unrelated formatting untouched.

### 4. Verify build + download source

Capture the build log and confirm bumped Lightwell artifacts were not silently pulled from Central:

```bash
set -a && source scripts/_creds.sh && set +a
[[ -n "${LIGHTWELL_TOKEN:-}" && -n "${LIGHTWELL_USERNAME:-}" ]] || { echo "CREDS_MISSING"; exit 1; }
log="$(mktemp)"
mvn --batch-mode --no-transfer-progress clean install --settings=.m2/settings.xml 2>&1 | tee "$log"
# For each bumped Lightwell dep, require lightwell-* lines for that artifactId/version:
#   Downloaded from lightwell-remediated: ...
#   Downloaded from lightwell-validated: ...
# Fail the upgrade summary if the only hit is "Downloaded from central" for that GAV.
grep -E 'Downloaded from lightwell-(remediated|validated):' "$log" || true
# Substitute each bumped artifactId into the pattern below (from inventory — do not hardcode):
# grep -E "Downloaded from central:.*/<artifactId>/<version>/" "$log" && echo "WARN: central download for Lightwell-intended artifact"
rm -f "$log"
```

Fix resolve/compile failures before finishing. Never dump env while debugging. 
Do not escalate to `mvn -X`, `set -x`, or credential-expanding commands — report auth/build failure without inspecting secret values.

### 5. Summarize

| Artifact | From | To | Source |
|----------|------|-----|--------|
| `g:a` | old | new | lightwell-remediated / lightwell-validated / upstream |

Call out skips (already latest, no Lightwell coverage, auth blocked, major bump needs approval, resolved from Central unexpectedly).

## Decision rules

| Situation | Action |
|-----------|--------|
| Newer `.rhlw-*` on same upstream base | Bump to that build |
| Validated patch within same minor | Bump to Lightwell `--latest` (or that patch) |
| Validated minor in breaking-minors ecosystem | **Ask** before applying |
| Validated / upstream major bump | **Ask** before applying |
| Other validated minor (not in breaking-minors list) | Bump within same major |
| Central suggests non-`rhlw` for a remediated dep | **Ignore** unless user asks to leave Lightwell |
| Plugin update available | Bump via Central; source **upstream** |
| Only Central for a dep | Bump upstream; label **upstream** |
| Build fails or Central download for Lightwell bump | Revert that bump; explain |

This skill owns intentional Lightwell bumps (do not defer to Renovate). Preserve `Source:` package comments and `.rhlw-*` shapes.

## Do not

- Strip Lightwell `Source:` package comment links (or leave deps without a catalog comment when adding/keeping Lightwell coverage)
- Replace a remediated (`.rhlw-*`) artifact with a non-`rhlw` Central jar without explicit user approval
- Use Lightwell metadata URLs to “upgrade” Maven plugins
- Read, print, or transmit `scripts/_creds.sh` or Lightwell secret values
- Run `mvn -X` / `--debug`, `set -x` / `bash -x` / `zsh -x`, or any command that expands `LIGHTWELL_USERNAME` / `LIGHTWELL_TOKEN` into stdout/stderr
- Commit secrets
- Touch ignored paths under `.m2/` or `scripts/`
- Use packages.redhat.com or console.redhat.com HTML as the primary version source
