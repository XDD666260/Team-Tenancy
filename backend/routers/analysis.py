"""分析结果 API 路由"""
from fastapi import APIRouter
from ..database import query
from ..schemas import APIResponse

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("/prediction")
def get_prediction():
    """房价预测分析结果"""
    results = query("""
        SELECT result_data, create_time
        FROM analysis_results
        WHERE analysis_type = 'prediction'
        ORDER BY create_time DESC
        LIMIT 1
    """)
    if not results:
        return APIResponse(code=404, message="暂无预测分析结果，请先运行分析模块")

    import json
    data = json.loads(results[0]['result_data']) if isinstance(results[0]['result_data'], str) else results[0]['result_data']
    return APIResponse(data=data)


@router.get("/clustering")
def get_clustering():
    """聚类分析结果"""
    results = query("""
        SELECT result_data, create_time
        FROM analysis_results
        WHERE analysis_type = 'clustering'
        ORDER BY create_time DESC
        LIMIT 1
    """)
    if not results:
        return APIResponse(code=404, message="暂无聚类分析结果，请先运行分析模块")

    import json
    data = json.loads(results[0]['result_data']) if isinstance(results[0]['result_data'], str) else results[0]['result_data']
    return APIResponse(data=data)


@router.get("/rules")
def get_rules():
    """关联规则结果"""
    results = query("""
        SELECT result_data, create_time
        FROM analysis_results
        WHERE analysis_type = 'rules'
        ORDER BY create_time DESC
        LIMIT 1
    """)
    if not results:
        return APIResponse(code=404, message="暂无关联规则结果，请先运行分析模块")

    import json
    data = json.loads(results[0]['result_data']) if isinstance(results[0]['result_data'], str) else results[0]['result_data']
    return APIResponse(data=data)


@router.get("/quick-stats")
def get_quick_stats():
    """快速统计摘要（基于现有数据实时计算）"""
    from ..database import query_one, query

    # 基础统计
    base = query_one("""
        SELECT
            COUNT(*) as total,
            ROUND(AVG(unit_price), 0) as avg_unit_price,
            ROUND(AVG(total_price), 1) as avg_total_price,
            ROUND(AVG(area), 1) as avg_area,
            ROUND(AVG(build_year), 0) as avg_build_year
        FROM houses
        WHERE total_price > 0 AND total_price < 5000
    """)

    # 装修分布
    decoration = query("""
        SELECT decoration as name, COUNT(*) as count
        FROM houses WHERE decoration != ''
        GROUP BY decoration ORDER BY count DESC
    """)

    # 楼层分布
    floor = query("""
        SELECT floor_type as name, COUNT(*) as count
        FROM houses WHERE floor_type != ''
        GROUP BY floor_type ORDER BY count DESC
    """)

    return APIResponse(data={
        "total_listings": base['total'] if base else 0,
        "avg_unit_price": int(base['avg_unit_price'] or 0) if base else 0,
        "avg_total_price": float(base['avg_total_price'] or 0) if base else 0,
        "avg_area": float(base['avg_area'] or 0) if base else 0,
        "avg_build_year": int(base['avg_build_year'] or 0) if base else 0,
        "decoration_distribution": list(decoration),
        "floor_distribution": list(floor),
    })
