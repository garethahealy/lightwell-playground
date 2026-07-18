---
name: packages-redhat-reference
---

# packages.redhat.com / Lightwell reference

Supporting detail for [SKILL.md](SKILL.md). Read when resolving Lightwell Maven **dependency** versions (not plugins).

## What Lightwell is

[packages.redhat.com](https://packages.redhat.com/) supplies remediated / validated open source packages. This repo resolves them via `.m2/settings.xml` with `LIGHTWELL_USERNAME` / `LIGHTWELL_TOKEN`. **Local:** `source scripts/_creds.sh`. **CI:** same env names from GitHub Actions secrets in `.github/workflows/build.yaml` (never read `_creds.sh` into the LLM).

Lightwell often **backports fixes** onto a pinned upstream line (`.rhlw-*`) instead of forcing a disruptive upgrade.

## Deps vs plugins

| Kind | Discovery | Source label |
|------|-----------|--------------|
| Dependencies (and BOMs) | Lightwell `maven-metadata.xml` via `fetch-metadata.sh` | lightwell-remediated / lightwell-validated / upstream |
| Build plugins | `mvn --batch-mode --no-transfer-progress versions:display-plugin-updates` (Central) | upstream |

## Repo layout

| Catalog | Maven repository path | `Source:` comment URL | Settings repo id (typical) |
|---------|----------------------|------------------------|----------------------------|
| Remediated | `lightwell/java/remediated` | `https://packages.redhat.com/lightwell/java/remediated/` | `lightwell-remediated` |
| Validated | `lightwell/java/validated` | `https://packages.redhat.com/lightwell/java/validated/` | `lightwell-validated` |

Do not open `.m2/settings.xml`.

## Metadata URLs

```text
https://packages.redhat.com/lightwell/java/remediated/{groupPath}/{artifactId}/maven-metadata.xml
https://packages.redhat.com/lightwell/java/validated/{groupPath}/{artifactId}/maven-metadata.xml
```

`groupPath` = `groupId` with `.` → `/`.

## Helper

```bash
bash .cursor/skills/upgrade-dependencies/fetch-metadata.sh <remediated|validated> <groupId> <artifactId>
bash .cursor/skills/upgrade-dependencies/fetch-metadata.sh <remediated|validated> <groupId> <artifactId> --latest
bash .cursor/skills/upgrade-dependencies/fetch-metadata.sh <remediated|validated> <groupId> <artifactId> --release
```

- Default: full metadata XML
- `--latest` / `--release`: single version string (preferred for agent context)
- Exit non-zero + `MISSING` / `CREDS_*` on failure — never prints secrets

**Parallelism:** background one call per inventoried dependency, then `wait` (see SKILL.md).

## Catalog inference

| Signal | Catalog |
|--------|---------|
| `Source: …/lightwell/java/remediated/` | remediated |
| `Source: …/lightwell/java/validated/` | validated |
| Version `*.rhlw-*`, no comment | remediated |
| Otherwise | try validated metadata; if missing → Central (**upstream**) |

## Version rules

| Type | Prefer |
|------|--------|
| Remediated | Highest `rhlw` on the **same** upstream base as the current pin |
| Validated | `--latest` within constraints below |

**Ask before applying** (unless the user already said to take latest):

- Any **major** version bump
- A **minor** bump when `groupId` is under a breaking-minors ecosystem: `com.fasterxml.jackson`, `com.google.guava`, `org.springframework` (including subpackages)

Patch bumps within the same minor may apply without asking. Other groupIds: same-major minors may apply without asking.

## Maven flags

Always use `--batch-mode --no-transfer-progress` on agent-invoked `mvn` commands.

## Why not `versions-maven-plugin` for Lightwell deps

It merges Central + Lightwell and often reports Central-only “upgrades.” Confirm with `fetch-metadata.sh` before changing a Lightwell-backed dependency. Plugin updates via `versions:display-plugin-updates` are fine.

## Verify download source

After `mvn --batch-mode --no-transfer-progress clean install`, bumped Lightwell artifacts should show:

```text
Downloaded from lightwell-remediated: ...
Downloaded from lightwell-validated: ...
```

If the bumped GAV only appears as `Downloaded from central:`, treat as a failed Lightwell upgrade (revert / investigate). Cached “nothing to download” is OK if a prior Lightwell download for that exact version succeeded in the same session or the log earlier showed lightwell-*.

## Source comments

Keep for humans / Renovate; do not scrape for versions. Match this repo's `pom.xml` form:

```xml
<!-- Source: https://packages.redhat.com/lightwell/java/remediated/ -->
<!-- Source: https://packages.redhat.com/lightwell/java/validated/ -->
```

When touching a dependency that still has a legacy console.redhat.com comment, replace it with the matching `Source:` form above.

## Renovate

This skill owns intentional Lightwell bumps; preserve `Source:` comments and `.rhlw-*` shapes.
