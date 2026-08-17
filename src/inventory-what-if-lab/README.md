# Inventory What-If Lab

门店库存 What-If 试验台：在默认库存规则之上，研究「一个局部参数变化 → 系统演化 → 宏观行为」。

默认原料含茶/牛奶/珍珠/芝士/芒果/葡萄（葡萄默认不自动采购）；默认配方含珍珠奶茶、纯奶茶、芝芝芒芒（开），多肉葡萄（关）。另含教学用原料单价与饮品售价（可改）。

- **对比实验**：同一 BaseConfig 深拷贝为 Control / Experiment，只改一个变量，各自从 Day 0 跑满 N 天
- **单次仿真**：配置窗口 + 跑一次，用于调试
- **价格统计**：原料单价、售价、报废成本、每日流水、真实盈利
- **保质期扫描**：对单一物料扫多个保质期，观察总报废等宏观指标

## 包结构

```
inventory_abm/
├── domain.py          # MaterialBatch / PurchaseOrder / Recipe / MaterialSpec / SimConfig
├── agents.py          # Store
├── world.py           # World（日循环 + 金额观测）
├── simulation.py      # Simulation
├── metrics.py         # DaySnapshot / SimulationResult / summarize
├── experiment/        # 实验层（不侵入领域决策）
│   ├── variables.py   # 实验变量 + apply_patch
│   ├── runner.py      # ExperimentRunner
│   ├── result.py      # ExperimentResult / 程序化结论
│   └── scan.py        # 物料保质期扫描
└── experiments/       # CLI 薄封装
```

## 依赖与启动

```bash
cd src/inventory-what-if-lab
pip install -r requirements.txt
streamlit run app.py
```

不要用 IDE 直接 `python app.py`（会自动转调 `streamlit run`）。

## 价格口径

| 指标 | 公式 |
|------|------|
| 销售额 | Σ(产量 × 售价) |
| 采购支出 | Σ(采购量 × 原料单价) |
| COGS | Σ(消耗量 × 原料单价) |
| 报废成本 | Σ(报废量 × 原料单价) |
| **每日流水** | 销售额 − 采购支出 |
| **真实盈利** | 销售额 − COGS − 报废成本 |

流水与盈利口径不同：采购进流水、不重复扣盈利；报废进盈利、不另扣流水。价格只影响统计，不改变订货决策。

## UI 用法

页面：**Inventory What-If Lab**

### Tab「对比实验」

1. 选实验变量（保质期 / 提前期 / 订货点 / 订货量 / 期初库存 / 产品开关 / 增减配方 / 原料单价 / 产品售价）
2. 设对照组、实验组与模拟天数（验收常用 365）
3. 点 **▶ 运行实验**
4. 查看：物量双曲线（库存/采购/报废/销售/产量）、金额双曲线（流水/盈利/报废成本）、宏观表、分物料报废、实验发现
5. 可选：展开「参数扫描」，对某物料扫保质期列表

### Tab「单次仿真」

侧边栏设天数与销售上限 → 配置窗口改物料/单价/配方/售价 → 运行仿真。

## 验收示例：芒果保质期 3 vs 7

实验变量选「物料保质期」→ 物料「芒果」→ Control=3、Experiment=7 → 365 天 → 运行。

说明：在**默认**订货量=60、日销上限=20、芝芝芒芒优先消耗芒果的设定下，芒果往往当日周转完毕，保质期 3→7 的宏观差异可能为 0。若要观察报废敏感度，可在实验变量中改「再订货量」（如 60 vs 300），或先调大芒果订货量再扫保质期。

## CLI 参数扫描

```bash
cd src/inventory-what-if-lab
python -m inventory_abm.experiments.shelf_life   # 默认扫芒果保质期
python -m inventory_abm.experiments.lead_time    # 全物料统一提前期（对照）
```

## 导出对比图

```bash
cd src/inventory-what-if-lab
python scripts/export_compare_charts.py
```

## NetLogo 对照（可选）

- `milk-tea-inventory.nlogo` / `.nls` 仅作对照，推荐使用本 Python 版。
