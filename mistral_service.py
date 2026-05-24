import requests
import json
import logging

logger = logging.getLogger(__name__)

def translate_texts(texts, api_key, batch_size=10):
    """
    使用 Mistral API 批量翻译文本列表。

    Args:
        texts: 待翻译文本列表
        api_key: Mistral API 密钥
        batch_size: 每次 API 调用最多翻译的文本数 (大语言模型建议设小一些，如 10)

    Returns:
        翻译后的文本列表（失败项会标注原因）
    """
    if not texts:
        logger.warning("⚠️ 翻译列表为空，返回空列表")
        return []

    texts_to_translate = [t for t in texts if t and t.strip()]

    if not texts_to_translate:
        logger.warning("⚠️ 所有文本为空，返回原始列表")
        return texts

    logger.info(f"Mistral API 端点: https://api.mistral.ai/v1/chat/completions")

    all_translated_raw = []
    num_batches = (len(texts_to_translate) + batch_size - 1) // batch_size
    logger.info(f"共 {len(texts_to_translate)} 个文本，分 {num_batches} 批翻译（每批最多 {batch_size} 个）")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    for i in range(0, len(texts_to_translate), batch_size):
        batch = texts_to_translate[i:i + batch_size]
        batch_num = i // batch_size + 1
        logger.info(f"正在翻译第 {batch_num}/{num_batches} 批（{len(batch)} 个文本）...")

        prompt = (
            "Translate the following JSON array of English movie summaries into Chinese. "
            "Return exactly a JSON object with a key 'translations' containing an array of translated strings in the exact same order.\n\n"
            f"{json.dumps(batch, ensure_ascii=False)}"
        )

        payload = {
            "model": "mistral-small-latest",
            "messages": [
                {"role": "system", "content": "You are a professional movie translator. Always return valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"}
        }

        try:
            response = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            parsed_content = json.loads(content)
            translations = parsed_content.get("translations", [])
            
            if len(translations) == len(batch):
                all_translated_raw.extend(translations)
                logger.info(f"✅ 第 {batch_num} 批翻译成功")
            else:
                logger.error(f"⚠️ 第 {batch_num} 批翻译结果数量不匹配！预期 {len(batch)}，实际 {len(translations)}")
                all_translated_raw.extend([f"[翻译不匹配] {t[:50]}..." for t in batch])

        except requests.HTTPError as e:
            status = e.response.status_code
            logger.error(f"❌ 第 {batch_num} 批 HTTP 错误: {status} - {e.response.text}")
            all_translated_raw.extend([f"[HTTP {status}] {t[:50]}..." for t in batch])
        except Exception as e:
            logger.error(f"❌ 第 {batch_num} 批未知错误: {type(e).__name__} - {e}")
            all_translated_raw.extend([f"[未知错误] {t[:50]}..." for t in batch])

    # 将翻译结果重新插回原始列表位置
    final = []
    translated_index = 0
    for original in texts:
        if original and original.strip():
            if translated_index < len(all_translated_raw):
                final.append(all_translated_raw[translated_index])
                translated_index += 1
            else:
                final.append("[翻译结果缺失]")
        else:
            final.append(original if original is not None else "无简介")

    logger.info(f"✅ 翻译任务完成")
    return final