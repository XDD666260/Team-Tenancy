"""
============================================================
重庆二手房数据分析模块
- 房价预测模型训练（Random Forest + XGBoost）
- 预测误差指标（MAE, MSE, RMSE, R²）
- 特征重要性排名与可视化
- KMeans 聚类分析
- 结果存入 analysis_results 表
============================================================
"""
import hashlib
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

import joblib
import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")  # 非交互后端，用于服务器端生成图表
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# 设置中文字体
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
warnings.filterwarnings("ignore")

# 路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(BASE_DIR, "..")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
MODEL_DIR = os.path.join(OUTPUT_DIR, "models")
CHART_DIR = os.path.join(OUTPUT_DIR, "charts")
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(CHART_DIR, exist_ok=True)

# 导入数据库模块
sys.path.insert(0, os.path.join(PROJECT_DIR, "backend"))
from database import query, query_one, execute


# ============================================================
# 1. 数据加载与预处理
# ============================================================
def load_data():
    """从数据库加载并预处理数据"""
    print("=" * 60)
    print("[1/7] 加载数据...")
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

    # 数值型特征
    numeric_cols = ["area", "rooms", "halls", "bathrooms", "total_floors", "build_year", "lng", "lat"]
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    df["total_price"] = pd.to_numeric(df["total_price"], errors="coerce")
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")

    # 去除极端异常值
    df = df[
        (df["total_price"] > 5)
        & (df["total_price"] < 3000)
        & (df["unit_price"] > 500)
        & (df["unit_price"] < 100000)
        & (df["area"] >= 15)
        & (df["area"] <= 400)
    ]

    # 处理缺失值
    df["build_year"] = df["build_year"].fillna(2010)
    df["build_year"] = df["build_year"].clip(1980, 2025)
    df["total_floors"] = df["total_floors"].fillna(df["total_floors"].median() if df["total_floors"].notna().any() else 20)
    df["total_floors"] = df["total_floors"].clip(1, 80)
    df["halls"] = df["halls"].fillna(1)
    df["bathrooms"] = df["bathrooms"].fillna(1)

    # 楼层类型编码
    floor_type_map = {"低层": 0, "中层": 1, "高层": 2, "": 1}
    df["floor_type_code"] = df["floor_type"].map(floor_type_map).fillna(1)

    # 装修编码
    deco_map = {"毛坯": 0, "简装": 1, "精装": 2, "豪装": 3, "": 1}
    df["decoration_code"] = df["decoration"].map(deco_map).fillna(1)

    # 朝向编码（简化）
    def encode_orient(o):
        o = str(o)
        if "南" in o:
            return 3
        if "东南" in o or "西南" in o:
            return 2
        if "东" in o or "西" in o:
            return 1
        return 0

    df["orientation_code"] = df["orientation"].apply(encode_orient)

    # 楼层比
    df["floor_ratio"] = 0.5
    df["floor_ratio"] = df["floor_ratio"].fillna(0.5)

    # 房龄
    df["house_age"] = 2026 - df["build_year"]
    df["house_age"] = df["house_age"].clip(0, 50)

    # 户均面积
    total_rooms = df["rooms"] + df["halls"] + df["bathrooms"]
    df["avg_room_area"] = (df["area"] / total_rooms.clip(1, 20)).clip(5, 100)

    # ===== 区县编码（Target Encoding: 用各区县均价做编码） =====
    district_stats = df.groupby("district")["unit_price"].agg(["mean", "count"])
    district_stats = district_stats[district_stats["count"] >= 5]  # 至少5条
    district_mean = district_stats["mean"].to_dict()
    df["district_encoded"] = df["district"].map(district_mean).fillna(
        df["unit_price"].median()
    )

    # ===== 小区编码 =====
    comm_stats = df.groupby("community")["unit_price"].agg(["mean", "count"])
    comm_stats = comm_stats[comm_stats["count"] >= 3]
    comm_mean = comm_stats["mean"].to_dict()
    df["community_encoded"] = df["community"].map(comm_mean).fillna(
        df["district_encoded"]
    )

    print(f"  清洗后: {len(df)} 条")
    print(f"  价格范围: {df['total_price'].min():.0f} ~ {df['total_price'].max():.0f} 万")
    print(f"  均价: {df['unit_price'].mean():.0f} 元/㎡")
    print(f"  区县数: {df['district'].nunique()}")
    print(f"  小区数: {df['community'].nunique()}")

    return df


# ============================================================
# 2. 房价预测模型训练
# ============================================================
def train_prediction_models(df):
    """训练房价预测模型"""
    print("\n" + "=" * 60)
    print("[2/7] 训练房价预测模型...")
    print("=" * 60)

    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.linear_model import LinearRegression
    from sklearn.model_selection import cross_val_score, train_test_split
    from sklearn.preprocessing import StandardScaler

    # 特征列
    feature_cols = [
        "area",
        "rooms",
        "halls",
        "bathrooms",
        "total_floors",
        "house_age",
        "floor_type_code",
        "decoration_code",
        "orientation_code",
        "avg_room_area",
        "district_encoded",
        "community_encoded",
    ]

    X = df[feature_cols].copy()
    y_total = df["total_price"].values  # 总价预测
    y_unit = df["unit_price"].values  # 单价预测

    # 处理可能的无穷值
    X = X.replace([np.inf, -np.inf], np.nan)
    X = X.fillna(X.median())

    # 划分训练/测试集
    X_train, X_test, yt_train, yt_test, yu_train, yu_test = train_test_split(
        X, y_total, y_unit, test_size=0.2, random_state=42
    )

    print(f"  训练集: {len(X_train)} 条, 测试集: {len(X_test)} 条")

    # 标准化
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # 模型列表
    models = {
        "RandomForest_total": RandomForestRegressor(
            n_estimators=200, max_depth=15, min_samples_leaf=5, random_state=42, n_jobs=-1
        ),
        "RandomForest_unit": RandomForestRegressor(
            n_estimators=200, max_depth=15, min_samples_leaf=5, random_state=42, n_jobs=-1
        ),
        "GradientBoosting_total": GradientBoostingRegressor(
            n_estimators=200, max_depth=6, learning_rate=0.1, random_state=42
        ),
        "GradientBoosting_unit": GradientBoostingRegressor(
            n_estimators=200, max_depth=6, learning_rate=0.1, random_state=42
        ),
    }

    results = {}
    trained_models = {}

    for name, model in models.items():
        target_train = yt_train if "total" in name else yu_train
        target_test = yt_test if "total" in name else yu_test

        print(f"\n  训练 {name}...")
        model.fit(X_train_scaled, target_train)
        pred_train = model.predict(X_train_scaled)
        pred_test = model.predict(X_test_scaled)

        # 误差指标
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

        train_mae = mean_absolute_error(target_train, pred_train)
        test_mae = mean_absolute_error(target_test, pred_test)
        train_rmse = np.sqrt(mean_squared_error(target_train, pred_train))
        test_rmse = np.sqrt(mean_squared_error(target_test, pred_test))
        train_r2 = r2_score(target_train, pred_train)
        test_r2 = r2_score(target_test, pred_test)

        # 交叉验证
        cv_scores = cross_val_score(model, X_train_scaled, target_train, cv=5, scoring="r2")
        cv_r2_mean = cv_scores.mean()
        cv_r2_std = cv_scores.std()

        unit_label = "万" if "total" in name else "元/㎡"

        results[name] = {
            "model_type": "RandomForest" if "RandomForest" in name else "GradientBoosting",
            "target": "total_price(万)" if "total" in name else "unit_price(元/㎡)",
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "train_mae": round(float(train_mae), 2),
            "test_mae": round(float(test_mae), 2),
            "train_rmse": round(float(train_rmse), 2),
            "test_rmse": round(float(test_rmse), 2),
            "train_r2": round(float(train_r2), 4),
            "test_r2": round(float(test_r2), 4),
            "cv_r2_mean": round(float(cv_r2_mean), 4),
            "cv_r2_std": round(float(cv_r2_std), 4),
            "features": feature_cols,
            "unit": unit_label,
        }

        print(
            f"    训练集: MAE={train_mae:.2f}{unit_label}, RMSE={train_rmse:.2f}{unit_label}, R²={train_r2:.4f}"
        )
        print(
            f"    测试集: MAE={test_mae:.2f}{unit_label}, RMSE={test_rmse:.2f}{unit_label}, R²={test_r2:.4f}"
        )
        print(f"    5折CV R²: {cv_r2_mean:.4f} ± {cv_r2_std:.4f}")

        trained_models[name] = model

    # 保存模型
    joblib.dump(scaler, os.path.join(MODEL_DIR, "scaler.pkl"))
    joblib.dump(trained_models, os.path.join(MODEL_DIR, "models.pkl"))
    joblib.dump(feature_cols, os.path.join(MODEL_DIR, "feature_cols.pkl"))
    print(f"\n  模型已保存至: {MODEL_DIR}")

    return results, trained_models, feature_cols, scaler, X_train_scaled, X_test_scaled, yt_test, yu_test


# ============================================================
# 3. 特征重要性分析
# ============================================================
def analyze_feature_importance(trained_models, feature_cols):
    """提取并可视化特征重要性"""
    print("\n" + "=" * 60)
    print("[3/7] 特征重要性分析...")
    print("=" * 60)

    importance_results = {}

    for name, model in trained_models.items():
        if hasattr(model, "feature_importances_"):
            importances = model.feature_importances_
            # 特征名中文映射
            feature_names_cn = {
                "area": "面积",
                "rooms": "室",
                "halls": "厅",
                "bathrooms": "卫",
                "total_floors": "总楼层",
                "house_age": "房龄",
                "floor_type_code": "楼层类型",
                "decoration_code": "装修",
                "orientation_code": "朝向",
                "avg_room_area": "户均面积",
                "district_encoded": "区县(均价编码)",
                "community_encoded": "小区(均价编码)",
            }

            ranked = sorted(
                zip(feature_cols, importances), key=lambda x: -x[1]
            )

            importance_results[name] = [
                {
                    "rank": i + 1,
                    "feature": f,
                    "feature_cn": feature_names_cn.get(f, f),
                    "importance": round(float(imp), 6),
                }
                for i, (f, imp) in enumerate(ranked)
            ]

            print(f"\n  {name} 特征重要性 TOP 10:")
            for item in importance_results[name][:10]:
                print(
                    f"    #{item['rank']:2d} {item['feature_cn']:12s} {item['importance']:.6f}"
                )

            # --- 生成特征重要性图 ---
            top_n = min(12, len(ranked))
            top_features = ranked[:top_n]
            top_names = [feature_names_cn.get(f, f) for f, _ in top_features]
            top_imps = [imp for _, imp in top_features]

            fig, ax = plt.subplots(figsize=(10, 6))
            colors = plt.cm.Blues(np.linspace(0.4, 0.9, len(top_names)))
            bars = ax.barh(range(len(top_names)), top_imps, color=colors[::-1])
            ax.set_yticks(range(len(top_names)))
            ax.set_yticklabels(top_names[::-1])
            ax.set_xlabel("Feature Importance")
            target_label = "总价" if "total" in name else "单价"
            ax.set_title(f"房价预测特征重要性排名 ({target_label} | {name.split('_')[0]})", fontsize=14)
            ax.invert_yaxis()
            # 在柱状图上标注数值
            for i, (bar, val) in enumerate(zip(bars, top_imps[::-1])):
                ax.text(bar.get_width() + 0.002, bar.get_y() + bar.get_height()/2,
                        f'{val:.4f}', va='center', fontsize=9)

            plt.tight_layout()
            chart_path = os.path.join(CHART_DIR, f"feature_importance_{name}.png")
            fig.savefig(chart_path, dpi=150, bbox_inches="tight")
            plt.close(fig)
            print(f"    图表已保存: {chart_path}")

    # 合并图：RF和GB的特征重要性对比
    rf_keys = [k for k in importance_results if "RandomForest" in k]
    gb_keys = [k for k in importance_results if "GradientBoosting" in k]

    for rf_key, gb_key in zip(rf_keys, gb_keys):
        rf_imp = {it["feature"]: it["importance"] for it in importance_results[rf_key]}
        gb_imp = {it["feature"]: it["importance"] for it in importance_results[gb_key]}

        feature_names_cn = {
            "area": "面积", "rooms": "室", "halls": "厅", "bathrooms": "卫",
            "total_floors": "总楼层", "house_age": "房龄",
            "floor_type_code": "楼层类型", "decoration_code": "装修",
            "orientation_code": "朝向", "avg_room_area": "户均面积",
            "district_encoded": "区县(均价编码)", "community_encoded": "小区(均价编码)",
        }

        all_features = feature_cols
        fig, ax = plt.subplots(figsize=(12, 7))
        x = np.arange(len(all_features))
        width = 0.35
        rf_vals = [rf_imp.get(f, 0) for f in all_features]
        gb_vals = [gb_imp.get(f, 0) for f in all_features]
        cn_names = [feature_names_cn.get(f, f) for f in all_features]

        bars1 = ax.bar(x - width/2, rf_vals, width, label='Random Forest', color='#2E86AB')
        bars2 = ax.bar(x + width/2, gb_vals, width, label='Gradient Boosting', color='#A23B72')
        ax.set_xticks(x)
        ax.set_xticklabels(cn_names, rotation=45, ha='right')
        ax.set_ylabel("Feature Importance")
        target_label = "总价" if "total" in rf_key else "单价"
        ax.set_title(f"特征重要性对比 ({target_label} | RF vs GB)", fontsize=14)
        ax.legend()

        plt.tight_layout()
        chart_path = os.path.join(CHART_DIR, f"feature_importance_compare_{target_label}.png")
        fig.savefig(chart_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"    对比图已保存: {chart_path}")

    return importance_results


# ============================================================
# 4. 预测效果可视化
# ============================================================
def plot_prediction_results(trained_models, X_test_scaled, yt_test, yu_test):
    """生成预测结果的散点图和残差图"""
    print("\n" + "=" * 60)
    print("[4/7] 预测效果可视化...")
    print("=" * 60)

    charts = []

    for name, model in trained_models.items():
        target_test = yt_test if "total" in name else yu_test
        pred_test = model.predict(X_test_scaled)
        unit_label = "总价 (万)" if "total" in name else "单价 (元/㎡)"

        # --- 实际值 vs 预测值散点图 ---
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        ax = axes[0]
        ax.scatter(target_test, pred_test, alpha=0.3, s=8, c="#2E86AB", edgecolors="none")
        # 对角线（完美预测）
        lims = [min(target_test.min(), pred_test.min()), max(target_test.max(), pred_test.max())]
        ax.plot(lims, lims, "r--", linewidth=1.5, alpha=0.7)
        ax.set_xlabel(f"实际{unit_label}")
        ax.set_ylabel(f"预测{unit_label}")
        ax.set_title(f"实际值 vs 预测值 ({name})", fontsize=12)

        # R²标注
        from sklearn.metrics import r2_score
        r2 = r2_score(target_test, pred_test)
        ax.text(
            0.05, 0.95, f"R² = {r2:.4f}",
            transform=ax.transAxes, fontsize=11, verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
        )

        # --- 残差图 ---
        ax = axes[1]
        residuals = target_test - pred_test
        ax.scatter(pred_test, residuals, alpha=0.3, s=8, c="#A23B72", edgecolors="none")
        ax.axhline(y=0, color="black", linestyle="--", linewidth=1, alpha=0.5)
        ax.set_xlabel(f"预测{unit_label}")
        ax.set_ylabel(f"残差 ({unit_label})")
        ax.set_title(f"残差图 ({name})", fontsize=12)

        # 残差统计
        resid_mean = np.mean(residuals)
        resid_std = np.std(residuals)
        ax.text(
            0.05, 0.95,
            f"均值={resid_mean:.2f}\n标准差={resid_std:.2f}",
            transform=ax.transAxes, fontsize=9, verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="lightblue", alpha=0.5),
        )

        plt.tight_layout()
        chart_path = os.path.join(CHART_DIR, f"prediction_{name}.png")
        fig.savefig(chart_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        charts.append(chart_path)
        print(f"  图表已保存: {chart_path}")

    return charts


# ============================================================
# 5. KMeans 聚类分析
# ============================================================
def run_clustering(df):
    """KMeans 聚类分析"""
    print("\n" + "=" * 60)
    print("[5/7] KMeans 聚类分析...")
    print("=" * 60)

    from sklearn.cluster import KMeans
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler

    feature_cols = [
        "area", "rooms", "halls", "bathrooms", "total_floors",
        "house_age", "floor_type_code", "decoration_code",
        "orientation_code", "avg_room_area",
        "district_encoded", "community_encoded",
        "unit_price", "total_price",
    ]

    X_cluster = df[feature_cols].copy()
    X_cluster = X_cluster.replace([np.inf, -np.inf], np.nan)
    X_cluster = X_cluster.fillna(X_cluster.median())

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_cluster)

    # 肘部法则：确定最佳K值
    print("  计算肘部法则...")
    inertias = []
    K_range = range(1, 11)
    for k in K_range:
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km.fit(X_scaled)
        inertias.append(km.inertia_)

    # 选K=5做最终聚类
    n_clusters = 5
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    df["cluster"] = kmeans.fit_predict(X_scaled)

    # 每个聚类的统计信息
    cluster_stats = []
    for c in range(n_clusters):
        cluster_data = df[df["cluster"] == c]
        stats = {
            "cluster_id": c,
            "count": len(cluster_data),
            "pct": round(100 * len(cluster_data) / len(df), 1),
            "avg_unit_price": round(float(cluster_data["unit_price"].mean()), 0),
            "avg_total_price": round(float(cluster_data["total_price"].mean()), 1),
            "avg_area": round(float(cluster_data["area"].mean()), 1),
            "avg_rooms": round(float(cluster_data["rooms"].mean()), 1),
            "avg_house_age": round(float(cluster_data["house_age"].mean()), 1),
            "top_districts": cluster_data["district"].value_counts().head(3).to_dict(),
            "dominant_decoration": cluster_data["decoration"].value_counts().index[0] if len(cluster_data) > 0 else "",
            "dominant_floor": cluster_data["floor_type"].value_counts().index[0] if len(cluster_data) > 0 else "",
        }
        cluster_stats.append(stats)

        print(f"\n  聚类 {c}: {len(cluster_data)} 条 ({100*len(cluster_data)/len(df):.1f}%)")
        print(f"    均价: {stats['avg_unit_price']:.0f} 元/㎡ | 平均总价: {stats['avg_total_price']:.1f} 万")
        print(f"    平均面积: {stats['avg_area']:.1f}㎡ | 平均户型: {stats['avg_rooms']:.1f}室")
        print(f"    房龄: {stats['avg_house_age']:.1f}年 | 装修: {stats['dominant_decoration']}")
        print(f"    TOP区县: {stats['top_districts']}")

    # ---------- 聚类可视化 ----------

    # 1. 肘部法则图
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(list(K_range), inertias, "bo-", markersize=8)
    ax.set_xlabel("聚类数 K")
    ax.set_ylabel("惯性 (Inertia)")
    ax.set_title("KMeans 肘部法则 — 确定最佳聚类数", fontsize=14)
    ax.grid(True, alpha=0.3)
    ax.axvline(x=n_clusters, color="red", linestyle="--", alpha=0.7, label=f"选择 K={n_clusters}")
    ax.legend()
    plt.tight_layout()
    elbow_path = os.path.join(CHART_DIR, "clustering_elbow.png")
    fig.savefig(elbow_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\n  肘部法则图: {elbow_path}")

    # 2. PCA降维可视化
    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X_scaled)

    fig, ax = plt.subplots(figsize=(12, 8))
    colors = ["#E63946", "#457B9D", "#2A9D8F", "#E9C46A", "#F4A261"]
    for c in range(n_clusters):
        mask = df["cluster"] == c
        ax.scatter(
            X_pca[mask, 0], X_pca[mask, 1],
            c=colors[c], label=f"聚类{c} ({cluster_stats[c]['count']}条)",
            alpha=0.4, s=10,
        )

    # 标注聚类中心
    centers_pca = pca.transform(kmeans.cluster_centers_)
    ax.scatter(centers_pca[:, 0], centers_pca[:, 1],
               c="black", marker="X", s=200, edgecolors="white", linewidth=1.5,
               label="聚类中心")

    ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]:.1%} 方差)")
    ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]:.1%} 方差)")
    ax.set_title("重庆二手房 KMeans 聚类结果 (PCA降维)", fontsize=14)
    ax.legend(loc="upper right", markerscale=2)
    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    cluster_pca_path = os.path.join(CHART_DIR, "clustering_pca.png")
    fig.savefig(cluster_pca_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  PCA图: {cluster_pca_path}")

    # 3. 聚类特征雷达图
    radar_features = ["avg_unit_price", "avg_total_price", "avg_area", "avg_rooms", "avg_house_age"]
    radar_labels = ["单价", "总价", "面积", "户型(室)", "房龄"]

    # 归一化到0-1
    radar_data = []
    for c in range(n_clusters):
        vals = [cluster_stats[c][f] for f in radar_features]
        max_vals = [max(cluster_stats[i][f] for i in range(n_clusters)) for f in radar_features]
        normalized = [v / max_vals[i] if max_vals[i] > 0 else 0 for i, v in enumerate(vals)]
        radar_data.append(normalized)

    angles = np.linspace(0, 2 * np.pi, len(radar_features), endpoint=False).tolist()
    angles += angles[:1]  # 闭合

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    for c in range(n_clusters):
        values = radar_data[c] + radar_data[c][:1]
        ax.fill(angles, values, alpha=0.15, color=colors[c])
        ax.plot(angles, values, "o-", color=colors[c], linewidth=2, markersize=6,
                label=f"聚类{c}")

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(radar_labels, fontsize=10)
    ax.set_title("各聚类特征雷达图", fontsize=14, pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))

    plt.tight_layout()
    radar_path = os.path.join(CHART_DIR, "clustering_radar.png")
    fig.savefig(radar_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  雷达图: {radar_path}")

    # 4. 各聚类区县分布堆叠柱状图
    cluster_district = {}
    for c in range(n_clusters):
        cluster_data = df[df["cluster"] == c]
        top_d = cluster_data["district"].value_counts().head(5)
        cluster_district[c] = top_d.to_dict()

    fig, ax = plt.subplots(figsize=(14, 6))
    all_top_districts = set()
    for d in cluster_district.values():
        all_top_districts.update(d.keys())
    all_top_districts = sorted(all_top_districts)
    x = np.arange(n_clusters)
    width = 0.12
    district_colors = plt.cm.tab10(np.linspace(0, 1, len(all_top_districts)))

    for i, (district, color) in enumerate(zip(all_top_districts, district_colors)):
        vals = [cluster_district[c].get(district, 0) for c in range(n_clusters)]
        ax.bar(x + i * width - width * len(all_top_districts) / 2, vals, width,
               label=district, color=color, alpha=0.85)

    ax.set_xlabel("聚类")
    ax.set_ylabel("房源数量")
    ax.set_title("各聚类区县分布", fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels([f"聚类{c}" for c in range(n_clusters)])
    ax.legend(loc="upper right", fontsize=8, ncol=2)

    plt.tight_layout()
    district_bar_path = os.path.join(CHART_DIR, "clustering_district_distribution.png")
    fig.savefig(district_bar_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  区县分布图: {district_bar_path}")

    clustering_result = {
        "n_clusters": n_clusters,
        "inertia_": float(kmeans.inertia_),
        "silhouette_score": None,  # 下面计算
        "cluster_stats": cluster_stats,
        "charts": {
            "elbow": os.path.basename(elbow_path),
            "pca": os.path.basename(cluster_pca_path),
            "radar": os.path.basename(radar_path),
            "district_distribution": os.path.basename(district_bar_path),
        },
    }

    # 计算轮廓系数
    try:
        from sklearn.metrics import silhouette_score
        sample_size = min(5000, len(X_scaled))
        idx = np.random.choice(len(X_scaled), sample_size, replace=False)
        sil_score = silhouette_score(X_scaled[idx], df["cluster"].values[idx])
        clustering_result["silhouette_score"] = round(float(sil_score), 4)
        print(f"\n  轮廓系数: {sil_score:.4f}")
    except Exception as e:
        print(f"  轮廓系数计算跳过 (样本过大): {e}")

    # 保存聚类模型
    joblib.dump(kmeans, os.path.join(MODEL_DIR, "kmeans.pkl"))
    joblib.dump(scaler, os.path.join(MODEL_DIR, "kmeans_scaler.pkl"))

    return clustering_result


# ============================================================
# 6. 区县价格地图/分布分析
# ============================================================
def analyze_district_distribution(df):
    """区县分析辅助"""
    print("\n" + "=" * 60)
    print("[6/7] 区县分析...")
    print("=" * 60)

    district_stats = (
        df.groupby("district")
        .agg(
            count=("unit_price", "count"),
            avg_unit_price=("unit_price", "mean"),
            avg_total_price=("total_price", "mean"),
            avg_area=("area", "mean"),
        )
        .sort_values("avg_unit_price", ascending=False)
    )

    # 柱状图
    top20 = district_stats.head(20)

    fig, axes = plt.subplots(2, 1, figsize=(14, 10))

    # 单价排名
    ax = axes[0]
    bars = ax.barh(range(len(top20)), top20["avg_unit_price"], color=plt.cm.Reds(np.linspace(0.4, 0.9, len(top20))))
    ax.set_yticks(range(len(top20)))
    ax.set_yticklabels(top20.index)
    ax.set_xlabel("平均单价 (元/㎡)")
    ax.set_title("重庆各区县二手房平均单价排名 TOP20", fontsize=14)
    ax.invert_yaxis()
    for bar, val in zip(bars, top20["avg_unit_price"]):
        ax.text(bar.get_width() + 50, bar.get_y() + bar.get_height()/2, f'{val:.0f}', va='center', fontsize=8)

    # 房源数量
    ax = axes[1]
    top20_by_count = district_stats.sort_values("count", ascending=False).head(20)
    bars = ax.barh(range(len(top20_by_count)), top20_by_count["count"], color=plt.cm.Blues(np.linspace(0.4, 0.9, len(top20_by_count))))
    ax.set_yticks(range(len(top20_by_count)))
    ax.set_yticklabels(top20_by_count.index)
    ax.set_xlabel("房源数量")
    ax.set_title("重庆各区县二手房房源数量 TOP20", fontsize=14)
    ax.invert_yaxis()
    for bar, val in zip(bars, top20_by_count["count"]):
        ax.text(bar.get_width() + 10, bar.get_y() + bar.get_height()/2, f'{int(val)}', va='center', fontsize=8)

    plt.tight_layout()
    chart_path = os.path.join(CHART_DIR, "district_price_ranking.png")
    fig.savefig(chart_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  区县排名图: {chart_path}")

    return {
        "top20_avg_price": top20.to_dict(),
        "chart": os.path.basename(chart_path),
    }


# ============================================================
# 7. 保存结果到数据库
# ============================================================
def save_results_to_db(prediction_results, importance_results, clustering_result, district_result, association_result=None):
    """将分析结果保存到 analysis_results 表"""
    print("\n" + "=" * 60)
    print("[保存] 保存结果到数据库...")
    print("=" * 60)

    # 清理旧结果
    execute("DELETE FROM analysis_results WHERE analysis_type IN ('prediction', 'clustering', 'rules')")
    # 注意：association_rules 类型由 association.py 独立管理，不在此清理

    # 保存预测结果
    execute(
        "INSERT INTO analysis_results (analysis_type, result_data) VALUES (%s, %s)",
        ("prediction", json.dumps({
            "models": prediction_results,
            "feature_importance": importance_results,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "charts": {
                "feature_importance": [
                    f for f in os.listdir(CHART_DIR) if "feature_importance" in f
                ],
                "prediction": [
                    f for f in os.listdir(CHART_DIR) if "prediction_" in f
                ],
                "district": [
                    f for f in os.listdir(CHART_DIR) if "district_" in f
                ],
            },
        }, ensure_ascii=False)),
    )
    print("  [OK] 预测结果已保存")

    # 保存聚类结果
    execute(
        "INSERT INTO analysis_results (analysis_type, result_data) VALUES (%s, %s)",
        ("clustering", json.dumps({
            "clustering": clustering_result,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "charts": clustering_result["charts"],
        }, ensure_ascii=False)),
    )
    print("  [OK] 聚类结果已保存")

    # 保存区县分析 + 关联规则结果
    rules_data = {
        "district_analysis": district_result,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    if association_result:
        # 合并关联规则结果（不覆盖 association.py 已写入的数据，仅追加区县分析）
        rules_data["association"] = {
            "total_rules": len(association_result.get("rules", [])),
            "conclusions": association_result.get("conclusions", ""),
        }
        print("  [OK] 区县分析 + 关联规则摘要已保存")
    else:
        print("  [OK] 区县分析已保存")

    execute(
        "INSERT INTO analysis_results (analysis_type, result_data) VALUES (%s, %s)",
        ("rules", json.dumps(rules_data, ensure_ascii=False)),
    )

    print("  所有分析结果已写入 analysis_results 表")


# ============================================================
# 主流程
# ============================================================
def main():
    start_time = datetime.now()
    print("=" * 60)
    print("重庆二手房数据分析模块")
    print(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. 加载数据
    df = load_data()

    # 2. 训练预测模型
    pred_results, models, feature_cols, scaler, X_train_s, X_test_s, yt_test, yu_test = train_prediction_models(df)

    # 3. 特征重要性
    importance_results = analyze_feature_importance(models, feature_cols)

    # 4. 预测效果图
    pred_charts = plot_prediction_results(models, X_test_s, yt_test, yu_test)

    # 5. 聚类
    clustering_result = run_clustering(df)

    # 6. 区县分析
    district_result = analyze_district_distribution(df)

    # 7. 关联规则挖掘（Apriori）
    print("\n\n")
    try:
        from association import run_association as run_ar
        association_result = run_ar(
            min_support=0.02,
            min_confidence=0.4,
            max_len=4,
            top_n=50,
        )
    except Exception as e:
        print(f"  ⚠️ 关联规则分析异常: {e}")
        import traceback
        traceback.print_exc()
        association_result = None

    # 8. 保存预测+聚类+区县+关联规则结果到数据库（统一写入，避免覆盖）
    save_results_to_db(pred_results, importance_results, clustering_result, district_result, association_result)

    # 完成
    elapsed = (datetime.now() - start_time).total_seconds()
    print("\n" + "=" * 60)
    print(f"分析完成! 总耗时 {elapsed:.1f} 秒")
    print(f"模型文件: {MODEL_DIR}")
    print(f"图表文件: {CHART_DIR}")
    print("=" * 60)

    print("\n📊 交付物清单:")
    print(f"  预测模型: {os.path.join(MODEL_DIR, 'models.pkl')}")
    print(f"  特征重要性图: {CHART_DIR}/feature_importance_*.png")
    print(f"  预测效果图: {CHART_DIR}/prediction_*.png")
    print(f"  聚类结果图: {CHART_DIR}/clustering_*.png")
    print(f"  区县排名图: {CHART_DIR}/district_price_ranking.png")
    print(f"  特征对比图: {CHART_DIR}/feature_importance_compare_*.png")
    print(f"  关联规则图: {CHART_DIR}/association_*.png")
    if association_result:
        print(f"  关联规则: {len(association_result.get('rules', []))} 条")

    return {
        "prediction": pred_results,
        "importance": importance_results,
        "clustering": clustering_result,
        "district": district_result,
        "association": association_result,
        "elapsed": elapsed,
    }


if __name__ == "__main__":
    main()
