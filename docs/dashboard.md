# Dashboard and Reports

The Rich dashboard is live status output. `events.jsonl` and `reports/` are authoritative.

## Modes

Use `--dashboard auto|rich|plain|off`:

- `auto`: Rich dashboard in interactive terminals, plain output otherwise.
- `rich`: force Rich dashboard when initialization succeeds.
- `plain`: line-based event output.
- `off`: no live event output except the final CLI summary.

`--dashboard-refresh-rate FLOAT` controls Rich redraws. The default is `2.0` refreshes per second; values must be greater than zero and are capped at 10.

## Panels

- Pipeline: stage states and current operation.
- Recent activity: compact pipeline and scheduler events.
- Last completed slice / Previous completed slice: completed scheduler jobs or slices.
- Arm statistics: per-arm runs, discoveries, reward, score, runtime, and recency.
- Discovered names: AXFR, NSEC, or NSEC3-validated names.

Scheduler slice lines are emitted after completion, so the dashboard labels scheduler panels as `Last completed slice` and `Previous completed slice`.

## Arm statistics

`Total` is total discoveries attributed to an arm, calculated as the sum of per-slice `new` values. `Last` is discoveries in that arm's latest completed slice. `R = latest reward`; `Score = latest scheduler score`. `Seen` is the last scheduler job/slice id where the arm produced a valid, scored `jobs.jsonl` record. It is a recency/debug field, not a timestamp and not a discovery, candidate, or hash count.

The scheduler line field `total` is the global discovered/cracked total and is not used as per-arm Total. warm-up slices are included in arm Total and Runs when `scheduler/jobs.jsonl` is available; stdout parsing remains a live fallback.

The jobs.jsonl mapper treats `shared_new_cracks`, `marginal_new_cracks`, and `new_cracks` as per-slice discovery fields, prefers `reward_used_for_score` for R, accepts `phase=warmup`, and treats `total_cracks`, `total`, and `total_discoveries` as global totals.

## Hash and name display

The footer includes fields such as `events=<n>`, `warnings=<n>`, `errors=<n>`, `hashes=4/4 (100.0%)`, and `parsed_slices=<n>`. Discovered-name counts are shown in the Discovered names panel.

NSEC3 progress uses cracked hashes / total hashes from `jobs.jsonl` `total_cracks` and hashcatify `hash_count`; unique discovered names are shown separately. In slice details, `18/150` is the job or slice index out of configured scheduler total slices, while `total=218` inside slice details is the global cracked-hash count.

NSEC3 cracked plaintexts are expanded to FQDNs for dashboard display and reports. An empty NSEC3 plaintext for the apex displays and reports as the zone name itself.

## Final refresh

After scheduler exit, the dashboard performs a final refresh from scheduler artifacts so completed slices, hash progress, and discovered names reflect the final persisted state.

## Reports

Review `reports/summary.json`, `reports/summary.md`, `reports/artifacts.json`, `reports/discovered_names.txt`, `reports/discovered_names.json`, and `reports/cracked_names.txt` for completed runs.
NSEC3 runs also write `nsec3_chain.tsv`, a tab-separated full-chain artifact ordered by NSEC3 hash-chain links and annotated with recovered plaintext/FQDN values where available.
