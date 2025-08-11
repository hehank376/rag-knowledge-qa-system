"""
重排序模型工厂

提供统一的重排序模型创建接口，支持延迟加载和多提供商。
与嵌入模型工厂保持架构一致。
"""

import logging
from typing import Dict, Type, Optional

from ..utils.exceptions import ConfigurationError, ProcessingError
from ..utils.model_exceptions import UnsupportedProviderError
from .base import BaseReranking, RerankingConfig
from .mock_reranking import MockReranking

logger = logging.getLogger(__name__)


class RerankingFactory:
    """重排序模型工厂类"""
    
    # 预加载的提供商
    _providers: Dict[str, Type[BaseReranking]] = {
        "mock": MockReranking
    }
    
    # 延迟加载的提供商映射
    _lazy_providers: Dict[str, str] = {
        "local": "rag_system.reranking.local_reranking.LocalReranking",
        "sentence_transformers": "rag_system.reranking.local_reranking.LocalReranking",
        "siliconflow": "rag_system.reranking.siliconflow_reranking.SiliconFlowReranking",
        "openai": "rag_system.reranking.openai_reranking.OpenAIReranking",
        "huggingface": "rag_system.reranking.huggingface_reranking.HuggingFaceReranking",
    }
    
    @classmethod
    def create_reranking(cls, config: RerankingConfig) -> BaseReranking:
        """
        创建重排序模型实例
        
        Args:
            config: 重排序配置
            
        Returns:
            重排序模型实例
            
        Raises:
            ProcessingError: 创建失败时抛出
        """
        provider = config.provider.lower()
        reranking_class = cls._get_reranking_class(provider)
        
        try:
            reranking = reranking_class(config)
            logger.info(f"创建重排序模型实例成功: {provider} - {config.get_model_name()}")
            return reranking
        except Exception as e:
            logger.error(f"创建重排序模型实例失败: {provider} - {str(e)}")
            raise ProcessingError(f"创建重排序模型实例失败: {str(e)}")
    
    @classmethod
    def _get_reranking_class(cls, provider: str) -> Type[BaseReranking]:
        """
        获取重排序模型类，支持延迟加载
        
        Args:
            provider: 提供商名称
            
        Returns:
            重排序模型类
            
        Raises:
            UnsupportedProviderError: 不支持的提供商
        """
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
                reranking_class = getattr(module, class_name)
                
                # 缓存已加载的类
                cls._providers[provider] = reranking_class
                logger.debug(f"延迟加载重排序模型提供商: {provider}")
                return reranking_class
                
            except ImportError as e:
                logger.error(f"无法导入重排序模型提供商 {provider}: {str(e)}")
                raise UnsupportedProviderError(
                    f"重排序模型提供商 {provider} 不可用，可能缺少相关依赖",
                    provider
                )
            except AttributeError as e:
                logger.error(f"重排序模型提供商 {provider} 类不存在: {str(e)}")
                raise UnsupportedProviderError(
                    f"重排序模型提供商 {provider} 实现不正确",
                    provider
                )
        
        # 提供商不存在
        available_providers = cls.get_available_providers()
        raise UnsupportedProviderError(
            f"不支持的重排序模型提供商: {provider}. "
            f"支持的提供商: {', '.join(available_providers)}",
            provider
        )
    
    @classmethod
    def register_provider(cls, name: str, reranking_class: Type[BaseReranking]):
        """
        注册自定义重排序提供商
        
        Args:
            name: 提供商名称
            reranking_class: 重排序类
            
        Raises:
            ValueError: 类型不正确时抛出
        """
        if not issubclass(reranking_class, BaseReranking):
            raise ValueError("重排序类必须继承自BaseReranking")
        
        cls._providers[name.lower()] = reranking_class
        logger.info(f"注册重排序提供商: {name}")
    
    @classmethod
    def get_available_providers(cls) -> list:
        """
        获取可用的重排序提供商列表
        
        Returns:
            提供商名称列表
        """
        # 合并已加载和延迟加载的提供商
        all_providers = set(cls._providers.keys())
        all_providers.update(cls._lazy_providers.keys())
        return sorted(list(all_providers))
    
    @classmethod
    def create_from_config_dict(cls, config_dict: dict) -> BaseReranking:
        """
        从配置字典创建重排序模型
        
        Args:
            config_dict: 配置字典
            
        Returns:
            重排序模型实例
        """
        config = RerankingConfig(**config_dict)
        return cls.create_reranking(config)
    
    @classmethod
    def is_provider_available(cls, provider: str) -> bool:
        """
        检查提供商是否可用
        
        Args:
            provider: 提供商名称
            
        Returns:
            是否可用
        """
        provider = provider.lower()
        
        # 检查已加载的提供商
        if provider in cls._providers:
            return True
        
        # 检查延迟加载的提供商
        if provider in cls._lazy_providers:
            try:
                cls._get_reranking_class(provider)
                return True
            except UnsupportedProviderError:
                return False
        
        return False
    
    @classmethod
    def get_provider_info(cls, provider: str) -> Optional[Dict[str, str]]:
        """
        获取提供商信息
        
        Args:
            provider: 提供商名称
            
        Returns:
            提供商信息字典，如果不可用则返回None
        """
        provider = provider.lower()
        
        if not cls.is_provider_available(provider):
            return None
        
        try:
            reranking_class = cls._get_reranking_class(provider)
            # 尝试获取提供商的默认信息
            if hasattr(reranking_class, 'get_provider_info'):
                return reranking_class.get_provider_info()
            else:
                return {
                    'provider': provider,
                    'class': reranking_class.__name__,
                    'module': reranking_class.__module__,
                    'type': 'api' if provider in ['siliconflow', 'openai'] else 'local'
                }
        except Exception as e:
            logger.error(f"获取重排序模型提供商信息失败 {provider}: {str(e)}")
            return None
    
    @classmethod
    def auto_detect_provider(cls, config_dict: dict) -> str:
        """
        自动检测最适合的提供商
        
        Args:
            config_dict: 配置字典
            
        Returns:
            推荐的提供商名称
        """
        # 如果有API密钥和基础URL，优先使用API提供商
        if config_dict.get('api_key') and config_dict.get('base_url'):
            base_url = config_dict['base_url'].lower()
            if 'siliconflow' in base_url:
                return 'siliconflow'
            elif 'openai' in base_url:
                return 'openai'
        
        # 如果指定了本地模型相关的配置
        provider = config_dict.get('provider', '').lower()
        if provider in ['local', 'sentence_transformers', 'huggingface']:
            return provider
        
        # 默认使用本地提供商
        return 'local'
    
    @classmethod
    def create_with_fallback(cls, config: RerankingConfig) -> tuple[BaseReranking, Optional[BaseReranking]]:
        """
        创建带备用模型的重排序实例
        
        Args:
            config: 重排序配置
            
        Returns:
            (主要模型, 备用模型) 元组
        """
        # 创建主要模型
        main_reranking = cls.create_reranking(config)
        
        # 创建备用模型
        fallback_reranking = None
        if config.enable_fallback:
            try:
                fallback_config = RerankingConfig(
                    provider=config.fallback_provider,
                    model="mock-reranking",
                    max_length=config.max_length,
                    batch_size=config.batch_size,
                    timeout=config.timeout
                )
                fallback_reranking = cls.create_reranking(fallback_config)
                logger.info(f"创建备用重排序模型成功: {config.fallback_provider}")
            except Exception as e:
                logger.warning(f"创建备用重排序模型失败: {str(e)}")
        
        return main_reranking, fallback_reranking


def create_reranking(config: RerankingConfig) -> BaseReranking:
    """
    便捷函数：创建重排序模型实例
    
    Args:
        config: 重排序配置
        
    Returns:
        重排序模型实例
    """
    return RerankingFactory.create_reranking(config)