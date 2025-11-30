import requests
import sys
import logging

logger = logging.getLogger(__name__)

def get_deepl_usage(api_key):
    """Check DeepL API Free usage quota."""
    url = "https://api-free.deepl.com/v2/usage"
    headers = {
        "Authorization": f"DeepL-Auth-Key {api_key}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        usage = response.json()
        used = usage.get("character_count", 0)
        limit = usage.get("character_limit", 500000)
        remaining = limit - used
        return used, remaining
    except requests.ConnectionError:
        logger.warning("⚠️ 检查 DeepL 配额时网络连接失败")
        return None, None
    except requests.Timeout:
        logger.warning("⚠️ 检查 DeepL 配额时请求超时")
        return None, None
    except requests.HTTPError as e:
        logger.warning(f"⚠️ DeepL API 返回错误: {e.response.status_code}")
        return None, None
    except Exception as e:
        logger.warning(f"⚠️ 检查 DeepL 配额时发生未知错误: {type(e).__name__}")
        return None, None

def translate_texts(texts, api_key, batch_size=50):
    """
    Translate a list of texts using DeepL API Free (Batch Translation with Chunking).
    
    Args:
        texts: List of texts to translate
        api_key: DeepL API key
        batch_size: Maximum number of texts per API call
        
    Returns:
        List of translated texts (or marked as failed)
    """
    if not texts:
        logger.warning("⚠️ 翻译列表为空，返回空列表")
        return []
    
    # 过滤掉空文本
    texts_to_translate = [t for t in texts if t and t.strip()]
    
    if not texts_to_translate:
        logger.warning("⚠️ 所有文本为空，返回原始列表")
        return texts

    # 检查配额
    used, remaining = get_deepl_usage(api_key)
    required_chars = sum(len(text) for text in texts_to_translate)
    
    if used is not None and remaining is not None:
        logger.info(f"DeepL 剩余配额: {remaining} 字符 (已用: {used} / 500,000)")
        if remaining < required_chars:
            logger.error(f"❌ 剩余配额 ({remaining}) 小于所需字符数 ({required_chars})，请检查！")
            sys.exit(1)
    else:
        logger.warning("⚠️ 无法获取配额信息，继续翻译")

    all_translated_summaries_raw = []
    total_chars_translated = 0
    
    # 分块翻译
    num_batches = (len(texts_to_translate) + batch_size - 1) // batch_size
    logger.info(f"共 {len(texts_to_translate)} 个文本待翻译，分为 {num_batches} 批（每批最多 {batch_size} 个）")
    
    for i in range(0, len(texts_to_translate), batch_size):
        batch = texts_to_translate[i:i + batch_size]
        batch_num = i // batch_size + 1
        
        char_count = sum(len(text) for text in batch)
        total_chars_translated += char_count
        logger.info(f"正在翻译第 {batch_num}/{num_batches} 批（{len(batch)} 个文本，{char_count} 字符）...")

        url = "https://api-free.deepl.com/v2/translate"
        params = {
            "auth_key": api_key,
            "text": batch,
            "source_lang": "EN",
            "target_lang": "ZH",
            "split_sentences": "nonewlines",
            "preserve_formatting": "1"
        }
        
        try:
            response = requests.post(url, data=params, timeout=30)
            response.raise_for_status()
            response_json = response.json()
            
            if 'translations' in response_json:
                all_translated_summaries_raw.extend([t["text"] for t in response_json["translations"]])
                logger.info(f"✅ 第 {batch_num} 批翻译成功")
            else:
                logger.error(f"⚠️ 第 {batch_num} 批 DeepL 响应格式异常，标记为翻译失败")
                all_translated_summaries_raw.extend([f"[翻译失败] {text[:50]}..." for text in batch])
                
        except requests.ConnectionError:
            logger.error(f"❌ 第 {batch_num} 批翻译时网络连接失败")
            all_translated_summaries_raw.extend([f"[网络错误] {text[:50]}..." for text in batch])
        except requests.Timeout:
            logger.error(f"❌ 第 {batch_num} 批翻译时请求超时")
            all_translated_summaries_raw.extend([f"[超时] {text[:50]}..." for text in batch])
        except requests.HTTPError as e:
            logger.error(f"❌ 第 {batch_num} 批翻译时 HTTP 错误: {e.response.status_code}")
            all_translated_summaries_raw.extend([f"[HTTP {e.response.status_code}] {text[:50]}..." for text in batch])
        except Exception as e:
            logger.error(f"❌ 第 {batch_num} 批翻译时发生未知错误: {type(e).__name__}")
            all_translated_summaries_raw.extend([f"[未知错误] {text[:50]}..." for text in batch])
            
    # 将翻译结果重新插入到原始列表的正确位置
    final_translated_summaries = []
    translated_index = 0
    for original_text in texts:
        if original_text and original_text.strip():
            if translated_index < len(all_translated_summaries_raw):
                final_translated_summaries.append(all_translated_summaries_raw[translated_index])
                translated_index += 1
            else:
                final_translated_summaries.append("[翻译结果缺失]")
        else:
            final_translated_summaries.append(original_text if original_text is not None else "无简介")
            
    logger.info(f"✅ 所有批次完成。总计翻译字符数: {total_chars_translated}")
    return final_translated_summaries
