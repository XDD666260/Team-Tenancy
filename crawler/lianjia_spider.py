# ============================================================
# 链家二手房爬虫 v2 — 私密代理池 + 真分页 + 断点续爬
# 链家每页30条，严格分页无重叠，是主要数据量来源
# ============================================================

import sys
import os
import re
import time
import csv as csv_module
import random
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

from crawler.utils import (
    LIANJIA_COOKIE, LIANJIA_DISTRICTS, LIANJIA_CSV_KEYS,
    USER_AGENTS_DESKTOP, OUTPUT_DIR, CHECKPOINT_DIR,
    make_lianjia_fingerprint,
    load_checkpoint, save_checkpoint,
    save_csv, get_proxy, refresh_proxy_list,
    parse_cookie_string,
)
import requests

WORKERS = 1            # 链家同IP不能并发，单线程
WRITE_LOCK = threading.Lock()
MAX_PAGES = 50         # 每区县最大翻页数
PAGE_SIZE = 30         # 链家每页固定30条


# ============================================================
# 列表页解析
# ============================================================

def parse_house_info(info_text):
    """解析链家 houseInfo: "3室2厅|122.25平米|南|精装|高楼层(共18层)|2005年建" """
    parts = [p.strip() for p in info_text.split('|')]
    result = {
        'layout': parts[0] if len(parts) > 0 else '',
        'area': 0, 'orientation': '', 'decoration': '',
        'floor_desc': '', 'rooms': 0, 'halls': 0, 'bathrooms': 0,
        'floor_type': '', 'total_floors': 0, 'build_year': 0,
    }

    if len(parts) > 1:
        try:
            result['area'] = float(parts[1].replace('平米', '').replace('㎡', '').strip())
        except ValueError:
            pass

    result['orientation'] = parts[2] if len(parts) > 2 else ''
    result['decoration'] = parts[3] if len(parts) > 3 else ''
    result['floor_desc'] = parts[4] if len(parts) > 4 else ''

    if len(parts) > 5:
        ym = re.search(r'(\d{4})年', parts[5])
        if ym:
            result['build_year'] = int(ym.group(1))

    if result['layout']:
        rm = re.search(r'(\d+)室', result['layout'])
        if rm: result['rooms'] = int(rm.group(1))
        hm = re.search(r'(\d+)厅', result['layout'])
        if hm: result['halls'] = int(hm.group(1))
        wm = re.search(r'(\d+)卫', result['layout'])
        if wm: result['bathrooms'] = int(wm.group(1))

    if result['floor_desc']:
        fm = re.search(r'(低层|中层|高层)', result['floor_desc'])
        if fm: result['floor_type'] = fm.group(1)
        fm2 = re.search(r'共(\d+)层', result['floor_desc'])
        if fm2: result['total_floors'] = int(fm2.group(1))

    return result


def parse_list_page(html):
    """解析链家列表页HTML"""
    soup = BeautifulSoup(html, 'lxml')
    items = soup.select('.sellListContent li')
    if not items:
        items = soup.select('li[data-housecode]')
    results = []

    for item in items:
        try:
            # ID
            a_tag = item.select_one('a[href*="/ershoufang/"]')
            if not a_tag:
                a_tag = item.find('a')
            href = a_tag.get('href', '') if a_tag else ''
            m_id = re.search(r'/ershoufang/(\d+)\.html', href)
            hid = m_id.group(1) if m_id else ''
            if not hid:
                continue

            # 标题
            title_el = item.select_one('.title a') or item.select_one('[title]')
            title = title_el.get_text(strip=True) if title_el else ''
            if not title:
                continue

            # 总价
            price_el = item.select_one('.totalPrice span') or item.select_one('.totalPrice')
            price_text = price_el.get_text(strip=True) if price_el else '0'
            try:
                total_price = float(re.sub(r'[^\d.]', '', price_text))
            except ValueError:
                continue

            if total_price <= 0:
                continue

            # 单价
            unit_el = item.select_one('.unitPrice span') or item.select_one('.unitPrice')
            unit_text = unit_el.get_text(strip=True) if unit_el else '0'
            try:
                unit_price = float(re.sub(r'[^\d.]', '', unit_text))
            except ValueError:
                unit_price = 0

            # 小区/商圈
            pos_els = item.select('.positionInfo a')
            community = pos_els[0].get_text(strip=True) if len(pos_els) >= 1 else ''
            biz_circle = pos_els[1].get_text(strip=True) if len(pos_els) >= 2 else ''

            # houseInfo
            info_el = item.select_one('.houseInfo')
            info_text = info_el.get_text(strip=True) if info_el else ''
            info_data = parse_house_info(info_text)

            results.append({
                'id': hid,
                'title': title,
                'total_price': total_price,
                'unit_price': unit_price,
                'community': community,
                'district': '',
                'address': biz_circle,
                'lng': 0, 'lat': 0,
                **info_data,
                'source': 'lianjia',
                'source_id': hid,
                'tags': '',
                'followers': 0,
            })
        except Exception:
            continue

    return results


# ============================================================
# 单区县爬取
# ============================================================

def crawl_district(code, name, max_pages=MAX_PAGES):
    """爬取链家一个区县的所有列表页

    链家是真分页，每页30条几乎无重叠，可以翻很深
    使用 Session 保持 Cookie 连续性
    """
    all_data = []
    seen_ids = set()
    checkpoint = load_checkpoint('lianjia_v2', code)
    pages_done = list(checkpoint.get('pages_done', []))
    completed = set(pages_done)

    if completed:
        print(f'  [{name}] 断点: {len(completed)}页已完成')

    consecutive_empty = 0
    prev_first_id = None

    # 使用 Session 保持 Cookie，同一区县用同一个代理IP
    session = requests.Session()
    init_cookies = parse_cookie_string(LIANJIA_COOKIE)
    for k, v in init_cookies.items():
        session.cookies.set(k, v)
    session.headers.update({
        'User-Agent': random.choice(USER_AGENTS_DESKTOP),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    })

    # 链家Cookie绑定IP，不用代理，直连
    # district_proxy = get_proxy()  # 不启用

    for page in range(1, max_pages + 1):
        if page in completed:
            continue

        url = f'https://cq.lianjia.com/ershoufang/{code}/pg{page}/'

        # 页间延迟
        if page > 1:
            delay = random.uniform(6, 12)
            time.sleep(delay)

        # Referer 模拟真实浏览路径
        session.headers['Referer'] = (
            f'https://cq.lianjia.com/ershoufang/{code}/pg{page-1}/'
            if page > 1 else 'https://cq.lianjia.com/ershoufang/'
        )

        # 请求列表页（重试时换代理）
        houses = None
        cur_page_empty = False

        for retry in range(4):
            if retry > 0:
                session.headers['User-Agent'] = random.choice(USER_AGENTS_DESKTOP)
                time.sleep(random.uniform(5, 10))

            try:
                resp = session.get(url, timeout=25)

                if resp.status_code == 404:
                    break
                if resp.status_code == 403 or resp.status_code == 302:
                    time.sleep(random.uniform(8, 15))
                    continue
                if resp.status_code != 200 or len(resp.text) < 5000:
                    continue

                houses = parse_list_page(resp.text)
                if not houses:
                    if page > 1:
                        cur_page_empty = True
                        break
                    continue

                # 缓存检测
                if page > 1 and houses:
                    first_id = houses[0].get('id', '')
                    if prev_first_id and first_id == prev_first_id and retry < 3:
                        time.sleep(random.uniform(3, 6))
                        continue

                prev_first_id = houses[0].get('id', '') if houses else prev_first_id
                break

            except Exception:
                time.sleep(random.uniform(3, 8))

        if cur_page_empty:
            break

        # ---- 处理结果 ----
        if houses is None or len(houses) == 0:
            consecutive_empty += 1
            if consecutive_empty >= 2:
                refresh_proxy_list()
            if consecutive_empty >= 3:
                print(f'  [{name}] 连续{consecutive_empty}页无数据，停止')
                break
            continue

        # 本区去重
        new_count = 0
        for h in houses:
            h['district'] = name
            h['fingerprint'] = make_lianjia_fingerprint(h)
            hid = h.get('id', '')
            if hid and hid not in seen_ids:
                seen_ids.add(hid)
                all_data.append(h)
                new_count += 1

        dup_info = f' (去重{len(houses)-new_count})' if len(houses) - new_count > 0 else ''
        print(f'  [{name}] pg{page}: {len(houses)}条 → 新增{new_count}条{dup_info}, '
              f'累计{len(all_data)}唯一')

        if len(houses) > 0:
            pages_done.append(page)
            save_checkpoint('lianjia_v2', code, pages_done)
            consecutive_empty = 0
        else:
            consecutive_empty += 1

        if consecutive_empty >= 3:
            break

    print(f'  [{name}] 完成: {len(pages_done)}页, {len(all_data)}条唯一')
    return all_data


# ============================================================
# 区县保存（线程安全 + CSV合并）
# ============================================================

def crawl_and_save(code, name):
    data = crawl_district(code, name)
    if data:
        out = os.path.join(OUTPUT_DIR, f'lianjia_{name}.csv')
        with WRITE_LOCK:
            existing = {}
            if os.path.exists(out):
                try:
                    with open(out, 'r', encoding='utf-8-sig') as f:
                        for row in csv_module.DictReader(f):
                            hid = row.get('id', '')
                            if hid and hid not in existing:
                                existing[hid] = row
                except Exception:
                    pass
            for h in data:
                hid = h.get('id', '')
                if hid:
                    existing[hid] = h
            merged = list(existing.values())
            save_csv(merged, out, LIANJIA_CSV_KEYS)
    return code, name, data


# ============================================================
# 主流程
# ============================================================

if __name__ == '__main__':
    proxy_count = refresh_proxy_list()
    print(f'链家爬虫 v2: {WORKERS}线程并行, 代理池{proxy_count}个, 页间5-10秒')
    print(f'覆盖区县: {len(LIANJIA_DISTRICTS)} 个 (链家仅覆盖主城区)')
    print(f'特性: 真分页(30条/页) | 私密代理轮换 | 断点续爬 | CSV合并')
    print()

    all_data = []
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {executor.submit(crawl_and_save, c, n): (c, n)
                   for c, n in LIANJIA_DISTRICTS}
        for future in as_completed(futures):
            c, n = futures[future]
            try:
                _, name, data = future.result()
                all_data.extend(data)
                done = len([f for f in futures if f.done()])
                print(f'>>> [{done}/{len(LIANJIA_DISTRICTS)}] {name}: '
                      f'{len(data)}条, 累计{len(all_data)}')
            except Exception as e:
                print(f'>>> [{n}] 异常: {e}')

    # 去重合并
    merged_path = os.path.join(OUTPUT_DIR, 'lianjia_all.csv')
    lj_all = []
    for c, n in LIANJIA_DISTRICTS:
        fpath = os.path.join(OUTPUT_DIR, f'lianjia_{n}.csv')
        if os.path.exists(fpath):
            try:
                with open(fpath, 'r', encoding='utf-8-sig') as f:
                    lj_all.extend(list(csv_module.DictReader(f)))
            except Exception:
                pass

    if lj_all:
        seen = set()
        unique = []
        for h in lj_all:
            fp = h.get('fingerprint', '')
            if fp and fp not in seen:
                seen.add(fp)
                unique.append(h)
        save_csv(unique, merged_path, LIANJIA_CSV_KEYS)
        print(f'\n链家总计: {len(lj_all)}条, 去重后{len(unique)}条 → {merged_path}')
