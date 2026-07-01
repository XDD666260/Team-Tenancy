# ============================================================
# 房源图片爬虫 — 单线程慢爬，不用代理
#
# 链家: source_id 是纯数字 → 详情页需要浏览器 Cookie
#       获取 Cookie: Chrome 打开 cq.lianjia.com → F12 → Application
#       → Cookies → 全选复制 → 设置环境变量 LIANJIA_COOKIE
#
# 安居客: source_id 已哈希化 → 从 raw CSV 恢复数字 ID → 详情页
#
# 用法:
#   python crawler/scrape_images.py --source lianjia --limit 10
#   python crawler/scrape_images.py --source anjuke --limit 10
#   python crawler/scrape_images.py --source all --limit 10 --dry-run
#
# 环境变量（可选，绕过反爬）:
#   LIANJIA_COOKIE="xxx"    — 链家浏览器 Cookie
#   ANJUKE_COOKIE="xxx"     — 安居客浏览器 Cookie
# ============================================================

import os
import re
import sys
import csv
import json
import time
import random
import argparse

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pymysql

# --------------- 数据库 ---------------
DB_CONFIG = {
    'host': 'localhost', 'user': 'root', 'password': '123456',
    'database': 'secondhouse_cq', 'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
    'conv': pymysql.converters.conversions.copy(),
}
DB_CONFIG['conv'][pymysql.constants.FIELD_TYPE.DECIMAL] = float
DB_CONFIG['conv'][pymysql.constants.FIELD_TYPE.NEWDECIMAL] = float

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw')

# --------------- Cookie（过期后重新粘贴）---------------
LIANJIA_COOKIE = "lianjia_uuid=84e647ad-44a3-4621-873d-fe484a1cfa17; _ga=GA1.2.115501286.1780982060; _ga_0VZPJRR5MM=GS2.2.s1780983078$o1$g0$t1780983078$j60$l0$h0; crosSdkDT2019DeviceId=lqz54m-h4glge-i7mgmroflq4zh3j-h60ivcfec; sensorsdata2015jssdkcross=%7B%22distinct_id%22%3A%2219eaacd69d9d7a-0d78c933abaac48-4c657b58-1474560-19eaacd69da2234%22%2C%22%24device_id%22%3A%2219eaacd69d9d7a-0d78c933abaac48-4c657b58-1474560-19eaacd69da2234%22%2C%22props%22%3A%7B%22%24latest_traffic_source_type%22%3A%22%E7%9B%B4%E6%8E%A5%E6%B5%81%E9%87%8F%22%2C%22%24latest_referrer%22%3A%22%22%2C%22%24latest_referrer_host%22%3A%22%22%2C%22%24latest_search_keyword%22%3A%22%E6%9C%AA%E5%8F%96%E5%88%B0%E5%80%BC_%E7%9B%B4%E6%8E%A5%E6%89%93%E5%BC%80%22%7D%7D; lfrc_=580a6bb9-8471-49fb-a448-f391eff97170; select_city=500000; login_ucid=2000000542622736; lianjia_token=2.00123321d948c18825039e08e89b9e5c64; lianjia_token_secure=2.00123321d948c18825039e08e89b9e5c64; security_ticket=tLfJOn0cxf8gOa7gnQld0SCRagn/jteWzcXTFY2PhiHq6TGkaimIK8CGyMvvqD2y4ZztewSyKDufVGBKIh0LNkDyOyMvJW85+C5xNRaAUn7aT0NKCnYUhqwkPRnA3aG0xWnh+ihIZPQ+sYnNeBWANx+KOBCVe3IBncTuJrcMiAQ=; Hm_lvt_46bf127ac9b856df503ec2dbf942b67e=1780982049,1782564485,1782875093; HMACCOUNT=807243DEB1481E17; _jzqc=1; _jzqx=1.1780982049.1782875093.8.jzqsr=my%2Efeishu%2Ecn|jzqct=/.jzqsr=clogin%2Elianjia%2Ecom|jzqct=/; _jzqckmp=1; _gid=GA1.2.2058176043.1782875105; lianjia_ssid=89725406-2625-4fee-a066-affdd39d2ad1; _jzqa=1.1801755635432145400.1780982049.1782875093.1782887528.13; hip=G6MRsbTSPIwymdU2OnG8AX3TeBvxsHViTLIr8cgYmpup6qF4UsjuIrgUJk8u8s3AiSHZ4f0fHahoww_8V3crb_Jug8qR8qVxD_Iij-WI7KOaILsGIiA_mpmEXtR2jSledBtwdfcnOlFDgeFb6E-vOjZehxtluPQRfE9Isango0l3twqxXXIKuCw-HkjuvBJkh1pZqCosoPsznYImR7vQodnR_awUQt2zYcf9RoHhL7hyqZH_iuLu64rZZkNPwX0VekTsHzPQftNSSK__nYliyFEh9M9dTScMlaZrOZpb9BePpIR0; _jzqb=1.6.10.1782887528.1; Hm_lpvt_46bf127ac9b856df503ec2dbf942b67e=1782887948; _gat=1; _gat_global=1; _gat_new_global=1; _gat_dianpu_agent=1; _ga_PV625F3L95=GS2.2.s1782887546$o12$g1$t1782887958$j60$l0$h0"
ANJUKE_COOKIE = "aQQ_ajkguid=F7B4D023-2524-4E8F-9FA7-FB4B466A414A; sessid=0ADC5D26-DE20-42FC-B1C9-C3DF9A7CCDFF; ajk-appVersion=; ctid=20; id58=uVcyWmonw3RqSxvUFwlTAg==; xxzlclientid=9e9f197b-4ac8-4fe0-b525-1780990835353; xxzlxxid=pfmx9YPrZMngaMg5IB8XhLUfiXG951fL3E4v4TYV7zQvgVqboAu0QQrrHcrCK6A494Dv; fzq_h=3d82d83b29d0dfe6675a7d088c1303e6_1782873636274_fb0f2dd40bce49e3822f8c226ad342b4_47901724934856372964671308539808896005; twe=2; obtain_by=1; xxzlbbid=pfmbRKAOb1gEKGGhjvz5OzVYqLNZshS6JF4hkVinwrRNa5DlNdH5tXf/I3zk+vBbe53X7MgUXckZegLcQKKqmvz6EsNSYEKO2FocP0gyMAV8tSnNi35QKsd7u92Yn06qk0tAPmjUVrIxNzgyODg4MjA2NjYyNTky_1; fzq_js_anjuke_ershoufang_pc=0799aa275a2a044a579162f5c442ccaf_1782888212806_25"

# --------------- 公共 Headers ---------------
MOBILE_UA = (
    'Mozilla/5.0 (Linux; Android 13; Pixel 7) '
    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
)
DESKTOP_UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
)


def safe_get(url, headers=None, timeout=30, cookie_str=None):
    """发送 GET 请求，返回 Response 或 None"""
    session = requests.Session()
    if headers:
        session.headers.update(headers)
    else:
        session.headers.update({
            'User-Agent': DESKTOP_UA,
            'Accept-Language': 'zh-CN,zh;q=0.9',
        })
    if cookie_str:
        for item in cookie_str.split(';'):
            item = item.strip()
            if '=' in item:
                k, v = item.split('=', 1)
                session.cookies.set(k.strip(), v.strip())

    try:
        resp = session.get(url, timeout=timeout, allow_redirects=True)
        return resp
    except Exception:
        return None


# ============================================================
# 链家图片爬取
# ============================================================

def scrape_lianjia_images(source_id, cookie=None, timeout=30):
    """
    链家移动站详情页:
    https://m.lianjia.com/cq/ershoufang/{source_id}.html

    桌面站反爬严格，移动站 + Cookie 成功率更高
    """
    url = f'https://m.lianjia.com/cq/ershoufang/{source_id}.html'
    images = []

    headers = {
        'User-Agent': MOBILE_UA,
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Referer': 'https://m.lianjia.com/cq/ershoufang/',
    }

    resp = safe_get(url, headers=headers, timeout=timeout, cookie_str=cookie)
    if not resp or resp.status_code != 200:
        return images

    html = resp.text

    # 验证码检查
    if 'CAPTCHA' in html or len(html) < 10000:
        return images

    # 从 HTML 中提取所有 image*.ljcdn.com 的真实房源图片
    # 房源实拍: image1.ljcdn.com/110000-inspection/pc*
    # 小区图片: image1.ljcdn.com/hdic-resblock/
    # 排除: hdic-frame（模板图）, static（默认图）
    seen = set()
    for m in re.finditer(r'(?:image\d*|pic\d*)\.ljcdn\.com/[^\"\s<>\)]+', html):
        url = 'https://' + m.group()
        # 只取房源实拍和小区图，排除模板图
        if 'hdic-frame' in url:
            continue
        if 'static' in url:
            continue
        # 去重：只保留不同的图片 ID（忽略裁剪参数）
        base = re.sub(r'[!\.].*$', '', url)
        if base not in seen:
            seen.add(base)
            images.append(url)

    # 如果不够，也搜直接的 http URL
    if len(images) < 3:
        for m in re.finditer(r'https?://[^\"\s<>]+\.(?:jpg|jpeg|png|webp)', html):
            url = m.group()
            if 'static' in url or 'default' in url or 'photo_none' in url:
                continue
            if url not in images:
                images.append(url)

    images = images[:6]

    return images[:6]


# ============================================================
# 安居客图片爬取
# ============================================================

def load_anjuke_id_map():
    """从原始 CSV 恢复 数字ID -> 指纹 的映射"""
    id_map = {}
    csv_files = ['anjuke_all.csv', 'anjuke_all_fast.csv', 'all_listings_merged.csv']

    for fname in csv_files:
        path = os.path.join(DATA_DIR, fname)
        if not os.path.exists(path):
            continue
        print(f'  Reading ID mapping: {fname} ...')
        with open(path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                src_id = row.get('source_id', '').strip()
                fp = row.get('fingerprint', '').strip()
                if src_id and src_id.isdigit():
                    if fp:
                        id_map[fp] = src_id
                    id_map[src_id] = src_id
        print(f'    Total: {len(id_map)} mappings')

    return id_map


def scrape_anjuke_images(numeric_id, cookie=None, timeout=30):
    """安居客桌面站: https://chongqing.anjuke.com/prop/view/S{numeric_id}"""
    url = f'https://chongqing.anjuke.com/prop/view/S{numeric_id}'
    images = []

    headers = {
        'User-Agent': DESKTOP_UA,
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Referer': 'https://chongqing.anjuke.com/sale/',
    }

    resp = safe_get(url, headers=headers, timeout=timeout, cookie_str=cookie)
    if not resp or resp.status_code != 200:
        return images

    soup = BeautifulSoup(resp.text, 'lxml')

    seen = set()
    # 安居客房源实拍图: pic*.ajkimg.com/display/anjuke/
    for m in re.finditer(r'pic\d*\.ajkimg\.com/display/anjuke/[^\"\s<>\)]+\.(?:jpg|jpeg|png|webp)', resp.text):
        url = 'https://' + m.group()
        # 去重（忽略裁剪参数）
        base = re.sub(r'\?.*$', '', url)
        if base not in seen:
            seen.add(base)
            images.append(url)

    # 不够则用 img 标签补充
    if len(images) < 3:
        for img in soup.find_all('img'):
            for attr in ['src', 'data-src', 'data-original']:
                src = img.get(attr, '')
                if not src:
                    continue
                if src.startswith('//'):
                    src = 'https:' + src
                if 'ajkimg.com/display/anjuke' in src and src not in images:
                    images.append(src)

    return images[:6]


# ============================================================
# 数据库操作
# ============================================================

def get_db():
    return pymysql.connect(**DB_CONFIG)


def update_image_urls(conn, house_id, image_urls):
    if not image_urls:
        return False
    cur = conn.cursor()
    cur.execute(
        'UPDATE houses SET image_urls = %s WHERE id = %s',
        (json.dumps(image_urls, ensure_ascii=False), house_id)
    )
    conn.commit()
    return True


def get_pending(conn, source, limit=None):
    cur = conn.cursor()
    sql = """
        SELECT id, source_id, fingerprint, title, community
        FROM houses
        WHERE source = %s
          AND (image_urls IS NULL OR image_urls = '')
        ORDER BY id
    """
    params = [source]
    if limit:
        sql += ' LIMIT %s'
        params.append(limit)
    cur.execute(sql, params)
    return cur.fetchall()


# ============================================================
# 主流程
# ============================================================

def process(conn, source, limit=None, dry_run=False,
            lianjia_cookie=None, anjuke_cookie=None):
    """处理指定来源的所有待爬取房源"""
    if source == 'anjuke':
        print('\n=== Loading anjuke ID map ===')
        id_map = load_anjuke_id_map()
        if not id_map:
            print('FAIL: no raw CSV found, cannot recover anjuke IDs')
            return 0

    rows = get_pending(conn, source, limit)
    total = len(rows)
    print(f'\n=== {source}: {total} pending ===')

    success = 0
    for i, row in enumerate(rows):
        hid = row['id']
        sid = row['source_id']

        # 确定详情页 URL 和 cookie
        if source == 'lianjia':
            detail_url = f'https://m.lianjia.com/cq/ershoufang/{sid}.html'
            cookie = lianjia_cookie
        else:  # anjuke
            numeric_id = (
                id_map.get(row.get('fingerprint', '')) or
                id_map.get(sid) or
                id_map.get('ajk_' + row.get('fingerprint', ''))
            )
            if not numeric_id:
                continue
            detail_url = f'https://chongqing.anjuke.com/prop/view/S{numeric_id}'
            cookie = anjuke_cookie

        print(f'[{i+1}/{total}] {detail_url}', end=' ', flush=True)

        # 爬取
        if source == 'lianjia':
            images = scrape_lianjia_images(sid, cookie=cookie)
        else:
            images = scrape_anjuke_images(numeric_id, cookie=cookie)

        if images:
            if not dry_run:
                update_image_urls(conn, hid, images)
            print(f'OK {len(images)} imgs')
            success += 1
        else:
            print('FAIL (captcha or no images)')

        # 慢速延迟，不用代理只能慢慢来
        delay = random.uniform(3, 8)
        if 'CAPTCHA' in str(images):
            delay = random.uniform(30, 60)  # 触发验证码时等待更久
            print('    (long wait after captcha...)')
        time.sleep(delay)

    print(f'\n{source} done: {success}/{total}')
    return success


def show_stats(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT source,
               COUNT(*) as total,
               SUM(CASE WHEN image_urls IS NOT NULL AND image_urls != '' THEN 1 ELSE 0 END) as has_images
        FROM houses GROUP BY source
    """)
    print('\n=== Image coverage ===')
    for r in cur.fetchall():
        pct = r['has_images'] / r['total'] * 100 if r['total'] > 0 else 0
        print(f"  {r['source']:15s}: {r['has_images']:>6}/{r['total']:<6} ({pct:.1f}%)")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scrape listing images (slow, no proxy)')
    parser.add_argument('--source', choices=['lianjia', 'anjuke', 'all'], default='all')
    parser.add_argument('--limit', type=int, help='Max listings to process')
    parser.add_argument('--dry-run', action='store_true', help='Test only, no DB write')
    parser.add_argument('--lj-cookie', help='Lianjia browser cookie string')
    parser.add_argument('--ajk-cookie', help='Anjuke browser cookie string')
    args = parser.parse_args()

    lj_cookie = args.lj_cookie or LIANJIA_COOKIE or os.environ.get('LIANJIA_COOKIE', '')
    ajk_cookie = args.ajk_cookie or ANJUKE_COOKIE or os.environ.get('ANJUKE_COOKIE', '')

    if args.source in ('lianjia', 'all'):
        if not lj_cookie:
            print('[WARN] No lianjia cookie. Paste it into LIANJIA_COOKIE at top of this file.')
            print('  Chrome -> cq.lianjia.com -> F12 -> Application -> Cookies -> copy all')

    conn = get_db()
    try:
        if args.source in ('lianjia', 'all'):
            process(conn, 'lianjia', limit=args.limit,
                     dry_run=args.dry_run, lianjia_cookie=lj_cookie)

        if args.source in ('anjuke', 'all'):
            process(conn, 'anjuke', limit=args.limit,
                     dry_run=args.dry_run, anjuke_cookie=ajk_cookie)
    finally:
        conn.close()

    conn2 = get_db()
    show_stats(conn2)
    conn2.close()
    print('\nDone.')
