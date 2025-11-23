import sys
from concurrent.futures import ThreadPoolExecutor
# 导入拆分后的功能模块
from config_reader import read_config
from deepl_service import translate_texts # <-- 导入新的批量翻译函数
from scraper import get_piratebay_top100
from movie_api_service import get_imdb_info
from html_generator import generate_html

# 为了提高 IMDb 查询速度，使用并行处理
def get_info_for_movie(name):
    """Worker function to fetch IMDb info for one movie."""
    # 获取 IMDb 信息
    rating, summary, image_url = get_imdb_info(name)
    if rating and summary and image_url:
        return name, rating, summary, image_url
    else:
        # 在多线程环境中，最好将日志输出放在主线程，但为了调试，这里保留
        print(f"\nSkipping invalid movie (IMDb info missing): {name}")
        return None

def main():
    try:
        print("Starting program, fetching movie list from The Pirate Bay...")
        
        # 1. 获取电影列表 (包含排序和去重)
        movie_list = get_piratebay_top100()

        if not movie_list:
            print("❌ Unable to fetch movie list, exiting")
            return

        max_movies = len(movie_list)
        
        # 2. 读取配置
        config = read_config()
        
        if not config:
            return
            
        deepl_api_key = config.get("deepl_api_key")

        # --- Stage 1: 并行获取 IMDb 信息并收集英文简介 ---
        print(f"\nStage 1: Starting parallel fetching of IMDb info for {max_movies} movies (max_workers=5)...")
        
        raw_results = []
        summaries_to_translate = []
        valid_movies_count = 0
        
        # 使用并行线程池加速网络I/O密集型任务 (IMDb查询)
        with ThreadPoolExecutor(max_workers=5) as executor:
            # 提交任务
            future_to_movie = {executor.submit(get_info_for_movie, name): name for name in movie_list[:max_movies]}
            
            # 处理结果
            for idx, future in enumerate(future_to_movie):
                name = future_to_movie[future]
                print(f"Fetching IMDb info progress: {idx + 1}/{max_movies}", end='\r')
                try:
                    result = future.result()
                    if result:
                        name, rating, summary, image_url = result
                        # 存储所有必要信息，等待批量翻译
                        raw_results.append({
                            'name': name,
                            'rating': rating,
                            'summary_en': summary,
                            'image_url': image_url
                        })
                        summaries_to_translate.append(summary)
                        valid_movies_count += 1
                except Exception as exc:
                    print(f'\nMovie {name} generated an exception during IMDb fetch: {exc}')

        if not raw_results:
            print("\n❌ No valid movie information was fetched from IMDb.")
            return

        print(f"\n✅ Stage 1 complete. Successfully fetched info for {valid_movies_count}/{max_movies} movies.")
        
        # --- Stage 2: 批量翻译英文简介 ---
        print("\nStage 2: Starting batch translation using DeepL API...")
        
        chinese_summaries = translate_texts(summaries_to_translate, deepl_api_key)
        
        if len(chinese_summaries) != valid_movies_count:
            print("❌ Translation result count mismatch. Exiting.")
            return

        print("✅ Stage 2 complete. Merging results.")
        
        # --- Stage 3: 合并结果并生成输出 ---
        final_results = []
        for i in range(valid_movies_count):
            movie = raw_results[i]
            # 最终格式: (name, rating, summary_cn, summary_en, image_url)
            final_results.append((
                movie['name'],
                movie['rating'],
                chinese_summaries[i], # 批量翻译结果
                movie['summary_en'],
                movie['image_url']
            ))

        # 4. 生成输出
        if final_results:
            generate_html(final_results)
        else:
            print("❌ No valid results to generate HTML")

    except Exception as e:
        print(f"❌ Main program error: {e}")

if __name__ == "__main__":
    main()
