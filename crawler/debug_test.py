# crawler/debug_test.py
import requests
from bs4 import BeautifulSoup

# 从 Chrome Console 复制过来的完整 cookie
COOKIE_STRING = "lianjia_uuid=84e647ad-44a3-4621-873d-fe484a1cfa17; Hm_lvt_46bf127ac9b856df503ec2dbf942b67e=1780982049; HMACCOUNT=807243DEB1481E17; _jzqc=1; _qzjc=1; _ga=GA1.2.115501286.1780982060; _ga_0VZPJRR5MM=GS2.2.s1780983078$o1$g0$t1780983078$j60$l0$h0; crosSdkDT2019DeviceId=lqz54m-h4glge-i7mgmroflq4zh3j-h60ivcfec; sensorsdata2015jssdkcross=%7B%22distinct_id%22%3A%2219eaacd69d9d7a-0d78c933abaac48-4c657b58-1474560-19eaacd69da2234%22%2C%22%24device_id%22%3A%2219eaacd69d9d7a-0d78c933abaac48-4c657b58-1474560-19eaacd69da2234%22%2C%22props%22%3A%7B%22%24latest_traffic_source_type%22%3A%22%E7%9B%B4%E6%8E%A5%E6%B5%81%E9%87%8F%22%2C%22%24latest_referrer%22%3A%22%22%2C%22%24latest_referrer_host%22%3A%22%22%2C%22%24latest_search_keyword%22%3A%22%E6%9C%AA%E5%8F%96%E5%88%B0%E5%80%BC_%E7%9B%B4%E6%8E%A5%E6%89%93%E5%BC%80%22%7D%7D; srcid=eyJ0Ijoie1wiZGF0YVwiOlwiZGU3NmUzNjAyZmJhNzg3MGM1ZjQ1MDAxOTQ5NmMwNGY2OWM1NjJjZDFkZDI0YTBiYmM5YjE2OWQxY2UzYjkwYjk1YTg2NmEwNmM4MGRjY2IyZjFjNTE3NmVkNDgzYWM3MGNiZGMyMWYwYjA3ODIzOWFkMjc2ZmM3YzE2MTBhMTUxYWMzZjIyMTJiMDI3OTk5MTBiYTcyODJkYjU5NGM1MzdjNjc3OWFhYWEzNjg4MDU3NGJlOTM5NjM1Yzc4YzBhODk4MTI5YmJiOTUyZDcxNDA0MzU3NTliN2M3N2MwOWRlMzllY2Q1NzcxNWNiNjk1NTY5NWM1YjY2MDU3ODA3NDVkNjQyMDFmY2Q2NTk5MWQ5NzlkYWNkMjllNGY5NTU1ODQ1Y2I0NDQ2OTQ4NTdiNTQ4ZGNmYWE5NmM3NWNkM2VcIixcImtleV9pZFwiOlwiMVwiLFwic2lnblwiOlwiOTZlYzFhNzZcIn0iLCJyIjoiaHR0cHM6Ly9jcS5saWFuamlhLmNvbS9lcnNob3VmYW5nLzEwNjEyNzczNjE4NS5odG1sIiwib3MiOiJ3ZWIiLCJ2IjoiMC4xIn0=; _ga_PV625F3L95=GS2.2.s1780993535$o2$g1$t1780994402$j60$l0$h0; lianjia_ssid=963ff1ed-dbdc-4852-899c-5148f552f8f5; hip=4oCzSf6pE7hx_WVZILOwmvokAFMm7dRKz3KJfkWmaTzZpcL9wKMpvuCIELQj-9TK0ALqjyhIIYbNaW6s9wKVDRAj9q-ziS2P2t97qqW3oHxT2Jq46hLeCu4V9T3SVdMbcXGr6sjN3kVuVKqTEv5oS4A05Zh-8CU-TEEME8kvEbLvTF1pUsMrlNtA2B8cBqFFsp6gyxyMBKnvIN_7aMpehTLe6F0k__FQNoew6xdJoz31NROPUrFuuXNqxQ%3D%3D; select_city=500000; Hm_lpvt_46bf127ac9b856df503ec2dbf942b67e=1781083453; _qzja=1.1859070309.1780982049166.1780991815790.1781083453389.1780994392640.1781083453389.0.0.0.64.4; _qzjto=1.1.0; _jzqa=1.1801755635432145400.1780982049.1780991816.1781083453.4; _jzqx=1.1780982049.1781083453.3.jzqsr=my%2Efeishu%2Ecn|jzqct=/.jzqsr=hip%2Elianjia%2Ecom|jzqct=/; _jzqckmp=1; _jzqb=1.1.10.1781083453.1; _qzjb=1.1781083453389.1.0.0.0"

# 把 cookie 字符串转成字典
cookies = {}
for item in COOKIE_STRING.split('; '):
    if '=' in item:
        k, v = item.split('=', 1)
        cookies[k] = v

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
})
session.cookies.update(cookies)

print('测试链家沙坪坝...')
resp = session.get('https://cq.lianjia.com/ershoufang/shapingba/', timeout=15)
print(f'状态码: {resp.status_code}  长度: {len(resp.text)}')

soup = BeautifulSoup(resp.text, 'lxml')
items = soup.select('.sellListContent li')
print(f'房源数: {len(items)}')

if items:
    for i, item in enumerate(items[:3]):
        title = item.select_one('.title a')
        price = item.select_one('.totalPrice span')
        unit = item.select_one('.unitPrice span')
        pos = item.select('.positionInfo a')
        info = item.select_one('.houseInfo')
        print(f'\n第{i+1}条:')
        print(f'  标题: {title.get_text(strip=True) if title else "无"}')
        print(f'  总价: {price.get_text(strip=True) if price else "无"}')
        print(f'  单价: {unit.get_text(strip=True) if unit else "无"}')
        print(f'  小区: {pos[0].get_text(strip=True) if len(pos)>=1 else "无"}')
        print(f'  商圈: {pos[1].get_text(strip=True) if len(pos)>=2 else "无"}')
else:
    print(f'页面预览:\n{resp.text[:300]}')