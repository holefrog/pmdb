import sys
import logging
from config_reader import CONFIG
from translate_service import translate_texts
from scraper import get_top100_with_fallback
from movie_api_service import fetch_imdb_info_batch
from html_generator import generate_html


def dedup_by_imdb_id(results: list) -> list:
    """
    按 imdbID 对 OMDb 命中的电影进行二次去重。
    - 同一 imdbID 的多条记录 → 保留 rating 不为 N/A 的那条，都有评分则保留先到的。
    - imdb_id 为 None 的（OMDb 未命中）→ 不参与去重，直接保留。
    """
    seen_ids: dict = {}
    unique: list = []
    for r in results:
        iid = r.get('imdb_id')
        if not iid:
            unique.append(r)  # 未命中的保留原样
            continue
        if iid not in seen_ids:
            seen_ids[iid] = len(unique)
            unique.append(r)
        else:
            # 已有相同 ID：尝试用数据更完整的替换
            existing_idx = seen_ids[iid]
            existing = unique[existing_idx]
            if existing['rating'] == 'N/A' and r['rating'] != 'N/A':
                unique[existing_idx] = r
    return unique


def setup_logging():
    """配置日志：同时输出到文件和控制台。"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('pmdb.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logging.getLogger('urllib3').setLevel(logging.WARNING)


logger = logging.getLogger(__name__)


def main():
    try:
        setup_logging()
        logger.info("=" * 60)
        logger.info("PMDB - 个人电影数据库工具 启动")
        logger.info("=" * 60)

        # ── 步骤 1：读取配置（在 import 时已完成校验） ─────────────
        logger.info("\n[步骤 1/4] 加载配置文件 (已通过模块自动加载并校验)...")
        max_movies = CONFIG["max_movies"]
        batch_size = CONFIG["mistral_batch_size"]
        provider   = CONFIG["translate_provider"]

        # ── 步骤 2：获取电影列表 ─────────────────────────────────
        logger.info("\n[步骤 2/4] 从 BT 站获取电影列表（支持多源 Fallback）...")
        movie_list = get_top100_with_fallback()

        if not movie_list:
            logger.error("❌ 无法获取电影列表，程序退出")
            return

        if len(movie_list) > max_movies:
            logger.info(f"电影列表过长，仅处理前 {max_movies} 部")
            movie_list = movie_list[:max_movies]

        # ── 步骤 3：并行获取 IMDb 信息 ───────────────────────────
        logger.info(f"\n[步骤 3/4] 开始并行获取 {len(movie_list)} 部电影的 OMDb 信息...")
        
        raw_results, failed_movies = fetch_imdb_info_batch(movie_list)

        if not raw_results:
            logger.error("❌ 未能获取任何有效电影信息")
            return

        logger.info(f"✅ 成功获取 {len(raw_results)}/{len(movie_list)} 部电影信息")

        if failed_movies:
            logger.warning(f"\n⚠️ 以下 {len(failed_movies)} 部电影未找到满足条件的信息：")
            for movie_reason in failed_movies:
                logger.warning(f"  - {movie_reason}")

        # ── IMDb ID 二次去重（合并同一部电影的不同 BT 站条目）────
        before_dedup = len(raw_results)
        raw_results = dedup_by_imdb_id(raw_results)
        valid_count = len(raw_results)
        if valid_count < before_dedup:
            logger.info(f"🔁 IMDb ID 去重：{before_dedup} → {valid_count} 部（合并了 {before_dedup - valid_count} 条重复）")

        # ── 步骤 4：批量翻译 ─────────────────────────────────────
        logger.info(f"\n[步骤 4/4] 使用 {provider} 批量翻译简介...")
        summaries_en = [r['summary_en'] for r in raw_results]
        chinese_summaries = translate_texts(summaries_en, batch_size)

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
