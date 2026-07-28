#!/usr/bin/env python3
"""测试: .mpt 解析 + 欧洲数字格式转换"""

import sys, tempfile, os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from parse_mpt import _to_float, parse_mpt


def test_to_float():
    assert abs(_to_float("1,1222671E+001") - 11.222671) < 0.001
    assert abs(_to_float("3,0019521E+004") - 30019.521) < 0.01
    assert abs(_to_float("6,4511746E-002") - 0.064511746) < 1e-6
    assert abs(_to_float("-7,3218948E-001") + 0.73218948) < 1e-6
    assert abs(_to_float("0,0000000E+000") - 0.0) < 1e-6
    print("  [PASS] 欧洲数字格式转换 (5 cases)")


def test_parse_mpt_minimal():
    content = """EC-Lab ASCII FILE
Nb header lines : 3                         

freq/Hz\tre(Z)/Ohm\t-Im(Z)/Ohm\t|Z|/Ohm\tPhase(Z)/deg
1,234E+004\t5,678E+001\t1,234E+000\t5,679E+001\t-1,244E+000
5,678E+003\t8,901E+001\t2,345E+000\t8,904E+001\t-1,508E+000
"""

    import tempfile, os

    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".mpt", delete=False, encoding="latin-1")
    try:
        tmp.write(content)
        tmp.close()
        df = parse_mpt(tmp.name, area_cm2=1.0)
        assert len(df) == 2
        assert abs(df.iloc[0]["freq_Hz"] - 12340.0) < 1
        assert abs(df.iloc[0]["Zre_ohm_cm2"] - 56.78) < 0.1
        assert abs(df.iloc[0]["Zim_ohm_cm2"] - 1.234) < 0.01
        assert df["freq_Hz"].is_monotonic_decreasing
        print("  [PASS] .mpt 解析 (2 行, 频率降序)")
    finally:
        os.unlink(tmp.name)


def test_area_normalization():
    content = """EC-Lab ASCII FILE
Nb header lines : 3                         

freq/Hz\tre(Z)/Ohm\t-Im(Z)/Ohm\t|Z|/Ohm\tPhase(Z)/deg
1,000E+004\t1,000E+001\t0,000E+000\t1,000E+001\t0,000E+000
"""

    import tempfile, os

    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".mpt", delete=False, encoding="latin-1")
    try:
        tmp.write(content)
        tmp.close()
        df = parse_mpt(tmp.name, area_cm2=6.4)
        assert abs(df.iloc[0]["Zre_ohm_cm2"] - 64.0) < 0.1
        assert abs(df.iloc[0]["Zim_ohm_cm2"] - 0.0) < 0.01
        print("  [PASS] 面积归一化 (10 Ω × 6.4 cm² = 64 Ω·cm²)")
    finally:
        os.unlink(tmp.name)


def main():
    print("=" * 40)
    print("测试: EIS .mpt 解析")
    print("=" * 40)
    test_to_float()
    test_parse_mpt_minimal()
    test_area_normalization()
    print("\n全部测试通过!")


if __name__ == "__main__":
    main()
