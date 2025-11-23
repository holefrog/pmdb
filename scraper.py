from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re
import time

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
    """Fetch and deduplicate movie names from The Pirate Bay using Selenium."""
    url = "https://thepiratebay.org/search.php?q=top100:207"
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(url)
        time.sleep(3)
        html = driver.page_source
        driver.quit()
    except Exception as e:
        print(f"❌ Failed to request The Pirate Bay: {e}")
        return []

    soup = BeautifulSoup(html, "html.parser")
    raw_names = set()

    list_items = soup.select("li.list-entry")
    print(f"Found {len(list_items)} entries")

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
    print(f"After deduplication, {len(unique_names)} movies remain")
    return unique_names
