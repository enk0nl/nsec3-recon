# NSEC3 Recon

NSEC3 Recon orchestrates DNS AXFR checks, DNSSEC probing, NSEC/NSEC3 walking through the external `nsec3map` fork, NSEC3 hashcat target generation, and adaptive cracking through the external `nsec3-candidate-scheduler`.

## Quick start

```bash
scripts/install.sh
source .venv/bin/activate
nsec3-recon example.nl --dry-run
nsec3-recon example.nl
```


## Default namespace scope

The default configuration is tuned for Dutch domains and the `.nl` namespace. It uses Dutch DNS wordlists, OpenTaal Dutch wordlists, and default generator assets selected for `.nl` naming patterns. The NSEC3 extraction and validation pipeline is generic, but results outside the Dutch namespace depend on replacing or extending the candidate sources and scheduler configuration.

## Boundaries

External projects are cloned under `deps/src/` and generated data is written under `assets/`. Neither directory is committed. The workspace for each run is under `runs/<domain>-<timestamp>/` and contains events, stage outputs, scheduler config, and reports.

## Dependencies

Required Python dependencies are `dnspython` and `rich`. Runtime tools include `n3map`, `n3map-hashcatify`, `python3 -m nsec3_candidate_scheduler`, and `hashcat` for the NSEC3 path. Amass and Subfinder are optional OSINT arms.

## Pipeline

The default path is AXFR, DNSSEC probe, nsec3map, NSEC short-circuit, or NSEC3 hashcatify and scheduler. `--dry-run` creates the workspace and rendered scheduler config and prints planned commands without network or external tool execution.

### Dashboard modes

Use `--dashboard auto|rich|plain|off` to choose live output. `auto` opens the Rich dashboard in an interactive terminal and otherwise uses plain console events. `rich` forces the dashboard with fallback warning if initialization fails, `plain` forces one-line event output, and `off` suppresses live event output while still writing `events.jsonl` and the final summary. The dashboard includes the target, workspace, pipeline progression, current operation, scheduler last completed and previous completed slices, arm statistics, and discovered names tailed from scheduler potfiles.

Scheduler slice lines are emitted after completion, so the dashboard labels those scheduler panels as `Last completed slice` and `Previous completed slice`.

Use `--dashboard-refresh-rate FLOAT` to tune the Rich dashboard redraw rate; the default is `2.0` refreshes per second to reduce terminal flicker. Values must be greater than zero and are capped at 10.

Discovered names are outputs found by AXFR zone transfer, NSEC walking, or NSEC3 hashcat potfile cracking; scheduler candidates remain inputs until validated or cracked. The Arm statistics table uses `Total` for total discoveries attributed to an arm (the sum of per-slice `new` values), `Last` for discoveries in the arm's latest completed slice, `R = latest reward`, `Score = latest scheduler score`, and `Seen` for the last scheduler job/slice id where the arm produced a valid, scored `jobs.jsonl` record. `Seen` is a recency/debug field, not a timestamp and not a discovery, candidate, or hash count. The scheduler line field `total` is the global discovered/cracked total and is not used as the per-arm Total.

Dashboard scheduler aggregation prefers `scheduler/jobs.jsonl` when available so warm-up slices are included in arm Total and Runs; stdout parsing remains a live fallback. Discovered names rows display only timestamp and name, with source summarized in the panel footer.

The jobs.jsonl mapper treats `shared_new_cracks`, `marginal_new_cracks`, and `new_cracks` as per-slice discovery fields, prefers `reward_used_for_score` for R, accepts `phase=warmup`, and treats `total_cracks`/`total`/`total_discoveries` as global totals. Discovered-name logical sources are `axfr`, `nsec`, and `nsec3`; `run.pot` is an artifact file, not a discovery source label.

Last/Previous completed slice panels show completed scheduler jobs/slices: `18/150` is the job or slice index out of configured scheduler total slices, while `total=218` inside slice details is the global cracked-hash count. NSEC3 progress uses cracked hashes / total hashes from jobs.jsonl `total_cracks` and hashcatify `hash_count`; unique discovered names are shown separately.

### nsec3map hash collection limit

Use `--nsec3map-hashlimit INT` to pass `--hashlimit` to nsec3map during NSEC3 enumeration. The default is `0`, which means no explicit limit. Use a positive value for short test runs, demos, or bounded experiments; use the default `0` for normal runs.

```bash
nsec3-recon example.nl
nsec3-recon example.nl --nsec3map-hashlimit 0
nsec3-recon example.nl --nsec3map-hashlimit 10000
```

## Production/beta controls

Relevant hardening flags include `--disable-osint`, `--dns-timeout`, `--dns-lifetime`, and `--axfr-timeout`. Report artifacts are authoritative even when `--dashboard off` is used or the Rich dashboard fails. The dependency manifest is written to `config/dependency_manifest.json` and referenced from `reports/summary.json`.

## Hashcat optimized-kernel controls

NSEC3 Recon exposes `--hashcat-optimized-kernels` / `--no-hashcat-optimized-kernels` and `--hashcat-optimized-kernel-failover` / `--no-hashcat-optimized-kernel-failover`. Optimized kernels and automatic failover are enabled by default. The rendered scheduler config always includes top-level `hashcat.optimized_kernels` and `hashcat.optimized_kernel_failover`; when disabled, the scheduler command also receives `--no-optimized-kernels` and/or `--no-optimized-kernel-failover`.
