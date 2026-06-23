#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"
REPO=${PCFG_REPO:-deps/src/pcfg-subdomain-generator}
OUT=${PCFG_OUTPUT:-assets/wordlists/rfc1035_pcfg_top100000000.txt}
COUNT=100000000
CMD="python3 pcfg_guesser.py --rule dutch_subdomains --limit 100000000"
FORCE=${FORCE:-0}
while [[ $# -gt 0 ]]; do
  case "$1" in
    --force) FORCE=1; shift;;
    *) echo "[error] unknown argument: $1"; exit 2;;
  esac
done
[[ -f "$REPO/pcfg_guesser.py" ]] || { echo "missing PCFG generator: $REPO/pcfg_guesser.py"; exit 1; }
[[ -e "$REPO/Rules/dutch_subdomains" ]] || { echo "missing PCFG ruleset: $REPO/Rules/dutch_subdomains"; exit 1; }
OUT_ABS="$(python3 -c 'import os,sys; print(os.path.abspath(sys.argv[1]))' "$OUT")"
TMP="${OUT_ABS}.tmp"
mkdir -p "$(dirname "$OUT_ABS")"
if [[ -f "$OUT_ABS" && "$FORCE" != "1" ]]; then
  echo "[skip] PCFG wordlist already exists: $OUT"
  exit 0
fi
echo "[info] Generating PCFG DNS wordlist"
echo "[info] Command: $CMD"
echo "[info] Output: $OUT"
echo "[info] This can take a long time and produces a large file."
(cd "$REPO" && python3 pcfg_guesser.py --rule dutch_subdomains --limit 100000000 > "$TMP")
mv "$TMP" "$OUT_ABS"
python3 - "$OUT" "$COUNT" "$CMD" <<'PY'
import json, sys, datetime
out, count, cmd = sys.argv[1], int(sys.argv[2]), sys.argv[3]
meta = {"source":"https://github.com/enk0nl/pcfg-subdomain-generator","command":cmd,"candidate_count":count,"output":out,"generated_at":datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')}
open(out.rsplit('.',1)[0]+'.json','w').write(json.dumps(meta, indent=2)+'\n')
PY

echo "[ok] PCFG wordlist written: $OUT"
