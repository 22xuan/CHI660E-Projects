#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================="
echo " EIS 分析 — 低合金钢 CO2 腐蚀"
echo "========================================="

echo "[1/4] 数据解析..."
python3 scripts/parse_mpt.py
echo "[2/4] Nyquist + Bode 图..."
python3 scripts/plot_eis.py
echo "[3/4] R(Q(RW)) 拟合..."
python3 scripts/circuit_fit.py

if command -v xelatex &> /dev/null && [ -f report/CO2_EIS_报告.tex ]; then
    echo "[4/4] 编译报告..."
    TMPDIR=$(mktemp -d)
    trap "rm -rf $TMPDIR" EXIT
    cp report/CO2_EIS_报告.tex "$TMPDIR/"
    cp output/figures/*.png "$TMPDIR/" 2>/dev/null
    cd "$TMPDIR"
    xelatex -interaction=nonstopmode CO2_EIS_报告.tex > /dev/null 2>&1
    xelatex -interaction=nonstopmode CO2_EIS_报告.tex > /dev/null 2>&1
    if [ -f CO2_EIS_报告.pdf ]; then
        cp CO2_EIS_报告.pdf "$SCRIPT_DIR"/report/
        echo "  编译成功: $(ls -lh "$SCRIPT_DIR"/report/CO2_EIS_报告.pdf | awk '{print $5}')"
    else
        echo "  编译失败!"
    fi
fi

echo ""
echo "完成: output/figures/ + output/tables/"
