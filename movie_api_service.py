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

def _get_imdb_id_from_ai(name: str, mistral_api_key: str, session: requests.Session, timeout: int) -> Optional[str]:
    """使用大语言模型智能推理并获取电影的 IMDb ID"""
    try:
        headers = {
            "Authorization": f"Bearer {mistral_api_key}",
            "Content-Type": "application/json"
        }
        prompt = (
            f"What is the IMDb ID for the movie '{name}'? "
            "Please reply ONLY with the exact IMDb ID (which starts with 'tt' followed by numbers). "
            "Do not output any other text, explanation or punctuation. "
            "If you don't know, reply with 'UNKNOWN'."
        )
        payload = {
            "model": "mistral-small-latest",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1
        }
        resp = session.post("https://api.mistral.ai/v1/chat/completions", headers=headers, json=payload, timeout=timeout)
        resp.raise_for_status()
        content = resp.json()['choices'][0]['message']['content'].strip()
        
        # 打印 AI 的原始回复，方便调试
        logger.info(f"🤖 AI 对 '{name}' 的原始回复内容: {content}")

        # 使用正则提取出以 tt 开头加纯数字的标准的 IMDb ID
        match = re.search(r'tt\d{7,10}', content)
        if match:
            return match.group(0)
    except Exception as e:
        logger.debug(f"AI 获取 IMDb ID 失败: {e}")
    return None

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

    # ==========================================
    # 4. 模糊搜索兜底 (Fuzzy Search Fallback)
    # 应对 BT 种子去掉标点符号（如 Tom Clancys 缺撇号）或添加系列名前缀的情况
    # ==========================================
    for fuzzy_title in unique_titles:
        logger.debug(f"🎯 精确匹配均失败，尝试模糊搜索: '{fuzzy_title}'...")
        try:
            delay = random.uniform(
                config.get("retry_delay_min", 0.2),
                config.get("retry_delay_max", 0.5)
            )
            time.sleep(delay)
            
            search_params = {
                "apikey": omdb_api_key,
                "s":      fuzzy_title,
                "type":   "movie"
            }
            resp = session.get("https://www.omdbapi.com/", params=search_params, timeout=timeout)
            resp.raise_for_status()
            search_data = resp.json()
            
            if search_data.get("Response") == "True" and search_data.get("Search"):
                # 获取最匹配的第一个结果的 imdbID
                first_match = search_data["Search"][0]
                imdb_id = first_match.get("imdbID")
                
                if imdb_id:
                    time.sleep(delay)
                    detail_params = {
                        "apikey": omdb_api_key,
                        "i":      imdb_id,
                        "plot":   "full"
                    }
                    detail_resp = session.get("https://www.omdbapi.com/", params=detail_params, timeout=timeout)
                    detail_resp.raise_for_status()
                    detail_data = detail_resp.json()
                    
                    if detail_data.get("Response") == "True":
                        rating    = detail_data.get("imdbRating", "N/A")
                        summary   = detail_data.get("Plot", "No summary available.")
                        image_url = detail_data.get("Poster", "")

                        if not image_url or image_url == "N/A":
                            image_url = "https://placehold.co/150x220?text=No+Poster"

                        logger.debug(f"✅ 模糊搜索最终命中: '{fuzzy_title}' -> ID: {imdb_id}, 评分={rating}")
                        return rating, summary, image_url
        except Exception as e:
            logger.debug(f"模糊搜索发生异常: {e}")
            continue

    # ==========================================
    # 5. AI 兜底 (LLM Fallback)
    # 遇到搜索死角，求助大模型直接返回 IMDb ID 再请求
    # ==========================================
    mistral_api_key = config.get("mistral_api_key")
    if mistral_api_key:
        logger.debug(f"🤖 常规搜索均失败，尝试使用 AI 推理 '{name}' 的 IMDb ID...")
        imdb_id = _get_imdb_id_from_ai(name, mistral_api_key, session, timeout)
        
        if imdb_id:
            logger.debug(f"🧠 AI 推理出了 ID: {imdb_id}，正在向 OMDb 验证...")
            try:
                time.sleep(random.uniform(
                    config.get("retry_delay_min", 0.2),
                    config.get("retry_delay_max", 0.5)
                ))
                detail_params = {
                    "apikey": omdb_api_key,
                    "i":      imdb_id,
                    "plot":   "full"
                }
                detail_resp = session.get("https://www.omdbapi.com/", params=detail_params, timeout=timeout)
                detail_resp.raise_for_status()
                detail_data = detail_resp.json()
                
                if detail_data.get("Response") == "True":
                    rating    = detail_data.get("imdbRating", "N/A")
                    summary   = detail_data.get("Plot", "No summary available.")
                    image_url = detail_data.get("Poster", "")

                    if not image_url or image_url == "N/A":
                        image_url = "https://placehold.co/150x220?text=No+Poster"

                    logger.debug(f"✅ AI 兜底完美命中: '{name}' -> ID: {imdb_id}, 评分={rating}")
                    return rating, summary, image_url
            except Exception as e:
                logger.debug(f"AI 兜底 OMDb 验证异常: {e}")

    logger.debug(f"❌ 所有搜索均失败: {name}")
    return None, None, None
