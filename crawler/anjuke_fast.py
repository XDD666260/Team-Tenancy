# ============================================================
# 安居客快速爬虫 — 多线程 + 隧道代理 + 纯列表页
# 优势: 速度快(6区并行), 代理自动换IP, 可快速达到5万+
# 缺陷: 不进详情页, 缺少 lng/lat/decoration/floor_desc/build_year
# ============================================================

import requests, re, csv, os, time, random, hashlib, json, threading
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==================== 代理 ====================
# 快代理隧道: 每次请求自动分配新IP
# 使用时替换为实际代理地址
PROXY_URL = 'http://用户名:密码@隧道地址:端口'
PROXIES = {'http': PROXY_URL, 'https': PROXY_URL}

# ==================== UA ====================
UA_MOBILE = [
    'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 14; SM-S9080) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Mobile Safari/537.36',
]

# ==================== 区县列表(安居客移动站编码) ====================
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

# ==================== CSV字段定义 ====================
CSV_KEYS = [
    'id','title','total_price','unit_price','community','district','address',
    'lng','lat','layout','rooms','halls','bathrooms','area','orientation',
    'decoration','floor_desc','floor_type','total_floors','build_year',
    'tags','source','fingerprint'
]
WRITE_LOCK = threading.Lock()
WORKERS = 6  # 并行区县数

# ==================== HTTP ====================
def mobile_get(url, timeout=60):
    """带代理的移动站请求, 强制Connection:close切换IP"""
    headers = {
        'User-Agent': random.choice(UA_MOBILE),
        'Accept': 'text/html,application/xhtml+xml',
        'Connection': 'close',
    }
    for attempt in range(4):
        try:
            resp = requests.get(url, headers=headers, proxies=PROXIES, timeout=timeout)
            resp.text  # 强制读取, 捕获ChunkedEncodingError
            return resp
        except Exception:
            time.sleep(random.uniform(3, 8))
    return None

# ==================== 指纹 ====================
def fingerprint(community, district, area, rooms, total_price):
    key = f"{community}|{district}|{area}|{rooms}|{total_price}"
    return hashlib.md5(key.encode()).hexdigest()

# ==================== 断点 ====================
def load_checkpoint(code):
    path = os.path.join(CHECKPOINT_DIR, f'anjuke_fast_{code}.json')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'pages_done': []}

def save_checkpoint(code, pages_done):
    path = os.path.join(CHECKPOINT_DIR, f'anjuke_fast_{code}.json')
    with WRITE_LOCK:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'pages_done': pages_done}, f)

# ==================== 列表页解析 ====================
def parse_list_page(html):
    """从移动站列表页HTML提取房源基本信息"""
    soup = BeautifulSoup(html, 'lxml')
    items = soup.select('li.item-wrap')
    results = []

    for item in items:
        try:
            # 房源ID (从链接提取)
            a_el = item.find('a') or item
            href = a_el.get('href', '') if hasattr(a_el, 'get') else ''
            id_match = re.search(r'/S(\d+)/', href)
            hid = id_match.group(1) if id_match else ''

            # 标题
            title_el = item.select_one('.content-title')
            title = title_el.get_text(strip=True) if title_el else ''
            if not title:
                continue

            # 描述字段: 户型 / 面积 / 朝向 / 区 / 商圈
            descs = item.select('.content-desc')
            desc_texts = [d.get_text(strip=True) for d in descs if d.get_text(strip=True)]
            layout = desc_texts[0] if len(desc_texts) > 0 else ''
            area_str = desc_texts[1] if len(desc_texts) > 1 else '0'
            orientation = desc_texts[2] if len(desc_texts) > 2 else ''
            biz_circle = desc_texts[3] if len(desc_texts) > 3 else ''

            # 面积
            area = 0.0
            try:
                area = float(re.sub(r'[^\d.]', '', area_str))
            except ValueError:
                pass

            # 总价
            price_el = item.select_one('.price') or item.select_one('[class*=price]')
            price_text = price_el.get_text(strip=True) if price_el else '0'
            total_price = 0.0
            try:
                total_price = float(re.sub(r'[^\d.]', '', price_text))
            except ValueError:
                pass

            if total_price <= 0:
                continue

            # 单价(列表页可能为空, 后续用 total_price/area 计算)
            unit_el = item.select_one('.unit-price')
            unit_text = unit_el.get_text(strip=True) if unit_el else '0'
            unit_price = 0.0
            try:
                unit_price = float(re.sub(r'[^\d.]', '', unit_text))
            except ValueError:
                pass

            # 小区名(从img alt或标题提取)
            community = ''
            for img in item.find_all('img'):
                alt = img.get('alt', '')
                cm = re.match(r'(.+?)\d+室', alt)
                if cm:
                    community = cm.group(1)
                    break
            if not community:
                title_match = re.match(r'\S+\s+(.+?)\s+[一二三四五六七八九\d]+房', title)
                if title_match:
                    community = title_match.group(1)

            # 户型解析
            rooms = halls = 0
            if layout:
                rm = re.search(r'(\d+)室', layout)
                if rm:
                    rooms = int(rm.group(1))
                hm = re.search(r'(\d+)厅', layout)
                if hm:
                    halls = int(hm.group(1))

            # 标签
            tags = '|'.join(t.get_text(strip=True) for t in item.select('.tag-wrap span, .tag'))

            results.append({
                'id': hid,
                'title': title,
                'total_price': total_price,
                'unit_price': unit_price,
                'community': community,
                'district': '',          # 由调用方填入
                'address': biz_circle,
                'lng': 0, 'lat': 0,     # 列表页无坐标
                'layout': layout,
                'rooms': rooms,
                'halls': halls,
                'bathrooms': 0,          # 列表页无卫生间数
                'area': area,
                'orientation': orientation,
                'decoration': '',         # 列表页无装修
                'floor_desc': '',         # 列表页无楼层描述
                'floor_type': '',
                'total_floors': 0,
                'build_year': 0,          # 列表页无建造年代
                'tags': tags,
                'source': 'anjuke',
            })
        except Exception:
            continue

    return results

# ==================== 字段计算 ====================
def compute_fields(house):
    """计算可推导字段"""
    # unit_price = total_price * 10000 / area
    if house['unit_price'] == 0 and house['area'] > 0 and house['total_price'] > 0:
        house['unit_price'] = round(house['total_price'] * 10000 / house['area'], 2)

    # bathrooms: 从layout提取, 或按室数推断
    if house['bathrooms'] == 0:
        wm = re.search(r'(\d+)卫', house.get('layout', ''))
        if wm:
            house['bathrooms'] = int(wm.group(1))
        else:
            house['bathrooms'] = 1 if house['rooms'] <= 2 else 2

# ==================== 单区县爬取 ====================
def crawl_district(code, name, max_pages=80):
    """爬取一个区县的所有列表页, 不进详情页"""
    all_data = []
    checkpoint = load_checkpoint(code)
    pages_done = list(checkpoint.get('pages_done', []))
    completed = set(pages_done)

    if completed:
        print(f'  [{name}] 断点续爬: {len(completed)}页已完成')

    for page in range(1, max_pages + 1):
        if page in completed:
            continue

        # 构建URL
        if page == 1:
            url = f'https://m.anjuke.com/cq/sale/{code}/'
        else:
            url = f'https://m.anjuke.com/cq/sale/{code}/p{page}/'

        # 页间延迟
        if page > 1:
            delay = random.uniform(10, 20)
            time.sleep(delay)

        # 请求列表页
        resp = mobile_get(url)
        if resp is None or len(resp.text) < 5000:
            print(f'  [{name}] p{page}: 请求失败, 重试...')
            time.sleep(30)
            resp = mobile_get(url)
            if resp is None or len(resp.text) < 5000:
                print(f'  [{name}] p{page}: 跳过')
                continue

        # 检测反爬
        if 'antibot' in resp.text or 'xxzlGatewayUrl' in resp.text:
            print(f'  [{name}] p{page}: 被拦截')
            continue

        # 解析
        houses = parse_list_page(resp.text)
        for h in houses:
            h['district'] = name
            compute_fields(h)
            h['fingerprint'] = fingerprint(
                h['community'], h['district'], h['area'],
                h['rooms'], h['total_price']
            )

        all_data.extend(houses)
        print(f'  [{name}] p{page}: {len(houses)}条, 累计{len(all_data)}')

        if len(houses) > 0:
            pages_done.append(page)
            save_checkpoint(code, pages_done)

        if len(houses) == 0 and page > 1:
            break

    print(f'  [{name}] 完成: {len(pages_done)}页, {len(all_data)}条')
    return all_data

# ==================== 区县保存(线程安全) ====================
def crawl_and_save(code, name):
    data = crawl_district(code, name)
    if data:
        out = os.path.join(OUTPUT_DIR, f'anjuke_fast_{name}.csv')
        with WRITE_LOCK:
            with open(out, 'w', newline='', encoding='utf-8-sig') as f:
                w = csv.DictWriter(f, fieldnames=CSV_KEYS, extrasaction='ignore')
                w.writeheader()
                w.writerows(data)
    return code, name, data

# ==================== 主流程 ====================
if __name__ == '__main__':
    print(f'安居客快速爬虫 v1: {WORKERS}线程并行, 纯列表页')
    print(f'覆盖区县: {len(DISTRICTS)} 个')

    all_data = []
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {executor.submit(crawl_and_save, c, n): (c, n) for c, n in DISTRICTS}
        for future in as_completed(futures):
            c, n = futures[future]
            try:
                _, name, data = future.result()
                all_data.extend(data)
                done = len([f for f in futures if f.done()])
                print(f'>>> [{done}/{len(DISTRICTS)}] {name}: {len(data)}条, 累计{len(all_data)}')
            except Exception as e:
                print(f'>>> [{n}] 异常: {e}')

    # 去重合并
    seen = set()
    unique = []
    for h in all_data:
        fp = h.get('fingerprint', '')
        if fp and fp not in seen:
            seen.add(fp)
            unique.append(h)

    merged = os.path.join(OUTPUT_DIR, 'anjuke_all_fast.csv')
    with open(merged, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=CSV_KEYS, extrasaction='ignore')
        w.writeheader()
        w.writerows(unique)

    print(f'\n总计: {len(all_data)}条, 去重: {len(unique)}条 -> {merged}')

    # 清理临时文件
    import glob
    for pat in ['data/raw/debug_*.html', 'data/raw/*test*', 'data/temp_*.py']:
        for fpath in glob.glob(os.path.join(BASE_DIR, '..', pat)):
            try: os.remove(fpath)
            except: pass
