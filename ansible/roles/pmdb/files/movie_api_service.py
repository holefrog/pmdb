import requests
import re
import time
import random
import logging
from typing import Tuple, Optional, List
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config_reader import CONFIG

# OMDb API 版本 - 替代 IMDb 网页抓取
# IMDb 已改为纯 JS 渲染，requests 直接请求只能拿到空壳 HTML
# 免费注册 OMDb Key: https://www.omdbapi.com/apikey.aspx （每天1000次，够用）

logger = logging.getLogger(__name__)

# 种子文件中常见的噪声标签（去掉后才是干净的标题）
NOISE_PATTERNS = [
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


def get_session_with_retries() -> requests.Session:
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
    """去除种子标签噪声，保留纯净标题。"""
    cleaned = title
    for pattern in NOISE_PATTERNS:
        cleaned = pattern.sub('', cleaned).strip()
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def normalize_title_variants(title: str) -> List[str]:
    """
    生成标题的多种等价变体，覆盖 BT 站常见差异：
    1. & ↔ And（双向转换）
    2. 撇号恢复（Clancys → Clancy's）
    3. 连字符处理（Spider-Man → Spider Man）
    返回去重保序列表。
    """
    variants = [title]

    # ── & ↔ And 双向 ──────────────────────────────────────────
    if ' & ' in title:
        variants.append(title.replace(' & ', ' And '))
    and_re = re.compile(r'\bAnd\b', re.IGNORECASE)
    if and_re.search(title):
        variants.append(and_re.sub('&', title))

    # ── 撇号还原：Clancys → Clancy's，Mans → Man's ──────────
    # BT 站常去掉撇号，OMDb 则保留原始拼写
    apostrophe_re = re.compile(r'\b(\w+)s\b')
    def _try_apostrophe(t: str) -> str:
        # 在最后一个 s 前插入撇号（保守处理，只生成一种变体）
        # 例: Clancys → Clancy's
        return apostrophe_re.sub(lambda m: m.group(1) + "'s", t)

    for v in list(variants):
        if 's ' in v or v.endswith('s'):
            cand = _try_apostrophe(v)
            if cand != v:
                variants.append(cand)

    # ── 连字符处理 ────────────────────────────────────────────
    for v in list(variants):
        if '-' in v:
            variants.append(v.replace('-', ' '))

    # 去重保序
    seen = set()
    unique = []
    for v in variants:
        key = v.lower()
        if key not in seen:
            seen.add(key)
            unique.append(v)
    return unique


def _build_search_queries(title: str, year: Optional[str]) -> List[Tuple[str, Optional[str]]]:
    """
    构建有序搜索策略：
    1. 完整清理标题 × 精确年份
    2. 各变体 × 精确年份
    3. 各变体 × 年份±1（OMDb 年份录入误差）
    4. 前3词短标题 × 精确年份（针对过长标题）
    5. 各变体 × 不限年份（最终兜底）
    """
    cleaned = clean_title_for_search(title)
    all_variants = normalize_title_variants(cleaned)

    queries: List[Tuple[str, Optional[str]]] = []

    # 精确年份
    for v in all_variants:
        queries.append((v, year))

    # 年份 ±1
    if year and year.isdigit():
        y = int(year)
        for v in all_variants:
            queries.append((v, str(y - 1)))
            queries.append((v, str(y + 1)))

    # 前3词（针对过长标题）
    words = cleaned.split()
    if len(words) > 3:
        short = " ".join(words[:3])
        queries.append((short, year))
        if year and year.isdigit():
            queries.append((short, str(int(year) - 1)))
            queries.append((short, str(int(year) + 1)))

    # 无年份兜底
    for v in all_variants:
        queries.append((v, None))

    # 去重保序
    seen = set()
    unique = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            unique.append(q)
    return unique


def _get_ai_imdb_id(
    name: str,
    session: requests.Session,
    timeout: int
) -> Optional[str]:
    """使用配置的 AI 服务推理 IMDb ID（AI 兜底查询）。"""
    # AI 兜底固定用 Mistral（最稳定，有 JSON mode）
    api_key = CONFIG["mistral_api_key"]
    if not api_key:
        return None

    model = CONFIG["imdb_lookup_model"]
    endpoint = CONFIG["mistral_endpoint"]
    prompt = (
        f"Find the official IMDb ID for the movie currently titled '{name}'. "
        "Note: This title might contain extra franchise names, incorrect release years, "
        "or be a working title from a torrent release. "
        "Please infer the correct official movie and return its exact IMDb ID. "
        "Reply ONLY with the IMDb ID (starting with 'tt' followed by numbers). "
        "Do not output any other text, explanation, or punctuation. "
        "If you don't know, reply with 'UNKNOWN'."
    )
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
    }
    try:
        resp = session.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=timeout
        )
        resp.raise_for_status()
        content = resp.json()['choices'][0]['message']['content'].strip()
        logger.info(f"🤖 AI 兜底 '{name}' → {content}")
        match = re.search(r'tt\d{7,10}', content)
        return match.group(0) if match else None
    except Exception as e:
        logger.debug(f"AI 兜底失败: {e}")
        return None


def _fetch_omdb_by_id(
    imdb_id: str,
    omdb_api_key: str,
    session: requests.Session,
    timeout: int,
    delay: float = 0
) -> Optional[dict]:
    """通过 IMDb ID 向 OMDb 获取详情。"""
    if delay:
        time.sleep(delay)
    resp = session.get(
        "https://www.omdbapi.com/",
        params={"apikey": omdb_api_key, "i": imdb_id, "plot": "full"},
        timeout=timeout
    )
    resp.raise_for_status()
    data = resp.json()
    return data if data.get("Response") == "True" else None


def _extract_result(data: dict) -> Tuple[str, str, str]:
    """从 OMDb 响应中提取 (rating, summary, image_url)。"""
    rating = data.get("imdbRating", "N/A")
    summary = data.get("Plot", "No summary available.")
    image_url = data.get("Poster", "")
    if not image_url or image_url == "N/A":
        image_url = "https://placehold.co/150x220?text=No+Poster"
    return rating, summary, image_url


def get_imdb_info(
    name: str,
    config: dict
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    使用 OMDb API 获取电影信息，四阶段搜索策略：
    1. 精确 title+year 搜索（多变体 × 年份±1）
    2. 模糊搜索（OMDb ?s= 接口）取第一个匹配
    3. AI 推理 IMDb ID（Mistral 兜底）
    4. 全部失败返回 None

    Args:
        name: "Title Year" 格式
        config: read_config() 返回的字典

    Returns:
        (rating, summary, image_url) 或 (None, None, None)
    """
    omdb_api_key = config.get("omdb_api_key")
    if not omdb_api_key:
        logger.error("❌ 未找到 OMDb API 密钥")
        return None, None, None

    # 拆分 "Title Year"
    parts = name.rsplit(" ", 1)
    title = parts[0]
    year = parts[1] if len(parts) > 1 and parts[1].isdigit() else None

    if not year:
        logger.warning(f"跳过 '{name}' - 缺少年份")
        return None, None, None

    session = get_session_with_retries()
    timeout = config["request_timeout"]
    delay_min = config["retry_delay_min"]
    delay_max = config["retry_delay_max"]

    def _delay() -> float:
        d = random.uniform(delay_min, delay_max)
        time.sleep(d)
        return d

    # ── 阶段 1：精确搜索（t=, y=）────────────────────────────
    queries = _build_search_queries(title, year)
    for search_title, search_year in queries:
        params = {
            "apikey": omdb_api_key,
            "t": search_title,
            "type": "movie",
            "plot": "full",
        }
        if search_year:
            params["y"] = search_year
        try:
            _delay()
            resp = session.get("https://www.omdbapi.com/", params=params, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            if data.get("Response") == "True":
                rating, summary, image_url = _extract_result(data)
                if rating == "N/A" and summary == "No summary available.":
                    logger.debug(f"找到但数据为空: '{search_title}' (y={search_year})")
                    continue
                logger.debug(f"✅ 精确命中: '{search_title}' (y={search_year})")
                return rating, summary, image_url
            else:
                logger.debug(f"OMDb 未命中: '{search_title}' (y={search_year}) → {data.get('Error')}")
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as e:
            logger.debug(f"网络错误 [{name}]: {e}")
            return None, None, None
        except Exception as e:
            logger.debug(f"未知错误 [{name}]: {e}")
            return None, None, None

    # ── 阶段 2：模糊搜索（s=）────────────────────────────────
    cleaned = clean_title_for_search(title)
    for fuzzy_title in normalize_title_variants(cleaned):
        logger.debug(f"🔍 模糊搜索: '{fuzzy_title}'")
        try:
            _delay()
            resp = session.get(
                "https://www.omdbapi.com/",
                params={"apikey": omdb_api_key, "s": fuzzy_title, "type": "movie"},
                timeout=timeout
            )
            resp.raise_for_status()
            search_data = resp.json()
            if search_data.get("Response") == "True" and search_data.get("Search"):
                imdb_id = search_data["Search"][0].get("imdbID")
                if imdb_id:
                    data = _fetch_omdb_by_id(imdb_id, omdb_api_key, session, timeout, _delay())
                    if data:
                        rating, summary, image_url = _extract_result(data)
                        logger.debug(f"✅ 模糊命中: '{fuzzy_title}' → {imdb_id}")
                        return rating, summary, image_url
        except Exception as e:
            logger.debug(f"模糊搜索异常: {e}")
            continue

    # ── 阶段 3：AI 推理兜底 ───────────────────────────────────
    logger.debug(f"🤖 所有搜索失败，尝试 AI 兜底: '{name}'")
    imdb_id = _get_ai_imdb_id(name, config, session, timeout)
    if imdb_id:
        try:
            data = _fetch_omdb_by_id(imdb_id, omdb_api_key, session, timeout, _delay())
            if data:
                rating, summary, image_url = _extract_result(data)
                logger.debug(f"✅ AI 兜底命中: '{name}' → {imdb_id}")
                return rating, summary, image_url
        except Exception as e:
            logger.debug(f"AI 兜底 OMDb 验证异常: {e}")

    logger.debug(f"❌ 所有搜索均失败: {name}")
    return None, None, None
