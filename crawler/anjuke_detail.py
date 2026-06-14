# ============================================================
# 安居客详情爬虫 — 单线程 + 进详情页 + 全字段
# 优势: 获取所有字段(坐标/装修/年代/楼层/卫生间)
# 缺陷: 速度慢(每个房源需请求桌面站+移动站)
# 适用: 对已有列表数据补全字段, 或小规模精确爬取
# ============================================================

import requests, re, csv, os, time, random, hashlib, json
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

# ==================== 代理 ====================
PROXY_URL = 'http://用户名:密码@隧道地址:端口'
PROXIES = {'http': PROXY_URL, 'https': PROXY_URL}

UA_MOBILE = [
    'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
]
UA_DESKTOP = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
]

DISTRICTS = [
    ('yubei','两江新区'),('yuzhong','渝中区'),('nanana','南岸区'),
    ('shapingba','沙坪坝区'),('jiulongpo','九龙坡区'),('banan','巴南区'),
    ('beibei','北碚区'),('dadukou','大渡口区'),('bishanqu','璧山区'),
    ('yongchuanqu','永川区'),('wanzhouqu','万州区'),('jiangjinqu','江津区'),
    ('hechuanqu','合川区'),('tongliangqu','铜梁区'),('fulingqu','涪陵区'),
    ('changshouqu','长寿区'),('rongchangqu','荣昌区'),('qijiangqu','綦江区'),
    ('nanchuanqu','南川区'),('dazhuqu','大足区'),('tongnanqu','潼南区'),
    ('kaizhoukuaixian','开州区'),('dainjiangxian','垫江县'),
    ('liangpingxian','梁平区'),('wansheng','万盛区'),('fengjiexian','奉节县'),
    ('yunyangxian','云阳县'),('zhongxian','忠县'),('wuxixian','巫溪县'),
    ('qianjiangqu','黔江区'),('wulongxian','武隆区'),('cqwushanxian','巫山县'),
    ('chengkouxian','城口县'),('pengshuimiaozutujiazuzhixian','彭水县'),
    ('xiushantujiazumiaozuzhixian','秀山县'),('shizhutujiazuzhixian','石柱县'),
    ('youyangtujiazumiaozuzhixian','酉阳县'),('fengduxian','丰都县'),
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, '..', 'data', 'raw')
CHECKPOINT_DIR = os.path.join(BASE_DIR, '..', 'data', 'checkpoints')
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CHECKPOINT_DIR, exist_ok=True)

CSV_KEYS = [
    'id','title','total_price','unit_price','community','district','address',
    'lng','lat','layout','rooms','halls','bathrooms','area','orientation',
    'decoration','floor_desc','floor_type','total_floors','build_year',
    'tags','source','fingerprint'
]
DETAIL_WORKERS = 4  # 每个区县的详情页并行线程数

# ==================== HTTP ====================
def mobile_get(url, timeout=60):
    """移动站请求"""
    headers = {
        'User-Agent': random.choice(UA_MOBILE),
        'Accept': 'text/html,application/xhtml+xml',
        'Connection': 'close',
    }
    for _ in range(4):
        try:
            resp = requests.get(url, headers=headers, proxies=PROXIES, timeout=timeout)
            resp.text  # 强制读取
            return resp
        except Exception:
            time.sleep(random.uniform(3, 8))
    return None

def desktop_get(url, timeout=50):
    """桌面站请求"""
    headers = {
        'User-Agent': random.choice(UA_DESKTOP),
        'Accept': 'text/html',
        'Connection': 'close',
    }
    for _ in range(3):
        try:
            resp = requests.get(url, headers=headers, proxies=PROXIES, timeout=timeout)
            resp.text
            return resp
        except Exception:
            time.sleep(2)
    return None

# ==================== 指纹 ====================
def fingerprint(community, district, area, rooms, total_price):
    key = f"{community}|{district}|{area}|{rooms}|{total_price}"
    return hashlib.md5(key.encode()).hexdigest()

# ==================== 断点 ====================
def load_checkpoint(code):
    path = os.path.join(CHECKPOINT_DIR, f'anjuke_detail_{code}.json')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'pages_done': []}

def save_checkpoint(code, pages_done):
    path = os.path.join(CHECKPOINT_DIR, f'anjuke_detail_{code}.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({'pages_done': pages_done}, f)

# ==================== 列表页解析(同快速版) ====================
def parse_list_page(html):
    """从移动站列表页提取房源基本信息"""
    soup = BeautifulSoup(html, 'lxml')
    items = soup.select('li.item-wrap')
    results = []

    for item in items:
        try:
            a_el = item.find('a') or item
            href = a_el.get('href', '') if hasattr(a_el, 'get') else ''
            id_match = re.search(r'/S(\d+)/', href)
            hid = id_match.group(1) if id_match else ''

            title_el = item.select_one('.content-title')
            title = title_el.get_text(strip=True) if title_el else ''
            if not title:
                continue

            descs = item.select('.content-desc')
            desc_texts = [d.get_text(strip=True) for d in descs if d.get_text(strip=True)]
            layout = desc_texts[0] if len(desc_texts) > 0 else ''
            area_str = desc_texts[1] if len(desc_texts) > 1 else '0'
            orientation = desc_texts[2] if len(desc_texts) > 2 else ''
            biz_circle = desc_texts[3] if len(desc_texts) > 3 else ''

            area = 0.0
            try: area = float(re.sub(r'[^\d.]', '', area_str))
            except: pass

            price_el = item.select_one('.price') or item.select_one('[class*=price]')
            price_text = price_el.get_text(strip=True) if price_el else '0'
            total_price = 0.0
            try: total_price = float(re.sub(r'[^\d.]', '', price_text))
            except: pass

            if total_price <= 0: continue

            community = ''
            for img in item.find_all('img'):
                alt = img.get('alt', '')
                cm = re.match(r'(.+?)\d+室', alt)
                if cm: community = cm.group(1); break
            if not community:
                tm = re.match(r'\S+\s+(.+?)\s+[一二三四五六七八九\d]+房', title)
                if tm: community = tm.group(1)

            rooms = halls = 0
            if layout:
                rm = re.search(r'(\d+)室', layout)
                if rm: rooms = int(rm.group(1))
                hm = re.search(r'(\d+)厅', layout)
                if hm: halls = int(hm.group(1))

            tags = '|'.join(t.get_text(strip=True) for t in item.select('.tag-wrap span, .tag'))

            results.append({
                'id': hid, 'title': title, 'total_price': total_price,
                'unit_price': 0, 'community': community, 'district': '',
                'address': biz_circle, 'lng': 0, 'lat': 0,
                'layout': layout, 'rooms': rooms, 'halls': halls,
                'bathrooms': 0, 'area': area, 'orientation': orientation,
                'decoration': '', 'floor_desc': '', 'floor_type': '',
                'total_floors': 0, 'build_year': 0,
                'tags': tags, 'source': 'anjuke',
            })
        except Exception:
            continue
    return results

# ==================== 详情页获取 ====================
def fetch_detail(house):
    """
    为一个房源补全所有详情页字段。
    1) 桌面站详情页: 经纬度(<meta name="location" coord="...">)
    2) 移动站详情页: 装修/年代/楼层/卫生间/单价(<meta name="keywords">)
    """
    hid = house['id']
    if not hid:
        return

    # --- 桌面站: 经纬度 ---
    for _ in range(3):
        try:
            resp = desktop_get(f'https://chongqing.anjuke.com/prop/view/S{hid}')
            if resp and resp.status_code == 200:
                coord_match = re.search(r'coord=([\d.]+),([\d.]+)', resp.text)
                if coord_match:
                    house['lng'] = float(coord_match.group(1))
                    house['lat'] = float(coord_match.group(2))
                    break
        except Exception:
            time.sleep(1)

    # --- 移动站: 其他字段 ---
    for _ in range(3):
        try:
            resp = mobile_get(f'https://m.anjuke.com/cq/sale/S{hid}/')
            if not resp or resp.status_code != 200:
                continue

            # meta keywords: "126万,3室2厅1卫,91.77平米,13730元/平米,2017年,北,精装修"
            kw = re.search(r'<meta[^>]+name="keywords"[^>]+content="([^"]+)"', resp.text)
            if not kw:
                kw = re.search(r'<meta[^>]+content="([^"]+)"[^>]+name="keywords"', resp.text)
            if kw:
                content = kw.group(1)

                # 卫生间: N室N厅N卫
                wm = re.search(r'(\d+)室\d+厅(\d+)卫', content)
                if wm:
                    house['bathrooms'] = int(wm.group(2))

                # 单价: NNNN元/平米
                upm = re.search(r'([\d.]+)\s*元/平米', content)
                if upm:
                    house['unit_price'] = float(upm.group(1))

                # 年代: NNNN年
                ym = re.search(r'(\d{4})年', content)
                if ym:
                    house['build_year'] = int(ym.group(1))

                # 装修: 精装修/简装/毛坯/豪装
                dm = re.search(r'(精装修|精装|简装|毛坯|豪装)', content)
                if dm:
                    house['decoration'] = dm.group(1)

            # 楼层信息从页面文本提取
            soup = BeautifulSoup(resp.text, 'lxml')
            page_text = soup.get_text(' ', strip=True)
            fm = re.search(r'(低层|中层|高层|低楼层|中楼层|高楼层).*?共\s*(\d+)\s*层', page_text)
            if fm:
                house['floor_desc'] = fm.group(0)
                house['total_floors'] = int(fm.group(2))
                ltm = re.search(r'(低层|中层|高层|低楼层|中楼层|高楼层)', fm.group(0))
                if ltm:
                    house['floor_type'] = ltm.group(1)
            else:
                fm2 = re.search(r'共\s*(\d+)\s*层', page_text)
                if fm2:
                    house['total_floors'] = int(fm2.group(1))
                ltm2 = re.search(r'(低层|中层|高层|低楼层|中楼层|高楼层)', page_text)
                if ltm2:
                    house['floor_desc'] = ltm2.group(1)
                    house['floor_type'] = ltm2.group(1)

            break
        except Exception:
            time.sleep(1)

    # --- 字段兜底计算 ---
    if house['unit_price'] == 0 and house['area'] > 0 and house['total_price'] > 0:
        house['unit_price'] = round(house['total_price'] * 10000 / house['area'], 2)

    if house['bathrooms'] == 0:
        wm = re.search(r'(\d+)卫', house.get('layout', ''))
        if wm:
            house['bathrooms'] = int(wm.group(1))
        else:
            house['bathrooms'] = 1 if house['rooms'] <= 2 else 2

    time.sleep(random.uniform(2, 5))

# ==================== 区县爬取 ====================
def crawl_district(code, name, max_pages=80):
    """
    单线程爬取一个区县: 列表页→详情页
    返回全字段房源列表
    """
    all_data = []
    checkpoint = load_checkpoint(code)
    pages_done = list(checkpoint.get('pages_done', []))
    completed = set(pages_done)
    if completed:
        print(f'  [{name}] 断点: {len(completed)}页')

    for page in range(1, max_pages + 1):
        if page in completed:
            continue

        url = f'https://m.anjuke.com/cq/sale/{code}/p{page}/' if page > 1 else f'https://m.anjuke.com/cq/sale/{code}/'

        if page > 1:
            time.sleep(random.uniform(15, 30))

        resp = mobile_get(url)
        if resp is None or len(resp.text) < 5000:
            time.sleep(30)
            resp = mobile_get(url)
            if resp is None or len(resp.text) < 5000:
                continue

        if 'antibot' in resp.text or 'xxzlGatewayUrl' in resp.text:
            continue

        houses = parse_list_page(resp.text)
        if not houses and page > 1:
            break
        if not houses:
            continue

        for h in houses:
            h['district'] = name

        # 并行抓详情页
        if houses:
            with ThreadPoolExecutor(max_workers=DETAIL_WORKERS) as ex:
                list(ex.map(fetch_detail, houses))

        for h in houses:
            h['fingerprint'] = fingerprint(
                h['community'], h['district'], h['area'],
                h['rooms'], h['total_price']
            )

        all_data.extend(houses)
        print(f'  [{name}] p{page}: {len(houses)}条,累计{len(all_data)}')

        pages_done.append(page)
        save_checkpoint(code, pages_done)

    print(f'  [{name}] 完成: {len(pages_done)}页, {len(all_data)}条')
    return all_data

# ==================== 主流程 ====================
if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        # 指定区县
        target = sys.argv[1]
        districts = [(c, n) for c, n in DISTRICTS if n == target or c == target]
        if not districts:
            print(f'未找到区县: {target}')
            sys.exit(1)
    else:
        districts = DISTRICTS

    print(f'安居客详情爬虫 v1: 单线程区县, {DETAIL_WORKERS}线程详情页')
    print(f'目标区县: {len(districts)}')

    all_data = []
    for code, name in districts:
        print(f'\n=== {name} ({code}) ===')
        data = crawl_district(code, name)
        all_data.extend(data)
        if data:
            out = os.path.join(OUTPUT_DIR, f'anjuke_detail_{name}.csv')
            with open(out, 'w', newline='', encoding='utf-8-sig') as f:
                w = csv.DictWriter(f, fieldnames=CSV_KEYS, extrasaction='ignore')
                w.writeheader()
                w.writerows(data)
            lng_ok = sum(1 for h in data if h.get('lng', 0) > 0)
            print(f'  CSV已保存: {out} ({len(data)}条, 坐标{lng_ok})')

    # 汇总
    if len(districts) > 1 and all_data:
        seen = set()
        unique = []
        for h in all_data:
            fp = h.get('fingerprint', '')
            if fp and fp not in seen:
                seen.add(fp)
                unique.append(h)
        merged = os.path.join(OUTPUT_DIR, 'anjuke_all_detail.csv')
        with open(merged, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.DictWriter(f, fieldnames=CSV_KEYS, extrasaction='ignore')
            w.writeheader()
            w.writerows(unique)
        print(f'\n去重汇总: {len(unique)}条 -> {merged}')
