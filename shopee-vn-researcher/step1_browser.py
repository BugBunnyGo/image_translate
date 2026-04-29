#!/usr/bin/env python3
"""
步骤一：启动浏览器并打开三个平台页面
运行后会弹出一个 Chromium 窗口，你在里面登录各平台
登录完成后，再运行 python3 step2_collect.py
"""
import asyncio
import sys
import os
import signal

sys.path.insert(0, os.path.dirname(__file__))

from playwright.async_api import async_playwright


async def main():
    print("=" * 60)
    print("  步骤一：启动浏览器")
    print("=" * 60)
    print()
    print("正在弹出 Chromium 窗口...")
    print("请在弹出的窗口中：")
    print("  1. 登录 Shopee 越南站 (shopee.vn)")
    print("  2. 登录 1688 (1688.com)")
    print("  3. 登录拼多多 (mobile.yangkeduo.com)")
    print()
    print("登录完成后，请重新运行：python3 step2_collect.py")
    print()

    async with async_playwright() as pw:
        # 启动浏览器（可见窗口）
        browser = await pw.chromium.launch(
            headless=False,
            args=["--window-size=1400,900"],
        )
        context = await browser.new_context(
            viewport={"width": 1400, "height": 900},
            locale="zh-CN",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )

        # 打开三个页面
        print(f"  -> 已打开 {len(context.pages)} 个页面")

        page1 = await context.new_page()
        print("  页面 1: Shopee 越南站")
        await page1.goto("https://shopee.vn", wait_until="domcontentloaded", timeout=30000)
        await page1.wait_for_timeout(2000)

        page2 = await context.new_page()
        print("  页面 2: 1688")
        await page2.goto("https://s.1688.com", wait_until="domcontentloaded", timeout=30000)
        await page2.wait_for_timeout(2000)

        page3 = await context.new_page()
        print("  页面 3: 拼多多")
        await page3.goto("https://mobile.yangkeduo.com/", wait_until="domcontentloaded", timeout=30000)
        await page3.wait_for_timeout(2000)

        print()
        print("三个页面已打开，浏览器窗口应该在你的桌面上。")
        print("完成后请运行: python3 step2_collect.py")
        print()
        print("浏览器会保持打开，直到你按 Ctrl+C 关闭。")
        print("如果不想采集了，直接关闭浏览器窗口即可。")

        # 保持浏览器打开
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n关闭浏览器...")
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
