# NSEC3 Recon

NSEC3 Recon orchestrates DNS AXFR checks, DNSSEC probing, NSEC/NSEC3 walking through the external `nsec3map` fork, NSEC3 hashcat target generation, and adaptive cracking through the external `nsec3-candidate-scheduler`.

## Quick start

```bash
python3 -m pip install -e ".[test]"
scripts/bootstrap-default.sh --skip-pcfg
nsec3-recon example.nl --dry-run
nsec3-recon example.nl
```

## Boundaries

External projects are cloned under `deps/src/` and generated data is written under `assets/`. Neither directory is committed. The workspace for each run is under `runs/<domain>-<timestamp>/` and contains events, stage outputs, scheduler config, and reports.

## Dependencies

Required Python dependencies are `dnspython` and `rich`. Runtime tools include `n3map`, `n3map-hashcatify`, `python3 -m nsec3_candidate_scheduler`, and `hashcat` for the NSEC3 path. Amass and Subfinder are optional OSINT arms.

## Pipeline

The default path is AXFR, DNSSEC probe, nsec3map, NSEC short-circuit, or NSEC3 hashcatify and scheduler. `--dry-run` creates the workspace and rendered scheduler config and prints planned commands without network or external tool execution.

### Dashboard modes

Use `--dashboard auto|rich|plain|off` to choose live output. `auto` opens the Rich dashboard in an interactive terminal and otherwise uses plain console events. `rich` forces the dashboard with fallback warning if initialization fails, `plain` forces one-line event output, and `off` suppresses live event output while still writing `events.jsonl` and the final summary. The dashboard includes the target, workspace, pipeline progression, current operation, scheduler last completed and previous completed slices, arm statistics, and recovered candidates tailed from scheduler potfiles.

Scheduler slice lines are emitted after completion, so the dashboard labels those scheduler panels as `Last completed slice` and `Previous completed slice`.

Use `--dashboard-refresh-rate FLOAT` to tune the Rich dashboard redraw rate; the default is `2.0` refreshes per second to reduce terminal flicker. Values must be greater than zero and are capped at 10.
