# ============================================================
# 链家二手房爬虫 — 基于列表页HTML解析
# 加固版：指数退避重试 / Session自愈 / UA轮换 / 断点续爬 / 自适应延迟
# ============================================================

import sys
import os
import re
import time
import random

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bs4 import BeautifulSoup

from crawler.utils import (
    LIANJIA_COOKIE, LIANJIA_DISTRICTS,
    USER_AGENTS_DESKTOP, BASE_HEADERS_DESKTOP,
    OUTPUT_DIR, CHECKPOINT_DIR, LIANJIA_CSV_KEYS,
    create_session, refresh_session, safe_get,
    make_lianjia_fingerprint,
    load_checkpoint, save_checkpoint,
    save_csv,
)


# ============================================================
# 房源信息解析
# ============================================================

def parse_house_info(info_text):
    """解析链家 houseInfo 字段

    格式: "3室2厅|122.25平米|南|精装|高楼层(共18层)|2005年建"
    """
    parts = [p.strip() for p in info_text.split('|')]
    result = {
        'layout': parts[0] if len(parts) > 0 else '',
        'area': 0,
        'orientation': parts[2] if len(parts) > 2 else '',
        'decoration': parts[3] if len(parts) > 3 else '',
        'floor_desc': parts[4] if len(parts) > 4 else '',
        'rooms': 0, 'halls': 0, 'bathrooms': 0,
        'floor_type': '', 'total_floors': 0,
    }

    # 面积
    if len(parts) > 1:
        area_str = parts[1].replace('平米', '').replace('㎡', '').strip()
        try:
            result['area'] = float(area_str)
        except ValueError:
            pass

    # 户型解析
    if result['layout']:
        m = re.search(r'(\d+)室', result['layout'])
        if m: result['rooms'] = int(m.group(1))
        m = re.search(r'(\d+)厅', result['layout'])
        if m: result['halls'] = int(m.group(1))
        m = re.search(r'(\d+)卫', result['layout'])
        if m: result['bathrooms'] = int(m.group(1))

    # 楼层解析
    if result['floor_desc']:
        m = re.search(r'(低层|中层|高层)', result['floor_desc'])
        if m: result['floor_type'] = m.group(1)
        m = re.search(r'共(\d+)层', result['floor_desc'])
        if m: result['total_floors'] = int(m.group(1))

    return result


# ============================================================
# 详情页获取（可选，用于获取经纬度和建造年代等列表页缺失字段）
# 注意：频繁访问详情页容易触发链家风控，仅按需使用
# ============================================================

def get_detail_page(house_id, district_name):
    """访问详情页，获取完整数据（带重试）。

    注意: 此函数会产生额外请求，建议优先使用列表页数据，
    仅在需要经纬度/建造年代时调用。使用独立 Session 避免关联。
    """
    url = f'https://cq.lianjia.com/ershoufang/{house_id}.html'
    detail_session = create_session(LIANJIA_COOKIE, USER_AGENTS_DESKTOP, BASE_HEADERS_DESKTOP)

    try:
        resp, _ = safe_get(detail_session, url, timeout=15, max_retries=2)
    except Exception:
        return {}

    if resp.status_code != 200:
        return {}

    soup = BeautifulSoup(resp.text, 'lxml')

    try:
        total_el = soup.select_one('.total')
        total_price = float(total_el.get_text(strip=True).replace('万', '')) if total_el else 0

        unit_el = soup.select_one('.unitPriceValue')
        unit_text = unit_el.get_text(strip=True) if unit_el else '0'
        unit_price = float(re.sub(r'[^\d.]', '', unit_text)) if unit_text else 0

        community_el = soup.select_one('.communityName .info')
        community = community_el.get_text(strip=True) if community_el else ''

        info_el = soup.select_one('.houseInfo .content')
        info_text = info_el.get_text(strip=True) if info_el else ''
        info_data = parse_house_info(info_text)

        # 区县：从 .areaName .info a 中提取（第2个是区县级）
        area_els = soup.select('.areaName .info a')
        district = area_els[1].get_text(strip=True) if len(area_els) >= 2 else district_name

        # 详细地址
        addr_spans = soup.select('.areaName .info')
        address = ''.join(s.get_text(strip=True) for s in addr_spans)

        # 经纬度
        lng, lat = 0, 0
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and 'resblock' in script.string:
                m_lng = re.search(r'"longitude":\s*([\d.]+)', script.string)
                m_lat = re.search(r'"latitude":\s*([\d.]+)', script.string)
                if m_lng: lng = float(m_lng.group(1))
                if m_lat: lat = float(m_lat.group(1))
                break

        # 建造年代
        build_year = 0
        for script in scripts:
            if script.string and 'buildYear' in script.string:
                m = re.search(r'"buildYear":\s*"(\d+)"', script.string)
                if m: build_year = int(m.group(1))
                break

        return {
            'id': house_id,
            'title': soup.select_one('h1').get_text(strip=True) if soup.select_one('h1') else '',
            'total_price': total_price,
            'unit_price': unit_price,
            'community': community,
            'district': district,
            'address': address,
            'lng': lng,
            'lat': lat,
            **info_data,
            'build_year': build_year,
            'source': 'lianjia',
        }
    except Exception:
        return {}


# ============================================================
# 区县爬取（列表页直接解析，不访问详情页）
# ============================================================

def crawl_district(code, name, max_pages=50, resume=True):
    """爬取一个区县的列表页，直接解析全部字段"""
    all_data = []
    session = create_session(LIANJIA_COOKIE, USER_AGENTS_DESKTOP, BASE_HEADERS_DESKTOP)
    done_ids = set()  # 本轮去重

    checkpoint = load_checkpoint('lianjia', code) if resume else {}
    pages_done = list(checkpoint.get('pages_done', []))
    completed_pages = set(pages_done)

    if completed_pages:
        print(f'  [CP] 断点: 已完成 {len(completed_pages)} 页，'
              f'从第 {max(completed_pages) + 1} 页继续')

    for page in range(1, max_pages + 1):
        if page in completed_pages:
            continue

        url = f'https://cq.lianjia.com/ershoufang/{code}/pg{page}/'
        print(f'\n--- [{name}] 第{page}/{max_pages}页 ---')

        # 极度保守延迟：链家风控比安居客更严格
        if page > 1:
            if page == 2:
                base_delay = random.uniform(90, 150)
            elif page <= 5:
                base_delay = random.uniform(60, 90)
            elif page <= 15:
                base_delay = random.uniform(45, 75)
            elif page <= 30:
                base_delay = random.uniform(35, 60)
            else:
                base_delay = random.uniform(30, 50)
            delay = base_delay * random.uniform(0.7, 1.3)
            print(f'  [T] 等待 {delay:.1f}s ...')
            time.sleep(delay)

        # 每 3 页后长休息（模拟离开电脑）
        if page > 1 and page % 3 == 0:
            rest = random.uniform(60, 180)
            print(f'  [REST] 长休息 {rest:.0f}s ...')
            time.sleep(rest)

        # 请求列表页
        referer = (f'https://cq.lianjia.com/ershoufang/{code}/pg{page - 1}/'
                   if page > 1
                   else f'https://cq.lianjia.com/ershoufang/{code}/')

        try:
            resp, session = safe_get(session, url, referer=referer, timeout=20)
        except Exception as e:
            print(f'  [ERR] 列表页请求失败: {type(e).__name__}')
            continue

        print(f'  状态码: {resp.status_code}  长度: {len(resp.text)}')

        if resp.status_code == 404:
            print(f'  404 — 没有更多页面')
            break
        if resp.status_code == 403:
            print(f'  403 — 被禁止，长冷却后继续...')
            time.sleep(random.uniform(30, 60))
            session = refresh_session(session)
            continue
        if resp.status_code != 200 or len(resp.text) < 2000:
            print(f'  列表页失败')
            if len(resp.text) < 2000:
                time.sleep(random.uniform(20, 40))
                session = refresh_session(session)
                continue
            break

        # 解析列表页
        soup = BeautifulSoup(resp.text, 'lxml')
        items = soup.select('.sellListContent li')
        if not items:
            items = soup.select('.sellListContent .info')
        if not items:
            items = soup.select('a[href*="/ershoufang/"]')
            items = [it for it in items
                     if re.search(r'/ershoufang/\d+\.html', it.get('href', ''))]

        if not items:
            print(f'  未找到房源，停止翻页')
            if page == 1:
                print(f'  页面无房源(长度{len(resp.text)}B)')
            break

        print(f'  找到 {len(items)} 个房源条目')

        page_count = 0
        for item in items:
            try:
                # 提取链接中的ID
                a_tag = item.select_one('a[href*="/ershoufang/"]') if item.name != 'a' else item
                if not a_tag or a_tag.name != 'a':
                    a_tag = item.find('a')
                href = a_tag.get('href', '') if a_tag else ''
                m_id = re.search(r'/ershoufang/(\d+)\.html', href)
                hid = m_id.group(1) if m_id else ''

                # 去重
                if hid and hid in done_ids:
                    continue

                # 标题
                title_el = item.select_one('.title a') or item.select_one('a[title]')
                title = title_el.get_text(strip=True) if title_el else ''

                # 总价
                price_el = item.select_one('.totalPrice span') or item.select_one('.totalPrice')
                price_text = price_el.get_text(strip=True) if price_el else '0'
                try:
                    total_price = float(re.sub(r'[^\d.]', '', price_text))
                except ValueError:
                    total_price = 0

                # 单价
                unit_el = item.select_one('.unitPrice span') or item.select_one('.unitPrice')
                unit_text = unit_el.get_text(strip=True) if unit_el else '0'
                try:
                    unit_price = float(re.sub(r'[^\d.]', '', unit_text))
                except ValueError:
                    unit_price = 0

                # 小区 / 商圈
                pos_els = item.select('.positionInfo a')
                community = pos_els[0].get_text(strip=True) if len(pos_els) >= 1 else ''
                biz_circle = pos_els[1].get_text(strip=True) if len(pos_els) >= 2 else ''

                # 户型/面积/朝向/装修/楼层
                info_el = item.select_one('.houseInfo')
                info_text = info_el.get_text(strip=True) if info_el else ''
                info_data = parse_house_info(info_text)

                if not title or total_price <= 0:
                    continue

                data = {
                    'id': hid,
                    'title': title,
                    'total_price': total_price,
                    'unit_price': unit_price,
                    'community': community,
                    'district': name,
                    'address': biz_circle,
                    'lng': 0, 'lat': 0,
                    **info_data,
                    'build_year': 0,
                    'source': 'lianjia',
                    'source_id': hid,
                }

                # 生成指纹（新增！）
                data['fingerprint'] = make_lianjia_fingerprint(data)

                all_data.append(data)
                if hid:
                    done_ids.add(hid)
                page_count += 1

            except Exception:
                continue

        print(f'  [{name}] 本页有效 {page_count} 条，累计 {len(all_data)} 条')

        if page_count > 0:
            pages_done.append(page)
            save_checkpoint('lianjia', code, pages_done)
        elif len(resp.text) < 10000:
            print(f'  [WARN] 页面过短({len(resp.text)}B)，疑似拦截，不保存断点')

        # 每5页刷session
        if page % 5 == 0:
            session = refresh_session(session)

        if page_count == 0 and page > 1:
            break

    print(f'  [OK] [{name}] 完成：{len(pages_done)} 页，共 {len(all_data)} 条')
    return all_data


# ============================================================
# 主流程
# ============================================================

if __name__ == '__main__':
    all_houses = []

    for code, name in LIANJIA_DISTRICTS:
        print(f'\n{"=" * 50}')
        print(f'开始爬取链家 {name}...')
        print(f'{"=" * 50}')

        data = crawl_district(code, name, max_pages=80, resume=True)
        all_houses.extend(data)

        output_path = os.path.join(OUTPUT_DIR, f'lianjia_{name}.csv')
        if data:
            save_csv(data, output_path, LIANJIA_CSV_KEYS)

        print(f'\n>>> {name}完成，本区{len(data)}条，累计{len(all_houses)}条')

        wait = random.uniform(5, 12)
        print(f'  区间冷却 {wait:.1f}s ...')
        time.sleep(wait)

    print(f'\n{"=" * 50}')
    print(f'链家全部完成！共 {len(all_houses)} 条')
    print(f'{"=" * 50}')
