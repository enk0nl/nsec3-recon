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

```bash
scripts/install.sh
```

The installer checks `ensurepip` before running `python3 -m venv .venv`. It prints exact apt commands and exits non-zero if venv support is missing. It only runs apt commands when invoked with `--install-system-packages`.

## Bootstrap dependencies

```bash
scripts/bootstrap.sh
```

The bootstrap clones code repositories fully and data repositories sparsely:

```bash
git clone --filter=blob:none --sparse https://github.com/danielmiessler/SecLists deps/src/SecLists
cd deps/src/SecLists
git sparse-checkout set Discovery/DNS

git clone --filter=blob:none --sparse https://github.com/OpenTaal/opentaal-wordlist deps/src/opentaal-wordlist
cd deps/src/opentaal-wordlist
git sparse-checkout set wordlist.txt
```

SecLists archive expected path:

```text
deps/src/SecLists/Discovery/DNS/subdomains-top1million-full.7z
```

OpenTaal expected path:

```text
deps/src/opentaal-wordlist/wordlist.txt
```

## PCFG asset generation

```bash
cd deps/src/pcfg-subdomain-generator
python3 pcfg_guesser.py --rule dutch_subdomains --limit 100000000 > output_file.txt
```

The product script writes `assets/wordlists/rfc1035_pcfg_top100000000.txt` through a temporary file and records metadata.

## Asset layout

```text
assets/wordlists/seclists-full-total.txt
assets/wordlists/rfc1035_pcfg_top100000000.txt
assets/wordlists/subsubdomains_all_by_occurrance.txt
assets/wordlists/opentaal-wordlist.txt
assets/models/prefix_pairs.tsv
assets/models/suffix_pairs.tsv
assets/models/common_prefixes_top10000.txt
assets/models/common_suffixes_top10000.txt
```
