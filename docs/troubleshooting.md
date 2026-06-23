# Troubleshooting

## ensurepip / python3-venv missing

Error:

```text
The virtual environment was not created successfully because ensurepip is not available.
```

Fix:

```bash
sudo apt update
sudo apt install python3.X-venv
```

Fallback:

```bash
sudo apt install python3-venv
```

## nsec3map editable build fails

The default pipeline does not require editable nsec3map installation. It uses direct source invocation:

```bash
cd deps/src/nsec3map
python3 map.py --detect-only example.nl
python3 map.py --output=/absolute/workspace/nsec3map/zone.txt example.nl
```

Install `python3-dev`, `gcc`/`build-essential`, `libssl-dev`, and `libssl3` only if building the optional OpenSSL-accelerated extension.

## SecLists archive missing

Expected:

```text
deps/src/SecLists/Discovery/DNS/subdomains-top1million-full.7z
```

Run `scripts/bootstrap.sh` to perform the sparse checkout for `Discovery/DNS`.

## PCFG generator missing ruleset

Expected:

```text
deps/src/pcfg-subdomain-generator/Rules/dutch_subdomains
```

Re-clone or update `deps/src/pcfg-subdomain-generator`.

## hashcat missing

Fix on Debian/Ubuntu:

```bash
sudo apt install hashcat
```

Alternatively install a local hashcat package appropriate for the target GPU/CPU environment.

## Pipeline produced little or no output

The line-based console output should show each stage as it runs. If a terminal session still appears quiet, inspect the workspace artifacts directly:

```bash
jq -r '[.ts,.stage,.event,.message] | @tsv' runs/<run>/events.jsonl
cat runs/<run>/probe/dnssec.json
cat runs/<run>/nsec3map/detect.json
cat runs/<run>/reports/summary.json
```

`events.jsonl` is authoritative for emitted pipeline events. The DNS probe is advisory only: `probe/dnssec.json` records lightweight DNSKEY/DS evidence and errors, but it does not decide whether the pipeline is allowed to run nsec3map. `nsec3map/detect.json` is the authoritative NSEC/NSEC3 routing result, and nsec3map detect-only is authoritative for NSEC/NSEC3 routing after AXFR is unavailable.

## nsec3map missing psycopg2

NSEC3 Recon uses direct `map.py` invocation by default from `deps/src/nsec3map`; editable installation is not required. The nsec3map fork imports psycopg2 through its database module, even when database output is not used.

If detect-only or enumeration fails with `ModuleNotFoundError: No module named 'psycopg2'`, install the required packages into the same interpreter used for `--nsec3map-python`:

```bash
source .venv/bin/activate
python -m pip install dnspython psycopg2-binary
.venv/bin/python -c "import dns, psycopg2, rich"
```

`psycopg2-binary` is the default recommended dependency. `libpq-dev` is optional only when building source psycopg2 manually; PostgreSQL server is not required.

## map.py fatal: unable to open output file

The error `map.py: fatal: unable to open output file` can happen when a relative output path is passed while `map.py` runs with a different cwd, such as `deps/src/nsec3map`. The pipeline now creates the nsec3map output directory first and passes absolute output paths to map.py.

For manual runs, either use absolute output paths or run from the directory where the relative path should be resolved:

```bash
cd deps/src/nsec3map
../../../.venv/bin/python map.py --output=/absolute/path/to/runs/example.nl/nsec3map/zone.txt example.nl
```

## Missing scheduler model assets

Symptoms include scheduler preflight errors for missing `prefix_pairs.tsv`, `suffix_pairs.tsv`, `common_prefixes_top10000.txt`, or `common_suffixes_top10000.txt`, or an empty `assets/models/` directory after dependency checkout.

Fix:

```bash
scripts/prepare-models.sh
# or
scripts/prepare-assets.sh
```

The model sources should exist under `deps/src/nsec3-candidate-scheduler/models/`, and prepared assets may be symlinks under `assets/models/`.

### Dashboard modes

Use `--dashboard auto|rich|plain|off` to choose live output. `auto` opens the Rich dashboard in an interactive terminal and otherwise uses plain console events. `rich` forces the dashboard with fallback warning if initialization fails, `plain` forces one-line event output, and `off` suppresses live event output while still writing `events.jsonl` and the final summary. The dashboard includes the target, workspace, pipeline progression, current operation, scheduler last completed and previous completed slices, arm statistics, and discovered names tailed from scheduler potfiles.

Scheduler slice lines are emitted after completion, so the dashboard labels those scheduler panels as `Last completed slice` and `Previous completed slice`.

Use `--dashboard-refresh-rate FLOAT` to tune the Rich dashboard redraw rate; the default is `2.0` refreshes per second to reduce terminal flicker. Values must be greater than zero and are capped at 10.

Discovered names are outputs found by AXFR zone transfer, NSEC walking, or NSEC3 hashcat potfile cracking; scheduler candidates remain inputs until validated or cracked. The Arm statistics table uses `Total` for total discoveries attributed to an arm (the sum of per-slice `new` values), `Last` for discoveries in the arm's latest completed slice, `R = latest reward`, `Score = latest scheduler score`, and `Seen` for the last completed slice index where the arm ran. The scheduler line field `total` is the global discovered/cracked total and is not used as the per-arm Total.

Dashboard scheduler aggregation prefers `scheduler/jobs.jsonl` when available so warm-up slices are included in arm Total and Runs; stdout parsing remains a live fallback. Discovered names rows display only timestamp and name, with source summarized in the panel footer.

The jobs.jsonl mapper treats `shared_new_cracks`, `marginal_new_cracks`, and `new_cracks` as per-slice discovery fields, prefers `reward_used_for_score` for R, accepts `phase=warmup`, and treats `total_cracks`/`total`/`total_discoveries` as global totals. Discovered-name logical sources are `axfr`, `nsec`, and `nsec3`; `run.pot` is an artifact file, not a discovery source label.

Last/Previous completed slice panels show completed scheduler jobs/slices: `18/150` is the job or slice index out of configured scheduler total slices, while `total=218` inside slice details is the global cracked-hash count. NSEC3 progress uses cracked hashes / total hashes from jobs.jsonl `total_cracks` and hashcatify `hash_count`; unique discovered names are shown separately.

## Production/beta troubleshooting

If a run fails, inspect `events.jsonl`, `logs/listener_errors.log` for dashboard/listener failures, `reports/summary.json`, and `reports/artifacts.json`. Scheduler asset preflight errors intentionally list every missing or empty enabled-arm asset before launching the scheduler. Use `--disable-osint` if Amass/Subfinder are not installed or external OSINT access is not authorized.
