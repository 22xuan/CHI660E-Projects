#!/usr/bin/env python3
"""生成 matplotlib 图表: Levich / 浓度校准 / K-L / Tafel / 半波电位"""

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from scipy import stats
import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent

with open(PROJECT_DIR / "params.yaml", encoding="utf-8") as f:
    CFG = yaml.safe_load(f)

OUTPUT_DIR = PROJECT_DIR / CFG["output"]["figures_dir"]
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TABLES_DIR = PROJECT_DIR / CFG["output"]["tables_dir"]
COLORS = ["#E41A1C", "#377EB8", "#4DAF4A", "#984EA3", "#FF7F00", "#A65628"]
GLABEL = {"1组": "Grp1", "2组": "Grp2", "3组": "Grp3", "4组": "Grp4"}

plt.rcParams.update(
    {"font.size": 11, "figure.dpi": 150, "savefig.dpi": 150, "savefig.bbox": "tight"}
)


def fig1_levich() -> None:
    lc = pd.read_csv(TABLES_DIR / "limiting_currents.csv")
    groups = CFG["data"]["groups"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    for idx, g in enumerate(groups):
        gdf = lc[lc["group"] == g].dropna(subset=["abs_i_cathode_A"])
        if len(gdf) >= 3:
            x, y = gdf["omega_sqrt"].values, gdf["abs_i_cathode_A"].values
            s, _, r, _, _ = stats.linregress(x, y)
            ax1.scatter(x, y, color=COLORS[idx], s=30, zorder=5)
            xf = np.linspace(x.min(), x.max(), 50)
            ax1.plot(
                xf, s * xf, "--", color=COLORS[idx], lw=1.2, label=f"Op.{GLABEL[g]} (R2={r**2:.3f})"
            )

        gdf = lc[lc["group"] == g].dropna(subset=["abs_i_anode_A"])
        if len(gdf) >= 3:
            x, y = gdf["omega_sqrt"].values, gdf["abs_i_anode_A"].values
            s, _, r, _, _ = stats.linregress(x, y)
            ax2.scatter(x, y, color=COLORS[idx], s=30, zorder=5)
            xf = np.linspace(x.min(), x.max(), 50)
            ax2.plot(
                xf, s * xf, "--", color=COLORS[idx], lw=1.2, label=f"Op.{GLABEL[g]} (R2={r**2:.3f})"
            )

    ax1.set_title("Levich Plot — Cathodic |i_l| vs omega^(1/2)")
    ax1.set_xlabel("omega^(1/2) (rad^(1/2)/s^(1/2))")
    ax1.set_ylabel("|i_l,c| (A)")
    ax1.legend(fontsize=8)
    ax1.grid(True, alpha=0.3)

    ax2.set_title("Levich Plot — Anodic |i_l| vs omega^(1/2)")
    ax2.set_xlabel("omega^(1/2) (rad^(1/2)/s^(1/2))")
    ax2.set_ylabel("|i_l,a| (A)")
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(str(OUTPUT_DIR / "Fig1_Levich.png"))
    plt.close()
    print("  Fig1_Levich.png")


def fig2_concentration() -> None:
    cal = pd.read_csv(TABLES_DIR / "concentration_cal.csv")
    groups = CFG["data"]["groups"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    for idx, g in enumerate(groups):
        gdf = cal[cal["group"] == g]
        ax1.plot(
            gdf["concentration_M"],
            gdf["abs_i_cathode_A"],
            "o-",
            color=COLORS[idx],
            ms=5,
            label=f"Op.{GLABEL[g]}",
        )
        ax2.plot(
            gdf["concentration_M"],
            gdf["abs_i_anode_A"],
            "o-",
            color=COLORS[idx],
            ms=5,
            label=f"Op.{GLABEL[g]}",
        )

    for ax, title in [(ax1, "Cathodic |i_l| vs c*"), (ax2, "Anodic |i_l| vs c*")]:
        ax.set_title(title)
        ax.set_xlabel("c* (mol/L)")
        ax.set_ylabel("|i_l| (A)")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(str(OUTPUT_DIR / "Fig2_Concentration.png"))
    plt.close()
    print("  Fig2_Concentration.png")


def fig3_kl() -> None:
    kl_raw = pd.read_csv(TABLES_DIR / "kl_raw_points.csv")
    kl_fit = pd.read_csv(TABLES_DIR / "kl_analysis.csv")
    if len(kl_raw) == 0:
        return

    groups = kl_raw["group"].unique()
    etas = sorted(kl_raw["eta_mV"].unique())
    n_etas = len(etas)

    for g in groups:
        fig, ax = plt.subplots(figsize=(8, 6))
        g_raw = kl_raw[kl_raw["group"] == g]
        g_fit = kl_fit[kl_fit["group"] == g]

        for i, eta in enumerate(etas):
            edf = g_raw[g_raw["eta_mV"] == eta]
            if len(edf) < 3:
                continue
            ax.scatter(edf["omega_neg_half"], edf["i_inv_A"], color=COLORS[i], s=25, zorder=5)

            # 拟合线
            ef = g_fit[g_fit["eta_mV"] == eta]
            if len(ef) > 0:
                x_arr = edf["omega_neg_half"].values
                y_pred = ef["slope"].values[0] * x_arr + ef["intercept"].values[0]
                ax.plot(
                    x_arr,
                    y_pred,
                    "--",
                    color=COLORS[i],
                    lw=1.2,
                    label=f"eta={eta}mV (R2={ef['r_squared'].values[0]:.3f})",
                )

        ax.set_title(f"Op.{GLABEL[g]} — Koutecky-Levich Plot")
        ax.set_xlabel("omega^(-1/2) (s^(1/2)/rad^(1/2))")
        ax.set_ylabel("i^(-1) (A^(-1))")
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        fig.savefig(str(OUTPUT_DIR / f"Fig3_KL_{g}.png"))
        plt.close()
        print(f"  Fig3_KL_{g}.png")


def fig4_tafel() -> None:
    tafel_raw = pd.read_csv(TABLES_DIR / "tafel_raw_points.csv")
    tafel_res = pd.read_csv(TABLES_DIR / "tafel_results.csv")
    if len(tafel_raw) == 0:
        return

    groups = tafel_raw["group"].unique()
    for g in groups:
        fig, ax = plt.subplots(figsize=(7, 5.5))
        g_raw = tafel_raw[tafel_raw["group"] == g]
        gr = tafel_res[tafel_res["group"] == g]

        ax.scatter(g_raw["log_ik"], g_raw["eta_mV"], s=30, color=COLORS[0], zorder=5)

        if len(gr) > 0:
            b = gr["tafel_slope_mV_per_dec"].values[0]
            r2 = gr["r_squared"].values[0]
            slope = gr["fit_slope"].values[0]
            intercept = gr["fit_intercept"].values[0]
            x_fit = np.linspace(g_raw["log_ik"].min(), g_raw["log_ik"].max(), 50)
            y_fit = slope * x_fit + intercept
            ax.plot(x_fit, y_fit, "k--", lw=1.5, label=f"b = {b:.1f} mV/dec (R2={r2:.3f})")

        # 参考线 a=0.5
        x_ref = np.linspace(g_raw["log_ik"].min(), g_raw["log_ik"].max(), 50)
        ax.plot(
            x_ref, 118 * x_ref, "gray", lw=1, alpha=0.5, ls=":", label="b=118 mV/dec (alpha=0.5)"
        )

        ax.set_title(f"Op.{GLABEL[g]} — Tafel Plot")
        ax.set_xlabel("log|i_k| (A)")
        ax.set_ylabel("eta (mV)")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        fig.savefig(str(OUTPUT_DIR / f"Fig4_Tafel_{g}.png"))
        plt.close()
        print(f"  Fig4_Tafel_{g}.png")


def fig5_half_wave() -> None:
    all_df = pd.read_csv(PROJECT_DIR / CFG["output"]["processed_dir"] / "all_data.csv")
    hw = pd.read_csv(TABLES_DIR / "half_wave.csv")
    groups = CFG["data"]["groups"]

    for g in groups:
        key = f"NoKCl_{g}"
        mask = all_df["key"] == key
        df = all_df[mask]
        if len(df) == 0:
            continue
        gh = hw[hw["group"] == g]

        fig, ax = plt.subplots(figsize=(7, 5))
        ax.plot(df["potential_v"], df["current_a"], "-", color=COLORS[0], lw=1.5)

        if len(gh) > 0:
            e0 = gh["E0_V"].values[0]
            e12 = gh["E1_2_V"].values[0]
            ylim = ax.get_ylim()
            ax.axvline(x=e0, color="green", ls="--", lw=1, label=f"E0 = {e0:.4f} V")
            ax.axvline(x=e12, color="red", ls="--", lw=1, label=f"E1/2 = {e12:.4f} V")
            ax.set_ylim(ylim)

        ax.set_title(f"Op.{GLABEL[g]} — 0.0008M (No KCl) Polarization Curve")
        ax.set_xlabel("Potential (V)")
        ax.set_ylabel("Current (A)")
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        fig.savefig(str(OUTPUT_DIR / f"Fig5_HalfWave_{g}.png"))
        plt.close()
        print(f"  Fig5_HalfWave_{g}.png")


def main() -> None:
    print("=" * 40)
    print("生成图表")
    print("=" * 40)
    fig1_levich()
    fig2_concentration()
    fig3_kl()
    fig4_tafel()
    fig5_half_wave()
    print(f"\n图表保存在 {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
