---
name: upgrade-directs
description: >-
  Upgrade direct Maven dependencies in pom.xml with preference for Red Hat
  Lightwell packages (java/remediated and java/validated). Workflow: plan,
  collect, apply, summary. Use when the user asks to upgrade directs, bump
  versions, or mentions upgrade-directs / Lightwell directs.
---

# Upgrade Directs

Upgrade **direct** Maven dependencies in `pom.xml`. Prefer Red Hat Lightwell
artifacts from the [Lightwell demo](https://console.redhat.com/lightwell/demo)
catalogs on [packages.redhat.com](https://packages.redhat.com/).

**Scope:** direct deps only. For transitives use
[upgrade-transitives](../upgrade-transitives/SKILL.md).
For cosign provenance use [verify-attestations](../verify-attestations/SKILL.md).

**Agent contract (read first):**
[upgrade-common.md](../lightwell-shared/upgrade-common.md)
(execution mode, SemVer, constraints, creds, attestations, shared Do not).

Shared API: [packages-redhat.md](../lightwell-shared/packages-redhat.md).

Scripts (one per phase): `scripts/plan.py`, `collect.py`, `apply.py`,
`summary.py`.

## CI

Workflow: [`.github/workflows/upgrade-directs.yaml`](../../../.github/workflows/upgrade-directs.yaml).

Manual `workflow_dispatch`, or push to `main` when `.cursor/skills/**` or
the workflow file changes. Runs Plan → Collect → Apply (`--include-ask`) →
Summary, then prints `pom.xml`. Uses `LIGHTWELL_USERNAME` /
`LIGHTWELL_TOKEN` secrets. Does not commit. Attestations:
[verify-attestations.yaml](../../../.github/workflows/verify-attestations.yaml).

## Workflow

```
Progress:
- [ ] 1. Plan
- [ ] 2. Collect
- [ ] 3. Apply
- [ ] 4. Summary
```

### 1. Plan

```bash
python3 .cursor/skills/upgrade-directs/scripts/plan.py \
  --pom pom.xml -o /tmp/direct-plan.json
```

Local parse only. Output: `{ pom, dependencies[], promotedSkipped[] }`.

### 2. Collect

```bash
source .cursor/skills/lightwell-shared/scripts/_load-creds.sh || exit 1
python3 .cursor/skills/upgrade-directs/scripts/collect.py \
  --from-plan /tmp/direct-plan.json -o /tmp/direct-collect.json
```

Output: `{ pom, results[] }` with `UPGRADE` | `ASK` | `KEEP` | `MISSING`.

- **remediated:** same SemVer base highest `.rhlw-*` → `UPGRADE` (same
  major.minor.patch auto-applies)
- **validated:** catalog `latest`; SemVer gate (never downgrade)
- Unknown catalog: remediated same-base first, then validated latest
- **Primary miss:** if no same-base / preferred hit, search G:A for catalog
  `latest` (remediated then validated). Newer hit → `ASK` with
  `reason=suggested-catalog-latest` (never auto-`UPGRADE`, even with
  `--take-latest`). Still nothing → `MISSING`
- `--take-latest` only if the user already approved those bumps

**Gate:** If any result is `ASK`, **stop** after Collect. Present the rows and
wait. Then Apply with `--include-ask` (or re-Collect with `--take-latest`).

Do not edit `pom.xml` in this phase.

### 3. Apply

```bash
python3 .cursor/skills/upgrade-directs/scripts/apply.py \
  --from-collect /tmp/direct-collect.json -o /tmp/direct-apply.json
```

| Flag | Meaning |
|------|---------|
| `--include-ask` | Also apply `ASK` rows (recorded as `UPGRADE`) |
| `--dry-run` | Show planned bumps; no pom write / build |
| `--skip-build` | Edit pom only |

Applies `UPGRADE` (and approved `ASK`), refreshes `Source:` comments, runs
`mvn clean install`. Build failure → leave pom for debugging, exit non-zero →
**stop**. Never `mvn -X`.


Then run [post-Apply attestations](../lightwell-shared/upgrade-common.md#post-apply-attestations)
with `/tmp/direct-apply.json`.

### 4. Summary

```bash
source .cursor/skills/lightwell-shared/scripts/_load-creds.sh || exit 1
python3 .cursor/skills/upgrade-directs/scripts/summary.py \
  --from-collect /tmp/direct-collect.json \
  --from-apply /tmp/direct-apply.json -o /tmp/direct-summary.md
```

`--from-apply` is **required**. Markdown table + OSV for remediated applied
bumps (`--skip-osv` to skip). OSV `AUTH_FAILED` → exit non-zero → **stop**.
Link CVE cells to `osv=` URLs. Do not invent CVEs.

## Skill-specific Do not

- Touch transitive promotions / exclusions (other skill)
- Replace `.rhlw-*` with Central without approval
