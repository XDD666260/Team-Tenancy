"""统计相关 API 路由"""
from fastapi import APIRouter, HTTPException
from ..database import query, query_one
from ..schemas import APIResponse

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/overview")
def get_overview():
    """数据总览 — 首页顶部卡片 + 各区县统计"""
    # 整体统计
    overview = query_one("""
        SELECT
            COUNT(*) as total_houses,
            ROUND(AVG(unit_price), 2) as avg_unit_price,
            ROUND(AVG(total_price), 2) as avg_total_price,
            ROUND(MAX(unit_price), 2) as max_unit_price,
            ROUND(MIN(unit_price), 2) as min_unit_price,
            COUNT(DISTINCT district) as district_count
        FROM houses
        WHERE total_price > 0 AND total_price < 5000
    """)

    if not overview:
        return APIResponse(code=404, message="暂无数据")

    # 最近更新时间
    last_update = query_one("""
        SELECT MAX(last_updated) as update_time FROM houses
    """)

    # 按来源统计
    by_source_rows = query("""
        SELECT source, COUNT(*) as cnt FROM houses GROUP BY source
    """)
    by_source = {r['source']: r['cnt'] for r in by_source_rows}

    # 按区县统计 (TOP 20)
    by_district_rows = query("""
        SELECT district, COUNT(*) as count,
               ROUND(AVG(unit_price), 2) as avg_unit_price,
               ROUND(AVG(total_price), 2) as avg_total_price
        FROM houses WHERE total_price > 0 AND total_price < 5000
        GROUP BY district
        ORDER BY count DESC
        LIMIT 20
    """)

    return APIResponse(data={
        "total_houses": overview['total_houses'],
        "avg_unit_price": float(overview['avg_unit_price'] or 0),
        "avg_total_price": float(overview['avg_total_price'] or 0),
        "max_unit_price": float(overview['max_unit_price'] or 0),
        "min_unit_price": float(overview['min_unit_price'] or 0),
        "district_count": overview['district_count'],
        "update_time": str(last_update['update_time']) if last_update else "",
        "by_source": by_source,
        "by_district": list(by_district_rows),
    })


@router.get("/district/{name}")
def get_district_detail(name: str):
    """某区县详细统计"""
    # 基础统计
    base = query_one("""
        SELECT
            COUNT(*) as house_count,
            ROUND(AVG(unit_price), 2) as avg_unit_price,
            ROUND(AVG(total_price), 2) as avg_total_price,
            ROUND(AVG(area), 2) as avg_area,
            ROUND(MAX(total_price), 2) as max_price,
            ROUND(MIN(total_price), 2) as min_price
        FROM houses
        WHERE district = %s AND total_price > 0 AND total_price < 5000
    """, (name,))

    if not base or base['house_count'] == 0:
        return APIResponse(code=404, message=f"区县 '{name}' 暂无数据")

    # 装修分布
    decoration_dist = query("""
        SELECT decoration as type, COUNT(*) as count
        FROM houses WHERE district = %s AND decoration != ''
        GROUP BY decoration ORDER BY count DESC
    """, (name,))

    # 户型分布
    layout_dist = query("""
        SELECT rooms, COUNT(*) as count
        FROM houses WHERE district = %s AND rooms > 0
        GROUP BY rooms ORDER BY rooms
    """, (name,))

    # 价格分布
    price_dist = query("""
        SELECT
            CASE
                WHEN total_price < 50 THEN '50万以下'
                WHEN total_price < 80 THEN '50-80万'
                WHEN total_price < 120 THEN '80-120万'
                WHEN total_price < 200 THEN '120-200万'
                WHEN total_price < 300 THEN '200-300万'
                ELSE '300万以上'
            END as `range`,
            COUNT(*) as count
        FROM houses WHERE district = %s AND total_price > 0 AND total_price < 5000
        GROUP BY `range`
        ORDER BY MIN(total_price)
    """, (name,))

    # 面积分布
    area_dist = query("""
        SELECT
            CASE
                WHEN area < 60 THEN '60㎡以下'
                WHEN area < 90 THEN '60-90㎡'
                WHEN area < 120 THEN '90-120㎡'
                WHEN area < 150 THEN '120-150㎡'
                ELSE '150㎡以上'
            END as `range`,
            COUNT(*) as count
        FROM houses WHERE district = %s AND area > 0
        GROUP BY `range`
        ORDER BY MIN(area)
    """, (name,))

    # TOP 小区
    top_communities = query("""
        SELECT community as name, COUNT(*) as count,
               ROUND(AVG(unit_price), 0) as avg_price
        FROM houses WHERE district = %s AND community != ''
        GROUP BY community ORDER BY count DESC
        LIMIT 10
    """, (name,))

    return APIResponse(data={
        "district": name,
        "house_count": base['house_count'],
        "avg_unit_price": float(base['avg_unit_price'] or 0),
        "avg_total_price": float(base['avg_total_price'] or 0),
        "avg_area": float(base['avg_area'] or 0),
        "max_price": float(base['max_price'] or 0),
        "min_price": float(base['min_price'] or 0),
        "decoration_distribution": list(decoration_dist),
        "layout_distribution": list(layout_dist),
        "price_distribution": list(price_dist),
        "area_distribution": list(area_dist),
        "top_communities": list(top_communities),
    })


@router.get("/price-distribution")
def get_price_distribution():
    """全市价格区间分布"""
    # 单价格区间
    unit_price_bins = query("""
        SELECT
            CASE
                WHEN unit_price < 5000 THEN '5000以下'
                WHEN unit_price < 8000 THEN '5000-8000'
                WHEN unit_price < 12000 THEN '8000-12000'
                WHEN unit_price < 18000 THEN '12000-18000'
                WHEN unit_price < 25000 THEN '18000-25000'
                ELSE '25000以上'
            END as `range`,
            COUNT(*) as count
        FROM houses WHERE unit_price > 0 AND unit_price < 100000
        GROUP BY `range`
        ORDER BY MIN(unit_price)
    """)

    # 总价区间
    total_price_bins = query("""
        SELECT
            CASE
                WHEN total_price < 50 THEN '50万以下'
                WHEN total_price < 80 THEN '50-80万'
                WHEN total_price < 120 THEN '80-120万'
                WHEN total_price < 200 THEN '120-200万'
                WHEN total_price < 300 THEN '200-300万'
                ELSE '300万以上'
            END as `range`,
            COUNT(*) as count
        FROM houses WHERE total_price > 0 AND total_price < 5000
        GROUP BY `range`
        ORDER BY MIN(total_price)
    """)

    return APIResponse(data={
        "unit_price_bins": list(unit_price_bins),
        "total_price_bins": list(total_price_bins),
    })


@router.get("/layout-distribution")
def get_layout_distribution():
    """户型分布统计"""
    rooms_dist = query("""
        SELECT rooms, COUNT(*) as count
        FROM houses WHERE rooms > 0 AND rooms <= 10
        GROUP BY rooms ORDER BY rooms
    """)

    avg_price_by_rooms = query("""
        SELECT rooms,
               ROUND(AVG(unit_price), 0) as avg_unit_price
        FROM houses WHERE rooms > 0 AND rooms <= 10 AND unit_price > 0
        GROUP BY rooms ORDER BY rooms
    """)

    return APIResponse(data={
        "rooms_distribution": list(rooms_dist),
        "avg_price_by_rooms": list(avg_price_by_rooms),
    })


@router.get("/area-distribution")
def get_area_distribution():
    """面积区间分布"""
    bins = query("""
        SELECT
            CASE
                WHEN area < 60 THEN '60㎡以下'
                WHEN area < 90 THEN '60-90㎡'
                WHEN area < 120 THEN '90-120㎡'
                WHEN area < 150 THEN '120-150㎡'
                ELSE '150㎡以上'
            END as `range`,
            COUNT(*) as count
        FROM houses WHERE area > 0
        GROUP BY `range`
        ORDER BY MIN(area)
    """)

    return APIResponse(data={"bins": list(bins)})
