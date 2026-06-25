# ============================================================
# 数据清洗器 — 读取所有CSV → 统一字段 → 修复价格 → 去重 → 输出
# ============================================================

import csv, re, os, glob, hashlib, json
from collections import defaultdict

RAW_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw')
OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'processed')
os.makedirs(OUT_DIR, exist_ok=True)

# 标准输出字段
STD_FIELDS = [
    'title', 'total_price', 'unit_price', 'community', 'district', 'address',
    'lng', 'lat', 'layout', 'rooms', 'halls', 'bathrooms', 'area', 'orientation',
    'decoration', 'floor_desc', 'floor_type', 'total_floors', 'build_year',
    'tags', 'source', 'fingerprint', 'source_id'
]

# 字段别名映射（将各种列名统一到标准名）
FIELD_ALIASES = {
    'id': 'source_id',
    'followers': '_followers',  # 暂不导入，但保留
}


def safe_float(val, default=0.0):
    try: return float(val) if val else default
    except: return default


def safe_int(val, default=0):
    try: return int(float(val)) if val else default
    except: return default


def make_cross_file_key(row, source):
    """
    生成跨文件去重key（用于判断是否同一条房源）。
    基于 title+community+district，这三个组合基本唯一。
    title 取前80字符作为近似匹配。
    """
    title = str(row.get('title', '')).strip()[:80]
    community = str(row.get('community', '')).strip()
    district = str(row.get('district', '')).strip()
    source_id = str(row.get('source_id', '')).strip()
    return f"{title}|{community}|{district}|{source}"


def make_fingerprint(row, source):
    """
    生成DB存储用指纹。
    包含足够多的字段以保证唯一性。
    """
    if source == 'lianjia':
        sid = str(row.get('source_id', '')).strip()
        if sid:
            return f"lj_{sid}"
        # fallback
    # 包含 title 的一部分 + community + district + area + rooms + total_price
    title = str(row.get('title', '')).strip()[:60]
    community = str(row.get('community', '')).strip()
    district = str(row.get('district', '')).strip()
    area = safe_float(row.get('area', 0))
    rooms = safe_int(row.get('rooms', 0))
    tp = safe_float(row.get('total_price', 0))
    key = f"{title}|{community}|{district}|{area:.1f}|{rooms}|{tp:.1f}"
    return f"ajk_{hashlib.md5(key.encode()).hexdigest()[:16]}"


def fix_price(row):
    """
    修复安居客价格损坏问题。
    损坏特征：total_price > 1000（应为 < 500 万）
    安居客 raw total_price 有不同单位：
      - 8位数 (>=10M)：price_in_wan * 100000 → 除以100000
      - 6-7位数 (100K-9.9M)：price_in_wan * 10000 → 除以10000
    策略1：从标题提取"XXX万"
    策略2：按数值位数自适应选择除数
    修复后重算 unit_price
    """
    tp = safe_float(row.get('total_price', 0))
    area = safe_float(row.get('area', 0))

    if tp <= 0:
        return row  # 无效数据，不修复

    if tp <= 1000:
        # 价格正常，但仍需验证 unit_price
        if area > 0:
            expected_up = round(tp * 10000 / area, 2)
            current_up = safe_float(row.get('unit_price', 0))
            # 如果 unit_price 明显不合理（与预期差10倍以上），重算
            if current_up > 0 and (current_up > expected_up * 5 or current_up < expected_up / 5):
                row['unit_price'] = str(expected_up)
        return row

    # --- 价格损坏，需要修复 ---
    title = str(row.get('title', ''))

    # 策略1：从标题提取价格（多种模式）
    # 模式: "XXX万", "XXX 万", "XXXW", "XXXw"
    pm = re.search(r'(\d+\.?\d*)\s*[万Ww]', title)
    if pm:
        corrected_tp = float(pm.group(1))
        # 验证合理性：标题提取价应在合理范围（3-3000万）
        if 3 <= corrected_tp <= 3000:
            row['total_price'] = str(round(corrected_tp, 2))
            if area > 0:
                row['unit_price'] = str(round(corrected_tp * 10000 / area, 2))
            return row

    # 策略2：按数值位数自适应除数
    # >= 10,000,000 (8位数) → ÷100000
    # 1,000 ~ 9,999,999 (4-7位数) → ÷10000
    if tp >= 10000000:
        corrected_tp = round(tp / 100000, 4)
    else:
        corrected_tp = round(tp / 10000, 4)

    # 最终验证：修正后的价格是否在合理范围
    if corrected_tp <= 0 or corrected_tp > 5000:
        # 极端情况回退：尝试另一种除数
        if tp >= 10000000:
            corrected_tp = round(tp / 10000, 4)
        else:
            corrected_tp = round(tp / 100000, 4)

    row['total_price'] = str(corrected_tp)
    if area > 0:
        row['unit_price'] = str(round(corrected_tp * 10000 / area, 2))
    return row


def normalize_row(row, source, district_from_filename):
    """将一行数据标准化到 STD_FIELDS"""
    out = {}
    for f in STD_FIELDS:
        out[f] = ''

    # 映射现有字段
    for k, v in row.items():
        k_clean = k.strip().lstrip('﻿')  # BOM
        if k_clean in FIELD_ALIASES:
            alias = FIELD_ALIASES[k_clean]
            if not alias.startswith('_'):
                out[alias] = str(v).strip()
        elif k_clean in STD_FIELDS:
            out[k_clean] = str(v).strip()

    # 设置来源和区县
    out['source'] = source
    if not out['district']:
        out['district'] = district_from_filename

    # 生成 source_id（如果没有）
    if not out['source_id']:
        out['source_id'] = make_fingerprint(out, source) or ''

    # 生成指纹
    fp = make_fingerprint(out, source)
    out['fingerprint'] = fp or ''

    return out


def read_csv_safe(filepath):
    """安全读取CSV，处理编码和BOM"""
    with open(filepath, 'r', encoding='utf-8-sig', errors='replace') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return rows


def classify_files():
    """分类 data/raw/ 下的所有CSV文件"""
    all_files = sorted(glob.glob(os.path.join(RAW_DIR, '*.csv')))

    anjuke_m = []    # anjuke_m_*.csv 主数据源
    anjuke_other = [] # anjuke_*.csv (非 m_)
    lianjia = []     # lianjia_*.csv
    merged = []      # all_listings_merged.csv, anjuke_all.csv

    for f in all_files:
        basename = os.path.basename(f)
        if 'anjuke_m_' in basename:
            anjuke_m.append(f)
        elif 'lianjia_' in basename:
            lianjia.append(f)
        elif 'all_listings_merged' in basename or 'anjuke_all' in basename:
            merged.append(f)
        elif 'anjuke_' in basename:
            anjuke_other.append(f)

    return anjuke_m, anjuke_other, lianjia, merged


def extract_district(filename):
    """从文件名提取区县名"""
    basename = os.path.basename(filename)
    for prefix in ['anjuke_m_', 'anjuke_fast_', 'anjuke_', 'lianjia_']:
        if prefix in basename:
            return basename.replace(prefix, '').replace('.csv', '')
    return basename.replace('.csv', '')


def clean_all():
    """主流程：读取、清洗、去重、输出"""
    print('=' * 60)
    print('数据清洗开始')
    print('=' * 60)

    anjuke_m, anjuke_other, lianjia, merged = classify_files()
    print(f'\n文件分类:')
    print(f'  安居客主数据(anjuke_m_): {len(anjuke_m)} 个')
    print(f'  安居客其它(anjuke_): {len(anjuke_other)} 个')
    print(f'  链家(lianjia_): {len(lianjia)} 个')
    print(f'  合并文件: {len(merged)} 个')

    all_rows = []
    seen_keys = set()  # 跨文件去重 key 集合
    stats = {
        'total_read': 0,
        'price_fixed': 0,
        'cross_file_dup': 0,
        'intra_file_dup_title': 0,
        'final_count': 0,
        'lng_ok': 0,
    }

    # ---- 处理安居客主数据 (主数据源，优先处理) ----
    # 修改顺序：anjuke_m 先处理（它是主要数据源，每个区县一个文件）
    # 然后处理 merged/all_listings/anjuke_all 作为补充（跨文件去重）
    print(f'\n--- 处理安居客主数据 (anjuke_m_*.csv) ---')
    for fpath in anjuke_m:
        district = extract_district(fpath)
        rows = read_csv_safe(fpath)
        file_count = 0
        file_fixed = 0
        file_title_dup = 0
        file_cross_dup = 0
        seen_titles_in_file = set()

        for row in rows:
            stats['total_read'] += 1
            nr = normalize_row(row, 'anjuke', district)

            # 修复价格
            old_tp = safe_float(nr.get('total_price', 0))
            nr = fix_price(nr)
            new_tp = safe_float(nr.get('total_price', 0))
            if abs(old_tp - new_tp) > 1:
                file_fixed += 1

            # 同文件内：标题完全相同视为重复
            title_full = str(nr.get('title', '')).strip()
            if title_full and title_full in seen_titles_in_file:
                file_title_dup += 1
                continue
            if title_full:
                seen_titles_in_file.add(title_full)

            if safe_float(nr.get('lng', 0)) > 0:
                stats['lng_ok'] += 1

            all_rows.append(nr)
            file_count += 1

        stats['price_fixed'] += file_fixed
        stats['intra_file_dup_title'] += file_title_dup
        if file_title_dup > 0:
            print(f'  {district}: {file_count}条, 修复价格:{file_fixed}, 标题去重:{file_title_dup}')
        else:
            print(f'  {district}: {file_count}条, 修复价格:{file_fixed}')

    # 将所有 anjuke_m 的跨文件key加入集合（用于后续去重）
    for r in all_rows:
        key = make_cross_file_key(r, r['source'])
        if key:
            seen_keys.add(key)

    print(f'\n  主数据小计: {len(all_rows)} 条')

    # ---- 处理合并文件 (补充数据，跨文件去重) ----
    print(f'\n--- 处理合并文件 (补充数据，跨文件去重) ---')
    merged_added = 0
    merged_skipped = 0
    for fpath in merged:
        basename = os.path.basename(fpath)
        rows = read_csv_safe(fpath)
        file_added = 0
        file_skipped = 0

        for row in rows:
            stats['total_read'] += 1
            source = 'lianjia' if 'lianjia' in basename else 'anjuke'
            district = str(row.get('district', '')).strip()
            nr = normalize_row(row, source, district)
            nr = fix_price(nr)

            # 跨文件去重（与已有的 anjuke_m 数据比较）
            key = make_cross_file_key(nr, source)
            if key and key in seen_keys:
                stats['cross_file_dup'] += 1
                file_skipped += 1
                continue
            if key:
                seen_keys.add(key)

            if safe_float(nr.get('lng', 0)) > 0:
                stats['lng_ok'] += 1

            all_rows.append(nr)
            file_added += 1

        merged_added += file_added
        merged_skipped += file_skipped
        print(f'  {basename}: 新增{file_added}, 跳过{file_skipped}(重复)')

    print(f'  合并文件新增: {merged_added}, 跳过: {merged_skipped}')
    merged = []  # 已处理，清空避免重复

    # ---- 处理安居客其它 (跨文件去重) ----
    print(f'\n--- 处理安居客其它 (anjuke_*.csv) ---')
    for fpath in anjuke_other:
        district = extract_district(fpath)
        rows = read_csv_safe(fpath)
        added = 0
        skipped = 0
        lng_added = 0

        for row in rows:
            stats['total_read'] += 1
            nr = normalize_row(row, 'anjuke', district)
            nr = fix_price(nr)

            # 跨文件去重
            key = make_cross_file_key(nr, 'anjuke')
            if key and key in seen_keys:
                stats['cross_file_dup'] += 1
                skipped += 1
                continue

            if key:
                seen_keys.add(key)

            if safe_float(nr.get('lng', 0)) > 0:
                stats['lng_ok'] += 1
                lng_added += 1

            all_rows.append(nr)
            added += 1

        print(f'  {district}: 新增{added}, 跳过{skipped}(重复), 有坐标{lng_added}')

    # ---- 处理链家数据 (跨文件去重) ----
    print(f'\n--- 处理链家数据 (lianjia_*.csv) ---')
    for fpath in lianjia:
        district = extract_district(fpath)
        rows = read_csv_safe(fpath)
        added = 0
        skipped = 0

        for row in rows:
            stats['total_read'] += 1
            nr = normalize_row(row, 'lianjia', district)

            # 链家: 优先用 source_id 去重
            key = make_cross_file_key(nr, 'lianjia')
            if key and key in seen_keys:
                stats['cross_file_dup'] += 1
                skipped += 1
                continue

            if key:
                seen_keys.add(key)

            if safe_float(nr.get('lng', 0)) > 0:
                stats['lng_ok'] += 1

            all_rows.append(nr)
            added += 1
        print(f'  {district}: {added}条, 跳过{skipped}(重复)')

    # ---- 最终生成 DB 指纹并做最终去重 ----
    print(f'\n--- 最终去重（指纹级别）---')
    seen_fingerprints = set()
    final_rows = []
    fp_dup_count = 0
    for r in all_rows:
        r['fingerprint'] = make_fingerprint(r, r['source'])
        fp = r['fingerprint']
        if fp and fp in seen_fingerprints:
            fp_dup_count += 1
            continue
        if fp:
            seen_fingerprints.add(fp)
        final_rows.append(r)

    if fp_dup_count > 0:
        print(f'  指纹去重: {fp_dup_count} 条重复被移除')
        stats['fingerprint_dup'] = fp_dup_count
    else:
        stats['fingerprint_dup'] = 0

    all_rows = final_rows
    stats['final_count'] = len(all_rows)

    # ---- 输出清洗后的CSV ----
    out_csv = os.path.join(OUT_DIR, 'houses_clean.csv')
    with open(out_csv, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=STD_FIELDS, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(all_rows)

    # ---- 输出统计JSON ----
    stats_json = os.path.join(OUT_DIR, 'clean_stats.json')
    with open(stats_json, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    # ---- 打印汇总 ----
    print(f'\n{"=" * 60}')
    print(f'清洗完成!')
    print(f'  总读取: {stats["total_read"]} 条')
    print(f'  价格修复: {stats["price_fixed"]} 条')
    print(f'  标题去重(同文件): {stats["intra_file_dup_title"]} 条')
    print(f'  跨文件去重: {stats["cross_file_dup"]} 条')
    print(f'  最终保留: {stats["final_count"]} 条')
    print(f'  有坐标: {stats["lng_ok"]} 条 ({100*stats["lng_ok"]/max(stats["final_count"],1):.1f}%)')
    print(f'  输出文件: {out_csv}')

    # ---- 按来源/区县分布 ----
    by_source = defaultdict(int)
    by_district = defaultdict(int)
    price_samples = []
    for r in all_rows:
        by_source[r['source']] += 1
        by_district[r['district']] += 1
        tp = safe_float(r['total_price'])
        if 1 < tp < 5000:
            price_samples.append(tp)

    print(f'\n按来源:')
    for s, c in sorted(by_source.items()):
        print(f'  {s}: {c} 条')
    print(f'按区县(TOP 10):')
    for d, c in sorted(by_district.items(), key=lambda x: -x[1])[:10]:
        print(f'  {d}: {c} 条')
    if price_samples:
        print(f'\n价格范围(清洗后): {min(price_samples):.1f} ~ {max(price_samples):.1f} 万, '
              f'均值 {sum(price_samples)/len(price_samples):.1f} 万')

    return all_rows, stats


if __name__ == '__main__':
    clean_all()
