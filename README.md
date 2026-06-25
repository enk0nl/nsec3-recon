# NSEC3 Recon

NSEC3 Recon is a CLI pipeline for DNSSEC-aware zone enumeration and NSEC3 hash-recovery workflows. It tries AXFR first, handles NSEC zones directly, and collects and cracks NSEC3 hashes with hashcat-backed candidate scheduling for NSEC3 zones.

![NSEC3 Recon screenshot](docs/screen.png?raw=true)


## Problem

NSEC3 protects zone walking by returning hashed owner names instead of cleartext names. Recovering names requires collecting the NSEC3 hash set, generating plausible DNS name candidates, and testing those candidates against the hashes. NSEC3 Recon automates collection, candidate generation, hashcat cracking, scheduling, dashboarding, and reporting into one reproducible run.

## What it does

- Tries AXFR before DNSSEC-specific enumeration.
- Detects the DNSSEC mode for the target zone.
- Walks and reports names directly when the zone uses NSEC.
- Collects and cracks NSEC3 hashes when the zone uses NSEC3.
- Writes reports and run artifacts under `runs/`.

## Features

- One-command pipeline: `nsec3-recon <domain>`.
- AXFR attempt before DNSSEC-specific enumeration.
- Authoritative DNSSEC mode detection.
- NSEC zone walking when the zone uses NSEC.
- NSEC3 hash collection and cracking with hashcat.
- Adaptive hashcat scheduler for fixed-time candidate runs.
- PCFG-generated DNS candidate names.
- Dictionary and brute-force candidate sources for DNS-like labels.
- Feedback candidate sources derived from recovered names.
- Optional OSINT candidate sources via Subfinder and Amass.
- Rich terminal dashboard.
- Final reports with fully qualified discovered names across AXFR, NSEC, and NSEC3.
- Reproducible run directories.

## Installation

```bash
scripts/install.sh
source .venv/bin/activate
```

`scripts/install.sh` calls `scripts/bootstrap.sh`; users should normally run the installer, not both scripts manually.

[Installation details](docs/installation.md)

## Quickstart

```bash
nsec3-recon example.nl --dry-run
nsec3-recon example.nl
```

Run artifacts are written under `runs/`.

[Usage guide](docs/usage.md)

## Output

Each run creates a timestamped workspace under `runs/` with events, rendered configuration, stage outputs, scheduler files, and reports. The main review files are `reports/summary.json`, `reports/summary.md`, `reports/artifacts.json`, and discovered/cracked-name reports when available.

## Default candidate configuration

The default configuration is tuned for Dutch domains and the `.nl` namespace. It uses Dutch DNS wordlists, OpenTaal Dutch, and PCFG/default generator assets derived from Dutch DNS naming patterns. The pipeline itself is not limited to `.nl`, but other namespaces should use adjusted candidate sources and scheduler configuration.

## Documentation

- [Installation details](docs/installation.md)
- [Usage guide](docs/usage.md)
- [Configuration reference](docs/configuration.md)
- [Architecture and workflow](docs/architecture.md)
- [Dashboard and reports](docs/dashboard.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Dependency details](docs/dependencies.md)
- [Pipeline notes](docs/pipeline.md)
- [Contribution guidelines for this project](docs/CONTRIBUTING.md)

## Related repositories

- [nsec3-candidate-scheduler](https://github.com/enk0nl/nsec3-candidate-scheduler): scheduler for hashcat-backed NSEC3 candidate sources.
- [nsec3map fork](https://github.com/enk0nl/nsec3map): NSEC/NSEC3 walking and detection source used by this pipeline.
- [pcfg-subdomain-generator](https://github.com/enk0nl/pcfg-subdomain-generator): PCFG DNS label generator.
- [dutch-dns-wordlists](https://github.com/enk0nl/dutch-dns-wordlists): Dutch DNS wordlist source.
- [OpenTaal wordlist](https://github.com/OpenTaal/opentaal-wordlist): Dutch language wordlist source.
- [SecLists](https://github.com/danielmiessler/SecLists): DNS discovery wordlist source.
