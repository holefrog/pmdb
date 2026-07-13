"""
使用 Playwright 抓取 BT 站电影 Top 100。
- 支持多个备用源（从 config 读取 scraper_urls），依次降级尝试
- 去重时统一转小写，避免大小写导致的重复
- 标准化 & / AND，确保去重 key 一致
"""
import re
import os
import logging
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)

# 内置备用镜像列表（config 中未配置时使用）
DEFAULT_SCRAPER_URLS = [
    "https://thepiratebay.org/search.php?q=top100:207",
    "https://piratebay.live/search.php?q=top100:207",
    "https://tpb.party/search.php?q=top100:207",
    "https://thepiratebay.org/top/207",
]


def _normalize_for_dedup(title: str) -> str:
    """
    将标题规范化用于去重 key，不改变显示用的原始标题。
    - 统一小写
    - & 与 And/AND 统一为 &
    - 多余空格合并
    - 去除撇号（Tom Clancy's → tom clancys）以对齐种子命名
    """
    t = title.lower().strip()
    # 把 " and " 统一成 " & "（用于去重比较）
    t = re.sub(r'\band\b', '&', t)
    # 合并连续空格（& 两侧可能有不对称空格）
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def extract_title_year(name: str):
    """从种子名中提取标题和年份。"""
    # 先替换点为空格（部分种子用点分隔）
    name = re.sub(r'\.', ' ', name)
    # 常见质量标签去除（避免影响标题提取）
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
    """
    使用 Playwright 从单个 URL 抓取电影名，返回原始名称列表。
    失败时抛出异常（由调用方捕获并尝试下一个源）。
    """
    logger.info(f"正在抓取: {url}")
    with sync_playwright() as p:
        # 尝试 Playwright 内置 Chromium，失败则找系统浏览器
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
    """
    去重：key = 规范化标题 + 年份（统一小写、& 标准化），value 保留原始大小写标题。
    返回格式：["Title Year", ...]
    """
    unique = {}  # key: normalized_key → value: "OriginalTitle Year"
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


def get_top100_with_fallback(config: dict | None = None) -> list[str]:
    """
    获取 Top 100 电影列表，支持多源 Fallback。
    - 先从 config['scraper_urls'] 读取 URL 列表
    - 若 config 为 None 或未配置，使用内置默认列表
    - 依次尝试每个 URL，第一个成功即返回
    """
    urls = DEFAULT_SCRAPER_URLS.copy()
    if config:
        configured = config.get("scraper_urls", [])
        if configured:
            # 用户配置的在前，内置的在后作为最终兜底
            urls = configured + [u for u in DEFAULT_SCRAPER_URLS if u not in configured]

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

    logger.error("❌ 所有源均失败，无法获取电影列表")
    return []


# 保留旧函数名作为兼容层（供其他可能调用旧接口的脚本使用）
def get_piratebay_top100() -> list[str]:
    """兼容旧接口，内部调用 get_top100_with_fallback()"""
    return get_top100_with_fallback(config=None)
