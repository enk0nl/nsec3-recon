#!/usr/bin/env bash
set -euo pipefail
ASSETS=assets; DEPS=deps/src; FORCE=0; SKIP_PCFG=0; SKIP_SECLISTS=0
while [[ $# -gt 0 ]]; do case "$1" in --assets-dir) ASSETS="$2"; shift 2;; --deps-dir) DEPS="$2"; shift 2;; --force) FORCE=1; shift;; --skip-pcfg) SKIP_PCFG=1; shift;; --skip-seclists) SKIP_SECLISTS=1; shift;; *) shift;; esac; done
mkdir -p "$ASSETS/wordlists" "$ASSETS/models" "$ASSETS/generated"
[[ $SKIP_SECLISTS -eq 1 ]] || scripts/prepare-seclists.sh --deps-dir "$DEPS/SecLists" --assets-dir "$ASSETS"
scripts/prepare-dutch-dns-wordlists.sh --source-dir "$DEPS/dutch-dns-wordlists" --assets-dir "$ASSETS" || echo "[warn] Dutch DNS wordlist preparation failed"
scripts/prepare-opentaal.sh --source-dir "$DEPS/opentaal-wordlist" --assets-dir "$ASSETS" || echo "[warn] OpenTaal preparation failed"
[[ $SKIP_PCFG -eq 1 || -e "$ASSETS/wordlists/rfc1035_pcfg_top100000000.txt" ]] || PCFG_REPO="$DEPS/pcfg-subdomain-generator" PCFG_OUTPUT="$ASSETS/wordlists/rfc1035_pcfg_top100000000.txt" scripts/generate-pcfg-wordlist.sh
miss=0; for f in prefix_pairs.tsv suffix_pairs.tsv common_prefixes_top10000.txt common_suffixes_top10000.txt; do [[ -e "$ASSETS/models/$f" ]] || miss=1; done
[[ $miss -eq 0 ]] || echo "[warn] predictive/static-affix model files are missing; scheduler config references assets/models/"
