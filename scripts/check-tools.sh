#!/usr/bin/env bash
STRICT=0; NO_OSINT=0
while [[ $# -gt 0 ]]; do case "$1" in --strict) STRICT=1; shift;; --no-osint) NO_OSINT=1; shift;; *) echo "[error] unknown argument: $1" >&2; exit 2;; esac; done
missing=0
ok(){ echo "[ok] $1"; }
miss(){ echo "[missing] $1"; missing=1; }
warn(){ echo "[warn] $1"; }
PYTHONPATH="${PYTHONPATH:-}:src"; export PYTHONPATH
command -v python3 >/dev/null && ok python3 || miss python3
python3 -m pip --version >/dev/null 2>&1 && ok "python3 -m pip" || command -v pip >/dev/null && ok pip || miss "pip or python3 -m pip"
command -v git >/dev/null && ok git || miss git
(command -v 7z >/dev/null && ok 7z) || (command -v 7za >/dev/null && ok 7za) || miss "7z/7za"
python3 - <<'PY' >/dev/null 2>&1
import ensurepip
PY
[[ $? -eq 0 ]] && ok "python3 venv support" || miss "python3 venv support"
check_tool(){
  local name="$1" strict="$2"
  local line rc
  set +e
  line=$(python3 - "$name" <<'PY'
import sys
from nsec3_recon.adapters.tools import check_hashcat, check_amass, check_subfinder
name=sys.argv[1]
paths={"hashcat":"hashcat","amass":__import__("os").environ.get("AMASS_BIN", "~/go/bin/amass"),"subfinder":__import__("os").environ.get("SUBFINDER_BIN", "~/go/bin/subfinder")}
check={"hashcat":check_hashcat,"amass":check_amass,"subfinder":check_subfinder}[name](paths[name])
if check.ok:
    print(f"[ok] {check.name} version={check.version} required>={check.required} path={check.path}")
    raise SystemExit(0)
if check.path is None:
    print(f"[missing] {check.name} required>={check.required}")
    raise SystemExit(2)
print(f"[bad-version] {check.name} version={check.version} required>={check.required} path={check.path}")
raise SystemExit(3)
PY
)
  rc=$?; set -e 2>/dev/null || true
  if [[ $name != hashcat && $strict -eq 0 && $rc -ne 0 ]]; then
    if [[ $rc -eq 2 ]]; then echo "[warn] $name missing; osint/$name will fail unless the scheduler arm is disabled or $name is installed."; else echo "$line"; echo "[warn] $name version is below the recommended minimum for enabled osint/$name arms."; fi
    return 0
  fi
  echo "$line"
  if [[ $name == hashcat && $rc -eq 3 ]]; then echo "  apt repositories may be behind; install upstream hashcat v7.1.2 or newer."; fi
  [[ $rc -eq 0 ]] || missing=1
}
check_tool hashcat 1
if [[ $NO_OSINT -eq 0 ]]; then check_tool amass "$STRICT"; check_tool subfinder "$STRICT"; fi
if [[ -n "${NSEC3MAP_PYTHON:-}" ]]; then
  N3PY="$NSEC3MAP_PYTHON"
elif [[ -x .venv/bin/python ]]; then
  N3PY=".venv/bin/python"
else
  N3PY="python3"
fi
N3PY_RUN="$N3PY"
if [[ "$N3PY_RUN" != /* && "$N3PY_RUN" == */* ]]; then N3PY_RUN="$(pwd)/${N3PY_RUN#./}"; fi
if "$N3PY" -c "import dns, psycopg2" >/dev/null 2>&1; then
  ok "nsec3map python deps: dns psycopg2 using $N3PY"
else
  echo "[missing] nsec3map python dependency psycopg2"
  echo "fix: $N3PY -m pip install psycopg2-binary"
  missing=1
fi
python3 -m nsec3_candidate_scheduler --help >/dev/null 2>&1 && ok "python3 -m nsec3_candidate_scheduler" || miss "python3 -m nsec3_candidate_scheduler"
if command -v timeout >/dev/null 2>&1; then TIMEOUT_CMD=(timeout 10); else TIMEOUT_CMD=(); fi
set +e
SCHED_HELP=$("${TIMEOUT_CMD[@]}" python3 -m nsec3_candidate_scheduler run --help 2>&1)
SCHED_RC=$?
set -e 2>/dev/null || true
if [[ $SCHED_RC -ne 0 ]]; then
  miss "python3 -m nsec3_candidate_scheduler run --help"
else
  sched_missing=0
  for opt in --no-optimized-kernels --optimized-kernel-failover --no-optimized-kernel-failover; do
    if [[ "$SCHED_HELP" != *"$opt"* ]]; then sched_missing=1; fi
  done
  if [[ $sched_missing -eq 0 ]]; then
    ok "nsec3-candidate-scheduler optimized-kernel failover options"
  else
    echo "[bad-version] nsec3-candidate-scheduler is too old. Re-run scripts/bootstrap.sh or install scheduler ref bdad139599761cece979eb17aabddf5c00369d7a."
    missing=1
  fi
fi
[[ -f deps/src/nsec3map/map.py ]] && ok "nsec3map source: deps/src/nsec3map/map.py" || miss "deps/src/nsec3map/map.py"
if [[ -f deps/src/nsec3map/map.py ]]; then (cd deps/src/nsec3map && "$N3PY_RUN" -c "import n3map.map" >/dev/null 2>&1) && ok "nsec3map import: n3map.map" || warn "nsec3map import n3map.map failed; ensure deps/src/nsec3map is cloned and $N3PY has dnspython psycopg2-binary"; fi
([[ -f deps/src/nsec3map/hashcatify.py ]] || [[ -f deps/src/nsec3map/n3map/hashcatify.py ]]) && ok "nsec3map hashcatify.py" || miss "nsec3map hashcatify.py"
[[ -f deps/src/pcfg-subdomain-generator/pcfg_guesser.py ]] && ok "pcfg_guesser.py" || miss "deps/src/pcfg-subdomain-generator/pcfg_guesser.py"
[[ -e deps/src/pcfg-subdomain-generator/Rules/dutch_subdomains ]] && ok "PCFG Rules/dutch_subdomains" || miss "deps/src/pcfg-subdomain-generator/Rules/dutch_subdomains"
exit $missing
