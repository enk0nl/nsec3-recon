#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"
INSTALL_SYSTEM=0; INSTALL_HASHCAT_UPSTREAM=0; INSTALL_GO_TOOLS=0; STRICT_TOOLS=0; FORCE=0
BOOTSTRAP_ARGS=()
while [[ $# -gt 0 ]]; do case "$1" in --install-system-packages) INSTALL_SYSTEM=1; shift;; --install-hashcat-upstream) INSTALL_HASHCAT_UPSTREAM=1; shift;; --install-go-tools) INSTALL_GO_TOOLS=1; shift;; --strict-tools) STRICT_TOOLS=1; shift;; --force) FORCE=1; shift;; --skip-pcfg|--skip-seclists|--skip-assets|--force-bootstrap) BOOTSTRAP_ARGS+=("${1/--force-bootstrap/--force}"); shift;; --deps-dir|--assets-dir|--jobs) BOOTSTRAP_ARGS+=("$1" "$2"); shift 2;; *) echo "[error] unknown argument: $1" >&2; exit 2;; esac; done
apt_packages=(git python3 python3-pip python3-venv python3-dev python3-setuptools build-essential gcc libssl-dev libssl3 p7zip-full hashcat)
install_system_packages(){
  echo "Will install Debian/Ubuntu packages: ${apt_packages[*]}"
  sudo apt update
  sudo apt install -y "${apt_packages[@]}"
}

ensure_go_available(){
  if ! command -v go >/dev/null 2>&1; then
    echo "[missing] go; install Go from https://go.dev/dl/ and ensure it is in PATH." >&2
    return 1
  fi
  GOVERSION="$(go version | awk '{print $3}' | sed 's/^go//')"
  GOMAJOR="${GOVERSION%%.*}"
  GOREST="${GOVERSION#*.}"
  GOMINOR="${GOREST%%.*}"
  if [[ "${GOMAJOR:-0}" -lt 1 || ( "${GOMAJOR:-0}" -eq 1 && "${GOMINOR:-0}" -lt 24 ) ]]; then
    echo "[bad-version] go version=$GOVERSION required>=1.24 for current Subfinder installs." >&2
    if [[ $FORCE -ne 1 ]]; then
      echo "Install Go 1.24 or newer, or rerun with --force to attempt installation anyway." >&2
      return 1
    fi
  fi
  mkdir -p "$HOME/go/bin"
  export PATH="$PATH:$HOME/go/bin"
}
install_go_tools(){
  ensure_go_available || exit 1
  CGO_ENABLED=0 go install -v github.com/owasp-amass/amass/v5/cmd/amass@main
  go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
  [[ -x "$HOME/go/bin/amass" ]] || { echo "[missing] $HOME/go/bin/amass after install" >&2; exit 1; }
  [[ -x "$HOME/go/bin/subfinder" ]] || { echo "[missing] $HOME/go/bin/subfinder after install" >&2; exit 1; }
  AMASS_BIN="$HOME/go/bin/amass" SUBFINDER_BIN="$HOME/go/bin/subfinder" scripts/check-tools.sh --strict || { echo "Installed Go tools did not satisfy required versions." >&2; exit 1; }
}
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
if [[ $INSTALL_HASHCAT_UPSTREAM -eq 1 ]]; then
  echo "Upstream hashcat installation is not automated. Download v7.1.2 or newer from https://hashcat.net/hashcat/ and install under deps/bin without overwriting system hashcat." >&2
  exit 1
fi
if [[ $INSTALL_GO_TOOLS -eq 1 ]]; then
  install_go_tools
fi
[[ $INSTALL_SYSTEM -eq 1 ]] && install_system_packages
ensure_python_venv_available || exit 1
[[ -d .venv ]] || python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -U pip
python3 -m pip install -e ".[test]"
if ! .venv/bin/python - <<'PYIMPORT' >/dev/null 2>&1
import dns
import psycopg2
import rich
PYIMPORT
then
  echo "[error] installed Python environment cannot import dns, psycopg2, and rich" >&2
  echo "Try: .venv/bin/python -m pip install dnspython psycopg2-binary rich" >&2
  exit 1
fi
if ! .venv/bin/nsec3-recon --help >/dev/null 2>&1; then
  echo "[error] .venv/bin/nsec3-recon --help failed after installation" >&2
  echo "Try: . .venv/bin/activate && python3 -m pip install -e \".[test]\"" >&2
  exit 1
fi
scripts/bootstrap.sh "${BOOTSTRAP_ARGS[@]}"
if [[ $STRICT_TOOLS -eq 1 ]]; then scripts/check-tools.sh --strict; else scripts/check-tools.sh; fi
echo "[ok] nsec3-recon installed into .venv"
echo
echo "Next steps:"
echo "  source .venv/bin/activate"
echo "  nsec3-recon --help"
echo "  nsec3-recon example.nl --dry-run"
echo
echo "Without activating the venv:"
echo "  .venv/bin/nsec3-recon --help"
echo "  .venv/bin/nsec3-recon example.nl --dry-run"
