#!/usr/bin/env bash
set -euo pipefail
DEPS=deps/src/dutch-dns-wordlists; ASSETS=assets
while [[ $# -gt 0 ]]; do case "$1" in --deps-dir) DEPS="$2/dutch-dns-wordlists"; shift 2;; --source-dir) DEPS="$2"; shift 2;; --assets-dir) ASSETS="$2"; shift 2;; *) echo "unknown arg $1"; exit 2;; esac; done
src="$DEPS/subsubdomains_all_by_occurrance.txt"; dst="$ASSETS/wordlists/subsubdomains_all_by_occurrance.txt"
[[ -f "$src" ]] || { echo "missing expected Dutch DNS wordlist: $src"; exit 1; }
mkdir -p "$(dirname "$dst")"
ln -sf "$(realpath "$src")" "$dst" 2>/dev/null || cp -f "$src" "$dst"
echo "[ok] $dst"
