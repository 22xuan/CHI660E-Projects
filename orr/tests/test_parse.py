#!/usr/bin/env python3
"""测试: CHI660E TXT 解析 + Hg/HgO -> RHE 电位转换 + 电流密度转换"""

import sys
import yaml
import numpy as np
import pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from common import (
    load_params,
    convert_potential_to_rhe,
    convert_current_to_density,
    find_onset_potential,
    find_half_wave,
    find_limiting_current_density,
)


def test_potential_conversion():
    params = load_params()
    df = pd.DataFrame({"potential_v": [-0.327, 0.0, 0.3]})
    result = convert_potential_to_rhe(df, params)
    assert "potential_vs_rhe" in result.columns
    offset = params["reference_electrode"]["conversion_to_rhe"]
    np.testing.assert_almost_equal(result["potential_vs_rhe"].iloc[0], -0.327 + offset)
    print("  [PASS] 电位转换 (Hg/HgO -> RHE)")


def test_current_density_conversion():
    params = load_params()
    df = pd.DataFrame({"current_a": [0.0, -0.001, 1e-6]})
    result = convert_current_to_density(df, params)
    assert "current_density_ma_cm2" in result.columns
    area = params["electrode"]["area_for_j"]
    expected = -0.001 * 1000 / area
    np.testing.assert_almost_equal(result["current_density_ma_cm2"].iloc[1], expected)
    print("  [PASS] 电流密度转换 (A -> mA/cm2)")


def test_onset_potential():
    E = np.linspace(0.3, -0.9, 100)
    j = np.zeros(100)
    j[40:] = -0.1
    df = pd.DataFrame({"potential_v": E, "current_density_ma_cm2": j})
    e_onset = find_onset_potential(df, threshold=-0.05)
    assert not np.isnan(e_onset)
    assert abs(e_onset - E[40]) < 0.05
    print(f"  [PASS] E_onset 计算: {e_onset:.3f} V")


def test_half_wave():
    params = load_params()
    E = np.linspace(0.3, -0.9, 1200)
    j = -5.0 / (1 + np.exp((E + 0.327) * 15))
    df = pd.DataFrame({"potential_v": E, "current_density_ma_cm2": j})
    e_half = find_half_wave(df, params)
    assert not np.isnan(e_half)
    assert abs(e_half - (-0.327)) < 0.01
    print(f"  [PASS] E_1/2 计算: {e_half:.3f} V (预期 -0.327)")


def test_limiting_current():
    params = load_params()
    E = np.linspace(0.3, -0.9, 1200)
    j = -5.0 / (1 + np.exp((E + 0.327) * 15))
    df = pd.DataFrame({"potential_v": E, "current_density_ma_cm2": j})
    j_lim, j_std = find_limiting_current_density(df, params)
    assert abs(abs(j_lim) - 5.0) < 0.1
    print(f"  [PASS] j_L 计算: {j_lim:.4f} mA/cm2")


def main():
    print("=" * 40)
    print("测试: parse + 电位/电流转换")
    print("=" * 40)
    test_potential_conversion()
    test_current_density_conversion()
    test_onset_potential()
    test_half_wave()
    test_limiting_current()
    print("\n全部测试通过!")


if __name__ == "__main__":
    main()
