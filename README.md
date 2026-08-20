# lightwell-playground

Small Java demo for [Red Hat Lightwell](https://console.redhat.com/lightwell/demo) / Trusted Packages — Maven deps pulled from the [public Lightwell demo](https://packages.redhat.com/api/pulp-content/public-lightwell-demo/) remediated and validated catalogs instead of (or preferred over) Central.

## Build

Needs `LIGHTWELL_USERNAME` and `LIGHTWELL_TOKEN` (locally via `scripts/_creds.sh`, or GitHub Actions secrets in CI):

```bash
source scripts/_creds.sh
mvn clean install --batch-mode --settings=.m2/settings.xml
```

## Renovate

[renovate](renovate.json) can be configured to look at the Lightwell, hosts per:

<img src="renovate-config.png" alt="renovate config" width="500" />
<br>
<img src="renovate-hostrules.png" alt="renovate host rules" width="500" />

## Dependabot

If you are not using renovate, [dependabot](.github/dependabot.yml) can also provide similar functionality.

## AI skills

Skills live in [garethahealy/lightwell-skills](https://github.com/garethahealy/lightwell-skills).
This repo copies them into `.cursor/skills` (gitignored). Invoke
`/upgrade-directs`, `/upgrade-transitives`, `/verify-attestations`, and
`/add-osv-to-renovate` against this `pom.xml`.

### Local

Each run removes `.cursor/skills` and clones a fresh copy:

```bash
make skills
```

Optional ref: `make skills LIGHTWELL_SKILLS_REF=<branch-or-tag>`. Then
**Developer: Reload Window**. Open **Customize → Skills** and confirm
`/upgrade-directs`, `/upgrade-transitives`, `/verify-attestations`, and
`/add-osv-to-renovate`.

Creds stay in this repo (`scripts/_creds.sh` or exported `LIGHTWELL_USERNAME` /
`LIGHTWELL_TOKEN`).

### CI

GitHub Actions runs `make skills` and then the skill scripts against this
`pom.xml` (upgrade directs/transitives, verify attestations, OSV comments
on Renovate PRs).
