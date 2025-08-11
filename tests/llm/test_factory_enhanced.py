"""
测试增强的LLM工厂类
"""
import pytest
from unittest.mock import Mock, patch

from rag_system.llm.factory import LLMFactory
from rag_system.llm.base import LLMConfig, BaseLLM
from rag_system.llm.mock_llm import MockLLM
from rag_system.llm.openai_llm import OpenAILLM
from rag_system.utils.exceptions import ProcessingError
from rag_system.utils.model_exceptions import UnsupportedProviderError


class TestLLMFactory:
    """测试LLM工厂类"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        # 重置工厂状态
        LLMFactory._providers = {
            "mock": MockLLM,
            "openai": OpenAILLM,
        }
    
    def test_create_mock_llm(self):
        """测试创建Mock LLM"""
        config = LLMConfig(provider="mock", model="test-model")
        llm = LLMFactory.create_llm(config)
        
        assert isinstance(llm, MockLLM)
        assert llm.config.provider == "mock"
        assert llm.config.model == "test-model"
    
    def test_create_openai_llm(self):
        """测试创建OpenAI LLM"""
        config = LLMConfig(
            provider="openai", 
            model="gpt-4",
            api_key="test-key"
        )
        llm = LLMFactory.create_llm(config)
        
        assert isinstance(llm, OpenAILLM)
        assert llm.config.provider == "openai"
        assert llm.config.model == "gpt-4"
    
    def test_create_siliconflow_llm_lazy_loading(self):
        """测试延迟加载SiliconFlow LLM"""
        config = LLMConfig(
            provider="siliconflow",
            model="Qwen/Qwen2-7B-Instruct",
            api_key="test-key"
        )
        
        # 确保SiliconFlow不在已加载的提供商中
        assert "siliconflow" not in LLMFactory._providers
        assert "siliconflow" in LLMFactory._lazy_providers
        
        llm = LLMFactory.create_llm(config)
        
        # 验证延迟加载成功
        assert "siliconflow" in LLMFactory._providers
        assert llm.config.provider == "siliconflow"
        assert llm.config.model == "Qwen/Qwen2-7B-Instruct"
    
    def test_case_insensitive_provider(self):
        """测试提供商名称大小写不敏感"""
        config = LLMConfig(provider="MOCK", model="test-model")
        llm = LLMFactory.create_llm(config)
        
        assert isinstance(llm, MockLLM)
    
    def test_unsupported_provider(self):
        """测试不支持的提供商"""
        config = LLMConfig(provider="unsupported", model="test-model")
        
        with pytest.raises(UnsupportedProviderError) as exc_info:
            LLMFactory.create_llm(config)
        
        assert "不支持的LLM提供商: unsupported" in str(exc_info.value)
        assert "支持的提供商:" in str(exc_info.value)
    
    def test_lazy_loading_import_error(self):
        """测试延迟加载时的导入错误"""
        # 添加一个不存在的提供商
        LLMFactory._lazy_providers["nonexistent"] = "nonexistent.module.NonexistentLLM"
        
        config = LLMConfig(provider="nonexistent", model="test-model")
        
        with pytest.raises(UnsupportedProviderError) as exc_info:
            LLMFactory.create_llm(config)
        
        assert "不可用，可能缺少相关依赖" in str(exc_info.value)
    
    def test_lazy_loading_attribute_error(self):
        """测试延迟加载时的属性错误"""
        # 模拟导入成功但类不存在的情况
        with patch('builtins.__import__') as mock_import:
            mock_module = Mock()
            mock_import.return_value = mock_module
            # 模拟getattr抛出AttributeError
            mock_module.__getattribute__ = Mock(side_effect=AttributeError("class not found"))
            
            LLMFactory._lazy_providers["badclass"] = "some.module.BadClass"
            config = LLMConfig(provider="badclass", model="test-model")
            
            with pytest.raises(UnsupportedProviderError) as exc_info:
                LLMFactory.create_llm(config)
            
            assert "实现不正确" in str(exc_info.value)
    
    def test_create_llm_initialization_error(self):
        """测试LLM初始化错误"""
        # 创建一个会抛出异常的配置
        config = LLMConfig(provider="openai", model="gpt-4")  # 缺少api_key
        
        with pytest.raises(ProcessingError) as exc_info:
            LLMFactory.create_llm(config)
        
        assert "创建LLM实例失败" in str(exc_info.value)
    
    def test_register_provider(self):
        """测试注册新的提供商"""
        class CustomLLM(BaseLLM):
            def __init__(self, config):
                super().__init__(config)
            
            async def generate(self, messages, **kwargs):
                pass
            
            async def generate_text(self, prompt, **kwargs):
                pass
            
            def generate_with_context(self, question, context, **kwargs):
                pass
            
            def get_model_info(self):
                return {"provider": "custom"}
            
            def health_check(self):
                return True
        
        LLMFactory.register_provider("custom", CustomLLM)
        
        assert "custom" in LLMFactory._providers
        assert LLMFactory._providers["custom"] == CustomLLM
        
        # 测试使用注册的提供商
        config = LLMConfig(provider="custom", model="test-model")
        llm = LLMFactory.create_llm(config)
        assert isinstance(llm, CustomLLM)
    
    def test_get_available_providers(self):
        """测试获取可用提供商列表"""
        providers = LLMFactory.get_available_providers()
        
        # 应该包含已加载和延迟加载的提供商
        assert "mock" in providers
        assert "openai" in providers
        assert "siliconflow" in providers
        assert "modelscope" in providers
        assert "deepseek" in providers
        assert "ollama" in providers
        
        # 应该是排序的
        assert providers == sorted(providers)
    
    def test_create_from_dict(self):
        """测试从字典创建LLM"""
        config_dict = {
            "provider": "mock",
            "model": "test-model",
            "temperature": 0.5,
            "max_tokens": 500
        }
        
        llm = LLMFactory.create_from_dict(config_dict)
        
        assert isinstance(llm, MockLLM)
        assert llm.config.provider == "mock"
        assert llm.config.model == "test-model"
        assert llm.config.temperature == 0.5
        assert llm.config.max_tokens == 500
    
    def test_is_provider_available(self):
        """测试检查提供商是否可用"""
        # 已加载的提供商
        assert LLMFactory.is_provider_available("mock") is True
        assert LLMFactory.is_provider_available("openai") is True
        
        # 延迟加载的提供商
        assert LLMFactory.is_provider_available("siliconflow") is True
        
        # 不存在的提供商
        assert LLMFactory.is_provider_available("nonexistent") is False
        
        # 大小写不敏感
        assert LLMFactory.is_provider_available("MOCK") is True
    
    def test_is_provider_available_with_import_error(self):
        """测试提供商不可用时的检查"""
        # 添加一个会导致导入错误的提供商
        LLMFactory._lazy_providers["broken"] = "broken.module.BrokenLLM"
        
        assert LLMFactory.is_provider_available("broken") is False
    
    def test_get_provider_info(self):
        """测试获取提供商信息"""
        # 测试已加载的提供商
        info = LLMFactory.get_provider_info("mock")
        assert info is not None
        assert info["provider"] == "mock"
        assert "class" in info
        assert "module" in info
        
        # 测试延迟加载的提供商
        info = LLMFactory.get_provider_info("siliconflow")
        assert info is not None
        assert info["provider"] == "siliconflow"
        
        # 测试不存在的提供商
        info = LLMFactory.get_provider_info("nonexistent")
        assert info is None
    
    def test_get_provider_info_with_custom_method(self):
        """测试带有自定义get_provider_info方法的提供商"""
        class CustomLLMWithInfo(BaseLLM):
            def __init__(self, config):
                super().__init__(config)
            
            @classmethod
            def get_provider_info(cls):
                return {
                    "provider": "custom_with_info",
                    "description": "Custom LLM with provider info",
                    "version": "1.0.0"
                }
            
            async def generate(self, messages, **kwargs):
                pass
            
            async def generate_text(self, prompt, **kwargs):
                pass
            
            def generate_with_context(self, question, context, **kwargs):
                pass
            
            def get_model_info(self):
                return {"provider": "custom_with_info"}
            
            def health_check(self):
                return True
        
        LLMFactory.register_provider("custom_with_info", CustomLLMWithInfo)
        
        info = LLMFactory.get_provider_info("custom_with_info")
        assert info is not None
        assert info["provider"] == "custom_with_info"
        assert info["description"] == "Custom LLM with provider info"
        assert info["version"] == "1.0.0"
    
    def test_caching_of_lazy_loaded_providers(self):
        """测试延迟加载提供商的缓存"""
        # 第一次加载
        config1 = LLMConfig(provider="siliconflow", model="test1", api_key="key1")
        llm1 = LLMFactory.create_llm(config1)
        
        # 验证已缓存
        assert "siliconflow" in LLMFactory._providers
        
        # 第二次加载应该使用缓存
        config2 = LLMConfig(provider="siliconflow", model="test2", api_key="key2")
        llm2 = LLMFactory.create_llm(config2)
        
        # 两个实例应该是同一个类
        assert type(llm1) == type(llm2)
        assert llm1.config.model != llm2.config.model  # 但配置不同