import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import re
import random
import time
from typing import Tuple, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging

logger = logging.getLogger(__name__)

# 预编译正则表达式（性能优化）
COMPILED_PATTERNS = [
    re.compile(r'\bEXTENDED\b', re.IGNORECASE),
    re.compile(r'\bREPACK\b', re.IGNORECASE),
    re.compile(r'\bTHEATRICAL\b', re.IGNORECASE),
    re.compile(r'\bUNCUT\b', re.IGNORECASE),
    re.compile(r'\b4K\b', re.IGNORECASE),
    re.compile(r'\bHDR\b', re.IGNORECASE),
    re.compile(r'\bIMAX\b', re.IGNORECASE),
    re.compile(r'\bWEB-DL\b', re.IGNORECASE),
    re.compile(r'\bBLURAY\b', re.IGNORECASE),
    re.compile(r'\{Extended\}', re.IGNORECASE)
]

def get_session_with_retries():
    """Create a requests session with automatic retry mechanism."""
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    return session

def clean_title_for_search(title: str) -> str:
    """Strips common torrent/edition tags using precompiled regex patterns."""
    cleaned_title = title
    for pattern in COMPILED_PATTERNS:
        cleaned_title = pattern.sub('', cleaned_title).strip()
    
    # 移除多余空格
    cleaned_title = re.sub(r'\s+', ' ', cleaned_title).strip()
    return cleaned_title

def get_imdb_info(name: str, config: dict) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Query IMDb with enhanced fuzzy search and date-filter fallback (Web Scraping).
    
    Args:
        name: Movie name in format "Title Year"
        config: Configuration dict containing retry delays
        
    Returns:
        Tuple of (rating, summary, image_url) or (None, None, None) if not found
    """
    
    # 提取标题和年份
    parts = name.rsplit(" ", 1)
    title = parts[0]
    year = parts[1] if len(parts) > 1 and parts[1].isdigit() else None

    if not year:
        logger.warning(f"跳过 IMDb 搜索 '{name}' - 缺少年份")
        return None, None, None

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }

    session = get_session_with_retries()
    
    def fetch_movie_info(search_url):
        """封装请求逻辑，用于多轮尝试"""
        try:
            # 随机延迟，避免触发反爬虫
            delay = random.uniform(
                config.get('retry_delay_min', 0.2), 
                config.get('retry_delay_max', 0.5)
            )
            time.sleep(delay)
            
            timeout = config.get('request_timeout', 10)
            response = session.get(search_url, headers=headers, timeout=timeout)
            
            if response.status_code != 200:
                return None, None, None

            soup = BeautifulSoup(response.text, "html.parser")
            result = soup.select_one("li.ipc-metadata-list-summary-item")
            if not result:
                return None, None, None

            # 提取电影详情页URL
            link = result.find("a", class_="ipc-title-link-wrapper")
            if not link or 'href' not in link.attrs:
                return None, None, None

            movie_url = "https://www.imdb.com" + link['href'].split('?')[0]
            
            # 访问电影详情页
            time.sleep(delay)
            movie_response = session.get(movie_url, headers=headers, timeout=timeout)
            if movie_response.status_code != 200:
                return None, None, None

            movie_soup = BeautifulSoup(movie_response.text, "html.parser")

            # 提取评分
            rating_tag = movie_soup.select_one("div[data-testid='hero-rating-bar__aggregate-rating__score'] span")
            rating = rating_tag.get_text(strip=True) if rating_tag else "N/A"

            # 提取简介
            summary_tag = movie_soup.select_one("span[data-testid='plot-xl']")
            summary = summary_tag.get_text(strip=True) if summary_tag else "No summary available."

            # 提取海报URL
            image_tag = movie_soup.select_one("img.ipc-image")
            image_url = image_tag['src'] if image_tag and 'src' in image_tag.attrs else "https://via.placeholder.com/150"

            if rating == "N/A" and summary == "No summary available.":
                return None, None, None

            return rating, summary, image_url

        except requests.ConnectionError:
            logger.debug(f"网络连接失败: {search_url}")
            return None, None, None
        except requests.Timeout:
            logger.debug(f"请求超时: {search_url}")
            return None, None, None
        except requests.HTTPError as e:
            logger.debug(f"HTTP 错误 {e.response.status_code}: {search_url}")
            return None, None, None
        except Exception as e:
            logger.debug(f"未知错误 ({type(e).__name__}): {search_url}")
            return None, None, None

    # 多阶段搜索策略
    cleaned_title = clean_title_for_search(title)
    
    search_attempts = [
        (cleaned_title, f"&release_date={year}-01-01,{year}-12-31"),
    ]
    
    # 如果标题过长，尝试使用核心标题
    words = cleaned_title.split()
    if len(words) > 3:
        core_title = " ".join(words[:3])
        search_attempts.append((core_title, f"&release_date={year}-01-01,{year}-12-31"))
    
    # 尝试不带年份过滤器
    search_attempts.append((cleaned_title, ""))
    
    # 尝试原始标题
    if cleaned_title != title:
        search_attempts.append((title, ""))
        
    # 去重
    unique_attempts = list(dict.fromkeys(search_attempts))

    for search_term, date_filter in unique_attempts:
        encoded_title = quote_plus(search_term)
        search_url = f"https://www.imdb.com/search/title/?title={encoded_title}&title_type=feature{date_filter}"
        
        rating, summary, image_url = fetch_movie_info(search_url)
        if rating:
            logger.debug(f"✅ 找到信息: '{search_term}' (日期过滤: '{date_filter}')")
            return rating, summary, image_url

    # 所有尝试均失败
    logger.debug(f"❌ 所有搜索尝试均失败: {name}")
    return None, None, None
