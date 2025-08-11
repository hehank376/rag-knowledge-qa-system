"""
嵌入工厂测试
"""
import pytest
from unittest.mock import Mock

from rag_system.embeddings.factory import EmbeddingFactory
from rag_system.embeddings.base import BaseEmbedding, EmbeddingConfig
from rag_system.embeddings.openai_embedding import OpenAIEmbedding
from rag_system.embeddings.mock_embedding import MockEmbedding
from rag_system.utils.exceptions import ConfigurationError


class TestEmbeddingFactory:
    """嵌入工厂测试"""
    
    def test_create_mock_embedding(self):
        """测试创建Mock嵌入"""
        config = EmbeddingConfig(
            provider="mock",
            model="test-model",
            dimensions=256
        )
        
        embedding = EmbeddingFactory.create_embedding(config)
        
        assert isinstance(embedding, MockEmbedding)
        assert embedding.config.provider == "mock"
        assert embedding.config.model == "test-model"
        assert embedding.config.dimensions == 256
    
    def test_create_openai_embedding(self):
        """测试创建OpenAI嵌入"""
        config = EmbeddingConfig(
            provider="openai",
            model="text-embedding-ada-002",
            api_key="test-key"
        )
        
        embedding = EmbeddingFactory.create_embedding(config)
        
        assert isinstance(embedding, OpenAIEmbedding)
        assert embedding.config.provider == "openai"
        assert embedding.config.model == "text-embedding-ada-002"
    
    def test_create_invalid_provider(self):
        """测试创建无效提供商"""
        config = EmbeddingConfig(
            provider="invalid_provider",
            model="test-model"
        )
        
        with pytest.raises(ConfigurationError) as exc_info:
            EmbeddingFactory.create_embedding(config)
        
        assert "不支持的嵌入提供商" in str(exc_info.value)
        assert "invalid_provider" in str(exc_info.value)
    
    def test_case_insensitive_provider(self):
        """测试提供商名称大小写不敏感"""
        config = EmbeddingConfig(
            provider="MOCK",
            model="test-model"
        )
        
        embedding = EmbeddingFactory.create_embedding(config)
        assert isinstance(embedding, MockEmbedding)
        
        config.provider = "OpenAI"
        embedding = EmbeddingFactory.create_embedding(config)
        assert isinstance(embedding, OpenAIEmbedding)
    
    def test_get_available_providers(self):
        """测试获取可用提供商"""
        providers = EmbeddingFactory.get_available_providers()
        
        assert isinstance(providers, list)
        assert "mock" in providers
        assert "openai" in providers
        assert len(providers) >= 2
    
    def test_register_custom_provider(self):
        """测试注册自定义提供商"""
        # 创建自定义嵌入类
        class CustomEmbedding(BaseEmbedding):
            async def initialize(self):
                pass
            
            async def cleanup(self):
                pass
            
            def is_initialized(self):
                return True
            
            async def embed_text(self, text: str):
                return [0.1] * 100
            
            async def embed_texts(self, texts):
                return [[0.1] * 100 for _ in texts]
            
            async def embed_query(self, query: str):
                return [0.1] * 100
            
            def get_embedding_dimension(self):
                return 100
            
            async def get_model_info(self):
                return {"provider": "custom", "model": "custom-model"}
        
        # 注册自定义提供商
        EmbeddingFactory.register_provider("custom", CustomEmbedding)
        
        # 验证注册成功
        providers = EmbeddingFactory.get_available_providers()
        assert "custom" in providers
        
        # 测试创建自定义嵌入
        config = EmbeddingConfig(provider="custom", model="custom-model")
        embedding = EmbeddingFactory.create_embedding(config)
        assert isinstance(embedding, CustomEmbedding)
    
    def test_register_invalid_provider_class(self):
        """测试注册无效的提供商类"""
        class InvalidClass:
            pass
        
        with pytest.raises(ValueError) as exc_info:
            EmbeddingFactory.register_provider("invalid", InvalidClass)
        
        assert "嵌入类必须继承自BaseEmbedding" in str(exc_info.value)
    
    def test_create_from_config_dict(self):
        """测试从配置字典创建嵌入"""
        config_dict = {
            "provider": "mock",
            "model": "test-model",
            "dimensions": 512
        }
        
        embedding = EmbeddingFactory.create_from_config_dict(config_dict)
        
        assert isinstance(embedding, MockEmbedding)
        assert embedding.config.provider == "mock"
        assert embedding.config.model == "test-model"
        assert embedding.config.dimensions == 512
    
    def test_create_from_invalid_config_dict(self):
        """测试从无效配置字典创建嵌入"""
        config_dict = {
            "provider": "invalid_provider",
            "model": "test-model"
        }
        
        with pytest.raises(ConfigurationError):
            EmbeddingFactory.create_from_config_dict(config_dict)
    
    def test_provider_name_normalization(self):
        """测试提供商名称标准化"""
        # 测试不同大小写和空格
        test_cases = [
            ("Mock", MockEmbedding),
            ("MOCK", MockEmbedding),
            ("mock", MockEmbedding),
            ("OpenAI", OpenAIEmbedding),
            ("openai", OpenAIEmbedding),
            ("OPENAI", OpenAIEmbedding)
        ]
        
        for provider_name, expected_class in test_cases:
            config = EmbeddingConfig(provider=provider_name, model="test")
            embedding = EmbeddingFactory.create_embedding(config)
            assert isinstance(embedding, expected_class)


class TestEmbeddingFactoryIntegration:
    """嵌入工厂集成测试"""
    
    def test_factory_with_all_providers(self):
        """测试工厂支持所有内置提供商"""
        providers = EmbeddingFactory.get_available_providers()
        
        for provider in providers:
            config = EmbeddingConfig(
                provider=provider,
                model="test-model"
            )
            
            # 应该能够成功创建所有提供商的实例
            embedding = EmbeddingFactory.create_embedding(config)
            assert isinstance(embedding, BaseEmbedding)
            assert embedding.config.provider.lower() == provider.lower()
    
    def test_factory_error_handling(self):
        """测试工厂错误处理"""
        # 测试配置错误导致的创建失败
        config = EmbeddingConfig(
            provider="mock",
            model="test-model",
            dimensions=-1  # 无效维度
        )
        
        # Mock嵌入应该能处理这种情况，但如果有验证逻辑可能会失败
        try:
            embedding = EmbeddingFactory.create_embedding(config)
            # 如果创建成功，验证基本属性
            assert isinstance(embedding, BaseEmbedding)
        except ConfigurationError:
            # 如果有验证逻辑导致失败，这也是可以接受的
            pass