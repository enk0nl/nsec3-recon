# NSEC3 Recon

NSEC3 Recon orchestrates AXFR checks, DNSSEC probing, NSEC/NSEC3 walking through the external `nsec3map` fork, NSEC3 hashcat target generation, and adaptive cracking through the external `nsec3-candidate-scheduler`.

## Quick start with virtualenv activation

```bash
scripts/install.sh
source .venv/bin/activate
nsec3-recon --help
nsec3-recon example.nl --dry-run
nsec3-recon example.nl
```

## Quick start without activating the virtualenv

```bash
scripts/install.sh
.venv/bin/nsec3-recon --help
.venv/bin/nsec3-recon example.nl --dry-run
.venv/bin/nsec3-recon example.nl
```

`scripts/install.sh` is the user-facing setup entrypoint and normally calls `scripts/bootstrap.sh` for dependency cloning and asset preparation. You do not need to run both back-to-back unless you are doing an advanced workflow and intentionally calling the lower-level bootstrap helper yourself.


## Default namespace scope

The default configuration is tuned for Dutch domains and the `.nl` namespace. It uses Dutch DNS wordlists, OpenTaal Dutch wordlists, and default generator assets selected for `.nl` naming patterns. The NSEC3 extraction and validation pipeline is generic, but results outside the Dutch namespace depend on replacing or extending the candidate sources and scheduler configuration.

## Runtime model

External projects are cloned under `deps/src/` and generated data is written under `assets/`. Neither directory is committed. The workspace for each run is under `runs/<domain>-<timestamp>/` and contains events, stage outputs, scheduler config, and reports.

The default nsec3map path uses direct source invocation:

```bash
cd deps/src/nsec3map
python3 map.py --detect-only example.nl
python3 map.py --output=<workspace>/nsec3map/zone.txt example.nl
```

### nsec3map hash collection limit

Use `--nsec3map-hashlimit INT` to pass `--hashlimit` to nsec3map during NSEC3 enumeration. The default is `0`, which means no explicit limit. Use a positive value for short test runs, demos, or bounded experiments; use the default `0` for normal runs.

```bash
nsec3-recon example.nl
nsec3-recon example.nl --nsec3map-hashlimit 0
nsec3-recon example.nl --nsec3map-hashlimit 10000
```

## Dependencies

Required Python dependencies are `dnspython` and `rich`. Runtime tools include `python3 map.py` from the cloned nsec3map fork, `python3 -m nsec3_candidate_scheduler`, and `hashcat` for the NSEC3 path. Amass and Subfinder are optional OSINT arms.

### Dashboard modes

`nsec3-recon` supports `--dashboard auto|rich|plain|off`. The default `auto` uses the Rich live dashboard in interactive terminals when Rich is available and falls back to plain one-line console events for non-TTY output. Use `--dashboard rich` to force the terminal dashboard, `--dashboard plain` for line-based event output, and `--dashboard off` to suppress live UI output except the final CLI summary. `events.jsonl` is always written. During scheduler execution the Rich dashboard shows pipeline stages, last completed and previous completed scheduler slices, arm statistics, and discovered names tailed from the scheduler potfile when available.

Scheduler slice lines are emitted after completion, so the dashboard labels those scheduler panels as `Last completed slice` and `Previous completed slice`.

Use `--dashboard-refresh-rate FLOAT` to tune the Rich dashboard redraw rate; the default is `2.0` refreshes per second to reduce terminal flicker. Values must be greater than zero and are capped at 10.

Discovered names are outputs found by AXFR zone transfer, NSEC walking, or NSEC3 hashcat potfile cracking; scheduler candidates remain inputs until validated or cracked. The Arm statistics table uses `Total` for total discoveries attributed to an arm (the sum of per-slice `new` values), `Last` for discoveries in the arm's latest completed slice, `R = latest reward`, `Score = latest scheduler score`, and `Seen` for the last scheduler job/slice id where the arm produced a valid, scored `jobs.jsonl` record. `Seen` is a recency/debug field, not a timestamp and not a discovery, candidate, or hash count. The scheduler line field `total` is the global discovered/cracked total and is not used as the per-arm Total.

Dashboard scheduler aggregation prefers `scheduler/jobs.jsonl` when available so warm-up slices are included in arm Total and Runs; stdout parsing remains a live fallback. Discovered names rows display only timestamp and name, with source summarized in the panel footer. NSEC3 cracked plaintexts are expanded to fully qualified names for dashboard display and reports; the empty plaintext apex is reported as the zone name itself, keeping AXFR, NSEC, and NSEC3 outputs consistent.

The jobs.jsonl mapper treats `shared_new_cracks`, `marginal_new_cracks`, and `new_cracks` as per-slice discovery fields, prefers `reward_used_for_score` for R, accepts `phase=warmup`, and treats `total_cracks`/`total`/`total_discoveries` as global totals. Discovered-name logical sources are `axfr`, `nsec`, and `nsec3`; `run.pot` is an artifact file, not a discovery source label.

Last/Previous completed slice panels show completed scheduler jobs/slices: `18/150` is the job or slice index out of configured scheduler total slices, while `total=218` inside slice details is the global cracked-hash count. NSEC3 progress uses cracked hashes / total hashes from jobs.jsonl `total_cracks` and hashcatify `hash_count`; unique discovered names are shown separately.

## Production/beta hardening notes

**Authorized use only.** Run NSEC3 Recon only for domains you own or are explicitly authorized to test. NSEC3 cracking can reveal internal hostnames, OSINT tools may contact external services, and hashcat can be resource intensive.

For deterministic installs, `scripts/bootstrap.sh` uses pinned Git refs by default and allows environment overrides: `NSEC3MAP_REF=5af04b9c900b8f0f1a2113a22f5b34e67e637c80`, `SCHEDULER_REF=cde74dbbccc641161846a9ccabf81551c3d586c1`, `PCFG_REF=171f89e85206cb22e89c3803c13f6a320d538e8b`, `SECLISTS_REF=198047f1e22251e3b88b98b10e8bd15283e8a1e9`, `OPENTAAL_REF=b250510dda431785f962019167d1415198ff3905`, and `DUTCH_DNS_WORDLISTS_REF=87403dff13f2a9da53084c88412a6e19280003ec`.

Binary dependencies are validated by minimum supported versions, not exact local versions: Python >= the `requires-python` value, Go >= 1.24.0 for Go-tool installation, hashcat >= 7.1.2, Amass >= 5.1.1, and Subfinder >= 2.14.0. Use `--disable-osint` to disable Amass/Subfinder scheduler arms; OSINT candidates are not reported as validated discoveries unless later cracked or confirmed.

Unattended runs always write `events.jsonl`, `config/run.json`, `config/dependency_manifest.json`, and report artifacts under `reports/`, including `summary.json`, `summary.md`, `artifacts.json`, `cracked_names.txt`, `discovered_names.txt`, and `discovered_names.json` when applicable. The Rich dashboard is observational only; report artifacts are authoritative.

DNS timeout options are available with `--dns-timeout`, `--dns-lifetime`, and `--axfr-timeout`. Development checks can be run with `python -m pytest -m "not slow and not integration"`, `python -m pytest`, `python -m ruff format --check .`, and `python -m ruff check .`.

### Hashcat optimized kernels

Optimized kernels are enabled by default, and automatic optimized-kernel failover is enabled by default. If hashcat hits an optimized-kernel-specific failure, the updated scheduler retries the failed slice once with unoptimized kernels and continues unoptimized. Use `--no-hashcat-optimized-kernels` to start unoptimized, `--hashcat-optimized-kernel-failover` to request the default automatic failover policy, or `--no-hashcat-optimized-kernel-failover` to keep optimized kernels enabled even after optimized-kernel-specific failures. `scheduler/jobs.jsonl` records observed scheduler behavior, `reports/summary.json` records requested and observed optimized-kernel state, and the dashboard shows compact failover/no-failover Recent activity messages.
