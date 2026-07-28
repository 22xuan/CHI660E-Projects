#!/usr/bin/env python3
"""CHI660E LSV 数据解析器 — TXT → 结构化 DataFrame + 电位/电流密度转换"""

import re
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Tuple

from common import (
    PROJECT_DIR,
    load_params,
    convert_potential_to_rhe,
    convert_current_to_density,
)

SCRIPT_DIR = Path(__file__).resolve().parent


def detect_delimiter(filepath: str) -> str:
    with open(filepath, encoding="utf-8-sig") as f:
        f.readline()
        for _ in range(20):
            line = f.readline()
            if not line:
                continue
            if "\t" in line and "," not in line:
                return "\t"
            if "," in line:
                return ","
    return ","


def parse_lsv_file(filepath: str) -> Tuple[Dict[str, float], pd.DataFrame]:
    delim = detect_delimiter(filepath)
    headers: Dict[str, float] = {}
    data_rows: list[Tuple[float, float]] = []

    with open(filepath, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            m = re.match(
                r"^(Init E|Final E|Scan Rate|Sample Interval|Quiet Time|Sensitivity)\s*\([^)]*\)\s*=\s*(.+)",
                line,
            )
            if m:
                key = m.group(1).replace(" ", "_").lower()
                headers[key] = float(m.group(2))
                continue

            if line.startswith("Potential/V") or line.startswith("Channel") or line == "Results:":
                continue
            if line.startswith(("Dec.", "File:", "Instrument", "Header:", "Note:", "Data Source:")):
                continue

            parts = re.split(r"[\t,]+", line)
            if len(parts) >= 2:
                try:
                    e = float(parts[0].strip())
                    i = float(parts[1].strip())
                    data_rows.append((e, i))
                except ValueError:
                    continue

    df = pd.DataFrame(data_rows, columns=["potential_v", "current_a"])
    return headers, df


def resolve_source_root(params: Dict[str, Any]) -> Path:
    source = params["data"]["source_root"]
    candidate = PROJECT_DIR / source
    if candidate.exists():
        return candidate.resolve()
    return Path(source).resolve()


def collect_all_data(params: Dict[str, Any]) -> Dict[str, Dict[int, pd.DataFrame]]:
    data_root = resolve_source_root(params)
    speeds = params["kl_analysis"]["rotation_speeds_rpm"]
    groups = params["data"]["groups"]
    special = params["data"].get("special_paths", {})

    all_data: Dict[str, Dict[int, pd.DataFrame]] = {}
    for group in groups:
        all_data[group] = {}
        for rpm in speeds:
            special_path = special.get(group, {}).get(rpm)
            if special_path:
                fpath = data_root / group / special_path
            else:
                fpath = data_root / group / "txt" / f"{rpm}r-{group[0]}.txt"

            if not fpath.exists():
                print(f"  [跳过] {group}/{rpm}r — 文件不存在: {fpath}")
                continue

            _headers, df = parse_lsv_file(str(fpath))
            all_data[group][rpm] = df
            print(
                f"  [解析] {group}/{rpm}r: {len(df)} 点, "
                f"E={df['potential_v'].iloc[0]:.3f}->{df['potential_v'].iloc[-1]:.3f}V"
            )

    return all_data


def process_all(
    all_data: Dict[str, Dict[int, pd.DataFrame]],
    params: Dict[str, Any],
) -> Dict[str, Dict[int, pd.DataFrame]]:
    processed: Dict[str, Dict[int, pd.DataFrame]] = {}
    for group, speeds in all_data.items():
        processed[group] = {}
        for rpm, df in speeds.items():
            df = df.copy()
            df = convert_potential_to_rhe(df, params)
            df = convert_current_to_density(df, params)
            processed[group][rpm] = df
    return processed


def save_all_data_csv(
    processed: Dict[str, Dict[int, pd.DataFrame]],
    params: Dict[str, Any],
) -> None:
    out_dir = PROJECT_DIR / params["output"]["processed_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for group, speeds in processed.items():
        for rpm, df in speeds.items():
            for _, row in df.iterrows():
                rows.append(
                    {
                        "group": group,
                        "rpm": rpm,
                        "potential_v": row["potential_v"],
                        "current_a": row["current_a"],
                        "potential_vs_rhe": row["potential_vs_rhe"],
                        "current_density_ma_cm2": row["current_density_ma_cm2"],
                    }
                )

    all_df = pd.DataFrame(rows)
    all_df.to_csv(out_dir / "all_data.csv", index=False, encoding="utf-8-sig")
    print(f"\n合并数据已保存到 {out_dir / 'all_data.csv'} ({len(rows)} 行)")


def save_origin_csv(
    processed: Dict[str, Dict[int, pd.DataFrame]],
    params: Dict[str, Any],
) -> None:
    out_dir = PROJECT_DIR / params["output"]["origin_input_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)

    for group, speeds in processed.items():
        for rpm, df in speeds.items():
            fname = f"{group}_{rpm}r.csv"
            df.to_csv(out_dir / fname, index=False, float_format="%.6e")
    print(f"Origin 导入数据已保存到 {out_dir}")


def main() -> None:
    params = load_params()
    print("=" * 60)
    print("CHI660E ORR-RDE 数据解析")
    print("=" * 60)

    print("\n[1/3] 采集原始数据...")
    all_data = collect_all_data(params)

    print("\n[2/3] 电位转换 (Hg/HgO -> RHE) + 电流密度转换...")
    processed = process_all(all_data, params)

    print("\n[3/3] 保存中间结果...")
    save_all_data_csv(processed, params)
    save_origin_csv(processed, params)

    print("\n解析完成 — 无 pickle 文件，数据以 CSV 格式存储")


if __name__ == "__main__":
    main()
