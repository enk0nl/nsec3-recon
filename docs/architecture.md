# Architecture and Workflow

NSEC3 Recon is an orchestrator. It owns workspace creation, stage ordering, event capture, scheduler configuration rendering, dashboard updates, and report generation. External tools perform NSEC/NSEC3 walking, candidate generation, OSINT collection, and hashcat cracking.

## Pipeline

```text
input domain
  -> workspace under runs/<domain>-<timestamp>/
  -> AXFR attempt
  -> DNSSEC probe
  -> nsec3map detect-only
  -> NSEC walk OR NSEC3 walk
  -> hashcat-compatible mode 8300 targets
  -> scheduler/hashcat fixed-time cracking slices
  -> reports and artifacts
```

The DNS probe is advisory. It records DNSKEY/DS evidence and errors for troubleshooting. After AXFR is unavailable, nsec3map detect-only is authoritative for NSEC/NSEC3 routing.

## Branches

- AXFR: successful zone transfer is reported as discovered names and avoids unnecessary DNSSEC walking.
- NSEC: `nsec3map` walks the zone and discovered names are reported directly.
- NSEC3: `nsec3map` collects hashes, `hashcatify` writes hashcat-compatible mode 8300 inputs, and the scheduler runs candidate arms until configured limits or all hashes are cracked.

## NSEC3 handoff

NSEC3 hash material is written under the run workspace, converted to hashcat mode 8300, and consumed by `python3 -m nsec3_candidate_scheduler`. A slice is one bounded hashcat run for one candidate source. The scheduler coordinates PCFG, dictionary, brute-force, feedback, and optional OSINT candidate streams, then uses recent discoveries to choose which source to run next. It does not guarantee complete recovery.

## Artifacts

Run state is contained under `runs/<domain>-<timestamp>/`:

```text
events.jsonl
config/run.json
config/scheduler_config.json
config/dependency_manifest.json
nsec3map/
hashcat/
scheduler/
reports/
```

Report generation harmonizes discovered names from AXFR, NSEC, and NSEC3. NSEC3 plaintexts from hashcat are expanded to FQDNs, and an empty NSEC3 plaintext for the apex is reported as the zone name itself.

See [Dashboard and reports](dashboard.md) for UI semantics and [Configuration reference](configuration.md) for scheduler inputs.
