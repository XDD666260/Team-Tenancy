# ============================================================
# CSV 导入 MySQL — 读取清洗后的 houses_clean.csv，导入 houses 表
# ============================================================

import pymysql
import pandas as pd
import os
import sys

DB_CONFIG = {
    'host': 'localhost', 'user': 'root', 'password': '123456',
    'database': 'secondhouse_cq', 'charset': 'utf8mb4',
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLEAN_CSV = os.path.join(BASE_DIR, '..', 'data', 'processed', 'houses_clean.csv')


def safe_float(val, default=0):
    try: return float(val) if pd.notna(val) and val != '' else default
    except: return default


def safe_int(val, default=0):
    try: return int(float(val)) if pd.notna(val) and val != '' else default
    except: return default


def import_clean_csv():
    """导入清洗后的数据到 MySQL"""
    if not os.path.exists(CLEAN_CSV):
        print(f'[ERROR] 清洗后的文件不存在: {CLEAN_CSV}')
        print('请先运行: python backend/data_cleaner.py')
        return

    # 先确保表存在
    from setup_database import create_database, create_tables
    create_database()
    create_tables()

    print(f'\n读取 {CLEAN_CSV} ...')
    df = pd.read_csv(CLEAN_CSV, encoding='utf-8-sig')
    print(f'共 {len(df)} 条记录')

    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # 清空旧数据
    cursor.execute("DELETE FROM houses")
    print('[OK] 已清空旧数据')

    new_count, skip_count = 0, 0
    batch = []
    batch_size = 500

    for _, row in df.iterrows():
        fingerprint = str(row.get('fingerprint', ''))
        if not fingerprint:
            skip_count += 1
            continue

        total_price = safe_float(row.get('total_price'))
        unit_price = safe_float(row.get('unit_price'))

        # 跳过价格明显异常的数据
        if total_price <= 0 or total_price > 5000:
            skip_count += 1
            continue

        batch.append((
            str(row.get('title', ''))[:300],
            str(row.get('district', ''))[:50],
            str(row.get('community', ''))[:100],
            str(row.get('address', ''))[:300],
            total_price,
            unit_price,
            safe_float(row.get('area')),
            str(row.get('layout', ''))[:20],
            safe_int(row.get('rooms')),
            safe_int(row.get('halls')),
            safe_int(row.get('bathrooms')),
            str(row.get('floor_desc', ''))[:50],
            str(row.get('floor_type', ''))[:10],
            safe_int(row.get('total_floors')),
            str(row.get('orientation', ''))[:20],
            str(row.get('decoration', ''))[:20],
            safe_int(row.get('build_year')),
            safe_float(row.get('lng')),
            safe_float(row.get('lat')),
            0,  # followers
            str(row.get('source', ''))[:20],
            str(row.get('source_id', ''))[:100],
            fingerprint,
        ))

        if len(batch) >= batch_size:
            try:
                cursor.executemany("""
                    INSERT IGNORE INTO houses
                    (title, district, community, address,
                     total_price, unit_price, area, layout, rooms, halls, bathrooms,
                     floor_desc, floor_type, total_floors, orientation, decoration,
                     build_year, lng, lat, followers, source, source_id, fingerprint)
                    VALUES (%s,%s,%s,%s,%s, %s,%s,%s,%s,%s,%s, %s,%s,%s,%s,%s, %s,%s,%s,%s,%s,%s,%s)
                """, batch)
            except Exception as e:
                # 批量失败时逐条插入
                for item in batch:
                    try:
                        cursor.execute("""
                            INSERT IGNORE INTO houses
                            (title, district, community, address,
                             total_price, unit_price, area, layout, rooms, halls, bathrooms,
                             floor_desc, floor_type, total_floors, orientation, decoration,
                             build_year, lng, lat, followers, source, source_id, fingerprint)
                            VALUES (%s,%s,%s,%s,%s, %s,%s,%s,%s,%s,%s, %s,%s,%s,%s,%s, %s,%s,%s,%s,%s,%s,%s)
                        """, item)
                    except Exception:
                        pass
            conn.commit()
            new_count += len(batch)
            print(f'  已导入 {new_count}/{len(df)} ...')
            batch = []

    # 剩余批次
    if batch:
        try:
            cursor.executemany("""
                INSERT IGNORE INTO houses
                (title, district, community, address,
                 total_price, unit_price, area, layout, rooms, halls, bathrooms,
                 floor_desc, floor_type, total_floors, orientation, decoration,
                 build_year, lng, lat, followers, source, source_id, fingerprint)
                VALUES (%s,%s,%s,%s,%s, %s,%s,%s,%s,%s,%s, %s,%s,%s,%s,%s, %s,%s,%s,%s,%s,%s,%s)
            """, batch)
        except Exception:
            for item in batch:
                try:
                    cursor.execute("""
                        INSERT IGNORE INTO houses
                        (title, district, community, address,
                         total_price, unit_price, area, layout, rooms, halls, bathrooms,
                         floor_desc, floor_type, total_floors, orientation, decoration,
                         build_year, lng, lat, followers, source, source_id, fingerprint)
                        VALUES (%s,%s,%s,%s,%s, %s,%s,%s,%s,%s,%s, %s,%s,%s,%s,%s, %s,%s,%s,%s,%s,%s,%s)
                    """, item)
                except Exception:
                    pass
        conn.commit()
        new_count += len(batch)

    cursor.close()
    conn.close()

    print(f'\n[OK] 导入完成! 新增 {new_count} 条, 跳过 {skip_count} 条')

    # 统计
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT source, COUNT(*) as cnt,
               ROUND(AVG(unit_price),0) as avg_price,
               ROUND(AVG(total_price),1) as avg_total
        FROM houses GROUP BY source
    """)
    print('\n[STATS] 数据库统计：')
    for row in cursor.fetchall():
        print(f'  {row[0]}: {row[1]}条, 均价{row[2]}元/㎡, 平均总价{row[3]}万')

    cursor.execute("SELECT COUNT(*), COUNT(DISTINCT district) FROM houses")
    total, districts = cursor.fetchone()
    cursor.execute("SELECT COUNT(*) FROM houses WHERE lng > 0")
    lng_count = cursor.fetchone()[0]
    print(f'\n  总计: {total}条, 覆盖 {districts} 个区县, 有坐标: {lng_count}条')

    cursor.close()
    conn.close()


if __name__ == '__main__':
    import_clean_csv()
