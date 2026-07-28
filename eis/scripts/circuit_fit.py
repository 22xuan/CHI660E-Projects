#!/usr/bin/env python3
"""R(Q(RW)) CNLS拟合 — CO2 腐蚀 FeCO3 层扩散模型"""

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


def Z_RQRW(freq, Rs, Q1, n1, R1, W, P):
    omega = 2 * np.pi * freq
    Zcpe = 1.0 / (Q1 * (1j * omega) ** n1)
    Zw = W * (1j * omega) ** (-P)
    Z = Rs + 1.0 / (1.0 / Zcpe + 1.0 / (R1 + Zw))
    return np.concatenate([Z.real, -Z.imag])


def prepare_data(df):
    """对数降采样 + 异常值剔除"""
    mask = (df["freq_Hz"] >= 0.02) & (df["freq_Hz"] <= 30000)
    d = df[mask].copy()
    # Remove high-freq outliers / 移除高频异常值
    hi = d[d["freq_Hz"] > 1000]
    med = hi["Zre_ohm_cm2"].median()
    hi_ok = (hi["Zre_ohm_cm2"] > 0) & (hi["Zre_ohm_cm2"] < 3 * med) & (hi["Zim_ohm_cm2"] > 0)
    hi = hi[hi_ok]
    lo = d[d["freq_Hz"] <= 1000]
    d = pd.concat([hi, lo])
    # Log downsample / 对数降采样
    logf = np.log10(d["freq_Hz"])
    bins = np.linspace(logf.min(), logf.max(), 80)
    idxs = sorted(set(np.argmin(np.abs(logf - b)) for b in bins))
    d = d.iloc[idxs].reset_index(drop=True)
    return d


def fit_RQRW(df):
    d = prepare_data(df)
    print(f"  拟合点数: {len(d)} (清洗+降采样后)")

    freq = d["freq_Hz"].values
    z_exp = np.concatenate([d["Zre_ohm_cm2"].values, d["Zim_ohm_cm2"].values])
    wgt = 1.0 / np.maximum(np.abs(d["Zmod_ohm_cm2"].values), 1e-6)
    sigma = np.concatenate([wgt, wgt])

    # Step 1: Rs from high freq
    n_top = max(3, len(d) // 10)
    top = d.iloc[:n_top]
    rs0 = float(top.loc[top["Zim_ohm_cm2"].abs().idxmin(), "Zre_ohm_cm2"])
    rs0 = max(rs0, 1.0)

    # Step 2: R1, Q1, n1 — fit high-freq arc only (f > 0.5 Hz)
    hi_mask = d["freq_Hz"] > 0.5
    dh = d[hi_mask]
    if len(dh) < 10:
        dh = d
    zh = np.concatenate([dh["Zre_ohm_cm2"].values, dh["Zim_ohm_cm2"].values])
    sh = 1.0 / np.maximum(np.abs(dh["Zmod_ohm_cm2"].values), 1e-6)
    sh = np.concatenate([sh, sh])
    fh = dh["freq_Hz"].values

    r10 = max(float(d["Zre_ohm_cm2"].iloc[-len(d) // 10 :].mean()) - rs0, 100.0)
    n10 = 0.60
    # Q estimate from where Zim is large
    mid = d.iloc[len(d) // 3 : 2 * len(d) // 3]
    p_iloc = int(mid["Zim_ohm_cm2"].values.argmax())
    fp = float(mid["freq_Hz"].iloc[p_iloc])
    q10 = 1.0 / (r10 * (2 * np.pi * fp) ** n10)
    q10 = max(min(q10, 0.1), 1e-12)

    def _RQ(f, R1, Q1, n1):
        return Z_RQRW(f, rs0, Q1, n1, R1, 0, 0.5)

    print(f"  Step2 (R(QR)): Rs={rs0:.1f}, R10={r10:.0f}, Q10={q10:.3e}, n10={n10:.3f}")
    try:
        popt2, _ = curve_fit(
            _RQ,
            fh,
            zh,
            p0=[r10, q10, n10],
            sigma=sh,
            bounds=([0.1, 1e-15, 0.2], [1e8, 1e0, 1.0]),
            maxfev=20000,
        )
        r_1, q_1, n_1 = popt2
        residuals2 = zh - _RQ(fh, *popt2)
        chi2_rq = np.sum((residuals2 / sh) ** 2) / (len(zh) - 3)
        ok = chi2_rq < 1e6
    except Exception as e:
        print(f"  R(QR)失败: {e}, 降级处理")
        r_1, q_1, n_1 = r10, q10, n10
        ok = False

    # Step 3: Add Warburg, fit full spectrum
    w0 = r_1 * 10 if r_1 > 0 else 1000
    p0 = 0.50

    print(f"  Step3 (+Warburg): R1={r_1:.0f}, Q1={q_1:.3e}, n1={n_1:.3f}, W0={w0:.0f}, P0={p0:.2f}")

    def _full(f, R1, Q1, n1, W, P):
        return Z_RQRW(f, rs0, Q1, n1, R1, W, P)

    try:
        popt3, _ = curve_fit(
            _full,
            freq,
            z_exp,
            p0=[r_1, q_1, n_1, w0, p0],
            sigma=sigma,
            bounds=([0.1, 1e-15, 0.2, 0.1, 0.2], [1e8, 1e0, 1.0, 1e8, 0.8]),
            maxfev=30000,
        )
        R1_f, Q1_f, n1_f, W_f, P_f = popt3
        zf = Z_RQRW(freq, rs0, Q1_f, n1_f, R1_f, W_f, P_f)
        m = len(zf) // 2
        res = z_exp - zf
        chi2 = np.sum((res / sigma) ** 2) / (len(z_exp) - 5)
        re = float(np.nanmean(np.abs(res / np.maximum(np.abs(z_exp), 1e-6))) * 100)
    except Exception as e:
        print(f"  全谱拟合失败: {e}")
        R1_f, Q1_f, n1_f = r_1, q_1, n_1
        W_f, P_f = 0.0, 0.5
        chi2 = np.nan
        re = np.nan
        zf = None

    return {
        "Rs": round(rs0, 1),
        "Q1": float(Q1_f),
        "n1": round(n1_f, 4),
        "R1": round(R1_f, 0),
        "W": round(W_f, 0),
        "P": round(P_f, 4),
        "chi2": round(float(chi2), 2) if not np.isnan(chi2) else "N/A",
        "rel_err_pct": round(float(re), 1) if not np.isnan(re) else "N/A",
        "zre_fit": zf[: len(zf) // 2] if zf is not None else None,
        "zim_fit": zf[len(zf) // 2 :] if zf is not None else None,
        "R_total": round(R1_f + W_f, 0) if not np.isnan(W_f) else round(R1_f, 0),
    }


def plot_fit(df, result, label, color):
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.scatter(
        df["Zre_ohm_cm2"], -df["Zim_ohm_cm2"], s=5, color=color, alpha=0.35, zorder=5, label="Data"
    )
    if result.get("zre_fit") is not None:
        ax.plot(result["zre_fit"], result["zim_fit"], "k-", lw=1.8, label="R(Q(RW)) fit")
    r = result
    title = (
        f"R(Q(RW)) Fit — pH {label}\n"
        f"Rs={r['Rs']:.1f}, Q1={r['Q1']:.2e}, n1={r['n1']:.4f}, R1={r['R1']:.0f}\n"
        f"W={r['W']:.0f}, P={r['P']:.4f}, R_total={r['R_total']:.0f} $\\Omega\\cdot$cm$^2$, $\\chi^2={r['chi2']}$"
    )
    ax.set_title(title, fontsize=9)
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
    print("R(Q(RW)) 等效电路拟合")
    print("=" * 40)
    records = []
    for idx, cond in enumerate(CONDS):
        label = cond["label"]
        df = pd.read_csv(PROJECT_DIR / CFG["output"]["processed_dir"] / f"eis_{label}.csv")
        print(f"\n{label} (pH {cond['pH']}):")
        r = fit_RQRW(df)
        ok = isinstance(r["chi2"], float)
        print(
            f"  Rs={r['Rs']:.1f}, R1={r['R1']:.0f}, W={r['W']:.0f}, P={r['P']:.4f}, R_total={r['R_total']:.0f}, χ²={r['chi2']}"
            if ok
            else f"  Rs={r['Rs']:.1f}, R1={r['R1']:.0f} (拟合未收敛)"
        )
        plot_fit(df, r, label, C[idx])
        records.append(
            {"pH": cond["pH"], **{k: v for k, v in r.items() if k not in ("zre_fit", "zim_fit")}}
        )

    dfp = pd.DataFrame(records)
    dfp.to_csv(TAB_DIR / "eis_parameters.csv", index=False, encoding="utf-8-sig")
    print(f"\n参数表: {TAB_DIR / 'eis_parameters.csv'}")
    print(dfp.to_string(index=False))

    lpr_csv = TAB_DIR / "lpr_results.csv"
    if lpr_csv.exists():
        lpr_df = pd.read_csv(lpr_csv)
        print("\nLPR-EIS 交叉验证:")
        for _, row in lpr_df.iterrows():
            ph = row["pH"]
            rp_lpr = row["Rp_LPR_ohm_cm2"]
            eis_row = dfp[dfp["pH"] == ph]
            if len(eis_row) > 0:
                r_total = eis_row.iloc[0]["R_total"]
                dev = abs(rp_lpr - r_total) / max(rp_lpr, r_total) * 100
                print(
                    f"  pH {ph}: Rp(LPR)={rp_lpr:.0f}, R_total(EIS)={r_total:.0f}, 偏差={dev:.0f}%"
                )


if __name__ == "__main__":
    main()
