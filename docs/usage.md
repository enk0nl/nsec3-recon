# Usage

```bash
nsec3-recon example.nl
nsec3-recon example.nl --dry-run
```

Dry run creates a workspace, renders `config/scheduler_config.json`, and prints direct `python3 map.py` commands without running network stages.

### Dashboard modes

Use `--dashboard auto|rich|plain|off` to choose live output. `auto` opens the Rich dashboard in an interactive terminal and otherwise uses plain console events. `rich` forces the dashboard with fallback warning if initialization fails, `plain` forces one-line event output, and `off` suppresses live event output while still writing `events.jsonl` and the final summary. The dashboard includes the target, workspace, pipeline progression, current operation, scheduler last completed and previous completed slices, arm statistics, and discovered names tailed from scheduler potfiles.

Scheduler slice lines are emitted after completion, so the dashboard labels those scheduler panels as `Last completed slice` and `Previous completed slice`.

Use `--dashboard-refresh-rate FLOAT` to tune the Rich dashboard redraw rate; the default is `2.0` refreshes per second to reduce terminal flicker. Values must be greater than zero and are capped at 10.

Discovered names are outputs found by AXFR zone transfer, NSEC walking, or NSEC3 hashcat potfile cracking; scheduler candidates remain inputs until validated or cracked. The Arm statistics table uses `Total` for total discoveries attributed to an arm (the sum of per-slice `new` values), `Last` for discoveries in the arm's latest completed slice, `R = latest reward`, `Score = latest scheduler score`, and `Seen` for the last completed slice index where the arm ran. The scheduler line field `total` is the global discovered/cracked total and is not used as the per-arm Total.

Dashboard scheduler aggregation prefers `scheduler/jobs.jsonl` when available so warm-up slices are included in arm Total and Runs; stdout parsing remains a live fallback. Discovered names rows display only timestamp and name, with source summarized in the panel footer.

The jobs.jsonl mapper treats `shared_new_cracks`, `marginal_new_cracks`, and `new_cracks` as per-slice discovery fields, prefers `reward_used_for_score` for R, accepts `phase=warmup`, and treats `total_cracks`/`total`/`total_discoveries` as global totals. Discovered-name logical sources are `axfr`, `nsec`, and `nsec3`; `run.pot` is an artifact file, not a discovery source label.

Last/Previous completed slice panels show completed scheduler jobs/slices: `18/150` is the job or slice index out of configured scheduler total slices, while `total=218` inside slice details is the global cracked-hash count. NSEC3 progress uses cracked hashes / total hashes from jobs.jsonl `total_cracks` and hashcatify `hash_count`; unique discovered names are shown separately.

## Safety, OSINT, and reports

Use this tool only for domains you own or are authorized to test. NSEC3 cracking can disclose internal hostnames, hashcat can consume substantial compute resources, and OSINT arms may contact external services. Use `--disable-osint` to render scheduler OSINT arms disabled and avoid requiring Amass/Subfinder.

The dashboard is not authoritative. For unattended runs, review `events.jsonl`, `reports/summary.json`, `reports/summary.md`, `reports/artifacts.json`, and discovered/cracked-name files in `reports/`. DNS behavior can be bounded with `--dns-timeout`, `--dns-lifetime`, and `--axfr-timeout`.

## Hashcat optimized kernels and failover

By default, NSEC3 Recon starts the scheduler with hashcat optimized kernels enabled and optimized-kernel failover enabled:

```sh
nsec3-recon example.nl
```

Use `--no-hashcat-optimized-kernels` to start scheduler/hashcat without optimized kernels. This is slower, but more compatible with long or problematic candidates:

```sh
nsec3-recon example.nl --no-hashcat-optimized-kernels
```

Use `--hashcat-optimized-kernel-failover` to allow automatic scheduler failover from optimized to unoptimized kernels; this is the default. If an optimized-kernel-specific hashcat failure occurs, the scheduler retries the failed slice once unoptimized and continues unoptimized. Use `--no-hashcat-optimized-kernel-failover` to keep optimized kernels enabled even after optimized-kernel-specific failures, which can be useful when the operator prefers speed and accepts some failed candidate sets:

```sh
nsec3-recon example.nl --no-hashcat-optimized-kernel-failover
nsec3-recon example.nl --no-hashcat-optimized-kernels --no-hashcat-optimized-kernel-failover
```

The dashboard Recent activity panel shows compact failover or no-failover messages from `scheduler/jobs.jsonl`. Reports include requested and observed optimized-kernel state in `reports/summary.json`.
