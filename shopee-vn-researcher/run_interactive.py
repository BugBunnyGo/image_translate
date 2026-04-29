#!/usr/bin/env python3
"""
交互版：Playwright 直接启动 Chromium，用户按回车确认登录完成
在终端中运行：python3 run_interactive.py
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
        print("\n[1/5] 已打开 Shopee 越南站...")
        page1 = await context.new_page()
        await page1.goto("https://shopee.vn", wait_until="domcontentloaded", timeout=30000)
        print("  如果未登录，请在弹出的浏览器窗口中登录 Shopee")
        print("  登录完成后，在此按回车继续 -> ", end="", flush=True)
        input()

        # 第二页：1688
        print("\n[2/5] 已打开 1688...")
        page2 = await context.new_page()
        await page2.goto("https://s.1688.com", wait_until="domcontentloaded", timeout=30000)
        print("  如果未登录，请在弹出的浏览器窗口中登录 1688")
        print("  登录完成后，在此按回车继续 -> ", end="", flush=True)
        input()

        # 第三页：拼多多
        print("\n[3/5] 已打开拼多多...")
        page3 = await context.new_page()
        await page3.goto("https://mobile.yangkeduo.com/", wait_until="domcontentloaded", timeout=30000)
        print("  如果未登录，请在弹出的浏览器窗口中登录拼多多")
        print("  登录完成后，在此按回车继续 -> ", end="", flush=True)
        input()

        # 采集 Shopee
        print("\n[4/5] 开始采集 Shopee 越南站数据（约需 2 分钟）...")
        shopee_products = await collect_all_shopee(page1, KEYWORDS)
        save_json(shopee_products, "shopee_products.json")

        # 采集 1688
        print("\n[5/5] 开始采集 1688 数据（约需 2 分钟）...")
        sourcing_1688 = await collect_all_1688(page2, KEYWORDS)
        save_json(sourcing_1688, "sourcing_1688.json")

        # 采集拼多多
        print("\n      开始采集拼多多数据（约需 2 分钟）...")
        sourcing_pdd = await collect_all_pdd(page3, KEYWORDS)
        save_json(sourcing_pdd, "sourcing_pdd.json")

        # 价格对比
        print("\n正在分析数据，生成选品报告...")
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
        print(f"\n输出文件在 results/ 目录下：")
        print(f"  - shopee_products.json    (Shopee 商品原始数据)")
        print(f"  - sourcing_1688.json      (1688 采购数据)")
        print(f"  - sourcing_pdd.json       (拼多多采购数据)")
        print(f"  - price_comparison.csv    (价格对比表)")
        print(f"  - recommendation_report.md (选品推荐报告 ⭐)")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
