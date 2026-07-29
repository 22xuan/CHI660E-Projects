#!/usr/bin/env python3
"""Bio-Logic .mpt 格式解析 — 提取 EIS 数据（欧洲逗号格式）"""

import yaml
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Tuple
from scipy import stats

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent


def load_params() -> Dict[str, Any]:
    with open(PROJECT_DIR / "params.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _to_float(s: str) -> float:
    return float(s.replace(",", ".").strip())


def parse_mpt(filepath: str, area_cm2: float = 1.0) -> pd.DataFrame:
    n_skip = 0
    rows: List[Tuple[float, float, float, float, float]] = []

    with open(filepath, encoding="latin-1") as f:
        lines = f.readlines()

    for line in lines:
        if line.startswith("Nb header lines"):
            n_skip = int(line.split(":")[1].strip())
            break

    for i, line in enumerate(lines):
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
    # Aggregate: round frequency to 1Hz then group by median (SP-200 repeats each freq ~700x)
    df["freq_group"] = df["freq_Hz"].round(0)
    df = (
        df.groupby("freq_group", as_index=False)
        .agg(
            {
                "Zre_ohm_cm2": "median",
                "Zim_ohm_cm2": "median",
                "Zmod_ohm_cm2": "median",
                "Phase_deg": "median",
            }
        )
        .rename(columns={"freq_group": "freq_Hz"})
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

    # Part E: LPR
    lpr_conds = params.get("lpr_conditions", [])
    lpr_rows = []
    if lpr_conds:
        print("\n[LPR] 线性极化分析...")
        for c in lpr_conds:
            fp = PROJECT_DIR / "data" / c["file"]
            if not fp.exists():
                continue
            ocp, rp, r2, npt = parse_lpr(str(fp), area_cm2=area)
            print(f"  {c['label']}: OCP={ocp:.4f}V, Rp={rp:.0f} Ω·cm², R²={r2:.4f}, pts={npt}")
            lpr_rows.append(
                {
                    "pH": c["pH"],
                    "OCP_V": round(ocp, 4),
                    "Rp_LPR_ohm_cm2": round(rp, 0),
                    "R2": round(r2, 4),
                }
            )
        if lpr_rows:
            _lpr_out = PROJECT_DIR / params["output"]["tables_dir"]
            _lpr_out.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(lpr_rows).to_csv(
                _lpr_out / "lpr_results.csv", index=False, encoding="utf-8-sig"
            )
            print(f"  LPR结果已保存到 {_lpr_out / 'lpr_results.csv'}")


def parse_lpr(filepath: str, area_cm2: float = 1.0) -> tuple:
    """Parse Linear Polarization .mpt, return (OCP_V, Rp_ohm_cm2, R2, n_points)."""
    n_skip = 0
    with open(filepath, encoding="latin-1") as f:
        for line in f:
            if line.startswith("Nb header lines"):
                n_skip = int(line.split(":")[1].strip())
                break

    rows_e, rows_i = [], []
    with open(filepath, encoding="latin-1") as f:
        for i, line in enumerate(f):
            if i < n_skip:
                continue
            parts = line.strip().split("\t")
            if len(parts) < 8:
                continue
            try:
                e = _to_float(parts[6])
                i_ma = _to_float(parts[7])
                if abs(i_ma) > 1e-12:
                    rows_e.append(e)
                    rows_i.append(i_ma * 1e-3 / area_cm2)
            except (ValueError, IndexError):
                continue

    idx_zero = int(np.argmin(np.abs(np.array(rows_i))))
    ocp = rows_e[idx_zero]

    mask = [abs(e - ocp) < 0.010 for e in rows_e]
    if sum(mask) < 5:
        mask = [abs(e - ocp) < 0.020 for e in rows_e]

    x = np.array([rows_e[i] for i in range(len(rows_e)) if mask[i]])
    y = np.array([rows_i[i] for i in range(len(rows_i)) if mask[i]])
    slope, _, r_val, _, _ = stats.linregress(x, y)
    rp = abs(1.0 / slope) if abs(slope) > 1e-12 else np.nan
    return ocp, rp, float(r_val) ** 2, len(x)


if __name__ == "__main__":
    main()
