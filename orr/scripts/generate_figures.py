#!/usr/bin/env python3
"""生成 matplotlib 预览图 — LSV叠加 / K-L图 / Tafel图 / 对比柱状图"""

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
from typing import Dict, Any, List
import matplotlib.pyplot as plt
from pathlib import Path

from common import (
    PROJECT_DIR,
    load_params,
    angular_velocity,
    levich_constant,
    compute_jk_corrected,
)

SCRIPT_DIR = Path(__file__).resolve().parent

with open(PROJECT_DIR / "params.yaml", encoding="utf-8") as _f:
    _cfg = load_params()
GROUPS = _cfg["data"]["groups"]
RPMS = _cfg["kl_analysis"]["rotation_speeds_rpm"]
CATALYST_NAMES = _cfg.get("catalysts", {g: g for g in GROUPS})
MERGE_PAIRS = _cfg.get("merge", {}).get("pairs", {})
MERGED_CATALYSTS = list(MERGE_PAIRS.keys())

# 用于图表标注的英文标签（避免 CJK 字体缺失警告）
CATALYST_LABELS = {
    "1组": "Co3O4/C (304SS, Op.A1)",
    "2组": "20% Pt/C (304SS, Op.A2)",
    "3组": "Co3O4/C (316SS, Op.B1)",
    "4组": "20% Pt/C (316SS, Op.B2)",
}

COLORS = ["#E41A1C", "#377EB8", "#4DAF4A", "#984EA3", "#FF7F00", "#A65628"]
STYLES = ["-", "--", "-.", ":", (0, (3, 1)), (0, (5, 2))]

OUTPUT_DIR = PROJECT_DIR / _cfg["output"]["figures_dir"]
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams.update(
    {
        "font.size": 11,
        "axes.titlesize": 13,
        "axes.labelsize": 11,
        "figure.dpi": 150,
        "savefig.dpi": 150,
        "savefig.bbox": "tight",
        "savefig.facecolor": "white",
    }
)


def load_all_data() -> pd.DataFrame:
    return pd.read_csv(PROJECT_DIR / "output" / "processed" / "all_data.csv")


def fig1_lsv_overlay(
    all_df: pd.DataFrame,
    params: Dict[str, Any],
    groups: list[str],
) -> None:
    rhe_offset = params["reference_electrode"]["conversion_to_rhe"]

    for group in groups:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        cat_name = CATALYST_LABELS.get(group, group)

        for i, rpm in enumerate(RPMS):
            mask = (all_df["group"] == group) & (all_df["rpm"] == rpm)
            gdf = all_df[mask]
            if len(gdf) == 0:
                continue
            label = f"{rpm} rpm"

            ax1.plot(
                gdf["potential_v"],
                gdf["current_density_ma_cm2"],
                color=COLORS[i],
                ls=STYLES[i % len(STYLES)],
                lw=1.2,
                label=label,
            )
            ax2.plot(
                gdf["potential_vs_rhe"],
                gdf["current_density_ma_cm2"],
                color=COLORS[i],
                ls=STYLES[i % len(STYLES)],
                lw=1.2,
                label=label,
            )

        for ax, title_suffix, xlabel in [
            (ax1, "vs Hg/HgO", "Potential (V vs Hg/HgO)"),
            (ax2, "vs RHE", "Potential (V vs RHE)"),
        ]:
            ax.set_title(f"{cat_name} - ORR LSV ({title_suffix})")
            ax.set_xlabel(xlabel)
            ax.set_ylabel("Current Density (mA/cm2)")
            ax.legend(fontsize=8, ncol=2)
            ax.grid(True, alpha=0.3)
            ax.axhline(y=0, color="gray", ls="--", alpha=0.3)
            ax.invert_xaxis()

        plt.tight_layout()
        out = str(OUTPUT_DIR / f"Fig1_LSV_{group}.png")
        fig.savefig(out)
        plt.close(fig)
        print(f"  {out}")


def fig2_catalyst_comparison(
    all_df: pd.DataFrame,
    params: Dict[str, Any],
) -> None:
    fig, ax = plt.subplots(figsize=(8, 5.5))
    rhe_offset = params["reference_electrode"]["conversion_to_rhe"]

    for idx, (cat_name, groups) in enumerate(MERGE_PAIRS.items()):
        for gi, group in enumerate(groups):
            mask = (all_df["group"] == group) & (all_df["rpm"] == 1600)
            gdf = all_df[mask]
            if len(gdf) == 0:
                continue
            label = f"{cat_name}" if gi == 0 else None
            ls = "-" if gi == 0 else "--"
            ax.plot(
                gdf["potential_vs_rhe"],
                gdf["current_density_ma_cm2"],
                color=COLORS[idx],
                lw=1.8,
                ls=ls,
                label=label,
            )

    ax.set_title("Catalyst Comparison - ORR LSV @ 1600 rpm (vs RHE)")
    ax.set_xlabel("Potential (V vs RHE)")
    ax.set_ylabel("Current Density (mA/cm2)")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color="gray", ls="--", alpha=0.3)
    ax.invert_xaxis()

    out = str(OUTPUT_DIR / "Fig2_Group_Comparison_1600r.png")
    fig.savefig(out)
    plt.close(fig)
    print(f"  {out}")


def fig3_kl_plots(
    all_df: pd.DataFrame,
    params: Dict[str, Any],
) -> None:
    rhe_offset = params["reference_electrode"]["conversion_to_rhe"]
    potentials = params["kl_analysis"]["potentials_vs_hghgo"]
    speeds = params["kl_analysis"]["rotation_speeds_rpm"]
    tol = float(params["lsv"]["sample_interval_v"]) / 2

    for group in GROUPS:
        fig, ax = plt.subplots(figsize=(7, 5.5))
        cat_name = CATALYST_LABELS.get(group, group)

        for i, pot in enumerate(potentials):
            x_vals: list[float] = []
            y_vals: list[float] = []
            for rpm in speeds:
                mask = (all_df["group"] == group) & (all_df["rpm"] == rpm)
                gdf = all_df[mask]
                if len(gdf) == 0:
                    continue
                omega = angular_velocity(rpm)
                omega_neg_half = omega ** (-0.5)

                pt_mask = (gdf["potential_v"] >= pot - tol) & (gdf["potential_v"] <= pot + tol)
                if pt_mask.any():
                    j = abs(float(gdf.loc[pt_mask, "current_density_ma_cm2"].mean()))
                    if j > 0:
                        x_vals.append(omega_neg_half)
                        y_vals.append(1.0 / j)

            if len(x_vals) >= 3:
                x_arr = np.array(x_vals)
                y_arr = np.array(y_vals)
                from scipy import stats

                slope, intercept, r_val, _, _ = stats.linregress(x_arr, y_arr)
                x_fit = np.linspace(x_arr.min(), x_arr.max(), 50)
                y_fit = slope * x_fit + intercept

                e_rhe = pot + rhe_offset
                label = f"{pot}V ({e_rhe:.2f}V RHE), R2={r_val**2:.3f}"
                ax.scatter(x_arr, y_arr, color=COLORS[i], s=30, zorder=5)
                ax.plot(x_fit, y_fit, color=COLORS[i], ls="--", lw=1.2, label=label)

        ax.set_title(f"{cat_name} - Koutecky-Levich Plot")
        ax.set_xlabel("w-1/2 (s^(1/2)*rad^(-1/2))")
        ax.set_ylabel("j-1 (cm2/mA)")
        ax.legend(fontsize=7.5)
        ax.grid(True, alpha=0.3)

        out = str(OUTPUT_DIR / f"Fig3_KL_{group}.png")
        fig.savefig(out)
        plt.close(fig)
        print(f"  {out}")


def fig4_tafel(
    all_df: pd.DataFrame,
    params: Dict[str, Any],
) -> None:
    rhe_offset = params["reference_electrode"]["conversion_to_rhe"]

    for idx, group in enumerate(GROUPS):
        target_rpm = 1600
        mask = (all_df["group"] == group) & (all_df["rpm"] == target_rpm)
        if mask.sum() == 0:
            for s in RPMS:
                mask = (all_df["group"] == group) & (all_df["rpm"] == s)
                if mask.sum() > 0:
                    target_rpm = s
                    break
        gdf = all_df[mask]
        if len(gdf) == 0:
            continue

        j_col = "current_density_ma_cm2"
        lim_mask = (gdf["potential_v"] >= params["lsv"]["limiting_range"][0]) & (
            gdf["potential_v"] <= params["lsv"]["limiting_range"][1]
        )
        j_lim_val = abs(float(gdf.loc[lim_mask, j_col].mean())) if lim_mask.any() else 1.0

        tafel_range = params["lsv"]["tafel_range"]
        tafel_mask = (gdf["potential_v"] >= tafel_range[0]) & (gdf["potential_v"] <= tafel_range[1])
        tafel_df = gdf[tafel_mask]

        fig, ax = plt.subplots(figsize=(7, 5.5))
        x_vals: list[float] = []
        y_vals: list[float] = []
        for _, row in tafel_df.iterrows():
            j = abs(float(row[j_col]))
            if j < 0.001 or j_lim_val <= 0:
                continue
            j_k = compute_jk_corrected(j, j_lim_val)
            if j_k > 0:
                x_vals.append(float(row["potential_v"]) + rhe_offset)
                y_vals.append(np.log10(j_k))

        if len(x_vals) >= 5:
            from scipy import stats

            slope, intercept, r_val, _, _ = stats.linregress(x_vals, y_vals)
            x_fit = np.linspace(min(x_vals), max(x_vals), 50)
            y_fit = slope * x_fit + intercept
            b_mv = abs(1000 / slope) if slope != 0 else np.nan

            ax.scatter(x_vals, y_vals, s=20, color=COLORS[idx], zorder=5)
            ax.plot(
                x_fit,
                y_fit,
                color="gray",
                ls="--",
                lw=1.5,
                label=f"Tafel slope = {b_mv:.1f} mV/dec, R2={r_val**2:.3f}",
            )

        cat_name = CATALYST_LABELS.get(group, group)
        ax.set_title(f"{cat_name} - Tafel Plot @ {target_rpm} rpm")
        ax.set_xlabel("E (V vs RHE)")
        ax.set_ylabel("log|j_k| (mA/cm2)")
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.invert_xaxis()

        out = str(OUTPUT_DIR / f"Fig4_Tafel_{group}.png")
        fig.savefig(out)
        plt.close(fig)
        print(f"  {out}")


def fig5_bar_chart(params: Dict[str, Any]) -> None:
    comp_path = PROJECT_DIR / params["output"]["tables_dir"] / "group_comparison.csv"
    if not comp_path.exists():
        print("  组间对比表不存在，跳过柱状图")
        return

    comp_df = pd.read_csv(comp_path)

    if not MERGED_CATALYSTS:
        print("  无平行样合并配置，跳过柱状图")
        return

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    cats = list(MERGED_CATALYSTS)
    bar_colors = COLORS[: len(cats)]

    def parse_err(val: str) -> tuple[float, float]:
        parts = val.split(" +/- ")
        v = abs(float(parts[0]))
        e = abs(float(parts[1])) if len(parts) > 1 else 0.0
        return v, e

    e_half = []
    e_half_err = []
    j_lim = []
    j_lim_err = []
    n_vals = []
    n_errs = []
    for _, row in comp_df.iterrows():
        eh, ehe = parse_err(str(row["E_1/2 (V vs RHE)"]))
        jl, jle = parse_err(str(row["|j_L| (mA/cm2) @1600r"]))
        nv, ne = parse_err(str(row["n (电子转移数)"]))
        e_half.append(eh)
        e_half_err.append(ehe)
        j_lim.append(jl)
        j_lim_err.append(jle)
        n_vals.append(nv)
        n_errs.append(ne)

    axes[0].bar(
        cats, e_half, yerr=e_half_err, color=bar_colors, edgecolor="white", linewidth=0.5, capsize=4
    )
    axes[0].set_title("Half-wave Potential E1/2")
    axes[0].set_ylabel("E1/2 (V vs RHE)")
    axes[0].tick_params(axis="x", rotation=10)
    for i, v in enumerate(e_half):
        axes[0].text(i, v + e_half_err[i] + 0.005, f"{v:.3f}", ha="center", fontsize=8)

    axes[1].bar(
        cats, j_lim, yerr=j_lim_err, color=bar_colors, edgecolor="white", linewidth=0.5, capsize=4
    )
    axes[1].set_title("Limiting Current Density @1600 rpm")
    axes[1].set_ylabel("|j_L| (mA/cm2)")
    axes[1].tick_params(axis="x", rotation=10)
    for i, v in enumerate(j_lim):
        axes[1].text(i, v + j_lim_err[i] + 0.05, f"{v:.2f}", ha="center", fontsize=8)

    axes[2].bar(
        cats, n_vals, yerr=n_errs, color=bar_colors, edgecolor="white", linewidth=0.5, capsize=4
    )
    axes[2].set_title("Electron Transfer Number (n)")
    axes[2].set_ylabel("n")
    axes[2].axhline(y=params["kl_analysis"]["n_theoretical_4e"], color="red", ls="--", alpha=0.6, label="n=4 (4e- pathway)")
    axes[2].axhline(y=params["kl_analysis"]["n_theoretical_2e"], color="blue", ls="--", alpha=0.6, label="n=2 (2e- pathway)")
    axes[2].legend(fontsize=8)
    axes[2].tick_params(axis="x", rotation=10)
    for i, (v, e) in enumerate(zip(n_vals, n_errs)):
        axes[2].text(i, v + e + 0.1, f"{v:.1f}", ha="center", fontsize=8)

    plt.tight_layout()
    out = str(OUTPUT_DIR / "Fig5_Key_Parameters_Bar.png")
    fig.savefig(out)
    plt.close(fig)
    print(f"  {out}")


def main() -> None:
    print("=" * 60)
    print("生成 matplotlib 预览图")
    print("=" * 60)

    params = load_params()
    all_df = load_all_data()

    print("\n[Fig 1] LSV 曲线叠加图...")
    fig1_lsv_overlay(all_df, params, GROUPS)

    print("\n[Fig 2] 催化剂对比图...")
    fig2_catalyst_comparison(all_df, params)

    print("\n[Fig 3] K-L 图...")
    fig3_kl_plots(all_df, params)

    print("\n[Fig 4] Tafel 图...")
    fig4_tafel(all_df, params)

    print("\n[Fig 5] 关键参数柱状图...")
    fig5_bar_chart(params)

    print(f"\n全部图表已保存到 {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
