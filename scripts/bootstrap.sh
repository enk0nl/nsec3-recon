#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

NSEC3MAP_REF="${NSEC3MAP_REF:-5af04b9c900b8f0f1a2113a22f5b34e67e637c80}"
SCHEDULER_REF="${SCHEDULER_REF:-bdad139599761cece979eb17aabddf5c00369d7a}"
PCFG_REF="${PCFG_REF:-171f89e85206cb22e89c3803c13f6a320d538e8b}"
SECLISTS_REF="${SECLISTS_REF:-198047f1e22251e3b88b98b10e8bd15283e8a1e9}"
OPENTAAL_REF="${OPENTAAL_REF:-b250510dda431785f962019167d1415198ff3905}"
DUTCH_DNS_WORDLISTS_REF="${DUTCH_DNS_WORDLISTS_REF:-87403dff13f2a9da53084c88412a6e19280003ec}"
DEPS=deps/src; ASSETS=assets; SKIP_ASSETS=0; FORCE=0; INSTALL_SYSTEM=0; EXTRA=()
while [[ $# -gt 0 ]]; do case "$1" in --force) FORCE=1; EXTRA+=(--force); shift;; --skip-assets) SKIP_ASSETS=1; shift;; --skip-pcfg|--skip-seclists) EXTRA+=("$1"); shift;; --deps-dir) DEPS="$2"; shift 2;; --assets-dir) ASSETS="$2"; shift 2;; --jobs) shift 2;; --install-system-packages) INSTALL_SYSTEM=1; shift;; *) echo "[error] unknown argument: $1"; exit 2;; esac; done
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
clone_full(){ url="$1"; dir="$2"; ref="$3"; if [[ -d "$dir/.git" ]]; then echo "[fetch] $dir"; git -C "$dir" fetch --all --tags; else echo "[clone] $url"; git clone "$url" "$dir"; fi; git -C "$dir" checkout "$ref"; }
clone_sparse_dir(){ url="$1"; dir="$2"; sparse_dir="$3"; ref="$4"; if [[ -d "$dir/.git" ]]; then echo "[update] $dir"; git -C "$dir" pull --ff-only || true; else echo "[sparse-dir-clone] $url $sparse_dir"; git clone --filter=blob:none --sparse "$url" "$dir"; fi; git -C "$dir" sparse-checkout set "$sparse_dir"; git -C "$dir" checkout "$ref"; }
clone_sparse_file(){ url="$1"; dir="$2"; file_path="$3"; ref="$4"; if [[ -d "$dir/.git" ]]; then echo "[update] $dir"; git -C "$dir" pull --ff-only || true; else echo "[sparse-file-clone] $url $file_path"; git clone --filter=blob:none --sparse "$url" "$dir"; fi; sparse_file_pattern="$file_path"; sparse_file_pattern="${sparse_file_pattern#/}"; sparse_file_pattern="/${sparse_file_pattern}"; git -C "$dir" sparse-checkout set --no-cone "$sparse_file_pattern"; git -C "$dir" checkout "$ref"; }
require_file(){ [[ -f "$1" ]] || { echo "[missing] expected dependency file: $1"; exit 1; }; }
clone_full https://github.com/enk0nl/nsec3-candidate-scheduler "$DEPS/nsec3-candidate-scheduler" "$SCHEDULER_REF"
clone_full https://github.com/enk0nl/nsec3map "$DEPS/nsec3map" "$NSEC3MAP_REF"
# Dutch DNS single-file sparse checkout: git sparse-checkout set --no-cone /subsubdomains_all_by_occurrance.txt
clone_sparse_file https://github.com/enk0nl/dutch-dns-wordlists "$DEPS/dutch-dns-wordlists" /subsubdomains_all_by_occurrance.txt "$DUTCH_DNS_WORDLISTS_REF"
clone_sparse_dir https://github.com/danielmiessler/SecLists "$DEPS/SecLists" Discovery/DNS "$SECLISTS_REF"
# OpenTaal single-file sparse checkout: git sparse-checkout set --no-cone /wordlist.txt
clone_sparse_file https://github.com/OpenTaal/opentaal-wordlist "$DEPS/opentaal-wordlist" /wordlist.txt "$OPENTAAL_REF"
clone_full https://github.com/enk0nl/pcfg-subdomain-generator "$DEPS/pcfg-subdomain-generator" "$PCFG_REF"
require_file "$DEPS/SecLists/Discovery/DNS/subdomains-top1million-full.7z"
require_file "$DEPS/opentaal-wordlist/wordlist.txt"
require_file "$DEPS/dutch-dns-wordlists/subsubdomains_all_by_occurrance.txt"
python3 -m pip install -e "$DEPS/nsec3-candidate-scheduler" || echo "[warn] scheduler editable install failed"
[[ $SKIP_ASSETS -eq 1 ]] || scripts/prepare-assets.sh --deps-dir "$DEPS" --assets-dir "$ASSETS" "${EXTRA[@]}"
scripts/check-tools.sh
