#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"
ASSETS=assets; DEPS=deps/src; FORCE=0; SKIP_PCFG=0; SKIP_SECLISTS=0; SKIP_MODELS=0
while [[ $# -gt 0 ]]; do case "$1" in --assets-dir) ASSETS="$2"; shift 2;; --deps-dir) DEPS="$2"; shift 2;; --force) FORCE=1; shift;; --skip-pcfg) SKIP_PCFG=1; shift;; --skip-seclists) SKIP_SECLISTS=1; shift;; --skip-models) SKIP_MODELS=1; shift;; *) shift;; esac; done
mkdir -p "$ASSETS/wordlists" "$ASSETS/models" "$ASSETS/generated"
[[ $SKIP_SECLISTS -eq 1 ]] || scripts/prepare-seclists.sh --deps-dir "$DEPS/SecLists" --assets-dir "$ASSETS"
scripts/prepare-dutch-dns-wordlists.sh --source-dir "$DEPS/dutch-dns-wordlists" --assets-dir "$ASSETS" || echo "[warn] Dutch DNS wordlist preparation failed"
scripts/prepare-opentaal.sh --source-dir "$DEPS/opentaal-wordlist" --assets-dir "$ASSETS" || echo "[warn] OpenTaal preparation failed"
if [[ $SKIP_MODELS -eq 0 ]]; then
  model_args=(--deps-dir "$DEPS" --assets-dir "$ASSETS")
  [[ $FORCE -eq 1 ]] && model_args+=(--force)
  scripts/prepare-models.sh "${model_args[@]}"
fi
[[ $SKIP_PCFG -eq 1 || -e "$ASSETS/wordlists/rfc1035_pcfg_top100000000.txt" ]] || PCFG_REPO="$DEPS/pcfg-subdomain-generator" PCFG_OUTPUT="$ASSETS/wordlists/rfc1035_pcfg_top100000000.txt" scripts/generate-pcfg-wordlist.sh
