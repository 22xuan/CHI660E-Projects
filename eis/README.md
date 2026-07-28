# EIS 分析 — 低合金钢 CO₂ 腐蚀

基于 Bio-Logic SP-200 电化学阻抗谱（EIS）数据，
对低合金钢在 CO₂ 饱和盐水（80°C, pH 6.0/6.6）中的腐蚀行为进行分析。

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

### 等效电路：Randles R(QR)

```
Rs — (CPE // Rp)
```

| 元件 | 含义 |
|------|------|
| Rs | 溶液电阻 |
| Rp | 极化电阻（电荷转移电阻），越高耐蚀性越好 |
| CPE-Q | 常相位元件系数，替代理想电容 |
| CPE-n | 指数（n→1 偏理想电容，n<1 反映表面不均匀） |

### CNLS 拟合

复数非线性最小二乘（Complex Nonlinear Least Squares），同时拟合实部和虚部，采用模量加权（1/|Z|）平衡高频和低频数据点的影响。

## 项目结构

```
eis/
├── params.yaml          # 实验参数
├── run_all.sh
├── scripts/
│   ├── parse_mpt.py     # Bio-Logic .mpt 解析（欧洲逗号格式）
│   ├── plot_eis.py      # Nyquist + Bode 图
│   └── circuit_fit.py   # Randles R(QR) CNLS 拟合
├── output/
│   ├── figures/         # Nyquist, Bode, Fit 图
│   └── tables/          # 拟合参数表
└── data -> symlink
```

## 快速开始

```bash
bash run_all.sh
```

## 参考文献

1. De Motte, R. et al. "A study by electrochemical impedance spectroscopy and surface analysis of corrosion product layers formed during CO₂ corrosion of low alloy steel." *Corrosion Science*, 2020, **172**, 108666.
2. Orazem, M.E. & Tribollet, B. *Electrochemical Impedance Spectroscopy*. Wiley, 2008.
