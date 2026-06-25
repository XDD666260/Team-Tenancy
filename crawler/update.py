"""
============================================================
增量更新爬虫 — 整合版

策略：
  1. 快速抓取最新列表页（复用已验证的 selectors）
  2. 将新抓取的数据通过增量对比写入数据库
  3. 标记长期未更新的房源为下架

用法：
  python crawler/update.py                      # 全量增量更新
  python crawler/update.py --source lianjia     # 仅链家
  python crawler/update.py --source anjuke      # 仅安居客
  python crawler/update.py --max-pages 5        # 每个区县抓5页
  python crawler/update.py --mark-offline       # 标记下架房源
============================================================
"""
import argparse
import os
import re
import sys
import time
import random
from datetime import datetime

import pymysql

from crawler.utils import (
    LIANJIA_COOKIE, LIANJIA_DISTRICTS, ANJUKE_DISTRICTS,
    make_lianjia_fingerprint, make_anjuke_fingerprint,
)

# ===================== 数据库配置 =====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(BASE_DIR, "..")
sys.path.insert(0, PROJECT_DIR)  # 项目根目录（crawler 包的父目录）
sys.path.insert(0, os.path.join(PROJECT_DIR, "backend"))

from database import DB_CONFIG as _DB

DB_CONFIG = {
    "host": _DB["host"],
    "user": _DB["user"],
    "password": _DB["password"],
    "database": _DB["database"],
    "charset": _DB["charset"],
}


def get_db_conn():
    return pymysql.connect(**DB_CONFIG)


def log_crawl(source, district, page, found, new_added, updated, status, message=""):
    """写入爬取日志"""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO crawl_log (source, district, page, houses_found,
                               new_added, updated, status, message)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (source, district, page, found, new_added, updated, status, message),
    )
    conn.commit()
    cursor.close()
    conn.close()


def update_single_listing(cursor, fingerprint, source, row):
    """
    核心：单条房源增量更新逻辑

    注意：last_updated 字段的语义是"最后一次确认该房源仍在售的时间"。
    每次爬取到房源时都会刷新此字段（即使价格未变），这样
    --mark-offline 才能正确识别长时间未被爬取到的下架房源。

    返回: 'new' | 'updated' | 'skipped' | 'error'
    """
    if not fingerprint or fingerprint in ("lj_", ""):
        return "skipped"

    cursor.execute(
        "SELECT id, total_price, unit_price, status FROM houses WHERE fingerprint=%s",
        (fingerprint,),
    )
    existing = cursor.fetchone()

    if not existing:
        # 新房源 → INSERT
        try:
            cursor.execute(
                """
                INSERT INTO houses
                (title, district, community, address,
                 total_price, unit_price, area, layout, rooms, halls, bathrooms,
                 floor_desc, floor_type, total_floors, orientation, decoration,
                 build_year, lng, lat, followers, source, source_id, fingerprint)
                VALUES (%s,%s,%s,%s,%s, %s,%s,%s,%s,%s,%s, %s,%s,%s,%s,%s, %s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    str(row.get("title", ""))[:300],
                    str(row.get("district", ""))[:50],
                    str(row.get("community", ""))[:100],
                    str(row.get("address", ""))[:300],
                    float(row.get("total_price", 0) or 0),
                    float(row.get("unit_price", 0) or 0),
                    float(row.get("area", 0) or 0),
                    str(row.get("layout", ""))[:20],
                    int(row.get("rooms", 0) or 0),
                    int(row.get("halls", 0) or 0),
                    int(row.get("bathrooms", 0) or 0),
                    str(row.get("floor_desc", ""))[:50],
                    str(row.get("floor_type", ""))[:10],
                    int(row.get("total_floors", 0) or 0),
                    str(row.get("orientation", ""))[:20],
                    str(row.get("decoration", ""))[:20],
                    int(row.get("build_year", 0) or 0),
                    float(row.get("lng", 0) or 0),
                    float(row.get("lat", 0) or 0),
                    int(row.get("followers", 0) or 0),
                    source,
                    str(row.get("source_id", ""))[:100],
                    fingerprint,
                ),
            )
            return "new"
        except Exception:
            return "error"

    else:
        db_id, old_price, old_unit, old_status = existing
        new_price = float(row.get("total_price", 0) or 0)
        new_unit = float(row.get("unit_price", 0) or 0)

        # 已下架房源重新出现 → 恢复在售
        if old_status != "on_sale":
            cursor.execute(
                "UPDATE houses SET status='on_sale', last_updated=NOW() WHERE id=%s",
                (db_id,),
            )
            return "updated"

        # 价格变动 → 更新价格
        if abs(new_price - float(old_price or 0)) > 0.1:
            cursor.execute(
                """
                UPDATE houses SET total_price=%s, unit_price=%s, last_updated=NOW()
                WHERE id=%s
                """,
                (new_price, new_unit, db_id),
            )
            return "updated"

        # 无变动 → 刷新 last_updated（表示"我们确认它还在售"）
        cursor.execute(
            "UPDATE houses SET last_updated=NOW() WHERE id=%s", (db_id,)
        )
        return "skipped"


# ============================================================
# 抓取函数 — 轻量版，用于增量更新
# ============================================================

def scrape_lianjia_page(code, district_name, page):
    """抓取链家单页列表（复用已验证的 selector）"""
    import requests
    from bs4 import BeautifulSoup
    from crawler.utils import parse_cookie_string

    cookies = parse_cookie_string(LIANJIA_COOKIE)

    UA_LIST = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    ]

    headers = {
        "User-Agent": random.choice(UA_LIST),
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }

    url = f"https://cq.lianjia.com/ershoufang/{code}/pg{page}/"
    try:
        resp = requests.get(url, headers=headers, cookies=cookies, timeout=20)

        if resp.status_code != 200 or len(resp.text) < 5000:
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        items = soup.select(".sellListContent li")

        results = []
        for item in items:
            try:
                # 链接 & ID
                a_tag = item.select_one('a[href*="/ershoufang/"]')
                href = a_tag.get("href", "") if a_tag else ""
                m_id = re.search(r"/ershoufang/(\d+)\.html", href)
                hid = m_id.group(1) if m_id else ""

                # 标题
                title_el = item.select_one(".title a")
                title = title_el.get_text(strip=True) if title_el else ""

                # 总价
                price_el = item.select_one(".totalPrice span")
                price_text = price_el.get_text(strip=True) if price_el else "0"
                try:
                    total_price = float(re.sub(r"[^\d.]", "", price_text))
                except ValueError:
                    total_price = 0

                # 单价
                unit_el = item.select_one(".unitPrice span")
                unit_text = unit_el.get_text(strip=True) if unit_el else "0"
                try:
                    unit_price = float(re.sub(r"[^\d.]", "", unit_text))
                except ValueError:
                    unit_price = 0

                # 小区
                pos_els = item.select(".positionInfo a")
                community = pos_els[0].get_text(strip=True) if len(pos_els) >= 1 else ""

                # houseInfo
                info_el = item.select_one(".houseInfo")
                info_text = info_el.get_text(strip=True) if info_el else ""
                parts = [p.strip() for p in info_text.split("|")]

                layout = parts[0] if len(parts) > 0 else ""
                area = 0.0
                if len(parts) > 1:
                    try:
                        area = float(parts[1].replace("平米", "").replace("㎡", ""))
                    except ValueError:
                        pass
                orientation = parts[2] if len(parts) > 2 else ""
                decoration = parts[3] if len(parts) > 3 else ""
                floor_desc = parts[4] if len(parts) > 4 else ""

                # 户型解析
                rooms = halls = bathrooms = 0
                if layout:
                    rm = re.search(r"(\d+)室", layout)
                    if rm: rooms = int(rm.group(1))
                    hm = re.search(r"(\d+)厅", layout)
                    if hm: halls = int(hm.group(1))
                    wm = re.search(r"(\d+)卫", layout)
                    if wm: bathrooms = int(wm.group(1))

                # 楼层
                floor_type = ""
                total_floors = 0
                if floor_desc:
                    fm = re.search(r"(低层|中层|高层)", floor_desc)
                    if fm: floor_type = fm.group(1)
                    fm2 = re.search(r"共(\d+)层", floor_desc)
                    if fm2: total_floors = int(fm2.group(1))

                if not title or total_price <= 0:
                    continue

                results.append({
                    "title": title,
                    "district": district_name,
                    "community": community,
                    "address": "",
                    "total_price": total_price,
                    "unit_price": unit_price,
                    "area": area,
                    "layout": layout,
                    "rooms": rooms,
                    "halls": halls,
                    "bathrooms": bathrooms,
                    "floor_desc": floor_desc,
                    "floor_type": floor_type,
                    "total_floors": total_floors,
                    "orientation": orientation,
                    "decoration": decoration,
                    "build_year": 0,
                    "lng": 0, "lat": 0,
                    "followers": 0,
                    "source": "lianjia",
                    "source_id": hid,
                })
            except Exception:
                continue

        return results
    except Exception:
        return []


def scrape_anjuke_page(code, district_name, page, proxy_url=None):
    """抓取安居客移动站单页列表（复用已验证的 selector）"""
    import requests
    from bs4 import BeautifulSoup

    if page == 1:
        url = f"https://m.anjuke.com/cq/sale/{code}/"
    else:
        url = f"https://m.anjuke.com/cq/sale/{code}/p{page}/"

    UA_MOBILE = [
        "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    ]

    headers = {
        "User-Agent": random.choice(UA_MOBILE),
        "Accept": "text/html,application/xhtml+xml",
        "Connection": "close",
    }

    proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None

    try:
        resp = requests.get(url, headers=headers, proxies=proxies, timeout=20)

        if resp is None or len(resp.text) < 3000:
            return []

        if "antibot" in resp.text or "xxzlGatewayUrl" in resp.text:
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        items = soup.select("li.item-wrap")

        results = []
        for item in items:
            try:
                a_el = item.find("a")
                href = a_el.get("href", "") if a_el else ""
                id_match = re.search(r"/S(\d+)/", href)
                hid = id_match.group(1) if id_match else ""

                title_el = item.select_one(".content-title")
                title = title_el.get_text(strip=True) if title_el else ""
                if not title:
                    continue

                descs = item.select(".content-desc")
                desc_texts = [d.get_text(strip=True) for d in descs if d.get_text(strip=True)]
                layout = desc_texts[0] if len(desc_texts) > 0 else ""
                area_str = desc_texts[1] if len(desc_texts) > 1 else "0"
                orientation = desc_texts[2] if len(desc_texts) > 2 else ""
                biz_circle = desc_texts[3] if len(desc_texts) > 3 else ""

                area = 0.0
                try:
                    area = float(re.sub(r"[^\d.]", "", area_str))
                except ValueError:
                    pass

                price_el = item.select_one(".price")
                price_text = price_el.get_text(strip=True) if price_el else "0"
                total_price = 0.0
                try:
                    total_price = float(re.sub(r"[^\d.]", "", price_text))
                except ValueError:
                    pass

                if total_price <= 0:
                    continue

                unit_el = item.select_one(".unit-price")
                unit_text = unit_el.get_text(strip=True) if unit_el else "0"
                unit_price = 0.0
                try:
                    unit_price = float(re.sub(r"[^\d.]", "", unit_text))
                except ValueError:
                    pass

                community = ""
                for img in item.find_all("img"):
                    alt = img.get("alt", "")
                    cm = re.match(r"(.+?)\d+室", alt)
                    if cm:
                        community = cm.group(1)
                        break

                rooms = halls = 0
                if layout:
                    rm = re.search(r"(\d+)室", layout)
                    if rm: rooms = int(rm.group(1))
                    hm = re.search(r"(\d+)厅", layout)
                    if hm: halls = int(hm.group(1))

                bathrooms = 0
                wm = re.search(r"(\d+)卫", layout)
                if wm:
                    bathrooms = int(wm.group(1))
                else:
                    bathrooms = 1 if rooms <= 2 else 2

                if unit_price == 0 and area > 0 and total_price > 0:
                    unit_price = round(total_price * 10000 / area, 2)

                results.append({
                    "title": title,
                    "district": district_name,
                    "community": community,
                    "address": biz_circle,
                    "total_price": total_price,
                    "unit_price": unit_price,
                    "area": area,
                    "layout": layout,
                    "rooms": rooms,
                    "halls": halls,
                    "bathrooms": bathrooms,
                    "floor_desc": "",
                    "floor_type": "",
                    "total_floors": 0,
                    "orientation": orientation,
                    "decoration": "",
                    "build_year": 0,
                    "lng": 0, "lat": 0,
                    "followers": 0,
                    "source": "anjuke",
                    "source_id": hid,
                })
            except Exception:
                continue

        return results
    except Exception:
        return []


# ============================================================
# 主流程
# ============================================================

def run_incremental_update(source=None, max_pages=3, mark_offline=False):
    """主流程：抓取 → 增量对比 → 写入DB → 日志"""
    start_time = datetime.now()
    print(f"{'=' * 60}")
    print(f"增量更新开始 — {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 60}")

    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM houses WHERE status='on_sale'")
    before_count = cursor.fetchone()[0]
    print(f"[更新前] 在售房源: {before_count} 条")

    total_new = 0
    total_updated = 0
    total_skipped = 0
    total_found = 0

    # ==================== 链家增量 ====================
    if not source or source == "lianjia":
        print(f"\n--- 链家增量更新 (每区县{max_pages}页) ---")
        for code, name in LIANJIA_DISTRICTS:
            district_new = 0
            district_updated = 0
            district_found = 0

            for page in range(1, max_pages + 1):
                try:
                    houses = scrape_lianjia_page(code, name, page)
                except Exception as e:
                    log_crawl("lianjia", name, page, 0, 0, 0, "failed", str(e)[:200])
                    continue

                if not houses:
                    continue

                district_found += len(houses)
                for h in houses:
                    # 使用统一的指纹函数（完整32位MD5）
                    fp = make_lianjia_fingerprint(h)
                    result = update_single_listing(cursor, fp, "lianjia", h)
                    if result == "new":
                        district_new += 1
                    elif result == "updated":
                        district_updated += 1
                    else:
                        total_skipped += 1

                conn.commit()

                if page > 1:
                    delay = 30 + (page * 10)
                    print(f"    等待 {delay}s ...")
                    time.sleep(delay)

            log_crawl(
                "lianjia", name, max_pages, district_found,
                district_new, district_updated,
                "success" if district_found > 0 else "empty",
            )

            total_new += district_new
            total_updated += district_updated
            total_found += district_found
            if district_found > 0:
                print(f"  链家 {name}: 抓取{district_found}条 | "
                      f"新增{district_new} | 更新{district_updated}")

            time.sleep(5)

    # ==================== 安居客增量 ====================
    if not source or source == "anjuke":
        print(f"\n--- 安居客增量更新 (每区县{max_pages}页) ---")
        for code, name in ANJUKE_DISTRICTS:
            district_new = 0
            district_updated = 0
            district_found = 0

            for page in range(1, max_pages + 1):
                try:
                    houses = scrape_anjuke_page(code, name, page)
                except Exception as e:
                    log_crawl("anjuke", name, page, 0, 0, 0, "failed", str(e)[:200])
                    continue

                if not houses:
                    continue

                district_found += len(houses)
                for h in houses:
                    # 使用统一的指纹函数（完整32位MD5，无截断）
                    fp = make_anjuke_fingerprint(h)
                    result = update_single_listing(cursor, fp, "anjuke", h)
                    if result == "new":
                        district_new += 1
                    elif result == "updated":
                        district_updated += 1
                    else:
                        total_skipped += 1

                conn.commit()
                time.sleep(3)

            log_crawl(
                "anjuke", name, max_pages, district_found,
                district_new, district_updated,
                "success" if district_found > 0 else "empty",
            )

            total_new += district_new
            total_updated += district_updated
            total_found += district_found
            if district_found > 0:
                print(f"  安居客 {name}: 抓取{district_found}条 | "
                      f"新增{district_new} | 更新{district_updated}")

            time.sleep(3)

    # ==================== 标记下架 ====================
    # 注意: last_updated 在每次爬取到房源时都会刷新（即使价格未变），
    #       因此超过30天未更新的房源就是超过30天未被爬取到的房源，
    #       可以合理推断为已下架。
    if mark_offline:
        print("\n--- 标记下架房源 ---")
        cursor.execute(
            """
            UPDATE houses
            SET status = 'probably_sold', last_updated = NOW()
            WHERE status = 'on_sale'
              AND last_updated < DATE_SUB(NOW(), INTERVAL 30 DAY)
            """
        )
        marked = cursor.rowcount
        conn.commit()
        if marked > 0:
            print(f"  标记 {marked} 条可能已下架房源")

    # ==================== 统计 ====================
    cursor.execute("SELECT COUNT(*) as cnt FROM houses WHERE status='on_sale'")
    after_count = cursor.fetchone()[0]

    elapsed = (datetime.now() - start_time).total_seconds()

    print(f"\n{'=' * 60}")
    print(f"增量更新完成!")
    print(f"  耗时: {elapsed:.1f}秒")
    print(f"  抓取房源: {total_found} 条")
    print(f"  新增: {total_new} 条")
    print(f"  更新: {total_updated} 条")
    print(f"  跳过(未变): {total_skipped} 条")
    print(f"  更新前在售: {before_count} 条")
    print(f"  更新后在售: {after_count} 条")
    print(f"{'=' * 60}")

    cursor.close()
    conn.close()

    return {
        "new": total_new,
        "updated": total_updated,
        "skipped": total_skipped,
        "found": total_found,
        "before": before_count,
        "after": after_count,
        "elapsed": elapsed,
    }


def main():
    parser = argparse.ArgumentParser(description="增量更新爬虫 — 整合版")
    parser.add_argument(
        "--source", choices=["lianjia", "anjuke"], help="只更新指定数据源"
    )
    parser.add_argument(
        "--max-pages", type=int, default=3, help="每个区县最大抓取页数（默认3）"
    )
    parser.add_argument(
        "--mark-offline", action="store_true", help="标记长期未更新的房源为下架"
    )
    args = parser.parse_args()

    result = run_incremental_update(
        source=args.source, max_pages=args.max_pages, mark_offline=args.mark_offline
    )

    if result["found"] == 0:
        print(
            "\n⚠ 注意: 本次未抓取到数据。可能原因:"
            "\n  1. 目标网站改版（CSS选择器需更新）"
            "\n  2. 网络问题或IP被暂时限制"
            "\n  3. Cookie/UA失效（链家cookie有时效性）"
            "\n  建议: 先单独运行 crawler/anjuke_fast.py 或 "
            "crawler/lianjia_spider.py 确认爬虫可用"
        )


if __name__ == "__main__":
    main()
