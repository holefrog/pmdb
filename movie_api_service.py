import requests
import re
import time
import random
import logging
from typing import Tuple, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# OMDb API 版本 - 替代 IMDb 网页抓取
# IMDb 已改为纯 JS 渲染，requests 直接请求只能拿到空壳 HTML（202状态码，0个元素）
# 免费注册 OMDb Key: https://www.omdbapi.com/apikey.aspx （每天1000次，够用）

logger = logging.getLogger(__name__)

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
    re.compile(r'\{Extended\}', re.IGNORECASE),
]

def get_session_with_retries():
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    return session

def clean_title_for_search(title: str) -> str:
    cleaned = title
    for pattern in COMPILED_PATTERNS:
        cleaned = pattern.sub('', cleaned).strip()
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def get_imdb_info(name: str, config: dict) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    使用 OMDb API 获取电影信息（替代 IMDb 网页抓取）。

    Args:
        name: 格式为 "Title Year" 的电影名
        config: 含 omdb_api_key 等配置的字典

    Returns:
        (rating, summary, image_url) 或 (None, None, None)
    """
    omdb_api_key = config.get("omdb_api_key")
    if not omdb_api_key:
        logger.error("❌ 未找到 OMDb API 密钥，请在 config.ini 的 [OMDb_API] 下填写 OMDB_KEY")
        return None, None, None

    parts = name.rsplit(" ", 1)
    title = parts[0]
    year = parts[1] if len(parts) > 1 and parts[1].isdigit() else None

    if not year:
        logger.warning(f"跳过 '{name}' - 缺少年份")
        return None, None, None

    cleaned_title = clean_title_for_search(title)
    session = get_session_with_retries()
    timeout = config.get("request_timeout", 10)

    # 多阶段搜索：完整清理标题 → 前3个词 → 原始标题
    search_attempts = [cleaned_title]
    words = cleaned_title.split()
    if len(words) > 3:
        search_attempts.append(" ".join(words[:3]))
    if cleaned_title != title:
        search_attempts.append(title)

    seen = set()
    unique_titles = [t for t in search_attempts if not (t in seen or seen.add(t))]

    search_queries = []
    # 1. 精确年份
    for t in unique_titles:
        search_queries.append((t, year))
    # 2. 年份 ± 1 (应对不同数据库的年份误差)
    if year and year.isdigit():
        y_int = int(year)
        for t in unique_titles:
            search_queries.append((t, str(y_int - 1)))
            search_queries.append((t, str(y_int + 1)))
    # 3. 不限制年份 (最后兜底)
    for t in unique_titles:
        search_queries.append((t, None))

    for search_title, search_year in search_queries:
        params = {
            "apikey": omdb_api_key,
            "t":      search_title,
            "type":   "movie",
            "plot":   "full",
        }
        if search_year:
            params["y"] = search_year

        try:
            delay = random.uniform(
                config.get("retry_delay_min", 0.2),
                config.get("retry_delay_max", 0.5)
            )
            time.sleep(delay)

            resp = session.get("https://www.omdbapi.com/", params=params, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()

            if data.get("Response") == "True":
                rating    = data.get("imdbRating", "N/A")
                summary   = data.get("Plot", "No summary available.")
                image_url = data.get("Poster", "")

                if not image_url or image_url == "N/A":
                    image_url = "https://placehold.co/150x220?text=No+Poster"

                if rating == "N/A" and summary == "No summary available.":
                    logger.debug(f"找到但数据为空: '{search_title}' (y={search_year})")
                    continue

                logger.debug(f"✅ OMDb 命中: '{search_title}' (y={search_year}) → 评分={rating}")
                return rating, summary, image_url
            else:
                logger.debug(f"OMDb 未找到: '{search_title}' (y={search_year}) → {data.get('Error')}")

        except requests.ConnectionError:
            logger.debug(f"网络连接失败 [{name}]")
            return None, None, None
        except requests.Timeout:
            logger.debug(f"请求超时 [{name}]")
            return None, None, None
        except requests.HTTPError as e:
            logger.debug(f"HTTP 错误 {e.response.status_code} [{name}]")
            return None, None, None
        except Exception as e:
            logger.debug(f"未知错误 ({type(e).__name__}) [{name}]: {e}")
            return None, None, None

    logger.debug(f"❌ 所有搜索均失败: {name}")
    return None, None, None
