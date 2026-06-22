#!/usr/bin/env bash
set -euo pipefail
REPO=${PCFG_REPO:-deps/src/pcfg-subdomain-generator}; OUT=${PCFG_OUTPUT:-assets/wordlists/rfc1035_pcfg_top100000000.txt}; COUNT=${PCFG_COUNT:-100000000}
mkdir -p "$(dirname "$OUT")"
if [[ ! -d "$REPO" ]]; then echo "PCFG repo missing: $REPO"; exit 1; fi
if [[ -z "${PCFG_COMMAND:-}" ]]; then echo "Could not locate PCFG generator entrypoint. Edit scripts/generate-pcfg-wordlist.sh and set PCFG_COMMAND."; exit 1; fi
tmp="$OUT.tmp.$$"; eval "$PCFG_COMMAND" > "$tmp"; mv "$tmp" "$OUT"
python3 - "$OUT" "$COUNT" <<'PY'
import json,sys,datetime
out,count=sys.argv[1],int(sys.argv[2])
meta={"source":"https://github.com/enk0nl/pcfg-subdomain-generator","candidate_count":count,"generated_at":datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z'),"output":out}
open(out.rsplit('.',1)[0]+'.json','w').write(json.dumps(meta,indent=2)+'\n')
PY
