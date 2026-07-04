"""数据更新 API 路由 — 支持手动触发和定时增量更新"""
import os
import subprocess
import sys
import threading
from datetime import datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Query

from ..database import query, query_one, execute
from ..schemas import APIResponse

router = APIRouter(prefix="/api", tags=["update"])

# 更新状态追踪
_update_status = {
    "running": False,
    "last_run": None,
    "last_result": None,
    "next_scheduled": None,
}


def _run_incremental_update_in_background():
    """在后台线程中运行增量更新爬虫"""
    global _update_status
    _update_status["running"] = True
    _update_status["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        # 获取项目根目录
        base_dir = os.path.join(os.path.dirname(__file__), "..", "..")
        crawler_script = os.path.join(base_dir, "crawler", "update.py")

        # 运行增量爬虫
        result = subprocess.run(
            [sys.executable, crawler_script, "--max-pages", "3", "--mark-offline"],
            capture_output=True,
            text=True,
            timeout=600,  # 10分钟超时
            cwd=base_dir,
        )

        output = result.stdout[-2000:] if result.stdout else ""
        error = result.stderr[-500:] if result.stderr else ""

        # 解析输出中的统计信息
        new_count, updated_count = 0, 0
        for line in output.split("\n"):
            if "新增:" in line:
                try:
                    new_count = int(line.split(":")[1].strip().split()[0])
                except Exception:
                    pass
            if "更新:" in line:
                try:
                    updated_count = int(line.split(":")[1].strip().split()[0])
                except Exception:
                    pass

        _update_status["last_result"] = {
            "success": result.returncode == 0,
            "new_count": new_count,
            "updated_count": updated_count,
            "message": "增量更新完成" if result.returncode == 0 else f"更新部分失败: {error[:200]}",
        }

    except subprocess.TimeoutExpired:
        _update_status["last_result"] = {
            "success": False,
            "new_count": 0,
            "updated_count": 0,
            "message": "更新超时（超过10分钟）",
        }
    except Exception as e:
        _update_status["last_result"] = {
            "success": False,
            "new_count": 0,
            "updated_count": 0,
            "message": f"更新异常: {str(e)[:200]}",
        }
    finally:
        _update_status["running"] = False


@router.post("/update")
def trigger_update(background_tasks: BackgroundTasks):
    """触发增量数据更新（后台执行）"""
    global _update_status

    if _update_status["running"]:
        return APIResponse(
            code=409,
            message="增量更新正在进行中，请等待完成后再触发",
            data={
                "running": True,
                "started_at": _update_status.get("last_run"),
            },
        )

    # 更新前统计
    before = query_one("SELECT COUNT(*) as cnt FROM houses WHERE status='on_sale'")
    total_before = before["cnt"] if before else 0

    # 记录更新日志
    execute(
        """
        INSERT INTO crawl_log (source, district, page, houses_found, new_added, updated, status, message)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """,
        ("api_trigger", "all", 0, 0, 0, 0, "started", "API手动触发增量更新"),
    )

    # 后台执行
    background_tasks.add_task(_run_incremental_update_in_background)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return APIResponse(
        message="增量更新已触发，正在后台执行",
        data={
            "running": True,
            "total_before": total_before,
            "update_time": now,
            "note": "更新完成后可通过 GET /api/update/status 查看结果",
        },
    )


@router.get("/update/status")
def get_update_status():
    """查询增量更新状态"""
    global _update_status

    # 最近一次爬取日志
    last_crawl = query_one(
        """
        SELECT source, district, houses_found, new_added, updated, status, message, crawl_time
        FROM crawl_log
        ORDER BY crawl_time DESC
        LIMIT 1
    """
    )

    # 数据库最新更新时间
    last_db_update = query_one("SELECT MAX(last_updated) as t FROM houses")

    # 最近24小时的新增/更新统计
    recent_stats = query_one(
        """
        SELECT
            SUM(CASE WHEN first_seen >= DATE_SUB(NOW(), INTERVAL 24 HOUR) THEN 1 ELSE 0 END) as new_24h,
            SUM(CASE WHEN last_updated >= DATE_SUB(NOW(), INTERVAL 24 HOUR) AND first_seen < DATE_SUB(NOW(), INTERVAL 24 HOUR) THEN 1 ELSE 0 END) as updated_24h
        FROM houses
    """
    )

    return APIResponse(
        data={
            "running": _update_status["running"],
            "last_run": _update_status.get("last_run"),
            "last_result": _update_status.get("last_result"),
            "last_crawl_log": {
                "source": last_crawl["source"] if last_crawl else None,
                "district": last_crawl["district"] if last_crawl else None,
                "houses_found": last_crawl["houses_found"] if last_crawl else 0,
                "new_added": last_crawl["new_added"] if last_crawl else 0,
                "updated": last_crawl["updated"] if last_crawl else 0,
                "status": last_crawl["status"] if last_crawl else None,
                "message": last_crawl["message"] if last_crawl else None,
                "crawl_time": str(last_crawl["crawl_time"]) if last_crawl else None,
            },
            "last_db_update": str(last_db_update["t"]) if last_db_update and last_db_update["t"] else None,
            "recent_24h": {
                "new": recent_stats["new_24h"] if recent_stats else 0,
                "updated": recent_stats["updated_24h"] if recent_stats else 0,
            },
        }
    )


@router.get("/update/history")
def get_update_history(
    source: str = Query(None, description="数据源筛选"),
    limit: int = Query(20, ge=1, le=100, description="条数"),
):
    """查询数据更新历史日志"""
    conditions = []
    params = []

    if source:
        conditions.append("source = %s")
        params.append(source)

    where = " AND ".join(conditions) if conditions else "1=1"
    rows = query(
        f"""
        SELECT id, source, district, page, houses_found, new_added, updated,
               status, message, crawl_time
        FROM crawl_log
        WHERE {where}
        ORDER BY crawl_time DESC
        LIMIT %s
    """,
        params + [limit],
    )

    return APIResponse(data=list(rows), total=len(rows))


@router.get("/update/schedule")
def get_schedule_info():
    """获取数据更新调度信息"""
    global _update_status

    # 最近30天的每日更新统计
    daily_stats = query(
        """
        SELECT
            DATE(crawl_time) as date,
            SUM(new_added) as total_new,
            SUM(updated) as total_updated,
            COUNT(DISTINCT source) as sources
        FROM crawl_log
        WHERE crawl_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        GROUP BY DATE(crawl_time)
        ORDER BY date DESC
    """
    )

    # 按来源统计
    source_stats = query(
        """
        SELECT source,
               COUNT(*) as total_runs,
               SUM(new_added) as total_new,
               SUM(updated) as total_updated,
               MAX(crawl_time) as last_crawl
        FROM crawl_log
        WHERE crawl_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        GROUP BY source
    """
    )

    return APIResponse(
        data={
            "running": _update_status["running"],
            "last_run": _update_status.get("last_run"),
            "daily_stats": list(daily_stats),
            "source_stats": list(source_stats),
            "recommended_interval": "建议每天执行1-2次增量更新（API触发或系统定时任务）",
            "note": "APScheduler 定时调度已集成，默认每天 2:00 和 14:00 自动执行",
        }
    )


# ── 定时调度器控制接口 ──

@router.get("/update/scheduler")
def get_scheduler_config():
    """查询定时调度器状态和配置"""
    from ..scheduler import get_scheduler_status
    sched = get_scheduler_status()
    return APIResponse(data=sched)


@router.post("/update/scheduler/trigger")
def trigger_scheduler_now():
    """手动触发一次定时调度任务（与 /api/update 独立，不冲突）"""
    from ..scheduler import trigger_scheduled_job_now
    result = trigger_scheduled_job_now()
    return APIResponse(
        code=200 if result["ok"] else 409,
        message=result["message"],
    )
