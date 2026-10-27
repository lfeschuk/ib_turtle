#!/usr/bin/env bash
# Build the laptop package: only what the live service and phone app need (no research code, data or tests).
#   deploy/build_package.sh   ->   dist/gapshort-live-YYYYMMDD.tar.gz (+ .sha256)
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p dist
out="dist/gapshort-live-$(date +%Y%m%d).tar.gz"
tar --exclude='__pycache__' --exclude='*.pyc' --exclude='trading_system/live/export_model.py' \
    --owner=0 --group=0 --numeric-owner -czf "$out" \
    trading_system/__init__.py trading_system/models.py trading_system/strategy_core.py \
    trading_system/engine.py trading_system/sizing.py trading_system/live \
    deploy/README.md deploy/config.example.toml deploy/gapshort.service deploy/requirements-live.txt
(cd dist && sha256sum "$(basename "$out")" > "$(basename "$out").sha256")
echo "$out ($(du -h "$out" | cut -f1))"
cat "$out.sha256"
