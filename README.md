# CHI660E 电化学数据分析项目集

基于 CHI660E 电化学工作站的 Python 自动化数据分析流水线。

## 项目

### [ORR-RDE 氧还原分析](orr/)

催化剂的氧还原反应（ORR）性能分析：
- Koutecky-Levich 电子转移数（$n$）、Tafel 动力学、iR 补偿
- Co$_3$O$_4$/C vs 20% Pt/C，304/316 不锈钢电极
- 4 组独立操作者跨操作者可复现性
- LaTeX 学术报告（含文献对比与局限性分析）

### [RDE 动力学参数测定](rde-kinetics/)

旋转圆盘电极测定 Fe(CN)$_6^{3-/4-}$ 氧化还原体系动力学参数：
- Levich 分析 → 扩散系数 $D_{\text{O}}$, $D_{\text{R}}$
- K-L 分析 → 动力学电流 $i_k$
- Tafel 外推 → 传递系数 $\alpha$, 交换电流 $i_0$
- Pt 盘电极，4 组独立操作者

## 快速开始

```bash
cd orr/ && bash run_all.sh           # ORR 全流程
cd rde-kinetics/ && bash run_all.sh  # RDE 全流程
```

## 技术栈

Python (NumPy, SciPy, Pandas, Matplotlib, PyYAML) + OriginPro + LaTeX

## 协议

MIT License
