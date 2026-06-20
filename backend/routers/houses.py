"""房源列表 API 路由"""
from typing import Optional
from fastapi import APIRouter, Query
from ..database import query, query_one
from ..schemas import APIResponse

router = APIRouter(prefix="/api", tags=["houses"])


@router.get("/houses")
def get_houses(
    district: Optional[str] = Query(None, description="区县"),
    min_price: Optional[float] = Query(None, description="最低总价（万）"),
    max_price: Optional[float] = Query(None, description="最高总价（万）"),
    min_area: Optional[float] = Query(None, description="最小面积（㎡）"),
    max_area: Optional[float] = Query(None, description="最大面积（㎡）"),
    rooms: Optional[int] = Query(None, description="户型-室"),
    floor_type: Optional[str] = Query(None, description="楼层类型"),
    decoration: Optional[str] = Query(None, description="装修"),
    orientation: Optional[str] = Query(None, description="朝向"),
    source: Optional[str] = Query(None, description="数据来源: lianjia/anjuke"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=50, description="每页条数"),
):
    """房源列表 — 多条件筛选 + 分页"""
    conditions = ["total_price > 0 AND total_price < 5000"]
    params = []

    if district:
        conditions.append("district = %s")
        params.append(district)
    if min_price is not None:
        conditions.append("total_price >= %s")
        params.append(min_price)
    if max_price is not None:
        conditions.append("total_price <= %s")
        params.append(max_price)
    if min_area is not None:
        conditions.append("area >= %s")
        params.append(min_area)
    if max_area is not None:
        conditions.append("area <= %s")
        params.append(max_area)
    if rooms is not None:
        conditions.append("rooms = %s")
        params.append(rooms)
    if floor_type:
        conditions.append("floor_type = %s")
        params.append(floor_type)
    if decoration:
        conditions.append("decoration = %s")
        params.append(decoration)
    if orientation:
        conditions.append("orientation LIKE %s")
        params.append(f"%{orientation}%")
    if source:
        conditions.append("source = %s")
        params.append(source)

    where_clause = " AND ".join(conditions)

    # 总数
    count_sql = f"SELECT COUNT(*) as total FROM houses WHERE {where_clause}"
    total_result = query_one(count_sql, params)
    total = total_result['total'] if total_result else 0

    # 分页数据
    offset = (page - 1) * page_size
    data_sql = f"""
        SELECT id, title, district, community, address,
               total_price, unit_price, area, layout,
               rooms, halls, bathrooms,
               floor_desc, floor_type, total_floors,
               orientation, decoration, build_year,
               lng, lat, source
        FROM houses
        WHERE {where_clause}
        ORDER BY id
        LIMIT %s OFFSET %s
    """
    rows = query(data_sql, params + [page_size, offset])

    return APIResponse(data=list(rows), total=total)


@router.get("/houses/{house_id}")
def get_house_detail(house_id: int):
    """单条房源详情"""
    row = query_one("""
        SELECT id, title, district, community, address,
               total_price, unit_price, area, layout,
               rooms, halls, bathrooms,
               floor_desc, floor_type, total_floors,
               orientation, decoration, build_year,
               lng, lat, source
        FROM houses WHERE id = %s
    """, (house_id,))

    if not row:
        return APIResponse(code=404, message="房源不存在")

    return APIResponse(data=row)
