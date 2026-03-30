"""AI Model service - LLM integration with multiple providers"""

import json
import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

# Fix httpx proxies issue - httpx 0.28+ uses 'proxy' instead of 'proxies'
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)

import httpx
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

# Monkey patch httpx.Client to accept 'proxies' for backward compatibility
_original_client_init = httpx.Client.__init__

def _patched_client_init(self, *args, **kwargs):
    if 'proxies' in kwargs:
        kwargs['proxy'] = kwargs.pop('proxies')
    return _original_client_init(self, *args, **kwargs)

httpx.Client.__init__ = _patched_client_init


@dataclass
class LLMResponse:
    """Standardized LLM response"""
    success: bool
    content: Optional[str] = None
    error: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None


class AIModelService:
    """Service for calling various LLM providers"""

    def __init__(self, api_key: str, model: str, api_domain: Optional[str] = None,
                 supplier: str = "openai", extra_config: Optional[Dict] = None):
        self.api_key = api_key
        self.model = model
        self.api_domain = api_domain or self._get_default_domain(supplier)
        self.supplier = supplier
        self.extra_config = extra_config or {}

    def _get_default_domain(self, supplier: str) -> str:
        """Get default API domain for supplier"""
        domains = {
            "openai": "https://api.openai.com/v1",
            "zhipu": "https://open.bigmodel.cn/api/paas/v4",
            "qianfan": "https://qianfan.baidubce.com/v2",
            "deepseek": "https://api.deepseek.com/v1",
            "tencent": "https://hunyuan.cloud.tencent.com",
            "xunfei": "https://spark-api.xf-yun.com/v1",
            "gemini": "https://generativelanguage.googleapis.com/v1beta",
            "kimi": "https://api.moonshot.cn/v1",
            "dashscope": "https://dashscope.aliyuncs.com/api/v1",
            "volcengine": "https://ark.cn-beijing.volces.com/api/v3",
            "minimax": "https://api.minimax.chat/v1",
        }
        return domains.get(supplier, "https://api.openai.com/v1")

    def _create_llm(self) -> ChatOpenAI:
        """Create LLM instance based on configuration"""
        # For OpenAI-compatible APIs
        if self.supplier in ["openai", "deepseek", "kimi", "custom"]:
            return ChatOpenAI(
                model=self.model,
                api_key=self.api_key,
                base_url=self.api_domain,
                temperature=self.extra_config.get("temperature", 0.0),  # SQL生成应该用0
                max_tokens=self.extra_config.get("max_tokens", 4000),  # 增加避免截断
            )
        elif self.supplier == "zhipu":
            # 智谱AI - OpenAI compatible
            return ChatOpenAI(
                model=self.model,
                api_key=self.api_key,
                base_url=self.api_domain,
                temperature=self.extra_config.get("temperature", 0.0),
                max_tokens=self.extra_config.get("max_tokens", 4000),
            )
        elif self.supplier == "qianfan":
            # 百度千帆 - uses secret_key
            return ChatOpenAI(
                model=self.model,
                api_key=self.api_key,  # In qianfan, api_key is the access_key
                base_url=self.api_domain,
                temperature=self.extra_config.get("temperature", 0.0),
                max_tokens=self.extra_config.get("max_tokens", 4000),
            )
        elif self.supplier == "dashscope":
            # 阿里云百炼
            return ChatOpenAI(
                model=self.model,
                api_key=self.api_key,
                base_url=self.api_domain,
                temperature=self.extra_config.get("temperature", 0.0),
                max_tokens=self.extra_config.get("max_tokens", 4000),
            )
        else:
            # Default to OpenAI compatible
            return ChatOpenAI(
                model=self.model,
                api_key=self.api_key,
                base_url=self.api_domain,
                temperature=self.extra_config.get("temperature", 0.0),
                max_tokens=self.extra_config.get("max_tokens", 4000),
            )

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        """Send chat request to LLM

        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional parameters like temperature, max_tokens

        Returns:
            LLMResponse with content or error
        """
        try:
            llm = self._create_llm()

            # Convert messages format
            langchain_messages = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")

                if role == "system":
                    langchain_messages.append(SystemMessage(content=content))
                else:
                    langchain_messages.append(HumanMessage(content=content))

            # Override with kwargs
            if kwargs:
                for key, value in kwargs.items():
                    if hasattr(llm, key):
                        setattr(llm, key, value)

            # Call LLM
            response = llm.invoke(langchain_messages)

            return LLMResponse(
                success=True,
                content=response.content,
                usage={
                    "prompt_tokens": getattr(response, "usage", {}).get("prompt_tokens", 0),
                    "completion_tokens": getattr(response, "usage", {}).get("completion_tokens", 0),
                } if hasattr(response, "usage") else None
            )

        except Exception as e:
            return LLMResponse(
                success=False,
                error=str(e)
            )

    def chat_with_prompt(self, system_prompt: str, user_prompt: str, **kwargs) -> LLMResponse:
        """Convenience method for simple prompt

        Args:
            system_prompt: System message
            user_prompt: User message
            **kwargs: Additional parameters

        Returns:
            LLMResponse with content or error
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        return self.chat(messages, **kwargs)

    @staticmethod
    def test_connection(api_key: str, model: str, supplier: str = "openai",
                       api_domain: Optional[str] = None, extra_config: Optional[Dict] = None) -> LLMResponse:
        """Test connection to LLM provider

        Args:
            api_key: API key
            model: Model name
            supplier: Supplier name
            api_domain: Custom API domain
            extra_config: Additional configuration

        Returns:
            LLMResponse indicating success or failure
        """
        service = AIModelService(api_key, model, api_domain, supplier, extra_config)
        return service.chat_with_prompt(
            "You are a helpful assistant.",
            "Say 'Connection successful!' if you can hear me.",
            temperature=0.1
        )


def get_default_ai_model() -> Optional[AIModelService]:
    """Get the default AI model service from database"""
    from server.db.database import get_db_session
    from server.models.ai_model import AIModel

    db = get_db_session()
    try:
        model_config = db.query(AIModel).filter(
            AIModel.is_default == True,
            AIModel.enabled == True
        ).first()

        if not model_config:
            # Try to use the first enabled model
            model_config = db.query(AIModel).filter(
                AIModel.enabled == True
            ).first()

        if not model_config:
            return None

        extra_config = {}
        if model_config.config_list:
            try:
                extra_config = json.loads(model_config.config_list)
            except json.JSONDecodeError:
                pass

        return AIModelService(
            api_key=model_config.api_key_encrypted,
            model=model_config.base_model,
            api_domain=model_config.api_domain,
            supplier=model_config.supplier,
            extra_config=extra_config
        )
    finally:
        db.close()
