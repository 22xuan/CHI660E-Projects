#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================="
echo " EIS 分析 — 低合金钢 CO2 腐蚀"
echo "========================================="

echo "[1/3] 数据解析..."
python3 scripts/parse_mpt.py
echo "[2/3] Nyquist + Bode 图..."
python3 scripts/plot_eis.py
echo "[3/3] Randles R(QR) 拟合..."
python3 scripts/circuit_fit.py
echo ""
echo "完成: output/figures/ + output/tables/"
