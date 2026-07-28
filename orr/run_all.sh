#!/bin/bash
# ============================================================
# CHI660E ORR-RDE 一键全流程分析
# 用法: bash run_all.sh
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================="
echo " CHI660E ORR-RDE 全流程分析"
echo "========================================="
echo ""

# Step 1: 数据解析
echo "[1/5] 数据解析 -> 电位转换 -> 电流密度转换..."
python3 scripts/parse_chi660e.py
echo ""

# Step 2: LSV 参数提取
echo "[2/5] LSV 关键参数提取 (E_onset, E_1/2, j_L, iR矫正)..."
python3 scripts/lsv_metrics.py
echo ""

# Step 3: K-L + Tafel 分析
echo "[3/5] Koutecky-Levich 分析 + Tafel 分析..."
python3 scripts/kl_analysis.py
echo ""

# Step 4: 组间对比汇总
echo "[4/5] 组间对比汇总报表 (平行样合并)..."
python3 scripts/generate_tables.py
echo ""

# Step 5: matplotlib 预览图
echo "[5/5] 生成 matplotlib 预览图..."
python3 scripts/generate_figures.py
echo ""

# LaTeX 报告编译 (ext4 临时目录，绕过 WSL 9P 文件系统限制)
if command -v xelatex &> /dev/null; then
    echo "-----------------------------------------"
    echo " 编译 LaTeX 报告..."
    TMPDIR=$(mktemp -d)
    trap "rm -rf $TMPDIR" EXIT
    cp report/ORR_RDE_分析报告.tex "$TMPDIR/"

    # 用 Python 读取并转换图片到 ext4 临时目录
    python3 -c "
from PIL import Image
import os
src = 'output/figures'
dst = '$TMPDIR'
figs = [
    # 注：如需新增图片引用，需同步更新此列表
    'Fig2_Group_Comparison_1600r.png',
    'Fig3_KL_1组.png', 'Fig3_KL_2组.png',
    'Fig4_Tafel_1组.png',
    'Fig5_Key_Parameters_Bar.png',
]
for f in figs:
    fpath = os.path.join(src, f)
    if os.path.exists(fpath):
        img = Image.open(fpath)
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        out = os.path.join(dst, f.replace('.png', '.jpg'))
        img.save(out, 'JPEG', quality=95)
        print(f'  {f} -> {f.replace(\".png\", \".jpg\")}')
    else:
        print(f'  [警告] 图片不存在: {f}')
"

    # 两次编译 (TOC + 交叉引用)，在临时目录内执行
    cd "$TMPDIR"
    LOGFILE="$TMPDIR/xelatex.log"
    xelatex -interaction=nonstopmode ORR_RDE_分析报告.tex > "$LOGFILE" 2>&1
    xelatex -interaction=nonstopmode ORR_RDE_分析报告.tex >> "$LOGFILE" 2>&1

    if [ -f ORR_RDE_分析报告.pdf ]; then
        cp ORR_RDE_分析报告.pdf "$SCRIPT_DIR"/report/
        cd "$SCRIPT_DIR"
        echo "  编译成功: $(ls -lh report/ORR_RDE_分析报告.pdf | awk '{print $5}')"
    else
        echo "  错误: LaTeX 编译失败!"
        echo "  ------ 最后 30 行编译日志 ------"
        tail -30 "$LOGFILE"
        cd "$SCRIPT_DIR"
        exit 1
    fi

    echo "-----------------------------------------"
else
    echo "  跳过 LaTeX 编译 (xelatex 未安装)"
fi

echo ""
echo "========================================="
echo " 全流程完成!"
echo " 图表: output/figures/"
echo " 表格: output/tables/"
echo " 报告: report/ORR_RDE_分析报告.pdf"
echo "========================================="
