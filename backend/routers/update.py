"""数据更新 API 路由"""
from fastapi import APIRouter
from ..database import query_one, execute
from ..schemas import APIResponse
from datetime import datetime

router = APIRouter(prefix="/api", tags=["update"])


@router.post("/update")
def trigger_update():
    """触发增量数据更新"""
    # 更新前统计
    before = query_one("SELECT COUNT(*) as cnt FROM houses")
    total_before = before['cnt'] if before else 0

    # 记录更新日志
    execute("""
        INSERT INTO crawl_log (source, district, page, houses_found, new_added, updated, status, message)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, ('manual', 'all', 0, 0, 0, 0, 'success', '手动触发增量更新'))

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    return APIResponse(
        message="增量更新已触发（当前为手动模式，需运行爬虫脚本完成实际更新）",
        data={
            "new_count": 0,
            "updated_count": 0,
            "total_before": total_before,
            "total_after": total_before,
            "update_time": now,
            "sources_updated": {
                "lianjia": {"new": 0, "updated": 0},
                "anjuke": {"new": 0, "updated": 0},
            },
            "note": "增量爬虫暂未运行，当前为数据快照模式。后续运行 crawler/update.py 可获取新数据。"
        }
    )
