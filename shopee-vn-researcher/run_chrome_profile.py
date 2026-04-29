#!/usr/bin/env python3
"""
使用 Playwright 以 Chrome 用户数据目录启动（复用登录态）
"""
import asyncio
import sys
import os
import glob

sys.path.insert(0, os.path.dirname(__file__))

from playwright.async_api import async_playwright


def find_chrome_profile_dir():
    """查找 Chrome 的用户数据目录"""
    base = "/Users/srcrs/Library/Application Support/Google/Chrome"
    if os.path.exists(base):
        return base
    return None


async def main():
    print("=" * 60)
    print("  使用 Chrome 用户数据目录启动 Playwright")
    print("=" * 60)
    print()

    chrome_data_dir = find_chrome_profile_dir()
    if chrome_data_dir:
        print(f"找到 Chrome 数据目录：{chrome_data_dir}")
    else:
        print("未找到 Chrome 数据目录")
        return

    # 需要关闭正在运行的 Chrome
    print("请先关闭 Chrome 浏览器，然后按回车继续...")
    try:
        input()
    except (KeyboardInterrupt, EOFError):
        return

    async with async_playwright() as pw:
        print("正在启动 Chromium（复用 Chrome 登录态）...")
        context = await pw.chromium.launch_persistent_context(
            chrome_data_dir,
            headless=False,
            viewport={"width": 1400, "height": 900},
            locale="zh-CN",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )

        print(f"已启动，当前有 {len(context.pages)} 个页面")

        # 打开目标页面
        for url, name in [
            ("https://shopee.vn", "Shopee 越南站"),
            ("https://s.1688.com", "1688"),
            ("https://mobile.yangkeduo.com/", "拼多多"),
        ]:
            page = await context.new_page()
            print(f"\n打开 {name}...")
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)
                print(f"  -> 页面已加载: {page.title}")
            except Exception as e:
                print(f"  -> 加载失败: {e}")

        print()
        print("页面已打开，请按 Ctrl+C 关闭浏览器")

        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n关闭浏览器...")
            await context.close()


if __name__ == "__main__":
    asyncio.run(main())
