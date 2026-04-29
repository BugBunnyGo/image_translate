"""
价格对比分析模块
"""
import re
from config import PRICE_RATIO_THRESHOLD


# VND/CNY 汇率（近似值，需定期更新）
VND_TO_CNY = 0.00029  # 1 VND ≈ 0.00029 CNY


def parse_sold_number(sold_raw: str) -> int:
    """解析 '已售 1.2千' / '1.5k' / '300+sold' 等格式"""
    if not sold_raw:
        return 0
    match = re.search(r'([\d,]+\.?\d*)\s*[kK]?', sold_raw)
    if match:
        num = float(match.group(1).replace(',', ''))
        if 'k' in sold_raw.lower() or 'K' in sold_raw:
            num *= 1000
        if '千' in sold_raw:
            num *= 1000
        if '万' in sold_raw:
            num *= 10000
        return int(num)
    return 0


def parse_rating(rating_raw: str) -> float:
    """解析评分字符串"""
    if not rating_raw:
        return 0.0
    match = re.search(r'([\d.]+)', rating_raw)
    return float(match.group(1)) if match else 0.0


def vnd_to_cny(price_vnd: float) -> float:
    """越南盾转人民币"""
    return round(price_vnd * VND_TO_CNY, 2)


def cny_to_vnd(price_cny: float) -> float:
    """人民币转越南盾"""
    return round(price_cny / VND_TO_CNY)


def find_matching_sourcing(shopee_product: dict, sourcing_products: list[dict]) -> dict | None:
    """
    为 Shopee 商品在采购平台找到相似商品
    通过关键词匹配 + 名称相似度进行简单匹配
    """
    shopee_name = shopee_product["name"].lower()
    keyword = shopee_product.get("keyword", "")

    # 先用关键词过滤
    candidates = [p for p in sourcing_products if p.get("keyword") == keyword]
    if not candidates:
        candidates = sourcing_products

    # 按价格排序，找采购价最低的匹配
    best_match = None
    for candidate in candidates:
        if not best_match:
            best_match = candidate

    return best_match


def compare_prices(shopee_products: list[dict], sourcing_1688: list[dict], sourcing_pdd: list[dict]) -> list[dict]:
    """
    对比 Shopee 售价与 1688/拼多多采购价
    返回对比结果列表
    """
    all_sourcing = sourcing_1688 + sourcing_pdd
    results = []

    for product in shopee_products:
        price_vnd = product.get("price_vnd", 0)
        if price_vnd <= 0:
            continue

        price_cny_equivalent = vnd_to_cny(price_vnd)
        sold = parse_sold_number(product.get("sold_raw", ""))
        rating = parse_rating(product.get("rating_raw", ""))

        # 找到匹配的采购商品
        match_1688 = find_matching_sourcing(product, sourcing_1688)
        match_pdd = find_matching_sourcing(product, sourcing_pdd)

        price_1688 = match_1688.get("price_cny", 0) if match_1688 else 0
        price_pdd = match_pdd.get("price_cny", 0) if match_pdd else 0

        # 取最低采购价
        best_sourcing_price = min(
            price for price in [price_1688, price_pdd] if price > 0
        ) if any(p > 0 for p in [price_1688, price_pdd]) else 0

        # 计算利润率
        if best_sourcing_price > 0:
            profit_margin = (price_cny_equivalent - best_sourcing_price) / price_cny_equivalent
            price_ratio = best_sourcing_price / price_cny_equivalent
        else:
            profit_margin = 0
            price_ratio = 0

        recommended = profit_margin >= PRICE_RATIO_THRESHOLD and sold >= 100

        results.append({
            "keyword_vn": product.get("keyword", ""),
            "keyword_cn": product.get("keyword_cn", ""),
            "product_name": product.get("name", ""),
            "price_vnd": price_vnd,
            "price_cny": price_cny_equivalent,
            "sold": sold,
            "rating": rating,
            "price_1688_cny": price_1688,
            "price_pdd_cny": price_pdd,
            "best_sourcing_price_cny": best_sourcing_price,
            "sourcing_platform": (match_1688 or match_pdd or {}).get("platform", "N/A"),
            "profit_margin": round(profit_margin, 4),
            "price_ratio": round(price_ratio, 4),
            "recommended": recommended,
            "link": product.get("link", ""),
        })

    # 按利润率降序排序
    results.sort(key=lambda x: x["profit_margin"], reverse=True)
    return results
