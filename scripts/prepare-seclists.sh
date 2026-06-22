#!/usr/bin/env bash
set -euo pipefail
ARCHIVE=""; DEPS="deps/src/SecLists"; ASSETS="assets"
while [[ $# -gt 0 ]]; do case "$1" in --archive) ARCHIVE="$2"; shift 2;; --deps-dir) DEPS="$2"; shift 2;; --assets-dir) ASSETS="$2"; shift 2;; *) echo "unknown arg $1"; exit 2;; esac; done
ARCHIVE=${ARCHIVE:-$DEPS/Discovery/DNS/subdomains-top1million-full.7z}
mkdir -p "$ASSETS/wordlists"
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
if [[ "$ARCHIVE" == *.7z ]]; then command -v 7z >/dev/null && EX=7z || EX=7za; "$EX" x -o"$tmp" "$ARCHIVE" >/dev/null; SRC=$(find "$tmp" -type f | head -1); else SRC="$ARCHIVE"; fi
python3 - "$SRC" "$ASSETS/wordlists/seclists-subdomains-full-clean.txt" <<'PY'
import sys,re
src,out=sys.argv[1:3]
def numeric(x):
    return bool(re.fullmatch(r'[0-9]+', x.strip()))
def pick(line):
    s=line.strip()
    if not s or s.startswith(('#',';')): return None
    if ',' in s:
        parts=[p.strip() for p in s.split(',')]
        return parts[1] if len(parts)>1 and numeric(parts[0]) and parts[1] else parts[0]
    parts=s.split()
    if len(parts)==1: return parts[0]
    if len(parts)==2:
        return parts[1] if numeric(parts[0]) else parts[0]
    raise ValueError('cannot interpret: '+s)
with open(src,errors='ignore') as f, open(out,'w') as o:
    for line in f:
        v=pick(line)
        if v:
            v=v.strip().lower().rstrip('.')
            if v: print(v,file=o)
PY
python3 scripts/combine-frequency-sort-wordlists.py --output "$ASSETS/wordlists/seclists-full-total.txt" "$ASSETS/wordlists/seclists-subdomains-full-clean.txt"
