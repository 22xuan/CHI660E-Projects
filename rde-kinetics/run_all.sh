#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================="
echo " RDE 动力学参数测定 — 全流程分析"
echo "========================================="

echo "[1/5] 数据解析..."
python3 scripts/parse_chi660e.py
echo "[2/5] Levich 分析 (扩散系数)..."
python3 scripts/levich_analysis.py
echo "[3/5] K-L/Tafel 分析 (动力学参数)..."
python3 scripts/kl_analysis.py
echo "[4/5] 图表生成..."
python3 scripts/generate_figures.py

# LaTeX 编译
if command -v xelatex &> /dev/null && [ -f report/RDE_分析报告.tex ]; then
    echo "-----------------------------------------"
    echo " 编译 LaTeX 报告..."
    TMPDIR=$(mktemp -d)
    cp report/RDE_分析报告.tex "$TMPDIR/"
    cp output/figures/Fig*.pdf "$TMPDIR/" 2>/dev/null
    cd "$TMPDIR"
    LOGFILE="$TMPDIR/xelatex.log"
    xelatex -interaction=nonstopmode RDE_分析报告.tex > "$LOGFILE" 2>&1
    xelatex -interaction=nonstopmode RDE_分析报告.tex >> "$LOGFILE" 2>&1
    if [ -f RDE_分析报告.pdf ]; then
        cp RDE_分析报告.pdf "$SCRIPT_DIR"/report/
        cd "$SCRIPT_DIR"
        echo "  编译成功: $(ls -lh report/RDE_分析报告.pdf | awk '{print $5}')"
    else
        echo "  错误: LaTeX 编译失败!"; tail -30 "$LOGFILE"; exit 1
    fi
    rm -rf "$TMPDIR"
fi

echo "[5/5] 完成"
echo "========================================="
