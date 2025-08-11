"""
重排序模块

提供统一的重排序接口，支持多种提供商：
- 本地模型（sentence-transformers）
- API调用（SiliconFlow, OpenAI等）
- Mock实现（测试用）

使用工厂模式和统一配置管理，与嵌入模型架构保持一致。
"""

from .base import BaseReranking, RerankingConfig
from .factory import RerankingFactory, create_reranking

__all__ = [
    'BaseReranking',
    'RerankingConfig', 
    'RerankingFactory',
    'create_reranking'
]