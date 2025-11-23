import requests
import sys

# Define a safe batch size based on DeepL's recommended limits (typically max 50 texts per call)
DEEPL_MAX_BATCH_SIZE = 50 
# Global variable to track total translated characters (local count)
total_chars_translated = 0

def get_deepl_usage(api_key):
    """Check DeepL API Free usage quota."""
    url = "https://api-free.deepl.com/v2/usage"
    headers = {
        "Authorization": f"DeepL-Auth-Key {api_key}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        usage = response.json()
        used = usage.get("character_count", 0)
        limit = usage.get("character_limit", 500000)
        remaining = limit - used
        return used, remaining
    except Exception as e:
        print(f"⚠️ Failed to check DeepL quota: {e}")
        return None, None

def translate_texts(texts, api_key):
    """Translate a list of texts using DeepL API Free (Batch Translation with Chunking)."""
    global total_chars_translated

    if not texts:
        print("⚠️ Empty text list, returning empty list")
        return []
    
    # 过滤掉空文本，DeepL API不接受空字符串。
    texts_to_translate = [t for t in texts if t and t.strip()]
    
    if not texts_to_translate:
        return texts # 如果全部为空，直接返回原始列表

    # 检查配额
    used, remaining = get_deepl_usage(api_key)
    required_chars = sum(len(text) for text in texts_to_translate)
    
    if used is not None and remaining is not None:
        print(f"Current remaining quota: {remaining} characters (used: {used} / 500,000)")
        if remaining < required_chars:
            print(f"⚠️ Remaining quota ({remaining}) is less than required characters ({required_chars}). Please check! Exiting.")
            sys.exit(1)
    else:
        print("⚠️ Unable to fetch quota information, continuing translation")

    
    all_translated_summaries_raw = []
    
    # --- 实现分块翻译 ---
    num_batches = (len(texts_to_translate) + DEEPL_MAX_BATCH_SIZE - 1) // DEEPL_MAX_BATCH_SIZE
    print(f"Total texts to translate: {len(texts_to_translate)}. Using {num_batches} batches (max {DEEPL_MAX_BATCH_SIZE} per batch).")
    
    for i in range(0, len(texts_to_translate), DEEPL_MAX_BATCH_SIZE):
        batch = texts_to_translate[i:i + DEEPL_MAX_BATCH_SIZE]
        
        char_count = sum(len(text) for text in batch)
        total_chars_translated += char_count
        print(f"\nTranslating batch {i//DEEPL_MAX_BATCH_SIZE + 1}/{num_batches} of {len(batch)} texts ({char_count} characters)...")

        url = "https://api-free.deepl.com/v2/translate"
        # DeepL API 通过多次传递 'text' 参数来处理文本列表
        params = {
            "auth_key": api_key,
            "text": batch, # 当前批次文本
            "source_lang": "EN",
            "target_lang": "ZH",
            "split_sentences": "nonewlines",
            "preserve_formatting": "1"
        }
        
        try:
            response = requests.post(url, data=params)
            response.raise_for_status()
            response_json = response.json()
            
            if 'translations' in response_json:
                all_translated_summaries_raw.extend([t["text"] for t in response_json["translations"]])
                print(f"✅ Batch {i//DEEPL_MAX_BATCH_SIZE + 1} translation successful.")
            else:
                print(f"⚠️ Invalid DeepL response for batch {i//DEEPL_MAX_BATCH_SIZE + 1}. Returning original texts.")
                return texts
                
        except Exception as e:
            print(f"❌ DeepL batch translation failed for batch {i//DEEPL_MAX_BATCH_SIZE + 1}: {e}. Returning original texts.")
            return texts
            
    # 将翻译结果重新插入到原始列表的正确位置，以保持顺序
    final_translated_summaries = []
    translated_index = 0
    for original_text in texts:
        if original_text and original_text.strip():
            if translated_index < len(all_translated_summaries_raw):
                 final_translated_summaries.append(all_translated_summaries_raw[translated_index])
                 translated_index += 1
            else:
                 final_translated_summaries.append("翻译失败或结果缺失。")
        else:
            final_translated_summaries.append(original_text if original_text is not None else "无简介")
            
    print(f"\n✅ All batches complete. Total characters translated: {total_chars_translated}")

    return final_translated_summaries
