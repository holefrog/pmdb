"""
多 AI 提供商翻译服务。
通过 config['translate_provider'] 动态选择翻译后端：
  mistral  → Mistral AI
  openai   → OpenAI
  groq     → Groq (OpenAI-compatible)
  nvidia   → Nvidia NIM (OpenAI-compatible)
  gemini   → Google Gemini

替代旧版 mistral_service.py（已删除）。
"""
import json
import logging
import requests
from abc import ABC, abstractmethod
from typing import List, Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# 抽象基类
# ─────────────────────────────────────────────────────────────────────────────

class AbstractTranslator(ABC):
    """所有翻译器的基类，提供批量翻译接口。"""

    def translate_texts(self, texts: List[str], batch_size: int = 10) -> List[str]:
        """
        批量翻译文本列表。
        - 空/None 项直接保留原值
        - 翻译失败的批次以 [错误标注] 形式返回
        """
        if not texts:
            return []

        # 过滤出需翻译的索引
        to_translate = [(i, t) for i, t in enumerate(texts) if t and t.strip()]
        results = list(texts)  # 先复制，空项保持原值

        if not to_translate:
            return results

        batches = [
            to_translate[i:i + batch_size]
            for i in range(0, len(to_translate), batch_size)
        ]
        num_batches = len(batches)
        logger.info(
            f"[{self.__class__.__name__}] 共 {len(to_translate)} 个文本，"
            f"分 {num_batches} 批翻译（每批≤{batch_size}）"
        )

        for batch_idx, batch in enumerate(batches, 1):
            indices = [item[0] for item in batch]
            source_texts = [item[1] for item in batch]
            logger.info(f"翻译第 {batch_idx}/{num_batches} 批（{len(source_texts)} 个）...")

            try:
                translated = self._translate_batch(source_texts)
                if len(translated) != len(source_texts):
                    logger.error(
                        f"⚠️ 第 {batch_idx} 批结果数量不匹配！"
                        f"预期 {len(source_texts)}，实际 {len(translated)}"
                    )
                    for i, t in zip(indices, source_texts):
                        results[i] = f"[翻译不匹配] {t[:50]}..."
                else:
                    for i, translated_text in zip(indices, translated):
                        results[i] = translated_text
                    logger.info(f"✅ 第 {batch_idx} 批翻译成功")
            except Exception as e:
                logger.error(f"❌ 第 {batch_idx} 批翻译失败: {type(e).__name__} - {e}")
                for i, t in zip(indices, source_texts):
                    results[i] = f"[翻译失败] {t[:50]}..."

        logger.info("✅ 翻译任务完成")
        return results

    @abstractmethod
    def _translate_batch(self, texts: List[str]) -> List[str]:
        """子类实现：翻译单批文本，返回等长的翻译结果列表。"""


# ─────────────────────────────────────────────────────────────────────────────
# OpenAI-compatible 通用实现（Mistral / OpenAI / Groq / Nvidia 均兼容）
# ─────────────────────────────────────────────────────────────────────────────

class OpenAICompatibleTranslator(AbstractTranslator):
    """
    通用 OpenAI-compatible API 翻译器。
    Mistral、OpenAI、Groq、Nvidia NIM 均可复用此实现。
    """

    def __init__(self, api_key: str, model: str, endpoint: str, timeout: int = 60):
        self.api_key = api_key
        self.model = model
        self.endpoint = endpoint
        self.timeout = timeout

    def _translate_batch(self, texts: List[str]) -> List[str]:
        prompt = (
            "Translate the following JSON array of English movie summaries into Chinese. "
            "Return exactly a JSON object with a key 'translations' containing an array "
            "of translated strings in the exact same order.\n\n"
            f"{json.dumps(texts, ensure_ascii=False)}"
        )
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a professional movie translator. Always return valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.3,
        }
        resp = requests.post(
            self.endpoint, headers=headers, json=payload, timeout=self.timeout
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        return parsed.get("translations", [])


# ─────────────────────────────────────────────────────────────────────────────
# Gemini 实现（使用 Google Generative Language API）
# ─────────────────────────────────────────────────────────────────────────────

class GeminiTranslator(AbstractTranslator):
    """Google Gemini API 翻译器（使用 REST generateContent 接口）。"""

    ENDPOINT_TEMPLATE = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "{model}:generateContent?key={api_key}"
    )

    def __init__(self, api_key: str, model: str, timeout: int = 60):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def _translate_batch(self, texts: List[str]) -> List[str]:
        prompt = (
            "Translate the following JSON array of English movie summaries into Chinese. "
            "Return exactly a JSON object with a key 'translations' containing an array "
            "of translated strings in the exact same order.\n\n"
            f"{json.dumps(texts, ensure_ascii=False)}"
        )
        url = self.ENDPOINT_TEMPLATE.format(model=self.model, api_key=self.api_key)
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        }
        resp = requests.post(url, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(text)
        return parsed.get("translations", [])


# ─────────────────────────────────────────────────────────────────────────────
# 工厂函数
# ─────────────────────────────────────────────────────────────────────────────

_PROVIDER_ENDPOINTS = {
    "mistral": "https://api.mistral.ai/v1/chat/completions",
    "openai": "https://api.openai.com/v1/chat/completions",
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "nvidia": "https://integrate.api.nvidia.com/v1/chat/completions",
}

_PROVIDER_API_KEY_FIELD = {
    "mistral": "mistral_api_key",
    "openai": "openai_api_key",
    "groq": "groq_api_key",
    "nvidia": "nvidia_api_key",
    "gemini": "gemini_api_key",
}

_PROVIDER_MODEL_FIELD = {
    "mistral": "mistral_translate_model",
    "openai": "openai_translate_model",
    "groq": "groq_translate_model",
    "nvidia": "nvidia_translate_model",
    "gemini": "gemini_translate_model",
}

_PROVIDER_MODEL_DEFAULTS = {
    "mistral": "mistral-large-latest",
    "openai": "gpt-4o-mini",
    "groq": "llama-3.3-70b-versatile",
    "nvidia": "meta/llama-3.3-70b-instruct",
    "gemini": "gemini-2.5-flash",
}


def get_translator(config: dict) -> Optional[AbstractTranslator]:
    """
    根据 config['translate_provider'] 实例化对应的翻译器。

    Args:
        config: read_config() 返回的字典

    Returns:
        AbstractTranslator 子类实例，或 None（配置错误时）
    """
    provider = config.get("translate_provider", "mistral").lower().strip()
    timeout = config.get("request_timeout", 60)

    api_key_field = _PROVIDER_API_KEY_FIELD.get(provider)
    if not api_key_field:
        logger.error(f"❌ 未知翻译提供商: '{provider}'，支持: {list(_PROVIDER_API_KEY_FIELD.keys())}")
        return None

    api_key = config.get(api_key_field, "").strip()
    if not api_key:
        logger.error(f"❌ 翻译提供商 '{provider}' 的 API 密钥为空（字段: {api_key_field}）")
        return None

    model_field = _PROVIDER_MODEL_FIELD[provider]
    model = config.get(model_field, _PROVIDER_MODEL_DEFAULTS[provider])

    if provider == "gemini":
        logger.info(f"✅ 使用翻译提供商: Gemini，模型: {model}")
        return GeminiTranslator(api_key=api_key, model=model, timeout=timeout)
    else:
        endpoint = _PROVIDER_ENDPOINTS[provider]
        logger.info(f"✅ 使用翻译提供商: {provider}，模型: {model}，端点: {endpoint}")
        return OpenAICompatibleTranslator(
            api_key=api_key, model=model, endpoint=endpoint, timeout=timeout
        )


# ─────────────────────────────────────────────────────────────────────────────
# 便捷函数（供 main.py 调用，与旧 mistral_service.translate_texts 接口兼容）
# ─────────────────────────────────────────────────────────────────────────────

def translate_texts(texts: List[str], config: dict, batch_size: int = 10) -> List[str]:
    """
    便捷入口：从 config 自动选择翻译器并翻译。

    Args:
        texts: 待翻译文本列表
        config: read_config() 返回的字典
        batch_size: 每批翻译数量

    Returns:
        翻译后的文本列表（失败项带错误标注）
    """
    translator = get_translator(config)
    if not translator:
        logger.error("❌ 无法初始化翻译器，返回原始文本")
        return [f"[翻译器初始化失败] {t[:50]}" for t in texts]
    return translator.translate_texts(texts, batch_size=batch_size)
