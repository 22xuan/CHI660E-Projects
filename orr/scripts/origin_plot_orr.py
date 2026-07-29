#!/usr/bin/env python3
"""OriginPro 批量出图脚本 — ORR RDE 就业展示用
运行环境: Windows Anaconda (D:\\Anaconda\\python.exe)
需要: originpro (pip install originpro)
前提: 先运行 parse_chi660e.py + kl_analysis.py 生成 output/origin_input/ 数据
"""

import sys
import csv
import yaml
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

try:
    import originpro as op
except ImportError:
    print("错误: originpro 未安装。请在 Windows Anaconda 下运行:")
    print("  D:\\Anaconda\\python.exe -m pip install originpro")
    sys.exit(1)

PROJECT_DIR = Path(__file__).resolve().parent.parent

# 从 params.yaml 读取配置
with open(PROJECT_DIR / "params.yaml", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

GROUPS = cfg["data"]["groups"]
RPMS = cfg["kl_analysis"]["rotation_speeds_rpm"]
CATALYST_NAMES = cfg.get("catalysts", {g: g for g in GROUPS})

INPUT_DIR = PROJECT_DIR / cfg["output"]["origin_input_dir"]
OUTPUT_DIR = PROJECT_DIR / cfg["output"]["figures_dir"]
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

COLORS = ["#E41A1C", "#377EB8", "#4DAF4A", "#984EA3", "#FF7F00", "#A65628"]


def import_lsv_data(sheet, group):
    for i, rpm in enumerate(RPMS):
        fpath = INPUT_DIR / f"{group}_{rpm}r.csv"
        if not fpath.exists():
            print(f"  跳过: {fpath}")
            continue

        col_x = i * 2
        col_y = i * 2 + 1

        x_vals, y_vals = [], []
        with open(fpath, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                x_vals.append(float(row["potential_v"]))
                y_vals.append(float(row["current_density_ma_cm2"]))

        sheet.from_list(col_x, x_vals, "X")
        sheet.from_list(col_y, y_vals, "Y")

        col_name = f"{rpm}rpm"
        try:
            sheet.cols[col_y].set_label(col_name)
            sheet.cols[col_x].set_label(f"E_{rpm}rpm")
        except:
            pass

        print(f"  {group} {rpm}r: {len(x_vals)} pts -> col {col_x}(X), {col_y}(Y)")


def create_lsv_overlay_plot(wks, group):
    gp = op.new_graph()
    gl = gp[0]
    gl.set_int("width", 800)
    gl.set_int("height", 600)

    n_speeds = len(RPMS)
    for i in range(n_speeds):
        plot = gl.add_plot(wks, i * 2 + 1, i * 2, type=200)
        plot.color = COLORS[i % len(COLORS)]

        gl.set_xlim(-1.0, 0.4)
    gl.set_ylim("", "", "Y")
    gl.rescale()

    cat_name = CATALYST_NAMES.get(group, group)
    gl.label(f"{cat_name} - ORR LSV 曲线", title=True)
    gl.label("Potential (V vs Hg/HgO)", xlabel=True)
    gl.label("Current Density (mA/cm2)", ylabel=True)

    out = str(OUTPUT_DIR / f"Fig1_LSV_{group}.png")
    gp.save_fig(out, width=1600)
    print(f"  图表已保存: {out}")
    return gp


def create_group_comparison_plot():
    gp = op.new_graph()
    gl = gp[0]
    gl.set_int("width", 800)
    gl.set_int("height", 600)

    for i, (group, color) in enumerate(zip(GROUPS, COLORS)):
        fpath = INPUT_DIR / f"{group}_1600r.csv"
        if not fpath.exists():
            continue
        x_vals, y_vals = [], []
        with open(fpath, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                x_vals.append(float(row["potential_v"]))
                y_vals.append(float(row["current_density_ma_cm2"]))

        wks_temp = op.new_sheet("w", f"tmp_{group}")
        wks_temp.from_list(0, x_vals, "X")
        wks_temp.from_list(1, y_vals, "Y")
        plot = gl.add_plot(wks_temp, 1, 0, type=200)
        plot.color = color

        gl.set_xlim(-1.0, 0.4)
    gl.rescale()
    gl.label("催化剂 ORR 性能对比 (@1600 rpm)", title=True)
    gl.label("Potential (V vs Hg/HgO)", xlabel=True)
    gl.label("Current Density (mA/cm2)", ylabel=True)

    out = str(OUTPUT_DIR / "Fig2_Group_Comparison_1600r.png")
    gp.save_fig(out, width=1600)
    print(f"  图表已保存: {out}")


def create_kl_plot_with_fit(group):
    kl_path = INPUT_DIR / f"KL_{group}.csv"
    if not kl_path.exists():
        print(f"  K-L 数据不存在: {kl_path}")
        return

    gp = op.new_graph()
    gl = gp[0]
    gl.set_int("width", 700)
    gl.set_int("height", 550)

    data = {}
    with open(kl_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pot = row["potential_v"]
            if pot not in data:
                data[pot] = {"x": [], "y": []}
            data[pot]["x"].append(float(row["omega_neg_half"]))
            data[pot]["y"].append(float(row["j_inv_cm2_per_ma"]))

    for i, (pot, d) in enumerate(sorted(data.items())):
        wks_temp = op.new_sheet("w", f"KL_{pot}")
        wks_temp.from_list(0, d["x"], "X")
        wks_temp.from_list(1, d["y"], "Y")
        plot = gl.add_plot(wks_temp, 1, 0, type=201)
        plot.color = COLORS[3 - i]

    cat_name = CATALYST_NAMES.get(group, group)
    gl.label(f"{cat_name} - Koutecky-Levich 图", title=True)
    gl.label("w^(-1/2) (s^(1/2)*rad^(-1/2))", xlabel=True)
    gl.label("j^(-1) (cm2/mA)", ylabel=True)

    out = str(OUTPUT_DIR / f"Fig3_KL_{group}.png")
    gp.save_fig(out, width=1400)
    print(f"  图表已保存: {out}")


def create_bar_chart():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    comp_path = PROJECT_DIR / "output" / "tables" / "group_comparison.csv"
    if not comp_path.exists():
        print("  组间对比表不存在")
        return

    data_map = {}
    with open(comp_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("催化剂", row.get("组别", ""))
            data_map[name] = row

    if not data_map:
        return

    cats = list(data_map.keys())

    def parse_val(key):
        vals = []
        for c in cats:
            v = data_map[c].get(key, "-")
            try:
                vals.append(abs(float(str(v).split(" +/- ")[0])))
            except (ValueError, AttributeError):
                vals.append(0)
        return vals

    e_half = parse_val("E_1/2 (V vs RHE)")
    j_lim = parse_val("|j_L| (mA/cm2) @1600r")
    n_el = parse_val("n (电子转移数)")

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    bar_colors = COLORS[: len(cats)]

    axes[0].bar(cats, e_half, color=bar_colors, edgecolor="white")
    axes[0].set_title("Half-wave Potential E1/2 (V vs RHE)")
    axes[0].set_ylabel("E1/2 (V vs RHE)")
    axes[0].tick_params(axis="x", rotation=15)

    axes[1].bar(cats, j_lim, color=bar_colors, edgecolor="white")
    axes[1].set_title("Limiting Current Density @1600r (mA/cm2)")
    axes[1].set_ylabel("|j_L| (mA/cm2)")
    axes[1].tick_params(axis="x", rotation=15)

    axes[2].bar(cats, n_el, color=bar_colors, edgecolor="white")
    axes[2].set_title("Electron Transfer Number (n)")
    axes[2].set_ylabel("n")
    axes[2].axhline(y=4.0, color="red", linestyle="--", alpha=0.5, label="n=4 (4e-)")
    axes[2].axhline(y=2.0, color="blue", linestyle="--", alpha=0.5, label="n=2 (2e-)")
    axes[2].legend()
    axes[2].tick_params(axis="x", rotation=15)

    plt.tight_layout()
    out = str(OUTPUT_DIR / "Fig5_Key_Parameters_Bar.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  图表已保存: {out}")


def main():
    print("=" * 60)
    print("OriginPro ORR-RDE 批量出图")
    print("=" * 60)

    op.set_show(False)

    print("\n[Fig 1] LSV 曲线叠加图...")
    for group in GROUPS:
        wks = op.new_sheet("w", f"LSV_{group}")
        import_lsv_data(wks, group)
        create_lsv_overlay_plot(wks, group)

    print("\n[Fig 2] 组间对比...")
    create_group_comparison_plot()

    print("\n[Fig 3] K-L 图...")
    for group in GROUPS:
        create_kl_plot_with_fit(group)

    print("\n[Fig 4] Tafel 图 (matplotlib)...")
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    tafel_path = PROJECT_DIR / "output" / "tables" / "tafel_analysis.csv"
    if tafel_path.exists():
        tafel_data = {}
        with open(tafel_path, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                tafel_data[row["group"]] = row

        fig, ax = plt.subplots(figsize=(6, 5))
        labels, slopes = [], []
        for g in GROUPS:
            if g in tafel_data:
                labels.append(CATALYST_NAMES.get(g, g))
                slopes.append(float(tafel_data[g]["tafel_slope_mv_per_dec"]))

        ax.bar(labels, slopes, color=COLORS[: len(labels)], edgecolor="white")
        ax.set_title("Tafel Slope Comparison")
        ax.set_ylabel("Tafel Slope (mV/dec)")
        ax.tick_params(axis="x", rotation=15)
        ax.axhline(y=120, color="blue", linestyle="--", alpha=0.5, label="120 mV/dec (2e-)")
        ax.axhline(y=60, color="red", linestyle="--", alpha=0.5, label="60 mV/dec (4e-)")
        ax.legend()
        plt.tight_layout()
        out = str(OUTPUT_DIR / "Fig4_Tafel_Comparison.png")
        plt.savefig(out, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"  图表已保存: {out}")

    print("\n[Fig 5] 关键参数柱状图...")
    create_bar_chart()

    print("\n所有图表已生成!")
    op.exit()


if __name__ == "__main__":
    main()
