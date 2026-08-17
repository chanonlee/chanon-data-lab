"""Inventory What-If Lab — 复杂系统实验台（Streamlit）。

对比实验为主 Tab；单次仿真保留为调试入口。
"""

from __future__ import annotations

import copy
from typing import Any

import pandas as pd
import streamlit as st

from inventory_abm.domain import (
    MaterialSpec,
    Recipe,
    SimConfig,
    default_materials,
    default_recipes,
)
from inventory_abm.experiment import (
    DEFAULT_SHELF_SCAN,
    ExperimentRunner,
    ExperimentVariable,
    MATERIAL_KINDS,
    RECIPE_KINDS,
    VariableKind,
    scan_shelf_life,
)
from inventory_abm.simulation import Simulation

POLICY_LABELS = {
    "reorder-point": "再订货点",
    "none": "不自动采购",
}
POLICY_VALUES = {v: k for k, v in POLICY_LABELS.items()}

KIND_LIST = list(VariableKind)


def _ensure_state() -> None:
    if "materials" not in st.session_state:
        st.session_state["materials"] = default_materials()
    if "recipes" not in st.session_state:
        st.session_state["recipes"] = default_recipes()
    if "sim_days" not in st.session_state:
        st.session_state["sim_days"] = 30
    if "sales_cap_enabled" not in st.session_state:
        st.session_state["sales_cap_enabled"] = True
    if "sales_cap_per_day" not in st.session_state:
        st.session_state["sales_cap_per_day"] = 20
    if "exp_days" not in st.session_state:
        st.session_state["exp_days"] = 365


def _base_config(days: int) -> SimConfig:
    return SimConfig(
        days=int(days),
        materials=copy.deepcopy(st.session_state["materials"]),
        recipes=copy.deepcopy(st.session_state["recipes"]),
        sales_cap_enabled=bool(st.session_state["sales_cap_enabled"]),
        sales_cap_per_day=max(1, int(st.session_state["sales_cap_per_day"])),
    )


def _materials_to_df(materials: dict[str, MaterialSpec]) -> pd.DataFrame:
    rows = []
    for m in materials.values():
        rows.append(
            {
                "键": m.key,
                "名称": m.display_name,
                "期初库存": float(m.initial_stock),
                "保质期(天)": int(m.shelf_life),
                "到货天数": int(m.lead_time_days),
                "订货点": float(m.reorder_point),
                "订货量": float(m.order_quantity),
                "单价": float(m.unit_cost),
                "采购规则": POLICY_LABELS.get(m.purchase_policy, "再订货点"),
            }
        )
    return pd.DataFrame(rows)


def _df_to_materials(df: pd.DataFrame) -> dict[str, MaterialSpec]:
    out: dict[str, MaterialSpec] = {}
    for _, row in df.iterrows():
        key = str(row["键"]).strip()
        if not key:
            continue
        policy_label = str(row["采购规则"])
        out[key] = MaterialSpec(
            key=key,
            display_name=str(row["名称"]).strip() or key,
            initial_stock=float(row["期初库存"]),
            shelf_life=max(1, int(row["保质期(天)"])),
            lead_time_days=max(1, int(row["到货天数"])),
            reorder_point=float(row["订货点"]),
            order_quantity=max(0.0, float(row["订货量"])),
            unit_cost=max(0.0, float(row["单价"])),
            purchase_policy=POLICY_VALUES.get(policy_label, "reorder-point"),
        )
    return out


@st.dialog("仿真配置窗口", width="large")
def open_settings_dialog() -> None:
    """物料 + 配方设置窗口。"""
    tab_mat, tab_recipe = st.tabs(["物料设置", "配方设置"])

    with tab_mat:
        st.caption(
            "每种物料可单独设置：保质期、到货天数、订货点/订货量、单价、采购规则。"
        )
        edited = st.data_editor(
            _materials_to_df(st.session_state["materials"]),
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "采购规则": st.column_config.SelectboxColumn(
                    options=list(POLICY_LABELS.values()),
                    required=True,
                ),
                "保质期(天)": st.column_config.NumberColumn(min_value=1, step=1),
                "到货天数": st.column_config.NumberColumn(
                    min_value=1,
                    step=1,
                    help="下单后几天到货；1=次日到",
                ),
                "单价": st.column_config.NumberColumn(min_value=0.0, step=0.01),
            },
            key="mat_editor",
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("恢复默认物料", use_container_width=True):
                st.session_state["materials"] = default_materials()
                st.rerun()
        with c2:
            if st.button("保存物料", type="primary", use_container_width=True):
                mats = _df_to_materials(edited)
                if not mats:
                    st.error("至少保留一种物料。")
                else:
                    st.session_state["materials"] = mats
                    for recipe in st.session_state["recipes"]:
                        recipe.ingredients = {
                            k: v
                            for k, v in recipe.ingredients.items()
                            if k in mats
                        }
                    st.success("物料已保存。")

    with tab_recipe:
        st.caption(
            "可配置多种奶茶配方与售价；每日按用料复杂度从高到低生产，"
            "并受销售上限约束。"
        )
        materials = st.session_state["materials"]
        mat_keys = list(materials.keys())
        recipes: list[Recipe] = st.session_state["recipes"]

        for i, recipe in enumerate(list(recipes)):
            with st.expander(f"配方 {i + 1}：{recipe.name}", expanded=(i == 0)):
                name = st.text_input("名称", value=recipe.name, key=f"rname_{i}")
                enabled = st.checkbox("启用", value=recipe.enabled, key=f"ren_{i}")
                sell_price = st.number_input(
                    "售价（元/杯）",
                    min_value=0.0,
                    value=float(recipe.sell_price),
                    step=0.5,
                    key=f"rprice_{i}",
                )
                amounts: dict[str, float] = {}
                cols = st.columns(min(3, max(1, len(mat_keys))))
                for j, key in enumerate(mat_keys):
                    label = materials[key].display_name
                    default = float(recipe.ingredients.get(key, 0.0))
                    with cols[j % len(cols)]:
                        amounts[key] = float(
                            st.number_input(
                                f"{label}（{key}）",
                                min_value=0.0,
                                value=default,
                                step=1.0,
                                key=f"ring_{i}_{key}",
                            )
                        )
                bc1, bc2 = st.columns(2)
                with bc1:
                    if st.button("保存此配方", key=f"rsave_{i}", use_container_width=True):
                        recipes[i] = Recipe(
                            name=name.strip() or f"配方{i + 1}",
                            ingredients={k: v for k, v in amounts.items() if v > 0},
                            enabled=enabled,
                            sell_price=float(sell_price),
                        )
                        st.session_state["recipes"] = recipes
                        st.success(f"已保存：{recipes[i].name}")
                with bc2:
                    if st.button("删除此配方", key=f"rdel_{i}", use_container_width=True):
                        recipes.pop(i)
                        st.session_state["recipes"] = recipes
                        st.rerun()

        if st.button("新增空白配方", use_container_width=True):
            recipes.append(
                Recipe(
                    name=f"新配方{len(recipes) + 1}",
                    ingredients={},
                    enabled=True,
                    sell_price=12.0,
                )
            )
            st.session_state["recipes"] = recipes
            st.rerun()

        if st.button("恢复默认配方", use_container_width=True):
            st.session_state["recipes"] = default_recipes()
            st.rerun()


def _dual_chart(title: str, days: list[int], control: list[float], experiment: list[float]) -> None:
    st.subheader(title)
    df = pd.DataFrame(
        {"day": days, "Control": control, "Experiment": experiment}
    ).set_index("day")
    st.line_chart(df)


def _default_control_value(kind: VariableKind, mat: MaterialSpec | None, recipe: Recipe | None) -> Any:
    if kind == VariableKind.SHELF_LIFE and mat:
        return int(mat.shelf_life)
    if kind == VariableKind.LEAD_TIME and mat:
        return int(mat.lead_time_days)
    if kind == VariableKind.REORDER_POINT and mat:
        return float(mat.reorder_point)
    if kind == VariableKind.ORDER_QUANTITY and mat:
        return float(mat.order_quantity)
    if kind == VariableKind.INITIAL_STOCK and mat:
        return float(mat.initial_stock)
    if kind == VariableKind.UNIT_COST and mat:
        return float(mat.unit_cost)
    if kind == VariableKind.PRODUCT_SWITCH and recipe:
        return bool(recipe.enabled)
    if kind == VariableKind.SELL_PRICE and recipe:
        return float(recipe.sell_price)
    return 0


def _render_experiment_tab() -> None:
    st.markdown("## ① 实验设置")
    st.caption("一次实验只改变一个局部变量；Control 与 Experiment 从相同初始条件各自从 Day 0 起步。")

    kind = st.selectbox(
        "实验变量",
        options=KIND_LIST,
        format_func=lambda k: k.value,
        key="exp_kind",
    )

    materials: dict[str, MaterialSpec] = st.session_state["materials"]
    recipes: list[Recipe] = st.session_state["recipes"]
    mat_options = {m.display_name: k for k, m in materials.items()}
    recipe_names = [r.name for r in recipes]

    material_key: str | None = None
    recipe_name: str | None = None
    recipe_mode: str | None = None
    control_value: Any = None
    experiment_value: Any = None

    if kind in MATERIAL_KINDS:
        mat_label = st.selectbox("物料", options=list(mat_options.keys()), key="exp_mat")
        material_key = mat_options[mat_label]
        mat = materials[material_key]
        default_c = _default_control_value(kind, mat, None)
        if kind in (VariableKind.SHELF_LIFE, VariableKind.LEAD_TIME):
            c1, c2 = st.columns(2)
            with c1:
                control_value = st.number_input(
                    "对照组", min_value=1, value=int(default_c), step=1, key="exp_c_int"
                )
            with c2:
                exp_default = 7 if kind == VariableKind.SHELF_LIFE else max(1, int(default_c) + 1)
                experiment_value = st.number_input(
                    "实验组", min_value=1, value=int(exp_default), step=1, key="exp_e_int"
                )
        else:
            c1, c2 = st.columns(2)
            with c1:
                control_value = st.number_input(
                    "对照组",
                    min_value=0.0,
                    value=float(default_c),
                    step=1.0 if kind != VariableKind.UNIT_COST else 0.01,
                    key="exp_c_float",
                )
            with c2:
                exp_default = float(default_c) * 2 if kind == VariableKind.INITIAL_STOCK else (
                    float(default_c) + 0.1 if kind == VariableKind.UNIT_COST else float(default_c) + 10
                )
                experiment_value = st.number_input(
                    "实验组",
                    min_value=0.0,
                    value=float(exp_default),
                    step=1.0 if kind != VariableKind.UNIT_COST else 0.01,
                    key="exp_e_float",
                )
    elif kind == VariableKind.RECIPE_ADD_REMOVE:
        recipe_name = st.selectbox("配方", options=recipe_names, key="exp_recipe_ar")
        recipe_mode = st.radio(
            "操作",
            options=["add", "remove"],
            format_func=lambda x: "实验组增加" if x == "add" else "实验组移除",
            horizontal=True,
            key="exp_recipe_mode",
        )
        control_value = recipe_mode
        experiment_value = recipe_mode
        st.caption(
            "增加：Control 关闭该配方，Experiment 开启。"
            "移除：Control 开启，Experiment 关闭。"
        )
    elif kind in RECIPE_KINDS:
        recipe_name = st.selectbox("配方", options=recipe_names, key="exp_recipe")
        recipe = next(r for r in recipes if r.name == recipe_name)
        if kind == VariableKind.PRODUCT_SWITCH:
            c1, c2 = st.columns(2)
            with c1:
                control_value = st.checkbox(
                    "对照组启用", value=bool(recipe.enabled), key="exp_c_bool"
                )
            with c2:
                experiment_value = st.checkbox(
                    "实验组启用", value=not bool(recipe.enabled), key="exp_e_bool"
                )
        else:
            c1, c2 = st.columns(2)
            with c1:
                control_value = st.number_input(
                    "对照组售价",
                    min_value=0.0,
                    value=float(recipe.sell_price),
                    step=0.5,
                    key="exp_c_price",
                )
            with c2:
                experiment_value = st.number_input(
                    "实验组售价",
                    min_value=0.0,
                    value=float(recipe.sell_price) + 2.0,
                    step=0.5,
                    key="exp_e_price",
                )

    st.session_state["exp_days"] = st.number_input(
        "模拟天数",
        min_value=5,
        max_value=2000,
        value=int(st.session_state["exp_days"]),
        step=5,
        key="exp_days_input",
    )

    with st.expander("基底配置（价格 / 销售上限，两组共用）"):
        st.session_state["sales_cap_enabled"] = st.checkbox(
            "启用销售上限",
            value=bool(st.session_state["sales_cap_enabled"]),
            key="exp_cap_en",
        )
        st.session_state["sales_cap_per_day"] = st.number_input(
            "每日上限（杯）",
            min_value=1,
            value=int(st.session_state["sales_cap_per_day"]),
            step=10,
            disabled=not st.session_state["sales_cap_enabled"],
            key="exp_cap_n",
        )
        if st.button("打开配置窗口（物料单价 / 配方售价）", key="exp_open_cfg"):
            open_settings_dialog()

    run_exp = st.button("▶ 运行实验", type="primary", use_container_width=True)

    if run_exp:
        variable = ExperimentVariable(
            kind=kind,
            material_key=material_key,
            recipe_name=recipe_name,
            control_value=control_value,
            experiment_value=experiment_value,
            recipe_mode=recipe_mode,
        )
        base = _base_config(int(st.session_state["exp_days"]))
        try:
            result = ExperimentRunner.run_from_base(
                base, variable, int(st.session_state["exp_days"])
            )
        except Exception as exc:  # noqa: BLE001
            st.error(f"实验失败：{exc}")
            return
        st.session_state["exp_result"] = result
        st.session_state["exp_variable"] = variable

    if "exp_result" not in st.session_state:
        st.info("设置实验变量后点击「运行实验」。")
        return

    result = st.session_state["exp_result"]
    variable: ExperimentVariable = st.session_state["exp_variable"]
    ctrl_h = result.control.history
    exp_h = result.experiment.history
    days = [h.day for h in ctrl_h]

    st.markdown("---")
    st.markdown("## ② 系统演化")
    st.caption(f"已改变：{variable.describe()}")
    st.caption("当前模型中日销售量 ≡ 日产量（按销售上限生产即售出）。")

    _dual_chart(
        "总库存",
        days,
        [sum(h.stock.values()) for h in ctrl_h],
        [sum(h.stock.values()) for h in exp_h],
    )
    _dual_chart(
        "每日采购量",
        days,
        [h.purchase_day for h in ctrl_h],
        [h.purchase_day for h in exp_h],
    )
    _dual_chart(
        "每日报废量",
        days,
        [h.waste_day for h in ctrl_h],
        [h.waste_day for h in exp_h],
    )
    _dual_chart(
        "每日销售量",
        days,
        [h.produced_day for h in ctrl_h],
        [h.produced_day for h in exp_h],
    )
    _dual_chart(
        "每日产量",
        days,
        [h.produced_day for h in ctrl_h],
        [h.produced_day for h in exp_h],
    )

    st.markdown("### 金额演化")
    st.caption(
        "流水 = 销售额 − 采购支出；盈利 = 销售额 − COGS − 报废成本。"
        "两者口径不同，勿直接相加比较。"
    )
    _dual_chart(
        "每日流水",
        days,
        [h.cash_flow_day for h in ctrl_h],
        [h.cash_flow_day for h in exp_h],
    )
    _dual_chart(
        "真实盈利（日）",
        days,
        [h.profit_day for h in ctrl_h],
        [h.profit_day for h in exp_h],
    )
    _dual_chart(
        "每日报废成本",
        days,
        [h.waste_cost_day for h in ctrl_h],
        [h.waste_cost_day for h in exp_h],
    )

    st.markdown("---")
    st.markdown("## ③ 宏观结果")
    st.dataframe(
        pd.DataFrame(result.comparison_rows),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("## ④ 物料层面的结果")
    st.dataframe(
        pd.DataFrame(result.waste_rows),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("## ⑤ 实验发现")
    st.markdown(result.insight)

    st.markdown("---")
    st.markdown("## ⑥ 参数扫描（物料保质期）")
    with st.expander("运行保质期扫描", expanded=False):
        scan_mat_label = st.selectbox(
            "扫描物料",
            options=list(mat_options.keys()),
            key="scan_mat",
        )
        scan_key = mat_options[scan_mat_label]
        scan_vals_text = st.text_input(
            "保质期列表（逗号分隔）",
            value=",".join(str(v) for v in DEFAULT_SHELF_SCAN),
            key="scan_vals",
        )
        scan_days = st.number_input(
            "扫描模拟天数",
            min_value=5,
            value=int(st.session_state["exp_days"]),
            step=5,
            key="scan_days",
        )
        if st.button("运行参数扫描", key="run_scan"):
            try:
                vals = [int(x.strip()) for x in scan_vals_text.split(",") if x.strip()]
            except ValueError:
                st.error("请输入整数列表，如 1,2,3,5,7,10")
                return
            if not vals:
                st.error("至少提供一个保质期。")
                return
            rows = scan_shelf_life(
                material_key=scan_key,
                values=vals,
                base_config=_base_config(int(scan_days)),
                days=int(scan_days),
            )
            st.session_state["scan_rows"] = rows
            st.session_state["scan_label"] = scan_mat_label

        if "scan_rows" in st.session_state:
            sdf = pd.DataFrame(st.session_state["scan_rows"])
            st.caption(
                f"{st.session_state.get('scan_label', '')} 保质期 → 宏观指标"
            )
            st.dataframe(sdf, use_container_width=True, hide_index=True)
            st.subheader("X = 保质期，Y = 总报废量")
            st.line_chart(sdf.set_index("shelf_life")[["total_waste"]])
            st.subheader("总盈利 / 总报废成本")
            st.line_chart(
                sdf.set_index("shelf_life")[["total_profit", "total_waste_cost"]]
            )


def _render_single_sim_tab() -> None:
    st.caption("单次仿真：调试库存规则与价格配置。")
    with st.sidebar:
        st.header("单次仿真运行")
        st.session_state["sim_days"] = st.slider(
            "模拟天数",
            min_value=5,
            max_value=365,
            value=int(st.session_state["sim_days"]),
            step=1,
        )
        st.session_state["sales_cap_enabled"] = st.checkbox(
            "启用销售上限",
            value=bool(st.session_state["sales_cap_enabled"]),
            help="关闭则当日产量仅受库存限制。",
            key="sim_cap_en",
        )
        st.session_state["sales_cap_per_day"] = st.number_input(
            "每日上限（杯）",
            min_value=1,
            value=int(st.session_state["sales_cap_per_day"]),
            step=10,
            disabled=not st.session_state["sales_cap_enabled"],
            key="sim_cap_n",
        )
        if st.button("打开配置窗口", use_container_width=True, key="sim_cfg"):
            open_settings_dialog()
        run = st.button("运行仿真", type="primary", use_container_width=True, key="sim_run")

        st.divider()
        if st.session_state["sales_cap_enabled"]:
            st.caption(f"销售上限：每日 {st.session_state['sales_cap_per_day']} 杯")
        else:
            st.caption("销售上限：关闭")
        st.markdown("**当前物料**")
        for m in st.session_state["materials"].values():
            st.caption(
                f"{m.display_name}：保质 {m.shelf_life} 天 / "
                f"单价 {m.unit_cost:g} / "
                f"{POLICY_LABELS.get(m.purchase_policy, m.purchase_policy)} "
                f"(点 {m.reorder_point} / 量 {m.order_quantity})"
            )
        st.markdown("**当前配方**")
        for r in st.session_state["recipes"]:
            flag = "开" if r.enabled else "关"
            parts = ", ".join(f"{k}:{v:g}" for k, v in r.ingredients.items())
            st.caption(
                f"[{flag}] {r.name} ¥{r.sell_price:g} ← {parts or '（未设用料）'}"
            )

    if run:
        config = _base_config(st.session_state["sim_days"])
        if not config.materials:
            st.error("请先在配置窗口添加物料。")
            return
        if not any(r.enabled and r.ingredients for r in config.recipes):
            st.error("请至少启用一个含用料的配方。")
            return
        result = Simulation(config).run_result()
        st.session_state["history"] = result.history
        st.session_state["sim_result"] = result
        st.session_state["last_config"] = config

    if "history" not in st.session_state:
        st.info("先点「打开配置窗口」设置物料/配方，再点「运行仿真」。")
        return

    history = st.session_state["history"]
    config: SimConfig = st.session_state.get("last_config") or _base_config(
        st.session_state["sim_days"]
    )
    last = history[-1]
    name_of = {k: m.display_name for k, m in config.materials.items()}
    summary = st.session_state.get("sim_result")
    if summary is None:
        from inventory_abm.metrics import to_simulation_result

        summary = to_simulation_result(history)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("累计产量（杯）", f"{last.produced_total:.0f}")
    m2.metric("累计报废", f"{last.waste_total:.0f}")
    m3.metric("总收入", f"{last.revenue_total:.0f}")
    m4.metric("总盈利", f"{summary.summary['total_profit']:.0f}")
    m5.metric("模拟天数", f"{last.day}")

    st.caption(
        "流水 = 销售额 − 采购支出；盈利 = 销售额 − COGS − 报废成本。"
    )

    money_df = pd.DataFrame(
        {
            "day": [h.day for h in history],
            "每日流水": [h.cash_flow_day for h in history],
            "真实盈利": [h.profit_day for h in history],
            "报废成本": [h.waste_cost_day for h in history],
            "销售额": [h.revenue_day for h in history],
        }
    ).set_index("day")
    st.subheader("每日流水 / 盈利 / 报废成本")
    st.line_chart(money_df[["每日流水", "真实盈利", "报废成本"]])

    recipe_names = list(last.produced_by_recipe.keys())
    day_recipe_cols = {
        name: [float(h.produced_by_recipe_day.get(name, 0.0)) for h in history]
        for name in recipe_names
    }
    prod_day_df = pd.DataFrame(
        {
            "day": [h.day for h in history],
            "当日产量": [float(h.produced_day) for h in history],
            **{f"当日:{k}": v for k, v in day_recipe_cols.items()},
        }
    )
    if config.sales_cap_enabled:
        cap = max(1, int(config.sales_cap_per_day))
        prod_day_df["销售上限"] = cap
        prod_day_df["触顶"] = prod_day_df["当日产量"] >= cap

    st.subheader("每日产量")
    chart_day_cols = ["当日产量"] + [f"当日:{k}" for k in recipe_names]
    st.line_chart(prod_day_df.set_index("day")[chart_day_cols])

    chart_a, chart_b = st.columns(2)
    with chart_a:
        if last.produced_by_recipe:
            st.subheader("分配方累计产量")
            st.bar_chart(pd.Series(last.produced_by_recipe, name="杯数"))
        st.subheader("累计产量")
        st.line_chart(
            pd.DataFrame(
                {
                    "day": [h.day for h in history],
                    "累计产量": [h.produced_total for h in history],
                }
            ).set_index("day")
        )
    with chart_b:
        waste_named = {
            name_of.get(k, k): v for k, v in last.waste_by_material.items() if v > 0
        }
        st.subheader("分物料累计报废")
        if waste_named:
            st.bar_chart(pd.Series(waste_named, name="报废量"))
        else:
            st.caption("本期无报废。")
        st.subheader("累计报废")
        st.line_chart(
            pd.DataFrame(
                {
                    "day": [h.day for h in history],
                    "累计报废": [h.waste_total for h in history],
                }
            ).set_index("day")
        )

    stock_cols = {
        name_of.get(k, k): [h.stock.get(k, 0.0) for h in history]
        for k in config.material_keys()
    }
    df = pd.DataFrame(
        {
            "day": [h.day for h in history],
            "当日产量": [float(h.produced_day) for h in history],
            "当日采购": [float(h.purchase_day) for h in history],
            "当日报废": [float(h.waste_day) for h in history],
            "累计产量": [h.produced_total for h in history],
            "累计报废": [h.waste_total for h in history],
            **stock_cols,
        }
    ).set_index("day")

    st.subheader("在库库存")
    if stock_cols:
        st.line_chart(df[list(stock_cols.keys())])

    with st.expander("每日明细"):
        st.dataframe(df.reset_index(), use_container_width=True, hide_index=True)


def main() -> None:
    st.set_page_config(page_title="Inventory What-If Lab", layout="wide")
    _ensure_state()

    st.title("Inventory What-If Lab")
    st.caption("一个局部规则发生变化后，整个库存系统会发生什么？")

    tab_exp, tab_sim = st.tabs(["对比实验", "单次仿真"])
    with tab_exp:
        _render_experiment_tab()
    with tab_sim:
        _render_single_sim_tab()


if __name__ == "__main__":
    import subprocess
    import sys
    from pathlib import Path

    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
    except ImportError:
        from streamlit.runtime.scriptrunner_utils.script_run_context import (
            get_script_run_ctx,
        )

    if get_script_run_ctx() is not None:
        main()
    else:
        app = str(Path(__file__).resolve())
        raise SystemExit(
            subprocess.call(
                [sys.executable, "-m", "streamlit", "run", app, *sys.argv[1:]]
            )
        )
