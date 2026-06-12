# 安居客二手房爬虫 与链家爬虫互补，两源数据合并去重
# 加固版：指数退避重试 / Session自愈 / UA轮换 / 断点续爬 / 自适应延迟

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import re
import csv
import os
import time
import random
import hashlib
import json
import copy

# ===================== Cookie（从浏览器复制） =====================
COOKIE_STRING = """aQQ_ajkguid=F7B4D023-2524-4E8F-9FA7-FB4B466A414A; sessid=0ADC5D26-DE20-42FC-B1C9-C3DF9A7CCDFF; ctid=20; twe=2; id58=uVcyWmonw3RqSxvUFwlTAg==; xxzlclientid=9e9f197b-4ac8-4fe0-b525-1780990835353; xxzlxxid=pfmx9YPrZMngaMg5IB8XhLUfiXG951fL3E4v4TYV7zQvgVqboAu0QQrrHcrCK6A494Dv; obtain_by=1; xxzlbbid=pfmbRKBxxeD3YHkVphZEbLbECGY88YcxPCZhssNIWgvpz4AO42cfftjxMxNqnl1aj3FA0uuvA2o4JqOELhIcA39PPcXOTmlLH5l8ZMpQVITrEg4/kx43I5oeFZyh7qazWzHnt7p0hgExNzgxMDg3NTM3MzMwNDAy_1; fzq_h=f8e2b59bb392b6e1f0cf822f12516317_1781087662383_ec260a0137dc4b4693351482f40131d5_47901724934887724844252811768033755437; fzq_js_anjuke_ershoufang_pc=f2c9d58d02b287e6e913925d1edf5950_1781087661950_25"""

cookies = {}
for item in COOKIE_STRING.replace('\n','').replace('\r','').split(';'):
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
    'Cache-Control': 'max-age=0',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
}

# ===================== 区县列表（安居客实际代码） =====================
DISTRICTS = [
    ('yubei', '两江新区'),
    ('yuzhong', '渝中区'),
    ('nanana', '南岸区'),
    ('shapingba', '沙坪坝区'),
    ('jiulongpo', '九龙坡区'),
    ('banan', '巴南区'),
    ('beibei', '北碚区'),
    ('dadukou', '大渡口区'),
    ('bishanqu', '璧山区'),
    ('yongchuanqu', '永川区'),
    ('wanzhouqu', '万州区'),
    ('jiangjinqu', '江津区'),
    ('hechuanqu', '合川区'),
    ('tongliangqu', '铜梁区'), 
    ('fulingqu', '涪陵区'),
    ('changshouqu', '长寿区'),
    ('rongchangqu', '荣昌区'),
    ('qijiangqu', '綦江区'),
    ('nanchuanqu', '南川区'),
    ('dazhuqu', '大足区'),
    ('tongnanqu', '潼南区'),
    ('kaizhoukuaixian', '开州区'),
    ('dainjiangxian', '垫江县'),
    ('liangpingxian', '梁平区'),
    ('wansheng', '万盛区'),
    ('fengjiexian', '奉节县'),
    ('yunyangxian', '云阳县'),
    ('zhongxian', '忠县'),
    ('wuxixian', '巫溪县'),
    ('qianjiangqu', '黔江区'),
    ('wulongxian', '武隆区'),
    ('cqwushanxian', '巫山县'),
    ('chengkouxian', '城口县'),
    ('pengshuimiaozutujiazuzhixian', '彭水县'),
    ('xiushantujiazumiaozuzhixian', '秀山县'),
    ('shizhutujiazuzhixian', '石柱县'),
    ('youyangtujiazumiaozuzhixian', '酉阳县'),
    ('fengduxian','丰都县'),
]

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw')
CHECKPOINT_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'checkpoints')
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CHECKPOINT_DIR, exist_ok=True)


# ===================== Session 工厂 =====================
def create_session():
    """创建一个带重试策略的新 Session"""
    session = requests.Session()

    # urllib3 层重试（处理 5xx、429 等 HTTP 级错误）
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

    # 初始化 headers 和 cookies
    session.headers.update(BASE_HEADERS)
    session.headers['User-Agent'] = random.choice(USER_AGENTS)
    session.cookies.update(cookies)

    return session


def refresh_session(old_session):
    """重建 Session，更换 UA 和连接池，避免被指纹追踪"""
    print('  [Refresh] 重建 Session（更换连接池 + UA）...')
    try:
        old_session.close()
    except:
        pass
    time.sleep(random.uniform(3, 6))  # 冷却期
    return create_session()


# ===================== 安全请求 =====================
def safe_get(session, url, referer='', timeout=20, max_retries=3):
    """
    带指数退避的 GET 请求。
    遇到 ConnectionError / RemoteDisconnected 时：
      1. 指数退避重试（最多 max_retries 次）
      2. 每次重试前刷新 Session
    返回 (response, new_session)
    """
    headers = {}
    if referer:
        headers['Referer'] = referer

    for attempt in range(max_retries):
        try:
            resp = session.get(url, headers=headers, timeout=timeout)
            return resp, session  # 成功，返回 response 和当前 session

        except (requests.ConnectionError, requests.Timeout,
                requests.exceptions.ChunkedEncodingError) as e:
            err_name = type(e).__name__
            if attempt < max_retries - 1:
                # 指数退避 + 随机抖动
                base = (2 ** attempt) * 3
                jitter = random.uniform(0, base)
                wait = base + jitter
                print(f'  [WARN] [{err_name}] {e}')
                print(f'  [Retry] {wait:.1f}s后重试 ({attempt+1}/{max_retries-1})...')
                time.sleep(wait)
                # 重建 session 避免被同一连接追踪
                session = refresh_session(session)
            else:
                print(f'  [ERR] 重试{max_retries}次后仍失败: {err_name}')
                raise

        except requests.RequestException as e:
            # 其他 requests 异常（非连接级）
            print(f'  [ERR] 请求异常 [{type(e).__name__}]: {e}')
            raise

    return None, session  # 不应到达这里


# ===================== 房源解析 =====================
def make_fingerprint(house):
    """生成房源指纹，用于去重"""
    key = f"{house.get('community','')}|{house.get('district','')}|{house.get('area',0)}|{house.get('rooms',0)}|{house.get('total_price',0)}"
    return hashlib.md5(key.encode()).hexdigest()


def parse_house_info(item):
    """解析安居客房源卡片
    安居客 .property-content-info 内多个 .property-content-info-text p：
      p[0] = 3室2厅2卫（每字符 span 包裹）
      p[1] = 122.25m²
      p[2] = 南
      p[3] = 高层(共18层)
      p[4] = 2005年建造
    .property-content-info-comm-address p = 详细地址
    """
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

        # 详细地址（列表页就有！）
        addr_el = item.select_one('.property-content-info-comm-address')
        house['address'] = addr_el.get_text(strip=True) if addr_el else ''

        # --- 户型/面积/朝向/楼层/年代 ---
        # 页面有两个 .property-content-info div：
        #   第1个（无额外class）包含 .property-content-info-text（p标签）
        #   第2个（.property-content-info-comm）包含小区名和地址
        # .property-content-info-text 本身是 <p>，不是容器
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
            try: house['area'] = float(area_str)
            except: pass

        # p[2] = 朝向 "南" / "南北" / "东南"
        house['orientation'] = info_texts[2] if len(info_texts) > 2 else ''

        # p[3] = 楼层 "高层(共18层)"
        floor_desc = info_texts[3] if len(info_texts) > 3 else ''
        house['floor_desc'] = floor_desc
        house['floor_type'] = ''
        house['total_floors'] = 0
        if floor_desc:
            # 楼层类型
            fm_type = re.search(r'(低层|中层|高层)', floor_desc)
            if fm_type: house['floor_type'] = fm_type.group(1)
            # 总楼层
            fm_total = re.search(r'共(\d+)层', floor_desc)
            if fm_total: house['total_floors'] = int(fm_total.group(1))

        # p[4] = 建成年代 "2005年建造"
        house['build_year'] = 0
        if len(info_texts) > 4:
            bm = re.search(r'(\d+)年建造', info_texts[4])
            if bm: house['build_year'] = int(bm.group(1))

        # 其他（列表页拿不到，留默认值）
        house['decoration'] = ''
        house['lng'] = house['lat'] = 0
        house['followers'] = 0
        house['source'] = 'anjuke'

    except Exception:
        pass

    return house


# ===================== 详情页补充字段 =====================
def get_anjuke_detail(session, house_id, timeout=15):
    """访问安居客详情页，获取装修和经纬度
    返回 {'decoration': str, 'lng': float, 'lat': float}
    """
    result = {'decoration': '', 'lng': 0, 'lat': 0}

    url = f'https://chongqing.anjuke.com/prop/view/{house_id}'
    try:
        resp, _ = safe_get(session, url, referer='https://chongqing.anjuke.com/sale/', timeout=timeout, max_retries=2)
    except Exception:
        return result

    if resp.status_code != 200:
        return result

    soup = BeautifulSoup(resp.text, 'lxml')

    # 装修：.maininfo-model-weak 第2个元素（第1个是楼层，第2个是装修，第3个是年代/类型）
    # 例：<div class="maininfo-model-weak">精装修</div>
    try:
        model_weaks = soup.select('.maininfo-model-weak')
        for el in model_weaks:
            text = el.get_text(strip=True)
            if '装' in text:
                result['decoration'] = text  # 精装修 / 简装 / 毛坯 / 豪装
                break
    except Exception:
        pass

    # 经纬度：<meta name="location" content="province=重庆;city=重庆;coord=106.526422,29.547963">
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


# ===================== 断点续爬 =====================
def load_checkpoint(code):
    """加载区县的爬取进度"""
    cp_path = os.path.join(CHECKPOINT_DIR, f'anjuke_{code}.json')
    if os.path.exists(cp_path):
        with open(cp_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'pages_done': [], 'pages_failed': [], 'total_crawled': 0}


def save_checkpoint(code, pages_done, pages_failed):
    """保存区县的爬取进度"""
    cp_path = os.path.join(CHECKPOINT_DIR, f'anjuke_{code}.json')
    with open(cp_path, 'w', encoding='utf-8') as f:
        json.dump({
            'pages_done': pages_done,
            'pages_failed': pages_failed,
            'total_crawled': sum(pages_done) if pages_done and isinstance(pages_done[0], int) else 0
        }, f, ensure_ascii=False)


# ===================== 区县爬取 =====================
def crawl_district(code, name, max_pages=50, resume=True, fetch_details=True):
    """爬取一个区县，支持断点续爬和自动容错
    fetch_details=True 时会进入详情页获取装修和经纬度
    """
    all_data = []
    session = create_session()

    # 加载断点（pages_done 从旧 checkpoint 继承，避免覆盖丢失）
    checkpoint = load_checkpoint(code) if resume else {}
    pages_done = list(checkpoint.get('pages_done', []))
    pages_failed = list(checkpoint.get('pages_failed', []))
    completed_pages = set(pages_done)

    if completed_pages:
        print(f'  [CP] 检测到断点: 已完成 {len(completed_pages)} 页，从第 {max(completed_pages)+1} 页继续')

    for page in range(1, max_pages + 1):
        # 跳过已完成页
        if page in completed_pages:
            print(f'\n--- [{name}] 第{page}页 (已爬，跳过) ---')
            continue

        if page == 1:
            url = f'https://chongqing.anjuke.com/sale/{code}/'
            referer = 'https://chongqing.anjuke.com/sale/'
        else:
            url = f'https://chongqing.anjuke.com/sale/{code}/p{page}/'
            referer = f'https://chongqing.anjuke.com/sale/{code}/p{page-1}/'

        print(f'\n--- [{name}] 第{page}/{max_pages}页 ---')

        # 自适应延迟：页码越大延迟越长（后期更容易触发风控）
        if page > 1:
            if page <= 10:
                base_delay = random.uniform(3, 6)
            elif page <= 30:
                base_delay = random.uniform(5, 10)
            elif page <= 50:
                base_delay = random.uniform(8, 15)
            else:
                base_delay = random.uniform(12, 25)
            # 加随机抖动 ±30%
            delay = base_delay * random.uniform(0.7, 1.3)
            print(f'  [T] 等待 {delay:.1f}s ...')
            time.sleep(delay)

        # 请求页面（带自动重试）
        try:
            resp, session = safe_get(session, url, referer=referer, timeout=20)
        except Exception as e:
            print(f'  [ERR] 页面请求最终失败: {type(e).__name__}: {e}')
            pages_failed.append(page)
            save_checkpoint(code, pages_done, pages_failed)
            # 失败后重建 session 再试下一页
            session = refresh_session(session)
            continue  # 不 break，继续下一页

        print(f'  状态码: {resp.status_code}  长度: {len(resp.text)}')

        # 状态码异常
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
            # 再试一次
            try:
                resp, session = safe_get(session, url, referer=referer, timeout=20)
            except:
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
            if house.get('title') and house.get('total_price', 0) > 0:
                house['district'] = name

                # 从包裹的 <a> 标签提取房源ID
                if fetch_details:
                    parent_a = item.find_parent('a')
                    if not parent_a:
                        parent_a = item.parent if item.parent and item.parent.name == 'a' else None
                    if parent_a:
                        href = parent_a.get('href', '')
                        m_id = re.search(r'/prop/view/(S\d+)', href)
                        if m_id:
                            house_id = m_id.group(1)
                            # 进入详情页获取装修和经纬度
                            detail = get_anjuke_detail(session, house_id)
                            if detail.get('decoration'):
                                house['decoration'] = detail['decoration']
                            if detail.get('lng'):
                                house['lng'] = detail['lng']
                                house['lat'] = detail['lat']
                            time.sleep(random.uniform(0.8, 1.5))  # 详情页间隔

                house['fingerprint'] = make_fingerprint(house)
                all_data.append(house)
                page_count += 1

        print(f'  [{name}] 本页有效 {page_count} 条，累计 {len(all_data)} 条')

        # 只有本页确实解析到房源才标记为已完成并保存断点
        if page_count > 0:
            pages_done.append(page)
            save_checkpoint(code, pages_done, pages_failed)
        # 无房源且页面长度异常（<10KB 通常是拦截页），不保存断点防止污染
        elif len(resp.text) < 10000:
            print(f'  [WARN] 页面过短({len(resp.text)}B)，疑似拦截页，不保存断点')

        # 每 10 页重建 session 避免指纹关联
        if page % 10 == 0 and page > 0:
            session = refresh_session(session)

        # 空页面就停止（第一页无结果也停止，说明该区县无数据或被拦截）
        if len(items) == 0 and page_count == 0:
            print(f'  页面无房源，停止翻页')
            # 第一页就空的，删除可能存在的旧断点（旧数据已失效）
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


# ===================== 主流程 =====================
if __name__ == '__main__':
    all_houses = []

    for code, name in DISTRICTS:
        print(f'\n{"="*50}')
        print(f'开始爬取安居客 {name}...')
        print(f'{"="*50}')

        data = crawl_district(code, name, max_pages=150, resume=True)
        all_houses.extend(data)

        # 每区保存
        if data:
            output_path = os.path.join(OUTPUT_DIR, f'anjuke_{name}.csv')
            keys = ['title','total_price','unit_price','community',
                    'district','address','lng','lat','layout','rooms','halls',
                    'bathrooms','area','orientation','decoration','floor_desc',
                    'floor_type','total_floors','build_year','followers','source','fingerprint']
            with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(data)
            print(f'  已保存 {output_path}')

        # 区间冷却
        wait = random.uniform(5, 12)
        print(f'  区间冷却 {wait:.1f}s ...')
        time.sleep(wait)

    # 汇总
    print(f'\n{"="*50}')
    print(f'安居客全部完成！共 {len(all_houses)} 条')
    print(f'{"="*50}')

    # 合并去重保存
    if all_houses:
        merged_path = os.path.join(OUTPUT_DIR, 'anjuke_all.csv')
        seen = set()
        unique = []
        for h in all_houses:
            fp = h.get('fingerprint', '')
            if fp and fp not in seen:
                seen.add(fp)
                unique.append(h)
        keys = ['title','total_price','unit_price','community',
                'district','address','lng','lat','layout','rooms','halls',
                'bathrooms','area','orientation','decoration','floor_desc',
                'floor_type','total_floors','build_year','followers','source','fingerprint']
        with open(merged_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(unique)
        print(f'去重后 {len(unique)} 条 → {merged_path}')
