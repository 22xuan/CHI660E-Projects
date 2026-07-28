#!/usr/bin/env python3
"""Randles R(QR) CNLS拟合 — 两步法（Rs固定, 3参数拟合）"""

import yaml, pandas as pd, numpy as np, matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
with open(PROJECT_DIR / "params.yaml", encoding="utf-8") as f:
    CFG = yaml.safe_load(f)

OUT_DIR = PROJECT_DIR / CFG["output"]["figures_dir"]
TAB_DIR = PROJECT_DIR / CFG["output"]["tables_dir"]
TAB_DIR.mkdir(parents=True, exist_ok=True)
CONDS = CFG["experiment"]["conditions"]
C = ["#E41A1C", "#377EB8"]


def randles_Z(freq, Rs, Rp, Q, n):
    omega = 2 * np.pi * freq
    Z = Rs + Rp / (1 + Rp * Q * (1j * omega) ** n)
    return np.concatenate([Z.real, -Z.imag])


def fit_randles(df):
    mask = (df["freq_Hz"] >= 0.05) & (df["freq_Hz"] <= 30000)
    d = df[mask].copy()
    logf = np.log10(d["freq_Hz"])
    bins = np.linspace(logf.min(), logf.max(), 150)
    idxs = sorted(set(np.argmin(np.abs(logf - b)) for b in bins))
    d = d.iloc[idxs]
    print(f"  拟合点数: {len(d)}")

    n_top = max(5, len(d) // 15)
    top = d.iloc[:n_top]
    rs = float(top.loc[top["Zim_ohm_cm2"].abs().idxmin(), "Zre_ohm_cm2"])
    bot = d.iloc[-n_top:]
    rp0 = max(float(bot["Zre_ohm_cm2"].mean()) - rs, 100.0)

    p_iloc = int(d["Zim_ohm_cm2"].values.argmax())
    fp = float(d["freq_Hz"].iloc[p_iloc])
    n0 = 0.70
    q0 = 1.0 / (rp0 * (2 * np.pi * fp) ** n0)
    q0 = max(min(q0, 1e-1), 1e-12)
    print(f"  Rs(fixed)={rs:.1f}, Rp0={rp0:.0f}, Q0={q0:.3e}, n0={n0:.3f}")

    freq = d["freq_Hz"].values
    z_exp = np.concatenate([d["Zre_ohm_cm2"].values, d["Zim_ohm_cm2"].values])
    weight = 1.0 / np.maximum(np.abs(d["Zmod_ohm_cm2"].values), 1e-6)
    sigma = np.concatenate([weight, weight])

    def _3p(f, Rp, Q, n):
        return randles_Z(f, rs, Rp, Q, n)

    try:
        popt, _ = curve_fit(
            _3p,
            freq,
            z_exp,
            p0=[rp0, q0, n0],
            sigma=sigma,
            bounds=([0.1, 1e-15, 0.2], [1e8, 1e0, 1.0]),
            maxfev=30000,
        )
        Rp, Q, n = popt
        zf = randles_Z(freq, rs, Rp, Q, n)
        m = len(zf) // 2
        res = z_exp - zf
        chi2 = np.sum((res / sigma) ** 2) / (len(z_exp) - 3)
        re = float(np.nanmean(np.abs(res / np.maximum(np.abs(z_exp), 1e-6))) * 100)
    except Exception as e:
        print(f"  拟合异常: {e}")
        return {
            "Rs": np.nan,
            "Rp": np.nan,
            "Q": np.nan,
            "n": np.nan,
            "chi2": np.nan,
            "rel_err_pct": np.nan,
        }

    return {
        "Rs": round(rs, 1),
        "Rp": round(Rp, 0),
        "Q": float(Q),
        "n": round(n, 4),
        "chi2": round(chi2, 2),
        "rel_err_pct": round(re, 1),
        "zre_fit": zf[:m],
        "zim_fit": zf[m:],
    }


def plot_fit(df, result, label, color):
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.scatter(
        df["Zre_ohm_cm2"], -df["Zim_ohm_cm2"], s=5, color=color, alpha=0.4, zorder=5, label="Data"
    )
    if "zre_fit" in result and not np.isnan(result.get("Rs", np.nan)):
        ax.plot(result["zre_fit"], result["zim_fit"], "k--", lw=1.5, label="Randles fit")
    r = result
    ax.set_title(
        f"Randles R(QR) Fit — pH {label}\nRs={r['Rs']:.1f}, Rp={r['Rp']:.0f}, Q={r['Q']:.2e}, n={r['n']:.4f}, $\\chi^2$={r['chi2']:.1f}\nNote: simple Randles; R(QR)(QR) may fit better",
        fontsize=8.5,
    )
    ax.set_xlabel("Re(Z) (Ω·cm²)")
    ax.set_ylabel("-Im(Z) (Ω·cm²)")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.set_aspect("equal")
    plt.tight_layout()
    fig.savefig(str(OUT_DIR / f"Fit_{label}.png"))
    plt.close()
    print(f"  Fit_{label}.png")


def main():
    print("=" * 40)
    print("Randles R(QR) 等效电路拟合")
    print("=" * 40)
    records = []
    for idx, cond in enumerate(CONDS):
        label = cond["label"]
        df = pd.read_csv(PROJECT_DIR / CFG["output"]["processed_dir"] / f"eis_{label}.csv")
        print(f"\n{label} (pH {cond['pH']}):")
        r = fit_randles(df)
        ok = not np.isnan(r.get("Rs", np.nan))
        print(
            f"  Rs={r['Rs']:.1f} (fixed), Rp={r['Rp']:.0f}, n={r['n']:.4f}, χ²={r['chi2']:.2f}"
            if ok
            else "  未收敛"
        )
        plot_fit(df, r, label, C[idx])
        records.append(
            {"pH": cond["pH"], **{k: v for k, v in r.items() if k not in ("zre_fit", "zim_fit")}}
        )

    dfp = pd.DataFrame(records)
    dfp.to_csv(TAB_DIR / "eis_parameters.csv", index=False, encoding="utf-8-sig")
    print(f"\n参数表: {TAB_DIR / 'eis_parameters.csv'}")
    print(dfp.to_string(index=False))


if __name__ == "__main__":
    main()
