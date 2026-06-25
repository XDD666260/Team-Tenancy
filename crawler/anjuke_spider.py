# ============================================================
# 安居客二手房爬虫 — PC站 + Cookie + 指数退避 + 断点续爬
# 与链家爬虫互补，两源数据合并去重
# ============================================================

import sys
import os
import re
import time
import random

# 确保项目根目录在 sys.path 中，支持直接 python crawler/xxx.py 运行
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bs4 import BeautifulSoup

from crawler.utils import (
    ANJUKE_COOKIE, ANJUKE_DISTRICTS,
    USER_AGENTS_DESKTOP, BASE_HEADERS_DESKTOP,
    OUTPUT_DIR, CHECKPOINT_DIR, ANJUKE_CSV_KEYS,
    create_session, refresh_session, safe_get,
    make_anjuke_fingerprint,
    load_checkpoint, save_checkpoint,
    save_csv, deduplicate_and_save,
)

# ============================================================
# 房源解析（PC站 .property-content 卡片）
# ============================================================

def parse_house_info(item):
    """解析安居客PC站房源卡片

    安居客 .property-content-info 内多个 .property-content-info-text p：
      p[0] = 3室2厅2卫（每字符 span 包裹）
      p[1] = 122.25m²
      p[2] = 南
      p[3] = 高层(共18层)
      p[4] = 2005年建造
    .property-content-info-comm-address p = 详细地址
    """
    house = {}

    # --- 标题 ---
    try:
        title_el = item.select_one('.property-content-title-name')
        house['title'] = title_el.get_text(strip=True) if title_el else ''
    except Exception:
        house['title'] = ''

    # --- 总价 ---
    try:
        price_el = item.select_one('.property-price-total-num')
        price_text = price_el.get_text(strip=True) if price_el else '0'
        house['total_price'] = float(re.sub(r'[^\d.]', '', price_text)) if price_text else 0
    except Exception:
        house['total_price'] = 0

    # --- 单价 ---
    try:
        unit_el = item.select_one('.property-price-average')
        unit_text = unit_el.get_text(strip=True) if unit_el else '0'
        house['unit_price'] = float(re.sub(r'[^\d.]', '', unit_text)) if unit_text else 0
    except Exception:
        house['unit_price'] = 0

    # --- 小区名称 ---
    try:
        comm_el = item.select_one('.property-content-info-comm-name')
        house['community'] = comm_el.get_text(strip=True) if comm_el else ''
    except Exception:
        house['community'] = ''

    # --- 详细地址（列表页就有） ---
    try:
        addr_el = item.select_one('.property-content-info-comm-address')
        house['address'] = addr_el.get_text(strip=True) if addr_el else ''
    except Exception:
        house['address'] = ''

    # --- 户型/面积/朝向/楼层/年代 ---
    # 页面有两个 .property-content-info div：
    #   第1个（无额外class）包含 .property-content-info-text（p标签）
    #   第2个（.property-content-info-comm）包含小区名和地址
    try:
        info_ps = item.select('.property-content-info:not(.property-content-info-comm) > .property-content-info-text')
        info_texts = [p.get_text(strip=True) for p in info_ps]

        # p[0] = 户型原文 "3室2厅2卫"
        layout = info_texts[0] if len(info_texts) > 0 else ''
        house['layout'] = layout
        house['rooms'] = house['halls'] = house['bathrooms'] = 0
        if layout:
            rm = re.search(r'(\d+)室', layout)
            if rm: house['rooms'] = int(rm.group(1))
            hm = re.search(r'(\d+)厅', layout)
            if hm: house['halls'] = int(hm.group(1))
            wm = re.search(r'(\d+)卫', layout)
            if wm: house['bathrooms'] = int(wm.group(1))

        # p[1] = 面积 "122.25m²"
        house['area'] = 0
        if len(info_texts) > 1:
            area_str = info_texts[1].replace('m²', '').replace('㎡', '').replace('平米', '').strip()
            try:
                house['area'] = float(area_str)
            except ValueError:
                pass

        # p[2] = 朝向
        house['orientation'] = info_texts[2] if len(info_texts) > 2 else ''

        # p[3] = 楼层 "高层(共18层)"
        floor_desc = info_texts[3] if len(info_texts) > 3 else ''
        house['floor_desc'] = floor_desc
        house['floor_type'] = ''
        house['total_floors'] = 0
        if floor_desc:
            fm_type = re.search(r'(低层|中层|高层)', floor_desc)
            if fm_type: house['floor_type'] = fm_type.group(1)
            fm_total = re.search(r'共(\d+)层', floor_desc)
            if fm_total: house['total_floors'] = int(fm_total.group(1))

        # p[4] = 建成年代 "2005年建造"
        house['build_year'] = 0
        if len(info_texts) > 4:
            bm = re.search(r'(\d+)年建造', info_texts[4])
            if bm: house['build_year'] = int(bm.group(1))
    except Exception:
        house['layout'] = house.get('layout', '')
        house.setdefault('rooms', 0)
        house.setdefault('halls', 0)
        house.setdefault('bathrooms', 0)
        house.setdefault('area', 0)
        house.setdefault('orientation', '')
        house.setdefault('floor_desc', '')
        house.setdefault('floor_type', '')
        house.setdefault('total_floors', 0)
        house.setdefault('build_year', 0)

    # --- 默认值 ---
    house.setdefault('id', '')
    house.setdefault('tags', '')
    house.setdefault('decoration', '')
    house.setdefault('lng', 0)
    house.setdefault('lat', 0)
    house.setdefault('followers', 0)
    house.setdefault('source', 'anjuke')

    return house


# ============================================================
# 详情页补充字段
# ============================================================

def get_anjuke_detail(session, house_id, timeout=15):
    """访问安居客详情页，获取装修和经纬度

    返回 {'decoration': str, 'lng': float, 'lat': float}
    """
    result = {'decoration': '', 'lng': 0, 'lat': 0}

    url = f'https://chongqing.anjuke.com/prop/view/{house_id}'
    try:
        resp, _ = safe_get(session, url,
                           referer='https://chongqing.anjuke.com/sale/',
                           timeout=timeout, max_retries=2)
    except Exception:
        return result

    if resp.status_code != 200:
        return result

    soup = BeautifulSoup(resp.text, 'lxml')

    # 装修：.maininfo-model-weak 中包含"装"字的元素
    try:
        model_weaks = soup.select('.maininfo-model-weak')
        for el in model_weaks:
            text = el.get_text(strip=True)
            if '装' in text:
                result['decoration'] = text
                break
    except Exception:
        pass

    # 经纬度：<meta name="location" content="...;coord=106.526422,29.547963">
    try:
        meta = soup.select_one('meta[name="location"]')
        if meta:
            content = meta.get('content', '')
            m = re.search(r'coord=([\d.]+),([\d.]+)', content)
            if m:
                result['lng'] = float(m.group(1))
                result['lat'] = float(m.group(2))
    except Exception:
        pass

    return result


# ============================================================
# 区县爬取
# ============================================================

def crawl_district(code, name, max_pages=50, resume=True, fetch_details=True):
    """爬取一个区县，支持断点续爬和自动容错

    Args:
        code: 安居客区县拼音编码
        name: 中文名
        max_pages: 最大爬取页数
        resume: 是否断点续爬
        fetch_details: 是否进详情页获取装修和经纬度

    Returns:
        list[dict]: 房源数据列表
    """
    all_data = []
    session = create_session(ANJUKE_COOKIE, USER_AGENTS_DESKTOP, BASE_HEADERS_DESKTOP)

    # 加载断点
    checkpoint = load_checkpoint('anjuke', code) if resume else {}
    pages_done = list(checkpoint.get('pages_done', []))
    pages_failed = list(checkpoint.get('pages_failed', []))
    completed_pages = set(pages_done)

    if completed_pages:
        print(f'  [CP] 检测到断点: 已完成 {len(completed_pages)} 页，'
              f'从第 {max(completed_pages) + 1} 页继续')

    for page in range(1, max_pages + 1):
        # 跳过已完成页
        if page in completed_pages:
            print(f'\n--- [{name}] 第{page}页 (已爬，跳过) ---')
            continue

        # 构建 URL
        if page == 1:
            url = f'https://chongqing.anjuke.com/sale/{code}/'
            referer = 'https://chongqing.anjuke.com/sale/'
        else:
            url = f'https://chongqing.anjuke.com/sale/{code}/p{page}/'
            referer = f'https://chongqing.anjuke.com/sale/{code}/p{page - 1}/'

        print(f'\n--- [{name}] 第{page}/{max_pages}页 ---')

        # 自适应延迟
        if page > 1:
            if page <= 10:
                base_delay = random.uniform(3, 6)
            elif page <= 30:
                base_delay = random.uniform(5, 10)
            elif page <= 50:
                base_delay = random.uniform(8, 15)
            else:
                base_delay = random.uniform(12, 25)
            delay = base_delay * random.uniform(0.7, 1.3)
            print(f'  [T] 等待 {delay:.1f}s ...')
            time.sleep(delay)

        # 请求页面
        try:
            resp, session = safe_get(session, url, referer=referer, timeout=20)
        except Exception as e:
            print(f'  [ERR] 页面请求最终失败: {type(e).__name__}: {e}')
            pages_failed.append(page)
            save_checkpoint('anjuke', code, pages_done, pages_failed)
            session = refresh_session(session)
            continue

        print(f'  状态码: {resp.status_code}  长度: {len(resp.text)}')

        # 状态码异常处理
        if resp.status_code == 404:
            print(f'  404 — 没有更多页面，停止')
            break
        if resp.status_code == 403:
            print(f'  403 — 被禁止访问，冷却后继续...')
            time.sleep(random.uniform(30, 60))
            session = refresh_session(session)
            continue
        if resp.status_code != 200:
            print(f'  状态码 {resp.status_code}，尝试下一页...')
            session = refresh_session(session)
            continue

        # 空页面判断
        if len(resp.text) < 2000:
            print(f'  响应内容过短({len(resp.text)})，可能被拦截，冷却后重试...')
            time.sleep(random.uniform(20, 40))
            session = refresh_session(session)
            try:
                resp, session = safe_get(session, url, referer=referer, timeout=20)
            except Exception:
                print(f'  重试仍失败，跳过此页')
                continue
            if len(resp.text) < 2000:
                print(f'  确认无数据，停止翻页')
                break

        # 解析
        soup = BeautifulSoup(resp.text, 'lxml')

        items = soup.select('.property-content')
        if not items:
            items = soup.select('li[class*=property]')
        if not items:
            items = soup.select('.list-item')

        print(f'  找到 {len(items)} 个房源卡片')

        # 第一页无结果 — 保存调试页面
        if not items and page == 1:
            debug_path = os.path.join(OUTPUT_DIR, f'debug_anjuke_{code}_p1.html')
            with open(debug_path, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(resp.text)
            print(f'  已保存调试文件: {debug_path}')

        page_count = 0
        for item in items:
            house = parse_house_info(item)
            if not house.get('title') or house.get('total_price', 0) <= 0:
                continue

            house['district'] = name

            # 从包裹的 <a> 标签提取房源ID → 进详情页
            if fetch_details:
                parent_a = item.find_parent('a')
                if not parent_a:
                    parent_a = item.parent if item.parent and item.parent.name == 'a' else None
                if parent_a:
                    href = parent_a.get('href', '')
                    m_id = re.search(r'/prop/view/(S\d+)', href)
                    if m_id:
                        house_id = m_id.group(1)
                        detail = get_anjuke_detail(session, house_id)
                        if detail.get('decoration'):
                            house['decoration'] = detail['decoration']
                        if detail.get('lng'):
                            house['lng'] = detail['lng']
                            house['lat'] = detail['lat']
                        time.sleep(random.uniform(0.8, 1.5))

            house['fingerprint'] = make_anjuke_fingerprint(house)
            all_data.append(house)
            page_count += 1

        print(f'  [{name}] 本页有效 {page_count} 条，累计 {len(all_data)} 条')

        # 保存断点
        if page_count > 0:
            pages_done.append(page)
            save_checkpoint('anjuke', code, pages_done, pages_failed)
        elif len(resp.text) < 10000:
            print(f'  [WARN] 页面过短({len(resp.text)}B)，疑似拦截页，不保存断点')

        # 每 10 页重建 session
        if page % 10 == 0 and page > 0:
            session = refresh_session(session)

        # 空页面停止
        if len(items) == 0 and page_count == 0:
            print(f'  页面无房源，停止翻页')
            if page == 1:
                cp_path = os.path.join(CHECKPOINT_DIR, f'anjuke_{code}.json')
                if os.path.exists(cp_path):
                    os.remove(cp_path)
                    print(f'  已清除旧断点: {cp_path}')
            break

    # 报告
    if pages_failed:
        print(f'\n  [WARN] [{name}] 失败页: {pages_failed}（已跳过）')
    print(f'  [OK] [{name}] 完成：成功 {len(pages_done)} 页，共 {len(all_data)} 条')

    return all_data


# ============================================================
# 主流程
# ============================================================

if __name__ == '__main__':
    all_houses = []

    for code, name in ANJUKE_DISTRICTS:
        print(f'\n{"=" * 50}')
        print(f'开始爬取安居客 {name}...')
        print(f'{"=" * 50}')

        data = crawl_district(code, name, max_pages=150, resume=True)
        all_houses.extend(data)

        # 每区保存
        if data:
            output_path = os.path.join(OUTPUT_DIR, f'anjuke_{name}.csv')
            save_csv(data, output_path, ANJUKE_CSV_KEYS)
            print(f'  已保存 {output_path}')

        # 区间冷却
        wait = random.uniform(5, 12)
        print(f'  区间冷却 {wait:.1f}s ...')
        time.sleep(wait)

    # 汇总去重
    print(f'\n{"=" * 50}')
    print(f'安居客全部完成！共 {len(all_houses)} 条')
    print(f'{"=" * 50}')

    if all_houses:
        merged_path = os.path.join(OUTPUT_DIR, 'anjuke_all.csv')
        unique, count = deduplicate_and_save(all_houses, merged_path, ANJUKE_CSV_KEYS)
        print(f'去重后 {count} 条 → {merged_path}')
