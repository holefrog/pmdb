"""
使用 Playwright 替代 Selenium（更轻量、更快、更稳定）
安装: pip install playwright && playwright install chromium
"""
import re
import logging
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)

def extract_title_year(name):
    """Extract title and year from movie name."""
    name = re.sub(r'\.', ' ', name)
    pattern = r"^(.*?)(?:\s*\((\d{4})\)|\s+(\d{4})\s+)"
    match = re.search(pattern, name)
    if match:
        title = match.group(1).strip()
        year = match.group(2) or match.group(3)
        return title, year
    else:
        clean = re.sub(r"\[.*?\]|\..*$", "", name).strip()
        return clean, None

def get_piratebay_top100():
    """Fetch and deduplicate movie names from The Pirate Bay using Playwright."""
    url = "https://thepiratebay.org/search.php?q=top100:207"
    
    try:
        logger.info(f"正在使用 Playwright 请求 The Pirate Bay: {url}")
        
        with sync_playwright() as p:
            # 启动无头浏览器
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = context.new_page()
            
            # 访问页面
            page.goto(url, wait_until="networkidle", timeout=30000)
            
            # 等待内容加载（等待列表项出现）
            try:
                page.wait_for_selector("li.list-entry", timeout=10000)
                logger.info("✅ 页面内容加载成功")
            except PlaywrightTimeout:
                logger.warning("⚠️ 等待列表加载超时，尝试继续解析")
            
            # 获取 HTML 内容
            html = page.content()
            
            # 关闭浏览器
            browser.close()
        
        # 使用 BeautifulSoup 解析（可选，也可以用 Playwright 的选择器）
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        raw_names = set()

        list_items = soup.select("li.list-entry")
        logger.info(f"找到 {len(list_items)} 个条目")

        for li in list_items:
            name_tag = li.select_one("span.item-title a")
            if name_tag:
                name = name_tag.text.strip()
                if name:
                    raw_names.add(name)

        unique_movies = {}
        for name in raw_names:
            title, year = extract_title_year(name)
            if title and year:
                key = f"{title} {year}"
                unique_movies[key] = key

        unique_names = sorted(unique_movies.values())
        logger.info(f"去重后剩余 {len(unique_names)} 部电影")
        return unique_names
        
    except Exception as e:
        logger.error(f"❌ 抓取失败: {type(e).__name__} - {e}")
        return []
