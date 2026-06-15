# ============================================================
# 安居客缺失区县爬虫 v2 — PC站 + Cookie + 直接连接
# 说明: 66daili免费代理不支持HTTPS穿透, 故改用直接连接+Cookie
#       实测直接连接 + Cookie 可稳定访问安居客PC站
# ============================================================

import sys
import io
# 修复Windows控制台GBK编码问题（仅在交互终端时生效）
if sys.platform == 'win32' and hasattr(sys.stdout, 'buffer') and sys.stdout.buffer:
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except (ValueError, AttributeError):
        pass

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import re
import csv
import os
import time
import random
import hashlib
import json
from bs4 import BeautifulSoup

# ==================== Cookie（从浏览器复制，过期需更新） ====================
COOKIE_STRING = """aQQ_ajkguid=F7B4D023-2524-4E8F-9FA7-FB4B466A414A; sessid=0ADC5D26-DE20-42FC-B1C9-C3DF9A7CCDFF; ajk-appVersion=; ctid=20; id58=uVcyWmonw3RqSxvUFwlTAg==; xxzlclientid=9e9f197b-4ac8-4fe0-b525-1780990835353; xxzlxxid=pfmx9YPrZMngaMg5IB8XhLUfiXG951fL3E4v4TYV7zQvgVqboAu0QQrrHcrCK6A494Dv; fzq_h=a0aac02a0d5f6990093f2ca9da7a4d64_1781527616283_330b581300e948bcaf5c7bd0f9862a5d_47901724934875746904071831303115791755; twe=2; obtain_by=1; xxzlbbid=pfmbREFo2urLhMWmZMEGU/Bwz1Q8xv58iE8STQVPF67vy4LzZv60YXPhcPE7oQPfnRXDqZwvZKTG2Q432Tn22Cvldx6veGZQ1DRcLWT4nMjv9ZUQ2Mj+Cq6AbZP4gAvZPCv10KGDQ/YxNzgxNTI4MzIwMTQyODI0_1; fzq_js_anjuke_ershoufang_pc=37a80981d01b212699fb5f2491586993_1781528328943_23"""


def parse_cookies(s):
    cookies = {}
    for item in s.replace('\n', '').replace('\r', '').split(';'):
        item = item.strip()
        if '=' in item:
            k, v = item.split('=', 1)
            cookies[k] = v
    return cookies


COOKIES = parse_cookies(COOKIE_STRING)

# ==================== UA 轮换池 ====================
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15',
]

BASE_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.3',
    'Accept-Encoding': 'gzip, deflate, br',
    'Cache-Control': 'max-age=0',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
}

# ==================== 目标: 8个缺失区县 ====================
MISSING_DISTRICTS = [
    ('wulongxian',      '武隆区'),
    ('cqwushanxian',    '巫山县'),
    ('chengkouxian',    '城口县'),
    ('fengduxian',      '丰都县'),
]

# ==================== 路径 ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, '..', 'data', 'raw')
CHECKPOINT_DIR = os.path.join(BASE_DIR, '..', 'data', 'checkpoints')
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CHECKPOINT_DIR, exist_ok=True)

# CSV字段（与 anjuke_fast.py 一致）
CSV_KEYS = [
    'id', 'title', 'total_price', 'unit_price', 'community', 'district',
    'address', 'lng', 'lat', 'layout', 'rooms', 'halls', 'bathrooms',
    'area', 'orientation', 'decoration', 'floor_desc', 'floor_type',
    'total_floors', 'build_year', 'tags', 'source', 'fingerprint'
]


# ==================== Session 工厂 ====================
def create_session():
    session = requests.Session()
    retry_strategy = Retry(
        total=2,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=1, pool_maxsize=1)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(BASE_HEADERS)
    session.headers['User-Agent'] = random.choice(USER_AGENTS)
    session.cookies.update(COOKIES)
    return session


def refresh_session(old_session):
    try:
        old_session.close()
    except Exception:
        pass
    time.sleep(random.uniform(3, 6))
    return create_session()


# ==================== 安全请求 (直接连接, 指数退避) ====================
def safe_get(session, url, referer='', timeout=25, max_retries=4):
    headers = {}
    if referer:
        headers['Referer'] = referer

    for attempt in range(max_retries):
        try:
            resp = session.get(url, headers=headers, timeout=timeout)

            # 检查反爬
            if len(resp.text) < 2000:
                print(f'  [WARN] 响应过短({len(resp.text)}B), 可能被拦截')
                if attempt < max_retries - 1:
                    wait = (2 ** attempt) * 5 + random.uniform(0, 5)
                    print(f'  [Retry] {wait:.1f}s后重试...')
                    time.sleep(wait)
                    session = refresh_session(session)
                    continue
                else:
                    return resp, session

            if '访问验证' in resp.text or '安全验证' in resp.text or 'antibot' in resp.text.lower() or 'xxzlGatewayUrl' in resp.text:
                print(f'  [WARN] 触发验证码, 冷却重试...')
                if attempt < max_retries - 1:
                    wait = random.uniform(30, 60)
                    time.sleep(wait)
                    session = refresh_session(session)
                    continue

            return resp, session

        except (requests.ConnectionError, requests.Timeout,
                requests.exceptions.ChunkedEncodingError) as e:
            if attempt < max_retries - 1:
                wait = (2 ** attempt) * 3 + random.uniform(0, 3)
                print(f'  [WARN] [{type(e).__name__}] {wait:.1f}s后重试 ({attempt+1}/{max_retries-1})...')
                time.sleep(wait)
                session = refresh_session(session)
            else:
                print(f'  [ERR] 重试{max_retries}次后仍失败: {type(e).__name__}')
                raise

        except requests.RequestException as e:
            print(f'  [ERR] 请求异常 [{type(e).__name__}]: {e}')
            raise

    return None, session


# ==================== PC站列表页解析 (来自anjuke_spider.py) ====================
def parse_house_info(item):
    """解析安居客PC站房源卡片"""
    house = {}

    try:
        # 标题
        title_el = item.select_one('.property-content-title-name')
        house['title'] = title_el.get_text(strip=True) if title_el else ''

        # 总价
        price_el = item.select_one('.property-price-total-num')
        price_text = price_el.get_text(strip=True) if price_el else '0'
        house['total_price'] = float(re.sub(r'[^\d.]', '', price_text)) if price_text else 0

        # 单价
        unit_el = item.select_one('.property-price-average')
        unit_text = unit_el.get_text(strip=True) if unit_el else '0'
        house['unit_price'] = float(re.sub(r'[^\d.]', '', unit_text)) if unit_text else 0

        # 小区名称
        comm_el = item.select_one('.property-content-info-comm-name')
        house['community'] = comm_el.get_text(strip=True) if comm_el else ''

        # 详细地址
        addr_el = item.select_one('.property-content-info-comm-address')
        house['address'] = addr_el.get_text(strip=True) if addr_el else ''

        # 户型/面积/朝向/楼层/年代
        info_ps = item.select('.property-content-info:not(.property-content-info-comm) > .property-content-info-text')
        info_texts = [p.get_text(strip=True) for p in info_ps]

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

        house['area'] = 0
        if len(info_texts) > 1:
            area_str = info_texts[1].replace('m²', '').replace('㎡', '').replace('平米', '').strip()
            try:
                house['area'] = float(area_str)
            except ValueError:
                pass

        house['orientation'] = info_texts[2] if len(info_texts) > 2 else ''

        floor_desc = info_texts[3] if len(info_texts) > 3 else ''
        house['floor_desc'] = floor_desc
        house['floor_type'] = ''
        house['total_floors'] = 0
        if floor_desc:
            fm_type = re.search(r'(低层|中层|高层)', floor_desc)
            if fm_type: house['floor_type'] = fm_type.group(1)
            fm_total = re.search(r'共(\d+)层', floor_desc)
            if fm_total: house['total_floors'] = int(fm_total.group(1))

        house['build_year'] = 0
        if len(info_texts) > 4:
            bm = re.search(r'(\d+)年建造', info_texts[4])
            if bm: house['build_year'] = int(bm.group(1))

        # 从链接提取房源ID
        parent_a = item.find_parent('a')
        if not parent_a:
            parent_a = item.parent if item.parent and item.parent.name == 'a' else None
        house['id'] = ''
        if parent_a:
            href = parent_a.get('href', '')
            m_id = re.search(r'/prop/view/(S?\d+)', href)
            if m_id:
                house['id'] = m_id.group(1)

        # 默认值
        house['decoration'] = ''
        house['lng'] = house['lat'] = 0
        house['tags'] = ''
        house['source'] = 'anjuke'

    except Exception:
        pass

    return house


def make_fingerprint(house):
    key = f"{house.get('community','')}|{house.get('district','')}|{house.get('area',0)}|{house.get('rooms',0)}|{house.get('total_price',0)}"
    return hashlib.md5(key.encode()).hexdigest()


# ==================== 断点管理 ====================
def load_checkpoint(code):
    path = os.path.join(CHECKPOINT_DIR, f'anjuke_m_{code}.json')
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data.get('pages_done', [])
                return data
        except Exception:
            pass
    return []


def save_checkpoint(code, pages_done):
    path = os.path.join(CHECKPOINT_DIR, f'anjuke_m_{code}.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({'pages_done': list(pages_done)}, f, ensure_ascii=False)


# ==================== 区县爬取 ====================
def crawl_district(code, name, max_pages=100):
    """爬取一个区县的PC站列表页"""
    all_data = []
    session = create_session()

    pages_done = load_checkpoint(code)
    completed = set(pages_done)

    if completed:
        print(f'  [{name}] 断点续爬: {len(completed)} 页已完成')

    for page in range(1, max_pages + 1):
        if page in completed:
            continue

        if page == 1:
            url = f'https://chongqing.anjuke.com/sale/{code}/'
            referer = 'https://chongqing.anjuke.com/sale/'
        else:
            url = f'https://chongqing.anjuke.com/sale/{code}/p{page}/'
            referer = f'https://chongqing.anjuke.com/sale/{code}/p{page-1}/'

        # 自适应延迟
        if page > 1:
            # 超保守延迟：每页30-60秒，避免触发反爬
            base_delay = random.uniform(30, 60)
            delay = base_delay * random.uniform(0.8, 1.2)
            print(f'  [{name}] 页间冷却 {delay:.1f}s ...')
            time.sleep(delay)

        print(f'  [{name}] p{page}/{max_pages}: {url}')

        try:
            resp, session = safe_get(session, url, referer=referer)
        except Exception as e:
            print(f'  [{name}] p{page}: 请求失败 {type(e).__name__}, 跳过')
            continue

        if resp.status_code == 404:
            print(f'  [{name}] 404 — 没有更多页面')
            break
        if resp.status_code != 200:
            print(f'  [{name}] 状态码 {resp.status_code}, 跳过')
            session = refresh_session(session)
            continue

        # 解析
        soup = BeautifulSoup(resp.text, 'lxml')
        items = soup.select('.property-content')
        if not items:
            items = soup.select('.list-item')
        if not items:
            items = soup.select('li[class*=property]')

        page_count = 0
        for item in items:
            house = parse_house_info(item)
            if house.get('title') and house.get('total_price', 0) > 0:
                house['district'] = name
                house['fingerprint'] = make_fingerprint(house)
                all_data.append(house)
                page_count += 1

        print(f'  [{name}] p{page}: {page_count} 条, 累计 {len(all_data)} 条')

        if page_count > 0:
            pages_done.append(page)
            save_checkpoint(code, pages_done)

        # 每10页重建session
        if page % 10 == 0:
            session = refresh_session(session)

        # 连续空页停止
        if page_count == 0:
            if page == 1:
                debug_path = os.path.join(OUTPUT_DIR, f'debug_anjuke_{code}_p1.html')
                with open(debug_path, 'w', encoding='utf-8', errors='ignore') as f:
                    f.write(resp.text)
                print(f'  [{name}] 首页无房源, 调试文件: {debug_path}')
            else:
                print(f'  [{name}] 无房源, 停止翻页')
            break

    print(f'  [{name}] 完成: {len(pages_done)} 页, {len(all_data)} 条')
    return all_data


# ==================== CSV保存 ====================
def save_csv(name, data):
    if not data:
        return
    out_path = os.path.join(OUTPUT_DIR, f'anjuke_m_{name}.csv')
    with open(out_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_KEYS, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(data)
    print(f'  已保存: {out_path} ({len(data)} 条)')


# ==================== 主流程 ====================
if __name__ == '__main__':
    print('=' * 60)
    print('安居客缺失区县爬虫 v2 — PC站 + Cookie 直连')
    print(f'目标: {len(MISSING_DISTRICTS)} 个远郊区县')
    print('注意: 免费HTTP代理不支持HTTPS穿透, 改用直接连接')
    print('=' * 60)

    all_data = []
    success = 0
    failed = []

    for i, (code, name) in enumerate(MISSING_DISTRICTS):
        print(f'\n{"=" * 50}')
        print(f'[{i+1}/{len(MISSING_DISTRICTS)}] 开始爬取: {name} ({code})')
        print(f'{"=" * 50}')

        try:
            data = crawl_district(code, name, max_pages=100)
            if data:
                save_csv(name, data)
                all_data.extend(data)
                success += 1
                print(f'  [OK] {name}: {len(data)} 条')
            else:
                print(f'  [WARN] {name}: 未获取到数据')
                failed.append(name)

        except KeyboardInterrupt:
            print(f'\n[STOP] 用户中断，当前进度已保存')
            break
        except Exception as e:
            print(f'  [ERR] {name}: {type(e).__name__}: {e}')
            failed.append(name)
            import traceback
            traceback.print_exc()

        # 区县间冷却
        if i < len(MISSING_DISTRICTS) - 1:
            wait = random.uniform(8, 15)
            print(f'  区县间冷却 {wait:.1f}s ...')
            time.sleep(wait)

    # ==================== 汇总 ====================
    print(f'\n{"=" * 60}')
    print(f'爬取完成!')
    print(f'  成功: {success}/{len(MISSING_DISTRICTS)} 个区县')
    if failed:
        print(f'  失败: {failed}')
    print(f'  本次共获取: {len(all_data)} 条')
    print(f'{"=" * 60}')

    # 去重合并
    if all_data:
        seen = set()
        unique = []
        for h in all_data:
            fp = h.get('fingerprint', '')
            if fp and fp not in seen:
                seen.add(fp)
                unique.append(h)

        merged = os.path.join(OUTPUT_DIR, 'anjuke_m_missing_merged.csv')
        with open(merged, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=CSV_KEYS, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(unique)
        print(f'  去重合并: {len(unique)} 条 → {merged}')
