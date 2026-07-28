#!/usr/bin/env python3
"""LSV 关键参数提取 — E_onset, E_1/2, j_L (含 iR 补偿估算)"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Dict as DictT

from common import (
    PROJECT_DIR,
    load_params,
    find_onset_potential,
    find_half_wave,
    find_limiting_current_density,
    ir_correct,
)

SCRIPT_DIR = Path(__file__).resolve().parent


def load_all_data() -> pd.DataFrame:
    path = PROJECT_DIR / "output" / "processed" / "all_data.csv"
    if not path.exists():
        raise FileNotFoundError(f"数据文件不存在: {path}\n请先运行 parse_chi660e.py")
    return pd.read_csv(path)


def extract_metrics(
    all_df: pd.DataFrame,
    params: Dict[str, Any],
) -> pd.DataFrame:
    param_map = params.get("catalysts", {})
    speeds = params["kl_analysis"]["rotation_speeds_rpm"]
    groups = params["data"]["groups"]
    threshold = params["thresholds"]["onset_j_ma_per_cm2"]

    records: List[Dict[str, Any]] = []
    for group in groups:
        cat_name = param_map.get(group, group)
        for rpm in speeds:
            mask = (all_df["group"] == group) & (all_df["rpm"] == rpm)
            gdf = all_df[mask]
            if len(gdf) == 0:
                continue

            e_onset = find_onset_potential(gdf, threshold)
            e_half = find_half_wave(gdf, params)
            j_lim, j_lim_std = find_limiting_current_density(gdf, params)

            records.append(
                {
                    "group": group,
                    "catalyst": cat_name,
                    "rpm": rpm,
                    "e_onset_v": round(e_onset, 4) if not np.isnan(e_onset) else np.nan,
                    "e_half_v": round(e_half, 4) if not np.isnan(e_half) else np.nan,
                    "j_lim_ma_cm2": round(j_lim, 4) if not np.isnan(j_lim) else np.nan,
                    "j_lim_std_ma_cm2": round(j_lim_std, 6) if not np.isnan(j_lim_std) else np.nan,
                }
            )

    return pd.DataFrame(records)


def extract_metrics_ir_corrected(
    all_df: pd.DataFrame,
    params: Dict[str, Any],
    ru_ohm: float,
) -> pd.DataFrame:
    param_map = params.get("catalysts", {})
    speeds = params["kl_analysis"]["rotation_speeds_rpm"]
    groups = params["data"]["groups"]
    threshold = params["thresholds"]["onset_j_ma_per_cm2"]

    records: List[Dict[str, Any]] = []
    for group in groups:
        cat_name = param_map.get(group, group)
        for rpm in speeds:
            mask = (all_df["group"] == group) & (all_df["rpm"] == rpm)
            gdf = all_df[mask]
            if len(gdf) == 0:
                continue

            gdf_ir = ir_correct(gdf, ru_ohm, params)

            lim_mask = (gdf_ir["potential_v"] >= params["lsv"]["limiting_range"][0]) & (
                gdf_ir["potential_v"] <= params["lsv"]["limiting_range"][1]
            )
            j_lim = (
                float(gdf_ir.loc[lim_mask, "current_density_ma_cm2"].mean())
                if lim_mask.any()
                else np.nan
            )

            records.append(
                {
                    "group": group,
                    "catalyst": cat_name,
                    "rpm": rpm,
                    "ru_ohm": ru_ohm,
                    "j_lim_ir_ma_cm2": round(j_lim, 4) if not np.isnan(j_lim) else np.nan,
                }
            )

    return pd.DataFrame(records)


def extract_e_half_ir(
    all_df: pd.DataFrame,
    params: Dict[str, Any],
    ru_ohm: float,
    target_rpm: int = 1600,
) -> pd.DataFrame:
    groups = params["data"]["groups"]
    param_map = params.get("catalysts", {})

    records: List[Dict[str, Any]] = []
    for group in groups:
        mask = (all_df["group"] == group) & (all_df["rpm"] == target_rpm)
        gdf = all_df[mask]
        if len(gdf) == 0:
            continue

        gdf_ir = ir_correct(gdf, ru_ohm, params)

        base_mask = (gdf_ir["potential_v"] >= params["lsv"]["baseline_range"][0]) & (
            gdf_ir["potential_v"] <= params["lsv"]["baseline_range"][1]
        )
        j_base = (
            float(gdf_ir.loc[base_mask, "current_density_ma_cm2"].mean())
            if base_mask.any()
            else 0.0
        )

        lim_mask = (gdf_ir["potential_v"] >= params["lsv"]["limiting_range"][0]) & (
            gdf_ir["potential_v"] <= params["lsv"]["limiting_range"][1]
        )
        j_lim = (
            float(gdf_ir.loc[lim_mask, "current_density_ma_cm2"].mean()) if lim_mask.any() else 0.0
        )

        j_half = (j_base + j_lim) / 2

        search_mask = (gdf_ir["potential_v"] >= params["lsv"]["half_wave_search_range"][0]) & (
            gdf_ir["potential_v"] <= params["lsv"]["half_wave_search_range"][1]
        )
        descend = gdf_ir[search_mask]
        if len(descend) == 0:
            continue

        idx = int((descend["current_density_ma_cm2"] - j_half).abs().idxmin())
        e_half_ir = descend.loc[idx, "potential_vs_rhe_ir"]

        # 原始值
        e_half_raw = find_half_wave(gdf, params)
        rhe_offset = params["reference_electrode"]["conversion_to_rhe"]
        e_half_raw_rhe = e_half_raw + rhe_offset if not np.isnan(e_half_raw) else np.nan

        records.append(
            {
                "group": group,
                "catalyst": param_map.get(group, group),
                "ru_ohm": ru_ohm,
                "e_half_raw_vs_rhe": round(float(e_half_raw_rhe), 4),
                "e_half_ir_vs_rhe": round(float(e_half_ir), 4),
            }
        )

    return pd.DataFrame(records)


def main() -> None:
    params = load_params()
    all_df = load_all_data()

    print("=" * 60)
    print("LSV 关键参数提取")
    print("=" * 60)

    # 原始数据提取
    metrics = extract_metrics(all_df, params)

    out_dir = PROJECT_DIR / params["output"]["tables_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(out_dir / "lsv_metrics.csv", index=False, encoding="utf-8-sig")
    print(f"\n参数表已保存到 {out_dir / 'lsv_metrics.csv'}")
    print("\n" + metrics.to_string(index=False))

    # iR 补偿估算
    print("\n--- iR 补偿估算 (@1600rpm) ---")
    ru_values = params["electrode"]["contact_resistance_ohm"]
    ir_records: List[Dict[str, Any]] = []
    for ru in ru_values:
        ir_df = extract_e_half_ir(all_df, params, ru, target_rpm=1600)
        if len(ir_df) > 0:
            for _, row in ir_df.iterrows():
                ir_records.append(row.to_dict())

    if ir_records:
        ir_summary = pd.DataFrame(ir_records)
        print(ir_summary.to_string(index=False))
        ir_summary.to_csv(out_dir / "ir_correction.csv", index=False, encoding="utf-8-sig")
        print(f"\niR 校正表已保存到 {out_dir / 'ir_correction.csv'}")


if __name__ == "__main__":
    main()
