"""
浏览器连接管理：通过 CDP 连接到已打开的 Chrome
"""
import asyncio
from playwright.async_api import async_playwright, Page, Browser, BrowserContext


async def connect_browser(cdp_host: str = "localhost", cdp_port: int = 9222) -> BrowserContext:
    """连接到已打开的 Chrome 浏览器（需带 --remote-debugging-port 启动）"""
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp(f"http://{cdp_host}:{cdp_port}")
    default_context = browser.contexts[0] if browser.contexts else await browser.new_context()
    return default_context


async def get_or_create_tab(context: BrowserContext, url: str) -> Page:
    """在已有标签页中找匹配 URL 的页面，没有则新建"""
    for page in context.pages:
        if url in page.url:
            await page.bring_to_front()
            return page
    page = await context.new_page()
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    return page


async def wait_for_selector(page: Page, selector: str, timeout: int = 10000) -> bool:
    """等待元素出现"""
    try:
        await page.wait_for_selector(selector, timeout=timeout)
        return True
    except Exception:
        return False


async def scroll_to_load(page: Page, max_scrolls: int = 20, delay_ms: int = 500):
    """滚动页面以触发懒加载"""
    for _ in range(max_scrolls):
        await page.evaluate("window.scrollBy(0, window.innerHeight)")
        await asyncio.sleep(delay_ms / 1000)


async def take_screenshot(page: Page, path: str):
    """截图用于调试"""
    await page.screenshot(path=path, full_page=True)
