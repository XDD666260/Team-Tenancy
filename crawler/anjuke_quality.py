# ============================================================
# 安居客质量爬虫 — 网页站详情补全 + 移动站详情补充
# 与 anjuke_fast.py 同步运行：
#   快速爬虫(移动站列表页) → 基础CSV → 质量爬虫(详情页) → 富CSV
#
# 策略：
#   1. 扫描 data/raw/ 下 anjuke_fast_*.csv（快速爬虫产出）
#   2. 对每条房源请求两个详情页补全字段
#   3. 桌面站详情页 → 经纬度坐标
#   4. 移动站详情页 → 装修/年代/楼层/卫生间/单价
#   5. 输出 anjuke_rich_{name}.csv（全22字段）
#
# 速度：10线程并行，约300-500条/分钟（取决于代理速度）
# ============================================================

import os
import re
import sys
import time
import csv
import glob
import json
import random
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from concurrent.futures import ThreadPoolExecutor, as_completed

from crawler.utils import (
    ANJUKE_DISTRICTS, ANJUKE_CSV_KEYS, OUTPUT_DIR, CHECKPOINT_DIR,
    mobile_get, desktop_get, get_proxy, refresh_proxy_list,
    make_anjuke_fingerprint,
)

QUALITY_WORKERS = 4               # 详情页并行线程数（降低避免冲垮代理）
DETAIL_RETRIES = 2                # 详情页请求重试次数
IDLE_SCAN_INTERVAL = 15           # 扫描新文件的间隔（秒）
DETAIL_DELAY = (2, 5)             # 详情请求间随机延迟(秒)
WRITE_LOCK = threading.Lock()     # CSV写入锁


# ============================================================
# 详情页字段获取
# ============================================================

def fetch_desktop_detail(hid):
    """桌面站详情页 → 经纬度 + 额外字段

    URL: https://chongqing.anjuke.com/prop/view/S{hid}/
    提取: <meta name="location" content="province=重庆;coord=106.52,29.54">
    """
    result = {'lng': 0, 'lat': 0}

    for attempt in range(DETAIL_RETRIES):
        try:
            resp = desktop_get(
                f'https://chongqing.anjuke.com/prop/view/S{hid}',
                proxy_url=None  # 让desktop_get自己每次重试换代理
            )
            if not resp or resp.status_code != 200:
                continue

            coord_match = re.search(r'coord=([\d.]+),([\d.]+)', resp.text)
            if coord_match:
                result['lng'] = float(coord_match.group(1))
                result['lat'] = float(coord_match.group(2))
                return result

            # 如果没找到坐标，尝试其他模式
            coord_match2 = re.search(r'"longitude":\s*([\d.]+).*?"latitude":\s*([\d.]+)', resp.text)
            if coord_match2:
                result['lng'] = float(coord_match2.group(1))
                result['lat'] = float(coord_match2.group(2))
                return result

        except Exception:
            time.sleep(random.uniform(1, 3))

    return result


def fetch_mobile_detail(hid):
    """移动站详情页 → 装修/年代/楼层/卫生间/单价

    URL: https://m.anjuke.com/cq/sale/S{hid}/
    提取: <meta name="keywords" content="126万,3室2厅1卫,91.77平米,13730元/平米,2017年,北,精装修">
    """
    result = {
        'decoration': '', 'build_year': 0, 'total_floors': 0,
        'floor_type': '', 'floor_desc': '', 'bathrooms': 0,
        'unit_price': 0,
    }

    for attempt in range(DETAIL_RETRIES):
        try:
            resp = mobile_get(
                f'https://m.anjuke.com/cq/sale/S{hid}/',
                proxy_url=None  # 让mobile_get每次重试自己换代理
            )
            if not resp or resp.status_code != 200:
                continue

            # meta keywords
            kw = re.search(r'<meta[^>]+name="keywords"[^>]+content="([^"]+)"', resp.text)
            if not kw:
                kw = re.search(r'<meta[^>]+content="([^"]+)"[^>]+name="keywords"', resp.text)

            if kw:
                content = kw.group(1)

                # 卫生间: N室N厅N卫
                wm = re.search(r'(\d+)室\d+厅(\d+)卫', content)
                if wm:
                    result['bathrooms'] = int(wm.group(2))

                # 单价: NNNN元/平米
                upm = re.search(r'([\d.]+)\s*元/平米', content)
                if upm:
                    result['unit_price'] = float(upm.group(1))

                # 年代: NNNN年
                ym = re.search(r'(\d{4})年', content)
                if ym:
                    result['build_year'] = int(ym.group(1))

                # 装修
                dm = re.search(r'(精装修|精装|简装|毛坯|豪装)', content)
                if dm:
                    result['decoration'] = dm.group(1)

            # 楼层信息（从页面文本提取）
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'lxml')
            page_text = soup.get_text(' ', strip=True)

            fm = re.search(r'(低层|中层|高层|低楼层|中楼层|高楼层).*?共\s*(\d+)\s*层', page_text)
            if fm:
                result['floor_desc'] = fm.group(0)
                result['total_floors'] = int(fm.group(2))
                ltm = re.search(r'(低层|中层|高层|低楼层|中楼层|高楼层)', fm.group(0))
                if ltm:
                    result['floor_type'] = ltm.group(1)
            else:
                fm2 = re.search(r'共\s*(\d+)\s*层', page_text)
                if fm2:
                    result['total_floors'] = int(fm2.group(1))
                ltm2 = re.search(r'(低层|中层|高层|低楼层|中楼层|高楼层)', page_text)
                if ltm2:
                    result['floor_desc'] = ltm2.group(1)
                    result['floor_type'] = ltm2.group(1)

            break

        except Exception:
            time.sleep(random.uniform(1, 3))

    return result


def enrich_single_house(house):
    """为单条房源补全所有缺失字段

    返回: (房源dict, 补全字段数)
    """
    hid = house.get('id', '') or house.get('source_id', '')
    if not hid:
        return house, 0

    # 随机延迟，降低代理压力
    time.sleep(random.uniform(*DETAIL_DELAY))

    filled = 0
    need_desktop = (float(house.get('lng', 0) or 0) == 0)
    need_mobile = (
        not house.get('decoration', '') or
        int(house.get('build_year', 0) or 0) == 0 or
        int(house.get('bathrooms', 0) or 0) == 0 or
        not house.get('floor_desc', '')
    )

    # 桌面站详情（坐标）
    if need_desktop:
        desktop = fetch_desktop_detail(hid)
        if desktop['lng'] > 0:
            house['lng'] = str(desktop['lng'])
            house['lat'] = str(desktop['lat'])
            filled += 1

    # 移动站详情（装修/年代/楼层/卫生间/单价）
    if need_mobile:
        mobile = fetch_mobile_detail(hid)
        if mobile['decoration'] and not house.get('decoration'):
            house['decoration'] = mobile['decoration']
            filled += 1
        if mobile['build_year'] > 0 and int(house.get('build_year', 0) or 0) == 0:
            house['build_year'] = str(mobile['build_year'])
            filled += 1
        if mobile['bathrooms'] > 0 and int(house.get('bathrooms', 0) or 0) == 0:
            house['bathrooms'] = str(mobile['bathrooms'])
            filled += 1
        if mobile['total_floors'] > 0 and int(house.get('total_floors', 0) or 0) == 0:
            house['total_floors'] = str(mobile['total_floors'])
            house['floor_type'] = mobile['floor_type']
            house['floor_desc'] = mobile['floor_desc']
            filled += 1
        if mobile['unit_price'] > 0 and float(house.get('unit_price', 0) or 0) == 0:
            house['unit_price'] = str(mobile['unit_price'])
            filled += 1

    # 字段兜底计算
    area = float(house.get('area', 0) or 0)
    tp = float(house.get('total_price', 0) or 0)
    if float(house.get('unit_price', 0) or 0) == 0 and area > 0 and tp > 0:
        house['unit_price'] = str(round(tp * 10000 / area, 2))

    if int(house.get('bathrooms', 0) or 0) == 0:
        wm = re.search(r'(\d+)卫', house.get('layout', ''))
        if wm:
            house['bathrooms'] = str(int(wm.group(1)))
        else:
            rooms = int(house.get('rooms', 0) or 0)
            house['bathrooms'] = str(1 if rooms <= 2 else 2)

    return house, filled


# ============================================================
# CSV 处理
# ============================================================

def get_district_from_filename(fname):
    """从文件名提取区县名"""
    for prefix in ['anjuke_fast_', 'anjuke_detail_', 'anjuke_']:
        if fname.startswith(prefix):
            return fname.replace(prefix, '').replace('.csv', '')
    return fname.replace('.csv', '')


def process_csv(input_path):
    """处理一个CSV文件：读取 → 补全字段 → 输出富CSV

    Returns: (处理条数, 补全条数)
    """
    fname = os.path.basename(input_path)
    district = get_district_from_filename(fname)
    output_path = os.path.join(OUTPUT_DIR, f'anjuke_rich_{district}.csv')

    # 跳过已处理的文件
    if os.path.exists(output_path):
        # 检查是否比输入文件新
        if os.path.getmtime(output_path) >= os.path.getmtime(input_path):
            print(f'  [{district}] 已处理，跳过')
            return 0, 0

    # 读取CSV
    try:
        with open(input_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        if not rows:
            return 0, 0
    except Exception as e:
        print(f'  [{district}] 读取失败: {e}')
        return 0, 0

    # 分析缺失字段
    total = len(rows)
    missing_lng = sum(1 for r in rows if float(r.get('lng', 0) or 0) == 0)
    missing_dec = sum(1 for r in rows if not r.get('decoration', ''))
    missing_year = sum(1 for r in rows if int(r.get('build_year', 0) or 0) == 0)

    print(f'  [{district}] {total}条 | 缺坐标:{missing_lng} 缺装修:{missing_dec} 缺年代:{missing_year}')

    # 筛选需要补全的房源
    need_enrich = []
    skip_count = 0
    for r in rows:
        has_lng = float(r.get('lng', 0) or 0) > 0
        has_dec = bool(r.get('decoration', ''))
        has_year = int(r.get('build_year', 0) or 0) > 0
        has_bath = int(r.get('bathrooms', 0) or 0) > 0

        if has_lng and has_dec and has_year and has_bath:
            skip_count += 1
            continue
        need_enrich.append(r)

    if not need_enrich:
        print(f'  [{district}] 全部字段完整({skip_count}条)，直接复制')
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys(), extrasaction='ignore')
            writer.writeheader()
            writer.writerows(rows)
        return total, 0

    # 并行补全
    print(f'  [{district}] 需补全:{len(need_enrich)}条, 完整:{skip_count}条 (10线程并行)')
    filled_count = 0
    processed = 0

    with ThreadPoolExecutor(max_workers=QUALITY_WORKERS) as ex:
        futures = {ex.submit(enrich_single_house, r): i for i, r in enumerate(need_enrich)}
        for future in as_completed(futures):
            try:
                _, filled = future.result()
                if filled > 0:
                    filled_count += 1
                processed += 1
                if processed % 50 == 0:
                    print(f'  [{district}] 进度: {processed}/{len(need_enrich)}')
            except Exception as e:
                processed += 1

    # 输出（need_enrich 中的 dict 是 rows 中的引用，已原地修改）
    with WRITE_LOCK:
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            fieldnames = list(rows[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(rows)

    lng_ok = sum(1 for r in rows if float(r.get('lng', 0) or 0) > 0)
    dec_ok = sum(1 for r in rows if r.get('decoration', ''))
    print(f'  [{district}] 完成! 坐标:{lng_ok}/{total}, 装修:{dec_ok}, 本次补全:{filled_count}条')
    return total, filled_count


# ============================================================
# 主流程：持续扫描 + 处理
# ============================================================

def scan_and_process(oneshot=False):
    """扫描 data/raw/ 下的 anjuke_fast_*.csv，处理新文件

    Args:
        oneshot: True=处理一轮就退出, False=持续监控
    """
    processed_files = set()
    total_processed = 0
    total_filled = 0

    while True:
        # 扫描快速爬虫产出的CSV
        fast_files = sorted(glob.glob(os.path.join(OUTPUT_DIR, 'anjuke_fast_*.csv')))
        pending = [f for f in fast_files if os.path.basename(f) not in processed_files]

        if pending:
            print(f'\n{"="*55}')
            print(f'发现 {len(pending)} 个新文件待处理')
            print(f'{"="*55}')

            for fpath in pending:
                processed, filled = process_csv(fpath)
                processed_files.add(os.path.basename(fpath))
                total_processed += processed
                total_filled += filled

            print(f'\n本轮完成: {total_processed}条处理, {total_filled}条补全')

        if oneshot:
            break

        # 等待新文件出现
        fast_count = len(fast_files)
        print(f'\n[监控] 已处理 {len(processed_files)} 个文件, '
              f'当前 {fast_count} 个fast文件, '
              f'{IDLE_SCAN_INTERVAL}秒后再次扫描...')
        time.sleep(IDLE_SCAN_INTERVAL)

    return total_processed, total_filled


# ============================================================
# 入口
# ============================================================

if __name__ == '__main__':
    proxy_count = refresh_proxy_list()
    print(f'安居客质量爬虫 v1: {QUALITY_WORKERS}线程详情页并行')
    print(f'代理池: {proxy_count} 个私密代理')
    print(f'模式: {"单次处理" if "--oneshot" in sys.argv else "持续监控（与快速爬虫同步）"}')
    print()

    if len(sys.argv) > 1 and sys.argv[-1] != '--oneshot':
        # 指定区县模式
        target = sys.argv[-1]
        fpath = os.path.join(OUTPUT_DIR, f'anjuke_fast_{target}.csv')
        if os.path.exists(fpath):
            process_csv(fpath)
        else:
            print(f'文件不存在: {fpath}')
            print(f'可用文件:')
            for f in sorted(glob.glob(os.path.join(OUTPUT_DIR, 'anjuke_fast_*.csv'))):
                print(f'  {os.path.basename(f)}')
    else:
        oneshot = '--oneshot' in sys.argv
        scan_and_process(oneshot=oneshot)
