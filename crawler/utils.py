"""
============================================================
爬虫公共工具模块 — UA轮换 / Session管理 / 安全请求 / 指纹 / 断点
============================================================

用法:
    from crawler.utils import (
        # 配置常量
        ANJUKE_DISTRICTS, LIANJIA_DISTRICTS,
        OUTPUT_DIR, CHECKPOINT_DIR,
        ANJUKE_CSV_KEYS, LIANJIA_CSV_KEYS,

        # Session & 请求
        create_session, refresh_session, safe_get,

        # 指纹 & 解析
        make_anjuke_fingerprint, make_lianjia_fingerprint,

        # 断点
        load_checkpoint, save_checkpoint,

        # 工具
        parse_cookie_string, save_csv, deduplicate_and_save,
        safe_float, safe_int,
    )

环境变量 (生产环境请设置，开发环境使用默认值):
    ANJUKE_COOKIE      — 安居客 Cookie 字符串
    LIANJIA_COOKIE     — 链家 Cookie 字符串
    CRAWLER_PROXY_URL  — 代理地址 (如 http://user:pass@host:port)
    DB_HOST / DB_USER / DB_PASSWORD / DB_DATABASE — 数据库配置
============================================================
"""

import os
import re
import csv
import json
import time
import random
import hashlib

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ============================================================
# 环境变量 — 生产环境通过环境变量注入，开发环境使用默认值
# ============================================================

def _env(key, default=''):
    """读取环境变量，空字符串视为未设置"""
    val = os.environ.get(key, '')
    return val if val else default


# Cookie（从浏览器复制，过期需更新；生产环境请设环境变量）
_ANJUKE_COOKIE_DEFAULT = (
    "aQQ_ajkguid=F7B4D023-2524-4E8F-9FA7-FB4B466A414A; "
    "sessid=0ADC5D26-DE20-42FC-B1C9-C3DF9A7CCDFF; "
    "ctid=20; twe=2; "
    "id58=uVcyWmonw3RqSxvUFwlTAg==; "
    "xxzlclientid=9e9f197b-4ac8-4fe0-b525-1780990835353; "
    "xxzlxxid=pfmx9YPrZMngaMg5IB8XhLUfiXG951fL3E4v4TYV7zQvgVqboAu0QQrrHcrCK6A494Dv; "
    "obtain_by=1; "
    "xxzlbbid=pfmbRKBxxeD3YHkVphZEbLbECGY88YcxPCZhssNIWgvpz4AO42cfftjxMxNqnl1aj3FA0uuvA2o4JqOELhIcA39PPcXOTmlLH5l8ZMpQVITrEg4/kx43I5oeFZyh7qazWzHnt7p0hgExNzgxMDg3NTM3MzMwNDAy_1; "
    "fzq_h=f8e2b59bb392b6e1f0cf822f12516317_1781087662383_ec260a0137dc4b4693351482f40131d5_47901724934887724844252811768033755437; "
    "fzq_js_anjuke_ershoufang_pc=f2c9d58d02b287e6e913925d1edf5950_1781087661950_25"
)

_LIANJIA_COOKIE_DEFAULT = (
    "lianjia_uuid=84e647ad-44a3-4621-873d-fe484a1cfa17; "
    "lianjia_token=2.001249871148bb2eed03e4ae205179712a; "
    "lianjia_ssid=45e1b503-b277-4d0f-8d42-8be337a561ca"
)

ANJUKE_COOKIE = _env('ANJUKE_COOKIE', _ANJUKE_COOKIE_DEFAULT)
LIANJIA_COOKIE = _env('LIANJIA_COOKIE', _LIANJIA_COOKIE_DEFAULT)
PROXY_URL = _env('CRAWLER_PROXY_URL', '')


def parse_cookie_string(cookie_string):
    """将浏览器Cookie字符串解析为字典"""
    cookies = {}
    for item in cookie_string.replace('\n', '').replace('\r', '').split(';'):
        item = item.strip()
        if '=' in item:
            k, v = item.split('=', 1)
            cookies[k] = v
    return cookies


# ============================================================
# UA 轮换池
# ============================================================

USER_AGENTS_DESKTOP = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15',
]

USER_AGENTS_MOBILE = [
    'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 14; SM-S9080) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
]

BASE_HEADERS_DESKTOP = {
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

BASE_HEADERS_MOBILE = {
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Connection': 'close',
}


# ============================================================
# 统一区县列表
# ============================================================

# 安居客区县（PC站拼音编码 → 中文名），共38个
ANJUKE_DISTRICTS = [
    ('yubei',       '两江新区'),
    ('yuzhong',     '渝中区'),
    ('nanana',      '南岸区'),
    ('shapingba',   '沙坪坝区'),
    ('jiulongpo',   '九龙坡区'),
    ('banan',       '巴南区'),
    ('beibei',      '北碚区'),
    ('dadukou',     '大渡口区'),
    ('bishanqu',    '璧山区'),
    ('yongchuanqu', '永川区'),
    ('wanzhouqu',   '万州区'),
    ('jiangjinqu',  '江津区'),
    ('hechuanqu',   '合川区'),
    ('tongliangqu', '铜梁区'),
    ('fulingqu',    '涪陵区'),
    ('changshouqu', '长寿区'),
    ('rongchangqu', '荣昌区'),
    ('qijiangqu',   '綦江区'),
    ('nanchuanqu',  '南川区'),
    ('dazhuqu',     '大足区'),
    ('tongnanqu',   '潼南区'),
    ('kaizhoukuaixian', '开州区'),
    ('dainjiangxian',   '垫江县'),
    ('liangpingxian',   '梁平区'),
    ('wansheng',        '万盛区'),
    ('fengjiexian',     '奉节县'),
    ('yunyangxian',     '云阳县'),
    ('zhongxian',       '忠县'),
    ('wuxixian',        '巫溪县'),
    ('qianjiangqu',     '黔江区'),
    ('wulongxian',      '武隆区'),
    ('cqwushanxian',    '巫山县'),
    ('chengkouxian',    '城口县'),
    ('pengshuimiaozutujiazuzhixian',    '彭水县'),
    ('xiushantujiazumiaozuzhixian',     '秀山县'),
    ('shizhutujiazuzhixian',            '石柱县'),
    ('youyangtujiazumiaozuzhixian',     '酉阳县'),
    ('fengduxian',      '丰都县'),
]

# 链家区县（拼音编码 → 中文名），共12个
LIANJIA_DISTRICTS = [
    ('liangjiangxinqu', '两江新区'),
    ('yuzhong',         '渝中区'),
    ('nanan',           '南岸区'),
    ('shapingba',       '沙坪坝区'),
    ('jiulongpo',       '九龙坡区'),
    ('dadukou',         '大渡口区'),
    ('banan',           '巴南区'),
    ('beibei',          '北碚区'),
    ('jiangjing',       '江津区'),
    ('kaizhouqu',       '开州区'),
    ('rongchangqu',     '荣昌区'),
    ('bishan',          '璧山'),
]

# 安居客编码 → 中文名 映射表
ANJUKE_CODE_TO_NAME = {c: n for c, n in ANJUKE_DISTRICTS}
ANJUKE_NAME_TO_CODE = {n: c for c, n in ANJUKE_DISTRICTS}


# ============================================================
# 输出路径
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, '..', 'data', 'raw')
CHECKPOINT_DIR = os.path.join(BASE_DIR, '..', 'data', 'checkpoints')

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CHECKPOINT_DIR, exist_ok=True)


# ============================================================
# 统一 CSV 字段定义
# ============================================================

ANJUKE_CSV_KEYS = [
    'id', 'title', 'total_price', 'unit_price', 'community', 'district',
    'address', 'lng', 'lat', 'layout', 'rooms', 'halls', 'bathrooms',
    'area', 'orientation', 'decoration', 'floor_desc', 'floor_type',
    'total_floors', 'build_year', 'tags', 'followers', 'source',
    'source_id', 'fingerprint',
]

LIANJIA_CSV_KEYS = [
    'id', 'title', 'total_price', 'unit_price', 'community', 'district',
    'address', 'lng', 'lat', 'layout', 'rooms', 'halls', 'bathrooms',
    'area', 'orientation', 'decoration', 'floor_desc', 'floor_type',
    'total_floors', 'build_year', 'source', 'source_id', 'fingerprint',
]


# ============================================================
# Session 工厂
# ============================================================

def create_session(cookie_string='', ua_pool=None, base_headers=None):
    """创建一个带重试策略的新 Session

    Args:
        cookie_string: Cookie 字符串（如 ANJUKE_COOKIE）
        ua_pool: UA 列表，默认 USER_AGENTS_DESKTOP
        base_headers: 基础请求头，默认 BASE_HEADERS_DESKTOP

    Returns:
        requests.Session
    """
    if ua_pool is None:
        ua_pool = USER_AGENTS_DESKTOP
    if base_headers is None:
        base_headers = BASE_HEADERS_DESKTOP

    session = requests.Session()

    # urllib3 层重试（处理 5xx、429 等 HTTP 级错误）
    retry_strategy = Retry(
        total=2,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=1,
        pool_maxsize=1,
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    # 初始化 headers 和 cookies
    session.headers.update(base_headers)
    session.headers['User-Agent'] = random.choice(ua_pool)

    if cookie_string:
        session.cookies.update(parse_cookie_string(cookie_string))

    # 保存配置以便 refresh_session 重建
    session._cookie_string = cookie_string
    session._ua_pool = ua_pool
    session._base_headers = base_headers

    return session


def refresh_session(old_session):
    """重建 Session，更换 UA 和连接池，避免被指纹追踪

    Args:
        old_session: 旧的 requests.Session

    Returns:
        新的 requests.Session
    """
    cookie_string = getattr(old_session, '_cookie_string', '')
    ua_pool = getattr(old_session, '_ua_pool', None)
    base_headers = getattr(old_session, '_base_headers', None)

    try:
        old_session.close()
    except Exception:
        pass

    time.sleep(random.uniform(3, 6))  # 冷却期
    return create_session(cookie_string, ua_pool, base_headers)


# ============================================================
# 安全请求 — 指数退避 + Session自愈
# ============================================================

def safe_get(session, url, referer='', timeout=20, max_retries=3):
    """带指数退避的 GET 请求。

    遇到 ConnectionError / RemoteDisconnected 时：
      1. 指数退避重试（最多 max_retries 次）
      2. 每次重试前刷新 Session

    Args:
        session: requests.Session
        url: 目标 URL
        referer: Referer 头
        timeout: 请求超时秒数
        max_retries: 最大重试次数

    Returns:
        (response, session) — session 可能是新创建的
    """
    headers = {}
    if referer:
        headers['Referer'] = referer

    for attempt in range(max_retries):
        try:
            resp = session.get(url, headers=headers, timeout=timeout)
            return resp, session

        except (requests.ConnectionError, requests.Timeout,
                requests.exceptions.ChunkedEncodingError) as e:
            err_name = type(e).__name__
            if attempt < max_retries - 1:
                base = (2 ** attempt) * 3
                jitter = random.uniform(0, base)
                wait = base + jitter
                print(f'  [WARN] [{err_name}] {e}')
                print(f'  [Retry] {wait:.1f}s后重试 ({attempt + 1}/{max_retries - 1})...')
                time.sleep(wait)
                session = refresh_session(session)
            else:
                print(f'  [ERR] 重试{max_retries}次后仍失败: {err_name}')
                raise

        except requests.RequestException as e:
            print(f'  [ERR] 请求异常 [{type(e).__name__}]: {e}')
            raise

    return None, session


# ============================================================
# 代理请求（移动站用）
# ============================================================

def mobile_get(url, timeout=60, proxy_url=None, max_retries=4):
    """移动站请求，自动轮换 UA。若提供代理则通过代理访问。

    Args:
        url: 目标 URL
        timeout: 超时秒数
        proxy_url: 代理地址，如 'http://user:pass@host:port'
        max_retries: 最大重试次数

    Returns:
        requests.Response 或 None
    """
    if proxy_url is None:
        proxy_url = PROXY_URL

    proxies = {'http': proxy_url, 'https': proxy_url} if proxy_url else None

    for attempt in range(max_retries):
        try:
            headers = {
                'User-Agent': random.choice(USER_AGENTS_MOBILE),
                'Accept': 'text/html,application/xhtml+xml',
                'Connection': 'close',
            }
            resp = requests.get(
                url, headers=headers,
                proxies=proxies, timeout=timeout,
            )
            resp.text  # 强制读取，捕获 ChunkedEncodingError
            return resp
        except Exception:
            time.sleep(random.uniform(3, 8))
    return None


def desktop_get(url, timeout=50, proxy_url=None, max_retries=3):
    """桌面站请求，自动轮换 UA。

    Args:
        url: 目标 URL
        timeout: 超时秒数
        proxy_url: 代理地址
        max_retries: 最大重试次数

    Returns:
        requests.Response 或 None
    """
    if proxy_url is None:
        proxy_url = PROXY_URL

    proxies = {'http': proxy_url, 'https': proxy_url} if proxy_url else None

    for attempt in range(max_retries):
        try:
            headers = {
                'User-Agent': random.choice(USER_AGENTS_DESKTOP),
                'Accept': 'text/html',
                'Connection': 'close',
            }
            resp = requests.get(
                url, headers=headers,
                proxies=proxies, timeout=timeout,
            )
            resp.text
            return resp
        except Exception:
            time.sleep(2)
    return None


# ============================================================
# 指纹生成 — 所有文件必须使用此函数以保证一致性
# ============================================================

def make_anjuke_fingerprint(house):
    """生成安居客房源指纹，用于去重和数据库匹配。

    算法: MD5 of "community|district|area|rooms|total_price"
    返回 32 位十六进制字符串。

    Args:
        house: dict，需包含 community, district, area, rooms, total_price

    Returns:
        str: 32位MD5指纹
    """
    community = str(house.get('community', '')).strip()
    district = str(house.get('district', '')).strip()

    try:
        area = round(float(house.get('area', 0) or 0), 1)
    except (ValueError, TypeError):
        area = 0

    try:
        rooms = int(float(house.get('rooms', 0) or 0))
    except (ValueError, TypeError):
        rooms = 0

    try:
        total_price = round(float(house.get('total_price', 0) or 0), 1)
    except (ValueError, TypeError):
        total_price = 0

    key = f"{community}|{district}|{area}|{rooms}|{total_price}"
    return hashlib.md5(key.encode()).hexdigest()


def make_lianjia_fingerprint(house):
    """生成链家房源指纹。链家有唯一的 source_id，以此为基础。

    算法: "lj_{source_id}"

    Args:
        house: dict，需包含 id 或 source_id

    Returns:
        str: 如 "lj_104123456789" 或空字符串
    """
    sid = str(house.get('id', '') or house.get('source_id', '')).strip()
    if sid:
        return f"lj_{sid}"
    return ""


# ============================================================
# 断点管理
# ============================================================

def _checkpoint_path(prefix, code):
    """生成断点文件路径"""
    return os.path.join(CHECKPOINT_DIR, f'{prefix}_{code}.json')


def load_checkpoint(prefix, code):
    """加载区县的爬取进度

    Args:
        prefix: 前缀，如 'anjuke' / 'anjuke_fast' / 'lianjia'
        code: 区县编码

    Returns:
        dict: {'pages_done': [1,2,3], 'pages_failed': [4], 'total_crawled': 0}
    """
    cp_path = _checkpoint_path(prefix, code)
    if os.path.exists(cp_path):
        try:
            with open(cp_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    # 兼容旧格式（纯列表）
                    return {'pages_done': data, 'pages_failed': [], 'total_crawled': 0}
                return data
        except (json.JSONDecodeError, IOError):
            print(f'  [WARN] 断点文件损坏，忽略: {cp_path}')
    return {'pages_done': [], 'pages_failed': [], 'total_crawled': 0}


def save_checkpoint(prefix, code, pages_done, pages_failed=None):
    """保存区县的爬取进度

    Args:
        prefix: 前缀
        code: 区县编码
        pages_done: 已完成页码列表
        pages_failed: 失败页码列表（可选）
    """
    if pages_failed is None:
        pages_failed = []

    cp_path = _checkpoint_path(prefix, code)
    with open(cp_path, 'w', encoding='utf-8') as f:
        json.dump({
            'pages_done': list(pages_done),
            'pages_failed': list(pages_failed),
            'total_crawled': len(pages_done),  # 修复: 使用页数而非页码之和
        }, f, ensure_ascii=False)


# ============================================================
# CSV 工具
# ============================================================

def save_csv(data, filepath, fieldnames):
    """保存数据到 CSV 文件"""
    if not data:
        return
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(data)


def deduplicate_and_save(all_data, filepath, fieldnames, fingerprint_key='fingerprint'):
    """去重后保存到 CSV"""
    if not all_data:
        return [], 0

    seen = set()
    unique = []
    for h in all_data:
        fp = h.get(fingerprint_key, '')
        if fp and fp not in seen:
            seen.add(fp)
            unique.append(h)

    save_csv(unique, filepath, fieldnames)
    return unique, len(unique)


# ============================================================
# 数值安全转换
# ============================================================

def safe_float(val, default=0.0):
    """安全转换为 float"""
    try:
        return float(val) if val is not None and val != '' else default
    except (ValueError, TypeError):
        return default


def safe_int(val, default=0):
    """安全转换为 int"""
    try:
        return int(float(val)) if val is not None and val != '' else default
    except (ValueError, TypeError):
        return default
