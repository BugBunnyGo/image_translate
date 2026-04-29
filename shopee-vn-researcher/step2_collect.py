#!/usr/bin/env python3
"""
步骤二：连接到已打开的浏览器并采集数据
前提：step1_browser.py 正在运行，你已在三个页面完成登录
"""
import asyncio
import sys
import os
import json
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


async def main():
    print("=" * 60)
    print("  步骤二：采集数据并分析")
    print("=" * 60)
    print()

    async with async_playwright() as pw:
        # 连接到已存在的浏览器（通过共享的用户数据目录）
        # Playwright 的 persistent context 可以复用已打开的浏览器
        user_data_dir = os.path.join(os.path.dirname(__file__), ".chrome-data")
        context = await pw.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
            viewport={"width": 1400, "height": 900},
            locale="zh-CN",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )

        # 查找已打开的页面
        pages = context.pages
        print(f"当前已打开 {len(pages)} 个页面")

        # 获取页面
        shopee_page = None
        p1688_page = None
        pdd_page = None

        for page in pages:
            if "shopee" in page.url.lower():
                shopee_page = page
            elif "1688" in page.url:
                p1688_page = page
            elif "yangkeduo" in page.url:
                pdd_page = page

        # 如果没有找到对应页面，尝试创建
        if not shopee_page:
            print("  -> 未找到 Shopee 页面，正在创建...")
            shopee_page = await context.new_page()
            await shopee_page.goto("https://shopee.vn", wait_until="domcontentloaded", timeout=30000)

        if not p1688_page:
            print("  -> 未找到 1688 页面，正在创建...")
            p1688_page = await context.new_page()
            await p1688_page.goto("https://s.1688.com", wait_until="domcontentloaded", timeout=30000)

        if not pdd_page:
            print("  -> 未找到拼多多页面，正在创建...")
            pdd_page = await context.new_page()
            await pdd_page.goto("https://mobile.yangkeduo.com/", wait_until="domcontentloaded", timeout=30000)

        print()

        # 采集 Shopee
        print("[1/3] 采集 Shopee 越南站数据...")
        shopee_products = await collect_all_shopee(shopee_page, KEYWORDS)
        save_json(shopee_products, "shopee_products.json")

        # 采集 1688
        print("\n[2/3] 采集 1688 数据...")
        sourcing_1688 = await collect_all_1688(p1688_page, KEYWORDS)
        save_json(sourcing_1688, "sourcing_1688.json")

        # 采集拼多多
        print("\n[3/3] 采集拼多多数据...")
        sourcing_pdd = await collect_all_pdd(pdd_page, KEYWORDS)
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
        print("  全部完成！")
        print("=" * 60)
        print(f"\n输出文件在 results/ 目录下：")
        print(f"  - shopee_products.json    (Shopee 商品原始数据)")
        print(f"  - sourcing_1688.json      (1688 采购数据)")
        print(f"  - sourcing_pdd.json       (拼多多采购数据)")
        print(f"  - price_comparison.csv    (价格对比表)")
        print(f"  - recommendation_report.md (选品推荐报告)")

        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
