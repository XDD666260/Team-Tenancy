# 链家二手房爬虫 — 基于API JSON数据
# 加固版：指数退避重试 / Session自愈 / UA轮换 / 断点续爬 / 自适应延迟

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import re
import json
import csv
import os
import time
import random

# ===================== Cookie（从浏览器复制） =====================
COOKIE_STRING = """lianjia_uuid=84e647ad-44a3-4621-873d-fe484a1cfa17; Hm_lvt_46bf127ac9b856df503ec2dbf942b67e=1780982049; HMACCOUNT=807243DEB1481E17; _jzqc=1; _qzjc=1; _ga=GA1.2.115501286.1780982060; _ga_0VZPJRR5MM=GS2.2.s1780983078$o1$g0$t1780983078$j60$l0$h0; crosSdkDT2019DeviceId=lqz54m-h4glge-i7mgmroflq4zh3j-h60ivcfec; sensorsdata2015jssdkcross=%7B%22distinct_id%22%3A%2219eaacd69d9d7a-0d78c933abaac48-4c657b58-1474560-19eaacd69da2234%22%2C%22%24device_id%22%3A%2219eaacd69d9d7a-0d78c933abaac48-4c657b58-1474560-19eaacd69da2234%22%2C%22props%22%3A%7B%22%24latest_traffic_source_type%22%3A%22%E7%9B%B4%E6%8E%A5%E6%B5%81%E9%87%8F%22%2C%22%24latest_referrer%22%3A%22%22%2C%22%24latest_referrer_host%22%3A%22%22%2C%22%24latest_search_keyword%22%3A%22%E6%9C%AA%E5%8F%96%E5%88%B0%E5%80%BC_%E7%9B%B4%E6%8E%A5%E6%89%93%E5%BC%80%22%7D%7D; lianjia_ssid=963ff1ed-dbdc-4852-899c-5148f552f8f5; select_city=500000; _jzqckmp=1; login_ucid=2000000542622736; lianjia_token=2.0013f346814901ef7d025e6fb0380d5971; lianjia_token_secure=2.0013f346814901ef7d025e6fb0380d5971; security_ticket=CY2ijta5R/DD7ZkxwcOlg7E/DLFpkYjmorLtqBo8hg/11QK17HXphDglZ0mC5bUv3r7N3PG9jbhaKP2Il7ngX5zXO4RVzj1a1D+jcv8RCJekqRf5JIX+SvSDkNIj/J+VH0BGL+z5d1HQ10MY639BIvXQ3SZ+rDIZzdWon0jZAgg=; lfrc_=580a6bb9-8471-49fb-a448-f391eff97170; _gid=GA1.2.1172135501.1781084398; hip=caKTqctAa46S8IYpNU0ueLSbhHVzGKGH4MneBUD0AP8LVAuYhDibDTqT_dkuAhpoTntwnEv85MsbUa3Qn2QL6ex_WG2Bzo0UYqnOIePudUQNAnPyQwfrkOKw9KxIrsgd8UxdnKdIDahk-LCxHRRToZFhaqQWrjt-yg1Bk2IePNyVqE61R2Jgg3_BXHkObPuaGp_Ppw0DeMHDE0Kvv5SJciCq57X065lKby1YC6wXsbvNJd7YaYI--J5hLyw2Kw79DZZF0qY6A_2m_qmfr_Es8s3qlS18MFuSkCT0; _jzqa=1.1801755635432145400.1780982049.1781090560.1781097859.6; _jzqx=1.1780982049.1781097859.5.jzqsr=my%2Efeishu%2Ecn|jzqct=/.jzqsr=hip%2Elianjia%2Ecom|jzqct=/; _gat=1; _gat_global=1; _gat_new_global=1; _gat_dianpu_agent=1; _ga_PV625F3L95=GS2.2.s1781097871$o5$g0$t1781097871$j60$l0$h0; Hm_lpvt_46bf127ac9b856df503ec2dbf942b67e=1781097873; _jzqb=1.2.10.1781097859.1; srcid=eyJ0Ijoie1wiZGF0YVwiOlwiZGU3NmUzNjAyZmJhNzg3MGM1ZjQ1MDAxOTQ5NmMwNGY2OWM1NjJjZDFkZDI0YTBiYmM5YjE2OWQxY2UzYjkwYjBkYjNkZDU0NTllNzBjNzA1MjU2MDU0ODExYmJmYzQ4NjNiZDM4YjQwY2FhNjhlM2E5NGFhM2U4YmMwMWZkMTdjYWNmYWE2OTJjOThiNTExMmUzY2U4ZDFkYjhiMTI0OWRiNmI4MzdkZTgyNzVmYjczZTgxOWFhNjJlYWY5NjJiNWJiNDUxODQ5N2YwZjRiMDNkNjViYzk5YzQxMjllY2Q5OWI4YzU0MTkyMTY5MWI5NDUzNmQ3MjJkM2ZlYzJiYjFiYzlkYTI1ZTk5YjgyMjYyMzVjN2QyMDk3OWM0Mjg4OGFiMmZkNTQ0YWQxMDhiMjA4ODI2YjczODZhN2M0NzlcIixcImtleV9pZFwiOlwiMVwiLFwic2lnblwiOlwiNTg4ODhjNTRcIn0iLCJyIjoiaHR0cHM6Ly9jcS5saWFuamlhLmNvbS9lcnNob3VmYW5nLyIsIm9zIjoid2ViIiwidiI6IjAuMSJ9; _qzja=1.1859070309.1780982049166.1781090559684.1781097858507.1781097858507.1781097874123.0.0.0.72.6; _qzjb=1.1781097858507.2.0.0.0; _qzjto=9.3.0"""

cookies = {}
COOKIE_STRING = COOKIE_STRING.replace('\n', '').replace('\r', '')
for item in COOKIE_STRING.split(';'):
    item = item.strip()
    if '=' in item:
        k, v = item.split('=', 1)
        cookies[k] = v

# ===================== UA 轮换池 =====================
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15',
]

BASE_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.3',
    'Accept-Encoding': 'gzip, deflate, br',
}

# ===================== 区县列表 =====================
DISTRICTS = [
    ('liangjiangxinqu', '两江新区'),
    ('jiangjing', '江津区'),
    ('yuzhong', '渝中区'),
    ('nanan', '南岸区'),
    ('shapingba', '沙坪坝区'),
    ('jiulongpo', '九龙坡区'),
    ('dadukou', '大渡口区'),
    ('banan', '巴南区'),
    ('beibei', '北碚区'),
    ('kaizhouqu','开州区'),
    ('rongchangqu','荣昌区'),
    ('bishan','璧山'),
]

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw')
CHECKPOINT_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'checkpoints')
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CHECKPOINT_DIR, exist_ok=True)


# ===================== Session 工厂 =====================
def create_session():
    """创建一个带重试策略的新 Session"""
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
    session.cookies.update(cookies)

    return session


def refresh_session(old_session):
    """重建 Session"""
    print('  [Refresh] 重建 Session...')
    try:
        old_session.close()
    except:
        pass
    time.sleep(random.uniform(3, 6))
    return create_session()


# ===================== 安全请求 =====================
def safe_get(session, url, headers_extra=None, timeout=20, max_retries=3):
    """
    带指数退避的 GET 请求。
    返回 (response, new_session)
    """
    hdrs = {}
    if headers_extra:
        hdrs.update(headers_extra)

    for attempt in range(max_retries):
        try:
            resp = session.get(url, headers=hdrs, timeout=timeout)
            return resp, session

        except (requests.ConnectionError, requests.Timeout,
                requests.exceptions.ChunkedEncodingError) as e:
            err_name = type(e).__name__
            if attempt < max_retries - 1:
                base = (2 ** attempt) * 3
                jitter = random.uniform(0, base)
                wait = base + jitter
                print(f'  [WARN] [{err_name}] {e}')
                print(f'  [Retry] {wait:.1f}s后重试 ({attempt+1}/{max_retries-1})...')
                time.sleep(wait)
                session = refresh_session(session)
            else:
                print(f'  [ERR] 重试{max_retries}次后仍失败: {err_name}')
                raise

        except requests.RequestException as e:
            print(f'  [ERR] 请求异常 [{type(e).__name__}]: {e}')
            raise

    return None, session


# ===================== 房源解析 =====================
def parse_house_info(info_text):
    """解析 houseInfo 字段"""
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
    if len(parts) > 1:
        area_str = parts[1].replace('平米', '').replace('㎡', '').strip()
        try: result['area'] = float(area_str)
        except: pass
    if result['layout']:
        m = re.search(r'(\d+)室', result['layout'])
        if m: result['rooms'] = int(m.group(1))
        m = re.search(r'(\d+)厅', result['layout'])
        if m: result['halls'] = int(m.group(1))
        m = re.search(r'(\d+)卫', result['layout'])
        if m: result['bathrooms'] = int(m.group(1))
    if result['floor_desc']:
        m = re.search(r'(低层|中层|高层)', result['floor_desc'])
        if m: result['floor_type'] = m.group(1)
        m = re.search(r'共(\d+)层', result['floor_desc'])
        if m: result['total_floors'] = int(m.group(1))
    return result


def get_detail_page(house_id, district_name):
    """访问详情页，获取完整数据（带重试）"""
    url = f'https://cq.lianjia.com/ershoufang/{house_id}.html'

    # 详情页使用独立 session，避免关联
    detail_session = create_session()

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

        # 详细地址：拼接 .areaName 下所有 .info 的文本
        addr_spans = soup.select('.areaName .info')
        address = ''.join(s.get_text(strip=True) for s in addr_spans)

        lng, lat = 0, 0
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and 'resblock' in script.string:
                m_lng = re.search(r'"longitude":\s*([\d.]+)', script.string)
                m_lat = re.search(r'"latitude":\s*([\d.]+)', script.string)
                if m_lng: lng = float(m_lng.group(1))
                if m_lat: lat = float(m_lat.group(1))
                break

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


# ===================== 断点续爬 =====================
def load_checkpoint(code):
    cp_path = os.path.join(CHECKPOINT_DIR, f'lianjia_{code}.json')
    if os.path.exists(cp_path):
        with open(cp_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'pages_done': [], 'house_ids_done': []}


def save_checkpoint(code, pages_done, house_ids_done=None):
    cp_path = os.path.join(CHECKPOINT_DIR, f'lianjia_{code}.json')
    with open(cp_path, 'w', encoding='utf-8') as f:
        json.dump({
            'pages_done': pages_done,
            'house_ids_done': house_ids_done or []
        }, f, ensure_ascii=False)


# ===================== 区县爬取 =====================
def crawl_district(code, name, max_pages=50, resume=True):
    """爬取一个区县"""
    all_data = []
    session = create_session()
    pages_done = []

    checkpoint = load_checkpoint(code) if resume else {}
    completed_pages = set(checkpoint.get('pages_done', []))
    done_ids = set(checkpoint.get('house_ids_done', []))

    if completed_pages:
        print(f'  [CP] 断点: 已完成 {len(completed_pages)} 页，{len(done_ids)} 个详情页')

    for page in range(1, max_pages + 1):
        if page in completed_pages:
            continue

        url = f'https://cq.lianjia.com/ershoufang/{code}/pg{page}/'
        print(f'\n--- [{name}] 第{page}/{max_pages}页 ---')

        # 自适应延迟
        if page > 1:
            if page <= 10:
                base_delay = random.uniform(3, 6)
            elif page <= 30:
                base_delay = random.uniform(5, 10)
            else:
                base_delay = random.uniform(8, 15)
            delay = base_delay * random.uniform(0.7, 1.3)
            print(f'  [T] 等待 {delay:.1f}s ...')
            time.sleep(delay)

            # 预热：先访问第1页模拟人类行为
            try:
                session.get(f'https://cq.lianjia.com/ershoufang/{code}/', timeout=15)
            except:
                pass

        # 请求列表页
        referer = f'https://cq.lianjia.com/ershoufang/{code}/pg{page-1}/' if page > 1 else f'https://cq.lianjia.com/ershoufang/{code}/'

        try:
            resp, session = safe_get(session, url, headers_extra={'Referer': referer}, timeout=20)
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

        # 提取房源ID
        soup = BeautifulSoup(resp.text, 'lxml')
        house_ids = []

        url_id_matches = re.findall(r'/ershoufang/(\d+)\.html', resp.text)
        if url_id_matches:
            seen = set()
            for hid in url_id_matches:
                if hid not in seen:
                    seen.add(hid)
                    house_ids.append(hid)
            print(f'  从链接提取到 {len(house_ids)} 个房源ID')

        if not house_ids:
            items = soup.select('.sellListContent li[data-id]')
            house_ids = [item.get('data-id') for item in items if item.get('data-id')]
            if house_ids:
                print(f'  从data-id属性提取到 {len(house_ids)} 个房源ID')

        if not house_ids:
            print(f'  未找到房源，停止翻页')
            if page == 1:
                debug_path = os.path.join(OUTPUT_DIR, f'debug_lianjia_{code}_p1.html')
                with open(debug_path, 'w', encoding='utf-8', errors='ignore') as f:
                    f.write(resp.text)
                print(f'  调试文件: {debug_path}')
            break

        # 访问详情页
        for i, hid in enumerate(house_ids):
            if hid in done_ids:
                print(f'  [{i+1}/{len(house_ids)}] {hid} (已爬，跳过)')
                continue

            print(f'  [{i+1}/{len(house_ids)}] {hid}...', end=' ')
            data = get_detail_page(hid, name)
            if data:
                all_data.append(data)
                done_ids.add(hid)
                print(f'[OK] {data["title"][:20]} | {data["total_price"]}万')
            else:
                print('[ERR]')

            time.sleep(random.uniform(1.5, 3))

        pages_done.append(page)
        save_checkpoint(code, pages_done, list(done_ids))

        # 每10页刷session
        if page % 10 == 0:
            session = refresh_session(session)

        if len(house_ids) == 0:
            break

    print(f'  [OK] [{name}] 完成：{len(pages_done)} 页，共 {len(all_data)} 条')
    return all_data


# ===================== 主流程 =====================
if __name__ == '__main__':
    all_houses = []

    for code, name in DISTRICTS:
        print(f'\n{"="*50}')
        print(f'开始爬取链家 {name}...')
        print(f'{"="*50}')

        data = crawl_district(code, name, max_pages=100, resume=True)
        all_houses.extend(data)

        output_path = os.path.join(OUTPUT_DIR, f'lianjia_{name}.csv')
        if data:
            keys = ['id','title','total_price','unit_price','community',
                    'district','address','lng','lat','layout','rooms','halls','bathrooms',
                    'area','orientation','decoration','floor_desc','floor_type',
                    'total_floors','build_year','source']
            with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(data)

        print(f'\n>>> {name}完成，本区{len(data)}条，累计{len(all_houses)}条')

        wait = random.uniform(5, 12)
        print(f'  区间冷却 {wait:.1f}s ...')
        time.sleep(wait)

    print(f'\n{"="*50}')
    print(f'链家全部完成！共 {len(all_houses)} 条')
    print(f'{"="*50}')
