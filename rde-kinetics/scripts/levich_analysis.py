#!/usr/bin/env python3
"""Levich 分析 — 极限电流 vs ω¹/² → 扩散系数 D_O, D_R"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Tuple
from scipy import stats
from common import load_params, angular_velocity

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent


def extract_limiting_currents(all_df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    groups = params["data"]["groups"]
    speeds = params["rotation_speeds_rpm"]
    cat_lo, cat_hi = params["limiting_current"]["cathode_range"]
    ano_lo, ano_hi = params["limiting_current"]["anode_range"]

    records = []
    for group in groups:
        # 提取基线 (KCl only, 2000rpm)
        bkey = f"Baseline_{group}"
        bl_df = all_df[all_df["key"] == bkey]
        bl_cat = (
            float(
                bl_df.loc[
                    (bl_df["potential_v"] >= cat_lo) & (bl_df["potential_v"] <= cat_hi), "current_a"
                ].mean()
            )
            if len(bl_df) > 0
            else 0.0
        )
        bl_ano = (
            float(
                bl_df.loc[
                    (bl_df["potential_v"] >= ano_lo) & (bl_df["potential_v"] <= ano_hi), "current_a"
                ].mean()
            )
            if len(bl_df) > 0
            else 0.0
        )

        for rpm in speeds:
            key = f"PartA_{group}_{rpm}rpm"
            df = all_df[all_df["key"] == key]
            if len(df) == 0:
                continue

            cmask = (df["potential_v"] >= cat_lo) & (df["potential_v"] <= cat_hi)
            amask = (df["potential_v"] >= ano_lo) & (df["potential_v"] <= ano_hi)

            i_c_raw = float(df.loc[cmask, "current_a"].mean()) if cmask.any() else np.nan
            i_a_raw = float(df.loc[amask, "current_a"].mean()) if amask.any() else np.nan
            i_c = i_c_raw - bl_cat if not np.isnan(i_c_raw) else np.nan
            i_a = i_a_raw - bl_ano if not np.isnan(i_a_raw) else np.nan

            records.append(
                {
                    "group": group,
                    "rpm": rpm,
                    "omega_rad_per_s": angular_velocity(rpm),
                    "omega_sqrt": np.sqrt(angular_velocity(rpm)),
                    "i_cathode_A": i_c_raw,
                    "i_anode_A": i_a_raw,
                    "i_cathode_bl_A": i_c,
                    "i_anode_bl_A": i_a,
                    "abs_i_cathode_A": abs(i_c_raw) if not np.isnan(i_c_raw) else np.nan,
                    "abs_i_anode_A": abs(i_a_raw) if not np.isnan(i_a_raw) else np.nan,
                    "abs_i_cathode_bl_A": abs(i_c) if not np.isnan(i_c) else np.nan,
                    "abs_i_anode_bl_A": abs(i_a) if not np.isnan(i_a) else np.nan,
                }
            )
    return pd.DataFrame(records)


def compute_diffusion_coefficient(
    i_l_values: List[float],
    omega_sqrt_values: List[float],
    params: Dict[str, Any],
    n: int = 1,
) -> Tuple[float, float, float]:
    """从 Levich 斜率计算扩散系数 D"""
    if len(i_l_values) < 3:
        return np.nan, np.nan, np.nan

    x = np.array(omega_sqrt_values)
    y = np.array(i_l_values)

    slope, intercept, r_value, _, _ = stats.linregress(x, y)

    F = params["electrolyte"]["faraday_constant"]
    nu = params["electrolyte"]["viscosity_cm2_per_s"]
    conc_M = params["concentrations"]["values_mol_per_L"][-1]
    c_star = conc_M * 1e-3
    A = params["electrode"]["area_for_j"]

    coeff = 0.62 * n * F * A * nu ** (-1 / 6) * c_star
    D = (abs(slope) / coeff) ** (3 / 2)

    return D, float(r_value) ** 2, float(slope)


def main() -> None:
    params = load_params()
    all_df = pd.read_csv(PROJECT_DIR / params["output"]["processed_dir"] / "all_data.csv")

    print("=" * 60)
    print("Levich 分析 — 扩散系数测定")
    print("=" * 60)

    lc_df = extract_limiting_currents(all_df, params)

    out_dir = PROJECT_DIR / params["output"]["tables_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    lc_df.to_csv(out_dir / "limiting_currents.csv", index=False, encoding="utf-8-sig")

    # Per-group / 每组分别计算
    groups = params["data"]["groups"]
    print("\n阴极扩散系数 D_O (Fe(CN)₆³⁻):")
    for g in groups:
        gdf = lc_df[lc_df["group"] == g].dropna(subset=["abs_i_cathode_A"])
        if len(gdf) >= 3:
            D, r2, slope = compute_diffusion_coefficient(
                gdf["abs_i_cathode_A"].tolist(),
                gdf["omega_sqrt"].tolist(),
                params,
            )
            if np.isnan(D):
                print(f"  [警告] {g} 阴极拟合失败, R2={r2:.4f}")
                continue
            print(f"  {g}: D_O = {D:.3e} cm²/s, R² = {r2:.4f}")

    print("\n阳极扩散系数 D_R (Fe(CN)₆⁴⁻):")
    for g in groups:
        gdf = lc_df[lc_df["group"] == g].dropna(subset=["abs_i_anode_A"])
        if len(gdf) >= 3:
            D, r2, slope = compute_diffusion_coefficient(
                gdf["abs_i_anode_A"].tolist(),
                gdf["omega_sqrt"].tolist(),
                params,
            )
            print(f"  {g}: D_R = {D:.3e} cm²/s, R² = {r2:.4f}")

    # Baseline-corrected / 基线校正后
    print("\n--- 基线校正后 ---")
    print("阴极扩散系数 D_O (基线校正):")
    for g in groups:
        gdf = lc_df[lc_df["group"] == g].dropna(subset=["abs_i_cathode_bl_A"])
        if len(gdf) >= 3:
            D, r2, _ = compute_diffusion_coefficient(
                gdf["abs_i_cathode_bl_A"].tolist(), gdf["omega_sqrt"].tolist(), params
            )
            if not np.isnan(D):
                print(
                    f"  {g}: D_O = {D:.3e} cm²/s (校正前 {lc_df[lc_df['group'] == g]['abs_i_cathode_A'].mean():.4e} A)"
                )

    print("阳极扩散系数 D_R (基线校正):")
    for g in groups:
        gdf = lc_df[lc_df["group"] == g].dropna(subset=["abs_i_anode_bl_A"])
        if len(gdf) >= 3:
            D, r2, _ = compute_diffusion_coefficient(
                gdf["abs_i_anode_bl_A"].tolist(), gdf["omega_sqrt"].tolist(), params
            )
            if not np.isnan(D):
                print(
                    f"  {g}: D_R = {D:.3e} cm²/s (校正前 {lc_df[lc_df['group'] == g]['abs_i_anode_A'].mean():.4e} A)"
                )
    print(f"\n文献参考值:")
    print(f"  D_O = {params['levich']['D_O_literature_cm2_per_s']:.1e} cm²/s")
    print(f"  D_R = {params['levich']['D_R_literature_cm2_per_s']:.1e} cm²/s")


if __name__ == "__main__":
    main()
