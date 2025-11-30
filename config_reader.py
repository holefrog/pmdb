import configparser
import os
import logging

logger = logging.getLogger(__name__)

# 默认配置
DEFAULT_CONFIG = {
    'max_workers': 5,
    'max_movies': 100,
    'deepl_batch_size': 50,
    'request_timeout': 10,
    'retry_delay_min': 0.2,
    'retry_delay_max': 0.5
}

def read_config(config_file="config.ini"):
    """Reads configuration from config.ini and validates the DeepL API key."""
    config = configparser.ConfigParser()
    result = {}
    
    if not os.path.exists(config_file):
        logger.error(f"❌ 配置文件 '{config_file}' 不存在。请从 'config.ini.example' 创建配置文件并填入 API 密钥。")
        return None
    
    try:
        config.read(config_file)
        
        # 读取 DeepL API 密钥
        if "DeepL_API" in config:
            deepl_api_key = config.get("DeepL_API", "API", fallback="").strip()
            # ✅ 改进后
            if not deepl_api_key or deepl_api_key.startswith("<YOUR_") or len(deepl_api_key) < 10:
                logger.error("⚠️ DeepL API 密钥无效（长度过短或为占位符）")
                return None
            result['deepl_api_key'] = deepl_api_key
        else:
            logger.error("❌ 配置文件中缺少 [DeepL_API] 部分")
            return None
        
        # 读取可选的设置项（使用默认值）
        if "Settings" in config:
            result['max_workers'] = config.getint("Settings", "max_workers", fallback=DEFAULT_CONFIG['max_workers'])
            result['max_movies'] = config.getint("Settings", "max_movies", fallback=DEFAULT_CONFIG['max_movies'])
            result['deepl_batch_size'] = config.getint("Settings", "deepl_batch_size", fallback=DEFAULT_CONFIG['deepl_batch_size'])
            result['request_timeout'] = config.getint("Settings", "request_timeout", fallback=DEFAULT_CONFIG['request_timeout'])
            result['retry_delay_min'] = config.getfloat("Settings", "retry_delay_min", fallback=DEFAULT_CONFIG['retry_delay_min'])
            result['retry_delay_max'] = config.getfloat("Settings", "retry_delay_max", fallback=DEFAULT_CONFIG['retry_delay_max'])
        else:
            # 使用默认配置
            logger.info("⚠️ 未找到 [Settings] 部分，使用默认配置")
            result.update(DEFAULT_CONFIG)
        
        logger.info(f"✅ 配置加载成功: max_workers={result['max_workers']}, max_movies={result['max_movies']}")
        return result
        
    except configparser.Error as e:
        logger.error(f"❌ 配置文件解析错误: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ 加载配置时发生未知错误: {type(e).__name__}")
        return None
