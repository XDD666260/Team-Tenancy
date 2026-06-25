# ============================================================
# 安居客缺失区县爬虫 v3 — PC站 + Cookie + 直接连接
# 说明: 66daili免费代理不支持HTTPS穿透, 故改用直接连接+Cookie
#       实测直接连接 + Cookie 可稳定访问安居客PC站
# 目标: 远郊区县（主爬虫覆盖不全的补充）
# ============================================================

import os
import re
import sys
import time
import random
import traceback

# 确保项目根目录在 sys.path 中
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
# Windows 控制台编码修复（仅在交互终端时生效）
# ============================================================

def _fix_windows_console():
    """修复 Windows 控制台 GBK 编码问题。

    注意: 仅在交互式终端时生效；重定向/管道输出不受影响。
    更推荐的方案是设置环境变量 PYTHONIOENCODING=utf-8。
    """
    if sys.platform != 'win32':
        return
    try:
        import io
        if hasattr(sys.stdout, 'buffer') and sys.stdout.buffer:
            sys.stdout = io.TextIOWrapper(
                sys.stdout.buffer,
                encoding='utf-8',
                errors='replace',
                line_buffering=sys.stdout.line_buffering,
            )
        if hasattr(sys.stderr, 'buffer') and sys.stderr.buffer:
            sys.stderr = io.TextIOWrapper(
                sys.stderr.buffer,
                encoding='utf-8',
                errors='replace',
                line_buffering=sys.stderr.line_buffering,
            )
    except (ValueError, AttributeError):
        pass  # 非交互式终端，忽略


_fix_windows_console()


# ============================================================
# 目标: 远郊区县（安居客38区中主爬虫重点覆盖14核心区，
#        此爬虫专门处理其余远郊区县）
# ============================================================

# 核心区（主爬虫已充分覆盖）
CORE_DISTRICTS = {
    'yubei', 'yuzhong', 'nanana', 'shapingba', 'jiulongpo',
    'banan', 'beibei', 'dadukou', 'bishanqu',
    'yongchuanqu', 'wanzhouqu', 'jiangjinqu', 'hechuanqu', 'fulingqu',
}

# 缺失区县 = 全部区县 - 核心区
MISSING_DISTRICTS = [(c, n) for c, n in ANJUKE_DISTRICTS if c not in CORE_DISTRICTS]


# ============================================================
# PC站列表页解析
# ============================================================

def parse_house_info(item):
    """解析安居客PC站房源卡片"""
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

    # --- 详细地址 ---
    try:
        addr_el = item.select_one('.property-content-info-comm-address')
        house['address'] = addr_el.get_text(strip=True) if addr_el else ''
    except Exception:
        house['address'] = ''

    # --- 户型/面积/朝向/楼层/年代 ---
    try:
        info_ps = item.select(
            '.property-content-info:not(.property-content-info-comm) > '
            '.property-content-info-text'
        )
        info_texts = [p.get_text(strip=True) for p in info_ps]

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

        house['area'] = 0
        if len(info_texts) > 1:
            area_str = info_texts[1].replace('m²', '').replace('㎡', '').replace('平米', '').strip()
            try:
                house['area'] = float(area_str)
            except ValueError:
                pass

        house['orientation'] = info_texts[2] if len(info_texts) > 2 else ''

        floor_desc = info_texts[3] if len(info_texts) > 3 else ''
        house['floor_desc'] = floor_desc
        house['floor_type'] = ''
        house['total_floors'] = 0
        if floor_desc:
            fm_type = re.search(r'(低层|中层|高层)', floor_desc)
            if fm_type: house['floor_type'] = fm_type.group(1)
            fm_total = re.search(r'共(\d+)层', floor_desc)
            if fm_total: house['total_floors'] = int(fm_total.group(1))

        house['build_year'] = 0
        if len(info_texts) > 4:
            bm = re.search(r'(\d+)年建造', info_texts[4])
            if bm: house['build_year'] = int(bm.group(1))

    except Exception:
        house.setdefault('layout', '')
        house.setdefault('rooms', 0)
        house.setdefault('halls', 0)
        house.setdefault('bathrooms', 0)
        house.setdefault('area', 0)
        house.setdefault('orientation', '')
        house.setdefault('floor_desc', '')
        house.setdefault('floor_type', '')
        house.setdefault('total_floors', 0)
        house.setdefault('build_year', 0)

    # --- 从链接提取房源ID ---
    try:
        parent_a = item.find_parent('a')
        if not parent_a:
            parent_a = item.parent if item.parent and item.parent.name == 'a' else None
        house['id'] = ''
        if parent_a:
            href = parent_a.get('href', '')
            m_id = re.search(r'/prop/view/(S?\d+)', href)
            if m_id:
                house['id'] = m_id.group(1)
    except Exception:
        house['id'] = ''

    # --- 默认值 ---
    house.setdefault('decoration', '')
    house.setdefault('lng', 0)
    house.setdefault('lat', 0)
    house.setdefault('tags', '')
    house.setdefault('followers', 0)
    house.setdefault('source', 'anjuke')
    house.setdefault('source_id', house.get('id', ''))

    return house


# ============================================================
# 区县爬取
# ============================================================

def crawl_district(code, name, max_pages=100):
    """爬取一个区县的PC站列表页"""
    all_data = []
    session = create_session(ANJUKE_COOKIE, USER_AGENTS_DESKTOP, BASE_HEADERS_DESKTOP)

    checkpoint = load_checkpoint('anjuke_m', code)
    pages_done = list(checkpoint.get('pages_done', []))
    completed = set(pages_done)

    if completed:
        print(f'  [{name}] 断点续爬: {len(completed)} 页已完成')

    for page in range(1, max_pages + 1):
        if page in completed:
            continue

        if page == 1:
            url = f'https://chongqing.anjuke.com/sale/{code}/'
            referer = 'https://chongqing.anjuke.com/sale/'
        else:
            url = f'https://chongqing.anjuke.com/sale/{code}/p{page}/'
            referer = f'https://chongqing.anjuke.com/sale/{code}/p{page - 1}/'

        # 远郊区县数据少，但反爬同样严格 — 自适应延迟
        if page > 1:
            base_delay = random.uniform(30, 60)
            delay = base_delay * random.uniform(0.8, 1.2)
            print(f'  [{name}] 页间冷却 {delay:.1f}s ...')
            time.sleep(delay)

        print(f'  [{name}] p{page}/{max_pages}: {url}')

        try:
            resp, session = safe_get(session, url, referer=referer)
        except Exception as e:
            print(f'  [{name}] p{page}: 请求失败 {type(e).__name__}, 跳过')
            continue

        if resp.status_code == 404:
            print(f'  [{name}] 404 — 没有更多页面')
            break
        if resp.status_code != 200:
            print(f'  [{name}] 状态码 {resp.status_code}, 跳过')
            session = refresh_session(session)
            continue

        # 解析
        soup = BeautifulSoup(resp.text, 'lxml')
        items = soup.select('.property-content')
        if not items:
            items = soup.select('.list-item')
        if not items:
            items = soup.select('li[class*=property]')

        page_count = 0
        for item in items:
            house = parse_house_info(item)
            if house.get('title') and house.get('total_price', 0) > 0:
                house['district'] = name
                house['fingerprint'] = make_anjuke_fingerprint(house)
                all_data.append(house)
                page_count += 1

        print(f'  [{name}] p{page}: {page_count} 条, 累计 {len(all_data)} 条')

        if page_count > 0:
            pages_done.append(page)
            save_checkpoint('anjuke_m', code, pages_done)

        # 每10页重建session
        if page % 10 == 0:
            session = refresh_session(session)

        # 空页停止
        if page_count == 0:
            if page == 1:
                debug_path = os.path.join(OUTPUT_DIR, f'debug_anjuke_{code}_p1.html')
                with open(debug_path, 'w', encoding='utf-8', errors='ignore') as f:
                    f.write(resp.text)
                print(f'  [{name}] 首页无房源, 调试文件: {debug_path}')
            else:
                print(f'  [{name}] 无房源, 停止翻页')
            break

    print(f'  [{name}] 完成: {len(pages_done)} 页, {len(all_data)} 条')
    return all_data


# ============================================================
# CSV保存
# ============================================================

def save_district_csv(name, data):
    if not data:
        return
    out_path = os.path.join(OUTPUT_DIR, f'anjuke_m_{name}.csv')
    save_csv(data, out_path, ANJUKE_CSV_KEYS)
    print(f'  已保存: {out_path} ({len(data)} 条)')


# ============================================================
# 主流程
# ============================================================

if __name__ == '__main__':
    print('=' * 60)
    print('安居客缺失区县爬虫 v3 — PC站 + Cookie 直连')
    print(f'目标: {len(MISSING_DISTRICTS)} 个远郊区县')
    print('注意: 免费HTTP代理不支持HTTPS穿透, 改用直接连接')
    print(f'已用环境变量 ANJUKE_COOKIE: '
          f'{"✓" if os.environ.get("ANJUKE_COOKIE") else "✗ (使用默认)"}')
    print('=' * 60)

    all_data = []
    success = 0
    failed = []

    for i, (code, name) in enumerate(MISSING_DISTRICTS):
        print(f'\n{"=" * 50}')
        print(f'[{i + 1}/{len(MISSING_DISTRICTS)}] 开始爬取: {name} ({code})')
        print(f'{"=" * 50}')

        try:
            data = crawl_district(code, name, max_pages=100)
            if data:
                save_district_csv(name, data)
                all_data.extend(data)
                success += 1
                print(f'  [OK] {name}: {len(data)} 条')
            else:
                print(f'  [WARN] {name}: 未获取到数据')
                failed.append(name)

        except KeyboardInterrupt:
            print(f'\n[STOP] 用户中断，当前进度已保存')
            break
        except Exception as e:
            print(f'  [ERR] {name}: {type(e).__name__}: {e}')
            failed.append(name)
            traceback.print_exc()

        # 区县间冷却
        if i < len(MISSING_DISTRICTS) - 1:
            wait = random.uniform(8, 15)
            print(f'  区县间冷却 {wait:.1f}s ...')
            time.sleep(wait)

    # ==================== 汇总 ====================
    print(f'\n{"=" * 60}')
    print(f'爬取完成!')
    print(f'  成功: {success}/{len(MISSING_DISTRICTS)} 个区县')
    if failed:
        print(f'  失败: {failed}')
    print(f'  本次共获取: {len(all_data)} 条')
    print(f'{"=" * 60}')

    # 去重合并
    if all_data:
        merged = os.path.join(OUTPUT_DIR, 'anjuke_m_missing_merged.csv')
        unique, count = deduplicate_and_save(all_data, merged, ANJUKE_CSV_KEYS)
        print(f'  去重合并: {count} 条 → {merged}')
