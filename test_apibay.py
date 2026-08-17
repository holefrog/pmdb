import requests
import json
import re

def extract_title_year(name: str):
    name = re.sub(r'\.', ' ', name)
    noise = re.compile(
        r'\b(EXTENDED|REPACK|THEATRICAL|UNCUT|4K|HDR|IMAX|WEB-DL|BLURAY|'
        r'1080p|720p|2160p|x264|x265|HEVC|AAC|DTS|BluRay|BRRip|DVDRip|'
        r'WEBRip|HDTV|NF|AMZN|DSNP|HULU|'
        r'TELESYNC|HDRip|DCPRIP|DCPRiP|iNTERNAL)\b.*$',
        re.IGNORECASE
    )
    name = noise.sub('', name).strip()
    pattern = r'^(.*?)(?:\s*\((\d{4})\)|\s+(\d{4})(?=\s|$))'
    match = re.search(pattern, name)
    if match:
        title = match.group(1).strip()
        year = match.group(2) or match.group(3)
        return title, year
    else:
        clean = re.sub(r'\[.*?\]|\..*$', '', name).strip()
        return clean, None

url = "https://apibay.org/precompiled/data_top100_207.json"
try:
    resp = requests.get(url, timeout=10)
    data = resp.json()
    print(f"✅ 成功连接 API，获取到 {len(data)} 条数据。\n")
    print("前 15 条解析结果测试：")
    print("-" * 50)
    for i, item in enumerate(data[:15]):
        raw_name = item.get("name", "")
        seeders = item.get("seeders", 0)
        imdb = item.get("imdb", "N/A")
        
        title, year = extract_title_year(raw_name)
        
        print(f"[{i+1}] 原始名字: {raw_name}")
        print(f"    解析结果: 标题='{title}', 年份='{year}'")
        print(f"    做种数: {seeders} | IMDb ID: {imdb}\n")
        
except Exception as e:
    print(f"测试失败: {e}")
