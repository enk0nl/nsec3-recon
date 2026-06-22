# NSEC3 Recon

NSEC3 Recon orchestrates AXFR checks, DNSSEC probing, NSEC/NSEC3 walking through the external `nsec3map` fork, NSEC3 hashcat target generation, and adaptive cracking through the external `nsec3-candidate-scheduler`.

## Quick start

```bash
scripts/install.sh
scripts/bootstrap.sh --skip-pcfg
nsec3-recon example.nl --dry-run
nsec3-recon example.nl
```

## Runtime model

External projects are cloned under `deps/src/` and generated data is written under `assets/`. Neither directory is committed. The workspace for each run is under `runs/<domain>-<timestamp>/` and contains events, stage outputs, scheduler config, and reports.

The default nsec3map path uses direct source invocation:

```bash
cd deps/src/nsec3map
python3 map.py --detect-only example.nl
python3 map.py --output=<workspace>/nsec3map/zone.txt example.nl
```

## Dependencies

Required Python dependencies are `dnspython` and `rich`. Runtime tools include `python3 map.py` from the cloned nsec3map fork, `python3 -m nsec3_candidate_scheduler`, and `hashcat` for the NSEC3 path. Amass and Subfinder are optional OSINT arms.
