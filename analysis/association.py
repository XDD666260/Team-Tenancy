"""
============================================================
重庆二手房 — 关联规则挖掘模块 (Apriori)
- 离散化房源特征为事务项
- 挖掘频繁项集 → 关联规则
- 可视化：支持度/置信度/提升度
- 结果存入 analysis_results 表
============================================================
"""
import io
import json
import os
import sys
import warnings
from datetime import datetime

# Fix Windows GBK encoding issue
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
warnings.filterwarnings("ignore")

# 路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(BASE_DIR, "..")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
CHART_DIR = os.path.join(OUTPUT_DIR, "charts")
os.makedirs(CHART_DIR, exist_ok=True)

# 导入数据库模块
sys.path.insert(0, os.path.join(PROJECT_DIR, "backend"))
from database import query, query_one, execute


# ============================================================
# 1. 数据加载 + 离散化
# ============================================================
def load_and_discretize():
    """从数据库加载数据，离散化为事务项"""
    print("=" * 60)
    print("[1/5] 加载数据并离散化...")
    print("=" * 60)

    rows = query("""
        SELECT
            district, community,
            total_price, unit_price, area,
            rooms, halls, bathrooms,
            floor_type, total_floors,
            orientation, decoration, build_year,
            lng, lat, source
        FROM houses
        WHERE total_price > 0 AND total_price < 5000
          AND area > 0 AND area < 500
          AND rooms > 0 AND rooms <= 10
          AND status = 'on_sale'
    """)

    if not rows:
        raise RuntimeError("数据库中没有可用的房源数据！")

    df = pd.DataFrame(rows)
    print(f"  原始数据: {len(df)} 条")

    # 数值型转换
    for c in ["area", "rooms", "halls", "bathrooms", "total_floors",
              "build_year", "total_price", "unit_price"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # ---- 离散化 ----
    transactions = []

    for _, row in df.iterrows():
        items = []

        # --- 区县 ---
        district = str(row.get("district", ""))
        if district and district != "nan":
            items.append(f"区县={district}")

        # --- 单价分档 ---
        up = row["unit_price"]
        if pd.notna(up) and up > 0:
            if up < 5000:
                items.append("单价=5000以下")
            elif up < 8000:
                items.append("单价=5000-8000")
            elif up < 12000:
                items.append("单价=8000-12000")
            elif up < 18000:
                items.append("单价=12000-18000")
            elif up < 25000:
                items.append("单价=18000-25000")
            else:
                items.append("单价=25000以上")

        # --- 总价分档 ---
        tp = row["total_price"]
        if pd.notna(tp) and tp > 0:
            if tp < 50:
                items.append("总价=50万以下")
            elif tp < 80:
                items.append("总价=50-80万")
            elif tp < 120:
                items.append("总价=80-120万")
            elif tp < 200:
                items.append("总价=120-200万")
            elif tp < 300:
                items.append("总价=200-300万")
            else:
                items.append("总价=300万以上")

        # --- 面积分档 ---
        area = row["area"]
        if pd.notna(area) and area > 0:
            if area < 60:
                items.append("面积=60㎡以下")
            elif area < 90:
                items.append("面积=60-90㎡")
            elif area < 120:
                items.append("面积=90-120㎡")
            elif area < 150:
                items.append("面积=120-150㎡")
            else:
                items.append("面积=150㎡以上")

        # --- 户型 ---
        rooms = row["rooms"]
        if pd.notna(rooms) and rooms > 0:
            if rooms == 1:
                items.append("户型=1室")
            elif rooms == 2:
                items.append("户型=2室")
            elif rooms == 3:
                items.append("户型=3室")
            elif rooms == 4:
                items.append("户型=4室")
            else:
                items.append("户型=5室+")

        # --- 装修 ---
        deco = str(row.get("decoration", ""))
        if deco and deco != "nan" and deco != "":
            items.append(f"装修={deco}")

        # --- 楼层类型 ---
        ft = str(row.get("floor_type", ""))
        if ft and ft != "nan" and ft != "":
            items.append(f"楼层={ft}")

        # --- 朝向 ---
        orient = str(row.get("orientation", ""))
        if orient and orient != "nan" and orient != "":
            # 简化为"南向"和"其他"
            if "南" in orient:
                items.append("朝向=南向")
            else:
                items.append("朝向=其他")

        # --- 房龄 ---
        build_year = row["build_year"]
        if pd.notna(build_year) and build_year > 1980:
            house_age = 2026 - int(build_year)
            if house_age < 5:
                items.append("房龄=5年内")
            elif house_age < 10:
                items.append("房龄=5-10年")
            elif house_age < 15:
                items.append("房龄=10-15年")
            elif house_age < 20:
                items.append("房龄=15-20年")
            else:
                items.append("房龄=20年+")

        # --- 数据来源 ---
        source = str(row.get("source", ""))
        if source and source != "nan":
            items.append(f"来源={source}")

        if len(items) >= 3:  # 至少要有3个特征才有分析意义
            transactions.append(items)

    print(f"  生成事务: {len(transactions)} 条")
    print(f"  平均每事务项数: {np.mean([len(t) for t in transactions]):.1f}")

    return transactions


# ============================================================
# 2. Apriori 频繁项集 + 关联规则
# ============================================================
def mine_rules(transactions, min_support=0.03, min_confidence=0.5, max_len=4):
    """
    运行 Apriori 算法挖掘关联规则。

    参数:
        transactions: 事务列表
        min_support: 最小支持度（默认3%）
        min_confidence: 最小置信度（默认50%）
        max_len: 频繁项集最大长度
    """
    print("\n" + "=" * 60)
    print(f"[2/5] Apriori 挖掘关联规则...")
    print(f"      min_support={min_support}, min_confidence={min_confidence}")
    print("=" * 60)

    from mlxtend.frequent_patterns import apriori, association_rules as arule
    from mlxtend.preprocessing import TransactionEncoder

    # 编码事务
    te = TransactionEncoder()
    te_ary = te.fit(transactions).transform(transactions)
    df_encoded = pd.DataFrame(te_ary, columns=te.columns_)

    n_items = len(te.columns_)
    print(f"  编码后特征数: {n_items}")

    # 频繁项集
    print(f"  挖掘频繁项集（min_support={min_support}）...")
    frequent_itemsets = apriori(
        df_encoded,
        min_support=min_support,
        use_colnames=True,
        max_len=max_len,
    )
    frequent_itemsets["length"] = frequent_itemsets["itemsets"].apply(len)
    print(f"  频繁项集: {len(frequent_itemsets)} 个")
    for length in sorted(frequent_itemsets["length"].unique()):
        cnt = len(frequent_itemsets[frequent_itemsets["length"] == length])
        print(f"    长度{length}: {cnt}个")

    if len(frequent_itemsets) < 2:
        print("  ⚠️ 频繁项集太少，尝试降低 min_support...")
        return None, None, frequent_itemsets

    # 关联规则
    print(f"\n  生成关联规则（min_confidence={min_confidence}）...")
    rules = arule(
        frequent_itemsets,
        metric="confidence",
        min_threshold=min_confidence,
    )

    # 数值格式化
    for col in ["antecedent support", "consequent support", "support",
                "confidence", "lift", "leverage", "conviction"]:
        if col in rules.columns:
            rules[col] = rules[col].round(4)

    # 按提升度排序
    rules = rules.sort_values("lift", ascending=False).reset_index(drop=True)

    print(f"  关联规则: {len(rules)} 条")
    if len(rules) > 0:
        print(f"  最高Lift: {rules['lift'].max():.2f}")
        print(f"  最高Confidence: {rules['confidence'].max():.2%}")

    return rules, df_encoded, frequent_itemsets


# ============================================================
# 3. 规则格式化 + 筛选有意义规则
# ============================================================
def format_rules(rules, top_n=50):
    """格式化规则输出，筛选有意义的规则"""
    print("\n" + "=" * 60)
    print("[3/5] 格式化规则...")
    print("=" * 60)

    if rules is None or len(rules) == 0:
        print("  无规则可格式化")
        return []

    def itemset_to_str(itemset):
        return ", ".join(sorted(itemset))

    formatted = []
    for _, r in rules.iterrows():
        antecedents = set(r["antecedents"])
        consequents = set(r["consequents"])

        # 跳过无意义的规则
        # 1. 避免区县→区县
        ant_types = {x.split("=")[0] for x in antecedents}
        con_types = {x.split("=")[0] for x in consequents}
        if ant_types == {"区县"} and con_types == {"区县"}:
            continue
        # 2. 提升度太低 (<0.8, 负相关意义不大)
        if r["lift"] < 0.8:
            continue

        formatted.append({
            "antecedent": itemset_to_str(antecedents),
            "consequent": itemset_to_str(consequents),
            "antecedent_support": float(r["antecedent support"]),
            "consequent_support": float(r["consequent support"]),
            "support": float(r["support"]),
            "confidence": float(r["confidence"]),
            "lift": float(r["lift"]),
            "leverage": float(r.get("leverage", 0)),
            "conviction": float(r.get("conviction", 0)) if pd.notna(r.get("conviction", float("nan"))) else None,
            "ant_types": list(ant_types),
            "con_types": list(con_types),
        })

    # 按Lift排序取TOP
    formatted.sort(key=lambda x: -x["lift"])
    formatted = formatted[:top_n]

    print(f"  筛选后规则: {len(formatted)} 条")
    print(f"\n  {'='*70}")
    print(f"  TOP 15 关联规则:")
    print(f"  {'='*70}")
    for i, rule in enumerate(formatted[:15], 1):
        print(f"  [{i:2d}] {rule['antecedent']}")
        print(f"       => {rule['consequent']}")
        print(f"       支持度={rule['support']:.3f}  置信度={rule['confidence']:.2%}  "
              f"Lift={rule['lift']:.2f}")
        print()

    return formatted


# ============================================================
# 4. 可视化
# ============================================================
def visualize_rules(formatted_rules, rules_df):
    """生成关联规则的可视化图表"""
    print("\n" + "=" * 60)
    print("[4/5] 关联规则可视化...")
    print("=" * 60)

    charts = {}

    if not formatted_rules:
        print("  无规则可可视化")
        return charts

    # ---- 4.1 Lift Top 20 水平柱状图 ----
    top20 = formatted_rules[:20]
    labels = [
        f"{r['antecedent'][:30]} ⇒ {r['consequent'][:20]}"
        for r in top20
    ]
    lifts = [r["lift"] for r in top20]
    confs = [r["confidence"] for r in top20]

    fig, ax = plt.subplots(figsize=(12, 8))
    colors = plt.cm.RdYlGn(np.linspace(0.3, 0.9, len(labels)))
    bars = ax.barh(range(len(labels)), lifts, color=colors[::-1])
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels[::-1], fontsize=7)
    ax.set_xlabel("Lift (提升度)")
    ax.set_title("关联规则 TOP 20 — 按提升度排序", fontsize=14)
    ax.invert_yaxis()

    # 标注
    for bar, lift, conf in zip(bars, lifts[::-1], confs[::-1]):
        ax.text(bar.get_width() + 0.02, bar.get_y() + bar.get_height() / 2,
                f'L={lift:.1f} C={conf:.0%}', va='center', fontsize=7)

    plt.tight_layout()
    chart_path = os.path.join(CHART_DIR, "association_top20_rules.png")
    fig.savefig(chart_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    charts["top20_rules"] = os.path.basename(chart_path)
    print(f"  TOP20规则图: {chart_path}")

    # ---- 4.2 Support-Confidence-Lift 散点图 ----
    top50 = formatted_rules[:min(50, len(formatted_rules))]
    supports = [r["support"] for r in top50]
    confidences = [r["confidence"] for r in top50]
    lifts = [r["lift"] for r in top50]

    fig, ax = plt.subplots(figsize=(10, 7))
    scatter = ax.scatter(supports, confidences, c=lifts, s=80,
                         cmap="RdYlGn", edgecolors="gray", linewidth=0.5,
                         alpha=0.85)
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label("Lift (提升度)", fontsize=10)

    ax.set_xlabel("Support (支持度)", fontsize=12)
    ax.set_ylabel("Confidence (置信度)", fontsize=12)
    ax.set_title("关联规则分布 (气泡=规则, 颜色=Lift)", fontsize=14)
    ax.grid(True, alpha=0.3)

    # 标注TOP5
    for i in range(min(5, len(top50))):
        r = top50[i]
        ax.annotate(
            f"#{i+1}",
            (r["support"], r["confidence"]),
            fontsize=8, fontweight="bold",
            textcoords="offset points", xytext=(8, 5),
            arrowprops=dict(arrowstyle="->", color="gray", lw=0.8),
        )

    plt.tight_layout()
    chart_path = os.path.join(CHART_DIR, "association_scatter.png")
    fig.savefig(chart_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    charts["scatter"] = os.path.basename(chart_path)
    print(f"  散点图: {chart_path}")

    # ---- 4.3 频繁项集支持度 TOP 20 ----
    if rules_df is not None and len(rules_df) > 0:
        freq_df = rules_df.nlargest(20, "support")
        labels = [", ".join(sorted(s)) for s in freq_df["itemsets"]]
        supports_freq = freq_df["support"].values

        fig, ax = plt.subplots(figsize=(10, 7))
        colors = plt.cm.Blues(np.linspace(0.4, 0.9, len(labels)))
        bars = ax.barh(range(len(labels)), supports_freq, color=colors[::-1])
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels[::-1], fontsize=7)
        ax.set_xlabel("Support (支持度)")
        ax.set_title("频繁项集 TOP 20 — 按支持度排序", fontsize=14)
        ax.invert_yaxis()
        for bar, val in zip(bars, supports_freq[::-1]):
            ax.text(bar.get_width() + 0.002, bar.get_y() + bar.get_height() / 2,
                    f'{val:.2%}', va='center', fontsize=8)

        plt.tight_layout()
        chart_path = os.path.join(CHART_DIR, "association_frequent_itemsets.png")
        fig.savefig(chart_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        charts["frequent_itemsets"] = os.path.basename(chart_path)
        print(f"  频繁项集图: {chart_path}")

    # ---- 4.4 按关联维度分组统计 ----
    dimension_lift = {}
    for r in formatted_rules[:50]:
        for at in r["ant_types"]:
            for ct in r["con_types"]:
                dim = f"{at} → {ct}"
                if dim not in dimension_lift:
                    dimension_lift[dim] = []
                dimension_lift[dim].append(r["lift"])

    # 取规则数>=3的维度
    dim_avg = {k: (np.mean(v), len(v)) for k, v in dimension_lift.items() if len(v) >= 3}
    if len(dim_avg) > 1:
        dim_names = sorted(dim_avg.keys(), key=lambda k: -dim_avg[k][0])
        dim_lifts = [dim_avg[k][0] for k in dim_names]
        dim_counts = [dim_avg[k][1] for k in dim_names]

        fig, ax = plt.subplots(figsize=(10, 5))
        bars = ax.bar(range(len(dim_names)), dim_lifts, color=plt.cm.Set2(np.linspace(0, 1, len(dim_names))))
        ax.set_xticks(range(len(dim_names)))
        ax.set_xticklabels(dim_names, fontsize=9)
        ax.set_ylabel("平均Lift")
        ax.set_title("关联维度平均提升度对比", fontsize=14)
        ax.grid(True, alpha=0.3, axis="y")

        for bar, lift, cnt in zip(bars, dim_lifts, dim_counts):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                    f'L={lift:.1f}\n({cnt}条)', ha='center', fontsize=8)

        plt.tight_layout()
        chart_path = os.path.join(CHART_DIR, "association_dimension_lift.png")
        fig.savefig(chart_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        charts["dimension_lift"] = os.path.basename(chart_path)
        print(f"  维度对比图: {chart_path}")

    return charts


# ============================================================
# 5. 保存到数据库
# ============================================================
def save_to_db(formatted_rules, charts, params):
    """保存关联规则结果到 analysis_results 表"""
    print("\n" + "=" * 60)
    print("[5/5] 保存结果到数据库...")
    print("=" * 60)

    result = {
        "rules": formatted_rules,
        "total_rules": len(formatted_rules),
        "parameters": params,
        "charts": charts,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # 删除旧的关联规则结果（只删自己的类型，不影响其他）
    execute("DELETE FROM analysis_results WHERE analysis_type = 'association_rules'")

    execute(
        "INSERT INTO analysis_results (analysis_type, result_data) VALUES (%s, %s)",
        ("association_rules", json.dumps(result, ensure_ascii=False)),
    )
    print(f"  [OK] {len(formatted_rules)} 条关联规则已写入数据库 (type=association_rules)")

    return result


# ============================================================
# 6. 生成分析结论文本
# ============================================================
def generate_conclusions(formatted_rules, n_transactions=0):
    """基于挖掘结果生成可读的分析结论"""
    print("\n" + "=" * 60)
    print("  生成分析结论...")
    print("=" * 60)

    conclusions = []
    conclusions.append("## 重庆二手房关联规则分析结论\n")

    if not formatted_rules:
        conclusions.append("  未挖掘到满足条件的关联规则，可能需要调整参数。")
        return "\n".join(conclusions)

    # 按维度分组抽取关键发现
    top10 = formatted_rules[:10]

    conclusions.append("### 核心发现\n")

    for i, rule in enumerate(top10[:5], 1):
        conclusions.append(
            f"{i}. **{rule['antecedent']}** → **{rule['consequent']}**"
        )
        conclusions.append(
            f"   - 支持度={rule['support']:.1%}，置信度={rule['confidence']:.0%}，"
            f"提升度={rule['lift']:.2f}"
        )
        if rule["lift"] > 2:
            conclusions.append(f"   - 🔴 强关联（Lift={rule['lift']:.1f} > 2）")
        elif rule["lift"] > 1.2:
            conclusions.append(f"   - 🟡 中等关联（Lift={rule['lift']:.1f}）")

    # 统计维度分布
    conclusions.append("\n### 维度关联总结\n")
    dim_map = {}
    for r in formatted_rules:
        for at in r["ant_types"]:
            for ct in r["con_types"]:
                key = f"{at} → {ct}"
                if key not in dim_map:
                    dim_map[key] = 0
                dim_map[key] += 1

    for dim, cnt in sorted(dim_map.items(), key=lambda x: -x[1]):
        conclusions.append(f"- {dim}: {cnt} 条规则")

    conclusions.append(f"\n### 分析方法说明\n")
    conclusions.append(f"- 算法: Apriori (mlxtend)")
    conclusions.append(f"- 数据量: {n_transactions}条在售二手房")
    conclusions.append(f"- 筛选条件: Lift > 0.8, 排除纯区县对区县规则")
    conclusions.append(f"- 有效规则数: {len(formatted_rules)} 条")

    conclusion_text = "\n".join(conclusions)
    print(conclusion_text)

    return conclusion_text


# ============================================================
# 主入口
# ============================================================
def run_association(
    min_support=0.03,
    min_confidence=0.5,
    max_len=4,
    top_n=50,
):
    """
    运行完整的关联规则分析流程。

    参数:
        min_support:  最小支持度（0-1之间，默认0.03=3%）
        min_confidence: 最小置信度（0-1之间，默认0.5=50%）
        max_len:       频繁项集最大长度
        top_n:         输出的TOP规则数
    """
    start_time = datetime.now()
    print("\n" + "=" * 60)
    print("重庆二手房 — 关联规则挖掘 (Apriori)")
    print(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"参数: support≥{min_support}, confidence≥{min_confidence}, "
          f"max_len={max_len}")
    print("=" * 60)

    # 1. 加载 + 离散化
    transactions = load_and_discretize()

    # 2. 挖掘规则
    rules_df, encoded_df, freq_itemsets = mine_rules(
        transactions,
        min_support=min_support,
        min_confidence=min_confidence,
        max_len=max_len,
    )

    # 3. 格式化
    formatted = format_rules(rules_df, top_n=top_n)

    # 4. 可视化
    charts = visualize_rules(formatted, freq_itemsets)

    # 5. 保存到数据库
    params = {
        "min_support": min_support,
        "min_confidence": min_confidence,
        "max_len": max_len,
        "n_transactions": len(transactions),
        "n_rules": len(formatted),
    }
    result = save_to_db(formatted, charts, params)

    # 6. 生成结论
    conclusions = generate_conclusions(formatted, len(transactions))

    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\n{'=' * 60}")
    print(f"关联规则分析完成! 耗时 {elapsed:.1f} 秒")
    print(f"图表文件: {CHART_DIR}")
    print(f"规则数量: {len(formatted)}")
    print(f"{'=' * 60}")

    print("\n📊 交付物清单:")
    print(f"  关联规则数据: analysis_results 表 (type='rules')")
    for name, fname in charts.items():
        print(f"  {name}: {CHART_DIR}/{fname}")

    return {
        "rules": formatted,
        "conclusions": conclusions,
        "charts": charts,
        "elapsed": elapsed,
    }


def main():
    """命令行直接运行"""
    # 先用较宽松的参数，如果规则太少则自动放宽
    result = run_association(
        min_support=0.02,    # 2%支持度 → 约340条
        min_confidence=0.4,  # 40%置信度
        max_len=4,
        top_n=50,
    )

    # 如果规则太少，再放宽参数
    if result["rules"] is None or len(result["rules"]) < 10:
        print("\n⚠️ 规则太少，自动放宽参数重试...")
        result = run_association(
            min_support=0.01,    # 1%
            min_confidence=0.3,  # 30%
            max_len=3,
            top_n=50,
        )

    return result


if __name__ == "__main__":
    main()
