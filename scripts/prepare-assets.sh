#!/usr/bin/env bash
set -euo pipefail
ASSETS=assets; DEPS=deps/src; FORCE=0; SKIP_PCFG=0; SKIP_SECLISTS=0
while [[ $# -gt 0 ]]; do case "$1" in --assets-dir) ASSETS="$2"; shift 2;; --deps-dir) DEPS="$2"; shift 2;; --force) FORCE=1; shift;; --skip-pcfg) SKIP_PCFG=1; shift;; --skip-seclists) SKIP_SECLISTS=1; shift;; *) shift;; esac; done
mkdir -p "$ASSETS/wordlists" "$ASSETS/models" "$ASSETS/generated"
[[ $SKIP_SECLISTS -eq 1 ]] || scripts/prepare-seclists.sh --deps-dir "$DEPS/SecLists" --assets-dir "$ASSETS" || echo "[warn] SecLists preparation skipped/failed"
linkcopy(){ src="$1"; dst="$2"; if [[ -e "$dst" && $FORCE -ne 1 ]]; then echo "[skip] $dst"; elif [[ -e "$src" ]]; then cp -f "$src" "$dst"; echo "[ok] $dst"; else echo "[warn] missing $src"; fi; }
linkcopy "$DEPS/dutch-dns-wordlists/subsubdomains_all_by_occurrance.txt" "$ASSETS/wordlists/subsubdomains_all_by_occurrance.txt"
find "$DEPS/opentaal-wordlist" -type f 2>/dev/null | head -1 | while read -r f; do linkcopy "$f" "$ASSETS/wordlists/opentaal-wordlist.txt"; done
[[ $SKIP_PCFG -eq 1 || -e "$ASSETS/wordlists/rfc1035_pcfg_top100000000.txt" ]] || scripts/generate-pcfg-wordlist.sh || echo "[warn] PCFG generation skipped/failed"
for f in prefix_pairs.tsv suffix_pairs.tsv common_prefixes_top10000.txt common_suffixes_top10000.txt; do [[ -e "$ASSETS/models/$f" ]] || miss=1; done
[[ -z "${miss:-}" ]] || echo "[warn] predictive/static-affix model files are missing; scheduler config references assets/models/"
