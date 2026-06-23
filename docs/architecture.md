# NSEC3 Recon

NSEC3 Recon orchestrates DNS AXFR checks, DNSSEC probing, NSEC/NSEC3 walking through the external `nsec3map` fork, NSEC3 hashcat target generation, and adaptive cracking through the external `nsec3-candidate-scheduler`.

## Quick start

```bash
python3 -m pip install -e ".[test]"
scripts/install.sh
nsec3-recon example.nl --dry-run
nsec3-recon example.nl
```

## Default namespace scope

The default configuration is tuned for Dutch domains and the `.nl` namespace. It uses Dutch DNS wordlists, OpenTaal Dutch wordlists, and default generator assets selected for `.nl` naming patterns. The NSEC3 extraction and validation pipeline is generic, but results outside the Dutch namespace depend on replacing or extending the candidate sources and scheduler configuration.

## Boundaries

External projects are cloned under `deps/src/` and generated data is written under `assets/`. Neither directory is committed. The workspace for each run is under `runs/<domain>-<timestamp>/` and contains events, stage outputs, scheduler config, and reports.

## Dependencies

Required Python dependencies are `dnspython` and `rich`. Runtime tools include `n3map`, `n3map-hashcatify`, `python3 -m nsec3_candidate_scheduler`, and `hashcat` for the NSEC3 path. Amass and Subfinder are optional OSINT arms.

## Pipeline

The default path is AXFR, DNSSEC probe, nsec3map, NSEC short-circuit, or NSEC3 hashcatify and scheduler. `--dry-run` creates the workspace and rendered scheduler config and prints planned commands without network or external tool execution.

Dashboard scheduler aggregation prefers `scheduler/jobs.jsonl` when available so warm-up slices are included in arm Total and Runs; stdout parsing remains a live fallback. Discovered names rows display only timestamp and name, with source summarized in the panel footer.

The jobs.jsonl mapper treats `shared_new_cracks`, `marginal_new_cracks`, and `new_cracks` as per-slice discovery fields, prefers `reward_used_for_score` for R, accepts `phase=warmup`, and treats `total_cracks`/`total`/`total_discoveries` as global totals. Discovered-name logical sources are `axfr`, `nsec`, and `nsec3`; `run.pot` is an artifact file, not a discovery source label.

Last/Previous completed slice panels show completed scheduler jobs/slices: `18/150` is the job or slice index out of configured scheduler total slices, while `total=218` inside slice details is the global cracked-hash count. NSEC3 progress uses cracked hashes / total hashes from jobs.jsonl `total_cracks` and hashcatify `hash_count`; unique discovered names are shown separately.
