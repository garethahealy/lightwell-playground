---
name: add-osv-to-renovate
description: >-
  Find open Renovate pull requests, look up Lightwell remediated OSV advisories
  for Maven dependency bumps, and comment an OSV summary when matches exist.
  Use when the user asks to add OSV comments to Renovate PRs, annotate Renovate
  dependency updates with CVEs, or mentions add-osv-to-renovate.
---

# Add OSV to Renovate

Comment Lightwell remediated OSV advisory summaries onto open Renovate PRs that
bump Maven dependencies (especially `.rhlw-*` remediations).

Reuses the OSV pipeline from
[lightwell-shared](../lightwell-shared/packages-redhat.md)
(`fetch_osv.py` / `match_osv_cves.py` / `format-osv-table.py`).

## Execution mode (deterministic)

This skill is a **scripted pipeline**. Run it; do not investigate it.

- Prefer `scripts/process-renovate-prs.sh` over ad-hoc `gh` + curl. Run it
  **exactly** as written (optionally `--dry-run`, `--pr N`, `-v` when requested).
- Treat script status lines (`COMMENTED`, `SKIP_*`, `ERROR_*`) as authoritative.
  Summarize them; do not reinterpret or “fix” skips.
- If the orchestrator exits non-zero or prints `ERROR_*`: **stop**, show the
  output, and wait for the user. Do not diagnose or retry with a hand-rolled
  flow unless the user asks.
- Do **not** use git history (`git log`, `git show`, `git blame`) to explain PR
  contents or why OSV matched/missed.
- Do **not** open, debug, or edit skill / `lightwell-shared` scripts unless the
  user explicitly asks to fix the tooling.
- Manual fallback is only when the orchestrator **cannot run** (missing binary),
  not when a PR was skipped or had no OSV matches.

## Constraints

- Do **not** read or modify paths listed in `.gitignore` / `.cursorignore`.
- Load Lightwell secrets only via helpers — never Read/cat/diff `scripts/_creds.sh`
  or print `LIGHTWELL_*`.
- Do not invent CVEs. Only comment when `fetch_osv.py` returns matches.
- Do not commit or merge Renovate PRs unless the user asks.
- Prefer the orchestrator script over ad-hoc `gh` + curl.
- Orchestrator needs `gh`, `jq`, and the shared OSV helper (no inline Python).

## CI

Workflow: [`.github/workflows/add-osv-to-renovate.yaml`](../../../.github/workflows/add-osv-to-renovate.yaml).

Runs `scripts/process-renovate-prs.sh` on Renovate `pull_request` events
(`opened` / `reopened` / `synchronize`), only when the PR author is
`renovate[bot]`. Uses `LIGHTWELL_USERNAME` / `LIGHTWELL_TOKEN` secrets and
`GITHUB_TOKEN` for comments.

## Workflow

```
Progress:
- [ ] 1. List open Renovate PRs
- [ ] 2. Extract Maven bumps + query OSV
- [ ] 3. Comment matches (skip duplicates)
- [ ] 4. Summarize
```

### 1–3. Process PRs (preferred)

From the repo root:

```bash
helper=".cursor/skills/add-osv-to-renovate/scripts/process-renovate-prs.sh"
"$helper"              # all open Renovate PRs
"$helper" --dry-run    # parse + OSV; print comment body; do not post
"$helper" --pr 6       # single PR
"$helper" -v           # progress on stderr
```

The script:

1. Lists open PRs authored by `app/renovate` (`gh`).
2. Skips PRs whose comments already contain `<!-- lightwell-osv-summary -->`.
3. Parses Maven `groupId:artifactId` + `from` → `to` from the Renovate PR body table.
4. Keeps bumps where **from or to** contains `.rhlw-` (remediated OSV scope).
5. Loads creds via `_load-creds.sh`, then calls `../lightwell-shared/scripts/fetch_osv.py`
   with those quadruplets.
6. On matches, posts a PR comment (unless `--dry-run`).

Stdout status lines (one per PR):

| Token | Meaning |
|-------|---------|
| `COMMENTED` | Posted OSV summary (`N` advisory lines) |
| `DRY_RUN_WOULD_COMMENT` | Matches found; comment body printed to stdout; not posted |
| `SKIP_ALREADY_COMMENTED` | Marker already present |
| `SKIP_NO_MAVEN_BUMPS` | No parseable Maven table rows |
| `SKIP_NO_RHLW` | Maven bumps present but none remediated |
| `SKIP_NO_OSV_MATCH` | Queried; no advisories fixed by the bump |
| `ERROR_*` | `gh` / creds / OSV failure |

### 4. Summarize

List which PRs were commented, skipped, or failed from the status lines. Link
PR URLs. Do not explain *why* beyond the status token. Do not paste credentials
or curl configs.

## Comment format

Posted body (marker required for idempotency):

```markdown
<!-- lightwell-osv-summary -->
## Lightwell OSV advisories fixed by this update

| Package | CVE / advisory | Summary | Fixed in |
|---------|----------------|---------|----------|
| `g:a` | [`CVE-…`](https://packages.redhat.com/api/pulp-content/public-lightwell-demo/osv/java/remediated/….json) | short text | `toVersion` |

_Source: Lightwell remediated OSV (`packages.redhat.com/api/pulp-content/public-lightwell-demo/osv/java/remediated`)._

Link the CVE/advisory cell to the `osv=` URL from `fetch_osv.py`.
```

## Manual fallback

If the orchestrator cannot run, mirror it with `gh` + the shared OSV helper:

```bash
gh pr list --author "app/renovate" --state open --json number,title,url,body
source .cursor/skills/lightwell-shared/scripts/_load-creds.sh || exit 1
python3 .cursor/skills/lightwell-shared/scripts/fetch_osv.py \
  <groupId> <artifactId> <fromVersion> <toVersion>
gh pr comment <N> --body-file /tmp/osv-comment.md
```

Parse bumps with:

```bash
python3 .cursor/skills/add-osv-to-renovate/scripts/parse-renovate-bumps.py < body.md
```

Matching rules and OSV URLs: [packages-redhat.md](../lightwell-shared/packages-redhat.md).

## Do not

- Look at git history or reason about *why* a PR was skipped / had no OSV
- Debug or bypass the orchestrator; invent workarounds
- Comment when there are no OSV matches
- Re-comment when `<!-- lightwell-osv-summary -->` is already on the PR
- Query OSV for non-Maven Renovate updates (actions, pre-commit, etc.)
- Read, print, or transmit `scripts/_creds.sh` or Lightwell secret values
- Run `set -x` / `bash -x` with visible secrets
