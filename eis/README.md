# EIS 分析 — 低合金钢 CO₂ 腐蚀

基于 Bio-Logic SP-200 电化学阻抗谱（EIS）数据，
对低合金钢在 CO₂ 饱和盐水（80°C, pH 6.0/6.6）中的腐蚀行为进行 R(Q(RW)) 等效电路分析。

## 数据来源

- **论文**: De Motte et al., *Corrosion Science*, 2020, **172**, 108666
- **DOI**: [10.1016/j.corsci.2020.108666](https://doi.org/10.1016/j.corsci.2020.108666)
- **数据集**: [Mendeley Data yvdggv253v/1](https://data.mendeley.com/datasets/yvdggv253v/1)
- **协议**: CC BY 4.0
- **背景**: ANDRA 法国核废料深地质处置项目

## 实验体系

| 参数 | 数值 |
|------|------|
| 电极 | 低合金钢（核废料容器候选材料） |
| 面积 | 6.4 cm² |
| 温度 | 80°C |
| 介质 | CO₂ 饱和盐水（NaCl + NaHCO₃） |
| pH | 6.0 和 6.6 |
| 仪器 | Bio-Logic SP-200 |

## 分析方法

### 等效电路：R(Q(RW))

```
Rs — CPE1 // (R1 + Warburg(Z_W))
```

| 元件 | 含义 |
|------|------|
| Rs | 溶液电阻 |
| R1 | 电荷转移电阻 |
| CPE1 (Q1, n1) | 界面非理想电容（n<1 反映表面不均匀） |
| W, P | Warburg 扩散阻抗（P=0.5 半无限扩散） |

### CNLS 拟合

复数非线性最小二乘：分步拟合（Rs 固定 → R(QR) 初值 → +Warburg 精修），
模量加权（1/|Z|），`scipy.optimize.curve_fit`。

## 拟合结果

| 参数 | pH 6.6 | pH 6.0 |
|------|--------|--------|
| Rs (Ω·cm²) | 54.1 | 90.1 |
| R_total (Ω·cm²) | **6,548** | **3,661** |
| n1 | 0.582 | 0.765 |

pH 6.6 的 R_total 约为 pH 6.0 的 1.8 倍，较高 pH 促进更具保护性的 FeCO₃ 腐蚀产物层。

## 项目结构

```
eis/
├── params.yaml          # 实验参数
├── run_all.sh
├── requirements.txt
├── scripts/
│   ├── parse_mpt.py     # Bio-Logic .mpt 解析（欧洲逗号格式）
│   ├── plot_eis.py      # Nyquist + Bode 图
│   └── circuit_fit.py   # R(Q(RW)) CNLS 拟合
├── tests/
│   └── test_parse.py    # 3 项测试（逗号转换 + 解析 + 面积归一化）
├── report/
│   ├── CO2_EIS_报告.pdf # LaTeX 报告 (768K)
│   ├── CO2_EIS_报告.tex
│   └── CO2_EIS_报告.md
└── output/
    ├── processed/  figures/  tables/
```

## 快速开始

```bash
bash run_all.sh
```

## 已知局限

- 简单 R(Q(RW)) 模型 χ²≈10¹¹，精确定量需双层模型 R(QR)(QR)
- 电极面积 6.4 cm² 来自文件名，EC-Lab 头文件为占位符
- 无 LPR 数据独立验证 R_total

## 参考文献

1. De Motte et al., *Corrosion Science*, 2020, **172**, 108666
2. Orazem & Tribollet, *Electrochemical Impedance Spectroscopy*, Wiley, 2008
3. Hsu & Mansfeld, *Corrosion*, 2001, **57**(9), 747–748
