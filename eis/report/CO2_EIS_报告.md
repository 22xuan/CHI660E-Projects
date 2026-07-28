# 低合金钢 CO₂ 腐蚀 EIS 分析

## 摘要

基于 Bio-Logic SP-200 EIS 数据（De Motte et al., Corrosion Science, 2020），
采用 R(Q(RW)) 等效电路 CNLS 拟合分析低合金钢在 CO₂ 饱和盐水（80°C）中的腐蚀行为。

## 实验条件

| 参数 | 数值 |
|------|------|
| 电极 | 低合金钢（ANDRA CIGEO 项目），6.4 cm² |
| 温度 | 80°C |
| 电解液 | CO₂ 饱和盐水（NaCl + NaHCO₃） |
| pH | 6.0 和 6.6 |
| 仪器 | Bio-Logic SP-200 |
| 频率 | 0.01 Hz – 30 kHz |
| 数据协议 | CC BY 4.0 |

## 等效电路：R(Q(RW))

```
Rs — CPE1 // (R1 + Warburg(Z_W))
```

| 参数 | 含义 |
|------|------|
| Rs | 溶液电阻 |
| R1 | 电荷转移电阻 |
| CPE (Q1, n1) | 界面非理想电容 |
| W, P | 扩散层阻抗 |

## 拟合结果

| 参数 | pH 6.6 | pH 6.0 |
|------|--------|--------|
| Rs (Ω·cm²) | 54.1 | 90.1 |
| R1 (Ω·cm²) | 5,978 | 3,599 |
| Q1 (S·s^n/cm²) | 1.83×10⁻⁴ | 7.0×10⁻⁵ |
| n1 | 0.582 | 0.765 |
| W (Ω·cm²) | 571 | 62 |
| P | 0.8 | 0.8 |
| **R_total (Ω·cm²)** | **6,548** | **3,661** |

## 结论

- pH 6.6 的 R_total 约为 pH 6.0 的 1.8 倍，较高 pH 促进更具保护性的 FeCO₃ 层
- CPE 指数 n1 < 0.6 表明腐蚀表面高度不均匀
- C_eff ≈ 6×10⁻⁶ F/cm²，与含 FeCO₃ 层的钢/盐水界面电容量级一致
- 简单 R(Q(RW)) 模型 χ²≈10¹¹，精确定量需 R(QR)(QR) 双层模型

## 局限

- 等效电路不唯一（R(QR), R(Q(RW)), R(QR)(QR) 可能给出相似视觉拟合）
- 电极面积 6.4 cm² 来自文件名，可能偏离实际有效面积
- 未用 LPR 数据独立验证 Rp

## 参考文献

1. De Motte et al., *Corrosion Science*, 2020, **172**, 108666
2. Orazem & Tribollet, *Electrochemical Impedance Spectroscopy*, Wiley, 2008
3. Hsu & Mansfeld, *Corrosion*, 2001, **57**(9), 747–748
