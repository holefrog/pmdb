import sys
import logging
from concurrent.futures import ThreadPoolExecutor
from config_reader import read_config
from deepl_service import translate_texts
from scraper import get_piratebay_top100
from movie_api_service import get_imdb_info
from html_generator import generate_html

# 配置日志系统
def setup_logging():
    """Setup logging configuration with both file and console output."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('pmdb.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    # 设置第三方库日志级别为WARNING
    logging.getLogger('urllib3').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

def get_info_for_movie(name, config):
    """Worker function to fetch IMDb info for one movie."""
    rating, summary, image_url = get_imdb_info(name, config)
    if rating and summary and image_url:
        return name, rating, summary, image_url
    else:
        return None

def main():
    try:
        setup_logging()
        logger.info("="*60)
        logger.info("PMDB - 个人电影数据库工具 启动")
        logger.info("="*60)
        
        # 1. 读取配置
        logger.info("\n[步骤 1/4] 加载配置文件...")
        config = read_config()
        
        if not config:
            logger.error("❌ 配置加载失败，程序退出")
            return
        
        deepl_api_key = config.get("deepl_api_key")
        max_workers = config.get("max_workers", 5)
        max_movies = config.get("max_movies", 100)
        batch_size = config.get("deepl_batch_size", 50)
        
        # 2. 获取电影列表
        logger.info("\n[步骤 2/4] 从 The Pirate Bay 获取电影列表...")
        movie_list = get_piratebay_top100()

        if not movie_list:
            logger.error("❌ 无法获取电影列表，程序退出")
            return
        
        # 限制电影数量
        if len(movie_list) > max_movies:
            logger.info(f"电影列表过长，仅处理前 {max_movies} 部")
            movie_list = movie_list[:max_movies]

        # 3. 并行获取 IMDb 信息
        logger.info(f"\n[步骤 3/4] 并行获取 {len(movie_list)} 部电影的 IMDb 信息（工作线程: {max_workers}）...")
        
        raw_results = []
        summaries_to_translate = []
        failed_movies = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_movie = {
                executor.submit(get_info_for_movie, name, config): name 
                for name in movie_list
            }
            
            completed = 0
            total = len(movie_list)
            
            for future in future_to_movie:
                name = future_to_movie[future]
                completed += 1
                print(f"\r正在获取 IMDb 信息: {completed}/{total} ({completed*100//total}%)", end='', flush=True)
                
                try:
                    result = future.result()
                    if result:
                        name, rating, summary, image_url = result
                        raw_results.append({
                            'name': name,
                            'rating': rating,
                            'summary_en': summary,
                            'image_url': image_url
                        })
                        summaries_to_translate.append(summary)
                    else:
                        failed_movies.append(name)
                except Exception as exc:
                    logger.error(f'\n电影 {name} 处理异常: {type(exc).__name__}')
                    failed_movies.append(name)

        print()  # 换行
        valid_movies_count = len(raw_results)
        
        if not raw_results:
            logger.error("❌ 未能从 IMDb 获取任何有效电影信息")
            return

        logger.info(f"✅ 成功获取 {valid_movies_count}/{total} 部电影信息")
        
        if failed_movies:
            logger.warning(f"\n⚠️ 以下 {len(failed_movies)} 部电影未找到信息：")
            for movie in failed_movies[:10]:  # 只显示前10个
                logger.warning(f"  - {movie}")
            if len(failed_movies) > 10:
                logger.warning(f"  ... 还有 {len(failed_movies) - 10} 部未显示")
        
        # 4. 批量翻译
        logger.info(f"\n[步骤 4/4] 使用 DeepL API 批量翻译简介...")
        chinese_summaries = translate_texts(summaries_to_translate, deepl_api_key, batch_size)
        
        if len(chinese_summaries) != valid_movies_count:
            logger.error("❌ 翻译结果数量不匹配，程序退出")
            return

        # 5. 合并结果
        logger.info("正在合并结果...")
        final_results = []
        for i in range(valid_movies_count):
            movie = raw_results[i]
            final_results.append((
                movie['name'],
                movie['rating'],
                chinese_summaries[i],
                movie['summary_en'],
                movie['image_url']
            ))

        # 6. 生成 HTML
        if final_results:
            logger.info("\n生成 HTML 文件...")
            generate_html(final_results)
            logger.info(f"\n✅ 任务完成！成功处理 {len(final_results)} 部电影")
        else:
            logger.error("❌ 没有有效结果可生成 HTML")

    except KeyboardInterrupt:
        logger.warning("\n⚠️ 用户中断程序")
    except Exception as e:
        logger.error(f"❌ 主程序错误: {type(e).__name__} - {e}", exc_info=True)

if __name__ == "__main__":
    main()
