#!/usr/bin/env python3
"""Koutecky-Levich 分析与 Tafel 分析"""

import json
import numpy as np
import pandas as pd
from scipy import stats
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Dict as DictT

from common import (
    PROJECT_DIR,
    load_params,
    levich_constant,
    angular_velocity,
    extract_kl_data,
    fit_kl,
    compute_electron_numbers,
    compute_jk_corrected,
)

SCRIPT_DIR = Path(__file__).resolve().parent


def load_all_data() -> pd.DataFrame:
    path = PROJECT_DIR / "output" / "processed" / "all_data.csv"
    if not path.exists():
        raise FileNotFoundError(f"数据文件不存在: {path}\n请先运行 parse_chi660e.py")
    return pd.read_csv(path)


def build_raw_data_dict(
    all_df: pd.DataFrame,
    params: Dict[str, Any],
) -> Dict[str, Dict[int, pd.DataFrame]]:
    groups = params["data"]["groups"]
    speeds = params["kl_analysis"]["rotation_speeds_rpm"]
    raw_data: Dict[str, Dict[int, pd.DataFrame]] = {}
    for group in groups:
        raw_data[group] = {}
        for rpm in speeds:
            mask = (all_df["group"] == group) & (all_df["rpm"] == rpm)
            gdf = all_df[mask]
            if len(gdf) > 0:
                raw_data[group][rpm] = gdf
    return raw_data


def kl_summary_table(
    kl_results: Dict[str, Dict[float, Dict[str, float]]],
    params: Dict[str, Any],
) -> pd.DataFrame:
    potentials = params["kl_analysis"]["potentials_vs_hghgo"]
    rhe_offset = params["reference_electrode"]["conversion_to_rhe"]
    rows: List[Dict[str, Any]] = []
    for group, pot_results in kl_results.items():
        for pot in potentials:
            r = pot_results.get(pot)
            if r:
                rows.append(
                    {
                        "group": group,
                        "potential_v": pot,
                        "potential_vs_rhe": round(pot + rhe_offset, 3),
                        "slope": round(r["slope"], 6),
                        "intercept": round(r["intercept"], 4),
                        "r_squared": round(r["r_squared"], 4),
                        "n_electrons": r.get("n_electrons", np.nan),
                        "j_k_ma_cm2": r.get("j_k_ma_cm2", np.nan),
                        "n_points": r["n_points"],
                    }
                )
    return pd.DataFrame(rows)


def tafel_analysis(
    all_df: pd.DataFrame,
    params: Dict[str, Any],
) -> Dict[str, Optional[Dict[str, Any]]]:
    tafel_range = params["lsv"]["tafel_range"]
    rhe_offset = params["reference_electrode"]["conversion_to_rhe"]
    speeds = params["kl_analysis"]["rotation_speeds_rpm"]
    groups = params["data"]["groups"]

    tafel_results: Dict[str, Optional[Dict[str, Any]]] = {}
    for group in groups:
        target_rpm = 1600
        mask = (all_df["group"] == group) & (all_df["rpm"] == target_rpm)
        if mask.sum() == 0:
            for s in speeds:
                mask = (all_df["group"] == group) & (all_df["rpm"] == s)
                if mask.sum() > 0:
                    target_rpm = s
                    break
            else:
                tafel_results[group] = None
                continue

        df = all_df[mask]
        j_col = "current_density_ma_cm2"

        lim_mask = (df["potential_v"] >= params["lsv"]["limiting_range"][0]) & (
            df["potential_v"] <= params["lsv"]["limiting_range"][1]
        )
        j_lim_val = abs(float(df.loc[lim_mask, j_col].mean())) if lim_mask.any() else 1.0

        tafel_mask = (df["potential_v"] >= tafel_range[0]) & (df["potential_v"] <= tafel_range[1])
        tafel_df = df[tafel_mask]

        tafel_points: List[Tuple[float, float]] = []
        for _, row in tafel_df.iterrows():
            j = abs(float(row[j_col]))
            if j < 0.001 or j_lim_val <= 0:
                continue
            j_k = compute_jk_corrected(j, j_lim_val)
            if j_k > 0:
                e_rhe = float(row["potential_v"]) + rhe_offset
                tafel_points.append((e_rhe, np.log10(j_k)))

        if len(tafel_points) < 5:
            tafel_results[group] = None
            continue

        x = np.array([p[0] for p in tafel_points])
        y = np.array([p[1] for p in tafel_points])

        slope, intercept, r_value, _p, _e = stats.linregress(x, y)
        tafel_slope_mv_dec = abs(1000.0 / slope) if slope != 0 else np.nan
        j0_log = slope * 1.23 + intercept
        j0_ma_cm2 = 10**j0_log if not np.isnan(j0_log) else np.nan

        tafel_results[group] = {
            "tafel_slope_mv_per_dec": round(tafel_slope_mv_dec, 1),
            "intercept": round(float(intercept), 3),
            "r_squared": round(float(r_value) ** 2, 4),
            "n_points": len(tafel_points),
            "j0_ma_cm2": round(j0_ma_cm2, 6) if not np.isnan(j0_ma_cm2) else np.nan,
            "e_rhe_range": f"{x.min():.3f} - {x.max():.3f}",
        }

    return tafel_results


def save_kl_json(
    kl_results: Dict[str, Dict[float, Dict[str, float]]],
    params: Dict[str, Any],
) -> None:
    out_dir = PROJECT_DIR / params["output"]["tables_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)

    serializable: Dict[str, Any] = {}
    for group, pot_results in kl_results.items():
        serializable[group] = {}
        for pot, r in pot_results.items():
            if r:
                serializable[group][str(pot)] = {
                    k: (v if not isinstance(v, float) or not np.isnan(v) else None)
                    for k, v in r.items()
                }

    with open(out_dir / "kl_results.json", "w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2, ensure_ascii=False)
    print(f"K-L 结果已保存到 {out_dir / 'kl_results.json'}")


def main() -> None:
    params = load_params()
    all_df = load_all_data()

    print("=" * 60)
    print("K-L 分析与 Tafel 分析")
    print("=" * 60)

    B = levich_constant(params)
    n_4e_slope = 1.0 / (4 * B)
    print(f"\nLevich 常数 B = {B:.4e} A*s^(1/2)/(cm2*rad^(1/2))")
    print(f"理论 4e- 斜率 = {n_4e_slope:.2e}")

    raw_data = build_raw_data_dict(all_df, params)

    print("\n[1] K-L 数据提取...")
    kl_data = extract_kl_data(raw_data, params)

    print("[2] K-L 线性拟合...")
    kl_results: Dict[str, Dict[float, Dict[str, float]]] = {}
    for group, pot_data in kl_data.items():
        kl_results[group] = {}
        for pot, points in pot_data.items():
            fit = fit_kl(points)
            kl_results[group][pot] = fit
            if fit:
                print(f"  {group} @ {pot}V: n={len(points)}点, R2={fit['r_squared']:.4f}")

    print("[3] 计算电子转移数 n...")
    kl_results = compute_electron_numbers(kl_results, params)

    kl_table = kl_summary_table(kl_results, params)
    out_dir = PROJECT_DIR / params["output"]["tables_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    kl_table.to_csv(out_dir / "kl_analysis.csv", index=False, encoding="utf-8-sig")
    print(f"\nK-L 分析表已保存到 {out_dir / 'kl_analysis.csv'}")

    save_kl_json(kl_results, params)

    for group in kl_results:
        n_vals = [
            r["n_electrons"]
            for r in kl_results[group].values()
            if r and not np.isnan(r.get("n_electrons", np.nan))
        ]
        if n_vals:
            print(f"  {group} 平均 n = {np.mean(n_vals):.2f} +/- {np.std(n_vals):.2f}")

    print("\n[4] Tafel 分析...")
    tafel_results = tafel_analysis(all_df, params)
    tafel_rows: List[Dict[str, Any]] = []
    for group, tr in tafel_results.items():
        if tr:
            print(
                f"  {group}: b = {tr['tafel_slope_mv_per_dec']:.1f} mV/dec, "
                f"R2 = {tr['r_squared']:.4f}"
            )
            tafel_rows.append({"group": group, **tr})
        else:
            print(f"  {group}: 数据不足")
    if tafel_rows:
        pd.DataFrame(tafel_rows).to_csv(
            out_dir / "tafel_analysis.csv", index=False, encoding="utf-8-sig"
        )

    # 导出 K-L 原始数据 (供 Origin 使用)
    origin_dir = PROJECT_DIR / params["output"]["origin_input_dir"]
    origin_dir.mkdir(parents=True, exist_ok=True)
    for group, pot_data in kl_data.items():
        rows_for_origin: List[Dict[str, Any]] = []
        for pot, points in pot_data.items():
            for omega_neg_half, j_inv in points:
                rows_for_origin.append(
                    {
                        "potential_v": pot,
                        "omega_neg_half": omega_neg_half,
                        "j_inv_cm2_per_ma": j_inv,
                    }
                )
        if rows_for_origin:
            pd.DataFrame(rows_for_origin).to_csv(
                origin_dir / f"KL_{group}.csv",
                index=False,
                encoding="utf-8-sig",
                float_format="%.6e",
            )
    print(f"\nK-L 数据已导出到 {origin_dir}/KL_*.csv")


if __name__ == "__main__":
    main()
