# ============================================================
# 安居客二手房爬虫 — PC站 + Cookie + 指数退避 + 断点续爬
# 与链家爬虫互补，两源数据合并去重
# ============================================================

import sys
import os
import re
import time
import random
import threading

# ============================================================
# ★ 单IP全局速率控制 + 紧急熔断 + 监控（模块级，所有线程共享）
# ============================================================
# -- 全局速率限制器：确保任意两个 safe_get 之间至少间隔 MIN_GAP 秒 --
_RATE_LOCK = threading.Lock()
_LAST_REQUEST_TS = 0.0
_MIN_REQUEST_GAP = 2.0        # IP 级最小请求间隔（秒）
_REQUEST_COUNT = 0             # 总请求计数器
_ERROR_COUNT_403 = 0           # 403 计数器（用于熔断）
_CONSECUTIVE_403 = 0           # 连续 403 计数
_FUSE_BLOWN = False            # 熔断标志
_FUSE_UNTIL = 0.0              # 熔断恢复时间戳
_MONITOR_START = 0.0           # 监控起始时间
_COOKIE_PAGE_COUNT = 0          # 当前 Cookie 累计翻页数（模块级，跨区县共享）
_COOKIE_PAGE_LIMIT = 200        # 单 Cookie 翻页上限，超限后建议换 Cookie

def _rate_limit():
    """在每次 safe_get 前调用，确保全局请求间隔。"""
    global _LAST_REQUEST_TS, _REQUEST_COUNT
    with _RATE_LOCK:
        now = time.time()
        gap = _LAST_REQUEST_TS + _MIN_REQUEST_GAP - now
        if gap > 0:
            time.sleep(gap)
        _LAST_REQUEST_TS = time.time()
        _REQUEST_COUNT += 1

def _check_fuse():
    """检查熔断状态：若熔断中则阻塞等待直到恢复。"""
    global _FUSE_BLOWN, _FUSE_UNTIL
    while _FUSE_BLOWN:
        remaining = _FUSE_UNTIL - time.time()
        if remaining <= 0:
            with _RATE_LOCK:
                _FUSE_BLOWN = False
                _FUSE_UNTIL = 0.0
            print(f'\n[FUSE] 熔断恢复，继续爬取...')
            return
        print(f'[FUSE] 熔断中，剩余 {remaining:.0f}s ...')
        time.sleep(min(remaining, 30))

def _report_403():
    """收到 403 时调用，累计并判断是否触发熔断。"""
    global _ERROR_COUNT_403, _CONSECUTIVE_403, _FUSE_BLOWN, _FUSE_UNTIL
    with _RATE_LOCK:
        _ERROR_COUNT_403 += 1
        _CONSECUTIVE_403 += 1
        if _CONSECUTIVE_403 >= 5 and not _FUSE_BLOWN:
            _FUSE_BLOWN = True
            _FUSE_UNTIL = time.time() + 1800  # 30分钟冷却
            print(f'\n[FUSE] ⚡ 连续 {_CONSECUTIVE_403} 次 403！触发熔断，冷却 30 分钟...')

def _clear_consecutive_403():
    """请求成功时调用，重置连续 403 计数器。"""
    global _CONSECUTIVE_403
    with _RATE_LOCK:
        _CONSECUTIVE_403 = 0

def _emergency_stop():
    """检查是否存在紧急停止信号文件。"""
    stop_file = os.path.join(os.path.dirname(__file__), '..', 'STOP_CRAWL.txt')
    return os.path.exists(stop_file)

def _monitor_thread(stats_dict):
    """后台监控线程：每 5 分钟输出统计。"""
    while not stats_dict.get('done', False):
        time.sleep(300)  # 5 分钟
        with _RATE_LOCK:
            elapsed = time.time() - _MONITOR_START
            rpm = (_REQUEST_COUNT / elapsed * 60) if elapsed > 0 else 0
        print(f'\n[MON] ⏱ 运行 {elapsed/60:.0f}min | '
            f'请求 {_REQUEST_COUNT} 次 ({rpm:.1f}/min) | '
            f'Cookie翻页 {_COOKIE_PAGE_COUNT}/{_COOKIE_PAGE_LIMIT} | '
            f'采集 {stats_dict.get("total", 0)} 条 | '
            f'403累计 {_ERROR_COUNT_403} 次 | '
            f'熔断 {"是" if _FUSE_BLOWN else "否"}')
          
          
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

    # --- 列表页缩略图（安居客图片服务，去裁剪参数=原图） ---
    try:
        img = item.select_one('img')
        if img:
            src = img.get('src') or img.get('data-src') or ''
            house['image_url'] = re.sub(r'\?.*$', '', src) if src else ''
    except Exception:
        house['image_url'] = ''

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

def crawl_district(
        code, name, max_pages=50, 
        resume=True, 
        fetch_details=False, 
        delay_multiplier = 1.0):

    global _COOKIE_PAGE_COUNT  # 模块级 Cookie 翻页计数器

    THREAD_SEMAPHORE = threading.Semaphore(3)  # 全局最多3个区县同时请求

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
            delay *= delay_multiplier
            print(f'  [T] 等待 {delay:.1f}s ...')
            time.sleep(delay)

        # ★ 全局速率控制 + 熔断检查 + 紧急停止（每次请求前）
        _rate_limit()
        _check_fuse()
        if _emergency_stop():
            print(f'\n[STOP] 检测到 STOP_CRAWL.txt，退出爬取')
            break

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

        # ★ 安全验证页面检测（安居客 JS 挑战 / 滑块验证）
        # 特征：200 状态码 + <title>安全验证</title> + ~5KB 大小
        if '<title>安全验证</title>' in resp.text or 'antibot' in resp.text[:500]:
            print(f'  [SEC] ⚡ 触发安全验证！Cookie 被标记，暂停本区县')
            _report_403()
            _check_fuse()
            save_checkpoint('anjuke', code, pages_done, pages_failed)
            print(f'  [SEC] 建议：浏览器重新登录安居客，复制新 Cookie 到环境变量 ANJUKE_COOKIE')
            print(f'  [SEC] 当前区县 {name} 已保存断点，换 Cookie 后重新运行即可续爬')
            _COOKIE_PAGE_COUNT = _COOKIE_PAGE_LIMIT  # 强制触发翻页上限，快速结束本轮
            time.sleep(random.uniform(60, 120))
            session = refresh_session(session)
            break  # 停止本区县

        # 状态码异常处理
        if resp.status_code == 404:
            print(f'  404 — 没有更多页面，停止')
            break
        if resp.status_code == 403:
            print(f'  403 — 被禁止访问，冷却后继续...')
            _report_403()
            _check_fuse()     # 若刚触发熔断，等30分钟再继续
            time.sleep(random.uniform(30, 60))
            session = refresh_session(session)
            continue
        if resp.status_code != 200:
            print(f'  状态码 {resp.status_code}，尝试下一页...')
            session = refresh_session(session)
            continue

        # 空页面判断（< 2KB 基本不是正常列表页）
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

        # ★ 成功解析到有效房源 → 重置连续403计数 + 累计Cookie翻页
        if page_count > 0:
            _clear_consecutive_403()
            _COOKIE_PAGE_COUNT += 1

        # ★ Cookie 翻页上限检查（避免单Cookie请求过多触发安全验证）
        if _COOKIE_PAGE_COUNT >= _COOKIE_PAGE_LIMIT:
            print(f'  [LIMIT] Cookie 已翻 {_COOKIE_PAGE_COUNT} 页（上限 {_COOKIE_PAGE_LIMIT}），'
                  f'建议换 Cookie 后重新运行')
            save_checkpoint('anjuke', code, pages_done, pages_failed)
            break

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


if __name__ == '__main__':
    # ======================== 区县分级 ========================
    MAJOR_DISTRICTS = {
        '两江新区', '渝中区', '南岸区', '沙坪坝区', '九龙坡区',
        '巴南区', '北碚区', '大渡口区', '渝北区',
    }
    MID_DISTRICTS = {
        '璧山区', '永川区', '万州区', '江津区', '合川区',
        '铜梁区', '涪陵区', '长寿区', '綦江区', '荣昌区',
    }

    def get_max_pages(name):
        if name in MAJOR_DISTRICTS: return 50
        elif name in MID_DISTRICTS: return 35
        else: return 20

    def get_tier(name):
        if name in MAJOR_DISTRICTS: return '主城'
        elif name in MID_DISTRICTS: return '近郊'
        else: return '远郊'

    def is_csv_exists(name):
        csv_path = os.path.join(OUTPUT_DIR, f'anjuke_m_{name}.csv')
        return os.path.exists(csv_path)

    # ======================== 核心参数 ========================
    DELAY_MULTIPLIER = 1.5

    # ======================== 构建区县状态列表 ========================
    district_list = []
    for code, name in ANJUKE_DISTRICTS:
        cp = load_checkpoint('anjuke', code)
        pages_done = len(cp.get('pages_done', []))
        has_csv = is_csv_exists(name)
        if has_csv:
            status = '✓ 已完成'
        elif pages_done > 0:
            status = f'↻ 断点({pages_done}页)'
        else:
            status = '○ 未爬'
        district_list.append({
            'code': code, 'name': name,
            'tier': get_tier(name),
            'max_p': get_max_pages(name),
            'status': status,
            'has_csv': has_csv,
            'pages_done': pages_done,
        })

    # ======================== 启动 ========================
    print('=' * 60)
    print('安居客重庆二手房 — 交互模式')
    print(f'  延迟倍率: {DELAY_MULTIPLIER}× | Cookie翻页上限: {_COOKIE_PAGE_LIMIT}页')
    print('=' * 60)

    while True:
        # ---- 打印区县列表 ----
        print(f'\n{"─" * 55}')
        print(f'{"#":<4} {"区县":<10} {"分级":<6} {"上限":<6} {"状态"}')
        print(f'{"─" * 55}')
        for i, d in enumerate(district_list):
            print(f'{i+1:<4} {d["name"]:<10} {d["tier"]:<6} {d["max_p"]}页{"":>3} {d["status"]}')
        print(f'{"─" * 55}')
        done_count = sum(1 for d in district_list if d['has_csv'])
        pending_count = len(district_list) - done_count
        print(f'已完成 {done_count}/{len(district_list)}，待爬 {pending_count}')

        # ---- 用户输入 ----
        print(f'\n输入区县编号或名称（如 "5" 或 "沙坪坝区"），多个用逗号分隔')
        print(f'输入 "all" 顺序爬所有未完成的')
        print(f'输入 "q" 退出')
        raw = input('> ').strip()

        if raw.lower() == 'q':
            print('退出。')
            break

        # ---- 解析输入 ----
        if raw.lower() == 'all':
            targets = [d for d in district_list if not d['has_csv']]
            if not targets:
                print('所有区县已完成！')
                continue
        else:
            targets = []
            for part in raw.split(','):
                part = part.strip()
                if part.isdigit():
                    idx = int(part) - 1
                    if 0 <= idx < len(district_list):
                        targets.append(district_list[idx])
                    else:
                        print(f'  编号 {part} 无效，跳过')
                else:
                    found = [d for d in district_list if d['name'] == part]
                    if found:
                        targets.append(found[0])
                    else:
                        print(f'  区县 "{part}" 未找到，跳过')

        if not targets:
            print('没有有效的爬取目标，请重新输入。')
            continue

        # 去重：如果已经完成，询问是否重爬
        already_done = [t for t in targets if t['has_csv']]
        if already_done:
            names = ', '.join(d['name'] for d in already_done)
            ans = input(f'  {names} 已有数据，重新爬取？(y/n): ').strip().lower()
            if ans != 'y':
                targets = [t for t in targets if not t['has_csv']]
                if not targets:
                    print('没有剩余目标。')
                    continue

        # ---- 顺序爬取 ----
        print(f'\n本次爬取: {", ".join(t["name"] for t in targets)}')
        _MONITOR_START = time.time()
        monitor = threading.Thread(target=_monitor_thread, args=({'total': 0, 'done': False},), daemon=True)
        monitor.start()

        all_houses = []

        for i, target in enumerate(targets):
            code, name, max_p = target['code'], target['name'], target['max_p']

            if i > 0:
                cool = random.uniform(20, 60)
                print(f'\n[COOL] 区县间冷却 {cool:.0f}s ...')
                time.sleep(cool)

            print(f'\n{"=" * 50}')
            print(f'[{i+1}/{len(targets)}] 开始爬取 {name} ({get_tier(name)}, max {max_p} 页)')
            print(f'{"=" * 50}')

            try:
                data = crawl_district(
                    code, name,
                    max_pages=max_p,
                    resume=True,
                    fetch_details=False,
                    delay_multiplier=DELAY_MULTIPLIER,
                )
            except Exception as e:
                print(f'[{name}] 异常: {type(e).__name__}: {e}')
                continue

            if data:
                output_path = os.path.join(OUTPUT_DIR, f'anjuke_m_{name}.csv')
                save_csv(data, output_path, ANJUKE_CSV_KEYS)
                all_houses.extend(data)
                target['has_csv'] = True
                target['status'] = f'✓ 已完成({len(data)}条)'
                print(f'[{name}] 保存 {len(data)} 条 → 累计 {len(all_houses)} 条')
            else:
                target['status'] = '○ 无数据'
                print(f'[{name}] 无数据')

            # Cookie 翻页上限
            if _COOKIE_PAGE_COUNT >= _COOKIE_PAGE_LIMIT:
                print(f'\n[LIMIT] Cookie 已翻 {_COOKIE_PAGE_COUNT} 页，达上限。请换 Cookie 后继续。')
                break

            # 安全验证
            if _FUSE_BLOWN:
                print(f'\n[FUSE] 熔断中，停止本轮。')
                break

        # ---- 本轮汇总 ----
        elapsed = time.time() - _MONITOR_START
        print(f'\n本轮完成: {len(all_houses)} 条 | 耗时 {elapsed/60:.1f}min | '
              f'Cookie翻页 {_COOKIE_PAGE_COUNT}/{_COOKIE_PAGE_LIMIT} | 403: {_ERROR_COUNT_403}次')
        if all_houses:
            merged_path = os.path.join(OUTPUT_DIR, 'anjuke_all.csv')
            unique, count = deduplicate_and_save(all_houses, merged_path, ANJUKE_CSV_KEYS)
            print(f'去重后 {count} 条 → {merged_path}')

        print()  # 空行，准备下一轮输入
