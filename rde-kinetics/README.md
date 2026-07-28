# CHI660E RDE 动力学参数测定

## 项目概述

基于 CHI660E 电化学工作站的旋转圆盘电极（RDE）实验数据，
测定 K₄Fe(CN)₆/K₃Fe(CN)₆ 氧化还原体系的动力学参数。
4 组独立操作者，Pt 盘电极（Φ=5mm）。

对应教材：《电化学实验》（唐安平主编）实验 26

## 分析内容

| 分析 | 方法 | 输出 |
|------|------|------|
| **扩散系数 D_O, D_R** | Levich 方程：i_l vs ω¹/² | D_O ≈ 6.55×10⁻⁶, D_R ≈ 4.15×10⁻⁶ cm²/s |
| **浓度校准** | i_l vs c* (0.0002–0.01M) | 线性关系验证 |
| **K-L 分析** | i⁻¹ vs ω⁻¹/² → i_k | 动力学电流 |
| **Tafel 外推** | log|i_k| vs η | b ≈ 60-82 mV/dec, α ≈ 0.72-0.98 |
| **半波电位** | 0.0008M 无KCl | E₁/₂ ≈ 0.17 V (vs Hg/HgO) |

## 项目结构

```
CHI660E-RDE-Kinetics/
├── params.yaml
├── run_all.sh
├── scripts/
│   ├── parse_chi660e.py      # Tafel Plot 3列格式解析
│   ├── levich_analysis.py    # Levich分析 → D_O, D_R
│   ├── kl_analysis.py        # 浓度校准 + K-L + Tafel
│   └── generate_figures.py   # matplotlib 图表
├── tests/
│   └── test_levich.py
└── output/
    ├── processed/  tables/  figures/
```

## 快速开始

```bash
bash run_all.sh
```

## 依赖

numpy scipy pandas matplotlib pyyaml
