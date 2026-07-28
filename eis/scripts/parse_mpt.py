#!/usr/bin/env python3
"""Bio-Logic .mpt 格式解析 — 提取 EIS 数据（欧洲逗号格式）"""

import yaml
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent


def load_params() -> Dict[str, Any]:
    with open(PROJECT_DIR / "params.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _to_float(s: str) -> float:
    return float(s.replace(",", ".").strip())


def parse_mpt(filepath: str, area_cm2: float = 1.0) -> pd.DataFrame:
    n_skip = 0
    columns: List[str] = []
    rows: List[Tuple[float, float, float, float, float]] = []

    with open(filepath, encoding="latin-1") as f:
        for line in f:
            if line.startswith("Nb header lines"):
                n_skip = int(line.split(":")[1].strip())
            if line.startswith("freq/Hz") and not columns:
                columns = line.strip().split("\t")
                break

    with open(filepath, encoding="latin-1") as f:
        for i, line in enumerate(f):
            if i < n_skip:
                continue
            if line.startswith("Loop"):
                break
            if line.startswith("freq/Hz"):
                continue
            parts = line.strip().split("\t")
            if len(parts) < 3:
                continue
            try:
                freq = _to_float(parts[0])
                zre = _to_float(parts[1]) * area_cm2
                zim = _to_float(parts[2]) * area_cm2
                zmod = _to_float(parts[3]) * area_cm2
                phase = _to_float(parts[4])
                rows.append((freq, zre, zim, zmod, phase))
            except (ValueError, IndexError):
                continue

    df = pd.DataFrame(
        rows, columns=["freq_Hz", "Zre_ohm_cm2", "Zim_ohm_cm2", "Zmod_ohm_cm2", "Phase_deg"]
    )
    return df.sort_values("freq_Hz", ascending=False)


def main() -> None:
    params = load_params()
    area = params["experiment"]["area_cm2"]
    out_dir = PROJECT_DIR / params["output"]["processed_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)

    for cond in params["experiment"]["conditions"]:
        fpath = PROJECT_DIR / "data" / cond["file"]
        if not fpath.exists():
            print(f"  [跳过] 文件不存在: {fpath}")
            continue

        print(f"  解析 {cond['label']}: {cond['file']}")
        df = parse_mpt(str(fpath), area_cm2=area)
        out = out_dir / f"eis_{cond['label']}.csv"
        df.to_csv(out, index=False, encoding="utf-8-sig")
        print(f"    {len(df)} 点, {df['freq_Hz'].max():.0f} -> {df['freq_Hz'].min():.4f} Hz")
        high = df.iloc[:10]
        rs_idx = high["Zim_ohm_cm2"].abs().idxmin()
        print(
            f"    Rs ≈ {df.loc[rs_idx, 'Zre_ohm_cm2']:.1f} Ω·cm² (@ {df.loc[rs_idx, 'freq_Hz']:.0f} Hz)"
        )
        print(f"    |Z|max = {df['Zmod_ohm_cm2'].max():.0f} Ω·cm²")


if __name__ == "__main__":
    main()
