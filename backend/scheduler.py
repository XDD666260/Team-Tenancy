"""
============================================================
定时增量更新调度器 — APScheduler 集成到 FastAPI
============================================================

功能:
  - 应用启动时自动启动后台调度器
  - 默认每天 2:00 和 14:00 执行增量更新
  - 支持通过 API 动态修改调度配置
  - 支持通过环境变量控制开关和 cron 表达式

环境变量:
  SCHEDULER_ENABLED=true       — 是否启用定时调度（默认 true）
  SCHEDULER_CRON=0 2,14 * * *  — cron 表达式（默认每天 2:00 & 14:00）
  SCHEDULER_MAX_PAGES=3        — 增量更新每次抓取页数
============================================================
"""

import os
import sys
import subprocess
import threading
import time
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.base import JobLookupError

from .database import query, execute

# ======================== 配置 ========================

def _env(key, default=""):
    return os.environ.get(key, default) or default

SCHEDULER_ENABLED = _env("SCHEDULER_ENABLED", "true").lower() == "true"
SCHEDULER_CRON = _env("SCHEDULER_CRON", "0 2,14 * * *")
SCHEDULER_MAX_PAGES = int(_env("SCHEDULER_MAX_PAGES", "3"))

# ======================== 调度器实例 ========================

_scheduler: Optional[BackgroundScheduler] = None
_job_lock = threading.Lock()
_last_run_result: dict = {"running": False, "last_run": None, "last_result": None}


def _run_update_job():
    """调度器触发的增量更新任务。"""
    global _last_run_result

    # 防止重复执行
    if _last_run_result.get("running"):
        print("[Scheduler] 上一次更新仍在执行，跳过本次调度")
        return

    _last_run_result["running"] = True
    _last_run_result["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    start = datetime.now()

    print(f"\n{'=' * 60}")
    print(f"[Scheduler] 定时增量更新触发 — {_last_run_result['last_run']}")
    print(f"{'=' * 60}")

    # 记录日志
    try:
        execute(
            """INSERT INTO crawl_log (source, district, page, houses_found, new_added, updated, status, message)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            ("scheduler", "all", 0, 0, 0, 0, "started", f"定时调度触发 (cron: {SCHEDULER_CRON})"),
        )
    except Exception:
        pass

    # 运行增量爬虫
    try:
        base_dir = os.path.join(os.path.dirname(__file__), "..")
        crawler_script = os.path.join(base_dir, "crawler", "update.py")

        result = subprocess.run(
            [sys.executable, crawler_script,
             "--max-pages", str(SCHEDULER_MAX_PAGES),
             "--mark-offline"],
            capture_output=True, text=True, timeout=900,  # 15 分钟超时
            cwd=base_dir,
        )

        output = result.stdout[-3000:] if result.stdout else ""
        error = result.stderr[-500:] if result.stderr else ""

        # 解析统计
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

        success = result.returncode == 0
        elapsed = (datetime.now() - start).total_seconds()

        _last_run_result["last_result"] = {
            "success": success,
            "new_count": new_count,
            "updated_count": updated_count,
            "elapsed_sec": int(elapsed),
            "message": f"调度更新完成 ({int(elapsed)}s)" if success else f"部分失败: {error[:150]}",
        }

        # 更新日志
        execute(
            """INSERT INTO crawl_log (source, district, page, houses_found, new_added, updated, status, message)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            ("scheduler", "all", SCHEDULER_MAX_PAGES, new_count + updated_count,
             new_count, updated_count, "success" if success else "failed",
             _last_run_result["last_result"]["message"]),
        )

        status = "success" if success else "failed"
        print(f"[Scheduler] 完成: {status} | 新增 {new_count} | 更新 {updated_count} | 耗时 {elapsed:.0f}s")

    except subprocess.TimeoutExpired:
        _last_run_result["last_result"] = {
            "success": False, "new_count": 0, "updated_count": 0,
            "message": "调度更新超时（>15分钟）",
        }
        print("[Scheduler] 超时（>15分钟）")
    except Exception as e:
        _last_run_result["last_result"] = {
            "success": False, "new_count": 0, "updated_count": 0,
            "message": f"调度异常: {str(e)[:200]}",
        }
        print(f"[Scheduler] 异常: {e}")
    finally:
        _last_run_result["running"] = False


# ======================== 调度器生命周期 ========================

def start_scheduler():
    """启动后台调度器（FastAPI startup 事件中调用）。"""
    global _scheduler

    if not SCHEDULER_ENABLED:
        print("[Scheduler] 已禁用（SCHEDULER_ENABLED=false）")
        return

    _scheduler = BackgroundScheduler(
        daemon=True,
        job_defaults={
            "misfire_grace_time": 900,   # 错过 15 分钟内仍执行
            "coalesce": True,            # 合并错过的多次触发
        },
    )

    _scheduler.add_job(
        _run_update_job,
        trigger=CronTrigger.from_crontab(SCHEDULER_CRON),
        id="incremental_update",
        name="增量数据更新",
        replace_existing=True,
    )

    _scheduler.start()
    print(f"[Scheduler] 定时调度已启动 | cron: {SCHEDULER_CRON} | max_pages: {SCHEDULER_MAX_PAGES}")
    _print_next_run()


def stop_scheduler():
    """停止调度器（FastAPI shutdown 事件中调用）。"""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        print("[Scheduler] 已停止")


def _print_next_run():
    """打印下次执行时间。"""
    if _scheduler and _scheduler.running:
        job = _scheduler.get_job("incremental_update")
        if job and job.next_run_time:
            print(f"[Scheduler] 下次执行: {job.next_run_time.strftime('%Y-%m-%d %H:%M:%S')}")


# ======================== 对外查询接口 ========================

def get_scheduler_status() -> dict:
    """返回调度器当前状态。"""
    global _scheduler

    if not SCHEDULER_ENABLED:
        return {"enabled": False, "message": "调度器已禁用（SCHEDULER_ENABLED=false）"}

    job_info = None
    next_run = None
    if _scheduler and _scheduler.running:
        job = _scheduler.get_job("incremental_update")
        if job:
            job_info = {
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if job.next_run_time else None,
            }
            next_run = job_info["next_run"]

    # 最近更新日志
    last_log = query(
        """SELECT source, houses_found, new_added, updated, status, message, crawl_time
           FROM crawl_log
           WHERE source = 'scheduler'
           ORDER BY crawl_time DESC LIMIT 5"""
    )

    return {
        "enabled": True,
        "running": _last_run_result.get("running", False),
        "cron": SCHEDULER_CRON,
        "max_pages": SCHEDULER_MAX_PAGES,
        "next_run": next_run,
        "last_run": _last_run_result.get("last_run"),
        "last_result": _last_run_result.get("last_result"),
        "recent_logs": list(last_log),
    }


def trigger_scheduled_job_now():
    """手动触发一次调度任务（供 API 调用）。"""
    if _last_run_result.get("running"):
        return {"ok": False, "message": "调度任务正在执行中"}
    t = threading.Thread(target=_run_update_job, daemon=True)
    t.start()
    return {"ok": True, "message": "调度任务已在后台启动"}
