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
