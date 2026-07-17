---
name: verify-attestations
description: >-
  Verify Lightwell Maven jars in the local repo against SLSA provenance
  Sigstore bundles from packages.redhat.com using cosign. Use when the user
  asks to verify attestations, provenance, or cosign Lightwell jars.
---

# Verify Attestations

Verify **local Maven repo jars** against sibling `.provenance.sigstore.json`
bundles via `cosign verify-blob-attestation`.

**Scope:** attestation only. Does not edit `pom.xml`. Pair with
[upgrade-directs](../upgrade-directs/SKILL.md) /
[upgrade-transitives](../upgrade-transitives/SKILL.md) after a successful
`mvn … clean install`.

Implementation (shared):
[verify-attestations.sh](../lightwell-shared/scripts/verify-attestations.sh).
Reference: [packages-redhat.md](../lightwell-shared/packages-redhat.md).

## CI

Workflow: [`.github/workflows/verify-attestations.yaml`](../../../.github/workflows/verify-attestations.yaml).

Manual `workflow_dispatch`, or push to `main` when `.cursor/skills/**` or
the workflow file changes. Builds with Maven, derives Lightwell coords via
`coords_from_pom.py`, then batch-verifies. Uses `LIGHTWELL_USERNAME` /
`LIGHTWELL_TOKEN` secrets. Exits successfully when the pom has no Lightwell
jars to verify.

## Execution mode (deterministic)

This skill is a **scripted pipeline**. Run it; do not investigate it.

- Run the verify commands **exactly** as written. Prefer
  `coords_from_apply.py` | `verify-attestations.sh --batch` over ad-hoc
  `cosign` invocations.
- Treat stdout lines (`OK …` / `FAIL … reason=…`) as authoritative. Report
  them; do not reinterpret, second-guess, or “improve” them.
- Documented stop only: **AUTH_FAILED** / HTTP 401/403. Otherwise, if the
  helper exits non-zero: **stop**, show the relevant stderr/stdout, and wait
  for the user.
- Do **not** use git history (`git log`, `git show`, `git blame`, historical
  `git diff`) to explain outcomes.
- Do **not** diagnose why a jar is missing, why provenance is
  `PROVENANCE_MISSING`, why cosign failed, or why a key/bundle looks wrong.
- Do **not** open, debug, or edit skill / `lightwell-shared` scripts unless the
  user explicitly asks to fix the tooling.
- Do **not** invent workarounds (manual `cosign`, re-download jars, cache
  bypasses, alternate public keys).

## Constraints

- Requires `cosign` and `mvn` or `mvnd` on `PATH` (`LIGHTWELL_MVN` to override).
- Creds: see [Credentials](../lightwell-shared/packages-redhat.md#credentials).
  Scripts are allowed to **run**, not to debug.
- If provenance download returns **HTTP 403** (or 401), **stop**. Tell the user
  to validate `LIGHTWELL_TOKEN`.
- Provenance cached under `lightwell-provenance/`. Does **not** re-download jars.

## Workflow

```
Progress:
- [ ] 1. Ensure jars exist (build already ran)
- [ ] 2. Batch-verify bumped Lightwell GAVs
- [ ] 3. Report OK / FAIL
```

### Verify

From pom.xml (standalone / CI):

```bash
source .cursor/skills/lightwell-shared/scripts/_load-creds.sh || exit 1
python3 .cursor/skills/lightwell-shared/scripts/coords_from_pom.py --pom pom.xml \
| bash .cursor/skills/lightwell-shared/scripts/verify-attestations.sh --batch
```

From an upgrade apply JSON (preferred after Apply):

```bash
source .cursor/skills/lightwell-shared/scripts/_load-creds.sh || exit 1
python3 .cursor/skills/lightwell-shared/scripts/coords_from_apply.py \
  --from-apply /tmp/direct-apply.json \
| bash .cursor/skills/lightwell-shared/scripts/verify-attestations.sh --batch
```

Or explicit coordinates:

```bash
attest=".cursor/skills/lightwell-shared/scripts/verify-attestations.sh"
source .cursor/skills/lightwell-shared/scripts/_load-creds.sh || exit 1
printf '%s\n' \
  "remediated org.json json 20220320.0.0.rhlw-00003" \
  "validated com.fasterxml.jackson.dataformat jackson-dataformat-yaml 2.19.4" \
  | "$attest" --batch
```

Stdout: `OK catalog g:a:v` or `FAIL catalog g:a:v reason=…`.
Report those lines as-is; do not dig into why. Workers:
`LIGHTWELL_ATTEST_JOBS` (default 8).

## Do not

- Look at git history or reason about *why* verification failed / provenance
  is missing
- Debug or bypass the helper; invent workarounds
- Invent public keys (helper extracts from Rekor entry in the bundle)
- Use `cosign verify-blob` instead of `verify-blob-attestation`
- Continue after `AUTH_FAILED` / HTTP 403 — stop and ask the user to validate
  `LIGHTWELL_TOKEN`
- Print secrets
