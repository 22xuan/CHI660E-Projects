#!/usr/bin/env python3
"""Nyquist + Bode 图 — CO2 腐蚀 EIS"""

import yaml
import pandas as pd
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent

with open(PROJECT_DIR / "params.yaml", encoding="utf-8") as f:
    CFG = yaml.safe_load(f)

OUT_DIR = PROJECT_DIR / CFG["output"]["figures_dir"]
OUT_DIR.mkdir(parents=True, exist_ok=True)
CONDS = CFG["experiment"]["conditions"]
COLORS = ["#E41A1C", "#377EB8"]

plt.rcParams.update(
    {"font.size": 11, "figure.dpi": 150, "savefig.dpi": 150, "savefig.bbox": "tight"}
)


def fig1_nyquist() -> None:
    fig, ax = plt.subplots(figsize=(7, 6))
    for idx, cond in enumerate(CONDS):
        df = pd.read_csv(PROJECT_DIR / CFG["output"]["processed_dir"] / f"eis_{cond['label']}.csv")
        # Filter noise: Zre > 0, Zim > -100
        ok = (df["Zre_ohm_cm2"] > 0) & (df["Zim_ohm_cm2"] > -100)
        d = df[ok].copy()
        # Log downsample to ~200 pts for clean Nyquist curve
        if len(d) > 200:
            logf = np.log10(d["freq_Hz"].values)
            bins = np.linspace(logf.min(), logf.max(), 200)
            idxs = sorted(set(np.argmin(np.abs(logf - b)) for b in bins))
            d = d.iloc[idxs]
        ax.plot(
            d["Zre_ohm_cm2"],
            -d["Zim_ohm_cm2"],
            ".-",
            color=COLORS[idx],
            ms=2,
            lw=1.0,
            label=f"pH {cond['pH']}",
        )

        # Rs: Zre where |Zim| is minimum in high-freq range
        high = d[d["freq_Hz"] > 1000]
        if len(high) > 0:
            rs = high.loc[high["Zim_ohm_cm2"].abs().idxmin(), "Zre_ohm_cm2"]
        else:
            rs = d["Zre_ohm_cm2"].iloc[:10].min()
        ax.annotate(
            f"Rs={rs:.1f}",
            xy=(rs, 0),
            xytext=(rs + 20, 15),
            arrowprops=dict(arrowstyle="->", color=COLORS[idx]),
            fontsize=9,
            color=COLORS[idx],
        )

    ax.set_xlabel("Re(Z) (Ω·cm²)")
    ax.set_ylabel("-Im(Z) (Ω·cm²)")
    ax.set_title("Nyquist Plot — Low Alloy Steel CO₂ Corrosion")
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.set_aspect("equal")

    plt.tight_layout()
    fig.savefig(str(OUT_DIR / "Fig1_Nyquist.pdf"))
    plt.close()
    print("  Fig1_Nyquist.pdf")


def fig2_bode() -> None:
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 7), sharex=True)
    for idx, cond in enumerate(CONDS):
        df = pd.read_csv(PROJECT_DIR / CFG["output"]["processed_dir"] / f"eis_{cond['label']}.csv")
        ax1.loglog(
            df["freq_Hz"],
            df["Zmod_ohm_cm2"],
            "-",
            color=COLORS[idx],
            lw=1.5,
            label=f"pH {cond['pH']}",
        )
        ax2.semilogx(
            df["freq_Hz"],
            -df["Phase_deg"],
            "-",
            color=COLORS[idx],
            lw=1.5,
            label=f"pH {cond['pH']}",
        )

    ax1.set_ylabel("|Z| (Ω·cm²)")
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax2.set_xlabel("Frequency (Hz)")
    ax2.set_ylabel("-Phase (deg)")
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)
    fig.suptitle("Bode Plot — Low Alloy Steel CO₂ Corrosion", fontsize=13)

    plt.tight_layout()
    fig.savefig(str(OUT_DIR / "Fig2_Bode.pdf"))
    plt.close()
    print("  Fig2_Bode.pdf")


def main() -> None:
    print("=" * 40)
    print("EIS 图表生成")
    print("=" * 40)
    fig1_nyquist()
    fig2_bode()
    print(f"\n图表保存在 {OUT_DIR}")


if __name__ == "__main__":
    main()
