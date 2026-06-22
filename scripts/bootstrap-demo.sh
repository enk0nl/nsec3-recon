#!/usr/bin/env bash
set -euo pipefail
DEPS=deps/src; ASSETS=assets; SKIP_ASSETS=0; FORCE=0; EXTRA=()
while [[ $# -gt 0 ]]; do case "$1" in --force) FORCE=1; EXTRA+=(--force); shift;; --skip-assets) SKIP_ASSETS=1; shift;; --skip-pcfg|--skip-seclists) EXTRA+=("$1"); shift;; --deps-dir) DEPS="$2"; shift 2;; --assets-dir) ASSETS="$2"; shift 2;; --jobs) shift 2;; --install-system-packages) echo "[warn] system package install not implemented"; shift;; *) echo "unknown arg $1"; exit 2;; esac; done
[[ -d .venv ]] || python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e ".[test]"
mkdir -p "$DEPS"
clone(){ url="$1"; dir="$2"; if [[ -d "$dir/.git" ]]; then echo "[update] $dir"; git -C "$dir" pull --ff-only || true; else echo "[clone] $url"; git clone "$url" "$dir"; fi; }
clone https://github.com/enk0nl/nsec3-candidate-scheduler "$DEPS/nsec3-candidate-scheduler"
clone https://github.com/enk0nl/nsec3map "$DEPS/nsec3map"
clone https://github.com/enk0nl/dutch-dns-wordlists "$DEPS/dutch-dns-wordlists"
clone https://github.com/OpenTaal/opentaal-wordlist "$DEPS/opentaal-wordlist"
clone https://github.com/danielmiessler/SecLists "$DEPS/SecLists"
clone https://github.com/enk0nl/pcfg-subdomain-generator "$DEPS/pcfg-subdomain-generator"
python3 -m pip install -e "$DEPS/nsec3-candidate-scheduler" || echo "[warn] scheduler editable install failed"
python3 -m pip install -e "$DEPS/nsec3map" || echo "[warn] nsec3map editable install failed"
[[ $SKIP_ASSETS -eq 1 ]] || scripts/prepare-assets.sh --deps-dir "$DEPS" --assets-dir "$ASSETS" "${EXTRA[@]}"
scripts/check-tools.sh
