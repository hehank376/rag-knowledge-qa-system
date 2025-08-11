"""
嵌入模型工厂
"""
import logging
from typing import Dict, Type, Optional

from ..utils.exceptions import ConfigurationError, ProcessingError
from ..utils.model_exceptions import UnsupportedProviderError
from .base import BaseEmbedding, EmbeddingConfig
from .openai_embedding import OpenAIEmbedding
from .mock_embedding import MockEmbedding

logger = logging.getLogger(__name__)


class EmbeddingFactory:
    """嵌入模型工厂类"""
    
    _providers: Dict[str, Type[BaseEmbedding]] = {
        "openai": OpenAIEmbedding,
        "mock": MockEmbedding
    }
    
    # 延迟加载的提供商映射
    _lazy_providers: Dict[str, str] = {
        "siliconflow": "rag_system.embeddings.siliconflow_embedding.SiliconFlowEmbedding",
        #"modelscope": "rag_system.embeddings.modelscope_embedding.ModelScopeEmbedding",
        #"deepseek": "rag_system.embeddings.deepseek_embedding.DeepSeekEmbedding",
        #"ollama": "rag_system.embeddings.ollama_embedding.OllamaEmbedding",
    }
    
    @classmethod
    def create_embedding(cls, config: EmbeddingConfig) -> BaseEmbedding:
        """创建嵌入模型实例"""
        provider = config.provider.lower()
        embedding_class = cls._get_embedding_class(provider)
        
        try:
            embedding = embedding_class(config)
            logger.info(f"创建嵌入模型实例成功: {provider} - {config.model}")
            return embedding
        except Exception as e:
            logger.error(f"创建嵌入模型实例失败: {provider} - {str(e)}")
            raise ProcessingError(f"创建嵌入模型实例失败: {str(e)}")
    
    @classmethod
    def _get_embedding_class(cls, provider: str) -> Type[BaseEmbedding]:
        """获取嵌入模型类，支持延迟加载"""
        # 首先检查已加载的提供商
        if provider in cls._providers:
            return cls._providers[provider]
        
        # 检查延迟加载的提供商
        if provider in cls._lazy_providers:
            module_path = cls._lazy_providers[provider]
            try:
                # 动态导入模块
                module_name, class_name = module_path.rsplit('.', 1)
                module = __import__(module_name, fromlist=[class_name])
                embedding_class = getattr(module, class_name)
                
                # 缓存已加载的类
                cls._providers[provider] = embedding_class
                logger.debug(f"延迟加载嵌入模型提供商: {provider}")
                return embedding_class
                
            except ImportError as e:
                logger.error(f"无法导入嵌入模型提供商 {provider}: {str(e)}")
                raise UnsupportedProviderError(
                    f"嵌入模型提供商 {provider} 不可用，可能缺少相关依赖",
                    provider
                )
            except AttributeError as e:
                logger.error(f"嵌入模型提供商 {provider} 类不存在: {str(e)}")
                raise UnsupportedProviderError(
                    f"嵌入模型提供商 {provider} 实现不正确",
                    provider
                )
        
        # 提供商不存在
        available_providers = cls.get_available_providers()
        raise UnsupportedProviderError(
            f"不支持的嵌入模型提供商: {provider}. "
            f"支持的提供商: {', '.join(available_providers)}",
            provider
        )
    
    @classmethod
    def register_provider(cls, name: str, embedding_class: Type[BaseEmbedding]):
        """注册自定义嵌入提供商"""
        if not issubclass(embedding_class, BaseEmbedding):
            raise ValueError("嵌入类必须继承自BaseEmbedding")
        
        cls._providers[name.lower()] = embedding_class
        logger.info(f"注册嵌入提供商: {name}")
    
    @classmethod
    def get_available_providers(cls) -> list:
        """获取可用的嵌入提供商列表"""
        # 合并已加载和延迟加载的提供商
        all_providers = set(cls._providers.keys())
        all_providers.update(cls._lazy_providers.keys())
        return sorted(list(all_providers))
    
    @classmethod
    def create_from_config_dict(cls, config_dict: dict) -> BaseEmbedding:
        """从配置字典创建嵌入模型"""
        config = EmbeddingConfig(**config_dict)
        return cls.create_embedding(config)
    
    @classmethod
    def is_provider_available(cls, provider: str) -> bool:
        """检查提供商是否可用"""
        provider = provider.lower()
        
        # 检查已加载的提供商
        if provider in cls._providers:
            return True
        
        # 检查延迟加载的提供商
        if provider in cls._lazy_providers:
            try:
                cls._get_embedding_class(provider)
                return True
            except UnsupportedProviderError:
                return False
        
        return False
    
    @classmethod
    def get_provider_info(cls, provider: str) -> Optional[Dict[str, str]]:
        """获取提供商信息"""
        provider = provider.lower()
        
        if not cls.is_provider_available(provider):
            return None
        
        try:
            embedding_class = cls._get_embedding_class(provider)
            # 尝试获取提供商的默认信息
            if hasattr(embedding_class, 'get_provider_info'):
                return embedding_class.get_provider_info()
            else:
                return {
                    'provider': provider,
                    'class': embedding_class.__name__,
                    'module': embedding_class.__module__
                }
        except Exception as e:
            logger.error(f"获取嵌入模型提供商信息失败 {provider}: {str(e)}")
            return None


def create_embedding(config: EmbeddingConfig) -> BaseEmbedding:
    """便捷函数：创建嵌入模型实例"""
    return EmbeddingFactory.create_embedding(config)