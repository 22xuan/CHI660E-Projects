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
rde-kinetics/
├── .gitignore
├── LICENSE
├── README.md
├── params.yaml
├── requirements.txt
├── run_all.sh
├── scripts/
│   ├── common.py            # 公共函数 (load_params, angular_velocity)
│   ├── parse_chi660e.py      # Tafel Plot 3列格式解析
│   ├── levich_analysis.py    # Levich分析 → D_O, D_R (含基线扣除)
│   ├── kl_analysis.py        # 浓度校准 + K-L + Tafel
│   ├── generate_figures.py   # matplotlib 图表
│   └── error_analysis.py     # 误差传播分析
├── tests/
│   └── test_levich.py
├── report/
│   ├── RDE_分析报告.tex
│   ├── RDE_分析报告.pdf
│   └── RDE_分析报告.md
└── output/
    ├── processed/  tables/  figures/
```

## 快速开始

**前提**：
1. `pip install -r requirements.txt`
2. `data/` 目录已软链接至原始数据

```bash
bash run_all.sh
```

## 已知局限

- D_R 偏低 34%：阳极极限电流平台不完整（误差传播证实非 c*/A/ν 误差）
- α 偏高：过电位选区偏低，反反应贡献
- 基线扣除后 D 值变化 < 0.01%，排除背景电流为主要因素
- 4 组数据大部分转速下一致（CHI660E 导出精度）

## 依赖

numpy scipy pandas matplotlib pyyaml Pillow
