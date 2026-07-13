import configparser
import os
import logging

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    'max_workers': 5,
    'max_movies': 100,
    'mistral_batch_size': 10,
    'request_timeout': 10,
    'retry_delay_min': 0.2,
    'retry_delay_max': 0.5,
    'translate_provider': 'mistral',
    'imdb_lookup_model': 'mistral-small-latest',
    # 翻译模型默认值（各提供商）
    'gemini_translate_model': 'gemini-2.5-flash',
    'openai_translate_model': 'gpt-4o-mini',
    'mistral_translate_model': 'mistral-large-latest',
    'groq_translate_model': 'llama-3.3-70b-versatile',
    'nvidia_translate_model': 'meta/llama-3.3-70b-instruct',
}

# 内置备用爬虫源（config.ini 未配置时使用）
DEFAULT_SCRAPER_URLS = [
    "https://thepiratebay.org/search.php?q=top100:207",
    "https://piratebay.live/search.php?q=top100:207",
    "https://tpb.party/search.php?q=top100:207",
    "https://thepiratebay.org/top/207",
]


def read_config(config_file: str = "config.ini") -> dict | None:
    """
    读取 config.ini（由 Ansible 从 ansible/secrets.yml + config.ini.j2 生成）并返回配置字典。

    Sections:
      [AI]       - 翻译提供商、各 API 密钥、各模型名
      [OMDb_API] - OMDb API 密钥
      [Settings] - 运行时参数
      [Sources]  - 爬虫 URL 列表（可选）
    """
    config = configparser.ConfigParser()
    result = {}

    if not os.path.exists(config_file):
        logger.error(
            f"❌ 配置文件 '{config_file}' 不存在。\n"
            "   请先运行 Ansible 部署: ansible-playbook ansible/playbook.yml -e @ansible/secrets.yml"
        )
        return None

    try:
        config.read(config_file, encoding='utf-8')

        # ── [AI] section ─────────────────────────────────────────────────────
        if "AI" not in config:
            logger.error("❌ 配置文件中缺少 [AI] 部分（请检查 config.ini.j2 模板）")
            return None

        ai = config["AI"]

        # 翻译提供商
        provider = ai.get("translate_provider", DEFAULT_CONFIG['translate_provider']).strip()
        result['translate_provider'] = provider

        # 各提供商 API 密钥（允许为空，由翻译器在使用时报错）
        for key_field in [
            'mistral_api_key', 'openai_api_key', 'groq_api_key',
            'nvidia_api_key', 'gemini_api_key'
        ]:
            val = ai.get(key_field, "").strip().strip('"\'')
            result[key_field] = val

        # 翻译模型
        for model_field, default in [
            ('gemini_translate_model',  DEFAULT_CONFIG['gemini_translate_model']),
            ('openai_translate_model',  DEFAULT_CONFIG['openai_translate_model']),
            ('mistral_translate_model', DEFAULT_CONFIG['mistral_translate_model']),
            ('groq_translate_model',    DEFAULT_CONFIG['groq_translate_model']),
            ('nvidia_translate_model',  DEFAULT_CONFIG['nvidia_translate_model']),
        ]:
            result[model_field] = ai.get(model_field, default).strip()

        # IMDb AI 兜底查询模型
        result['imdb_lookup_model'] = ai.get(
            'imdb_lookup_model', DEFAULT_CONFIG['imdb_lookup_model']
        ).strip()

        # 验证当前选择的提供商有可用密钥
        provider_key_map = {
            'mistral': 'mistral_api_key',
            'openai':  'openai_api_key',
            'groq':    'groq_api_key',
            'nvidia':  'nvidia_api_key',
            'gemini':  'gemini_api_key',
        }
        active_key_field = provider_key_map.get(provider)
        if active_key_field:
            active_key = result.get(active_key_field, "")
            if not active_key or active_key.startswith("<YOUR_"):
                logger.error(
                    f"⚠️ 翻译提供商 '{provider}' 的 API 密钥无效或未填写\n"
                    f"   请在 ansible/secrets.yml 中填写 {active_key_field}"
                )
                return None
            logger.info(f"✅ 翻译提供商: {provider}，密钥已加载")
        else:
            logger.error(
                f"❌ 未知翻译提供商: '{provider}'，"
                f"支持: {list(provider_key_map.keys())}"
            )
            return None

        # ── [OMDb_API] section ───────────────────────────────────────────────
        if "OMDb_API" not in config:
            logger.error("❌ 配置文件中缺少 [OMDb_API] 部分")
            return None

        omdb_key = config.get("OMDb_API", "OMDB_KEY", fallback="").strip()
        if not omdb_key or omdb_key.startswith("<YOUR_"):
            logger.error(
                "❌ OMDb API 密钥无效或未填写\n"
                "   请前往 https://www.omdbapi.com/apikey.aspx 免费注册\n"
                "   然后在 ansible/secrets.yml 中填写 omdb_api_key"
            )
            return None
        result['omdb_api_key'] = omdb_key
        logger.info("✅ OMDb API 密钥已加载")

        # ── [Settings] section ───────────────────────────────────────────────
        if "Settings" in config:
            result['max_workers']        = config.getint("Settings", "max_workers",         fallback=DEFAULT_CONFIG['max_workers'])
            result['max_movies']         = config.getint("Settings", "max_movies",           fallback=DEFAULT_CONFIG['max_movies'])
            result['mistral_batch_size'] = config.getint("Settings", "mistral_batch_size",   fallback=DEFAULT_CONFIG['mistral_batch_size'])
            result['request_timeout']    = config.getint("Settings", "request_timeout",      fallback=DEFAULT_CONFIG['request_timeout'])
            result['retry_delay_min']    = config.getfloat("Settings", "retry_delay_min",    fallback=DEFAULT_CONFIG['retry_delay_min'])
            result['retry_delay_max']    = config.getfloat("Settings", "retry_delay_max",    fallback=DEFAULT_CONFIG['retry_delay_max'])
        else:
            logger.info("⚠️ 未找到 [Settings]，使用默认配置")
            for k in ['max_workers', 'max_movies', 'mistral_batch_size',
                      'request_timeout', 'retry_delay_min', 'retry_delay_max']:
                result[k] = DEFAULT_CONFIG[k]

        # ── [Sources] section（可选）────────────────────────────────────────
        result['scraper_urls'] = DEFAULT_SCRAPER_URLS.copy()
        if "Sources" in config:
            raw_urls = config.get("Sources", "scraper_urls", fallback="").strip()
            if raw_urls:
                # 支持逗号或换行分隔
                urls = [u.strip() for u in raw_urls.replace('\n', ',').split(',') if u.strip()]
                if urls:
                    result['scraper_urls'] = urls
                    logger.info(f"✅ 爬虫源已加载: {len(urls)} 个 URL")

        logger.info(
            f"✅ 配置加载成功: provider={provider}, "
            f"max_workers={result['max_workers']}, max_movies={result['max_movies']}"
        )
        return result

    except configparser.Error as e:
        logger.error(f"❌ 配置文件解析错误: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ 加载配置时发生未知错误: {type(e).__name__} - {e}")
        return None
