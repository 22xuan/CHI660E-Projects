#!/usr/bin/env python3
"""CHI660E ORR-RDE 公共模块 — 复用函数与常量"""

from typing import Dict, List, Tuple, Optional, Any

import numpy as np
import pandas as pd
import yaml
from pathlib import Path
from scipy import stats

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent


def load_params() -> Dict[str, Any]:
    with open(PROJECT_DIR / "params.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def angular_velocity(rpm: float) -> float:
    return rpm * 2 * np.pi / 60


def levich_constant(params: Dict[str, Any]) -> float:
    p = params["electrolyte"]
    F = float(p["faraday_constant"])
    D = float(p["o2_diffusion_cm2_per_s"])
    nu = float(p["viscosity_cm2_per_s"])
    C0 = float(p["o2_conc_mol_per_cm3"])
    return 0.62 * F * D ** (2 / 3) * nu ** (-1 / 6) * C0


def convert_potential_to_rhe(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    offset = float(params["reference_electrode"]["conversion_to_rhe"])
    df = df.copy()
    df["potential_vs_rhe"] = df["potential_v"] + offset
    return df


def convert_current_to_density(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    area = float(params["electrode"]["area_for_j"])
    df = df.copy()
    df["current_density_ma_cm2"] = df["current_a"] * 1000 / area
    return df


def ir_correct(
    df: pd.DataFrame,
    ru_ohm: float,
    params: Dict[str, Any],
) -> pd.DataFrame:
    area = float(params["electrode"]["area_for_j"])
    offset = float(params["reference_electrode"]["conversion_to_rhe"])
    df = df.copy()
    df["potential_ir_corrected"] = df["potential_v"] - df["current_a"] * ru_ohm
    df["potential_vs_rhe_ir"] = df["potential_ir_corrected"] + offset
    return df


def find_onset_potential(
    df: pd.DataFrame,
    threshold: float = -0.05,
) -> float:
    below = df[df["current_density_ma_cm2"] < threshold]
    if len(below) == 0:
        return np.nan
    return float(below["potential_v"].iloc[0])


def find_half_wave(df: pd.DataFrame, params: Dict[str, Any]) -> float:
    e_col = "potential_v"
    j_col = "current_density_ma_cm2"

    base_lo, base_hi = params["lsv"]["baseline_range"]
    lim_lo, lim_hi = params["lsv"]["limiting_range"]
    search_lo, search_hi = params["lsv"]["half_wave_search_range"]

    base = df[(df[e_col] >= base_lo) & (df[e_col] <= base_hi)]
    j_base = float(base[j_col].mean()) if len(base) > 0 else 0.0

    lim = df[(df[e_col] >= lim_lo) & (df[e_col] <= lim_hi)]
    j_lim = float(lim[j_col].mean()) if len(lim) > 0 else float(df[j_col].min())

    j_half = (j_base + j_lim) / 2

    descend = df[(df[e_col] >= search_lo) & (df[e_col] <= search_hi)]
    if len(descend) == 0:
        return np.nan

    idx = int((descend[j_col] - j_half).abs().idxmin())
    return float(descend.loc[idx, e_col])


def find_limiting_current_density(df: pd.DataFrame, params: Dict[str, Any]) -> Tuple[float, float]:
    lim_lo, lim_hi = params["lsv"]["limiting_range"]
    lim = df[(df["potential_v"] >= lim_lo) & (df["potential_v"] <= lim_hi)]
    if len(lim) == 0:
        return np.nan, np.nan
    return float(lim["current_density_ma_cm2"].mean()), float(lim["current_density_ma_cm2"].std())


def compute_jk_corrected(j: float, j_lim: float) -> float:
    if abs(j) < 1e-12 or abs(j_lim) < 1e-12:
        return j
    return (abs(j) * abs(j_lim)) / (abs(j_lim) - abs(j)) if abs(j_lim) > abs(j) else j


def extract_kl_data(
    raw_data: Dict[str, Dict[int, pd.DataFrame]],
    params: Dict[str, Any],
) -> Dict[str, Dict[float, List[Tuple[float, float]]]]:
    potentials = params["kl_analysis"]["potentials_vs_hghgo"]
    speeds = params["kl_analysis"]["rotation_speeds_rpm"]
    tol = float(params["lsv"]["sample_interval_v"]) / 2

    kl_data: Dict[str, Dict[float, List[Tuple[float, float]]]] = {}
    for group, group_data in raw_data.items():
        kl_data[group] = {p: [] for p in potentials}
        for rpm in speeds:
            df = group_data.get(rpm)
            if df is None:
                continue
            omega = angular_velocity(rpm)
            omega_neg_half = omega ** (-0.5)

            for pot in potentials:
                mask = (df["potential_v"] >= pot - tol) & (df["potential_v"] <= pot + tol)
                if mask.any():
                    j = df.loc[mask, "current_density_ma_cm2"].mean()
                    j_abs = abs(j)
                    if j_abs > 1e-9:
                        kl_data[group][pot].append((omega_neg_half, 1.0 / j_abs))

    return kl_data


def fit_kl(kl_points: List[Tuple[float, float]]) -> Optional[Dict[str, float]]:
    if len(kl_points) < 3:
        return None

    x = np.array([p[0] for p in kl_points])
    y = np.array([p[1] for p in kl_points])

    slope, intercept, r_value, _p_value, std_err = stats.linregress(x, y)

    return {
        "slope": float(slope),
        "intercept": float(intercept),
        "r_squared": float(r_value) ** 2,
        "std_err": float(std_err),
        "n_points": len(kl_points),
    }


def compute_electron_numbers(
    kl_results: Dict[str, Dict[float, Dict[str, float]]],
    params: Dict[str, Any],
) -> Dict[str, Dict[float, Dict[str, float]]]:
    B = levich_constant(params)

    for group, pot_results in kl_results.items():
        for pot, result in pot_results.items():
            if result and result["slope"] > 0:
                slope_A = result["slope"] * 1000
                n = 1.0 / (slope_A * B)
                result["n_electrons"] = round(n, 2)
                result["j_k_ma_cm2"] = (
                    round(1.0 / result["intercept"], 2) if result["intercept"] > 0 else np.nan
                )
                result["B_levich"] = float(B)
            else:
                if result is not None:
                    result["n_electrons"] = float(np.nan)
                    result["j_k_ma_cm2"] = float(np.nan)

    return kl_results
