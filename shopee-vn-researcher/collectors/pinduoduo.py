"""
拼多多数据采集
"""
import asyncio
from playwright.async_api import Page
from utils.data_io import save_json


async def search_pdd(page: Page, keyword: str) -> list[dict]:
    """在拼多多搜索商品并采集"""
    search_url = f"https://mobile.yangkeduo.com/proxy/api/search?keyword={keyword.replace(' ', '+')}"
    await page.goto("https://mobile.yangkeduo.com/", wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(2)

    # 尝试在搜索框输入
    try:
        search_input = await page.query_selector('input[type="text"], input[type="search"]')
        if search_input:
            await search_input.click()
            await search_input.fill(keyword)
            await page.keyboard.press("Enter")
            await asyncio.sleep(3)
    except Exception:
        # 如果移动端页面交互失败，尝试直接导航
        await page.goto(f"https://mobile.yangkeduo.com/search_result.html?search_key={keyword}",
                        wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

    items = await page.evaluate("""() => {
        const results = [];
        // 拼多多常见选择器
        const cards = document.querySelectorAll('[class*="goods"], [class*="item"], .goods-item');
        cards.forEach(card => {
            try {
                const title = card.querySelector('[class*="title"], [class*="name"]');
                const price = card.querySelector('[class*="price"]');
                const sold = card.querySelector('[class*="sold"], [class*="count"]');

                const name = title ? title.textContent.trim() : '';
                const priceRaw = price ? price.textContent.trim() : '';
                const price = parseFloat(priceRaw.replace(/[^0-9.]/g, '')) || 0;
                const soldRaw = sold ? sold.textContent.trim() : '';

                if (name && price > 0) {
                    results.push({ name, price, sold: soldRaw });
                }
            } catch (e) {}
        });
        return results;
    }""")

    products = []
    for item in items:
        if item.get("name") and item.get("price", 0) > 0:
            products.append({
                "keyword": keyword,
                "name": item.get("name", ""),
                "price_cny": item.get("price", 0),
                "sold_raw": item.get("sold", ""),
                "platform": "pinduoduo",
            })

    return products


async def collect_all_pdd(page: Page, keywords: dict) -> list[dict]:
    """采集所有中文关键词的拼多多商品数据"""
    all_products = []
    for cn_keyword in set(keywords.values()):
        print(f"\n[拼多多] 正在搜索: {cn_keyword}")
        try:
            products = await search_pdd(page, cn_keyword)
            all_products.extend(products)
            print(f"  -> 找到 {len(products)} 个商品")
            await asyncio.sleep(2)
        except Exception as e:
            print(f"  -> 搜索失败: {e}")
    return all_products
