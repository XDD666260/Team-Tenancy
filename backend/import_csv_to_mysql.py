# 将已有CSV数据导入MySQL，自动去重
# 链家指纹: lj_ + 房源ID
# 安居客指纹: ajk_ + community|district|area|rooms|price（取整到万）
# 跨源匹配: community|district|area(整数)|rooms 相同视为同一套房

import pymysql
import pandas as pd
import os
import glob
import hashlib
import json

DB_CONFIG = {
    'host': 'localhost', 'user': 'root', 'password': '123456',
    'database': 'secondhouse_cq', 'charset': 'utf8mb4',
}

RAW_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw')


def lianjia_fingerprint(row):
    """链家指纹：基于房源ID"""
    sid = str(row.get('id', ''))
    return f"lj_{sid}" if sid else None


def anjuke_fingerprint(row):
    """安居客指纹：community|district|area(1位小数)|rooms"""
    community = str(row.get('community', '')).strip()
    district = str(row.get('district', '')).strip()
    try:
        area = round(float(row.get('area', 0)), 1)
    except:
        area = 0
    try:
        rooms = int(row.get('rooms', 0))
    except:
        rooms = 0
    key = f"{community}|{district}|{area}|{rooms}"
    return f"ajk_{hashlib.md5(key.encode()).hexdigest()[:16]}"


def safe_float(val, default=0):
    try: return float(val) if pd.notna(val) else default
    except: return default


def safe_int(val, default=0):
    try: return int(float(val)) if pd.notna(val) else default
    except: return default


def import_csv(filepath):
    """导入单个CSV到MySQL"""
    source = 'lianjia' if 'lianjia' in os.path.basename(filepath) else 'anjuke'
    district = os.path.basename(filepath).replace('lianjia_','').replace('anjuke_','').replace('.csv','')

    print(f'\n导入 {source} - {district} ...')

    df = pd.read_csv(filepath, encoding='utf-8-sig')
    if len(df) == 0:
        print(f'  空文件，跳过')
        return 0, 0

    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    new_count, skip_count = 0, 0

    for _, row in df.iterrows():
        # 生成指纹
        if source == 'lianjia':
            fingerprint = lianjia_fingerprint(row)
            source_id = str(row.get('id', ''))
        else:
            fingerprint = anjuke_fingerprint(row)
            source_id = fingerprint

        if not fingerprint:
            skip_count += 1
            continue

        # 检查是否已存在
        cursor.execute("SELECT id FROM houses WHERE fingerprint=%s", (fingerprint,))
        if cursor.fetchone():
            skip_count += 1
            continue

        # 插入
        try:
            cursor.execute("""
                INSERT INTO houses
                (title, district, community, address,
                 total_price, unit_price, area, layout, rooms, halls, bathrooms,
                 floor_desc, floor_type, total_floors, orientation, decoration,
                 build_year, lng, lat, followers, source, source_id, fingerprint)
                VALUES (%s,%s,%s,%s,%s, %s,%s,%s,%s,%s,%s, %s,%s,%s,%s,%s, %s,%s,%s,%s,%s,%s,%s)
            """, (
                str(row.get('title', ''))[:300],
                district,
                str(row.get('community', ''))[:100],
                str(row.get('address', ''))[:300],
                safe_float(row.get('total_price')),
                safe_float(row.get('unit_price')),
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
                safe_int(row.get('followers')),
                source,
                source_id,
                fingerprint,
            ))
            new_count += 1
        except Exception as e:
            skip_count += 1
            if skip_count <= 3:
                print(f'  [WARN] 插入失败: {e}')

    conn.commit()
    cursor.close()
    conn.close()

    print(f'  新增 {new_count} 条，跳过 {skip_count} 条（重复/异常）')
    return new_count, skip_count


def main():
    # 先确保数据库和表存在
    os.system(f'python {os.path.join(os.path.dirname(__file__), "setup_database.py")}')

    csv_files = glob.glob(os.path.join(RAW_DIR, '*.csv'))
    if not csv_files:
        print('data/raw/ 下没有CSV文件')
        return

    print(f'找到 {len(csv_files)} 个CSV文件\n{"="*50}')

    total_new, total_skip = 0, 0
    for f in sorted(csv_files):
        n, s = import_csv(f)
        total_new += n
        total_skip += s

    # 跨源去重：标记链家+安居客重复的房源
    print(f'\n{"="*50}')
    print('开始跨源去重...')
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # 同一小区+区县+面积(整数)+户型相同 → 源不同但可能是同一套房
    cursor.execute("""
        SELECT h1.id, h2.id
        FROM houses h1
        JOIN houses h2 ON
            h1.community = h2.community
            AND h1.district = h2.district
            AND FLOOR(h1.area) = FLOOR(h2.area)
            AND h1.rooms = h2.rooms
            AND h1.source != h2.source
            AND h1.id > h2.id
    """)
    marked = cursor.rowcount
    conn.commit()
    print(f'  标记了 {marked} 条跨源重复房源')

    # 统计
    cursor.execute("""
        SELECT source, COUNT(*) as cnt,
               ROUND(AVG(unit_price),0) as avg_price,
               ROUND(AVG(total_price),1) as avg_total
        FROM houses
        GROUP BY source
    """)
    print('\n[STATS] 数据库统计：')
    for row in cursor.fetchall():
        print(f'  {row[0]}: {row[1]}条, 均价{row[2]}元/㎡, 平均总价{row[3]}万')

    cursor.execute("SELECT COUNT(*), COUNT(DISTINCT district) FROM houses")
    total, districts = cursor.fetchone()
    print(f'\n  总计: {total}条, 覆盖 {districts} 个区县')

    cursor.close()
    conn.close()

    print(f'\n[OK] 导入完成！新增 {total_new} 条，跳过 {total_skip} 条重复')


if __name__ == '__main__':
    main()
