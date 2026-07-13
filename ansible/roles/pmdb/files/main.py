import sys
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from config_reader import read_config
from translate_service import translate_texts   # 替代旧 mistral_service
from scraper import get_top100_with_fallback
from movie_api_service import get_imdb_info
from html_generator import generate_html


def setup_logging():
    """配置日志：同时输出到文件和控制台。"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('pmdb.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logging.getLogger('urllib3').setLevel(logging.WARNING)


logger = logging.getLogger(__name__)


def _fetch_movie(name: str, config: dict):
    """线程工作函数：获取单部电影的 IMDb 信息。"""
    rating, summary, image_url = get_imdb_info(name, config)
    if rating and summary and image_url:
        return name, rating, summary, image_url
    return None


def main():
    try:
        setup_logging()
        logger.info("=" * 60)
        logger.info("PMDB - 个人电影数据库工具 启动")
        logger.info("=" * 60)

        # ── 步骤 1：读取配置 ─────────────────────────────────────
        logger.info("\n[步骤 1/4] 加载配置文件...")
        config = read_config()
        if not config:
            logger.error("❌ 配置加载失败，程序退出")
            return

        max_workers  = config.get("max_workers", 5)
        max_movies   = config.get("max_movies", 100)
        batch_size   = config.get("mistral_batch_size", 10)
        provider     = config.get("translate_provider", "mistral")

        # ── 步骤 2：获取电影列表 ─────────────────────────────────
        logger.info("\n[步骤 2/4] 从 BT 站获取电影列表（支持多源 Fallback）...")
        movie_list = get_top100_with_fallback(config)

        if not movie_list:
            logger.error("❌ 无法获取电影列表，程序退出")
            return

        if len(movie_list) > max_movies:
            logger.info(f"电影列表过长，仅处理前 {max_movies} 部")
            movie_list = movie_list[:max_movies]

        total = len(movie_list)

        # ── 步骤 3：并行获取 IMDb 信息 ───────────────────────────
        logger.info(f"\n[步骤 3/4] 并行获取 {total} 部电影的 OMDb 信息（线程数: {max_workers}）...")

        results_ordered = [None] * total
        failed_movies = []
        completed = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {
                executor.submit(_fetch_movie, name, config): (i, name)
                for i, name in enumerate(movie_list)
            }
            for future in as_completed(future_to_idx):
                i, name = future_to_idx[future]
                completed += 1
                print(
                    f"\r正在获取 OMDb 信息: {completed}/{total} "
                    f"({completed * 100 // total}%)",
                    end='', flush=True
                )
                try:
                    result = future.result()
                    if result:
                        _, rating, summary, image_url = result
                        results_ordered[i] = {
                            'name': name,
                            'rating': rating,
                            'summary_en': summary,
                            'image_url': image_url,
                        }
                    else:
                        failed_movies.append(name)
                except Exception as exc:
                    logger.error(f'\n电影 {name} 处理异常: {type(exc).__name__}')
                    failed_movies.append(name)

        print()  # 换行

        raw_results = [r for r in results_ordered if r is not None]
        valid_count = len(raw_results)

        if not raw_results:
            logger.error("❌ 未能获取任何有效电影信息")
            return

        logger.info(f"✅ 成功获取 {valid_count}/{total} 部电影信息")
        if failed_movies:
            logger.warning(f"\n⚠️ 以下 {len(failed_movies)} 部电影未找到信息：")
            for movie in failed_movies[:10]:
                logger.warning(f"  - {movie}")
            if len(failed_movies) > 10:
                logger.warning(f"  ... 还有 {len(failed_movies) - 10} 部未显示")

        # ── 步骤 4：批量翻译 ─────────────────────────────────────
        logger.info(f"\n[步骤 4/4] 使用 {provider} 批量翻译简介...")
        summaries_en = [r['summary_en'] for r in raw_results]
        chinese_summaries = translate_texts(summaries_en, config, batch_size)

        if len(chinese_summaries) != valid_count:
            logger.error("❌ 翻译结果数量不匹配，程序退出")
            return

        # ── 合并结果并生成 HTML ──────────────────────────────────
        logger.info("正在合并结果并生成 HTML...")
        final_results = [
            (
                raw_results[i]['name'],
                raw_results[i]['rating'],
                chinese_summaries[i],
                raw_results[i]['summary_en'],
                raw_results[i]['image_url'],
            )
            for i in range(valid_count)
        ]

        if final_results:
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
