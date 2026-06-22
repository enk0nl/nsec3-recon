#!/usr/bin/env bash
set -euo pipefail
DEPS=deps/src; ASSETS=assets; SKIP_ASSETS=0; FORCE=0; INSTALL_SYSTEM=0; EXTRA=()
while [[ $# -gt 0 ]]; do case "$1" in --force) FORCE=1; EXTRA+=(--force); shift;; --skip-assets) SKIP_ASSETS=1; shift;; --skip-pcfg|--skip-seclists) EXTRA+=("$1"); shift;; --deps-dir) DEPS="$2"; shift 2;; --assets-dir) ASSETS="$2"; shift 2;; --jobs) shift 2;; --install-system-packages) INSTALL_SYSTEM=1; shift;; *) echo "unknown arg $1"; exit 2;; esac; done
ensure_python_venv_available(){
  if python3 - <<'PY' >/dev/null 2>&1
import ensurepip
PY
  then return 0; fi
  PYVER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  echo "[missing] python3 venv support"
  echo "Debian/Ubuntu fix:"
  echo "  sudo apt update"
  echo "  sudo apt install -y python${PYVER}-venv"
  echo "Fallback:"
  echo "  sudo apt install -y python3-venv"
  return 1
}
if [[ $INSTALL_SYSTEM -eq 1 ]]; then sudo apt update; sudo apt install -y git python3 python3-pip python3-venv python3-dev python3-setuptools build-essential gcc libssl-dev libssl3 p7zip-full hashcat; fi
ensure_python_venv_available || exit 1
[[ -d .venv ]] || python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e ".[test]"
mkdir -p "$DEPS"
clone_full(){ url="$1"; dir="$2"; if [[ -d "$dir/.git" ]]; then echo "[update] $dir"; git -C "$dir" pull --ff-only || true; else echo "[clone] $url"; git clone "$url" "$dir"; fi; }
clone_sparse_dir(){ url="$1"; dir="$2"; sparse_dir="$3"; if [[ -d "$dir/.git" ]]; then echo "[update] $dir"; git -C "$dir" pull --ff-only || true; else echo "[sparse-dir-clone] $url $sparse_dir"; git clone --filter=blob:none --sparse "$url" "$dir"; fi; git -C "$dir" sparse-checkout set "$sparse_dir"; }
clone_sparse_file(){ url="$1"; dir="$2"; file_path="$3"; if [[ -d "$dir/.git" ]]; then echo "[update] $dir"; git -C "$dir" pull --ff-only || true; else echo "[sparse-file-clone] $url $file_path"; git clone --filter=blob:none --sparse "$url" "$dir"; fi; git -C "$dir" sparse-checkout set --no-cone "$file_path"; }
require_file(){ [[ -f "$1" ]] || { echo "[missing] expected dependency file: $1"; exit 1; }; }
clone_full https://github.com/enk0nl/nsec3-candidate-scheduler "$DEPS/nsec3-candidate-scheduler"
clone_full https://github.com/enk0nl/nsec3map "$DEPS/nsec3map"
clone_sparse_file https://github.com/enk0nl/dutch-dns-wordlists "$DEPS/dutch-dns-wordlists" subsubdomains_all_by_occurrance.txt
clone_sparse_dir https://github.com/danielmiessler/SecLists "$DEPS/SecLists" Discovery/DNS
clone_sparse_file https://github.com/OpenTaal/opentaal-wordlist "$DEPS/opentaal-wordlist" wordlist.txt
clone_full https://github.com/enk0nl/pcfg-subdomain-generator "$DEPS/pcfg-subdomain-generator"
require_file "$DEPS/SecLists/Discovery/DNS/subdomains-top1million-full.7z"
require_file "$DEPS/opentaal-wordlist/wordlist.txt"
require_file "$DEPS/dutch-dns-wordlists/subsubdomains_all_by_occurrance.txt"
python3 -m pip install -e "$DEPS/nsec3-candidate-scheduler" || echo "[warn] scheduler editable install failed"
echo "[info] nsec3map editable install is intentionally skipped; using direct python3 map.py"
[[ $SKIP_ASSETS -eq 1 ]] || scripts/prepare-assets.sh --deps-dir "$DEPS" --assets-dir "$ASSETS" "${EXTRA[@]}"
scripts/check-tools.sh
