"""
选品推荐报告生成
"""
from datetime import datetime
from config import MIN_SHOPEE_SOLD, MIN_RATING, MAX_SHOPEE_PRICE_VND, MIN_PROFIT_MARGIN
from utils.data_io import save_markdown


def generate_report(comparison_results: list[dict], shopee_count: int, sourcing_count: int):
    """生成选品推荐 Markdown 报告"""

    # 筛选推荐商品
    recommended = [r for r in comparison_results if r["recommended"]]
    high_margin = [r for r in comparison_results if r["profit_margin"] >= MIN_PROFIT_MARGIN]
    high_demand = [r for r in comparison_results if r["sold"] >= MIN_SHOPEE_SOLD]

    report = []
    report.append(f"# Shopee 越南站 3C 手机配件选品分析报告")
    report.append(f"\n> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"\n> 数据概览：Shopee 商品 {shopee_count} 条 | 采购平台商品 {sourcing_count} 条")
    report.append(f"\n---\n")

    report.append(f"## 一、筛选标准")
    report.append(f"- Shopee 最低销量：{MIN_SHOPEE_SOLD}")
    report.append(f"- 最低评分：{MIN_RATING}")
    report.append(f"- 最高售价：{MAX_SHOPEE_PRICE_VND:,.0f} VND（约 {MAX_SHOPEE_PRICE_VND * 0.00029:.0f} CNY）")
    report.append(f"- 最低利润率：{MIN_PROFIT_MARGIN * 100}%")
    report.append(f"- 价格阈值：采购价 ≤ Shopee 售价 × {MIN_PROFIT_MARGIN}")
    report.append(f"")

    report.append(f"## 二、数据摘要")
    report.append(f"- Shopee 采集商品总数：{shopee_count}")
    report.append(f"- 采购平台采集商品总数：{sourcing_count}")
    report.append(f"- 满足利润率要求的商品：{len(high_margin)}")
    report.append(f"- 高需求商品（销量>{MIN_SHOPEE_SOLD}）：{len(high_demand)}")
    report.append(f"- **综合推荐商品：{len(recommended)}**")
    report.append(f"")

    if recommended:
        report.append(f"## 三、推荐选品 TOP {min(20, len(recommended))}")
        report.append(f"")
        report.append(f"| 排名 | 品类 | 商品名 | Shopee售价(VND) | Shopee售价(CNY) | 采购价(CNY) | 利润率 | 已售 | 推荐采购平台 |")
        report.append(f"|------|------|--------|-----------------|-----------------|-------------|--------|------|-------------|")

        for i, item in enumerate(recommended[:20], 1):
            keyword_cn = item.get("keyword_vn", "")
            name = item["product_name"][:30] + "..." if len(item["product_name"]) > 30 else item["product_name"]
            report.append(
                f"| {i} | {keyword_cn} | {name} | {item['price_vnd']:,} | {item['price_cny']:.2f} "
                f"| {item['best_sourcing_price_cny']:.2f} | {item['profit_margin']*100:.1f}% "
                f"| {item['sold']:,} | {item['sourcing_platform']} |"
            )
        report.append(f"")
    else:
        report.append(f"## 三、暂无推荐商品")
        report.append(f"可能原因：")
        report.append(f"- 采购平台数据未成功采集（需要确保浏览器已登录并打开 1688/拼多多）")
        report.append(f"- Shopee 商品利润空间不足 50%")
        report.append(f"- 关键词匹配失败")
        report.append(f"")

    report.append(f"## 四、按品类分析")
    report.append(f"")

    # 按关键词分组
    categories = {}
    for item in comparison_results:
        kw = item.get("keyword_vn", "Unknown")
        if kw not in categories:
            categories[kw] = {"count": 0, "avg_price": 0, "avg_margin": 0, "max_sold": 0}
        categories[kw]["count"] += 1
        categories[kw]["avg_price"] += item["price_cny"]
        categories[kw]["avg_margin"] += item["profit_margin"]
        categories[kw]["max_sold"] = max(categories[kw]["max_sold"], item["sold"])

    report.append(f"| 品类 | 商品数 | 平均售价(CNY) | 平均利润率 | 最高销量 | 推荐 |")
    report.append(f"|------|--------|---------------|------------|----------|------|")

    for kw, stats in sorted(categories.items(), key=lambda x: x[1]["avg_margin"], reverse=True):
        count = stats["count"]
        avg_price = stats["avg_price"] / count
        avg_margin = stats["avg_margin"] / count
        max_sold = stats["max_sold"]
        rec = "⭐" if avg_margin >= MIN_PROFIT_MARGIN and max_sold >= MIN_SHOPEE_SOLD else ""
        report.append(f"| {kw} | {count} | {avg_price:.2f} | {avg_margin*100:.1f}% | {max_sold:,} | {rec} |")
    report.append(f"")

    report.append(f"## 五、新手建议")
    report.append(f"")
    report.append(f"### 适合新手的品类特征")
    report.append(f"1. **低客单价**：建议 Shopee 售价 ≤ 300,000 VND（约 87 CNY），降低试错成本")
    report.append(f"2. **高利润率**：采购价 ≤ Shopee 售价的 50%，预留物流和推广成本")
    report.append(f"3. **高需求量**：已售数量 > 100，证明市场已验证")
    report.append(f"4. **小体积/轻重量**：降低跨境物流成本")
    report.append(f"5. **低售后率**：手机壳、数据线等标准化产品，不易产生售后纠纷")
    report.append(f"")
    report.append(f"### 初期建议")
    report.append(f"- 先从 **手机壳、充电线** 这两个品类切入，市场需求大、标准化程度高")
    report.append(f"- 初期上架 10-20 个 SKU 测试市场")
    report.append(f"- 关注 Shopee 越南站的热销趋势，避开饱和的低价竞争")
    report.append(f"- 1688 采购建议小批量试单，确认质量后再批量进货")
    report.append(f"")
    report.append(f"### 风险提示")
    report.append(f"- 汇率波动会影响利润空间")
    report.append(f"- 需预留 15-20% 的物流和平台手续费成本")
    report.append(f"- 建议定期运行此脚本更新数据，跟踪市场变化")
    report.append(f"")

    content = "\n".join(report)
    save_markdown(content, "recommendation_report.md")
    return content
