# Usage

## Basic commands

```bash
nsec3-recon example.nl --dry-run
nsec3-recon example.nl
```

`--dry-run` creates a workspace, renders `config/scheduler_config.json`, and prints planned commands without running network stages or external cracking.

## Common options

```bash
nsec3-recon example.nl --disable-osint
nsec3-recon example.nl --dashboard auto
nsec3-recon example.nl --dashboard plain
nsec3-recon example.nl --nsec3map-hashlimit 10000
nsec3-recon example.nl --dns-timeout 3 --dns-lifetime 10 --axfr-timeout 10
```

`--nsec3map-hashlimit INT` passes `--hashlimit` to nsec3map during NSEC3 enumeration. The default is `0`, meaning no explicit limit. Positive values are useful for bounded tests or demos.

## Output layout

Each run writes a self-contained workspace under `runs/<domain>-<timestamp>/`:

```text
events.jsonl
config/run.json
config/scheduler_config.json
config/dependency_manifest.json
reports/summary.json
reports/summary.md
reports/artifacts.json
reports/discovered_names.txt
reports/discovered_names.json
reports/cracked_names.txt
```

`events.jsonl` and files under `reports/` are authoritative for review. Dashboard output is live status only.

## Discovery terminology

Discovered names are AXFR/NSEC/NSEC3-validated outputs. Scheduler candidates, dictionary entries, PCFG guesses, brute-force guesses, and OSINT returns are inputs until a transfer, walk, or hashcat validation confirms them.

Logical discovery sources are `axfr`, `nsec`, and `nsec3`; `run.pot` is an artifact file, not a discovery source label.

## Dashboard selection

`--dashboard auto|rich|plain|off` controls live output. `auto` uses Rich in an interactive terminal and plain line output otherwise. `off` suppresses live event output except the final CLI summary while still writing artifacts.

See [Dashboard and reports](dashboard.md) for panel and footer details.
