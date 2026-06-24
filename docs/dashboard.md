# Dashboard

The Rich dashboard is live status output. Report files under `reports/` and `events.jsonl` are authoritative.

## Footer/status line

The footer contains:

- `events=<n>`: pipeline events processed by the dashboard.
- `warnings=<n>` and `errors=<n>`: warning and error event counts.
- `hashes=<cracked>/<total> (<pct>%)`: NSEC3 hash cracking progress. Unknown totals render as `?`.
- `parsed_slices=<n>`: completed scheduler slices parsed into dashboard state.

Discovered-name counts are shown in the Discovered names panel, not in the footer.

## Panels

- Pipeline: current stage states.
- Recent activity: compact event and scheduler messages.
- Last completed slice / Previous completed slice: completed scheduler jobs or slices.
- Arm statistics: per-arm runs, discoveries, reward, score, average runtime, and recency.
- Discovered names: AXFR, NSEC, or NSEC3-validated names with `total=<n>` in the panel subtitle. The zone apex is displayed as `@` when hashcat cracks an empty plaintext value from the potfile; it counts toward the panel total and hash progress as a cracked hash.

`Seen` is the last scheduler job/slice id where the arm produced a valid, scored `jobs.jsonl` record. It is a recency/debug field, not a timestamp and not a discovery, candidate, or hash count.
