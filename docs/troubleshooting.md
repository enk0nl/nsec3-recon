# Troubleshooting

## ensurepip or python3-venv missing

Symptom: `.venv` creation fails because `ensurepip` is unavailable.

Fix:

```bash
PYVER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
sudo apt install -y python${PYVER}-venv
```

Fallback:

```bash
sudo apt install -y python3-venv
```

## hashcat missing or too old

Symptom: preflight reports missing hashcat or a version below `hashcat >= 7.1.2`.

Fix: install a package appropriate for the CPU/GPU environment and verify with:

```bash
hashcat --version
scripts/check-tools.sh
```

Apt repositories may provide hashcat older than 7.1.2.

## Missing Go OSINT tools

Symptom: Amass or Subfinder arms fail preflight.

Fix:

```bash
CGO_ENABLED=0 go install -v github.com/owasp-amass/amass/v5/cmd/amass@main
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
amass -version
subfinder -version
```

Use `--disable-osint` if OSINT tools are unavailable or OSINT traffic is not authorized.

## nsec3map imports psycopg2

Symptom: `ModuleNotFoundError: No module named 'psycopg2'` during detect-only or enumeration.

Cause: nsec3map imports `psycopg2` even when database output is not used. Direct `map.py` invocation is default; editable installation is not required.

Fix:

```bash
source .venv/bin/activate
python -m pip install psycopg2-binary
```

## map.py fatal: unable to open output file

Symptom: `map.py: fatal: unable to open output file`.

Cause: a relative output path was resolved from the `map.py` cwd, often `deps/src/nsec3map`.

Fix: use absolute output paths for manual nsec3map runs. The pipeline creates output directories first and passes absolute output paths.

```bash
cd deps/src/nsec3map
../../../.venv/bin/python map.py --output=/absolute/path/to/runs/example/nsec3map/zone.txt --hashlimit=0 example.nl
```

## Missing scheduler model assets

Symptom: scheduler preflight reports missing `prefix_pairs.tsv`, `suffix_pairs.tsv`, `common_prefixes_top10000.txt`, or `common_suffixes_top10000.txt`.

Fix:

```bash
scripts/prepare-models.sh
# or
scripts/prepare-assets.sh
```

The source files should exist under `deps/src/nsec3-candidate-scheduler/models`; prepared files appear under `assets/models`.

## Missing PCFG assets or use of --skip-pcfg

Symptom: scheduler preflight reports missing PCFG files or the PCFG arm is unavailable.

Cause: `--skip-pcfg` was used during install/bootstrap. Use `--skip-pcfg` only for development, CI shortcuts, or debugging flows that do not require the PCFG generator.

Fix:

```bash
scripts/prepare-assets.sh
```

## Optimized-kernel compatibility

Symptom: hashcat rejects a slice only when optimized kernels are enabled.

Fix: keep the default optimized-kernel failover enabled, or start unoptimized:

```bash
nsec3-recon example.nl --no-hashcat-optimized-kernels
```

With failover enabled, the scheduler retries the failed slice once with unoptimized kernels and continues unoptimized.

## Scheduler stops before configured slice count

Symptom: the scheduler exits after all hashes are cracked.

Cause: completion after all target hashes are cracked is expected, even if configured slices remain.

Check:

```bash
tail -n 20 runs/<run>/scheduler/jobs.jsonl
cat runs/<run>/reports/summary.json
```

## No hashes loaded

Symptom: hash progress remains `hashes=0/?` or hashcat reports malformed input.

Cause: the NSEC3 hashfile is missing, empty, or not in hashcat mode 8300 format.

Check:

```bash
wc -l runs/<run>/hashcat/*.hashes 2>/dev/null || true
cat runs/<run>/events.jsonl | jq -r 'select(.stage=="hashcatify")'
```

## No discoveries after scheduler starts

Symptom: scheduler slices run but no new discovered names appear.

Cause: candidates are inputs; only AXFR, NSEC walking, or NSEC3 hashcat cracking creates discovered names.

Check:

```bash
tail -n 20 runs/<run>/scheduler/jobs.jsonl
```

## pytest collects dependency tests

Symptom: pytest enters `deps/`, including dependency tests such as `deps/src/pcfg-subdomain-generator/lib_trainer/unit_tests/`.

Fix: run project tests explicitly:

```bash
pytest tests
```

The project pytest configuration also restricts discovery to `tests`.

## Poor results outside Dutch domains

Symptom: few productive candidates on a non-Dutch domain.

Cause: default candidate sources are tuned for Dutch DNS naming patterns and the `.nl` namespace.

Fix: add namespace-specific wordlists/generators and adjust scheduler configuration. See [Configuration reference](configuration.md).
