#!/usr/bin/env bash
check(){ command -v "$1" >/dev/null && echo "[ok] $1" || echo "[missing] $1"; }
check python3; check pip; check git
(command -v 7z >/dev/null || command -v 7za >/dev/null) && echo "[ok] 7z/7za" || echo "[missing] 7z/7za"
check n3map; check n3map-hashcatify
python3 -m nsec3_candidate_scheduler --help >/dev/null 2>&1 && echo "[ok] python3 -m nsec3_candidate_scheduler" || echo "[missing] python3 -m nsec3_candidate_scheduler"
check hashcat
[[ -x /home/vboxuser/go/bin/amass ]] || command -v amass >/dev/null && echo "[ok] amass" || echo "[warn] amass not found; OSINT Amass arm will fail unless configured"
[[ -x /home/vboxuser/go/bin/subfinder ]] || command -v subfinder >/dev/null && echo "[ok] subfinder" || echo "[warn] subfinder not found; OSINT Subfinder arm will fail unless configured"
