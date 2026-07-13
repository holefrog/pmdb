import configparser
import os
import sys
import logging

logger = logging.getLogger(__name__)

def read_config(config_file: str = "config.ini") -> dict:
    """
    读取 config.ini（由 Ansible 从 ansible/secrets.yml + config.ini.j2 生成）并返回配置字典。
    禁止使用任何 fallback。如果有配置缺失，直接抛出错误并退出程序。
    """
    config = configparser.ConfigParser()
    result = {}

    if not os.path.exists(config_file):
        logger.error(f"❌ 配置文件 '{config_file}' 不存在。请先运行部署脚本生成配置。")
        sys.exit(1)

    try:
        config.read(config_file, encoding='utf-8')

        # ── [AI] section ─────────────────────────────────────────────────────
        if "AI" not in config:
            logger.error("❌ 配置文件中缺少 [AI] 部分")
            sys.exit(1)

        ai = config["AI"]

        provider = ai.get("translate_provider", "").strip()
        if not provider:
            logger.error("❌ 未配置 translate_provider")
            sys.exit(1)
        result['translate_provider'] = provider

        # 检查所有模型和端点配置
        for key in [
            'mistral_api_key', 'openai_api_key', 'groq_api_key', 'nvidia_api_key', 'gemini_api_key',
            'mistral_translate_model', 'openai_translate_model', 'groq_translate_model', 'nvidia_translate_model', 'gemini_translate_model',
            'mistral_endpoint', 'openai_endpoint', 'groq_endpoint', 'nvidia_endpoint', 'gemini_endpoint',
            'imdb_lookup_model'
        ]:
            val = ai.get(key, "").strip().strip('"\'')
            # 只有当前激活的 provider 必须提供模型和端点配置，其它如果没填可以不管（但API_KEY是单独校验的）
            if not val and key.startswith(f"{provider}_") and "api_key" not in key:
                logger.error(f"❌ 缺少必填 AI 配置项: {key}")
                sys.exit(1)
            result[key] = val

        if not result.get('imdb_lookup_model'):
            logger.error("❌ 未配置 imdb_lookup_model")
            sys.exit(1)

        # 验证当前选择的提供商有可用密钥
        active_key_field = f"{provider}_api_key"
        active_key = result.get(active_key_field, "")
        if not active_key or active_key.startswith("<YOUR_"):
            logger.error(
                f"❌ 翻译提供商 '{provider}' 的 API 密钥无效或未填写 ({active_key_field})"
            )
            sys.exit(1)
        
        logger.info(f"✅ 翻译提供商: {provider}，密钥与端点已加载")

        # ── [OMDb_API] section ───────────────────────────────────────────────
        if "OMDb_API" not in config:
            logger.error("❌ 配置文件中缺少 [OMDb_API] 部分")
            sys.exit(1)

        omdb_key = config["OMDb_API"].get("OMDB_KEY", "").strip()
        if not omdb_key or omdb_key.startswith("<YOUR_"):
            logger.error("❌ OMDb API 密钥无效或未填写 (OMDB_KEY)")
            sys.exit(1)
        result['omdb_api_key'] = omdb_key
        logger.info("✅ OMDb API 密钥已加载")

        # ── [Settings] section ───────────────────────────────────────────────
        if "Settings" not in config:
            logger.error("❌ 配置文件中缺少 [Settings] 部分")
            sys.exit(1)
        
        settings = config["Settings"]
        try:
            result['max_workers']        = settings.getint("max_workers")
            result['max_movies']         = settings.getint("max_movies")
            result['mistral_batch_size'] = settings.getint("mistral_batch_size")
            result['request_timeout']    = settings.getint("request_timeout")
            result['retry_delay_min']    = settings.getfloat("retry_delay_min")
            result['retry_delay_max']    = settings.getfloat("retry_delay_max")
        except ValueError as e:
            logger.error(f"❌ [Settings] 某些配置项缺失或格式错误: {e}")
            sys.exit(1)

        # ── [Sources] section ────────────────────────────────────────────────
        if "Sources" not in config:
            logger.error("❌ 配置文件中缺少 [Sources] 部分")
            sys.exit(1)

        raw_urls = config["Sources"].get("scraper_urls", "").strip()
        urls = [u.strip() for u in raw_urls.replace('\n', ',').split(',') if u.strip()]
        if not urls:
            logger.error("❌ 爬虫源 scraper_urls 不能为空")
            sys.exit(1)
            
        result['scraper_urls'] = urls
        logger.info(f"✅ 爬虫源已加载: {len(urls)} 个 URL")

        logger.info(
            f"✅ 配置全部加载成功: provider={provider}, "
            f"max_workers={result['max_workers']}, max_movies={result['max_movies']}"
        )
        return result

    except configparser.Error as e:
        logger.error(f"❌ 配置文件解析错误: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ 加载配置时发生未知错误: {type(e).__name__} - {e}")
        sys.exit(1)
