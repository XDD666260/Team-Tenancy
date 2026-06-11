# 增量更新模块
# 每次爬取后运行此脚本，自动处理：
#   1. 新上架房源 → INSERT
#   2. 价格变动 → UPDATE（保留历史价格记录）
#   3. 已下架/卖出 → 标记 status='probably_sold'

import pymysql
import pandas as pd
import os
import glob
import hashlib
from datetime import datetime

DB_CONFIG = {
    'host': 'localhost', 'user': 'root', 'password': '123456',
    'database': 'secondhouse_cq', 'charset': 'utf8mb4',
}

RAW_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw')


def process_new_csv(filepath):
    """处理新爬取的CSV，与数据库对比后增量更新"""
    source = 'lianjia' if 'lianjia' in os.path.basename(filepath) else 'anjuke'
    district = os.path.basename(filepath).replace('lianjia_','').replace('anjuke_','').replace('.csv','')
    print(f'\n--- {source} {district} ---')

    df = pd.read_csv(filepath, encoding='utf-8-sig')
    if len(df) == 0:
        print('  空文件')
        return 0, 0, 0

    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    new_count, updated_count, skipped = 0, 0, 0

    for _, row in df.iterrows():
        # 生成指纹
        if source == 'lianjia':
            sid = str(row.get('id', ''))
            fingerprint = f"lj_{sid}"
        else:
            key = f"{row.get('community','')}|{row.get('district','')}|{round(float(row.get('area',0) or 0),1)}|{int(row.get('rooms',0) or 0)}"
            fingerprint = f"ajk_{hashlib.md5(key.encode()).hexdigest()[:16]}"

        if not fingerprint or fingerprint in ('lj_', 'ajk_'):
            skipped += 1
            continue

        # 检查是否存在
        cursor.execute("SELECT id, total_price, unit_price, status FROM houses WHERE fingerprint=%s", (fingerprint,))
        existing = cursor.fetchone()

        if not existing:
            # 🆕 新房源
            cursor.execute("""
                INSERT INTO houses
                (title, district, community, address,
                 total_price, unit_price, area, layout, rooms, halls, bathrooms,
                 floor_desc, floor_type, total_floors, orientation, decoration,
                 build_year, lng, lat, followers, source, source_id, fingerprint)
                VALUES (%s,%s,%s,%s,%s, %s,%s,%s,%s,%s,%s, %s,%s,%s,%s,%s, %s,%s,%s,%s,%s,%s,%s)
            """, (
                str(row.get('title',''))[:300], district,
                str(row.get('community',''))[:100],
                str(row.get('address',''))[:300],
                float(row.get('total_price',0) or 0), float(row.get('unit_price',0) or 0),
                float(row.get('area',0) or 0), str(row.get('layout',''))[:20],
                int(row.get('rooms',0) or 0), int(row.get('halls',0) or 0), int(row.get('bathrooms',0) or 0),
                str(row.get('floor_desc',''))[:50], str(row.get('floor_type',''))[:10],
                int(row.get('total_floors',0) or 0), str(row.get('orientation',''))[:20],
                str(row.get('decoration',''))[:20], int(row.get('build_year',0) or 0),
                float(row.get('lng',0) or 0), float(row.get('lat',0) or 0),
                int(row.get('followers',0) or 0), source,
                str(row.get('id', fingerprint)), fingerprint,
            ))
            new_count += 1
        else:
            db_id, old_price, old_unit, old_status = existing
            new_price = float(row.get('total_price', 0) or 0)
            new_unit = float(row.get('unit_price', 0) or 0)

            # 如果是已下架的重新出现
            if old_status != 'on_sale':
                cursor.execute("UPDATE houses SET status='on_sale', last_updated=NOW() WHERE id=%s", (db_id,))
                updated_count += 1
            # 价格变动
            elif abs(new_price - float(old_price or 0)) > 0.1 or abs(new_unit - float(old_unit or 0)) > 1:
                cursor.execute("""
                    UPDATE houses SET total_price=%s, unit_price=%s, last_updated=NOW()
                    WHERE id=%s
                """, (new_price, new_unit, db_id))
                updated_count += 1
            else:
                skipped += 1

    conn.commit()
    cursor.close()
    conn.close()

    print(f'  新增 {new_count} | 更新 {updated_count} | 跳过 {skipped}')
    return new_count, updated_count, skipped


def mark_sold_listings(source, current_ids):
    """将本次爬取中未出现的房源标记为可能已下架"""
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    ids_tuple = tuple(current_ids) if current_ids else ('__none__',)

    # 该数据源+区县中，状态为on_sale但不在本次爬取结果中的 → 标记
    cursor.execute(f"""
        UPDATE houses SET status='probably_sold', last_updated=NOW()
        WHERE source=%s AND status='on_sale' AND source_id NOT IN ({','.join(['%s']*len(current_ids))})
    """, [source] + list(current_ids))

    sold = cursor.rowcount
    conn.commit()
    cursor.close()
    conn.close()
    print(f'  标记 {sold} 条可能已下架房源（{source}）')


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

    cursor.execute("SELECT COUNT(*), ROUND(AVG(total_price),1), ROUND(AVG(unit_price),0) FROM houses WHERE status='on_sale'")
    total, avg_price, avg_unit = cursor.fetchone()
    print(f'\n  在售房源: {total}条 | 平均总价: {avg_price}万 | 平均单价: {avg_unit}元/㎡')

    cursor.close()
    conn.close()


def main():
    print(f'增量更新 - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('='*50)

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

    print(f'\n{"="*50}')
    print(f'本次更新: 新增 {total_new} | 价格变动 {total_updated} | 未变 {total_skip}')
    summary()


if __name__ == '__main__':
    main()
