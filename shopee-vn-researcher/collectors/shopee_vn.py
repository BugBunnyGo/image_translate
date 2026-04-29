"""
Shopee 越南站数据采集
"""
import asyncio
from playwright.async_api import Page
from utils.data_io import save_json


async def search_shopee_vn(page: Page, keyword: str) -> list[dict]:
    """
    在 Shopee 越南站搜索商品并采集数据
    返回商品列表
    """
    search_url = f"https://shopee.vn/search?keyword={keyword.replace(' ', '+')}"
    await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(3)

    products = []

    # 滚动加载更多内容
    for _ in range(15):
        await page.evaluate("window.scrollBy(0, window.innerHeight)")
        await asyncio.sleep(0.8)

    # 采集商品信息
    items = await page.evaluate("""() => {
        const cards = document.querySelectorAll('[data-sqe="item"]');
        const results = [];
        cards.forEach(card => {
            try {
                const nameEl = card.querySelector('[data-sqe="item_name"]');
                const priceEl = card.querySelector('[data-sqe="item_price"]');
                const soldEl = card.querySelector('[data-sqe="item_sold"]');
                const ratingEl = card.querySelector('[data-sqe="item_rating"]');
                const linkEl = card.querySelector('a');

                const name = nameEl ? nameEl.textContent.trim() : '';
                const priceRaw = priceEl ? priceEl.textContent.trim() : '';
                const price = parseInt(priceRaw.replace(/[^0-9]/g, '')) || 0;
                const sold = soldEl ? soldEl.textContent.trim() : '';
                const rating = ratingEl ? ratingEl.textContent.trim() : '';
                const link = linkEl ? linkEl.href : '';

                results.push({ name, price, priceRaw, sold, rating, link });
            } catch (e) {}
        });
        return results;
    }""")

    # 尝试通过 CSS 选择器采集（备用方案）
    if not items:
        items = await page.evaluate("""() => {
            const results = [];
            const cards = document.querySelectorAll('.shop-search-result-view__item, ._1UoZlX');
            cards.forEach(card => {
                try {
                    const nameEl = card.querySelector('.yLeMR9, .Ic8Hgf');
                    const priceEl = card.querySelector('.HPA6I8, ._1xRDHk');
                    const soldEl = card.querySelector('.sMl93z, ._14OL1j');
                    const ratingEl = card.querySelector('.m7i7dM');

                    const name = nameEl ? nameEl.textContent.trim() : '';
                    const priceRaw = priceEl ? priceEl.textContent.trim() : '';
                    const price = parseInt(priceRaw.replace(/[^0-9]/g, '')) || 0;
                    const sold = soldEl ? soldEl.textContent.trim() : '';
                    const rating = ratingEl ? ratingEl.textContent.trim() : '';

                    results.push({ name, price, priceRaw, sold, rating, link: '' });
                } catch (e) {}
            });
            return results;
        }""")

    for item in items:
        if item.get("name") and item.get("price", 0) > 0:
            products.append({
                "keyword": keyword,
                "name": item.get("name", ""),
                "price_vnd": item.get("price", 0),
                "sold_raw": item.get("sold", ""),
                "rating_raw": item.get("rating", ""),
                "link": item.get("link", ""),
                "platform": "shopee_vn",
            })

    return products


async def collect_all_shopee(page: Page, keywords: dict) -> list[dict]:
    """采集所有关键词的商品数据"""
    all_products = []
    for vn_keyword, cn_keyword in keywords.items():
        print(f"\n[Shopee] 正在搜索: {cn_keyword} ({vn_keyword})")
        try:
            products = await search_shopee_vn(page, vn_keyword)
            all_products.extend(products)
            print(f"  -> 找到 {len(products)} 个商品")
            await asyncio.sleep(2)
        except Exception as e:
            print(f"  -> 搜索失败: {e}")
    return all_products
