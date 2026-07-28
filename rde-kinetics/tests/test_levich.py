#!/usr/bin/env python3
"""测试: Tafel Plot 解析 + Levich 常数计算"""

import sys, numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from levich_analysis import angular_velocity, compute_diffusion_coefficient


def test_angular_velocity():
    omega = angular_velocity(2000)
    expected = 2000 * 2 * np.pi / 60
    assert abs(omega - expected) < 0.01
    print(f"  [PASS] 2000rpm = {omega:.2f} rad/s")


def test_levich_fit():
    # 模拟完美 Levich 数据
    omega_sqrt = np.sqrt(np.array([500, 1000, 1500, 2000, 2500]) * 2 * np.pi / 60)
    D_true = 7.0e-6
    # i_l = K × D^(2/3) × ω^(1/2)
    # K = 0.62 × n × F × A × ν^(-1/6) × c*
    A, nu, c = 0.196, 0.0089, 1e-5  # mol/cm³
    K = 0.62 * 1 * 96485 * A * nu ** (-1 / 6) * c
    i_l = K * D_true ** (2 / 3) * omega_sqrt

    import yaml

    with open(Path(__file__).resolve().parent.parent / "params.yaml") as f:
        params = yaml.safe_load(f)
    D, r2, slope = compute_diffusion_coefficient(i_l.tolist(), omega_sqrt.tolist(), params)
    assert abs(D - D_true) / D_true < 0.02
    assert r2 > 0.999
    print(f"  [PASS] Levich拟合: D={D:.2e} (期望 {D_true:.2e})")


def main():
    print("=" * 40)
    print("测试: RDE 动力学分析")
    print("=" * 40)
    test_angular_velocity()
    test_levich_fit()
    print("\n全部通过!")


if __name__ == "__main__":
    main()
