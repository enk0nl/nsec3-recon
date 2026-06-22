#!/usr/bin/env bash
set -euo pipefail
INSTALL_SYSTEM=0
while [[ $# -gt 0 ]]; do case "$1" in --install-system-packages) INSTALL_SYSTEM=1; shift;; *) echo "unknown arg $1" >&2; exit 2;; esac; done
apt_packages=(git python3 python3-pip python3-venv python3-dev python3-setuptools build-essential gcc libssl-dev libssl3 p7zip-full hashcat)
install_system_packages(){
  echo "Will install Debian/Ubuntu packages: ${apt_packages[*]}"
  sudo apt update
  sudo apt install -y "${apt_packages[@]}"
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
[[ $INSTALL_SYSTEM -eq 1 ]] && install_system_packages
ensure_python_venv_available || exit 1
[[ -d .venv ]] || python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -U pip
python3 -m pip install -e ".[test]"
