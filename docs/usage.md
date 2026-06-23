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
