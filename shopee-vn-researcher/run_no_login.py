#!/usr/bin/env python3
"""
无需登录版：直接启动 Chromium，打开页面后自动采集
不需要任何登录操作
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from playwright.async_api import async_playwright
from config import KEYWORDS
from collectors.shopee_vn import collect_all_shopee
from collectors.source_1688 import collect_all_1688
from collectors.pinduoduo import collect_all_pdd
from analyzer.price_compare import compare_prices
from analyzer.recommendation import generate_report
from utils.data_io import save_json, save_csv


async def main():
    print("=" * 60)
    print("  Shopee 越南站 3C 手机配件选品分析工具")
    print("  模式：免登录直接采集")
    print("=" * 60)
    print()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1400, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )

        # 页面1: Shopee
        page1 = await context.new_page()
        print("[1/3] 正在打开 Shopee 越南站...")
        await page1.goto("https://shopee.vn", wait_until="domcontentloaded", timeout=30000)
        await page1.wait_for_timeout(2000)

        # 页面2: 1688
        page2 = await context.new_page()
        print("[2/3] 正在打开 1688...")
        await page2.goto("https://s.1688.com", wait_until="domcontentloaded", timeout=30000)
        await page2.wait_for_timeout(2000)

        # 页面3: 拼多多
        page3 = await context.new_page()
        print("[3/3] 正在打开拼多多...")
        await page3.goto("https://mobile.yangkeduo.com/", wait_until="domcontentloaded", timeout=30000)
        await page3.wait_for_timeout(2000)

        print()
        print("三个页面已打开，开始采集数据...")
        print()

        # Shopee 采集
        print("[采集 1/3] Shopee 越南站数据（约 2 分钟）...")
        shopee_products = await collect_all_shopee(page1, KEYWORDS)
        save_json(shopee_products, "shopee_products.json")

        # 1688 采集
        print("\n[采集 2/3] 1688 数据（约 2 分钟）...")
        sourcing_1688 = await collect_all_1688(page2, KEYWORDS)
        save_json(sourcing_1688, "sourcing_1688.json")

        # 拼多多采集
        print("\n[采集 3/3] 拼多多数据（约 2 分钟）...")
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
