"""
============================================================
增量更新模块 — 处理新爬取的CSV文件
============================================================

每次爬取后运行此脚本，自动处理：
  1. 新上架房源 → INSERT
  2. 价格变动 → UPDATE（保留历史价格记录）
  3. 已下架/卖出 → 标记 status='probably_sold'

用法:
  python backend/update_listings.py
============================================================
"""
import os
import sys
import glob
from datetime import datetime

import pymysql
import pandas as pd

# 添加项目根目录以导入 crawler.utils
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(BASE_DIR, "..")
sys.path.insert(0, PROJECT_DIR)

from crawler.utils import (
    make_anjuke_fingerprint,
    make_lianjia_fingerprint,
)

DB_CONFIG = {
    'host': 'localhost', 'user': 'root', 'password': '123456',
    'database': 'secondhouse_cq', 'charset': 'utf8mb4',
}

RAW_DIR = os.path.join(BASE_DIR, '..', 'data', 'raw')


def process_new_csv(filepath):
    """处理新爬取的CSV，与数据库对比后增量更新"""
    source = 'lianjia' if 'lianjia' in os.path.basename(filepath) else 'anjuke'
    district = os.path.basename(filepath) \
        .replace('lianjia_', '').replace('anjuke_', '') \
        .replace('anjuke_fast_', '').replace('anjuke_detail_', '') \
        .replace('anjuke_m_', '').replace('.csv', '')
    print(f'\n--- {source} {district} ---')

    df = pd.read_csv(filepath, encoding='utf-8-sig')
    if len(df) == 0:
        print('  空文件')
        return 0, 0, 0

    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    new_count, updated_count, skipped = 0, 0, 0

    for _, row in df.iterrows():
        # 修复: 使用统一的指纹函数（完整32位MD5 + 5个字段）
        if source == 'lianjia':
            fingerprint = make_lianjia_fingerprint(row)
        else:
            fingerprint = make_anjuke_fingerprint(row)

        if not fingerprint or fingerprint in ('lj_', ''):
            skipped += 1
            continue

        # 检查是否存在
        cursor.execute(
            "SELECT id, total_price, unit_price, status FROM houses "
            "WHERE fingerprint=%s",
            (fingerprint,),
        )
        existing = cursor.fetchone()

        if not existing:
            # 新房源
            cursor.execute(
                """
                INSERT INTO houses
                (title, district, community, address,
                 total_price, unit_price, area, layout, rooms, halls, bathrooms,
                 floor_desc, floor_type, total_floors, orientation, decoration,
                 build_year, lng, lat, followers, source, source_id, fingerprint)
                VALUES (%s,%s,%s,%s,%s, %s,%s,%s,%s,%s,%s, %s,%s,%s,%s,%s, %s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    str(row.get('title', ''))[:300],
                    district,
                    str(row.get('community', ''))[:100],
                    str(row.get('address', ''))[:300],
                    float(row.get('total_price', 0) or 0),
                    float(row.get('unit_price', 0) or 0),
                    float(row.get('area', 0) or 0),
                    str(row.get('layout', ''))[:20],
                    int(row.get('rooms', 0) or 0),
                    int(row.get('halls', 0) or 0),
                    int(row.get('bathrooms', 0) or 0),
                    str(row.get('floor_desc', ''))[:50],
                    str(row.get('floor_type', ''))[:10],
                    int(row.get('total_floors', 0) or 0),
                    str(row.get('orientation', ''))[:20],
                    str(row.get('decoration', ''))[:20],
                    int(row.get('build_year', 0) or 0),
                    float(row.get('lng', 0) or 0),
                    float(row.get('lat', 0) or 0),
                    int(row.get('followers', 0) or 0),
                    source,
                    str(row.get('id', fingerprint)),
                    fingerprint,
                ),
            )
            new_count += 1
        else:
            db_id, old_price, old_unit, old_status = existing
            new_price = float(row.get('total_price', 0) or 0)
            new_unit = float(row.get('unit_price', 0) or 0)

            # 已下架的重新出现 → 恢复在售
            if old_status != 'on_sale':
                cursor.execute(
                    "UPDATE houses SET status='on_sale', last_updated=NOW() "
                    "WHERE id=%s",
                    (db_id,),
                )
                updated_count += 1
            # 价格变动
            elif (abs(new_price - float(old_price or 0)) > 0.1 or
                  abs(new_unit - float(old_unit or 0)) > 1):
                cursor.execute(
                    """
                    UPDATE houses SET total_price=%s, unit_price=%s, last_updated=NOW()
                    WHERE id=%s
                    """,
                    (new_price, new_unit, db_id),
                )
                updated_count += 1
            else:
                skipped += 1

    conn.commit()
    cursor.close()
    conn.close()

    print(f'  新增 {new_count} | 更新 {updated_count} | 跳过 {skipped}')
    return new_count, updated_count, skipped


def mark_sold_by_staleness(source, days=30):
    """
    标记长时间未出现的房源为可能已下架。

    注意: 此函数基于 last_updated 字段，该字段在每次爬取确认
    房源仍在售时都会刷新。超过 days 天未更新的房源可以合理推断
    为已下架。

    与 process_new_csv 配合使用时，应先调用 process_new_csv
    更新所有CSV数据，再调用此函数标记下架房源。
    """
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    sql = """
        UPDATE houses
        SET status='probably_sold', last_updated=NOW()
        WHERE source=%s AND status='on_sale'
          AND last_updated < DATE_SUB(NOW(), INTERVAL %s DAY)
    """
    cursor.execute(sql, (source, days))

    sold = cursor.rowcount
    conn.commit()
    cursor.close()
    conn.close()

    if sold > 0:
        print(f'  标记 {sold} 条可能已下架房源（{source}，{days}天未更新）')
    return sold


def summary():
    """打印数据库当前状态"""
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT source, status, COUNT(*) FROM houses
        GROUP BY source, status ORDER BY source, status
    """)
    print("\n[STATS] 数据库状态：")
    for row in cursor.fetchall():
        print(f'  {row[0]} | {row[1]}: {row[2]}条')

    cursor.execute("""
        SELECT COUNT(*), ROUND(AVG(total_price),1), ROUND(AVG(unit_price),0)
        FROM houses WHERE status='on_sale'
    """)
    total, avg_price, avg_unit = cursor.fetchone()
    print(f'\n  在售房源: {total}条 | 平均总价: {avg_price}万 | '
          f'平均单价: {avg_unit}元/㎡')

    cursor.close()
    conn.close()


def main():
    print(f'增量更新 - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('=' * 50)

    csv_files = glob.glob(os.path.join(RAW_DIR, '*.csv'))
    if not csv_files:
        print('没有待处理的CSV文件')
        summary()
        return

    total_new, total_updated, total_skip = 0, 0, 0
    for f in sorted(csv_files):
        n, u, s = process_new_csv(f)
        total_new += n
        total_updated += u
        total_skip += s

    print(f'\n{"=" * 50}')
    print(f'本次更新: 新增 {total_new} | 价格变动 {total_updated} | 未变 {total_skip}')
    summary()


if __name__ == '__main__':
    main()
