#!/usr/bin/env python3
"""误差传播分析 — 评估各参数不确定度对扩散系数的影响"""

import numpy as np
import pandas as pd
from pathlib import Path
from common import load_params

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent


def error_propagation(params):
    F, A, nu, cstar = (
        params["electrolyte"]["faraday_constant"],
        params["electrode"]["area_for_j"],
        params["electrolyte"]["viscosity_cm2_per_s"],
        params["concentrations"]["values_mol_per_L"][-1] * 1e-3,
    )
    D_O = params["levich"]["D_O_literature_cm2_per_s"]
    D_R = params["levich"]["D_R_literature_cm2_per_s"]

    # Read actual Levich slope from limiting_currents.csv
    levich_slope = D_O  # placeholder replaced below if slope data available
    try:
        lc = pd.read_csv(PROJECT_DIR / params["output"]["tables_dir"] / "limiting_currents.csv")
        g1 = lc[lc["group"] == lc["group"].unique()[0]].dropna(subset=["abs_i_cathode_A"])
        if len(g1) > 0:
            from scipy import stats as _st

            s, _, _, _, _ = _st.linregress(g1["omega_sqrt"], g1["abs_i_cathode_A"])
            levich_slope = s
    except Exception:
        pass

    params_def = [
        ("c* (mol/cm3)", cstar, 0.05, "浓度称量"),
        ("A (cm2)", A, 0.03, "电极几何面积"),
        ("nu (cm2/s)", nu, 0.02, "粘度文献值"),
        ("slope (Levich)", levich_slope, 0.01, "极限电流拟合"),
    ]

    records = []
    for name, nominal, rel_unc, source in params_def:
        if name.startswith("c*"):
            dD_dp = -(3 / 2) * D_O / nominal if nominal else 0
        elif name.startswith("A"):
            dD_dp = -(3 / 2) * D_O / nominal if nominal else 0
        elif name.startswith("nu"):
            dD_dp = (1 / 4) * D_O / nominal if nominal else 0
        elif name.startswith("slope"):
            dD_dp = (3 / 2) * D_O / nominal if nominal else 0
        else:
            dD_dp = 0

        delta_D_rel = abs(dD_dp * nominal * rel_unc / D_O) if D_O and nominal else 0
        records.append(
            {
                "parameter": name,
                "nominal_value": f"{nominal:.3e}" if nominal else "N/A",
                "rel_uncertainty_pct": f"{rel_unc * 100:.0f}",
                "source": source,
                "delta_D_pct": f"{delta_D_rel * 100:.1f}",
                "explains_D_O_deviation": f"{delta_D_rel * 100 / 14 * 100:.0f}%"
                if delta_D_rel
                else "-",
            }
        )

    df = pd.DataFrame(records)
    return df


def main():
    params = load_params()
    df = error_propagation(params)
    out = PROJECT_DIR / params["output"]["tables_dir"] / "error_propagation.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(df.to_string(index=False))
    print(f"\n已保存到 {out}")


if __name__ == "__main__":
    main()
