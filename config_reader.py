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
    'retry_delay_max': 0.5
}

def read_config(config_file="config.ini"):
    """Reads configuration from config.ini and validates API keys."""
    config = configparser.ConfigParser()
    result = {}

    if not os.path.exists(config_file):
        logger.error(f"❌ 配置文件 '{config_file}' 不存在，请从 'config.ini.example' 复制并填写")
        return None

    try:
        config.read(config_file)

        # ── Mistral API ─────────────────────────────────────────
        if "Mistral" in config:
            mistral_api_key = config.get("Mistral", "api_key_mistral", fallback="").strip()
            # 清除两侧可能由于复制粘贴导致的中英文引号
            mistral_api_key = mistral_api_key.strip("'\"“”")
            if not mistral_api_key or mistral_api_key.startswith("<YOUR_"):
                logger.error("⚠️ Mistral API 密钥无效（长度过短或为占位符）")
                return None
            result['mistral_api_key'] = mistral_api_key
        else:
            logger.error("❌ 配置文件中缺少 [Mistral] 部分")
            return None

        # ── OMDb API ───────────────────────────────────────────
        if "OMDb_API" in config:
            omdb_key = config.get("OMDb_API", "OMDB_KEY", fallback="").strip()
            if omdb_key and not omdb_key.startswith("<YOUR_"):
                result['omdb_api_key'] = omdb_key
                logger.info("✅ OMDb API 密钥已加载")
            else:
                logger.error("❌ OMDb API 密钥无效或未填写")
                logger.error("   请前往 https://www.omdbapi.com/apikey.aspx 免费注册")
                logger.error("   然后在 config.ini 的 [OMDb_API] 下填写 OMDB_KEY=你的key")
                return None
        else:
            logger.error("❌ 配置文件中缺少 [OMDb_API] 部分")
            return None

        # ── Settings ───────────────────────────────────────────
        if "Settings" in config:
            result['max_workers']      = config.getint("Settings", "max_workers",      fallback=DEFAULT_CONFIG['max_workers'])
            result['max_movies']       = config.getint("Settings", "max_movies",        fallback=DEFAULT_CONFIG['max_movies'])
            result['mistral_batch_size'] = config.getint("Settings", "mistral_batch_size",  fallback=DEFAULT_CONFIG['mistral_batch_size'])
            result['request_timeout']  = config.getint("Settings", "request_timeout",   fallback=DEFAULT_CONFIG['request_timeout'])
            result['retry_delay_min']  = config.getfloat("Settings", "retry_delay_min", fallback=DEFAULT_CONFIG['retry_delay_min'])
            result['retry_delay_max']  = config.getfloat("Settings", "retry_delay_max", fallback=DEFAULT_CONFIG['retry_delay_max'])
        else:
            logger.info("⚠️ 未找到 [Settings]，使用默认配置")
            result.update(DEFAULT_CONFIG)

        logger.info(f"✅ 配置加载成功: max_workers={result['max_workers']}, max_movies={result['max_movies']}")
        return result

    except configparser.Error as e:
        logger.error(f"❌ 配置文件解析错误: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ 加载配置时发生未知错误: {type(e).__name__}")
        return None
