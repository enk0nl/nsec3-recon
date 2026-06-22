#!/usr/bin/env bash
missing=0
ok(){ echo "[ok] $1"; }
miss(){ echo "[missing] $1"; missing=1; }
warn(){ echo "[warn] $1"; }
command -v python3 >/dev/null && ok python3 || miss python3
python3 -m pip --version >/dev/null 2>&1 && ok "python3 -m pip" || command -v pip >/dev/null && ok pip || miss "pip or python3 -m pip"
command -v git >/dev/null && ok git || miss git
(command -v 7z >/dev/null && ok 7z) || (command -v 7za >/dev/null && ok 7za) || miss "7z/7za"
python3 - <<'PY' >/dev/null 2>&1
import ensurepip
PY
[[ $? -eq 0 ]] && ok "python3 venv support" || miss "python3 venv support"
command -v hashcat >/dev/null && ok hashcat || miss hashcat
python3 -m nsec3_candidate_scheduler --help >/dev/null 2>&1 && ok "python3 -m nsec3_candidate_scheduler" || miss "python3 -m nsec3_candidate_scheduler"
[[ -f deps/src/nsec3map/map.py ]] && ok "deps/src/nsec3map/map.py" || miss "deps/src/nsec3map/map.py"
([[ -f deps/src/nsec3map/hashcatify.py ]] || [[ -f deps/src/nsec3map/n3map/hashcatify.py ]]) && ok "nsec3map hashcatify.py" || miss "nsec3map hashcatify.py"
[[ -f deps/src/pcfg-subdomain-generator/pcfg_guesser.py ]] && ok "pcfg_guesser.py" || miss "deps/src/pcfg-subdomain-generator/pcfg_guesser.py"
[[ -e deps/src/pcfg-subdomain-generator/Rules/dutch_subdomains ]] && ok "PCFG Rules/dutch_subdomains" || miss "deps/src/pcfg-subdomain-generator/Rules/dutch_subdomains"
[[ -x /home/vboxuser/go/bin/amass ]] || command -v amass >/dev/null && ok amass || warn "amass not found; osint/amass will fail unless configured"
[[ -x /home/vboxuser/go/bin/subfinder ]] || command -v subfinder >/dev/null && ok subfinder || warn "subfinder not found; osint/subfinder will fail unless configured"
exit $missing
