#!/usr/bin/env python3
"""CHI660E Tafel Plot 数据解析器 — 3列格式 (E, I, log|I|)"""

import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent

from common import load_params


def parse_tafel_file(filepath: str) -> pd.DataFrame:
    rows: List[Tuple[float, float]] = []
    with open(filepath, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith(
                (
                    "Jan.",
                    "Tafel Plot",
                    "File:",
                    "Instrument",
                    "Header:",
                    "Note:",
                    "Init E",
                    "Final E",
                    "Segment",
                    "Hold Time",
                    "Scan Rate",
                    "Quiet Time",
                    "Potential/V",
                )
            ):
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 2:
                try:
                    e = float(parts[0])
                    i = float(parts[1])
                    rows.append((e, i))
                except ValueError:
                    continue
    return pd.DataFrame(rows, columns=["potential_v", "current_a"])


def collect_data(params: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
    data_root = (PROJECT_DIR / params["data"]["source_root"]).resolve()
    groups = params["data"]["groups"]
    speeds = params["rotation_speeds_rpm"]
    concs = params["concentrations"]["values_mol_per_L"]
    target_rpm = params["concentrations"]["target_rpm"]

    all_data: Dict[str, pd.DataFrame] = {}

    # Part A: 0.01M + KCl, 各转速
    for group in groups:
        for rpm in speeds:
            fname = f"0.01-kcl-{rpm}r-{group}.txt"
            fpath = data_root / fname
            if fpath.exists():
                key = f"PartA_{group}_{rpm}rpm"
                all_data[key] = parse_tafel_file(str(fpath))
                print(f"  [PartA] {group} {rpm}rpm: {len(all_data[key])} pts")

    # Part B: 各浓度 + KCl, 2000rpm
    for group in groups:
        for conc in concs:
            if conc == 0.01:
                continue  # already in Part A
            fname = f"{conc}-kcl-{target_rpm}r-{group}.txt"
            fpath = data_root / fname
            if fpath.exists():
                key = f"PartB_{group}_{conc}M"
                all_data[key] = parse_tafel_file(str(fpath))
                print(f"  [PartB] {group} {conc}M: {len(all_data[key])} pts")

    # KCl baseline
    for group in groups:
        fpath = data_root / f"kcl-{target_rpm}r-{group}.txt"
        if fpath.exists():
            key = f"Baseline_{group}"
            all_data[key] = parse_tafel_file(str(fpath))
            print(f"  [Baseline] {group}: {len(all_data[key])} pts")

    # 0.0008M no KCl
    no_kcl = params["concentrations"].get("no_kcl", {})
    if no_kcl.get("enabled"):
        for group in groups:
            fpath = data_root / f"0.0008-{target_rpm}r-{group}.txt"
            if fpath.exists():
                key = f"NoKCl_{group}"
                all_data[key] = parse_tafel_file(str(fpath))
                print(f"  [NoKCl] {group}: {len(all_data[key])} pts")

    return all_data


def save_csv(all_data: Dict[str, pd.DataFrame], params: Dict[str, Any]) -> None:
    out_dir = PROJECT_DIR / params["output"]["processed_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for key, df in all_data.items():
        for _, row in df.iterrows():
            rows.append(
                {
                    "key": key,
                    "potential_v": row["potential_v"],
                    "current_a": row["current_a"],
                }
            )
    all_df = pd.DataFrame(rows)
    all_df.to_csv(out_dir / "all_data.csv", index=False, encoding="utf-8-sig")
    print(f"\n合并数据已保存到 {out_dir / 'all_data.csv'} ({len(rows)} 行)")


def main() -> None:
    params = load_params()
    print("=" * 60)
    print("CHI660E Tafel Plot 数据解析")
    print("=" * 60)
    all_data = collect_data(params)
    save_csv(all_data, params)


if __name__ == "__main__":
    main()
