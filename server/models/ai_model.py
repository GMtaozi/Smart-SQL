"""AI Model configuration model"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from server.db.base import Base


class AIModel(Base):
    """AI Model configuration.

    Stores configuration for various LLM providers.
    """

    __tablename__ = "ai_models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)  # Display name
    supplier = Column(String(50), nullable=False)  # openai, zhipu, qianfan, deepseek, etc.
    model_type = Column(Integer, default=0)  # 0=GPT, 1=Claude, etc.
    base_model = Column(String(100), nullable=False)  # e.g., gpt-4, gpt-4o-mini, claude-3-opus
    api_key_encrypted = Column(String(255), nullable=False)  # Encrypted API key
    api_domain = Column(String(255), nullable=True)  # API endpoint domain
    is_default = Column(Boolean, default=False)
    config_list = Column(Text, nullable=True)  # JSON string for additional config
    protocol = Column(Integer, default=1)  # 1=OpenAI compatible, 2=vllm
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<AIModel(id={self.id}, name='{self.name}', supplier='{self.supplier}')>"


# AI Model Suppliers
class ModelSupplier:
    """Supported AI model suppliers"""
    OPENAI = "openai"
    ZHIPU = "zhipu"              # 智谱AI
    QIANFAN = "qianfan"          # 百度千帆
    DEEPSEEK = "deepseek"        # DeepSeek
    TENCENT = "tencent"          # 腾讯混元
    XUNFEI = "xunfei"            # 讯飞星火
    GEMINI = "gemini"            # Google Gemini
    KIMI = "kimi"               # Kimi/Moonshot
    DASHSCOPE = "dashscope"      # 阿里云百炼
    VOLCENGINE = "volcengine"    # 火山引擎
    MINIMAX = "minimax"          # MiniMax
    CUSTOM = "custom"            # Custom OpenAI compatible

    @classmethod
    def values(cls):
        return [
            cls.OPENAI, cls.ZHIPU, cls.QIANFAN, cls.DEEPSEEK,
            cls.TENCENT, cls.XUNFEI, cls.GEMINI, cls.KIMI,
            cls.DASHSCOPE, cls.VOLCENGINE, cls.MINIMAX, cls.CUSTOM
        ]

    @classmethod
    def names(cls):
        return {
            cls.OPENAI: "OpenAI",
            cls.ZHIPU: "智谱AI",
            cls.QIANFAN: "百度千帆",
            cls.DEEPSEEK: "DeepSeek",
            cls.TENCENT: "腾讯混元",
            cls.XUNFEI: "讯飞星火",
            cls.GEMINI: "Google Gemini",
            cls.KIMI: "Kimi/Moonshot",
            cls.DASHSCOPE: "阿里云百炼",
            cls.VOLCENGINE: "火山引擎",
            cls.MINIMAX: "MiniMax",
            cls.CUSTOM: "自定义",
        }
