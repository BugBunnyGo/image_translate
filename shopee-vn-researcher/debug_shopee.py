import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1400, "height": 900})
        page = await context.new_page()

        print("打开 Shopee 搜索页...")
        await page.goto("https://shopee.vn/search?keyword=%C3%94p+l%C6%B0ng",
                        wait_until="networkidle", timeout=60000)
        print(f"当前 URL: {page.url}")
        print(f"页面标题: {await page.title()}")

        # 等待 5 秒让 JS 渲染
        await asyncio.sleep(5)

        # 截图
        await page.screenshot(path="debug_shopee.png", full_page=True)
        print("截图已保存: debug_shopee.png")

        # 尝试所有可能的选择器
        selectors = [
            '[data-sqe="item"]',
            '.shop-search-result-view__item',
            'a[href*="/i/"]',
            '[class*="search-result"]',
            '[class*="item"]',
            '[class*="card"]',
            '[class*="product"]',
            '.shopee-search-item-result__item',
            'main a',
        ]
        for sel in selectors:
            try:
                count = await page.evaluate(f'document.querySelectorAll("{sel}").length')
                print(f"  {sel}: {count}")
            except Exception as e:
                print(f"  {sel}: ERROR - {e}")

        # 获取 body 的 innerHTML 前 3000 字符
        html = await page.evaluate("document.body.innerHTML.substring(0, 3000)")
        print(f"\nHTML 前 3000 字符:\n{html[:3000]}")

        # 保存完整 HTML
        full_html = await page.content()
        with open("debug_shopee.html", "w", encoding="utf-8") as f:
            f.write(full_html)
        print(f"\n完整 HTML 已保存: debug_shopee.html ({len(full_html)} bytes)")

        await browser.close()


asyncio.run(main())
