"""
多 AI 提供商翻译服务。
通过 config['translate_provider'] 动态选择翻译后端：
  mistral  → Mistral AI
  openai   → OpenAI
  groq     → Groq (OpenAI-compatible)
  nvidia   → Nvidia NIM (OpenAI-compatible)
  gemini   → Google Gemini

所有模型、端点均通过 config (secrets.yml -> config.ini) 获取，不在代码中硬编码。
"""
import json
import logging
import requests
from abc import ABC, abstractmethod
from typing import List, Optional

try:
    from retry import with_retry
    _HAS_RETRY = True
except ImportError:
    _HAS_RETRY = False

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# 抽象基类
# ─────────────────────────────────────────────────────────────────────────────

class AbstractTranslator(ABC):
    """所有翻译器的基类，提供批量翻译接口。"""

    def translate_texts(self, texts: List[str], batch_size: int = 10) -> List[str]:
        if not texts:
            return []

        to_translate = [(i, t) for i, t in enumerate(texts) if t and t.strip()]
        results = list(texts)

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
    def __init__(self, api_key: str, model: str, endpoint: str, timeout: int = 60):
        self.api_key = api_key
        self.model = model
        self.endpoint = endpoint
        self.timeout = timeout
        self._retry_cfg = {
            "max_retries": 3,
            "base_delay": 5.0,
            "backoff_factor": 2.0,
            "max_delay": 60.0,
        }

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

        def _do_request():
            resp = requests.post(
                self.endpoint, headers=headers, json=payload, timeout=self.timeout
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return parsed.get("translations", [])

        if _HAS_RETRY:
            return with_retry(_do_request, self._retry_cfg, label=f"{self.model}")
        return _do_request()


# ─────────────────────────────────────────────────────────────────────────────
# Gemini 实现（使用 Google Generative Language API）
# ─────────────────────────────────────────────────────────────────────────────

class GeminiTranslator(AbstractTranslator):
    def __init__(self, api_key: str, model: str, endpoint_template: str, timeout: int = 60):
        self.api_key = api_key
        self.model = model
        self.endpoint_template = endpoint_template
        self.timeout = timeout
        self._retry_cfg = {
            "max_retries": 3,
            "base_delay": 5.0,
            "backoff_factor": 2.0,
            "max_delay": 60.0,
        }

    def _translate_batch(self, texts: List[str]) -> List[str]:
        prompt = (
            "Translate the following JSON array of English movie summaries into Chinese. "
            "Return exactly a JSON object with a key 'translations' containing an array "
            "of translated strings in the exact same order.\n\n"
            f"{json.dumps(texts, ensure_ascii=False)}"
        )
        # 支持从配置里提供 {model} 和 {api_key} 占位符
        url = self.endpoint_template.format(model=self.model, api_key=self.api_key)
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        }

        def _do_request():
            resp = requests.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(text)
            return parsed.get("translations", [])

        if _HAS_RETRY:
            return with_retry(_do_request, self._retry_cfg, label=f"gemini/{self.model}")
        return _do_request()


# ─────────────────────────────────────────────────────────────────────────────
# 工厂函数
# ─────────────────────────────────────────────────────────────────────────────

def get_translator(config: dict) -> Optional[AbstractTranslator]:
    """
    根据 config['translate_provider'] 实例化对应的翻译器。
    """
    provider = config.get("translate_provider", "").lower().strip()
    timeout = config.get("request_timeout", 60)

    if not provider:
        logger.error("❌ 翻译提供商未配置！")
        return None

    api_key_field = f"{provider}_api_key"
    model_field = f"{provider}_translate_model"
    endpoint_field = f"{provider}_endpoint"

    api_key = config.get(api_key_field)
    if not api_key:
        logger.error(f"❌ 翻译提供商 '{provider}' 的 API 密钥为空（字段: {api_key_field}）")
        return None

    model = config.get(model_field)
    if not model:
        logger.error(f"❌ 翻译提供商 '{provider}' 的模型为空（字段: {model_field}）")
        return None

    endpoint = config.get(endpoint_field)
    if not endpoint:
        logger.error(f"❌ 翻译提供商 '{provider}' 的端点为空（字段: {endpoint_field}）")
        return None

    if provider == "gemini":
        logger.info(f"✅ 使用翻译提供商: Gemini，模型: {model}")
        return GeminiTranslator(api_key=api_key, model=model, endpoint_template=endpoint, timeout=timeout)
    else:
        logger.info(f"✅ 使用翻译提供商: {provider}，模型: {model}，端点: {endpoint}")
        return OpenAICompatibleTranslator(
            api_key=api_key, model=model, endpoint=endpoint, timeout=timeout
        )


def translate_texts(texts: List[str], config: dict, batch_size: int = 10) -> List[str]:
    translator = get_translator(config)
    if not translator:
        logger.error("❌ 无法初始化翻译器，返回原始文本")
        return [f"[翻译器初始化失败] {t[:50]}" for t in texts]
    return translator.translate_texts(texts, batch_size=batch_size)
