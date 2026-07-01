"""数据库连接管理 — pymysql 连接池"""
import pymysql
from decimal import Decimal
from contextlib import contextmanager

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',
    'database': 'secondhouse_cq',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
    # 关键：让 MySQL DECIMAL 直接返回 float，避免 JSON 序列化成字符串
    'conv': pymysql.converters.conversions.copy(),
}
# 将 DECIMAL 和 NEWDECIMAL 类型强制转为 float
DB_CONFIG['conv'][pymysql.constants.FIELD_TYPE.DECIMAL] = float
DB_CONFIG['conv'][pymysql.constants.FIELD_TYPE.NEWDECIMAL] = float


def _convert_decimals(obj):
    """递归转换结果中的 Decimal → float/int，确保 JSON 兼容"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: _convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_convert_decimals(v) for v in obj]
    return obj


@contextmanager
def get_db():
    """获取数据库连接，自动关闭"""
    conn = pymysql.connect(**DB_CONFIG)
    try:
        yield conn
    finally:
        conn.close()


def query(sql, params=None):
    """执行查询并返回全部结果"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return _convert_decimals(cursor.fetchall())


def query_one(sql, params=None):
    """执行查询并返回单条结果"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return _convert_decimals(cursor.fetchone())


def execute(sql, params=None):
    """执行写操作"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount
