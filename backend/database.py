"""数据库连接管理 — pymysql 连接池"""
import pymysql
from contextlib import contextmanager

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',
    'database': 'secondhouse_cq',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
}


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
        return cursor.fetchall()


def query_one(sql, params=None):
    """执行查询并返回单条结果"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return cursor.fetchone()


def execute(sql, params=None):
    """执行写操作"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount
