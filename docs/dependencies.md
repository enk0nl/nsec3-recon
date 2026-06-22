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
