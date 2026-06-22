# NSEC3 Recon

NSEC3 Recon orchestrates DNS AXFR checks, DNSSEC probing, NSEC/NSEC3 walking through the external `nsec3map` fork, NSEC3 hashcat target generation, and adaptive cracking through the external `nsec3-candidate-scheduler`.

## Quick start

```bash
python3 -m pip install -e ".[test]"
scripts/bootstrap-default.sh --skip-pcfg
nsec3-recon example.nl --dry-run
nsec3-recon example.nl
```

## Boundaries

External projects are cloned under `deps/src/` and generated data is written under `assets/`. Neither directory is committed. The workspace for each run is under `runs/<domain>-<timestamp>/` and contains events, stage outputs, scheduler config, and reports.

## Dependencies

Required Python dependencies are `dnspython` and `rich`. Runtime tools include `n3map`, `n3map-hashcatify`, `python3 -m nsec3_candidate_scheduler`, and `hashcat` for the NSEC3 path. Amass and Subfinder are optional OSINT arms.

## Pipeline

The default path is AXFR, DNSSEC probe, nsec3map, NSEC short-circuit, or NSEC3 hashcatify and scheduler. `--dry-run` creates the workspace and rendered scheduler config and prints planned commands without network or external tool execution.

## DNSSEC routing authority

The DNS probe is advisory and records DNSKEY/DS evidence for troubleshooting. It is intentionally not terminal truth. After AXFR is unavailable, `nsec3map` detect-only is authoritative for NSEC/NSEC3 routing, so a false-negative DNS probe does not prevent NSEC or NSEC3 enumeration.
