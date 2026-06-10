# 安居客二手房爬虫
# 与链家爬虫互补，两源数据合并去重

import requests
from bs4 import BeautifulSoup
import re
import csv
import os
import time
import random
import hashlib

# ===================== Cookie（从浏览器复制） =====================
COOKIE_STRING = """aQQ_ajkguid=F7B4D023-2524-4E8F-9FA7-FB4B466A414A; sessid=0ADC5D26-DE20-42FC-B1C9-C3DF9A7CCDFF; ctid=20; twe=2; id58=uVcyWmonw3RqSxvUFwlTAg==; xxzlclientid=9e9f197b-4ac8-4fe0-b525-1780990835353; xxzlxxid=pfmx9YPrZMngaMg5IB8XhLUfiXG951fL3E4v4TYV7zQvgVqboAu0QQrrHcrCK6A494Dv; obtain_by=1; xxzlbbid=pfmbRKBxxeD3YHkVphZEbLbECGY88YcxPCZhssNIWgvpz4AO42cfftjxMxNqnl1aj3FA0uuvA2o4JqOELhIcA39PPcXOTmlLH5l8ZMpQVITrEg4/kx43I5oeFZyh7qazWzHnt7p0hgExNzgxMDg3NTM3MzMwNDAy_1; fzq_h=f8e2b59bb392b6e1f0cf822f12516317_1781087662383_ec260a0137dc4b4693351482f40131d5_47901724934887724844252811768033755437; fzq_js_anjuke_ershoufang_pc=f2c9d58d02b287e6e913925d1edf5950_1781087661950_25"""

cookies = {}
for item in COOKIE_STRING.replace('\n','').replace('\r','').split(';'):
    item = item.strip()
    if '=' in item:
        k, v = item.split('=', 1)
        cookies[k] = v

# ===================== 请求配置 =====================
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
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
]

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw')
os.makedirs(OUTPUT_DIR, exist_ok=True)

session = requests.Session()
session.headers.update(HEADERS)
session.cookies.update(cookies)


def make_fingerprint(house):
    """生成房源指纹，用于去重"""
    key = f"{house.get('community','')}|{house.get('district','')}|{house.get('area',0)}|{house.get('rooms',0)}|{house.get('total_price',0)}"
    return hashlib.md5(key.encode()).hexdigest()


def parse_house_info(item):
    """解析安居客房源卡片"""
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

        # 信息行（户型/面积/朝向/装修/楼层）
        info_el = item.select_one('.property-content-info')
        info_text = info_el.get_text(strip=True) if info_el else ''

        # 解析信息行：安居客格式类似 "3室2厅 | 120㎡ | 南 | 精装 | 中层"
        parts = [p.strip() for p in info_text.replace('\n',' ').split('|')]

        layout = parts[0] if len(parts) > 0 else ''
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
        if len(parts) > 1:
            area_str = parts[1].replace('㎡','').replace('平米','').strip()
            try: house['area'] = float(area_str)
            except: pass

        house['orientation'] = parts[2] if len(parts) > 2 else ''
        house['decoration'] = parts[3] if len(parts) > 3 else ''

        floor_desc = parts[4] if len(parts) > 4 else ''
        house['floor_desc'] = floor_desc
        house['floor_type'] = ''
        house['total_floors'] = 0
        if '低层' in floor_desc: house['floor_type'] = '低层'
        elif '中层' in floor_desc: house['floor_type'] = '中层'
        elif '高层' in floor_desc: house['floor_type'] = '高层'
        fm = re.search(r'共(\d+)层', floor_desc)
        if fm: house['total_floors'] = int(fm.group(1))

        # 其他
        house['biz_circle'] = ''
        house['address'] = ''
        house['build_year'] = 0
        house['lng'] = house['lat'] = 0
        house['followers'] = 0
        house['source'] = 'anjuke'

    except Exception as e:
        pass

    return house


def crawl_district(code, name, max_pages=3):
    """爬取一个区县"""
    all_data = []

    for page in range(1, max_pages + 1):
        if page == 1:
            url = f'https://chongqing.anjuke.com/sale/{code}/'
        else:
            url = f'https://chongqing.anjuke.com/sale/{code}/p{page}/'

        print(f'\n--- [{name}] 第{page}页 ---')

        if page > 1:
            time.sleep(random.uniform(3, 5))

        page_headers = HEADERS.copy()
        if page > 1:
            page_headers['Referer'] = f'https://chongqing.anjuke.com/sale/{code}/p{page-1}/'
        else:
            page_headers['Referer'] = 'https://chongqing.anjuke.com/sale/'

        resp = session.get(url, headers=page_headers, timeout=15)
        print(f'  状态码: {resp.status_code}  长度: {len(resp.text)}')

        if resp.status_code != 200 or len(resp.text) < 2000:
            print(f'  请求失败，跳过剩余页')
            break

        soup = BeautifulSoup(resp.text, 'lxml')

        # 安居客房源列表选择器
        items = soup.select('.property-content')
        if not items:
            # 备选选择器
            items = soup.select('li[class*=property]')
        if not items:
            items = soup.select('.list-item')

        print(f'  找到 {len(items)} 个房源卡片')

        if not items and page == 1:
            # 保存第一页HTML调试
            debug_path = os.path.join(OUTPUT_DIR, f'debug_anjuke_{code}.html')
            with open(debug_path, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(resp.text)
            print(f'  已保存调试文件: {debug_path}')

        for item in items:
            house = parse_house_info(item)
            if house.get('title') and house.get('total_price', 0) > 0:
                house['district'] = name
                house['fingerprint'] = make_fingerprint(house)
                all_data.append(house)

        print(f'  [{name}] 本页有效 {len([h for h in all_data if h.get("total_price",0)>0])} 条，累计 {len(all_data)} 条')

        if len(items) == 0:
            break

    return all_data


# ===================== 主流程 =====================
if __name__ == '__main__':
    all_houses = []

    for code, name in DISTRICTS:
        print(f'\n{"="*40}')
        print(f'开始爬取安居客 {name}...')
        print(f'{"="*40}')

        data = crawl_district(code, name, max_pages=50)
        all_houses.extend(data)

        # 每区保存
        if data:
            output_path = os.path.join(OUTPUT_DIR, f'anjuke_{name}.csv')
            keys = ['title','total_price','unit_price','community','biz_circle',
                    'district','address','lng','lat','layout','rooms','halls',
                    'bathrooms','area','orientation','decoration','floor_desc',
                    'floor_type','total_floors','build_year','followers','source','fingerprint']
            with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(data)
            print(f'  已保存 {output_path}')

        time.sleep(random.uniform(2, 4))

    print(f'\n{"="*40}')
    print(f'安居客全部完成！共 {len(all_houses)} 条')
    print(f'{"="*40}')
