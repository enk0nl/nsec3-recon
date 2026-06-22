#!/usr/bin/env bash
set -euo pipefail
ARCHIVE=""; ARCHIVE_SUPPLIED=0; DEPS="deps/src/SecLists"; ASSETS="assets"
while [[ $# -gt 0 ]]; do case "$1" in --archive) ARCHIVE="$2"; ARCHIVE_SUPPLIED=1; shift 2;; --deps-dir) DEPS="$2"; shift 2;; --assets-dir) ASSETS="$2"; shift 2;; *) echo "unknown arg $1"; exit 2;; esac; done
DNS_DIR="$DEPS/Discovery/DNS"
ARCHIVE=${ARCHIVE:-$DNS_DIR/subdomains-top1million-full.7z}
mkdir -p "$ASSETS/wordlists"
if [[ $ARCHIVE_SUPPLIED -eq 0 && ! -d "$DNS_DIR" ]]; then echo "missing SecLists DNS directory: $DNS_DIR"; exit 1; fi
[[ -e "$ARCHIVE" ]] || { echo "missing SecLists top1m archive: $ARCHIVE"; exit 1; }
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
if [[ "$ARCHIVE" == *.7z ]]; then command -v 7z >/dev/null && EX=7z || EX=7za; "$EX" x -o"$tmp" "$ARCHIVE" >/dev/null; SRC=$(find "$tmp" -type f | head -1); else SRC="$ARCHIVE"; fi
CLEAN="$ASSETS/wordlists/seclists-subdomains-full-clean.txt"
python3 - "$SRC" "$CLEAN" <<'PY'
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
TMP_ARGS=()
[[ -n "${TMP_DIR:-}" ]] && TMP_ARGS+=(--tmp-dir "$TMP_DIR")
python3 scripts/seclists_fqdn_and_labels_external_sort.py \
  --input-dir "$DNS_DIR" \
  --extra-input "$CLEAN" \
  --out-prefix "$ASSETS/wordlists/seclists" \
  --sort-memory "${SORT_MEMORY:-1G}" \
  "${TMP_ARGS[@]}"
COMPAT="$ASSETS/wordlists/seclists-full-total.txt"
TARGET="seclists_total.txt"
ln -sf "$TARGET" "$COMPAT" 2>/dev/null || cp -f "$ASSETS/wordlists/$TARGET" "$COMPAT"
echo "[ok] cleaned top1m full archive: $CLEAN"
echo "[ok] combined SecLists DNS wordlists: $ASSETS/wordlists/seclists_total.txt"
echo "[ok] counts: $ASSETS/wordlists/seclists_total_counts.tsv"
echo "[ok] scheduler wordlist: $COMPAT"
