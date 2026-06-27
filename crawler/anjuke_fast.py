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
    ANJUKE_DISTRICTS, PROXY_URL,
    OUTPUT_DIR, CHECKPOINT_DIR, ANJUKE_CSV_KEYS,
    make_anjuke_fingerprint,
    load_checkpoint, save_checkpoint,
    save_csv, deduplicate_and_save,
    mobile_get, get_proxy, refresh_proxy_list,
)

# ============================================================
# 并发配置
# ============================================================

WRITE_LOCK = threading.Lock()
WORKERS = 3  # 并行区县数（降低以减少代理消耗）


# ============================================================
# 列表页解析（移动站 li.item-wrap）
# ============================================================

def parse_list_page(html):
    """从移动站列表页HTML提取房源基本信息

    价格提取：.content-price(新版) → .price-wrap → .price(旧版) → 标题正则
    """
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

            # ====== 价格提取（适配2026年6月移动站新版CSS） ======
            # 新版: .content-price=总价数字, .house-avg-price=单价
            # 旧版: .price=总价+万, .unit-price=单价
            total_price = 0.0
            price_text = ''

            # 方法1: .content-price (2026新版，纯数字如"120")
            price_el = item.select_one('.content-price')
            if price_el:
                price_text = price_el.get_text(strip=True)
                if price_text and not price_text.endswith('万'):
                    price_text += '万'

            # 方法2: .price-wrap (新版包裹元素，如"120万12173元/m2")
            if not price_text:
                pw = item.select_one('.price-wrap')
                if pw:
                    full_text = pw.get_text(' ', strip=True)
                    pm = re.search(r'([\d.]+)万', full_text)
                    if pm:
                        price_text = pm.group(1) + '万'

            # 方法3: .price (旧版)
            if not price_text:
                price_el = item.select_one('.price')
                if price_el:
                    price_text = price_el.get_text(strip=True)

            # 方法4: [class*=price] 泛匹配
            if not price_text:
                for el in item.select('[class*=price]'):
                    txt = el.get_text(strip=True)
                    if re.search(r'\d', txt) and '万' in txt and len(txt) < 30:
                        pm = re.search(r'([\d.]+)万', txt)
                        if pm:
                            price_text = pm.group(1) + '万'
                            break

            # 方法5: 标题兜底
            if price_text:
                try:
                    total_price = float(re.sub(r'[^\d.]', '', price_text))
                except ValueError:
                    total_price = 0.0
            if total_price <= 0:
                pm = re.search(r'(\d+\.?\d*)\s*万', title)
                if pm:
                    total_price = float(pm.group(1))

            if total_price <= 0:
                continue

            # 单价: .house-avg-price (新版) 或 .unit-price (旧版)
            unit_price = 0.0
            unit_el = (item.select_one('.house-avg-price') or
                       item.select_one('.unit-price') or
                       item.select_one('[class*=unit]'))
            if unit_el:
                unit_text = unit_el.get_text(strip=True)
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

def crawl_district(code, name, max_pages=20, price_range=None, room_range=None):
    """爬取一个区县的所有列表页, 不进详情页

    翻页去重策略（修复代理缓存bug）：
    1. URL添加时间戳参数破坏缓存命中
    2. 每页请求前随机延迟 + 轮换UA
    3. 页面内容校验：仅前5页做缓存检测(>90%重合=缓存)
    4. 支持按价格段/户型段细分搜索以获取更多唯一房源

    Args:
        code: 区县编码
        name: 区县名
        max_pages: 最大翻页数
        price_range: 价格段 (p1-p6), None=不限
        room_range: 户型段 (r1-r5), None=不限
    """
    all_data = []
    seen_ids = set()
    # 为细分搜索生成独立断点key
    suffix = ''
    if price_range: suffix += f'_p{price_range}'
    if room_range: suffix += f'_r{room_range}'
    checkpoint_key = f'anjuke_fast{suffix}'
    checkpoint = load_checkpoint(checkpoint_key, code)
    pages_done = list(checkpoint.get('pages_done', []))
    completed = set(pages_done)

    if completed:
        print(f'  [{name}] 断点续爬: {len(completed)}页已完成')

    consecutive_empty = 0
    prev_page_ids = set()

    for page in range(1, max_pages + 1):
        if page in completed:
            continue

        # ---- 构建URL ----
        cache_buster = int(time.time() * 1000) % 1000000
        base_url = f'https://m.anjuke.com/cq/sale/{code}/'
        if page == 1:
            url = base_url
        else:
            url = f'{base_url}p{page}/'

        # ---- 添加筛选参数 ----
        params = []
        if price_range:
            params.append(f'pricerange={price_range}')
        if room_range:
            params.append(f'roomrange={room_range}')
        params.append(f'_t={cache_buster}')
        url += '?' + '&'.join(params)

        # ---- 页间延迟 ----
        if page > 1:
            has_private_proxies = bool(get_proxy())
            delay = random.uniform(5, 8) if has_private_proxies else random.uniform(12, 20)
            time.sleep(delay)

        # ---- 请求列表页（带缓存检测重试） ----
        houses = None
        MAX_CACHE_RETRIES = 4

        for cache_retry in range(MAX_CACHE_RETRIES):
            # 每次重试换时间戳 + 换代理IP
            retry_url = url
            if cache_retry >= 1:
                retry_url = url.replace(f'_t={cache_buster}', f'_t={int(time.time()*1000)%1000000}')
                time.sleep(random.uniform(5, 10))

            # 始终走代理池（proxy_url=None → 自动从代理池选取）
            resp = mobile_get(retry_url, proxy_url=None)
            if resp is None or len(resp.text) < 5000:
                continue

            if 'antibot' in resp.text or 'xxzlGatewayUrl' in resp.text:
                continue

            houses = parse_list_page(resp.text)
            if not houses:
                continue

            # ---- 第一页诊断 ----
            if page == 1 and houses:
                zero_prices = sum(1 for h in houses if h['total_price'] <= 0)
                if zero_prices > len(houses) * 0.5:
                    debug_path = os.path.join(OUTPUT_DIR, f'debug_{code}_p1.html')
                    with open(debug_path, 'w', encoding='utf-8') as f:
                        f.write(resp.text)
                    print(f'  [{name}] WARN: {zero_prices}/{len(houses)} prices=0, saved debug HTML')

            # ---- 缓存检测 ----
            # 仅对前5页做缓存检测（后面页码重叠是正常的）
            page_ids = {h['id'] for h in houses if h.get('id')}
            if page <= 5 and prev_page_ids and page_ids:
                overlap = len(page_ids & prev_page_ids)
                overlap_ratio = overlap / max(len(page_ids), 1)
                if overlap_ratio > 0.9:
                    print(f'  [{name}] p{page}: 缓存检测({overlap}/{len(page_ids)}={overlap_ratio:.0%}), '
                          f'换代理重试{cache_retry+1}/{MAX_CACHE_RETRIES}')
                    continue

            # 通过检测
            prev_page_ids = page_ids
            break

        # ---- 处理请求结果 ----
        if houses is None or len(houses) == 0:
            print(f'  [{name}] p{page}: 请求失败(重试{MAX_CACHE_RETRIES}次后)')
            consecutive_empty += 1
            # 失败时刷新代理池
            if consecutive_empty >= 1:
                new_count = refresh_proxy_list()
                if new_count > 0:
                    print(f'  [{name}] 已刷新代理池: {new_count}个新IP')
                    time.sleep(random.uniform(15, 25))  # 冷却
            if consecutive_empty >= 3:
                print(f'  [{name}] 连续{consecutive_empty}页无数据，停止翻页')
                break
            continue

        # ---- 本区内去重 + 计算字段 ----
        new_on_page = 0
        for h in houses:
            h['district'] = name
            compute_fields(h)
            h['fingerprint'] = make_anjuke_fingerprint(h)
            hid = h.get('id', '')
            if hid and hid not in seen_ids:
                seen_ids.add(hid)
                all_data.append(h)
                new_on_page += 1

        dup_on_page = len(houses) - new_on_page
        dup_info = f' (去重{dup_on_page})' if dup_on_page > 0 else ''
        print(f'  [{name}] p{page}: {len(houses)}条 → 新增{new_on_page}条{dup_info}, '
              f'累计{len(all_data)}唯一')

        # 追踪连续0新增页数（节省代理，避免无意义翻页）
        if new_on_page == 0:
            consecutive_empty += 1
        else:
            consecutive_empty = 0

        if len(houses) > 0:
            pages_done.append(page)
            save_checkpoint(checkpoint_key, code, pages_done)

        # 连续3页0新增 → 该区县已无新数据
        if consecutive_empty >= 3:
            print(f'  [{name}] 连续{consecutive_empty}页无新增，停止翻页')
            break

    label = f'{name}'
    if price_range: label += f'[价段{price_range}]'
    if room_range: label += f'[户型{room_range}]'
    print(f'  [{label}] 完成: {len(pages_done)}页, {len(all_data)}条唯一')
    return all_data


# ============================================================
# 区县保存(线程安全)
# ============================================================

def crawl_and_save(code, name, price_range=None, room_range=None):
    data = crawl_district(code, name, price_range=price_range, room_range=room_range)
    out = os.path.join(OUTPUT_DIR, f'anjuke_fast_{name}.csv')
    with WRITE_LOCK:
        # 加载旧CSV数据
        existing = {}
        if os.path.exists(out):
            import csv as csv_module
            try:
                with open(out, 'r', encoding='utf-8-sig') as f:
                    for row in csv_module.DictReader(f):
                        hid = row.get('id', '')
                        if hid and hid not in existing:
                            existing[hid] = row
            except Exception:
                pass
        # 合并新数据
        for h in data:
            hid = h.get('id', '')
            if hid:
                existing[hid] = h
        merged = list(existing.values())
        save_csv(merged, out, ANJUKE_CSV_KEYS)
        # 返回合并后的数据（确保日志显示真实总数）
        data = merged
    return code, name, data


# ============================================================
# 主流程
# ============================================================

if __name__ == '__main__':
    proxy_count = refresh_proxy_list()
    print(f'安居客快速爬虫 v3.2: {WORKERS}线程并行, 代理池{proxy_count}个, 页间5-8秒')
    print(f'覆盖区县: {len(ANJUKE_DISTRICTS)} 个')
    print(f'特性: 自动刷新代理 | 多级价格提取 | 缓存检测 | 断点续爬')
    print()

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
