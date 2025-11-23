import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import re
import time
from typing import Tuple, Optional

# --- 新增辅助函数：清理标题 ---
def clean_title_for_search(title: str) -> str:
    """Strips common torrent/edition tags (e.g., EXTENDED, 4K) that interfere with official IMDb search."""
    # 常用标签列表（不区分大小写）
    tags_to_strip = [
        r'\bEXTENDED\b', r'\bREPACK\b', r'\bTHEATRICAL\b', r'\bUNCUT\b', 
        r'\b4K\b', r'\bHDR\b', r'\bIMAX\b', r'\bWEB-DL\b', r'\bBLURAY\b', 
        r'\{Extended\}'
    ]
    
    cleaned_title = title
    for tag in tags_to_strip:
        cleaned_title = re.sub(tag, '', cleaned_title, flags=re.IGNORECASE).strip()
    
    # 移除多余空格
    cleaned_title = re.sub(r'\s+', ' ', cleaned_title).strip()
    return cleaned_title
# -----------------------------

def get_imdb_info(name: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Query IMDb with enhanced fuzzy search and date-filter fallback (Web Scraping)."""
    
    # Title extraction from unique_movies format (e.g., "Deadpool and Wolverine 2024")
    parts = name.rsplit(" ", 1)
    title = parts[0]
    year = parts[1] if len(parts) > 1 and parts[1].isdigit() else None

    if not year:
        print(f"Skipping IMDb search for '{name}' - missing year.")
        return None, None, None

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }

    def fetch_movie_info(search_url):
        # 封装请求逻辑，用于多轮尝试
        try:
            # 增加一个短暂的等待，避免过于频繁的请求导致IP被封锁
            time.sleep(0.5) 
            response = requests.get(search_url, headers=headers, timeout=10)
            if response.status_code != 200:
                # 仅在获取失败时打印错误，不视为致命错误
                # print(f"❌ IMDb search request failed, status code: {response.status_code}, URL: {search_url}")
                return None, None, None

            soup = BeautifulSoup(response.text, "html.parser")
            # 尝试获取第一个搜索结果
            result = soup.select_one("li.ipc-metadata-list-summary-item")
            if not result:
                # print(f"❌ No search results found, URL: {search_url}")
                return None, None, None

            # 提取电影详情页URL
            link = result.find("a", class_="ipc-title-link-wrapper")
            if not link or 'href' not in link.attrs:
                return None, None, None

            movie_url = "https://www.imdb.com" + link['href'].split('?')[0]
            
            # 访问电影详情页
            time.sleep(0.5)
            movie_response = requests.get(movie_url, headers=headers, timeout=10)
            if movie_response.status_code != 200:
                # print(f"❌ Movie page request failed, status code: {movie_response.status_code}, URL: {movie_url}")
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
                # print(f"❌ No rating or summary found, URL: {movie_url}")
                return None, None, None

            return rating, summary, image_url

        except Exception as e:
            # print(f"❌ Error querying IMDb: {e}, URL: {search_url}")
            return None, None, None

    # --- 搜索策略：多阶段回退 ---
    cleaned_title = clean_title_for_search(title)
    
    # 定义搜索尝试列表: (搜索词, 日期过滤器)
    # 日期过滤器可以是 "&release_date={year}-01-01,{year}-12-31" 或 ""
    
    # 1. 尝试使用**清理后的标题**和**严格的年份过滤器** (最精确)
    search_attempts = [
        (cleaned_title, f"&release_date={year}-01-01,{year}-12-31"),
    ]
    
    # 2. 如果清理后的标题长度大于3个词，尝试使用**核心标题**和**严格的年份过滤器** (解决长标题问题)
    words = cleaned_title.split()
    if len(words) > 3:
        core_title = " ".join(words[:3])
        search_attempts.append((core_title, f"&release_date={year}-01-01,{year}-12-31"))
    
    # 3. 尝试使用**清理后的标题**和**不带年份过滤器** (解决上映日期不确定问题)
    search_attempts.append((cleaned_title, ""))
    
    # 4. 尝试使用**原始标题**和**不带年份过滤器** (最后的宽松回退)
    if cleaned_title != title:
        search_attempts.append((title, ""))
        
    # 去重
    unique_attempts = list(dict.fromkeys(search_attempts))

    for search_term, date_filter in unique_attempts:
        encoded_title = quote_plus(search_term)
        search_url = f"https://www.imdb.com/search/title/?title={encoded_title}&title_type=feature{date_filter}"
        
        rating, summary, image_url = fetch_movie_info(search_url)
        if rating:
            print(f"✅ Found info using search term: '{search_term}' and date filter: '{date_filter}'")
            return rating, summary, image_url
        
        # 如果搜索失败，打印失败的尝试，以便调试
        print(f"❌ No search results found for attempt: '{search_term}' with date filter: '{date_filter}'")


    # 所有尝试均失败
    return None, None, None
