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

Discovered names are outputs found by AXFR zone transfer, NSEC walking, or NSEC3 hashcat potfile cracking; scheduler candidates remain inputs until validated or cracked. The Arm statistics table uses `New` for total new discoveries, `Last` for discoveries in the arm's last completed run, `R = latest reward`, `Score = latest scheduler score`, and `Seen` for the last slice index where the arm ran.
