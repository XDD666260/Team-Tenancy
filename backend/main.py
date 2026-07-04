"""FastAPI 应用入口 — 重庆二手房数据 API"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import stats, houses, analysis, update
from decimal import Decimal
import json


class DecimalEncoder(json.JSONEncoder):
    """自定义 JSON 编码器：将 Decimal 转为 float，避免序列化为字符串"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def jsonable_encoder_with_decimal(obj, **kwargs):
    """替代 fastapi.encoders.jsonable_encoder，确保 Decimal → float"""
    if isinstance(obj, dict):
        return {k: jsonable_encoder_with_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [jsonable_encoder_with_decimal(v) for v in obj]
    elif isinstance(obj, Decimal):
        return float(obj)
    return obj


app = FastAPI(
    title="重庆二手房数据 API",
    description="为 Android App 提供数据查询、统计和分析接口",
    version="1.0.0",
    json_encoders={Decimal: float},  # 关键：告诉 FastAPI 把 Decimal 当 float 处理
)

# CORS — 允许 Android 模拟器和真机跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(stats.router)
app.include_router(houses.router)
app.include_router(analysis.router)
app.include_router(update.router)


@app.get("/")
def root():
    return {
        "service": "重庆二手房数据 API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    """健康检查"""
    from .database import query_one
    try:
        result = query_one("SELECT COUNT(*) as cnt FROM houses")
        from .scheduler import get_scheduler_status
        sched = get_scheduler_status()
        return {
            "status": "ok",
            "database": "connected",
            "total_houses": result['cnt'] if result else 0,
            "scheduler": {
                "enabled": sched["enabled"],
                "next_run": sched.get("next_run"),
            },
        }
    except Exception as e:
        return {
            "status": "error",
            "database": str(e),
        }


# ── 调度器生命周期 ──

@app.on_event("startup")
def startup():
    from .scheduler import start_scheduler
    start_scheduler()


@app.on_event("shutdown")
def shutdown():
    from .scheduler import stop_scheduler
    stop_scheduler()
