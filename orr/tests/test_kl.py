#!/usr/bin/env python3
"""测试: Levich 常数 + K-L 线性拟合 + n 值计算"""

import sys
import yaml
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from common import (
    load_params,
    angular_velocity,
    levich_constant,
    fit_kl,
    compute_electron_numbers,
    compute_jk_corrected,
)


def test_angular_velocity():
    omega = angular_velocity(1600)
    expected = 1600 * 2 * np.pi / 60
    np.testing.assert_almost_equal(omega, expected)
    print(f"  [PASS] rpm-> rad/s: 1600rpm = {omega:.2f} rad/s")


def test_levich_constant():
    params = load_params()
    B = levich_constant(params)
    assert B > 0
    B_expected = 1.10e-4
    assert abs(B / B_expected - 1.0) < 0.01
    print(f"  [PASS] Levich 常数 B = {B:.4e} (预期 ~1.10e-4)")


def test_fit_kl():
    np.random.seed(42)
    x = np.array([0.02, 0.025, 0.03, 0.035, 0.04, 0.045])
    slope_true = 2.0
    intercept_true = 0.1
    y = slope_true * x + intercept_true + np.random.normal(0, 0.005, len(x))
    points = [(float(x[i]), float(y[i])) for i in range(len(x))]
    result = fit_kl(points)
    assert result is not None
    assert abs(result["slope"] - slope_true) < 0.1
    assert result["r_squared"] > 0.95
    print(f"  [PASS] K-L 拟合: slope={result['slope']:.3f}, R2={result['r_squared']:.4f}")


def test_electron_number():
    params = load_params()
    kl_results = {
        "test": {
            -0.40: {"slope": 2.0, "intercept": 0.1, "r_squared": 0.99, "n_points": 6},
        }
    }
    result = compute_electron_numbers(kl_results, params)
    n = result["test"][-0.40]["n_electrons"]
    B = levich_constant(params)
    n_expected = 1.0 / (2.0 * 1000 * B)
    assert abs(n - n_expected) < 0.5
    assert 0 < n < 10
    print(f"  [PASS] n 值计算: n = {n:.2f}")


def test_jk_correction():
    j_k = compute_jk_corrected(2.0, 5.0)
    expected = (2.0 * 5.0) / (5.0 - 2.0)
    np.testing.assert_almost_equal(j_k, expected)
    print(f"  [PASS] 质量传输校正: j={2.0}, j_L={5.0} -> j_k={j_k:.4f}")

    j_k2 = compute_jk_corrected(6.0, 5.0)
    assert j_k2 == 6.0
    print(f"  [PASS] 校正边界: j>j_L 时不校正, j_k={j_k2}")


def main():
    print("=" * 40)
    print("测试: K-L 分析 + Tafel")
    print("=" * 40)
    test_angular_velocity()
    test_levich_constant()
    test_fit_kl()
    test_electron_number()
    test_jk_correction()
    print("\n全部测试通过!")


if __name__ == "__main__":
    main()
