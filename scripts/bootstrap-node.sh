#!/usr/bin/env bash
set -euo pipefail

echo "== NeoSentinel node bootstrap =="
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2 git curl python3-pip python3-venv
sudo usermod -aG docker "$USER"

REPO_URL="${NEOSENTINEL_REPO_URL:-https://github.com/your-org/NeoSentinel.git}"
INSTALL_DIR="${NEOSENTINEL_INSTALL_DIR:-$HOME/NeoSentinel}"

if [ ! -d "$INSTALL_DIR/.git" ]; then
  git clone "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
neosentinel init

echo "== ARM64 / SVE2 check =="
uname -m
grep -E 'sve|sve2' /proc/cpuinfo | head -1 || true

echo "[SUCCESS] Bootstrap complete. Log out and back in for docker group, then run docker compose on node-001."
