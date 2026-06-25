# Dependencies

This file records dependency layout and asset preparation details. See [Installation](installation.md) for setup commands.

## External repositories

- [nsec3-candidate-scheduler](https://github.com/enk0nl/nsec3-candidate-scheduler) -> `deps/src/nsec3-candidate-scheduler`
- [nsec3map fork](https://github.com/enk0nl/nsec3map) -> `deps/src/nsec3map`
- [pcfg-subdomain-generator](https://github.com/enk0nl/pcfg-subdomain-generator) -> `deps/src/pcfg-subdomain-generator`
- [dutch-dns-wordlists](https://github.com/enk0nl/dutch-dns-wordlists) -> `deps/src/dutch-dns-wordlists`
- [OpenTaal wordlist](https://github.com/OpenTaal/opentaal-wordlist) -> `deps/src/opentaal-wordlist`
- [SecLists](https://github.com/danielmiessler/SecLists) -> `deps/src/SecLists`

## Generated assets

Generated assets live under `assets/`:

```text
assets/wordlists/
assets/models/
assets/generated/
```

`assets/models` may contain symlinks to `deps/src/nsec3-candidate-scheduler/models`. If model files are missing, run `scripts/prepare-models.sh` or `scripts/prepare-assets.sh`.

## Sparse checkouts

SecLists uses directory sparse checkout:

```bash
git sparse-checkout set Discovery/DNS
```

OpenTaal and Dutch DNS wordlists use single-file sparse checkout with non-cone mode and leading slash:

```bash
git sparse-checkout set --no-cone /wordlist.txt
git sparse-checkout set --no-cone /subsubdomains_all_by_occurrance.txt
```

## Wordlist processing

SecLists processing combines all Discovery/DNS `*.txt` files, cleaned `subdomains-top1million-full.7z`, and labels split on dots. Cleaning removes invalid records, including a leading empty line. `[info] Preparing SecLists DNS wordlist` is printed before work starts; SecLists combining can take several minutes and may use temporary disk space.

PCFG generation uses the Dutch subdomain ruleset from `pcfg-subdomain-generator` and writes `assets/wordlists/rfc1035_pcfg_top100000000.txt`. `[info] Generating PCFG DNS wordlist` is printed before work starts; PCFG top 100M generation can take a long time.

## Version checks

`scripts/check-tools.sh` validates required tools and optional OSINT tools. Use `scripts/check-tools.sh --strict` to treat missing or outdated Amass/Subfinder as errors, and `scripts/check-tools.sh --no-osint` to skip OSINT checks.
