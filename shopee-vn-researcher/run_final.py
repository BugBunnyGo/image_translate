#!/usr/bin/env python3
"""
全自动采集：后台启动 Chromium，打开页面，用户截图确认登录，然后采集
"""
import asyncio
import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))

from playwright.async_api import async_playwright
from config import KEYWORDS
from collectors.shopee_vn import collect_all_shopee
from collectors.source_1688 import collect_all_1688
from collectors.pinduoduo import collect_all_pdd
from analyzer.price_compare import compare_prices
from analyzer.recommendation import generate_report
from utils.data_io import save_json, save_csv

SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)


async def main():
    print("=" * 60)
    print("  Shopee 越南站 3C 手机配件选品分析工具")
    print("=" * 60)
    print()
    print("正在弹出 Chromium 浏览器...")
    print("请在弹出的窗口中依次登录三个页面")
    print("每个页面登录完成后，在此按回车继续")
    print()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1400, "height": 900})

        # === 页面1: Shopee ===
        page1 = await context.new_page()
        await page1.goto("https://shopee.vn", wait_until="domcontentloaded", timeout=30000)
        await page1.wait_for_timeout(2000)
        await page1.screenshot(path=os.path.join(SCREENSHOTS_DIR, "01_shopee.png"))
        print("[1/3] Shopee 页面已打开，请登录后查看")
        print("      登录完成后按回车 -> ", end="", flush=True)
        try:
            input()
        except (KeyboardInterrupt, EOFError):
            print("\n已取消")
            await browser.close()
            return

        # === 页面2: 1688 ===
        page2 = await context.new_page()
        await page2.goto("https://s.1688.com", wait_until="domcontentloaded", timeout=30000)
        await page2.wait_for_timeout(2000)
        await page2.screenshot(path=os.path.join(SCREENSHOTS_DIR, "02_1688.png"))
        print("[2/3] 1688 页面已打开，请登录后查看")
        print("      登录完成后按回车 -> ", end="", flush=True)
        try:
            input()
        except (KeyboardInterrupt, EOFError):
            print("\n已取消")
            await browser.close()
            return

        # === 页面3: 拼多多 ===
        page3 = await context.new_page()
        await page3.goto("https://mobile.yangkeduo.com/", wait_until="domcontentloaded", timeout=30000)
        await page3.wait_for_timeout(2000)
        await page3.screenshot(path=os.path.join(SCREENSHOTS_DIR, "03_pdd.png"))
        print("[3/3] 拼多多页面已打开，请登录后查看")
        print("      登录完成后按回车 -> ", end="", flush=True)
        try:
            input()
        except (KeyboardInterrupt, EOFError):
            print("\n已取消")
            await browser.close()
            return

        # === 开始采集 ===
        print()
        print("开始采集数据...")

        # 登录完成后截图留档
        await page1.screenshot(path=os.path.join(SCREENSHOTS_DIR, "01_shopee_after_login.png"))
        await page2.screenshot(path=os.path.join(SCREENSHOTS_DIR, "02_1688_after_login.png"))
        await page3.screenshot(path=os.path.join(SCREENSHOTS_DIR, "03_pdd_after_login.png"))

        # Shopee 采集
        print("\n[1/3] 采集 Shopee 越南站数据...")
        shopee_products = await collect_all_shopee(page1, KEYWORDS)
        save_json(shopee_products, "shopee_products.json")

        # 1688 采集
        print("\n[2/3] 采集 1688 数据...")
        sourcing_1688 = await collect_all_1688(page2, KEYWORDS)
        save_json(sourcing_1688, "sourcing_1688.json")

        # 拼多多采集
        print("\n[3/3] 采集拼多多数据...")
        sourcing_pdd = await collect_all_pdd(page3, KEYWORDS)
        save_json(sourcing_pdd, "sourcing_pdd.json")

        # 分析
        print("\n分析数据，生成选品报告...")
        comparison = compare_prices(shopee_products, sourcing_1688, sourcing_pdd)
        save_csv(comparison, "price_comparison.csv")
        generate_report(
            comparison,
            shopee_count=len(shopee_products),
            sourcing_count=len(sourcing_1688) + len(sourcing_pdd),
        )

        print()
        print("=" * 60)
        print("  全部完成！")
        print("=" * 60)
        print(f"\n输出文件在 results/ 目录下")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
