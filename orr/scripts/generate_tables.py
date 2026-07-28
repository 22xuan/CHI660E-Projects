#!/usr/bin/env python3
"""汇总报表生成 — 催化剂组间对比 CSV + Markdown (含平行样合并)"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Optional

from common import PROJECT_DIR, load_params

SCRIPT_DIR = Path(__file__).resolve().parent


def read_if_exists(path: Path) -> Optional[pd.DataFrame]:
    if not path.exists():
        print(f"  [警告] 文件不存在: {path}")
        return None
    return pd.read_csv(path)


def load_data(
    params: Dict[str, Any],
) -> tuple[pd.DataFrame, Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    out_dir = PROJECT_DIR / params["output"]["tables_dir"]

    all_data = pd.read_csv(PROJECT_DIR / params["output"]["processed_dir"] / "all_data.csv")
    metrics = read_if_exists(out_dir / "lsv_metrics.csv")
    kl_table = read_if_exists(out_dir / "kl_analysis.csv")
    tafel_table = read_if_exists(out_dir / "tafel_analysis.csv")

    return all_data, metrics, kl_table, tafel_table


def build_merged_summary(
    metrics_df: pd.DataFrame,
    kl_table: pd.DataFrame,
    tafel_df: pd.DataFrame,
    params: Dict[str, Any],
) -> pd.DataFrame:
    merge_config = params.get("merge", {})
    pairs: Dict[str, list[str]] = merge_config.get("pairs", {})
    param_map = params.get("catalysts", {})
    rhe_offset = params["reference_electrode"]["conversion_to_rhe"]

    rows: List[Dict[str, Any]] = []
    for cat_name, groups in pairs.items():
        e_onset_vs_rhe_vals: list[float] = []
        e_half_vs_rhe_vals: list[float] = []
        j_lim_vals: list[float] = []
        n_vals: list[float] = []
        tafel_b_vals: list[float] = []

        for group in groups:
            g_metrics = metrics_df[metrics_df["group"] == group]
            row_1600 = g_metrics[g_metrics["rpm"] == 1600]
            if len(row_1600) > 0:
                e_onset = row_1600["e_onset_v"].values[0]
                e_half = row_1600["e_half_v"].values[0]
                j_lim = row_1600["j_lim_ma_cm2"].values[0]
                if not np.isnan(e_onset):
                    e_onset_vs_rhe_vals.append(float(e_onset) + rhe_offset)
                if not np.isnan(e_half):
                    e_half_vs_rhe_vals.append(float(e_half) + rhe_offset)
                if not np.isnan(j_lim):
                    j_lim_vals.append(abs(float(j_lim)))

            if kl_table is not None:
                gn = kl_table[kl_table["group"] == group]["n_electrons"].dropna()
                if len(gn) > 0:
                    n_vals.extend(gn.tolist())

            if tafel_df is not None:
                gt = tafel_df[tafel_df["group"] == group]
                if len(gt) > 0:
                    tb = gt["tafel_slope_mv_per_dec"].values[0]
                    if not np.isnan(tb):
                        tafel_b_vals.append(float(tb))

        def fmt_mean_std(vals: list[float], decimals: int = 3) -> str:
            if not vals:
                return "-"
            m = np.mean(vals)
            s = np.std(vals, ddof=1) if len(vals) > 1 else 0.0
            return f"{m:.{decimals}f} +/- {s:.{decimals}f}"

        rows.append(
            {
                "催化剂": cat_name,
                "E_onset (V vs RHE)": fmt_mean_std(e_onset_vs_rhe_vals),
                "E_1/2 (V vs RHE)": fmt_mean_std(e_half_vs_rhe_vals),
                "|j_L| (mA/cm2) @1600r": fmt_mean_std(j_lim_vals, 2),
                "n (电子转移数)": fmt_mean_std(n_vals, 2),
                "Tafel b (mV/dec)": fmt_mean_std(tafel_b_vals, 1),
            }
        )

    return pd.DataFrame(rows)


def to_markdown(df: pd.DataFrame, title: str = "## 催化剂性能对比") -> str:
    lines = [title, "", df.to_markdown(index=False), ""]
    return "\n".join(lines)


def main() -> None:
    params = load_params()
    all_data, metrics, kl_table, tafel_df = load_data(params)

    print("=" * 60)
    print("组间对比汇总 (平行样合并)")
    print("=" * 60)

    if metrics is None or kl_table is None or tafel_df is None:
        print(
            "错误: 缺少必要的数据文件，请确保已运行 parse_chi660e.py, lsv_metrics.py, kl_analysis.py"
        )
        return

    summary = build_merged_summary(metrics, kl_table, tafel_df, params)

    out_dir = PROJECT_DIR / params["output"]["tables_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)

    summary.to_csv(out_dir / "group_comparison.csv", index=False, encoding="utf-8-sig")
    print(f"\n对比表已保存到 {out_dir / 'group_comparison.csv'}")

    md_content = to_markdown(summary, "## 催化剂性能对比 (ORR RDE 测试)")
    md_path = out_dir / "group_comparison.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Markdown 已保存到 {md_path}")

    print("\n" + md_content)


if __name__ == "__main__":
    main()
