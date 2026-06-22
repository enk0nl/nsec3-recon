#!/usr/bin/env bash
set -euo pipefail
DEPS=deps/src/opentaal-wordlist; ASSETS=assets
while [[ $# -gt 0 ]]; do case "$1" in --deps-dir) DEPS="$2/opentaal-wordlist"; shift 2;; --source-dir) DEPS="$2"; shift 2;; --assets-dir) ASSETS="$2"; shift 2;; *) echo "unknown arg $1"; exit 2;; esac; done
src="$DEPS/wordlist.txt"; dst="$ASSETS/wordlists/opentaal-wordlist.txt"
[[ -f "$src" ]] || { echo "missing OpenTaal wordlist: $src"; exit 1; }
mkdir -p "$(dirname "$dst")"
ln -sf "$(realpath "$src")" "$dst" 2>/dev/null || cp -f "$src" "$dst"
echo "[ok] $dst"
