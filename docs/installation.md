# Installation

## Prerequisites

Debian/Ubuntu baseline packages:

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

`python3-venv` is required for `.venv`. If venv creation fails because `ensurepip` is unavailable, install the package for the active Python minor version:

```bash
PYVER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
sudo apt install -y python${PYVER}-venv
```

`python3-dev`, `gcc`/`build-essential`, `libssl-dev`, and `libssl3` are needed only for nsec3map's optional OpenSSL extension. Direct `map.py` invocation is default; editable nsec3map installation is not required. `libpq-dev` is optional only when building source psycopg2 manually; the default Python dependency is `psycopg2-binary`.

## Install NSEC3 Recon

```bash
scripts/install.sh
source .venv/bin/activate
nsec3-recon --help
```

Without activating the virtual environment:

```bash
scripts/install.sh
.venv/bin/nsec3-recon --help
.venv/bin/nsec3-recon example.nl --dry-run
```

`scripts/install.sh` creates `.venv`, installs NSEC3 Recon editable, calls `scripts/bootstrap.sh`, runs tool checks, and prints next commands. `scripts/bootstrap.sh` is a lower-level dependency/bootstrap helper normally called by `scripts/install.sh`; do not run both back-to-back for a normal install.

## Advanced installer options

`--skip-pcfg`, `--skip-seclists`, `--skip-assets`, `--deps-dir`, `--assets-dir`, and `--jobs` are passed through to bootstrap. Use `--skip-pcfg` only for development, CI shortcuts, or debugging flows that do not require the PCFG generator. Normal installs should prepare PCFG assets.

## Dependency checkout and assets

Bootstrap clones external source under `deps/src/` and prepares generated assets under `assets/`. These directories are not committed.

Sparse checkout commands used for large data sources:

```bash
git sparse-checkout set Discovery/DNS
git sparse-checkout set --no-cone /wordlist.txt
git sparse-checkout set --no-cone /subsubdomains_all_by_occurrance.txt
```

Single-file sparse checkout uses non-cone mode with a leading slash; do not use `--skip-checks` for these files.

Expected checkout files include:

```text
deps/src/opentaal-wordlist/wordlist.txt
deps/src/dutch-dns-wordlists/subsubdomains_all_by_occurrance.txt
```

Prepared assets include:

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

Model assets are prepared from `deps/src/nsec3-candidate-scheduler/models` into `assets/models` by `scripts/prepare-models.sh`, usually through `scripts/prepare-assets.sh`.

SecLists processing combines all Discovery/DNS `*.txt` inputs, cleaned `subdomains-top1million-full.7z` entries, and labels split on dots. The cleaner removes malformed values, including a leading empty line. `[info] Preparing SecLists DNS wordlist` is printed before work starts; SecLists combining can take several minutes.

PCFG generation writes `assets/wordlists/rfc1035_pcfg_top100000000.txt`. `[info] Generating PCFG DNS wordlist` is printed before work starts; PCFG top 100M generation can take a long time.

## External tool versions

Minimum supported versions:

```text
hashcat >= 7.1.2
amass >= 5.1.1
subfinder >= 2.14.0
```

Debian/Ubuntu apt repositories may be behind and can provide hashcat older than 7.1.2. Verify versions after installation:

```bash
hashcat --version
amass -version
subfinder -version
scripts/check-tools.sh
```

## Go OSINT tools

Subfinder and Amass are optional OSINT arms. Use Go 1.24 or newer when installing them from source:

```bash
CGO_ENABLED=0 go install -v github.com/owasp-amass/amass/v5/cmd/amass@main
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
```

`@main` and `@latest` are moving targets; version verification after install is mandatory.

## nsec3map Python dependency

NSEC3 Recon invokes `deps/src/nsec3map/map.py` directly by default. The nsec3map fork imports `psycopg2`; install dependencies into the same interpreter used for `--nsec3map-python`:

```bash
source .venv/bin/activate
python -m pip install dnspython psycopg2-binary rich
```
