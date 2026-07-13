"""
使用 Playwright 抓取 BT 站电影 Top 100。
- 支持多个备用源（从 config 读取 scraper_urls），依次降级尝试
- 没有任何硬编码的回退 URL。
"""
import re
import os
import logging
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from config_reader import CONFIG

logger = logging.getLogger(__name__)


def _normalize_for_dedup(title: str) -> str:
    t = title.lower().strip()
    t = re.sub(r'\band\b', '&', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def extract_title_year(name: str):
    name = re.sub(r'\.', ' ', name)
    noise = re.compile(
        r'\b(EXTENDED|REPACK|THEATRICAL|UNCUT|4K|HDR|IMAX|WEB-DL|BLURAY|'
        r'1080p|720p|2160p|x264|x265|HEVC|AAC|DTS|BluRay|BRRip|DVDRip|'
        r'WEBRip|HDTV|NF|AMZN|DSNP|HULU)\b.*$',
        re.IGNORECASE
    )
    name = noise.sub('', name).strip()

    pattern = r'^(.*?)(?:\s*\((\d{4})\)|\s+(\d{4})\s*$)'
    match = re.search(pattern, name)
    if match:
        title = match.group(1).strip()
        year = match.group(2) or match.group(3)
        return title, year
    else:
        clean = re.sub(r'\[.*?\]|\..*$', '', name).strip()
        return clean, None


def _fetch_from_url(url: str) -> list[str]:
    logger.info(f"正在抓取: {url}")
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
        except Exception:
            logger.warning("⚠️ 内置 Chromium 启动失败，尝试系统浏览器...")
            possible_paths = [
                "/usr/bin/google-chrome-stable",
                "/usr/bin/google-chrome",
                "/usr/bin/chromium",
                "/usr/bin/chromium-browser",
            ]
            system_browser = next(
                (p_ for p_ in possible_paths if os.path.exists(p_)), None
            )
            if not system_browser:
                raise RuntimeError("未找到可用的 Chrome/Chromium 浏览器")
            browser = p.chromium.launch(
                headless=True,
                executable_path=system_browser,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )

        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()

        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            try:
                page.wait_for_selector("li.list-entry", timeout=10000)
                logger.info("✅ 页面内容加载成功")
            except PlaywrightTimeout:
                logger.warning("⚠️ 等待列表超时，尝试继续解析")

            html = page.content()
        finally:
            browser.close()

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    list_items = soup.select("li.list-entry")
    logger.info(f"找到 {len(list_items)} 个条目")

    raw_names = []
    for li in list_items:
        tag = li.select_one("span.item-title a")
        if tag:
            name = tag.text.strip()
            if name:
                raw_names.append(name)

    if not raw_names:
        raise ValueError(f"页面解析结果为空，可能结构已变化: {url}")

    return raw_names


def _dedup_movies(raw_names: list[str]) -> list[str]:
    unique = {}
    for name in raw_names:
        title, year = extract_title_year(name)
        if not title or not year:
            continue
        norm_key = f"{_normalize_for_dedup(title)} {year}"
        if norm_key not in unique:
            unique[norm_key] = f"{title.strip()} {year}"

    result = sorted(unique.values())
    logger.info(f"去重后剩余 {len(result)} 部电影")
    return result


def get_top100_with_fallback() -> list[str]:
    """
    获取 Top 100 电影列表，支持多源 Fallback。
    必须从 CONFIG 中读取 scraper_urls。
    """
    urls = CONFIG.get("scraper_urls", [])
    if not urls:
        logger.error("❌ config.ini 中未配置 scraper_urls。无法继续。")
        return []

    for i, url in enumerate(urls):
        try:
            logger.info(f"[源 {i+1}/{len(urls)}] 尝试: {url}")
            raw_names = _fetch_from_url(url)
            movies = _dedup_movies(raw_names)
            if movies:
                logger.info(f"✅ 成功从 {url} 获取 {len(movies)} 部电影")
                return movies
            else:
                logger.warning(f"⚠️ 源 {url} 返回空列表，尝试下一个源")
        except Exception as e:
            logger.warning(f"⚠️ 源 {url} 失败 ({type(e).__name__}: {e})，尝试下一个源")

    logger.error("❌ 所有配置的源均失败，无法获取电影列表")
    return []
