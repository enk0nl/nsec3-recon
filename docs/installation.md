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
assets/wordlists/seclists-full-total.txt
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

Install Amass v5.1.1 or newer from the official GitHub releases. Place the binary at:

```text
$HOME/go/bin/amass
```

or ensure it is in `PATH`. Verify with:

```bash
amass -version
$HOME/go/bin/amass -version
```

Amass is optional only if the `osint/amass` scheduler arm is disabled. Do not rely on apt for Amass unless the resulting version is verified to be at least 5.1.1.

### Subfinder and Go

Install Subfinder v2.14.0 or newer with Go:

```bash
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@v2.14.0
export PATH="$PATH:$HOME/go/bin"
subfinder -version
```

If using `@latest`, check the version afterwards with `subfinder -version`; the required version is `>= 2.14.0`.

Subfinder upstream currently requires Go 1.24 or newer. Check Go with:

```bash
go version
```

If Debian/Ubuntu apt provides an older Go version, install Go from the upstream Go distribution or another trusted package source. After installing Go, ensure `$HOME/go/bin` is in `PATH`. If Subfinder is installed at `$HOME/go/bin/subfinder`, the default scheduler config can use that path directly.

## SecLists DNS asset generation

SecLists is sparse-checked out with only `Discovery/DNS`. Asset preparation extracts `subdomains-top1million-full.7z` to a temporary directory, removes the prevalence/count column from the extracted archive, and passes the cleaned output as an extra input to the external-sort combiner.

The combiner reads all Discovery/DNS `*.txt` files plus the cleaned `subdomains-top1million-full.7z` output, emits both original FQDN-like candidates and labels split on dots, and frequency-sorts the result using GNU `sort` and `uniq`.

Outputs:

```text
assets/wordlists/seclists_total_counts.tsv
assets/wordlists/seclists_total.txt
assets/wordlists/seclists-full-total.txt
```

`seclists_total.txt` and the scheduler-compatible `seclists-full-total.txt` start with exactly one leading empty line. `seclists_total_counts.tsv` does not include a leading empty candidate. `sort` and `uniq` are provided by GNU coreutils; `p7zip-full` provides `7z`/`7za` for the archive extraction.
