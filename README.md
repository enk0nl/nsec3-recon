# NSEC3 Recon

NSEC3 Recon orchestrates AXFR checks, DNSSEC probing, NSEC/NSEC3 walking through the external `nsec3map` fork, NSEC3 hashcat target generation, and adaptive cracking through the external `nsec3-candidate-scheduler`.

## Quick start with virtualenv activation

```bash
scripts/install.sh --skip-pcfg
source .venv/bin/activate
nsec3-recon --help
nsec3-recon example.nl --dry-run
nsec3-recon example.nl
```

## Quick start without activating the virtualenv

```bash
scripts/install.sh --skip-pcfg
.venv/bin/nsec3-recon --help
.venv/bin/nsec3-recon example.nl --dry-run
.venv/bin/nsec3-recon example.nl
```

`scripts/install.sh` is the user-facing setup entrypoint and normally calls `scripts/bootstrap.sh` for dependency cloning and asset preparation. You do not need to run both back-to-back unless you are doing an advanced workflow and intentionally calling the lower-level bootstrap helper yourself.

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
