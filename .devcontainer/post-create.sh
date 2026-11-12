#!/usr/bin/env bash
# Runs once after the dev container is created.
set -euo pipefail

echo "==> Upgrading pip"
python -m pip install --upgrade pip

echo "==> Installing backend dependencies (runtime + dev)"
pip install -r backend/requirements-dev.txt

echo "==> Tool versions"
python --version
node --version
psql --version

echo "==> Dev container ready"
