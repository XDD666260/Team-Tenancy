# 链家二手房爬虫 — 基于API JSON数据
# 列表页HTML中内嵌了房源ID列表，通过API获取详细信息

import requests
from bs4 import BeautifulSoup
import re
import json
import csv
import os
import time
import random

# ===================== Cookie（从浏览器复制） =====================
COOKIE_STRING = """lianjia_uuid=84e647ad-44a3-4621-873d-fe484a1cfa17; Hm_lvt_46bf127ac9b856df503ec2dbf942b67e=1780982049; HMACCOUNT=807243DEB1481E17; _jzqc=1; _qzjc=1; _ga=GA1.2.115501286.1780982060; _ga_0VZPJRR5MM=GS2.2.s1780983078$o1$g0$t1780983078$j60$l0$h0; crosSdkDT2019DeviceId=lqz54m-h4glge-i7mgmroflq4zh3j-h60ivcfec; sensorsdata2015jssdkcross=%7B%22distinct_id%22%3A%2219eaacd69d9d7a-0d78c933abaac48-4c657b58-1474560-19eaacd69da2234%22%2C%22%24device_id%22%3A%2219eaacd69d9d7a-0d78c933abaac48-4c657b58-1474560-19eaacd69da2234%22%2C%22props%22%3A%7B%22%24latest_traffic_source_type%22%3A%22%E7%9B%B4%E6%8E%A5%E6%B5%81%E9%87%8F%22%2C%22%24latest_referrer%22%3A%22%22%2C%22%24latest_referrer_host%22%3A%22%22%2C%22%24latest_search_keyword%22%3A%22%E6%9C%AA%E5%8F%96%E5%88%B0%E5%80%BC_%E7%9B%B4%E6%8E%A5%E6%89%93%E5%BC%80%22%7D%7D; lianjia_ssid=963ff1ed-dbdc-4852-899c-5148f552f8f5; select_city=500000; _jzqckmp=1; login_ucid=2000000542622736; lianjia_token=2.0013f346814901ef7d025e6fb0380d5971; lianjia_token_secure=2.0013f346814901ef7d025e6fb0380d5971; security_ticket=CY2ijta5R/DD7ZkxwcOlg7E/DLFpkYjmorLtqBo8hg/11QK17HXphDglZ0mC5bUv3r7N3PG9jbhaKP2Il7ngX5zXO4RVzj1a1D+jcv8RCJekqRf5JIX+SvSDkNIj/J+VH0BGL+z5d1HQ10MY639BIvXQ3SZ+rDIZzdWon0jZAgg=; lfrc_=580a6bb9-8471-49fb-a448-f391eff97170; _gid=GA1.2.1172135501.1781084398; hip=caKTqctAa46S8IYpNU0ueLSbhHVzGKGH4MneBUD0AP8LVAuYhDibDTqT_dkuAhpoTntwnEv85MsbUa3Qn2QL6ex_WG2Bzo0UYqnOIePudUQNAnPyQwfrkOKw9KxIrsgd8UxdnKdIDahk-LCxHRRToZFhaqQWrjt-yg1Bk2IePNyVqE61R2Jgg3_BXHkObPuaGp_Ppw0DeMHDE0Kvv5SJciCq57X065lKby1YC6wXsbvNJd7YaYI--J5hLyw2Kw79DZZF0qY6A_2m_qmfr_Es8s3qlS18MFuSkCT0; _jzqa=1.1801755635432145400.1780982049.1781090560.1781097859.6; _jzqx=1.1780982049.1781097859.5.jzqsr=my%2Efeishu%2Ecn|jzqct=/.jzqsr=hip%2Elianjia%2Ecom|jzqct=/; _gat=1; _gat_global=1; _gat_new_global=1; _gat_dianpu_agent=1; _ga_PV625F3L95=GS2.2.s1781097871$o5$g0$t1781097871$j60$l0$h0; Hm_lpvt_46bf127ac9b856df503ec2dbf942b67e=1781097873; _jzqb=1.2.10.1781097859.1; srcid=eyJ0Ijoie1wiZGF0YVwiOlwiZGU3NmUzNjAyZmJhNzg3MGM1ZjQ1MDAxOTQ5NmMwNGY2OWM1NjJjZDFkZDI0YTBiYmM5YjE2OWQxY2UzYjkwYjBkYjNkZDU0NTllNzBjNzA1MjU2MDU0ODExYmJmYzQ4NjNiZDM4YjQwY2FhNjhlM2E5NGFhM2U4YmMwMWZkMTdjYWNmYWE2OTJjOThiNTExMmUzY2U4ZDFkYjhiMTI0OWRiNmI4MzdkZTgyNzVmYjczZTgxOWFhNjJlYWY5NjJiNWJiNDUxODQ5N2YwZjRiMDNkNjViYzk5YzQxMjllY2Q5OWI4YzU0MTkyMTY5MWI5NDUzNmQ3MjJkM2ZlYzJiYjFiYzlkYTI1ZTk5YjgyMjYyMzVjN2QyMDk3OWM0Mjg4OGFiMmZkNTQ0YWQxMDhiMjA4ODI2YjczODZhN2M0NzlcIixcImtleV9pZFwiOlwiMVwiLFwic2lnblwiOlwiNTg4ODhjNTRcIn0iLCJyIjoiaHR0cHM6Ly9jcS5saWFuamlhLmNvbS9lcnNob3VmYW5nLyIsIm9zIjoid2ViIiwidiI6IjAuMSJ9; _qzja=1.1859070309.1780982049166.1781090559684.1781097858507.1781097858507.1781097874123.0.0.0.72.6; _qzjb=1.1781097858507.2.0.0.0; _qzjto=9.3.0"""

# 解析Cookie（处理换行和空格）
cookies = {}
COOKIE_STRING = COOKIE_STRING.replace('\n', '').replace('\r', '')
for item in COOKIE_STRING.split(';'):
    item = item.strip()
    if '=' in item:
        k, v = item.split('=', 1)
        cookies[k] = v

# ===================== 请求头 =====================
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Referer': 'https://cq.lianjia.com/',
}

# API请求头（多了X-Requested-With）
API_HEADERS = {**HEADERS, 'X-Requested-With': 'XMLHttpRequest',
    'Accept': 'application/json, text/javascript, */*; q=0.01'}

# ===================== 区县列表 =====================
DISTRICTS = [
    # ('liangjiangxinqu', '两江新区'),
    # ('jiangjing', '江津区'),
    # ('yuzhong', '渝中区'),
    # ('nanan', '南岸区'),
    # ('shapingba', '沙坪坝区'),
    # ('jiulongpo', '九龙坡区'),
    # ('dadukou', '大渡口区'),
    ('banan', '巴南区'),
    ('beibei', '北碚区'),
]

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw')
os.makedirs(OUTPUT_DIR, exist_ok=True)

session = requests.Session()
session.headers.update(HEADERS)
session.cookies.update(cookies)


def parse_house_info(info_text):
    """解析 houseInfo 字段: '1室0厅 | 42.05平米 | 东南 | 精装 | 中楼层(共32层)'"""
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
    # 面积
    if len(parts) > 1:
        area_str = parts[1].replace('平米', '').replace('㎡', '').strip()
        try: result['area'] = float(area_str)
        except: pass
    # 户型
    if result['layout']:
        m = re.search(r'(\d+)室', result['layout'])
        if m: result['rooms'] = int(m.group(1))
        m = re.search(r'(\d+)厅', result['layout'])
        if m: result['halls'] = int(m.group(1))
        m = re.search(r'(\d+)卫', result['layout'])
        if m: result['bathrooms'] = int(m.group(1))
    # 楼层
    if result['floor_desc']:
        m = re.search(r'(低层|中层|高层)', result['floor_desc'])
        if m: result['floor_type'] = m.group(1)
        m = re.search(r'共(\d+)层', result['floor_desc'])
        if m: result['total_floors'] = int(m.group(1))
    return result


def get_detail_page(house_id, district_name):
    """访问详情页，获取完整数据"""
    url = f'https://cq.lianjia.com/ershoufang/{house_id}.html'
    resp = session.get(url, timeout=15)
    if resp.status_code != 200:
        return {}

    soup = BeautifulSoup(resp.text, 'lxml')

    try:
        # 总价
        total_el = soup.select_one('.total')
        total_price = float(total_el.get_text(strip=True).replace('万', '')) if total_el else 0

        # 单价
        unit_el = soup.select_one('.unitPriceValue')
        unit_text = unit_el.get_text(strip=True) if unit_el else '0'
        unit_price = float(re.sub(r'[^\d.]', '', unit_text)) if unit_text else 0

        # 小区
        community_el = soup.select_one('.communityName .info')
        community = community_el.get_text(strip=True) if community_el else ''

        # houseInfo
        info_el = soup.select_one('.houseInfo .content')
        info_text = info_el.get_text(strip=True) if info_el else ''
        info_data = parse_house_info(info_text)

        # 商圈、区县
        area_els = soup.select('.areaName .info a')
        biz_circle = area_els[0].get_text(strip=True) if len(area_els) >= 1 else ''
        district = area_els[1].get_text(strip=True) if len(area_els) >= 2 else district_name

        # 经纬度 — 从 script 标签中提取
        lng, lat = 0, 0
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and 'resblock' in script.string:
                m_lng = re.search(r'"longitude":\s*([\d.]+)', script.string)
                m_lat = re.search(r'"latitude":\s*([\d.]+)', script.string)
                if m_lng: lng = float(m_lng.group(1))
                if m_lat: lat = float(m_lat.group(1))
                break

        # 建成年代
        build_year = 0
        for script in scripts:
            if script.string and 'buildYear' in script.string:
                m = re.search(r'"buildYear":\s*"(\d+)"', script.string)
                if m: build_year = int(m.group(1))
                break

        # 关注人数
        follow_el = soup.select_one('#favCount')
        followers = int(follow_el.get_text(strip=True)) if follow_el and follow_el.get_text(strip=True).isdigit() else 0

        return {
            'id': house_id,
            'title': soup.select_one('h1').get_text(strip=True) if soup.select_one('h1') else '',
            'total_price': total_price,
            'unit_price': unit_price,
            'community': community,
            'biz_circle': biz_circle,
            'district': district,
            'address': '',
            'lng': lng,
            'lat': lat,
            **info_data,
            'build_year': build_year,
            'followers': followers,
            'source': 'lianjia',
        }
    except Exception as e:
        return {}


def crawl_district(code, name, max_pages=3):
    """爬取一个区县"""
    all_data = []

    for page in range(1, max_pages + 1):
        url = f'https://cq.lianjia.com/ershoufang/{code}/pg{page}/'
        print(f'\n--- [{name}] 第{page}页 ---')

        # 翻页前先回首页"预热"，防止触发验证码
        if page > 1:
            session.get(f'https://cq.lianjia.com/ershoufang/{code}/', timeout=15)
            time.sleep(random.uniform(3, 5))

        # 1. 获取列表页HTML（带正确的Referer）
        page_headers = HEADERS.copy()
        if page == 1:
            page_headers['Referer'] = f'https://cq.lianjia.com/ershoufang/{code}/'
        else:
            page_headers['Referer'] = f'https://cq.lianjia.com/ershoufang/{code}/pg{page-1}/'
        resp = session.get(url, headers=page_headers, timeout=15)

        print(f'  状态码: {resp.status_code}  长度: {len(resp.text)}')

        if resp.status_code != 200 or len(resp.text) < 2000:
            print(f'  列表页请求失败，可能触发验证码，跳过剩余页')
            break

        # 2. 从HTML中提取房源ID列表
        soup = BeautifulSoup(resp.text, 'lxml')

        # 2. 从HTML中提取房源ID列表
        house_ids = []
        import re

        # 调试：在第1页搜索各种ID格式
        if page == 1:
            # 搜所有11-12位数字
            all_ids = re.findall(r'\b(\d{11,12})\b', resp.text)
            print(f'  调试: 页面找到 {len(all_ids)} 个11-12位数字, 前5个: {all_ids[:5]}')
            # 搜 /ershoufang/数字.html 格式
            url_ids = re.findall(r'/ershoufang/(\d{11,12})\.html', resp.text)
            print(f'  调试: /ershoufang/ID.html 格式找到 {len(url_ids)} 个, 前5个: {url_ids[:5]}')

        # 方法1：从链接中提取房源ID（最常见）
        url_id_matches = re.findall(r'/ershoufang/(\d+)\.html', resp.text)
        if url_id_matches:
            seen = set()
            for hid in url_id_matches:
                if hid not in seen:
                    seen.add(hid)
                    house_ids.append(hid)
            print(f'  从链接提取到 {len(house_ids)} 个房源ID')

        # 备选：从 .sellListContent 的 data-id 属性提取
        if not house_ids:
            items = soup.select('.sellListContent li[data-id]')
            house_ids = [item.get('data-id') for item in items if item.get('data-id')]
            if house_ids:
                print(f'  从data-id属性提取到 {len(house_ids)} 个房源ID')

        # 3. 逐个访问详情页
        for i, hid in enumerate(house_ids):
            print(f'  [{i+1}/{len(house_ids)}] {hid}...', end=' ')
            data = get_detail_page(hid, name)
            if data:
                all_data.append(data)
                print(f'✅ {data["title"][:20]} | {data["total_price"]}万')
            else:
                print('❌')

            time.sleep(random.uniform(1, 2))  # 详情页间隔

    print(f'  [{name}] 累计 {len(all_data)} 条')
    time.sleep(random.uniform(2, 4))  # 翻页间隔

    return all_data


# ===================== 主流程 =====================
if __name__ == '__main__':
    all_houses = []

    for code, name in DISTRICTS:
        print(f'\n{"="*40}')
        print(f'开始爬取 {name}...')
        print(f'{"="*40}')

        data = crawl_district(code, name, max_pages=3)  # 先每区3页测试
        all_houses.extend(data)

        # 每爬完一个区县就保存一次
        output_path = os.path.join(OUTPUT_DIR, f'lianjia_{name}.csv')
        if data:
            keys = ['id','title','total_price','unit_price','community','biz_circle',
                    'district','address','lng','lat','layout','rooms','halls','bathrooms',
                    'area','orientation','decoration','floor_desc','floor_type',
                    'total_floors','build_year','followers','source']
            with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(data)

        print(f'\n>>> {name}完成，本区{len(data)}条，累计{len(all_houses)}条')
        time.sleep(random.uniform(3, 5))  # 换区县间隔

    print(f'\n{"="*40}')
    print(f'全部完成！共 {len(all_houses)} 条')
    print(f'{"="*40}')