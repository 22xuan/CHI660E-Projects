#!/usr/bin/env python3
"""浓度校准 + K-L 分析 + Tafel 外推 -> i0, alpha, beta"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Tuple
from scipy import stats
import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent


def load_params() -> Dict[str, Any]:
    with open(PROJECT_DIR / "params.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def angular_velocity(rpm: float) -> float:
    return rpm * 2 * np.pi / 60


def find_zero_crossing(df: pd.DataFrame) -> float:
    for i in range(len(df) - 1):
        if df.iloc[i]["current_a"] * df.iloc[i + 1]["current_a"] <= 0:
            return float((df.iloc[i]["potential_v"] + df.iloc[i + 1]["potential_v"]) / 2)
    return np.nan


def concentration_calibration(all_df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    groups = params["data"]["groups"]
    concs = params["concentrations"]["values_mol_per_L"]
    cat_lo, cat_hi = params["limiting_current"]["cathode_range"]
    ano_lo, ano_hi = params["limiting_current"]["anode_range"]

    records = []
    for group in groups:
        for conc in concs:
            if conc == 0.01:
                key = f"PartA_{group}_2000rpm"
            else:
                key = f"PartB_{group}_{conc}M"
            mask = all_df["key"] == key
            df = all_df[mask]
            if len(df) == 0:
                continue
            cat_mask = (df["potential_v"] >= cat_lo) & (df["potential_v"] <= cat_hi)
            i_c = float(df.loc[cat_mask, "current_a"].mean()) if cat_mask.any() else np.nan
            ano_mask = (df["potential_v"] >= ano_lo) & (df["potential_v"] <= ano_hi)
            i_a = float(df.loc[ano_mask, "current_a"].mean()) if ano_mask.any() else np.nan
            records.append(
                {
                    "group": group,
                    "concentration_M": conc,
                    "abs_i_cathode_A": abs(i_c) if not np.isnan(i_c) else np.nan,
                    "abs_i_anode_A": abs(i_a) if not np.isnan(i_a) else np.nan,
                }
            )
    return pd.DataFrame(records)


def kl_analysis(
    all_df: pd.DataFrame, params: Dict[str, Any]
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, float]]:
    groups = params["data"]["groups"]
    speeds = params["rotation_speeds_rpm"]
    overpotentials = params["kl_analysis"]["overpotentials_mv"]
    tol = params["kl_analysis"]["potential_tol_v"]

    e0_map: Dict[str, float] = {}
    for group in groups:
        key = f"PartA_{group}_2000rpm"
        mask = all_df["key"] == key
        df = all_df[mask]
        if len(df) > 0:
            e0_map[group] = find_zero_crossing(df)
    print(f"平衡电位 E0: { {g: f'{v:.3f}' for g, v in e0_map.items()} }")

    kl_records = []
    kl_raw_records = []

    for group in groups:
        if group not in e0_map or np.isnan(e0_map[group]):
            continue
        e0 = e0_map[group]

        for eta_mv in overpotentials:
            eta_v = eta_mv / 1000
            e_target = e0 + eta_v

            x_vals, y_vals = [], []
            rpm_points = []
            for rpm in speeds:
                key = f"PartA_{group}_{rpm}rpm"
                mask = all_df["key"] == key
                df = all_df[mask]
                if len(df) == 0:
                    continue
                pt_mask = (df["potential_v"] >= e_target - tol) & (
                    df["potential_v"] <= e_target + tol
                )
                if pt_mask.any():
                    i = abs(float(df.loc[pt_mask, "current_a"].mean()))
                    if i > 1e-9:
                        omega = angular_velocity(rpm)
                        omega_neg_half = omega ** (-0.5)
                        i_inv = 1.0 / i
                        x_vals.append(omega_neg_half)
                        y_vals.append(i_inv)
                        rpm_points.append(rpm)
                        kl_raw_records.append(
                            {
                                "group": group,
                                "eta_mV": eta_mv,
                                "rpm": rpm,
                                "omega_neg_half": omega_neg_half,
                                "i_A": i,
                                "i_inv_A": i_inv,
                            }
                        )

            if len(x_vals) >= 3:
                slope, intercept, r_val, _, _ = stats.linregress(x_vals, y_vals)
                kl_records.append(
                    {
                        "group": group,
                        "eta_mV": eta_mv,
                        "e_target_V": round(e_target, 4),
                        "slope": float(slope),
                        "intercept": float(intercept),
                        "r_squared": float(r_val) ** 2,
                        "n_points": len(x_vals),
                    }
                )

    kl_df = pd.DataFrame(kl_records)
    kl_raw_df = pd.DataFrame(kl_raw_records)

    # Tafel: log|i_k| vs eta
    tafel_records = []
    tafel_raw_records = []
    for group in groups:
        gdf = kl_df[kl_df["group"] == group]
        if len(gdf) < 3:
            continue
        eta_list, log_ik_list = [], []
        for _, row in gdf.iterrows():
            if row["intercept"] > 0:
                ik = 1.0 / row["intercept"]
                eta_list.append(row["eta_mV"])
                log_ik_list.append(np.log10(ik))
                tafel_raw_records.append(
                    {
                        "group": group,
                        "eta_mV": row["eta_mV"],
                        "ik_A": ik,
                        "log_ik": np.log10(ik),
                    }
                )

        if len(eta_list) >= 3:
            x_arr = np.array(eta_list)
            y_arr = np.array(log_ik_list)
            slope, intercept, r_val, _, _ = stats.linregress(x_arr, y_arr)
            b_mv = abs(1.0 / slope) if slope != 0 else np.nan
            i0 = 10 ** float(intercept)
            alpha_val = round(0.059 / (b_mv / 1000), 3) if not np.isnan(b_mv) else np.nan
            tafel_records.append(
                {
                    "group": group,
                    "tafel_slope_mV_per_dec": round(b_mv, 1),
                    "r_squared": round(float(r_val) ** 2, 4),
                    "i0_A": float(i0),
                    "alpha": alpha_val,
                    "fit_slope": float(slope),
                    "fit_intercept": float(intercept),
                }
            )

    tafel_df = pd.DataFrame(tafel_records)
    tafel_raw_df = pd.DataFrame(tafel_raw_records)
    return kl_df, kl_raw_df, tafel_df, tafel_raw_df, e0_map


def half_wave_analysis(all_df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    groups = params["data"]["groups"]
    records = []
    for group in groups:
        key = f"NoKCl_{group}"
        mask = all_df["key"] == key
        df = all_df[mask]
        if len(df) == 0:
            continue
        e0 = find_zero_crossing(df)
        cat_lo, cat_hi = params["limiting_current"]["cathode_range"]
        ano_lo, ano_hi = params["limiting_current"]["anode_range"]
        i_base = float(
            df.loc[
                (df["potential_v"] >= cat_lo) & (df["potential_v"] <= cat_hi), "current_a"
            ].mean()
        )
        i_lim = float(
            df.loc[
                (df["potential_v"] >= ano_lo) & (df["potential_v"] <= ano_hi), "current_a"
            ].mean()
        )
        i_half = (i_base + i_lim) / 2
        trans = df[(df["potential_v"] >= -0.05) & (df["potential_v"] <= 0.45)]
        if len(trans) > 0:
            idx = (trans["current_a"] - i_half).abs().idxmin()
            e_half = trans.loc[idx, "potential_v"]
        else:
            e_half = np.nan
        records.append(
            {
                "group": group,
                "E0_V": round(e0, 4) if not np.isnan(e0) else np.nan,
                "E1_2_V": round(float(e_half), 4),
                "i_cathode_A": round(float(i_base), 6),
                "i_anode_A": round(float(i_lim), 6),
            }
        )
    return pd.DataFrame(records)


def main() -> None:
    params = load_params()
    all_df = pd.read_csv(PROJECT_DIR / params["output"]["processed_dir"] / "all_data.csv")
    out_dir = PROJECT_DIR / params["output"]["tables_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("浓度校准 + K-L/Tafel 分析")
    print("=" * 60)

    print("\n[1] 浓度校准 (i_l vs c*)...")
    cal_df = concentration_calibration(all_df, params)
    cal_df.to_csv(out_dir / "concentration_cal.csv", index=False, encoding="utf-8-sig")

    print("\n[2] K-L 分析 + Tafel 外推...")
    kl_df, kl_raw_df, tafel_df, tafel_raw_df, e0_map = kl_analysis(all_df, params)
    kl_df.to_csv(out_dir / "kl_analysis.csv", index=False, encoding="utf-8-sig")
    kl_raw_df.to_csv(out_dir / "kl_raw_points.csv", index=False, encoding="utf-8-sig")
    tafel_df.to_csv(out_dir / "tafel_results.csv", index=False, encoding="utf-8-sig")
    tafel_raw_df.to_csv(out_dir / "tafel_raw_points.csv", index=False, encoding="utf-8-sig")
    print(f"  K-L 原始数据: {len(kl_raw_df)} 点")
    print(f"  Tafel 原始数据: {len(tafel_raw_df)} 点")
    print("\nTafel 结果:")
    print(tafel_df.to_string(index=False))

    print("\n[3] 半波电位分析 (0.0008M 无KCl)...")
    hw_df = half_wave_analysis(all_df, params)
    hw_df.to_csv(out_dir / "half_wave.csv", index=False, encoding="utf-8-sig")
    print(hw_df.to_string(index=False))


if __name__ == "__main__":
    main()
