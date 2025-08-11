"""
测试增强的嵌入模型工厂类
"""
import pytest
from unittest.mock import Mock, patch

from rag_system.embeddings.factory import EmbeddingFactory
from rag_system.embeddings.base import EmbeddingConfig, BaseEmbedding
from rag_system.embeddings.mock_embedding import MockEmbedding
from rag_system.embeddings.openai_embedding import OpenAIEmbedding
from rag_system.utils.exceptions import ProcessingError
from rag_system.utils.model_exceptions import UnsupportedProviderError


class TestEmbeddingFactory:
    """测试嵌入模型工厂类"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        # 重置工厂状态
        EmbeddingFactory._providers = {
            "mock": MockEmbedding,
            "openai": OpenAIEmbedding,
        }
        # 重置延迟加载提供商
        EmbeddingFactory._lazy_providers = {
            "siliconflow": "rag_system.embeddings.siliconflow_embedding.SiliconFlowEmbedding",
            # 为将来的平台预留
            "modelscope": "rag_system.embeddings.modelscope_embedding.ModelScopeEmbedding",
            "deepseek": "rag_system.embeddings.deepseek_embedding.DeepSeekEmbedding",
            "ollama": "rag_system.embeddings.ollama_embedding.OllamaEmbedding",
        }
    
    def test_create_mock_embedding(self):
        """测试创建Mock嵌入模型"""
        config = EmbeddingConfig(provider="mock", model="test-model")
        embedding = EmbeddingFactory.create_embedding(config)
        
        assert isinstance(embedding, MockEmbedding)
        assert embedding.config.provider == "mock"
        assert embedding.config.model == "test-model"
    
    def test_create_openai_embedding(self):
        """测试创建OpenAI嵌入模型"""
        config = EmbeddingConfig(
            provider="openai", 
            model="text-embedding-ada-002",
            api_key="test-key"
        )
        embedding = EmbeddingFactory.create_embedding(config)
        
        assert isinstance(embedding, OpenAIEmbedding)
        assert embedding.config.provider == "openai"
        assert embedding.config.model == "text-embedding-ada-002"
    
    def test_create_siliconflow_embedding_lazy_loading(self):
        """测试延迟加载SiliconFlow嵌入模型"""
        config = EmbeddingConfig(
            provider="siliconflow",
            model="BAAI/bge-large-zh-v1.5",
            api_key="test-key"
        )
        
        # 确保SiliconFlow不在已加载的提供商中
        assert "siliconflow" not in EmbeddingFactory._providers
        assert "siliconflow" in EmbeddingFactory._lazy_providers
        
        embedding = EmbeddingFactory.create_embedding(config)
        
        # 验证延迟加载成功
        assert "siliconflow" in EmbeddingFactory._providers
        assert embedding.config.provider == "siliconflow"
        assert embedding.config.model == "BAAI/bge-large-zh-v1.5"
    
    def test_case_insensitive_provider(self):
        """测试提供商名称大小写不敏感"""
        config = EmbeddingConfig(provider="MOCK", model="test-model")
        embedding = EmbeddingFactory.create_embedding(config)
        
        assert isinstance(embedding, MockEmbedding)
    
    def test_unsupported_provider(self):
        """测试不支持的提供商"""
        config = EmbeddingConfig(provider="unsupported", model="test-model")
        
        with pytest.raises(UnsupportedProviderError) as exc_info:
            EmbeddingFactory.create_embedding(config)
        
        assert "不支持的嵌入模型提供商: unsupported" in str(exc_info.value)
        assert "支持的提供商:" in str(exc_info.value)
    
    def test_lazy_loading_import_error(self):
        """测试延迟加载时的导入错误"""
        # 添加一个不存在的提供商
        EmbeddingFactory._lazy_providers["nonexistent"] = "nonexistent.module.NonexistentEmbedding"
        
        config = EmbeddingConfig(provider="nonexistent", model="test-model")
        
        with pytest.raises(UnsupportedProviderError) as exc_info:
            EmbeddingFactory.create_embedding(config)
        
        assert "不可用，可能缺少相关依赖" in str(exc_info.value)
    
    def test_lazy_loading_attribute_error(self):
        """测试延迟加载时的属性错误"""
        # 添加一个不存在的类路径
        EmbeddingFactory._lazy_providers["badclass"] = "rag_system.embeddings.nonexistent.NonexistentClass"
        
        config = EmbeddingConfig(provider="badclass")
        
        with pytest.raises(UnsupportedProviderError) as exc_info:
            EmbeddingFactory.create_embedding(config)
        
        # 应该是导入错误，因为模块不存在
        assert "不可用，可能缺少相关依赖" in str(exc_info.value)
    
    def test_create_embedding_initialization_error(self):
        """测试嵌入模型初始化错误"""
        # 创建一个会抛出异常的Mock嵌入类
        class FailingEmbedding(BaseEmbedding):
            def __init__(self, config):
                raise ValueError("Initialization failed")
        
        # 临时注册失败的嵌入类
        EmbeddingFactory.register_provider("failing", FailingEmbedding)
        
        config = EmbeddingConfig(provider="failing")
        
        with pytest.raises(ProcessingError) as exc_info:
            EmbeddingFactory.create_embedding(config)
        
        assert "创建嵌入模型实例失败" in str(exc_info.value)
    
    def test_register_provider(self):
        """测试注册新的提供商"""
        class CustomEmbedding(BaseEmbedding):
            def __init__(self, config):
                super().__init__(config)
            
            async def initialize(self):
                pass
            
            async def embed_text(self, text):
                return [0.1] * 384
            
            async def embed_texts(self, texts):
                return [[0.1] * 384 for _ in texts]
            
            async def embed_query(self, query):
                return [0.1] * 384
            
            def get_embedding_dimension(self):
                return 384
            
            async def cleanup(self):
                pass
            
            def embed(self, text):
                return [0.1] * 384
            
            def embed_batch(self, texts):
                return [[0.1] * 384 for _ in texts]
            
            def get_dimension(self):
                return 384
            
            def health_check(self):
                return True
        
        EmbeddingFactory.register_provider("custom", CustomEmbedding)
        
        assert "custom" in EmbeddingFactory._providers
        assert EmbeddingFactory._providers["custom"] == CustomEmbedding
        
        # 测试使用注册的提供商
        config = EmbeddingConfig(provider="custom", model="test-model")
        embedding = EmbeddingFactory.create_embedding(config)
        assert isinstance(embedding, CustomEmbedding)
    
    def test_register_invalid_provider(self):
        """测试注册无效的提供商"""
        class InvalidEmbedding:
            pass
        
        with pytest.raises(ValueError, match="嵌入类必须继承自BaseEmbedding"):
            EmbeddingFactory.register_provider("invalid", InvalidEmbedding)
    
    def test_get_available_providers(self):
        """测试获取可用提供商列表"""
        providers = EmbeddingFactory.get_available_providers()
        
        # 应该包含已加载和延迟加载的提供商
        assert "mock" in providers
        assert "openai" in providers
        assert "siliconflow" in providers
        #assert "modelscope" in providers
        #assert "deepseek" in providers
        #assert "ollama" in providers
        
        # 应该是排序的
        assert providers == sorted(providers)
    
    def test_create_from_config_dict(self):
        """测试从字典创建嵌入模型"""
        config_dict = {
            "provider": "mock",
            "model": "test-model",
            "dimensions": 512,
            "batch_size": 50
        }
        
        embedding = EmbeddingFactory.create_from_config_dict(config_dict)
        
        assert isinstance(embedding, MockEmbedding)
        assert embedding.config.provider == "mock"
        assert embedding.config.model == "test-model"
        assert embedding.config.dimensions == 512
        assert embedding.config.batch_size == 50
    
    def test_is_provider_available(self):
        """测试检查提供商是否可用"""
        # 已加载的提供商
        assert EmbeddingFactory.is_provider_available("mock") is True
        assert EmbeddingFactory.is_provider_available("openai") is True
        
        # 延迟加载的提供商
        assert EmbeddingFactory.is_provider_available("siliconflow") is True
        
        # 不存在的提供商
        assert EmbeddingFactory.is_provider_available("nonexistent") is False
        
        # 大小写不敏感
        assert EmbeddingFactory.is_provider_available("MOCK") is True
    
    def test_is_provider_available_with_import_error(self):
        """测试提供商不可用时的检查"""
        # 添加一个会导致导入错误的提供商
        EmbeddingFactory._lazy_providers["broken"] = "broken.module.BrokenEmbedding"
        
        assert EmbeddingFactory.is_provider_available("broken") is False
    
    def test_get_provider_info(self):
        """测试获取提供商信息"""
        # 测试已加载的提供商
        info = EmbeddingFactory.get_provider_info("mock")
        assert info is not None
        assert info["provider"] == "mock"
        assert "class" in info
        assert "module" in info
        
        # 测试延迟加载的提供商
        info = EmbeddingFactory.get_provider_info("siliconflow")
        assert info is not None
        assert info["provider"] == "siliconflow"
        
        # 测试不存在的提供商
        info = EmbeddingFactory.get_provider_info("nonexistent")
        assert info is None
    
    def test_get_provider_info_with_custom_method(self):
        """测试带有自定义get_provider_info方法的提供商"""
        class CustomEmbeddingWithInfo(BaseEmbedding):
            def __init__(self, config):
                super().__init__(config)
            
            @classmethod
            def get_provider_info(cls):
                return {
                    "provider": "custom_with_info",
                    "description": "Custom embedding with provider info",
                    "version": "1.0.0"
                }
            
            async def initialize(self):
                pass
            
            async def embed_text(self, text):
                return [0.1] * 384
            
            async def embed_texts(self, texts):
                return [[0.1] * 384 for _ in texts]
            
            async def embed_query(self, query):
                return [0.1] * 384
            
            def get_embedding_dimension(self):
                return 384
            
            async def cleanup(self):
                pass
            
            def embed(self, text):
                return [0.1] * 384
            
            def embed_batch(self, texts):
                return [[0.1] * 384 for _ in texts]
            
            def get_dimension(self):
                return 384
            
            def health_check(self):
                return True
        
        EmbeddingFactory.register_provider("custom_with_info", CustomEmbeddingWithInfo)
        
        info = EmbeddingFactory.get_provider_info("custom_with_info")
        assert info is not None
        assert info["provider"] == "custom_with_info"
        assert info["description"] == "Custom embedding with provider info"
        assert info["version"] == "1.0.0"
    
    def test_caching_of_lazy_loaded_providers(self):
        """测试延迟加载提供商的缓存"""
        # 第一次加载
        config1 = EmbeddingConfig(provider="siliconflow", model="test1", api_key="key1")
        embedding1 = EmbeddingFactory.create_embedding(config1)
        
        # 验证已缓存
        assert "siliconflow" in EmbeddingFactory._providers
        
        # 第二次加载应该使用缓存
        config2 = EmbeddingConfig(provider="siliconflow", model="test2", api_key="key2")
        embedding2 = EmbeddingFactory.create_embedding(config2)
        
        # 两个实例应该是同一个类
        assert type(embedding1) == type(embedding2)
        assert embedding1.config.model != embedding2.config.model  # 但配置不同