# Installation

## Debian/Ubuntu system dependencies

Install baseline packages before creating the Python environment:

```bash
sudo apt update
sudo apt install -y \
  git \
  python3 \
  python3-pip \
  python3-venv \
  python3-dev \
  python3-setuptools \
  build-essential \
  gcc \
  libssl-dev \
  libssl3 \
  p7zip-full \
  hashcat
```

Optional distribution packages:

```bash
sudo apt install -y \
  python3-numpy \
  python3-scipy \
  python3-dnspython
```

Prefer installing Python runtime packages such as `dnspython` and `rich` inside `.venv` with `python3 -m pip install -e ".[test]"`.

`python3-venv` is required for `.venv` creation on Debian/Ubuntu. If venv creation fails because `ensurepip` is unavailable, install the package for the active Python minor version:

```bash
PYVER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
sudo apt update
sudo apt install -y python${PYVER}-venv
```

Fallback:

```bash
sudo apt install -y python3-venv
```

`python3-dev`, `gcc`/`build-essential`, `libssl-dev`, and `libssl3` are needed only if building nsec3map's optional OpenSSL-accelerated extension. The default pipeline invokes nsec3map directly with `python3 map.py`, so editable nsec3map installation and extension builds are not mandatory. `p7zip-full` provides `7z`/`7za` for SecLists extraction. `hashcat` is required for NSEC3 cracking. Amass and Subfinder are optional OSINT dependencies unless those scheduler arms are enabled.

## Install

Quick start with virtualenv activation:

```bash
scripts/install.sh --skip-pcfg
source .venv/bin/activate
nsec3-recon --help
nsec3-recon example.nl --dry-run
nsec3-recon example.nl
```

Alternative without activating the virtualenv:

```bash
scripts/install.sh --skip-pcfg
.venv/bin/nsec3-recon --help
.venv/bin/nsec3-recon example.nl --dry-run
.venv/bin/nsec3-recon example.nl
```

The installer checks `ensurepip` before running `python3 -m venv .venv`. It prints exact apt commands and exits non-zero if venv support is missing. It only runs apt commands when invoked with `--install-system-packages`. It installs NSEC3 Recon editable into `.venv`, verifies `.venv/bin/nsec3-recon --help`, calls `scripts/bootstrap.sh`, runs `scripts/check-tools.sh`, and prints next commands.

`--skip-pcfg`, `--skip-seclists`, `--skip-assets`, `--deps-dir`, `--assets-dir`, and `--jobs` are passed through to `scripts/bootstrap.sh`; for example, `scripts/install.sh --skip-pcfg` calls bootstrap with equivalent PCFG skipping behavior.

## Using the virtual environment

`scripts/install.sh` installs into `.venv`. To use `nsec3-recon` directly, activate the virtual environment:

```bash
source .venv/bin/activate
```

Without activation, call the entrypoint by path:

```bash
.venv/bin/nsec3-recon
```

If you open a new shell, activate `.venv` again unless you use `.venv/bin/nsec3-recon` explicitly.


## Dry run

After activating `.venv`:

```bash
source .venv/bin/activate
nsec3-recon example.nl --dry-run
```

Without activation:

```bash
.venv/bin/nsec3-recon example.nl --dry-run
```

Dry run creates a workspace, renders scheduler config, prints planned commands, and does not run external network stages.

## Bootstrap dependencies

`scripts/bootstrap.sh` is a lower-level dependency/bootstrap helper that is normally called by `scripts/install.sh`. It clones or updates dependencies, prepares assets, and may be run manually for advanced workflows. `scripts/check-tools.sh` verifies external tool availability and versions but does not install anything. `scripts/prepare-assets.sh` prepares derived wordlists/assets and may be called by bootstrap.

```bash
scripts/bootstrap.sh
```

The bootstrap clones code repositories fully and uses sparse checkout for data repositories. Directory sparse checkout uses normal cone mode. Single-file sparse checkout must use non-cone mode; do not use `--skip-checks`.

```bash
git clone --filter=blob:none --sparse https://github.com/danielmiessler/SecLists deps/src/SecLists
cd deps/src/SecLists
git sparse-checkout set Discovery/DNS

git clone --filter=blob:none --sparse https://github.com/OpenTaal/opentaal-wordlist deps/src/opentaal-wordlist
cd deps/src/opentaal-wordlist
git sparse-checkout set --no-cone wordlist.txt

git clone --filter=blob:none --sparse https://github.com/enk0nl/dutch-dns-wordlists deps/src/dutch-dns-wordlists
cd deps/src/dutch-dns-wordlists
git sparse-checkout set --no-cone subsubdomains_all_by_occurrance.txt
```

SecLists archive expected path:

```text
deps/src/SecLists/Discovery/DNS/subdomains-top1million-full.7z
```

OpenTaal expected path:

```text
deps/src/opentaal-wordlist/wordlist.txt
```

Dutch DNS expected path:

```text
deps/src/dutch-dns-wordlists/subsubdomains_all_by_occurrance.txt
```

## PCFG asset generation

```bash
cd deps/src/pcfg-subdomain-generator
python3 pcfg_guesser.py --rule dutch_subdomains --limit 100000000 > output_file.txt
```

The product script writes `assets/wordlists/rfc1035_pcfg_top100000000.txt` through a temporary file and records metadata.

## Asset layout

```text
assets/wordlists/seclists_total.txt
assets/wordlists/rfc1035_pcfg_top100000000.txt
assets/wordlists/subsubdomains_all_by_occurrance.txt
assets/wordlists/opentaal-wordlist.txt
assets/models/prefix_pairs.tsv
assets/models/suffix_pairs.tsv
assets/models/common_prefixes_top10000.txt
assets/models/common_suffixes_top10000.txt
```

## External tool versions

Required minimum versions:

```text
hashcat >= 7.1.2
amass >= 5.1.1
subfinder >= 2.14.0
```

Verify versions explicitly:

```bash
hashcat --version
amass -version
$HOME/go/bin/amass -version
subfinder -version
$HOME/go/bin/subfinder -version
```

Debian/Ubuntu apt repositories may be behind, especially for hashcat. Do not assume apt hashcat satisfies `hashcat >= 7.1.2`; always verify after installation.

### Hashcat

Apt installation is acceptable only if the version is new enough:

```bash
sudo apt update
sudo apt install -y hashcat
hashcat --version
```

If this reports a version older than 7.1.2, install hashcat from the upstream release instead.

Manual upstream install flow:

```bash
mkdir -p deps/bin
cd deps/bin
# download hashcat v7.1.2 or newer from https://hashcat.net/hashcat/
# extract the 7z archive
# add extracted directory to PATH or set HASHCAT_BIN / --hashcat-bin
```

The project does not hardcode a fragile hashcat download URL. Use the official hashcat download page and verify the archive before use.

### Amass

Install Amass v5.1.1 or newer with Go:

```bash
export PATH="$PATH:$HOME/go/bin"
CGO_ENABLED=0 go install -v github.com/owasp-amass/amass/v5/cmd/amass@main
$HOME/go/bin/amass -version
```

`CGO_ENABLED=0` is intentional. The command tracks `@main`, so version verification after install is mandatory. If `$HOME/go/bin/amass -version` reports a version older than 5.1.1, the install is not acceptable for the default enabled `osint/amass` scheduler arm. Fallback version commands still accepted by tool checks are `amass -version`, `amass version`, and `amass --version`.

Amass is optional only if the `osint/amass` scheduler arm is disabled.

### Subfinder and Go

Install Subfinder v2.14.0 or newer with Go:

```bash
export PATH="$PATH:$HOME/go/bin"
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
$HOME/go/bin/subfinder -version
```

The `@latest` selector is a moving target, so version verification after install is mandatory. If `$HOME/go/bin/subfinder -version` reports a version older than 2.14.0, the install is not acceptable for the default enabled `osint/subfinder` scheduler arm.

Subfinder upstream currently requires Go 1.24 or newer. Check Go with:

```bash
go version
```

If Debian/Ubuntu apt provides an older Go version, install Go from the upstream Go distribution or another trusted package source. After installing Go, ensure `$HOME/go/bin` is in `PATH`. If Subfinder is installed at `$HOME/go/bin/subfinder`, the default scheduler config can use that path directly.

## SecLists DNS asset generation

SecLists is sparse-checked out with only `Discovery/DNS`. Asset preparation extracts `subdomains-top1million-full.7z` to a temporary directory, removes the prevalence/count column from the extracted archive, and passes the cleaned output as an extra input to the external-sort combiner.

The combiner reads all Discovery/DNS `*.txt` files plus the cleaned `subdomains-top1million-full.7z` output, emits both original FQDN-like candidates and labels split on dots, and frequency-sorts the result using GNU `sort` and `uniq`.

Default output:

```text
assets/wordlists/seclists_total.txt
```

Optional debug output with `--keep-counts`:

```text
assets/wordlists/seclists_total_counts.tsv
```

`seclists_total.txt` starts with exactly one leading empty line. `seclists_total_counts.tsv` is not written unless `--keep-counts` is passed and does not include a leading empty candidate. `sort` and `uniq` are provided by GNU coreutils; `p7zip-full` provides `7z`/`7za` for the archive extraction.

## nsec3map Python dependencies

NSEC3 Recon invokes the public nsec3map fork directly from `deps/src/nsec3map`; direct `map.py` invocation is default. Editable nsec3map installation is not required by default, and building the nsec3map C extension remains optional.

The nsec3map fork imports `psycopg2` through its database module even when database output is not used. The product virtual environment must therefore include:

```text
dnspython
psycopg2-binary
```

`scripts/install.sh` installs these through the normal project dependency set. `psycopg2-binary` avoids requiring PostgreSQL development headers for the default path. PostgreSQL server is not required.

Manual fix if an alternate interpreter is used:

```bash
source .venv/bin/activate
python -m pip install dnspython psycopg2-binary
```

Verify the project interpreter:

```bash
.venv/bin/python -c "import dns, psycopg2, rich"
```

Verify direct nsec3map invocation:

```bash
.venv/bin/python deps/src/nsec3map/map.py --detect-only example.nl
# or
cd deps/src/nsec3map
../../../.venv/bin/python map.py --detect-only example.nl
```

If you deliberately use source `psycopg2` instead of `psycopg2-binary`, `libpq-dev` is an optional package for source psycopg2 builds:

```bash
sudo apt install -y libpq-dev
```

Do not add `libpq-dev` to the base dependency list for the default `psycopg2-binary` path, and do not install a PostgreSQL server for this pipeline.

Note: nsec3map imports psycopg2 during startup, so `psycopg2-binary` is part of the default runtime dependency set.

## Scheduler model assets

The scheduler repository includes predictive/static-affix model files under:

```text
deps/src/nsec3-candidate-scheduler/models/
```

`scripts/prepare-assets.sh` calls `scripts/prepare-models.sh` to copy or symlink those files into:

```text
assets/models/
```

Required model assets are:

```text
assets/models/prefix_pairs.tsv
assets/models/suffix_pairs.tsv
assets/models/common_prefixes_top10000.txt
assets/models/common_suffixes_top10000.txt
```

Manual repair:

```bash
scripts/prepare-models.sh
# or
scripts/prepare-assets.sh
```

By default `assets/models/` may contain symlinks into `deps/src/nsec3-candidate-scheduler/models/`; this is expected and avoids duplicating generated model files.

Dashboard scheduler aggregation prefers `scheduler/jobs.jsonl` when available so warm-up slices are included in arm Total and Runs; stdout parsing remains a live fallback. Discovered names rows display only timestamp and name, with source summarized in the panel footer.

The jobs.jsonl mapper treats `shared_new_cracks`, `marginal_new_cracks`, and `new_cracks` as per-slice discovery fields, prefers `reward_used_for_score` for R, accepts `phase=warmup`, and treats `total_cracks`/`total`/`total_discoveries` as global totals. Discovered-name logical sources are `axfr`, `nsec`, and `nsec3`; `run.pot` is an artifact file, not a discovery source label.
