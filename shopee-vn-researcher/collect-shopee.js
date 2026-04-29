/*
Shopee 越南站采集脚本
使用方法：
1. 在 Chrome 中打开 shopee.vn，搜索 "Ốp lưng điện thoại" 或其他关键词
2. 按 F12 打开开发者工具
3. 粘贴此脚本到 Console 中运行
4. 结果会显示在控制台，并自动复制到剪贴板
*/

(async function() {
    const keyword = prompt('请输入搜索关键词（越南语）：', 'Ốp lưng điện thoại');
    if (!keyword) return;

    // 导航到搜索页
    window.location.href = `https://shopee.vn/search?keyword=${encodeURIComponent(keyword)}`;

    // 等待页面加载
    await new Promise(r => setTimeout(r, 3000));

    // 滚动加载
    console.log('正在滚动加载更多...');
    for (let i = 0; i < 20; i++) {
        window.scrollBy(0, window.innerHeight);
        await new Promise(r => setTimeout(r, 800));
    }

    // 采集商品数据
    const results = [];

    // 方案A：data-sqe 属性（Shopee 常见选择器）
    let items = document.querySelectorAll('[data-sqe="item"]');

    // 方案B：通用选择器
    if (items.length === 0) {
        items = document.querySelectorAll('.shop-search-result-view__item, [class*="item"], [class*="card"]');
    }

    console.log(`找到 ${items.length} 个商品元素`);

    items.forEach((item, idx) => {
        try {
            const nameEl = item.querySelector('[data-sqe="item_name"], [class*="name"], [class*="title"], h3, h4');
            const priceEl = item.querySelector('[data-sqe="item_price"], [class*="price"]');
            const soldEl = item.querySelector('[data-sqe="item_sold"], [class*="sold"], [class*="sales"]');
            const ratingEl = item.querySelector('[data-sqe="item_rating"], [class*="rating"], [class*="star"]');
            const linkEl = item.querySelector('a');

            const name = nameEl ? nameEl.textContent.trim() : '';
            const priceRaw = priceEl ? priceEl.textContent.trim() : '';
            const price = parseInt(priceRaw.replace(/[^0-9]/g, '')) || 0;
            const sold = soldEl ? soldEl.textContent.trim() : '';
            const rating = ratingEl ? ratingEl.textContent.trim() : '';
            const link = linkEl ? linkEl.href : '';

            if (name && price > 0) {
                results.push({
                    index: idx + 1,
                    name,
                    price_vnd: price,
                    sold_raw: sold,
                    rating_raw: rating,
                    link
                });
            }
        } catch (e) {}
    });

    console.log(`\n===== 采集结果：${results.length} 个商品 =====`);
    console.log(JSON.stringify(results, null, 2));

    // 复制到剪贴板
    copy(JSON.stringify(results, null, 2));
    console.log('\n已复制到剪贴板！');

    // 显示摘要
    results.forEach(r => {
        console.log(`  ${r.index}. ${r.name.substring(0, 40)} | ₫${r.price_vnd.toLocaleString()} | ${r.sold_raw} | ${r.rating_raw}`);
    });
    console.log(`\n共 ${results.length} 个商品`);
})();
