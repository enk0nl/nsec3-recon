#!/usr/bin/env bash
set -euo pipefail
DEPS_DIR="deps/src"
ASSETS_DIR="assets"
FORCE=0
COPY=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --deps-dir) DEPS_DIR="$2"; shift 2;;
    --assets-dir) ASSETS_DIR="$2"; shift 2;;
    --force) FORCE=1; shift;;
    --copy) COPY=1; shift;;
    *) echo "unknown arg $1" >&2; exit 2;;
  esac
done
SRC_DIR="$DEPS_DIR/nsec3-candidate-scheduler/models"
DEST_DIR="$ASSETS_DIR/models"
required=(prefix_pairs.tsv suffix_pairs.tsv common_prefixes_top10000.txt common_suffixes_top10000.txt)
mkdir -p "$DEST_DIR"
for f in "${required[@]}"; do
  src="$SRC_DIR/$f"
  dst="$DEST_DIR/$f"
  if [[ ! -e "$src" ]]; then
    echo "[missing] $src" >&2
    echo "Run scripts/bootstrap.sh first or verify the nsec3-candidate-scheduler checkout." >&2
    exit 1
  fi
  if [[ -e "$dst" || -L "$dst" ]]; then
    if [[ $FORCE -eq 1 ]]; then
      rm -f "$dst"
    else
      echo "[ok] model asset exists: $dst"
      continue
    fi
  fi
  if [[ $COPY -eq 1 ]]; then
    cp "$src" "$dst"
  else
    rel=$(python3 - "$src" "$DEST_DIR" <<'PY'
import os, sys
print(os.path.relpath(sys.argv[1], sys.argv[2]))
PY
)
    ln -s "$rel" "$dst" 2>/dev/null || cp "$src" "$dst"
  fi
  echo "[ok] model asset: $dst"
done
