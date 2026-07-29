# CHI660E ORR-RDE 数据分析项目

## 项目概述

基于 CHI660E 电化学工作站的旋转圆盘电极（RDE）氧还原反应（ORR）数据自动化分析系统。实验由 4 组独立操作者分别完成，采用 304/316 不锈钢工作电极。

## 就业展示能力点

| 能力维度 | 具体体现 |
|---------|---------|
| **电化学理论** | ORR 反应机理、RDE 质量传输理论、Koutecky-Levich 方程、Tafel 动力学分析、iR 补偿 |
| **Python 编程** | 数据自动化解析、科学计算（NumPy/SciPy/Pandas）、Matplotlib 可视化、类型注解、模块化设计 |
| **工程素养** | 多格式兼容、可复现分析流水线、YAML 参数化配置、单元测试、Git 版本控制 |
| **OriginPro** | originpro API 出图、图生成（Windows） |
| **项目管理** | 结构化文件组织、CSV 中间格式、LaTeX 学术报告 |

## 项目结构

```
orr/
├── .gitignore
├── README.md
├── run_all.sh                # 一键全流程脚本
├── requirements.txt
├── params.yaml               # 实验参数与配置 (YAML)
├── scripts/
│   ├── common.py             # 公共函数模块 (Levich/K-L/Tafel/iR)
│   ├── parse_chi660e.py      # 步骤1: TXT解析 + 电位/电流密度转换
│   ├── lsv_metrics.py        # 步骤2: E_onset, E_1/2, j_L + iR补偿估算
│   ├── kl_analysis.py        # 步骤3: K-L拟合 + n值 + Tafel斜率
│   ├── generate_tables.py    # 步骤4: 催化剂汇总 + 组间对比 (CSV+Markdown)
│   ├── generate_figures.py   # matplotlib 预览图
│   └── origin_plot_orr.py    # OriginPro 出图 (Windows)
├── tests/
│   ├── test_parse.py         # 解析/电位/电流测试
│   └── test_kl.py            # Levich常数/K-L拟合/n值测试
├── output/
│   ├── processed/            # 中间数据 (CSV)
│   ├── tables/               # 分析表格
│   ├── figures/              # 图表
│   └── origin_input/         # Origin 导入数据
└── report/
    ├── ORR_RDE_分析报告.pdf   # LaTeX 编译 PDF
    ├── ORR_RDE_分析报告.tex   # LaTeX 源码
    └── ORR_RDE_分析报告.md    # Markdown 版
```

## 快速开始

### 数据准备

将 CHI660E 导出的 TXT 文件按以下结构放入 `data/` 目录（或创建软链接指向实际数据目录）：

```
data/
├── 1组/
│   ├── 1/1000r-1.TXT
│   └── txt/{1200r,1600r,2000r,2500r,3000r}-*.txt
├── 2组/txt/...
├── 3组/txt/...
└── 4组/txt/...
```

### WSL/Linux 环境

```bash
bash run_all.sh    # 一键全流程
```

### 运行测试

```bash
python3 tests/test_parse.py && python3 tests/test_kl.py
```

### Windows OriginPro 出图

```powershell
D:\Anaconda\python.exe scripts\origin_plot_orr.py
```

## 实验概况

| 参数 | 数值 |
|------|------|
| 仪器 | CHI660E 电化学工作站 |
| 技术 | LSV (Linear Sweep Voltammetry) |
| 工作电极 | 304不锈钢/316不锈钢, Φ=5mm, A=0.196 cm² (AB胶连接) |
| 参比电极 | Hg/HgO (0.1M KOH) |
| 电解液 | 0.1M KOH, O₂ 饱和 |
| 扫描范围 | 0.3 → -0.9 V vs Hg/HgO |
| 扫描速率 | 10 mV/s |
| 转速 | 1000, 1200, 1600, 2000, 2500, 3000 rpm |
| iR 补偿 | 未开启（R_u=50-150Ω 为估计值） |

> 注：4 组独立操作者分别完成实验。1200-3000rpm 数据完全一致（CHI660E 4 位有效数字精度限制），差异仅见于 1000rpm。

### 催化剂分组（4 组独立实验）

| 组别 | 催化剂 | 工作电极 | 操作者 |
|------|--------|---------|--------|
| 1组 | Co₃O₄/C | 304SS | A1 |
| 2组 | 20% Pt/C | 304SS | A2 |
| 3组 | Co₃O₄/C | 316SS | B1 |
| 4组 | 20% Pt/C | 316SS | B2 |

## K-L 方程参数 (0.1M KOH, 25°C)

| 符号 | 参数 | 数值 |
|------|------|------|
| ν | 动力学粘度 | 1.009×10⁻² cm²/s |
| D₀ | O₂ 扩散系数 | 1.9×10⁻⁵ cm²/s |
| C₀ | O₂ 溶解浓度 | 1.2×10⁻⁶ mol/cm³ |
| B | Levich 常数 | 1.10×10⁻⁴ A·s^(1/2)/(cm²·rad^(1/2)) |

## 已知局限

1. 无 N₂ 背景扣除、无 EIS 实测 R_u、无玻碳电极对照、无 RRDE 验证 n 值
2. CHI660E 4 位有效数字导出精度限制了 1200-3000rpm 的测量区分度
3. 催化剂与 SS 基底类型绑定，未做交叉对照

详见报告第 5 节「局限性与改进方向」。

## 参考文献

1. Spendelow & Wieckowski, *PCCP*, 2007, 9(21), 2654-2675. DOI: 10.1039/B703315J
2. Ge et al., *ACS Catal.*, 2015, 5(8), 4643-4667. DOI: 10.1021/acscatal.5b00524
3. Bard & Faulkner, *Electrochemical Methods*, 2nd ed., Wiley, 2001
4. van der Vliet et al., *J. Electroanal. Chem.*, 2010, 647(1), 29-34. DOI: 10.1016/j.jelechem.2010.05.016
5. Kim, *Corrosion*, 1999, 55(5), 456-461. DOI: 10.5006/1.3284007
6. Xu et al., *Electrochim. Acta*, 2017, 255, 99-108. DOI: 10.1016/j.electacta.2017.09.145

## 依赖

```
numpy scipy pandas matplotlib pyyaml tabulate pytest
```
