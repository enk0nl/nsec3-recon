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
git sparse-checkout set --no-cone wordlist.txt
```

Dutch DNS wordlists uses single-file sparse checkout in non-cone mode:

```bash
git sparse-checkout set --no-cone subsubdomains_all_by_occurrance.txt
```

Do not use `--skip-checks` as the preferred solution for single files; use `--no-cone`.

## External tool minimum versions

- `hashcat >= 7.1.2`
- `amass >= 5.1.1`
- `subfinder >= 2.14.0`

Run `scripts/check-tools.sh` to verify installed versions. Use `scripts/check-tools.sh --strict` to make missing or outdated Amass/Subfinder errors, and `scripts/check-tools.sh --no-osint` to skip OSINT tool checks.

## SecLists DNS wordlist processing

SecLists is sparse-checked out with only `Discovery/DNS`. `scripts/prepare-seclists.sh` extracts `Discovery/DNS/subdomains-top1million-full.7z` into a temporary directory, removes the prevalence/count column, and writes `assets/wordlists/seclists-subdomains-full-clean.txt`.

The cleaned `subdomains-top1million-full.7z` output is combined with all Discovery/DNS `*.txt` wordlists. The combiner emits both original FQDN-like candidates and labels split on dots, then frequency-sorts with GNU `sort` and `uniq`. The final `assets/wordlists/seclists_total.txt` wordlist intentionally starts with one leading empty line. Counts are not retained by default; pass `--keep-counts` to write `assets/wordlists/seclists_total_counts.tsv` for debugging.

Required tools for this step are `sort` and `uniq` from GNU coreutils, plus `p7zip-full` for `7z` archive extraction.
