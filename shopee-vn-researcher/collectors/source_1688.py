"""
1688 数据采集
"""
import asyncio
from playwright.async_api import Page
from utils.data_io import save_json


async def search_1688(page: Page, keyword: str) -> list[dict]:
    """在 1688 搜索商品并采集"""
    search_url = f"https://s.1688.com/selloffer/offer_search.htm?keywords={keyword.replace(' ', '+')}"
    await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(3)

    items = await page.evaluate("""() => {
        const results = [];
        const cards = document.querySelectorAll('.offer-item, .sm-offer-item, .list-item-offer');
        cards.forEach(card => {
            try {
                const nameEl = card.querySelector('.title-text, .offer-title, .sm-offer-title');
                const priceEl = card.querySelector('.price-text, .offer-price, .sm-offer-price');
                const soldEl = card.querySelector('.deal-count, .sm-offer-sold');
                const shopEl = card.querySelector('.shop-name, .sm-offer-shop');

                const name = nameEl ? nameEl.textContent.trim() : '';
                const priceRaw = priceEl ? priceEl.textContent.trim() : '';
                const price = parseFloat(priceRaw.replace(/[^0-9.]/g, '')) || 0;
                const sold = soldEl ? soldEl.textContent.trim() : '';
                const shop = shopEl ? shopEl.textContent.trim() : '';

                results.push({ name, price, sold, shop });
            } catch (e) {}
        });
        return results;
    }""")

    # 备用选择器
    if not items:
        items = await page.evaluate("""() => {
            const results = [];
            const cards = document.querySelectorAll('[class*="offer"], [class*="list-item"]');
            cards.forEach(card => {
                try {
                    const title = card.querySelector('[class*="title"]');
                    const price = card.querySelector('[class*="price"]');
                    if (title && price) {
                        const priceVal = parseFloat(price.textContent.replace(/[^0-9.]/g, '')) || 0;
                        if (priceVal > 0) {
                            results.push({
                                name: title.textContent.trim(),
                                price: priceVal,
                                sold: '',
                                shop: ''
                            });
                        }
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
                "shop": item.get("shop", ""),
                "platform": "1688",
            })

    return products


async def collect_all_1688(page: Page, keywords: dict) -> list[dict]:
    """采集所有中文关键词的商品数据"""
    all_products = []
    for cn_keyword in set(keywords.values()):
        print(f"\n[1688] 正在搜索: {cn_keyword}")
        try:
            products = await search_1688(page, cn_keyword)
            all_products.extend(products)
            print(f"  -> 找到 {len(products)} 个商品")
            await asyncio.sleep(2)
        except Exception as e:
            print(f"  -> 搜索失败: {e}")
    return all_products
