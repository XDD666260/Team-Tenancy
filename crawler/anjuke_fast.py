# ============================================================
# 安居客快速爬虫 — 多线程 + 隧道代理 + 纯列表页
# 优势: 速度快(6区并行), 代理自动换IP, 可快速达到5万+
# 缺陷: 不进详情页, 缺少 lng/lat/decoration/floor_desc/build_year
# ============================================================

import sys
import os
import re
import time
import random
import threading

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

from crawler.utils import (
    ANJUKE_DISTRICTS,
    OUTPUT_DIR, CHECKPOINT_DIR, ANJUKE_CSV_KEYS,
    make_anjuke_fingerprint,
    load_checkpoint, save_checkpoint,
    save_csv, deduplicate_and_save,
    mobile_get,
)

# ============================================================
# 并发配置
# ============================================================

WRITE_LOCK = threading.Lock()
WORKERS = 6  # 并行区县数


# ============================================================
# 列表页解析（移动站 li.item-wrap）
# ============================================================

def parse_list_page(html):
    """从移动站列表页HTML提取房源基本信息"""
    soup = BeautifulSoup(html, 'lxml')
    items = soup.select('li.item-wrap')
    results = []

    for item in items:
        try:
            # 房源ID (从链接提取)
            a_el = item.find('a') or item
            href = a_el.get('href', '') if hasattr(a_el, 'get') else ''
            id_match = re.search(r'/S(\d+)/', href)
            hid = id_match.group(1) if id_match else ''

            # 标题
            title_el = item.select_one('.content-title')
            title = title_el.get_text(strip=True) if title_el else ''
            if not title:
                continue

            # 描述字段: 户型 / 面积 / 朝向 / 区 / 商圈
            descs = item.select('.content-desc')
            desc_texts = [d.get_text(strip=True) for d in descs if d.get_text(strip=True)]
            layout = desc_texts[0] if len(desc_texts) > 0 else ''
            area_str = desc_texts[1] if len(desc_texts) > 1 else '0'
            orientation = desc_texts[2] if len(desc_texts) > 2 else ''
            biz_circle = desc_texts[3] if len(desc_texts) > 3 else ''

            # 面积
            area = 0.0
            try:
                area = float(re.sub(r'[^\d.]', '', area_str))
            except ValueError:
                pass

            # 总价
            price_el = item.select_one('.price') or item.select_one('[class*=price]')
            price_text = price_el.get_text(strip=True) if price_el else '0'
            total_price = 0.0
            try:
                total_price = float(re.sub(r'[^\d.]', '', price_text))
            except ValueError:
                pass

            if total_price <= 0:
                continue

            # 单价(列表页可能为空, 后续用 total_price/area 计算)
            unit_el = item.select_one('.unit-price')
            unit_text = unit_el.get_text(strip=True) if unit_el else '0'
            unit_price = 0.0
            try:
                unit_price = float(re.sub(r'[^\d.]', '', unit_text))
            except ValueError:
                pass

            # 小区名(从img alt或标题提取)
            community = ''
            for img in item.find_all('img'):
                alt = img.get('alt', '')
                cm = re.match(r'(.+?)\d+室', alt)
                if cm:
                    community = cm.group(1)
                    break
            if not community:
                title_match = re.match(r'\S+\s+(.+?)\s+[一二三四五六七八九\d]+房', title)
                if title_match:
                    community = title_match.group(1)

            # 户型解析
            rooms = halls = 0
            if layout:
                rm = re.search(r'(\d+)室', layout)
                if rm:
                    rooms = int(rm.group(1))
                hm = re.search(r'(\d+)厅', layout)
                if hm:
                    halls = int(hm.group(1))

            # 标签
            tags = '|'.join(t.get_text(strip=True) for t in item.select('.tag-wrap span, .tag'))

            results.append({
                'id': hid,
                'title': title,
                'total_price': total_price,
                'unit_price': unit_price,
                'community': community,
                'district': '',          # 由调用方填入
                'address': biz_circle,
                'lng': 0, 'lat': 0,     # 列表页无坐标
                'layout': layout,
                'rooms': rooms,
                'halls': halls,
                'bathrooms': 0,          # 列表页无卫生间数
                'area': area,
                'orientation': orientation,
                'decoration': '',         # 列表页无装修
                'floor_desc': '',         # 列表页无楼层描述
                'floor_type': '',
                'total_floors': 0,
                'build_year': 0,          # 列表页无建造年代
                'tags': tags,
                'followers': 0,
                'source': 'anjuke',
                'source_id': hid,
            })
        except Exception:
            continue

    return results


# ============================================================
# 字段计算
# ============================================================

def compute_fields(house):
    """计算可推导字段"""
    # unit_price = total_price * 10000 / area
    if house['unit_price'] == 0 and house['area'] > 0 and house['total_price'] > 0:
        house['unit_price'] = round(house['total_price'] * 10000 / house['area'], 2)

    # bathrooms: 从layout提取, 或按室数推断
    if house['bathrooms'] == 0:
        wm = re.search(r'(\d+)卫', house.get('layout', ''))
        if wm:
            house['bathrooms'] = int(wm.group(1))
        else:
            house['bathrooms'] = 1 if house['rooms'] <= 2 else 2


# ============================================================
# 单区县爬取
# ============================================================

def crawl_district(code, name, max_pages=80):
    """爬取一个区县的所有列表页, 不进详情页"""
    all_data = []
    checkpoint = load_checkpoint('anjuke_fast', code)
    pages_done = list(checkpoint.get('pages_done', []))
    completed = set(pages_done)

    if completed:
        print(f'  [{name}] 断点续爬: {len(completed)}页已完成')

    consecutive_empty = 0  # 连续空页计数

    for page in range(1, max_pages + 1):
        if page in completed:
            continue

        # 构建URL
        if page == 1:
            url = f'https://m.anjuke.com/cq/sale/{code}/'
        else:
            url = f'https://m.anjuke.com/cq/sale/{code}/p{page}/'

        # 页间延迟
        if page > 1:
            delay = random.uniform(10, 20)
            time.sleep(delay)

        # 请求列表页
        resp = mobile_get(url)
        if resp is None or len(resp.text) < 5000:
            print(f'  [{name}] p{page}: 请求失败, 重试...')
            time.sleep(30)
            resp = mobile_get(url)
            if resp is None or len(resp.text) < 5000:
                print(f'  [{name}] p{page}: 跳过')
                consecutive_empty += 1
                # 修复: 连续2页失败则停止（包括第1页）
                if consecutive_empty >= 2:
                    print(f'  [{name}] 连续{consecutive_empty}页无数据，停止翻页')
                    break
                continue

        # 检测反爬
        if 'antibot' in resp.text or 'xxzlGatewayUrl' in resp.text:
            print(f'  [{name}] p{page}: 被拦截')
            consecutive_empty += 1
            if consecutive_empty >= 2:
                print(f'  [{name}] 连续被拦截，停止翻页')
                break
            continue

        # 解析
        houses = parse_list_page(resp.text)
        for h in houses:
            h['district'] = name
            compute_fields(h)
            h['fingerprint'] = make_anjuke_fingerprint(h)

        all_data.extend(houses)
        print(f'  [{name}] p{page}: {len(houses)}条, 累计{len(all_data)}')

        if len(houses) > 0:
            pages_done.append(page)
            save_checkpoint('anjuke_fast', code, pages_done)
            consecutive_empty = 0
        else:
            consecutive_empty += 1

        # 修复: 连续2页空就停止（不限page>1）
        if consecutive_empty >= 2:
            print(f'  [{name}] 连续空页，停止翻页')
            break

    print(f'  [{name}] 完成: {len(pages_done)}页, {len(all_data)}条')
    return all_data


# ============================================================
# 区县保存(线程安全)
# ============================================================

def crawl_and_save(code, name):
    data = crawl_district(code, name)
    if data:
        out = os.path.join(OUTPUT_DIR, f'anjuke_fast_{name}.csv')
        with WRITE_LOCK:
            save_csv(data, out, ANJUKE_CSV_KEYS)
    return code, name, data


# ============================================================
# 主流程
# ============================================================

if __name__ == '__main__':
    print(f'安居客快速爬虫 v2: {WORKERS}线程并行, 纯列表页')
    print(f'覆盖区县: {len(ANJUKE_DISTRICTS)} 个')

    all_data = []
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {executor.submit(crawl_and_save, c, n): (c, n)
                   for c, n in ANJUKE_DISTRICTS}
        for future in as_completed(futures):
            c, n = futures[future]
            try:
                _, name, data = future.result()
                all_data.extend(data)
                done = len([f for f in futures if f.done()])
                print(f'>>> [{done}/{len(ANJUKE_DISTRICTS)}] {name}: '
                      f'{len(data)}条, 累计{len(all_data)}')
            except Exception as e:
                print(f'>>> [{n}] 异常: {e}')

    # 去重合并
    merged = os.path.join(OUTPUT_DIR, 'anjuke_all_fast.csv')
    unique, count = deduplicate_and_save(all_data, merged, ANJUKE_CSV_KEYS)
    print(f'\n总计: {len(all_data)}条, 去重: {count}条 -> {merged}')

    # 清理临时文件（修复: Windows兼容路径）
    import glob
    for pattern in ['debug_*.html', '*test*']:
        full_pattern = os.path.join(OUTPUT_DIR, pattern)
        for fpath in glob.glob(full_pattern):
            try:
                os.remove(fpath)
            except Exception:
                pass
