# ============================================================
# 安居客字段回填 — 读CSV, 标题+地址匹配, 进详情页补缺失字段
# 匹配策略: 标题一致 AND 区县一致 AND 小区名一致
# 补字段: lng/lat/decoration/floor_desc/build_year/bathrooms/id
# 边补边写回CSV, 支持断点续补
# ============================================================

import os
import re
import sys
import time
import random
import json
import glob

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

from crawler.utils import (
    ANJUKE_NAME_TO_CODE,
    OUTPUT_DIR, CHECKPOINT_DIR,
    mobile_get, desktop_get, safe_float,
)

DETAIL_WORKERS = 6
PROGRESS_FILE = os.path.join(CHECKPOINT_DIR, 'backfill_progress.json')


# ============================================================
# 进度管理
# ============================================================

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {'processed_files': [], 'total_filled': 0}


def save_progress(processed_files, total_filled):
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump({'processed_files': processed_files, 'total_filled': total_filled}, f)


# ============================================================
# 缺失字段分析
# ============================================================

def analyze_csv(fpath):
    """分析CSV中哪些字段缺失"""
    import csv
    with open(fpath, 'r', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return rows, None, 0

    total = len(rows)
    missing = {
        'lng': sum(1 for r in rows if safe_float(r.get('lng')) == 0),
        'decoration': sum(1 for r in rows if not r.get('decoration', '')),
        'floor_desc': sum(1 for r in rows if not r.get('floor_desc', '')),
        'build_year': sum(1 for r in rows if int(r.get('build_year', 0) or 0) == 0),
        'bathrooms': sum(1 for r in rows if int(r.get('bathrooms', 0) or 0) == 0),
        'id': sum(1 for r in rows if not r.get('id', '')),
    }
    return rows, missing, total


# ============================================================
# 列表页扫描(ID获取)
# ============================================================

def scan_list_pages(code, max_pages=12):
    """扫描移动站列表页, 建立 title→id 映射"""
    title_to_id = {}
    for page in range(1, max_pages + 1):
        if page == 1:
            url = f'https://m.anjuke.com/cq/sale/{code}/'
        else:
            url = f'https://m.anjuke.com/cq/sale/{code}/p{page}/'

        resp = mobile_get(url)
        if resp is None or len(resp.text) < 5000:
            break
        if 'antibot' in resp.text or 'xxzlGatewayUrl' in resp.text:
            continue

        soup = BeautifulSoup(resp.text, 'lxml')
        items = soup.select('li.item-wrap')
        if not items:
            break

        for item in items:
            try:
                a_el = item.find('a') or item
                href = a_el.get('href', '') if hasattr(a_el, 'get') else ''
                id_match = re.search(r'/S(\d+)/', href)
                if not id_match:
                    continue
                hid = id_match.group(1)

                title_el = item.select_one('.content-title')
                title = title_el.get_text(strip=True) if title_el else ''
                if title and title not in title_to_id:
                    title_to_id[title] = hid
            except Exception:
                continue

        time.sleep(random.uniform(3, 8))

    return title_to_id


# ============================================================
# 详情页字段获取
# ============================================================

def fetch_detail_fields(hid):
    """获取一个房源的详情页字段"""
    result = {
        'lng': 0, 'lat': 0, 'decoration': '',
        'floor_desc': '', 'floor_type': '', 'total_floors': 0,
        'build_year': 0, 'bathrooms': 0, 'id': hid,
    }

    # 桌面站: 经纬度
    for _ in range(3):
        try:
            resp = desktop_get(f'https://chongqing.anjuke.com/prop/view/S{hid}')
            if resp and resp.status_code == 200:
                coord_match = re.search(r'coord=([\d.]+),([\d.]+)', resp.text)
                if coord_match:
                    result['lng'] = float(coord_match.group(1))
                    result['lat'] = float(coord_match.group(2))
                    break
        except Exception:
            time.sleep(1)

    # 移动站: 装修/年代/楼层
    for _ in range(3):
        try:
            resp = mobile_get(f'https://m.anjuke.com/cq/sale/S{hid}/')
            if not resp or resp.status_code != 200:
                continue

            # meta keywords
            kw = re.search(r'<meta[^>]+name="keywords"[^>]+content="([^"]+)"', resp.text)
            if not kw:
                kw = re.search(r'<meta[^>]+content="([^"]+)"[^>]+name="keywords"', resp.text)
            if kw:
                content = kw.group(1)

                wm = re.search(r'(\d+)室\d+厅(\d+)卫', content)
                if wm:
                    result['bathrooms'] = int(wm.group(2))

                ym = re.search(r'(\d{4})年', content)
                if ym:
                    result['build_year'] = int(ym.group(1))

                dm = re.search(r'(精装修|精装|简装|毛坯|豪装)', content)
                if dm:
                    result['decoration'] = dm.group(1)

            # 楼层信息
            soup = BeautifulSoup(resp.text, 'lxml')
            page_text = soup.get_text(' ', strip=True)
            fm = re.search(r'(低层|中层|高层|低楼层|中楼层|高楼层).*?共\s*(\d+)\s*层', page_text)
            if fm:
                result['floor_desc'] = fm.group(0)
                result['total_floors'] = int(fm.group(2))
                ltm = re.search(r'(低层|中层|高层|低楼层|中楼层|高楼层)', fm.group(0))
                if ltm:
                    result['floor_type'] = ltm.group(1)

            break
        except Exception:
            time.sleep(1)

    return result


# ============================================================
# 单文件处理
# ============================================================

def process_csv(fpath):
    """处理一个CSV文件: 分析→扫描→匹配→补字段→保存"""
    import csv

    fname = os.path.basename(fpath)
    # 修复: 更健壮的文件名解析
    dist_name = fname.replace('anjuke_m_', '').replace('anjuke_fast_', '') \
                      .replace('anjuke_detail_', '').replace('anjuke_', '') \
                      .replace('.csv', '')
    code = ANJUKE_NAME_TO_CODE.get(dist_name)
    if not code:
        print(f'[{fname}] 找不到区县代码 (提取名称: {dist_name})')
        return 0

    print(f'\n=== {dist_name} ===')

    # 1. 分析
    rows, missing, total = analyze_csv(fpath)
    if not rows:
        return 0
    print(f'  总{total}条')
    print(f'  缺坐标:{missing["lng"]} 缺装修:{missing["decoration"]} '
          f'缺年代:{missing["build_year"]}')
    print(f'  缺楼层:{missing["floor_desc"]} 缺卫生间:{missing["bathrooms"]}')

    need_fill = missing['lng'] + missing['decoration'] + missing['build_year']
    if need_fill == 0:
        print(f'  [{dist_name}] 无需补字段')
        return 0

    # 2. 扫描列表页
    print(f'  扫描列表页获取ID...')
    title_to_id = scan_list_pages(code)
    print(f'  获取到 {len(title_to_id)} 个ID')

    # 3. 匹配
    to_fill = []
    for i, row in enumerate(rows):
        # 跳过已有坐标的
        if safe_float(row.get('lng')) > 0:
            continue

        title = row.get('title', '').strip()
        hid = title_to_id.get(title)
        if not hid:
            continue

        to_fill.append((i, hid))

    print(f'  可补充: {len(to_fill)}条')

    if not to_fill:
        return 0

    # 4. 并行补详情
    def fill_one(idx_hid):
        idx, hid = idx_hid
        fields = fetch_detail_fields(hid)
        # 修复: 统计所有补全的字段，不只是lng
        filled_any = False
        if fields['lng']:
            rows[idx]['lng'] = str(fields['lng'])
            rows[idx]['lat'] = str(fields['lat'])
            filled_any = True
        if fields['decoration']:
            rows[idx]['decoration'] = fields['decoration']
            filled_any = True
        if fields['floor_desc']:
            rows[idx]['floor_desc'] = fields['floor_desc']
            rows[idx]['floor_type'] = fields['floor_type']
            rows[idx]['total_floors'] = str(fields['total_floors'])
            filled_any = True
        if fields['build_year']:
            rows[idx]['build_year'] = str(fields['build_year'])
            filled_any = True
        if fields['bathrooms']:
            rows[idx]['bathrooms'] = str(fields['bathrooms'])
            filled_any = True
        if fields['id']:
            rows[idx]['id'] = fields['id']
            filled_any = True
        return 1 if filled_any else 0

    updated = 0
    with ThreadPoolExecutor(max_workers=DETAIL_WORKERS) as ex:
        results = list(ex.map(fill_one, to_fill))
        updated = sum(r for r in results if r)

    # 5. 保存
    fieldnames = list(rows[0].keys())
    if 'id' not in fieldnames:
        fieldnames.append('id')

    with open(fpath, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)

    lng_ok = sum(1 for r in rows if safe_float(r.get('lng')) > 0)
    print(f'  [{dist_name}] 完成: 坐标{lng_ok}/{len(rows)}, 本次更新{updated}个字段组')
    return updated


# ============================================================
# 主流程
# ============================================================

if __name__ == '__main__':
    # 支持指定文件或目录
    if len(sys.argv) > 1:
        target = sys.argv[1]
        if os.path.isdir(target):
            csv_files = sorted(glob.glob(os.path.join(target, '*.csv')))
        elif os.path.isfile(target):
            csv_files = [target]
        else:
            # 按区县名匹配
            csv_files = sorted(glob.glob(os.path.join(OUTPUT_DIR, f'anjuke_m_{target}.csv')))
            if not csv_files:
                csv_files = sorted(glob.glob(os.path.join(OUTPUT_DIR, f'anjuke_fast_{target}.csv')))
            if not csv_files:
                csv_files = sorted(glob.glob(os.path.join(OUTPUT_DIR, f'anjuke_detail_{target}.csv')))
    else:
        # 默认处理所有 anjuke_*.csv（排除汇总文件）
        all_csv = sorted(glob.glob(os.path.join(OUTPUT_DIR, 'anjuke_*.csv')))
        csv_files = [f for f in all_csv
                     if not any(x in f for x in ['anjuke_all', 'anjuke_m_missing', 'lianjia'])]

    if not csv_files:
        print('未找到CSV文件')
        sys.exit(1)

    print(f'待处理: {len(csv_files)} 个文件')
    progress = load_progress()
    processed = set(progress.get('processed_files', []))
    total_filled = progress.get('total_filled', 0)

    pending = [f for f in csv_files if os.path.basename(f) not in processed]
    print(f'已完成: {len(processed)}, 待处理: {len(pending)}')

    for fpath in pending:
        updated = process_csv(fpath)
        processed.add(os.path.basename(fpath))
        total_filled += updated
        save_progress(list(processed), total_filled)

    print(f'\n全部完成! 累计更新 {total_filled} 个字段组')
