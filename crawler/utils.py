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
"aQQ_ajkguid=F7B4D023-2524-4E8F-9FA7-FB4B466A414A; sessid=0ADC5D26-DE20-42FC-B1C9-C3DF9A7CCDFF; ajk-appVersion=; ctid=20; id58=uVcyWmonw3RqSxvUFwlTAg==; xxzlclientid=9e9f197b-4ac8-4fe0-b525-1780990835353; xxzlxxid=pfmx9YPrZMngaMg5IB8XhLUfiXG951fL3E4v4TYV7zQvgVqboAu0QQrrHcrCK6A494Dv; wmda_uuid=b437387b8712d4bdd346301f93d8dd69; wmda_new_uuid=1; wmda_visited_projects=%3B6289197098934; fzq_h=1577c2cad1194274cda86fd4a6fcdca1_1783154596128_914c4e3e829944adbe73a7cbe0d59835_47901724934847785907590631820825004708; twe=2; obtain_by=1; xxzlbbid=pfmbRNCfHhZ+hmtopClXJkxyg7ZdM3ldKKqpia9aRFXhKiKaTQRGSh0YApSbwb356vMCxje0aaBK1pz6bPLy059bdAbgJvzJSzOl3tPA9U0Z1zDyAAZmheRSxPGWvGi2NQUnNjBr8SUxNzgzMTY0NDY1Mjg0MjEz_1; fzq_js_anjuke_ershoufang_pc=e81e9e61e94f000b4392297b700268e4_1783164694368_23"

    )

_LIANJIA_COOKIE_DEFAULT = (
    "lianjia_uuid=84e647ad-44a3-4621-873d-fe484a1cfa17; "
    "lianjia_token=2.00134251b449b0f84802ef78853196894d; "
    "lianjia_token_secure=2.00134251b449b0f84802ef78853196894d; "
    "lianjia_ssid=19d42f80-6852-44ee-a138-08721482eb90; "
    "select_city=500000; "
    "login_ucid=2000000542622736; "
    "hip=Iozv8HMO6fOBEC0BqZU0u0gZGzDZcOzFD5zF7VsrqlGFydROEmup--npB1m6LTfZ_-sH1roojhhlttqFItAVi_FY65zpRj1T0g35VPTreqMU-7E8NCfDFaTnw8LSzARbgEorKBHTE1FCq-51RhJj7IitAYCzD2_H8LxXZ5gGM6jbbZoFO4yZKt13QEkGSh5HLLeLw7WailvV9ZMysMjfZkef2R4qIkVPlFYYq9epEO6fKIeTFjZ93iF5gBEYvn2sP3Ld1pt1l8yVkplHDkdD3_2vzD01uM7nz1ne"
)

ANJUKE_COOKIE = _env('ANJUKE_COOKIE', _ANJUKE_COOKIE_DEFAULT)
LIANJIA_COOKIE = _env('LIANJIA_COOKIE', _LIANJIA_COOKIE_DEFAULT)
PROXY_URL = _env('CRAWLER_PROXY_URL', '')           # 隧道代理（单地址）
PROXY_LIST = []                                       # 私密代理池（多IP轮换）


# ============================================================
# 快代理 API 配置（私密代理提取）
# ============================================================

KDL_SECRET_ID = _env('KDL_SECRET_ID', 'ofpnwoplktv7km428dk1')
KDL_SIGNATURE = _env('KDL_SIGNATURE', 'jr03zjctv11my32k685b30sl3y84trt4')
KDL_USERNAME  = _env('KDL_USERNAME', 'd3133818967')
KDL_PASSWORD  = _env('KDL_PASSWORD', 'dn2qhllv')
KDL_PROXY_COUNT = int(_env('KDL_PROXY_COUNT', '20'))  # 默认提取20个
KDL_API_URL = 'https://dps.kdlapi.com/api/getdps/'


_PROXY_LAST_FETCH = 0
_PROXY_FETCH_COOLDOWN = 120  # API冷却时间


def _should_refetch():
    global _PROXY_LAST_FETCH
    if not PROXY_LIST:
        return True
    if time.time() - _PROXY_LAST_FETCH > _PROXY_FETCH_COOLDOWN:
        return True
    return False


def fetch_proxies_from_api(count=None):
    """从快代理API提取私密代理IP

    Args:
        count: 提取数量，默认 KDL_PROXY_COUNT

    Returns:
        list[str]: 代理URL列表 (格式: http://user:pass@ip:port)
    """
    if count is None:
        count = KDL_PROXY_COUNT

    params = {
        'secret_id': KDL_SECRET_ID,
        'signature': KDL_SIGNATURE,
        'num': count,
        'sep': '1',       # 换行分隔
        'format': 'text',  # 纯文本返回 ip:port
    }

    try:
        resp = requests.get(KDL_API_URL, params=params, timeout=15)
        if resp.status_code != 200:
            print(f'[proxy] API请求失败: HTTP {resp.status_code}')
            return []

        raw = resp.text.strip()
        if not raw or 'ERROR' in raw:
            print(f'[proxy] API返回异常: {raw[:200]}')
            return []

        # 解析 ip:port 列表（每行一个）
        proxies = []
        for line in raw.split('\n'):
            line = line.strip()
            if line and ':' in line and not line.startswith('#'):
                # 格式: ip:port → 拼上用户名密码
                proxies.append(f'http://{KDL_USERNAME}:{KDL_PASSWORD}@{line}')

        return proxies

    except Exception as e:
        print(f'[代理API] 提取异常: {e}')
        return []


def _load_proxy_list():
    """加载私密代理池

    来源优先级：
      1. 快代理API动态提取 → proxies.txt（自动缓存）
      2. 环境变量 CRAWLER_PROXY_LIST
      3. 模块目录下的 proxies.txt

    支持的代理格式：
      http://user:pass@ip:port    (推荐)
      ip:port                      (快代理API直出，自动拼接用户名密码)

    Returns:
        list[str]: 代理URL列表
    """
    proxies = []

    # 1) 快代理API动态提取（带冷却）
    api_proxies = fetch_proxies_from_api() if _should_refetch() else []
    if api_proxies:
        # 缓存到文件（方便下次直接用）
        txt_path = os.path.join(os.path.dirname(__file__), 'proxies.txt')
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(f'# 快代理私密代理池 ({len(api_proxies)}个) — 自动提取于 {time.strftime("%Y-%m-%d %H:%M:%S")}\n')
            for p in api_proxies:
                f.write(p + '\n')
        proxies.extend(api_proxies)
        global _PROXY_LAST_FETCH
        _PROXY_LAST_FETCH = time.time()
        print(f'[proxy] API提取 {len(api_proxies)} 个代理')

    # 2) 环境变量（补充）
    if not proxies:
        env_val = os.environ.get('CRAWLER_PROXY_LIST', '')
        if env_val:
            proxies.extend(p.strip() for p in env_val.split(',') if p.strip())

    # 3) proxies.txt 文件（补充/回退）
    if not proxies:
        txt_path = os.path.join(os.path.dirname(__file__), 'proxies.txt')
        if os.path.exists(txt_path):
            with open(txt_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        proxies.append(line)

    # 统一转换为 http://user:pass@ip:port 格式
    normalized = []
    for p in proxies:
        if p.startswith('http://') or p.startswith('https://'):
            normalized.append(p)
        else:
            # ip:port 格式 → 拼接用户名密码
            parts = p.split(':')
            if len(parts) == 2:
                normalized.append(f'http://{KDL_USERNAME}:{KDL_PASSWORD}@{p}')
            elif len(parts) == 4:
                ip, port, user, passwd = parts
                normalized.append(f'http://{user}:{passwd}@{ip}:{port}')
            else:
                normalized.append(p)
    return normalized


def refresh_proxy_list():
    """（重新）加载代理池，返回当前可用代理数量"""
    global PROXY_LIST
    PROXY_LIST = _load_proxy_list()
    return len(PROXY_LIST)


def get_proxy():
    """随机获取一个代理URL（从私密代理池中）

    Returns:
        str | None: 代理URL，若未配置代理池则返回 None（走直连）
    """
    if not PROXY_LIST:
        return None
    return random.choice(PROXY_LIST)


# 启动时自动加载
refresh_proxy_list()


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
    'source_id', 'fingerprint', 'image_url',
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

def mobile_get(url, timeout=60, proxy_url=None, max_retries=5, no_cache=True):
    """移动站请求，自动轮换 UA 和代理IP，失败时自动换代理重试。

    Args:
        url: 目标 URL
        timeout: 超时秒数
        proxy_url: 指定代理地址
        max_retries: 最大重试次数（每次重试会换一个新代理）
        no_cache: 是否添加防缓存头

    Returns:
        requests.Response 或 None
    """
    for attempt in range(max_retries):
        # 选择代理：每次重试都换新代理
        if proxy_url is not None:
            chosen_proxy = proxy_url
        else:
            chosen_proxy = get_proxy()  # 从代理池随机取

        proxies = {'http': chosen_proxy, 'https': chosen_proxy} if chosen_proxy else None

        try:
            headers = {
                'User-Agent': random.choice(USER_AGENTS_MOBILE),
                'Accept': 'text/html,application/xhtml+xml',
                'Accept-Language': 'zh-CN,zh;q=0.9',
                'Connection': 'close',
            }
            if no_cache:
                headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                headers['Pragma'] = 'no-cache'

            resp = requests.get(
                url, headers=headers,
                proxies=proxies, timeout=timeout,
            )
            resp.text  # 强制读取，捕获解码错误
            return resp

        except Exception as e:
            err_name = type(e).__name__
            if attempt < max_retries - 1:
                wait = 2 + attempt * 3 + random.uniform(0, 3)
                if attempt >= 2 and not proxy_url:
                    # 第3次失败后尝试刷新代理池
                    new_count = refresh_proxy_list()
                    if new_count > 0:
                        print(f'  [proxy] 刷新代理池: {new_count}个新IP')
                time.sleep(wait)
            else:
                print(f'  [proxy] 请求失败({max_retries}次重试后): {err_name}')

    return None


def desktop_get(url, timeout=50, proxy_url=None, max_retries=4):
    """桌面站请求，自动轮换 UA 和代理IP。

    Args:
        url: 目标 URL
        timeout: 超时秒数
        proxy_url: 代理地址（None=自动从代理池选，''=直连）
        max_retries: 最大重试次数

    Returns:
        requests.Response 或 None
    """
    for attempt in range(max_retries):
        if proxy_url is not None:
            chosen_proxy = proxy_url
        else:
            chosen_proxy = get_proxy()

        proxies = {'http': chosen_proxy, 'https': chosen_proxy} if chosen_proxy else None

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
            time.sleep(random.uniform(2, 5))
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
