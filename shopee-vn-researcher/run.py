#!/usr/bin/env python3
"""
Shopee 越南站 3C 手机配件选品分析工具
主入口：连接已打开的 Chrome，采集数据，对比价格，生成选品报告
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from config import CDP_HOST, CDP_PORT, KEYWORDS
from browser import connect_browser, get_or_create_tab
from collectors.shopee_vn import collect_all_shopee
from collectors.source_1688 import collect_all_1688
from collectors.pinduoduo import collect_all_pdd
from analyzer.price_compare import compare_prices
from analyzer.recommendation import generate_report
from utils.data_io import save_json, save_csv


async def main():
    print("=" * 60)
    print("  Shopee 越南站 3C 手机配件选品分析工具")
    print("=" * 60)
    print()
    print("请确保：")
    print("  1. Chrome 已带调试端口启动:")
    print("     macOS: open -a 'Google Chrome' --args --remote-debugging-port=9222")
    print("     Windows: chrome.exe --remote-debugging-port=9222")
    print("  2. 已在 Chrome 中登录 shopee.vn 和 1688.com")
    print("  3. 按任意键继续...")
    print()

    try:
        input()
    except KeyboardInterrupt:
        print("\n已取消")
        return

    # 连接浏览器
    print("[1/5] 连接 Chrome 浏览器...")
    try:
        context = await connect_browser(CDP_HOST, CDP_PORT)
        print(f"  -> 已连接，当前打开 {len(context.pages)} 个标签页")
    except Exception as e:
        print(f"  -> 连接失败：{e}")
        print("  -> 请先按上述步骤启动 Chrome 并带 --remote-debugging-port=9222")
        return

    # 采集 Shopee 数据
    print("\n[2/5] 采集 Shopee 越南站数据...")
    shopee_page = await get_or_create_tab(context, "shopee.vn")
    shopee_products = await collect_all_shopee(shopee_page, KEYWORDS)
    save_json(shopee_products, "shopee_products.json")

    # 采集 1688 数据
    print("\n[3/5] 采集 1688 数据...")
    page_1688 = await get_or_create_tab(context, "1688.com")
    sourcing_1688 = await collect_all_1688(page_1688, KEYWORDS)
    save_json(sourcing_1688, "sourcing_1688.json")

    # 采集拼多多数据
    print("\n[4/5] 采集拼多多数据...")
    page_pdd = await get_or_create_tab(context, "yangkeduo.com")
    sourcing_pdd = await collect_all_pdd(page_pdd, KEYWORDS)
    save_json(sourcing_pdd, "sourcing_pdd.json")

    # 价格对比
    print("\n[5/5] 分析数据，生成选品报告...")
    comparison = compare_prices(shopee_products, sourcing_1688, sourcing_pdd)
    save_csv(comparison, "price_comparison.csv")

    report = generate_report(
        comparison,
        shopee_count=len(shopee_products),
        sourcing_count=len(sourcing_1688) + len(sourcing_pdd),
    )

    print()
    print("=" * 60)
    print("  分析完成！")
    print("=" * 60)
    print(f"\n输出文件在 results/ 目录下：")
    print(f"  - shopee_products.json  (Shopee 商品原始数据)")
    print(f"  - sourcing_1688.json    (1688 采购数据)")
    print(f"  - sourcing_pdd.json     (拼多多采购数据)")
    print(f"  - price_comparison.csv  (价格对比表)")
    print(f"  - recommendation_report.md (选品推荐报告)")


if __name__ == "__main__":
    asyncio.run(main())
