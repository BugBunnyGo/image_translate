#!/usr/bin/env python3
"""
通过 AppleScript 控制用户已有的 Chrome 浏览器采集数据
不需要重启浏览器，不需要 CDP 端口
"""
import subprocess
import json
import os
import time


def run_applescript(script: str) -> str:
    """执行 AppleScript 并返回输出"""
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=30
    )
    return result.stdout.strip()


def execute_js_in_tab(tab_index: int, js_code: str) -> str:
    """在指定标签页执行 JavaScript 并返回结果"""
    # 先激活该标签页
    activate_script = f'''
        tell application "Google Chrome"
            activate
            set active tab index of window 1 to {tab_index}
        end tell
    '''
    run_applescript(activate_script)
    time.sleep(1)

    # 执行 JavaScript
    # Chrome AppleScript 语法: execute <tab> javascript "<code>"
    # 使用临时文件避免引号转义问题
    js_file = "/tmp/chrome_exec_js.txt"
    with open(js_file, "w") as f:
        f.write(js_code)

    exec_script = f'''
        tell application "Google Chrome"
            set jsFile to POSIX file "{js_file}"
            set jsCode to read jsFile as string
            set jsResult to execute active tab of window 1 javascript jsCode
            return jsResult
        end tell
    '''
    return run_applescript(exec_script)


def list_tabs() -> list:
    """列出所有标签页的标题和URL"""
    script = '''
        tell application "Google Chrome"
            set result to ""
            set i to 1
            repeat with t in tabs of window 1
                set result to result & i & " | " & (title of t) & " | " & (URL of t) & "\\n"
                set i to i + 1
            end repeat
            return result
        end tell
    '''
    output = run_applescript(script)
    tabs = []
    for line in output.strip().split('\n'):
        if ' | ' in line:
            parts = line.split(' | ', 2)
            if len(parts) == 3:
                tabs.append({
                    "index": int(parts[0]),
                    "title": parts[1],
                    "url": parts[2],
                })
    return tabs


def main():
    print("=" * 60)
    print("  Shopee 越南站 3C 手机配件选品分析工具")
    print("  模式：AppleScript 控制现有 Chrome")
    print("=" * 60)
    print()

    # 列出标签页
    tabs = list_tabs()
    print(f"当前 Chrome 共有 {len(tabs)} 个标签页：")
    print()
    for tab in tabs:
        print(f"  [{tab['index']}] {tab['title'][:60]}")
        print(f"      {tab['url'][:80]}")
        print()

    # 识别对应平台
    shopee_tab = None
    alibaba_tab = None
    pdd_tab = None

    for tab in tabs:
        url = tab["url"].lower()
        if "shopee.vn" in url or "shopee" in url:
            shopee_tab = tab
        elif "1688" in url or "alibaba.com" in url:
            alibaba_tab = tab
        elif "yangkeduo" in url:
            pdd_tab = tab

    if not shopee_tab:
        print("未找到 Shopee 标签页，请先打开 shopee.vn")
        return
    if not alibaba_tab:
        print("未找到 1688/阿里巴巴 标签页，请先打开 1688.com")
        return
    if not pdd_tab:
        print("未找到拼多多 标签页，请先打开 mobile.yangkeduo.com")
        return

    print("识别到目标平台：")
    print(f"  Shopee:     标签页 {shopee_tab['index']}")
    print(f"  1688/阿里:  标签页 {alibaba_tab['index']}")
    print(f"  拼多多:     标签页 {pdd_tab['index']}")
    print()

    # 采集 Shopee
    print("[1/3] 采集 Shopee 越南站数据...")
    shopee_js = '''
        (function() {
            var results = [];
            var items = document.querySelectorAll('[data-sqe="item"], ._35cDcS, ._1cSFKC, ._2c3YfD');
            if (items.length === 0) {
                items = document.querySelectorAll('[class*="item"], [class*="card"], [class*="product"]');
            }
            items.forEach(function(item) {
                try {
                    var nameEl = item.querySelector('[data-sqe="item_name"], [class*="title"], [class*="name"], h3, .shopee-search-item-result__name');
                    var priceEl = item.querySelector('[data-sqe="item_price"], [class*="price"], .shopee-search-item-result__price');
                    var soldEl = item.querySelector('[data-sqe="item_sold"], [class*="sold"], [class*="sales"], .shopee-search-item-result__sales');
                    var ratingEl = item.querySelector('[data-sqe="item_rating"], [class*="rating"], [class*="star"], .shopee-search-item-result__rating');
                    var linkEl = item.querySelector('a');

                    var name = nameEl ? nameEl.innerText.trim() : '';
                    var priceRaw = priceEl ? priceEl.innerText.trim() : '';
                    var price = parseInt(priceRaw.replace(/[^0-9]/g, '')) || 0;
                    var sold = soldEl ? soldEl.innerText.trim() : '';
                    var rating = ratingEl ? ratingEl.innerText.trim() : '';
                    var link = linkEl ? linkEl.href : '';

                    if (name && price > 0) {
                        results.push({name: name, price: price, sold: sold, rating: rating, link: link});
                    }
                } catch(e) {}
            });
            return JSON.stringify(results);
        })()
    '''
    shopee_result = execute_js_in_tab(shopee_tab["index"], shopee_js)
    try:
        shopee_data = json.loads(shopee_result)
    except (json.JSONDecodeError, TypeError):
        print(f"  -> Shopee 数据解析失败，原始输出：{shopee_result[:200]}")
        shopee_data = []
    print(f"  -> 采集到 {len(shopee_data)} 个商品")

    # 采集 1688/阿里巴巴
    print("\n[2/3] 采集 1688/阿里巴巴数据...")
    p1688_js = '''
        (function() {
            var results = [];
            var items = document.querySelectorAll('.offer-item, .sm-offer-item, [class*="offer"], [class*="item"], [class*="product"]');
            items.forEach(function(item) {
                try {
                    var title = item.querySelector('[class*="title"], [class*="name"], h3, h4');
                    var price = item.querySelector('[class*="price"], .price');
                    var sold = item.querySelector('[class*="sold"], [class*="sales"], [class*="deal"]');
                    var shop = item.querySelector('[class*="shop"], [class*="company"], [class*="supplier"]');

                    var name = title ? title.innerText.trim() : '';
                    var priceRaw = price ? price.innerText.trim() : '';
                    var priceVal = parseFloat(priceRaw.replace(/[^0-9.]/g, '')) || 0;
                    var soldRaw = sold ? sold.innerText.trim() : '';
                    var shopName = shop ? shop.innerText.trim() : '';

                    if (name && priceVal > 0) {
                        results.push({name: name, price: priceVal, sold: soldRaw, shop: shopName});
                    }
                } catch(e) {}
            });
            return JSON.stringify(results);
        })()
    '''
    p1688_result = execute_js_in_tab(alibaba_tab["index"], p1688_js)
    try:
        p1688_data = json.loads(p1688_result)
    except (json.JSONDecodeError, TypeError):
        print(f"  -> 1688 数据解析失败，原始输出：{p1688_result[:200]}")
        p1688_data = []
    print(f"  -> 采集到 {len(p1688_data)} 个商品")

    # 采集拼多多
    print("\n[3/3] 采集拼多多数据...")
    pdd_js = '''
        (function() {
            var results = [];
            var items = document.querySelectorAll('.goods-item, [class*="goods"], [class*="item"], [class*="product"]');
            items.forEach(function(item) {
                try {
                    var title = item.querySelector('[class*="title"], [class*="name"], h3, h4');
                    var price = item.querySelector('[class*="price"], .price');
                    var sold = item.querySelector('[class*="sold"], [class*="sales"], [class*="count"]');

                    var name = title ? title.innerText.trim() : '';
                    var priceRaw = price ? price.innerText.trim() : '';
                    var priceVal = parseFloat(priceRaw.replace(/[^0-9.]/g, '')) || 0;
                    var soldRaw = sold ? sold.innerText.trim() : '';

                    if (name && priceVal > 0) {
                        results.push({name: name, price: priceVal, sold: soldRaw});
                    }
                } catch(e) {}
            });
            return JSON.stringify(results);
        })()
    '''
    pdd_result = execute_js_in_tab(pdd_tab["index"], pdd_js)
    try:
        pdd_data = json.loads(pdd_result)
    except (json.JSONDecodeError, TypeError):
        print(f"  -> 拼多多数据解析失败，原始输出：{pdd_result[:200]}")
        pdd_data = []
    print(f"  -> 采集到 {len(pdd_data)} 个商品")

    # 保存数据
    output_dir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(output_dir, exist_ok=True)

    for filename, data in [
        ("shopee_products.json", shopee_data),
        ("sourcing_1688.json", p1688_data),
        ("sourcing_pdd.json", pdd_data),
    ]:
        path = os.path.join(output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  已保存 {path} ({len(data)} 条)")

    print()
    print("采集完成！下一步运行: python3 analyze.py 进行价格对比和选品分析")


if __name__ == "__main__":
    main()
