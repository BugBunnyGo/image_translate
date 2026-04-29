#!/usr/bin/env python3
"""
备选方案：Playwright 直接启动 Chromium（不需要 CDP）
首次运行会弹出浏览器窗口，需要手动登录各平台
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
    print("  模式：Playwright 直接启动 Chromium")
    print("=" * 60)
    print()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="zh-CN",
        )

        # 第一页：Shopee
        print("\n[1/5] 打开 Shopee 越南站...")
        page1 = await context.new_page()
        await page1.goto("https://shopee.vn", wait_until="domcontentloaded", timeout=30000)
        print("  -> 请在此页面登录 Shopee（如果未登录）")
        print("  -> 登录完成后按回车继续...")
        input()

        # 第二页：1688
        print("\n[2/5] 打开 1688...")
        page2 = await context.new_page()
        await page2.goto("https://s.1688.com", wait_until="domcontentloaded", timeout=30000)
        print("  -> 请在此页面登录 1688（如果未登录）")
        print("  -> 登录完成后按回车继续...")
        input()

        # 第三页：拼多多
        print("\n[3/5] 打开拼多多...")
        page3 = await context.new_page()
        await page3.goto("https://mobile.yangkeduo.com/", wait_until="domcontentloaded", timeout=30000)
        print("  -> 请在此页面登录拼多多（如果未登录）")
        print("  -> 登录完成后按回车继续...")
        input()

        # 采集 Shopee
        print("\n[4/5] 采集 Shopee 越南站数据...")
        shopee_products = await collect_all_shopee(page1, KEYWORDS)
        save_json(shopee_products, "shopee_products.json")

        # 采集 1688
        print("\n[5/5] 采集 1688 数据...")
        sourcing_1688 = await collect_all_1688(page2, KEYWORDS)
        save_json(sourcing_1688, "sourcing_1688.json")

        # 采集拼多多
        print("\n      采集拼多多数据...")
        sourcing_pdd = await collect_all_pdd(page3, KEYWORDS)
        save_json(sourcing_pdd, "sourcing_pdd.json")

        # 价格对比
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
        print("  分析完成！")
        print("=" * 60)
        print(f"\n输出文件在 results/ 目录下")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
