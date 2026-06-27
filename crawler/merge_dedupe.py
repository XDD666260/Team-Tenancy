# ============================================================
# 数据合并去重 — 合并快速爬虫(量) + 质量爬虫(质) 的产出
#
# 策略：
#   1. 对每个区县，优先使用 anjuke_rich_{name}.csv（全字段）
#      若不存在则回退到 anjuke_fast_{name}.csv（基础字段）
#   2. 跨区县 MD5 指纹去重（同一房源可能出现在相邻区县）
#   3. 输出统一的 all_listings_merged.csv
#
# 用法：
#   python crawler/merge_dedupe.py                    # 全量合并
#   python crawler/merge_dedupe.py --stats            # 仅统计
# ============================================================

import os
import sys
import csv
import glob
import hashlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawler.utils import OUTPUT_DIR, ANJUKE_CSV_KEYS, make_anjuke_fingerprint


def safe_float(val, default=0.0):
    try:
        return float(val) if val else default
    except (ValueError, TypeError):
        return default


def safe_int(val, default=0):
    try:
        return int(float(val)) if val else default
    except (ValueError, TypeError):
        return default


def load_csv(fpath):
    """安全加载CSV"""
    try:
        with open(fpath, 'r', encoding='utf-8-sig') as f:
            return list(csv.DictReader(f))
    except Exception as e:
        print(f'  [WARN] 读取失败 {fpath}: {e}')
        return []


def merge_and_dedupe():
    """主流程：合并 + 去重"""
    print('=' * 60)
    print('数据合并去重')
    print('=' * 60)

    # ---- 1. 按区县择优加载 ----
    all_rows = []
    stats = {'rich': 0, 'fast': 0, 'total_loaded': 0}

    # 收集所有区县名
    districts_seen = set()
    for pattern in ['anjuke_rich_*.csv', 'anjuke_fast_*.csv']:
        for fpath in sorted(glob.glob(os.path.join(OUTPUT_DIR, pattern))):
            fname = os.path.basename(fpath)
            # 提取区县名
            for prefix in ['anjuke_rich_', 'anjuke_fast_']:
                if fname.startswith(prefix):
                    districts_seen.add(fname.replace(prefix, '').replace('.csv', ''))
                    break

    print(f'\n发现 {len(districts_seen)} 个区县')

    for district in sorted(districts_seen):
        rich_path = os.path.join(OUTPUT_DIR, f'anjuke_rich_{district}.csv')
        fast_path = os.path.join(OUTPUT_DIR, f'anjuke_fast_{district}.csv')

        # 优先用 rich（质量版），回退到 fast（基础版）
        if os.path.exists(rich_path):
            rows = load_csv(rich_path)
            source = 'rich'
        elif os.path.exists(fast_path):
            rows = load_csv(fast_path)
            source = 'fast'
        else:
            continue

        if rows:
            all_rows.extend(rows)
            stats[source] += len(rows)
            lng_ok = sum(1 for r in rows if safe_float(r.get('lng', 0)) > 0)
            dec_ok = sum(1 for r in rows if r.get('decoration', ''))
            print(f'  {district}: {len(rows)}条 ({source}), '
                  f'坐标{lng_ok}, 装修{dec_ok}')

    stats['total_loaded'] = len(all_rows)
    print(f'\n加载总计: {len(all_rows)}条 (rich={stats["rich"]}, fast={stats["fast"]})')

    if not all_rows:
        print('无数据可合并')
        return

    # ---- 2. 补充缺失的指纹 ----
    for r in all_rows:
        if not r.get('fingerprint', ''):
            r['fingerprint'] = make_anjuke_fingerprint(r)

    # ---- 3. 指纹去重 ----
    seen_fp = set()
    unique_rows = []
    dup_count = 0

    for r in all_rows:
        fp = r.get('fingerprint', '')
        if fp and fp in seen_fp:
            dup_count += 1
            continue
        if fp:
            seen_fp.add(fp)
        unique_rows.append(r)

    print(f'指纹去重: {dup_count}条重复 → 保留 {len(unique_rows)} 条唯一')

    # ---- 4. 统计 ----
    lng_ok = sum(1 for r in unique_rows if safe_float(r.get('lng', 0)) > 0)
    dec_ok = sum(1 for r in unique_rows if r.get('decoration', ''))
    year_ok = sum(1 for r in unique_rows if safe_int(r.get('build_year', 0)) > 0)

    # 按来源统计
    by_source = {}
    for r in unique_rows:
        src = r.get('source', 'unknown')
        by_source[src] = by_source.get(src, 0) + 1

    # 价格统计
    prices = []
    for r in unique_rows:
        tp = safe_float(r.get('total_price', 0))
        if 3 < tp < 5000:
            prices.append(tp)

    print(f'\n{"=" * 60}')
    print(f'合并结果')
    print(f'{"=" * 60}')
    print(f'  总房源: {len(unique_rows)} 条')
    print(f'  按来源: {by_source}')
    print(f'  有坐标: {lng_ok} ({100*lng_ok/max(len(unique_rows),1):.1f}%)')
    print(f'  有装修: {dec_ok} ({100*dec_ok/max(len(unique_rows),1):.1f}%)')
    print(f'  有年代: {year_ok} ({100*year_ok/max(len(unique_rows),1):.1f}%)')
    if prices:
        print(f'  价格范围: {min(prices):.1f} ~ {max(prices):.1f} 万')
        print(f'  均价: {sum(prices)/len(prices):.1f} 万')

    # ---- 5. 输出 ----
    # 统一字段
    fieldnames = ANJUKE_CSV_KEYS if ANJUKE_CSV_KEYS else list(unique_rows[0].keys())

    output_path = os.path.join(OUTPUT_DIR, 'all_listings_merged.csv')
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(unique_rows)

    print(f'\n输出: {output_path}')

    # 达到5万了吗？
    print(f'\n{"⚠ 注意" if len(unique_rows) < 50000 else "✅ 达标"}: '
          f'{len(unique_rows)} 条 (目标: 50000+)')

    return unique_rows


if __name__ == '__main__':
    merge_and_dedupe()
