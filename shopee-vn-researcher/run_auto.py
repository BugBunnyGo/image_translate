#!/usr/bin/env python3
"""
全自动采集 v3：修复页面导航等待问题
"""
import asyncio
import sys
import os
import json
import re

sys.path.insert(0, os.path.dirname(__file__))

from playwright.async_api import async_playwright
from config import KEYWORDS
from utils.data_io import save_json, save_csv, save_markdown

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

VND_TO_CNY = 0.00029


async def wait_page_ready(page, timeout=15000):
    """等待页面稳定：先等 domcontentloaded，再等 2 秒"""
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=timeout)
        await asyncio.sleep(3)
    except Exception:
        await asyncio.sleep(3)


async def dismiss_shopee_popups(page):
    """关闭 Shopee 弹窗"""
    await asyncio.sleep(2)
    try:
        # 语言选择
        lang_btn = await page.query_selector('button:has-text("Tiếng Việt")')
        if lang_btn:
            await lang_btn.click()
            await asyncio.sleep(1)
    except Exception:
        pass
    try:
        # 关闭按钮
        for selector in ['.shopee-popup__close-btn', '.shopee-modal__close', '[aria-label="Close"]', '.close-btn']:
            btn = await page.query_selector(selector)
            if btn and await btn.is_visible():
                await btn.click()
                await asyncio.sleep(0.5)
    except Exception:
        pass
    await asyncio.sleep(1)


async def scroll_and_wait(page, scrolls=12, delay=0.8):
    """滚动页面并等待懒加载"""
    for _ in range(scrolls):
        try:
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await asyncio.sleep(delay)
        except Exception:
            break


async def scrape_shopee(page, keywords: dict) -> list[dict]:
    """采集 Shopee 越南站"""
    all_products = []

    for vn_kw, cn_kw in keywords.items():
        print(f"\n  搜索 Shopee: {cn_kw} ({vn_kw})")

        try:
            await page.goto(f"https://shopee.vn/search?keyword={vn_kw.replace(' ', '+')}",
                            wait_until="domcontentloaded", timeout=30000)
            await wait_page_ready(page)
            await dismiss_shopee_popups(page)
            await scroll_and_wait(page)

            items = await page.evaluate("""() => {
                const results = [];
                let cards = document.querySelectorAll('[data-sqe="item"]');
                if (cards.length === 0) {
                    cards = document.querySelectorAll('.shop-search-result-view__item');
                }
                if (cards.length === 0) {
                    cards = document.querySelectorAll('[class*="item"], [class*="card"]');
                }

                cards.forEach(card => {
                    try {
                        const nameEl = card.querySelector('[data-sqe="item_name"], [class*="name"], [class*="title"], h3, h4');
                        const priceEl = card.querySelector('[data-sqe="item_price"], [class*="price"]');
                        const soldEl = card.querySelector('[data-sqe="item_sold"], [class*="sold"], [class*="sales"]');
                        const ratingEl = card.querySelector('[data-sqe="item_rating"], [class*="rating"], [class*="star"]');
                        const linkEl = card.querySelector('a');

                        const name = nameEl ? nameEl.textContent.trim() : '';
                        const priceRaw = priceEl ? priceEl.textContent.trim() : '';
                        const price = parseInt(priceRaw.replace(/[^0-9]/g, '')) || 0;
                        const sold = soldEl ? soldEl.textContent.trim() : '';
                        const rating = ratingEl ? ratingEl.textContent.trim() : '';
                        const link = linkEl ? linkEl.href : '';

                        if (name && price > 0) {
                            results.push({ name, price, sold, rating, link });
                        }
                    } catch(e) {}
                });

                return results;
            }""")

            for item in items:
                all_products.append({
                    "keyword": vn_kw,
                    "keyword_cn": cn_kw,
                    "name": item["name"],
                    "price_vnd": item["price"],
                    "sold_raw": item.get("sold", ""),
                    "rating_raw": item.get("rating", ""),
                    "link": item.get("link", ""),
                    "platform": "shopee_vn",
                })

            print(f"    -> 采集到 {len(items)} 个商品")
        except Exception as e:
            print(f"    -> 搜索失败: {e}")

        await asyncio.sleep(1)

    return all_products


async def scrape_1688(page, keywords: dict) -> list[dict]:
    """采集 1688"""
    all_products = []

    for cn_kw in set(keywords.values()):
        print(f"\n  搜索 1688: {cn_kw}")

        try:
            await page.goto(f"https://s.1688.com/selloffer/offer_search.htm?keywords={cn_kw.replace(' ', '+')}",
                            wait_until="domcontentloaded", timeout=30000)
            await wait_page_ready(page)
            await scroll_and_wait(page)

            items = await page.evaluate("""() => {
                const results = [];
                let cards = document.querySelectorAll('.offer-item, .sm-offer-item');
                if (cards.length === 0) {
                    cards = document.querySelectorAll('[class*="offer"], [class*="list-item"]');
                }

                cards.forEach(card => {
                    try {
                        const title = card.querySelector('[class*="title"], [class*="name"], h3, h4');
                        const price = card.querySelector('[class*="price"], .price');
                        const sold = card.querySelector('[class*="sold"], [class*="deal"]');
                        const shop = card.querySelector('[class*="shop"], [class*="company"]');

                        const name = title ? title.textContent.trim() : '';
                        const priceRaw = price ? price.textContent.trim() : '';
                        const priceVal = parseFloat(priceRaw.replace(/[^0-9.]/g, '')) || 0;
                        const soldRaw = sold ? sold.textContent.trim() : '';
                        const shopName = shop ? shop.textContent.trim() : '';

                        if (name && priceVal > 0) {
                            results.push({ name, price: priceVal, sold: soldRaw, shop: shopName });
                        }
                    } catch(e) {}
                });

                return results;
            }""")

            for item in items:
                all_products.append({
                    "keyword": cn_kw,
                    "name": item["name"],
                    "price_cny": item["price"],
                    "sold_raw": item.get("sold", ""),
                    "shop": item.get("shop", ""),
                    "platform": "1688",
                })

            print(f"    -> 采集到 {len(items)} 个商品")
        except Exception as e:
            print(f"    -> 搜索失败: {e}")

        await asyncio.sleep(1)

    return all_products


async def scrape_pdd(page, keywords: dict) -> list[dict]:
    """采集拼多多"""
    all_products = []

    for cn_kw in set(keywords.values()):
        print(f"\n  搜索拼多多: {cn_kw}")

        try:
            await page.goto("https://mobile.yangkeduo.com/", wait_until="domcontentloaded", timeout=30000)
            await wait_page_ready(page)

            # 搜索
            try:
                search_input = await page.query_selector('input[type="text"], input[type="search"], input[class*="search"]')
                if search_input:
                    await search_input.click()
                    await asyncio.sleep(1)
                    await search_input.fill(cn_kw)
                    await asyncio.sleep(1)
                    search_btn = await page.query_selector('button[class*="search"], .search-btn')
                    if search_btn:
                        await search_btn.click()
                    else:
                        await page.keyboard.press("Enter")
                    await wait_page_ready(page)
            except Exception as e:
                print(f"    -> 搜索交互失败: {e}")
                await asyncio.sleep(1)
                continue

            await scroll_and_wait(page)

            items = await page.evaluate("""() => {
                const results = [];
                let cards = document.querySelectorAll('.goods-item');
                if (cards.length === 0) {
                    cards = document.querySelectorAll('[class*="goods"], [class*="item"], [class*="product"]');
                }

                cards.forEach(card => {
                    try {
                        const title = card.querySelector('[class*="title"], [class*="name"], h3, h4');
                        const price = card.querySelector('[class*="price"], .price');
                        const sold = card.querySelector('[class*="sold"], [class*="count"]');

                        const name = title ? title.textContent.trim() : '';
                        const priceRaw = price ? price.textContent.trim() : '';
                        const priceVal = parseFloat(priceRaw.replace(/[^0-9.]/g, '')) || 0;
                        const soldRaw = sold ? sold.textContent.trim() : '';

                        if (name && priceVal > 0) {
                            results.push({ name, price: priceVal, sold: soldRaw });
                        }
                    } catch(e) {}
                });

                return results;
            }""")

            for item in items:
                all_products.append({
                    "keyword": cn_kw,
                    "name": item["name"],
                    "price_cny": item["price"],
                    "sold_raw": item.get("sold", ""),
                    "platform": "pinduoduo",
                })

            print(f"    -> 采集到 {len(items)} 个商品")
        except Exception as e:
            print(f"    -> 搜索失败: {e}")

        await asyncio.sleep(1)

    return all_products


def generate_report(shopee_products: list, sourcing_1688: list, sourcing_pdd: list):
    """生成选品报告"""
    from datetime import datetime

    report = []
    report.append(f"# Shopee 越南站 3C 手机配件选品分析报告")
    report.append(f"\n> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"\n---\n")

    report.append(f"## 数据概览")
    report.append(f"- Shopee 商品：{len(shopee_products)} 条")
    report.append(f"- 1688 商品：{len(sourcing_1688)} 条")
    report.append(f"- 拼多多商品：{len(sourcing_pdd)} 条")
    report.append(f"")

    if shopee_products:
        report.append(f"## Shopee 热销商品 TOP 30")
        report.append(f"")
        report.append(f"| 排名 | 品类 | 商品名 | 售价(VND) | 售价(CNY) | 已售 | 评分 |")
        report.append(f"|------|------|--------|----------|-----------|------|------|")

        def parse_sold(s):
            if not s: return 0
            m = re.search(r'([\d,]+\.?\d*)\s*[kK]?', s)
            if m:
                n = float(m.group(1).replace(',', ''))
                if 'k' in s.lower(): n *= 1000
                if '千' in s: n *= 1000
                if '万' in s: n *= 10000
                return int(n)
            return 0

        def parse_rating(s):
            if not s: return 0.0
            m = re.search(r'([\d.]+)', s)
            return float(m.group(1)) if m else 0.0

        sorted_products = sorted(shopee_products, key=lambda x: parse_sold(x.get("sold_raw", "")), reverse=True)
        for i, p in enumerate(sorted_products[:30], 1):
            name = p["name"][:30] + "..." if len(p["name"]) > 30 else p["name"]
            sold = parse_sold(p.get("sold_raw", ""))
            rating = parse_rating(p.get("rating_raw", ""))
            price_cny = round(p['price_vnd'] * VND_TO_CNY, 2)
            report.append(
                f"| {i} | {p.get('keyword_cn', '')} | {name} | {p['price_vnd']:,} "
                f"| {price_cny} | {sold:,} | {rating} |")
        report.append(f"")

        # 按品类汇总
        report.append(f"## 各品类平均价格")
        report.append(f"")
        report.append(f"| 品类 | 商品数 | 平均价格(VND) | 平均价格(CNY) | 推荐 |")
        report.append(f"|------|--------|--------------|---------------|------|")

        categories = {}
        for p in shopee_products:
            kw = p.get("keyword_cn", "Unknown")
            if kw not in categories:
                categories[kw] = {"count": 0, "total_vnd": 0}
            categories[kw]["count"] += 1
            categories[kw]["total_vnd"] += p["price_vnd"]

        for kw, stats in sorted(categories.items(), key=lambda x: x[1]["total_vnd"] / max(x[1]["count"], 1)):
            avg = stats["total_vnd"] // max(stats["count"], 1)
            rec = "⭐ 新手友好" if avg <= 300000 else ""
            report.append(f"| {kw} | {stats['count']} | {avg:,} | {round(avg * VND_TO_CNY, 2)} | {rec} |")
        report.append(f"")

    if sourcing_1688:
        report.append(f"## 1688 采购参考价")
        report.append(f"")
        report.append(f"| 品类 | 商品数 | 最低价(CNY) | 最高价(CNY) | 均价 |")
        report.append(f"|------|--------|------------|------------|------|")
        cats = {}
        for p in sourcing_1688:
            kw = p.get("keyword", "Unknown")
            if kw not in cats:
                cats[kw] = {"count": 0, "min": float('inf'), "max": 0, "total": 0}
            cats[kw]["count"] += 1
            cats[kw]["min"] = min(cats[kw]["min"], p["price_cny"])
            cats[kw]["max"] = max(cats[kw]["max"], p["price_cny"])
            cats[kw]["total"] += p["price_cny"]
        for kw, s in cats.items():
            avg = s["total"] / s["count"]
            report.append(f"| {kw} | {s['count']} | ¥{s['min']:.2f} | ¥{s['max']:.2f} | ¥{avg:.2f} |")
        report.append(f"")

    if sourcing_pdd:
        report.append(f"## 拼多多采购参考价")
        report.append(f"")
        report.append(f"| 品类 | 商品数 | 最低价(CNY) | 最高价(CNY) | 均价 |")
        report.append(f"|------|--------|------------|------------|------|")
        cats = {}
        for p in sourcing_pdd:
            kw = p.get("keyword", "Unknown")
            if kw not in cats:
                cats[kw] = {"count": 0, "min": float('inf'), "max": 0, "total": 0}
            cats[kw]["count"] += 1
            cats[kw]["min"] = min(cats[kw]["min"], p["price_cny"])
            cats[kw]["max"] = max(cats[kw]["max"], p["price_cny"])
            cats[kw]["total"] += p["price_cny"]
        for kw, s in cats.items():
            avg = s["total"] / s["count"]
            report.append(f"| {kw} | {s['count']} | ¥{s['min']:.2f} | ¥{s['max']:.2f} | ¥{avg:.2f} |")
        report.append(f"")

    report.append(f"## 新手选品建议")
    report.append(f"")
    report.append(f"1. 优先选择低客单价（<300,000 VND）的商品")
    report.append(f"2. 已销量 > 100 的商品说明市场需求已验证")
    report.append(f"3. 对比 1688/拼多多采购价，确保有 >50% 的利润空间")
    report.append(f"4. 手机壳、充电线是新手最佳切入点")
    report.append(f"5. 建议小批量试单后再扩大")
    report.append(f"")

    content = "\n".join(report)
    save_markdown(content, "recommendation_report.md")
    print(f"  报告已生成：{os.path.join(RESULTS_DIR, 'recommendation_report.md')}")


async def main():
    print("=" * 60)
    print("  Shopee 越南站 3C 手机配件选品分析工具")
    print("  全自动模式 v3")
    print("=" * 60)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1400, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        )

        # Shopee
        print("\n[1/3] Shopee 越南站采集...")
        page1 = await context.new_page()
        shopee_products = await scrape_shopee(page1, KEYWORDS)
        save_json(shopee_products, "shopee_products.json")
        print(f"  -> 总计 {len(shopee_products)} 个商品")

        # 1688
        print("\n[2/3] 1688 采集...")
        page2 = await context.new_page()
        sourcing_1688 = await scrape_1688(page2, KEYWORDS)
        save_json(sourcing_1688, "sourcing_1688.json")
        print(f"  -> 总计 {len(sourcing_1688)} 个商品")

        # 拼多多
        print("\n[3/3] 拼多多采集...")
        page3 = await context.new_page()
        sourcing_pdd = await scrape_pdd(page3, KEYWORDS)
        save_json(sourcing_pdd, "sourcing_pdd.json")
        print(f"  -> 总计 {len(sourcing_pdd)} 个商品")

        # 报告
        print("\n生成选品报告...")
        generate_report(shopee_products, sourcing_1688, sourcing_pdd)

        print("\n" + "=" * 60)
        print("  全部完成！查看 results/ 目录获取结果")
        print("=" * 60)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
