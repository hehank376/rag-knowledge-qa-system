"""
LLM工厂类
"""
import logging
from typing import Dict, Type, Optional

from .base import BaseLLM, LLMConfig
from .mock_llm import MockLLM
from .openai_llm import OpenAILLM
from ..utils.exceptions import ProcessingError
from ..utils.model_exceptions import UnsupportedProviderError

logger = logging.getLogger(__name__)


class LLMFactory:
    """LLM工厂类"""
    
    _providers: Dict[str, Type[BaseLLM]] = {
        "mock": MockLLM,
        "openai": OpenAILLM,
    }
    
    # 延迟加载的提供商映射
    _lazy_providers: Dict[str, str] = {
        "siliconflow": "rag_system.llm.siliconflow_llm.SiliconFlowLLM",
        #"modelscope": "rag_system.llm.modelscope_llm.ModelScopeLLM",
        #"deepseek": "rag_system.llm.deepseek_llm.DeepSeekLLM",
        #"ollama": "rag_system.llm.ollama_llm.OllamaLLM",
    }
    
    @classmethod
    def create_llm(cls, config: LLMConfig) -> BaseLLM:
        """创建LLM实例"""
        provider = config.provider.lower()
        llm_class = cls._get_llm_class(provider)
        
        try:
            llm = llm_class(config)
            logger.info(f"创建LLM实例成功: {provider} - {config.model}")
            return llm
        except Exception as e:
            logger.error(f"创建LLM实例失败: {provider} - {str(e)}")
            raise ProcessingError(f"创建LLM实例失败: {str(e)}")
    
    @classmethod
    def _get_llm_class(cls, provider: str) -> Type[BaseLLM]:
        """获取LLM类，支持延迟加载"""
        if provider in cls._providers:
            return cls._providers[provider]
        
        if provider in cls._lazy_providers:
            module_path = cls._lazy_providers[provider]
            try:
                module_name, class_name = module_path.rsplit('.', 1)
                module = __import__(module_name, fromlist=[class_name])
                llm_class = getattr(module, class_name)
                cls._providers[provider] = llm_class
                logger.debug(f"延迟加载LLM提供商: {provider}")
                return llm_class
            except ImportError as e:
                logger.error(f"无法导入LLM提供商 {provider}: {str(e)}")
                raise UnsupportedProviderError(
                    f"LLM提供商 {provider} 不可用，可能缺少相关依赖", provider
                )
            except AttributeError as e:
                logger.error(f"LLM提供商 {provider} 类不存在: {str(e)}")
                raise UnsupportedProviderError(
                    f"LLM提供商 {provider} 实现不正确", provider
                )
        
        available_providers = cls.get_available_providers()
        raise UnsupportedProviderError(
            f"不支持的LLM提供商: {provider}. 支持的提供商: {', '.join(available_providers)}",
            provider
        )
    
    @classmethod
    def register_provider(cls, name: str, llm_class: Type[BaseLLM]):
        """注册新的LLM提供商"""
        cls._providers[name.lower()] = llm_class
        logger.info(f"注册LLM提供商: {name}")
    
    @classmethod
    def get_available_providers(cls) -> list:
        """获取可用的LLM提供商列表"""
        all_providers = set(cls._providers.keys())
        all_providers.update(cls._lazy_providers.keys())
        return sorted(list(all_providers))
    
    @classmethod
    def create_from_dict(cls, config_dict: dict) -> BaseLLM:
        """从字典配置创建LLM实例"""
        config = LLMConfig(**config_dict)
        return cls.create_llm(config)
    
    @classmethod
    def is_provider_available(cls, provider: str) -> bool:
        """检查提供商是否可用"""
        provider = provider.lower()
        
        if provider in cls._providers:
            return True
        
        if provider in cls._lazy_providers:
            try:
                cls._get_llm_class(provider)
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
            llm_class = cls._get_llm_class(provider)
            if hasattr(llm_class, 'get_provider_info'):
                return llm_class.get_provider_info()
            else:
                return {
                    'provider': provider,
                    'class': llm_class.__name__,
                    'module': llm_class.__module__
                }
        except Exception as e:
            logger.error(f"获取提供商信息失败 {provider}: {str(e)}")
            return None