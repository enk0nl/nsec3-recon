# Dependencies

External source repositories are cloned under `deps/src/` and are not vendored:

- https://github.com/enk0nl/nsec3-candidate-scheduler -> `deps/src/nsec3-candidate-scheduler`
- https://github.com/enk0nl/nsec3map -> `deps/src/nsec3map`
- https://github.com/enk0nl/dutch-dns-wordlists -> `deps/src/dutch-dns-wordlists`
- https://github.com/OpenTaal/opentaal-wordlist -> `deps/src/opentaal-wordlist`
- https://github.com/danielmiessler/SecLists -> `deps/src/SecLists`
- https://github.com/enk0nl/pcfg-subdomain-generator -> `deps/src/pcfg-subdomain-generator`

Generated assets live under:

- `assets/wordlists/`
- `assets/models/`
- `assets/generated/`

Required system tools and libraries include `git`, `python3`, `python3-venv`, `python3-dev`, `gcc`/`build-essential`, `libssl-dev`/`libssl3`, `p7zip-full`, and `hashcat`.

Optional OSINT tools are `amass` and `subfinder`.

NSEC3 Recon invokes `deps/src/nsec3map/map.py` directly by default and does not require editable nsec3map installation.

## Sparse checkout modes

SecLists uses directory sparse checkout in cone mode:

```bash
git sparse-checkout set Discovery/DNS
```

OpenTaal uses single-file sparse checkout in non-cone mode:

```bash
git sparse-checkout set --no-cone /wordlist.txt
```

Dutch DNS wordlists uses single-file sparse checkout in non-cone mode:

```bash
git sparse-checkout set --no-cone /subsubdomains_all_by_occurrance.txt
```

Single-file sparse checkout uses non-cone mode with a leading slash; this avoids Git warnings about single-file sparse checkout patterns.

Do not use `--skip-checks` as the preferred solution for single files; use `--no-cone`.

## External tool minimum versions

- `hashcat >= 7.1.2`
- `amass >= 5.1.1`
- `subfinder >= 2.14.0`

Run `scripts/check-tools.sh` to verify installed versions. Use `scripts/check-tools.sh --strict` to make missing or outdated Amass/Subfinder errors, and `scripts/check-tools.sh --no-osint` to skip OSINT tool checks.

## SecLists DNS wordlist processing

SecLists is sparse-checked out with only `Discovery/DNS`. `scripts/prepare-seclists.sh` extracts `Discovery/DNS/subdomains-top1million-full.7z` into a temporary directory, removes the prevalence/count column, and writes `assets/wordlists/seclists-subdomains-full-clean.txt`.

SecLists combining can take several minutes and may use significant temporary disk space. PCFG top 100M generation can take a long time and creates a large file; use `--skip-pcfg` during bootstrap/install when you do not need that asset immediately.

The cleaned `subdomains-top1million-full.7z` output is combined with all Discovery/DNS `*.txt` wordlists. The combiner emits both original FQDN-like candidates and labels split on dots, then frequency-sorts with GNU `sort` and `uniq`. The final `assets/wordlists/seclists_total.txt` wordlist intentionally starts with one leading empty line. Counts are not retained by default; pass `--keep-counts` to write `assets/wordlists/seclists_total_counts.tsv` for debugging.

Required tools for this step are `sort` and `uniq` from GNU coreutils, plus `p7zip-full` for `7z` archive extraction.

## Scheduler model assets

Model assets are prepared from `deps/src/nsec3-candidate-scheduler/models/` into `assets/models/` by `scripts/prepare-models.sh`, which is called by `scripts/prepare-assets.sh`.

Required prepared files:

```text
assets/models/prefix_pairs.tsv
assets/models/suffix_pairs.tsv
assets/models/common_prefixes_top10000.txt
assets/models/common_suffixes_top10000.txt
```

The prepared files may be symlinks back to `deps/src/nsec3-candidate-scheduler/models/`. If `assets/models/` is empty, run `scripts/prepare-models.sh` or `scripts/prepare-assets.sh`.

Dashboard scheduler aggregation prefers `scheduler/jobs.jsonl` when available so warm-up slices are included in arm Total and Runs; stdout parsing remains a live fallback. Discovered names rows display only timestamp and name, with source summarized in the panel footer.

The jobs.jsonl mapper treats `shared_new_cracks`, `marginal_new_cracks`, and `new_cracks` as per-slice discovery fields, prefers `reward_used_for_score` for R, accepts `phase=warmup`, and treats `total_cracks`/`total`/`total_discoveries` as global totals. Discovered-name logical sources are `axfr`, `nsec`, and `nsec3`; `run.pot` is an artifact file, not a discovery source label.

Last/Previous completed slice panels show completed scheduler jobs/slices: `18/150` is the job or slice index out of configured scheduler total slices, while `total=218` inside slice details is the global cracked-hash count. NSEC3 progress uses cracked hashes / total hashes from jobs.jsonl `total_cracks` and hashcatify `hash_count`; unique discovered names are shown separately.

Recent activity shows OSINT start and completion/return events. OSINT returns candidate names, not discovered names, unless later validated by NSEC3 cracking. Discovered names are AXFR/NSEC/NSEC3-validated outputs only.
