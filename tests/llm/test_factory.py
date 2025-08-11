"""
LLM工厂测试
"""
import pytest

from rag_system.llm.factory import LLMFactory
from rag_system.llm.base import LLMConfig, BaseLLM
from rag_system.llm.mock_llm import MockLLM
from rag_system.llm.openai_llm import OpenAILLM
from rag_system.utils.exceptions import ProcessingError


class TestLLMFactory:
    """LLM工厂测试"""
    
    def test_create_mock_llm(self):
        """测试创建Mock LLM"""
        config = LLMConfig(
            provider="mock",
            model="test-model"
        )
        
        llm = LLMFactory.create_llm(config)
        
        assert isinstance(llm, MockLLM)
        assert llm.config.provider == "mock"
        assert llm.config.model == "test-model"
    
    def test_create_openai_llm(self):
        """测试创建OpenAI LLM"""
        config = LLMConfig(
            provider="openai",
            model="gpt-3.5-turbo",
            api_key="test-key"
        )
        
        llm = LLMFactory.create_llm(config)
        
        assert isinstance(llm, OpenAILLM)
        assert llm.config.provider == "openai"
        assert llm.config.model == "gpt-3.5-turbo"
    
    def test_create_llm_case_insensitive(self):
        """测试大小写不敏感的提供商名称"""
        config = LLMConfig(
            provider="MOCK",
            model="test-model"
        )
        
        llm = LLMFactory.create_llm(config)
        
        assert isinstance(llm, MockLLM)
    
    def test_create_llm_unsupported_provider(self):
        """测试不支持的提供商"""
        config = LLMConfig(
            provider="unsupported",
            model="test-model"
        )
        
        with pytest.raises(ProcessingError) as exc_info:
            LLMFactory.create_llm(config)
        
        assert "不支持的LLM提供商" in str(exc_info.value)
        assert "unsupported" in str(exc_info.value)
    
    def test_get_available_providers(self):
        """测试获取可用提供商"""
        providers = LLMFactory.get_available_providers()
        
        assert isinstance(providers, list)
        assert "mock" in providers
        assert "openai" in providers
        assert len(providers) >= 2
    
    def test_register_custom_provider(self):
        """测试注册自定义提供商"""
        # 创建一个自定义LLM类
        class CustomLLM(BaseLLM):
            async def generate(self, messages, **kwargs):
                return None
            
            async def generate_text(self, prompt, **kwargs):
                return "custom response"
        
        # 注册自定义提供商
        LLMFactory.register_provider("custom", CustomLLM)
        
        # 验证注册成功
        providers = LLMFactory.get_available_providers()
        assert "custom" in providers
        
        # 测试创建自定义LLM
        config = LLMConfig(
            provider="custom",
            model="custom-model"
        )
        
        llm = LLMFactory.create_llm(config)
        assert isinstance(llm, CustomLLM)
    
    def test_create_from_dict(self):
        """测试从字典创建LLM"""
        config_dict = {
            "provider": "mock",
            "model": "test-model",
            "temperature": 0.8,
            "max_tokens": 500
        }
        
        llm = LLMFactory.create_from_dict(config_dict)
        
        assert isinstance(llm, MockLLM)
        assert llm.config.provider == "mock"
        assert llm.config.model == "test-model"
        assert llm.config.temperature == 0.8
        assert llm.config.max_tokens == 500
    
    def test_create_from_dict_invalid_config(self):
        """测试从无效字典创建LLM"""
        config_dict = {
            "provider": "mock",
            # 缺少必需的model字段
        }
        
        with pytest.raises(Exception):  # Pydantic验证错误
            LLMFactory.create_from_dict(config_dict)
    
    def test_create_llm_with_all_parameters(self):
        """测试创建包含所有参数的LLM"""
        config = LLMConfig(
            provider="mock",
            model="advanced-model",
            api_key="test-api-key",
            api_base="https://api.test.com",
            temperature=0.9,
            max_tokens=2000,
            timeout=60
        )
        
        llm = LLMFactory.create_llm(config)
        
        assert isinstance(llm, MockLLM)
        assert llm.config.provider == "mock"
        assert llm.config.model == "advanced-model"
        assert llm.config.api_key == "test-api-key"
        assert llm.config.api_base == "https://api.test.com"
        assert llm.config.temperature == 0.9
        assert llm.config.max_tokens == 2000
        assert llm.config.timeout == 60
    
    def test_factory_state_isolation(self):
        """测试工厂状态隔离"""
        # 创建两个不同的LLM实例
        config1 = LLMConfig(provider="mock", model="model1")
        config2 = LLMConfig(provider="mock", model="model2")
        
        llm1 = LLMFactory.create_llm(config1)
        llm2 = LLMFactory.create_llm(config2)
        
        # 验证实例是独立的
        assert llm1 is not llm2
        assert llm1.config.model == "model1"
        assert llm2.config.model == "model2"
    
    def test_provider_name_normalization(self):
        """测试提供商名称标准化"""
        test_cases = [
            ("Mock", MockLLM),
            ("MOCK", MockLLM),
            ("mock", MockLLM),
            ("OpenAI", OpenAILLM),
            ("OPENAI", OpenAILLM),
            ("openai", OpenAILLM)
        ]
        
        for provider_name, expected_class in test_cases:
            config = LLMConfig(
                provider=provider_name,
                model="test-model"
            )
            
            llm = LLMFactory.create_llm(config)
            assert isinstance(llm, expected_class)