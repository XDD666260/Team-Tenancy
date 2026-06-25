# ============================================================
# 安居客详情爬虫 — 单线程 + 进详情页 + 全字段
# 优势: 获取所有字段(坐标/装修/年代/楼层/卫生间)
# 缺陷: 速度慢(每个房源需请求桌面站+移动站)
# 适用: 对已有列表数据补全字段, 或小规模精确爬取
# ============================================================

import os
import re
import sys
import time
import random

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

from crawler.utils import (
    ANJUKE_DISTRICTS,
    OUTPUT_DIR, CHECKPOINT_DIR, ANJUKE_CSV_KEYS,
    make_anjuke_fingerprint,
    load_checkpoint, save_checkpoint,
    save_csv, deduplicate_and_save,
    mobile_get, desktop_get,
)

DETAIL_WORKERS = 4  # 每个区县的详情页并行线程数


# ============================================================
# 列表页解析（移动站 li.item-wrap）
# ============================================================

def parse_list_page(html):
    """从移动站列表页提取房源基本信息"""
    soup = BeautifulSoup(html, 'lxml')
    items = soup.select('li.item-wrap')
    results = []

    for item in items:
        try:
            a_el = item.find('a') or item
            href = a_el.get('href', '') if hasattr(a_el, 'get') else ''
            id_match = re.search(r'/S(\d+)/', href)
            hid = id_match.group(1) if id_match else ''

            title_el = item.select_one('.content-title')
            title = title_el.get_text(strip=True) if title_el else ''
            if not title:
                continue

            descs = item.select('.content-desc')
            desc_texts = [d.get_text(strip=True) for d in descs if d.get_text(strip=True)]
            layout = desc_texts[0] if len(desc_texts) > 0 else ''
            area_str = desc_texts[1] if len(desc_texts) > 1 else '0'
            orientation = desc_texts[2] if len(desc_texts) > 2 else ''
            biz_circle = desc_texts[3] if len(desc_texts) > 3 else ''

            area = 0.0
            try:
                area = float(re.sub(r'[^\d.]', '', area_str))
            except ValueError:
                pass

            price_el = item.select_one('.price') or item.select_one('[class*=price]')
            price_text = price_el.get_text(strip=True) if price_el else '0'
            total_price = 0.0
            try:
                total_price = float(re.sub(r'[^\d.]', '', price_text))
            except ValueError:
                pass

            if total_price <= 0:
                continue

            community = ''
            for img in item.find_all('img'):
                alt = img.get('alt', '')
                cm = re.match(r'(.+?)\d+室', alt)
                if cm:
                    community = cm.group(1)
                    break
            if not community:
                tm = re.match(r'\S+\s+(.+?)\s+[一二三四五六七八九\d]+房', title)
                if tm:
                    community = tm.group(1)

            rooms = halls = 0
            if layout:
                rm = re.search(r'(\d+)室', layout)
                if rm:
                    rooms = int(rm.group(1))
                hm = re.search(r'(\d+)厅', layout)
                if hm:
                    halls = int(hm.group(1))

            tags = '|'.join(t.get_text(strip=True) for t in item.select('.tag-wrap span, .tag'))

            results.append({
                'id': hid, 'title': title, 'total_price': total_price,
                'unit_price': 0, 'community': community, 'district': '',
                'address': biz_circle, 'lng': 0, 'lat': 0,
                'layout': layout, 'rooms': rooms, 'halls': halls,
                'bathrooms': 0, 'area': area, 'orientation': orientation,
                'decoration': '', 'floor_desc': '', 'floor_type': '',
                'total_floors': 0, 'build_year': 0,
                'tags': tags, 'followers': 0, 'source': 'anjuke',
                'source_id': hid,
            })
        except Exception:
            continue
    return results


# ============================================================
# 详情页获取
# ============================================================

def fetch_detail(house):
    """为一个房源补全所有详情页字段。

    1) 桌面站详情页: 经纬度(<meta name="location" coord="...">)
    2) 移动站详情页: 装修/年代/楼层/卫生间/单价(<meta name="keywords">)
    """
    hid = house.get('id', '')
    if not hid:
        return

    # --- 桌面站: 经纬度 ---
    for _ in range(3):
        try:
            resp = desktop_get(f'https://chongqing.anjuke.com/prop/view/S{hid}')
            if resp and resp.status_code == 200:
                coord_match = re.search(r'coord=([\d.]+),([\d.]+)', resp.text)
                if coord_match:
                    house['lng'] = float(coord_match.group(1))
                    house['lat'] = float(coord_match.group(2))
                    break
        except Exception:
            time.sleep(1)

    # --- 移动站: 其他字段 ---
    for _ in range(3):
        try:
            resp = mobile_get(f'https://m.anjuke.com/cq/sale/S{hid}/')
            if not resp or resp.status_code != 200:
                continue

            # meta keywords: "126万,3室2厅1卫,91.77平米,13730元/平米,2017年,北,精装修"
            kw = re.search(r'<meta[^>]+name="keywords"[^>]+content="([^"]+)"', resp.text)
            if not kw:
                kw = re.search(r'<meta[^>]+content="([^"]+)"[^>]+name="keywords"', resp.text)
            if kw:
                content = kw.group(1)

                # 卫生间: N室N厅N卫
                wm = re.search(r'(\d+)室\d+厅(\d+)卫', content)
                if wm:
                    house['bathrooms'] = int(wm.group(2))

                # 单价: NNNN元/平米
                upm = re.search(r'([\d.]+)\s*元/平米', content)
                if upm:
                    house['unit_price'] = float(upm.group(1))

                # 年代: NNNN年
                ym = re.search(r'(\d{4})年', content)
                if ym:
                    house['build_year'] = int(ym.group(1))

                # 装修: 精装修/简装/毛坯/豪装
                dm = re.search(r'(精装修|精装|简装|毛坯|豪装)', content)
                if dm:
                    house['decoration'] = dm.group(1)

            # 楼层信息从页面文本提取
            soup = BeautifulSoup(resp.text, 'lxml')
            page_text = soup.get_text(' ', strip=True)
            fm = re.search(r'(低层|中层|高层|低楼层|中楼层|高楼层).*?共\s*(\d+)\s*层', page_text)
            if fm:
                house['floor_desc'] = fm.group(0)
                house['total_floors'] = int(fm.group(2))
                ltm = re.search(r'(低层|中层|高层|低楼层|中楼层|高楼层)', fm.group(0))
                if ltm:
                    house['floor_type'] = ltm.group(1)
            else:
                fm2 = re.search(r'共\s*(\d+)\s*层', page_text)
                if fm2:
                    house['total_floors'] = int(fm2.group(1))
                ltm2 = re.search(r'(低层|中层|高层|低楼层|中楼层|高楼层)', page_text)
                if ltm2:
                    house['floor_desc'] = ltm2.group(1)
                    house['floor_type'] = ltm2.group(1)

            break
        except Exception:
            time.sleep(1)

    # --- 字段兜底计算 ---
    if house.get('unit_price', 0) == 0 and house.get('area', 0) > 0 and house.get('total_price', 0) > 0:
        house['unit_price'] = round(house['total_price'] * 10000 / house['area'], 2)

    if house.get('bathrooms', 0) == 0:
        wm = re.search(r'(\d+)卫', house.get('layout', ''))
        if wm:
            house['bathrooms'] = int(wm.group(1))
        else:
            house['bathrooms'] = 1 if house.get('rooms', 0) <= 2 else 2

    time.sleep(random.uniform(2, 5))


# ============================================================
# 区县爬取
# ============================================================

def crawl_district(code, name, max_pages=80):
    """单线程爬取一个区县: 列表页→详情页，返回全字段房源列表"""
    all_data = []
    checkpoint = load_checkpoint('anjuke_detail', code)
    pages_done = list(checkpoint.get('pages_done', []))
    completed = set(pages_done)
    if completed:
        print(f'  [{name}] 断点: {len(completed)}页')

    for page in range(1, max_pages + 1):
        if page in completed:
            continue

        if page == 1:
            url = f'https://m.anjuke.com/cq/sale/{code}/'
        else:
            url = f'https://m.anjuke.com/cq/sale/{code}/p{page}/'

        if page > 1:
            time.sleep(random.uniform(15, 30))

        resp = mobile_get(url)
        if resp is None or len(resp.text) < 5000:
            time.sleep(30)
            resp = mobile_get(url)
            if resp is None or len(resp.text) < 5000:
                continue

        if 'antibot' in resp.text or 'xxzlGatewayUrl' in resp.text:
            continue

        houses = parse_list_page(resp.text)
        if not houses and page > 1:
            break
        if not houses:
            continue

        for h in houses:
            h['district'] = name

        # 并行抓详情页
        if houses:
            with ThreadPoolExecutor(max_workers=DETAIL_WORKERS) as ex:
                # 使用 list() 消费迭代器以触发所有任务
                for _ in ex.map(fetch_detail, houses):
                    pass

        for h in houses:
            h['fingerprint'] = make_anjuke_fingerprint(h)

        all_data.extend(houses)
        print(f'  [{name}] p{page}: {len(houses)}条,累计{len(all_data)}')

        pages_done.append(page)
        save_checkpoint('anjuke_detail', code, pages_done)

    print(f'  [{name}] 完成: {len(pages_done)}页, {len(all_data)}条')
    return all_data


# ============================================================
# 主流程
# ============================================================

if __name__ == '__main__':
    if len(sys.argv) > 1:
        # 指定区县
        target = sys.argv[1]
        districts = [(c, n) for c, n in ANJUKE_DISTRICTS if n == target or c == target]
        if not districts:
            print(f'未找到区县: {target}')
            sys.exit(1)
    else:
        districts = ANJUKE_DISTRICTS

    print(f'安居客详情爬虫 v2: 单线程区县, {DETAIL_WORKERS}线程详情页')
    print(f'目标区县: {len(districts)}')

    all_data = []
    for code, name in districts:
        print(f'\n=== {name} ({code}) ===')
        data = crawl_district(code, name)
        all_data.extend(data)
        if data:
            out = os.path.join(OUTPUT_DIR, f'anjuke_detail_{name}.csv')
            save_csv(data, out, ANJUKE_CSV_KEYS)
            lng_ok = sum(1 for h in data if h.get('lng', 0) > 0)
            print(f'  CSV已保存: {out} ({len(data)}条, 坐标{lng_ok})')

    # 汇总
    if len(districts) > 1 and all_data:
        merged = os.path.join(OUTPUT_DIR, 'anjuke_all_detail.csv')
        unique, count = deduplicate_and_save(all_data, merged, ANJUKE_CSV_KEYS)
        print(f'\n去重汇总: {count}条 -> {merged}')
