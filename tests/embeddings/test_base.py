"""
测试嵌入模型基础类
"""
import pytest
from unittest.mock import Mock, patch
from typing import List, Dict, Any

from rag_system.embeddings.base import BaseEmbedding, EmbeddingConfig, EmbeddingResult


class MockEmbedding(BaseEmbedding):
    """用于测试的Mock嵌入模型实现"""
    
    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        self.dimension = 768
        self.should_fail = False
    
    async def initialize(self) -> None:
        if self.should_fail:
            raise Exception("Mock initialization failed")
        self._initialized = True
    
    async def embed_text(self, text: str) -> List[float]:
        if self.should_fail:
            raise Exception("Mock embedding failed")
        return [0.1] * self.dimension
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if self.should_fail:
            raise Exception("Mock batch embedding failed")
        return [[0.1] * self.dimension for _ in texts]
    
    async def embed_query(self, query: str) -> List[float]:
        if self.should_fail:
            raise Exception("Mock query embedding failed")
        return [0.2] * self.dimension
    
    def get_embedding_dimension(self) -> int:
        return self.dimension
    
    async def cleanup(self) -> None:
        self._initialized = False
    
    def embed(self, text: str) -> List[float]:
        if self.should_fail:
            raise Exception("Mock sync embedding failed")
        return [0.1] * self.dimension
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if self.should_fail:
            raise Exception("Mock sync batch embedding failed")
        return [[0.1] * self.dimension for _ in texts]
    
    def get_dimension(self) -> int:
        return self.dimension
    
    def health_check(self) -> bool:
        return not self.should_fail


class TestEmbeddingConfig:
    """测试嵌入配置类"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = EmbeddingConfig()
        
        assert config.provider == "openai"
        assert config.model == "text-embedding-ada-002"
        assert config.max_tokens == 8192
        assert config.batch_size == 100
        assert config.timeout == 60
        assert config.retry_attempts == 3
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = EmbeddingConfig(
            provider="siliconflow",
            model="bge-large-zh",
            api_key="test-key",
            base_url="https://api.test.com",
            batch_size=50,
            dimensions=1024,
            timeout=30
        )
        
        assert config.provider == "siliconflow"
        assert config.model == "bge-large-zh"
        assert config.api_key == "test-key"
        assert config.base_url == "https://api.test.com"
        assert config.batch_size == 50
        assert config.dimensions == 1024
        assert config.timeout == 30


class TestEmbeddingResult:
    """测试嵌入结果类"""
    
    def test_basic_result(self):
        """测试基础结果"""
        embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        usage = {"total_tokens": 10}
        
        result = EmbeddingResult(
            embeddings=embeddings,
            model="test-model",
            usage=usage,
            processing_time=1.5
        )
        
        assert result.embeddings == embeddings
        assert result.model == "test-model"
        assert result.usage == usage
        assert result.processing_time == 1.5


class TestBaseEmbedding:
    """测试嵌入模型基础类"""
    
    @pytest.fixture
    def config(self):
        """测试配置"""
        return EmbeddingConfig(provider="test", model="test-embedding")
    
    @pytest.fixture
    def mock_embedding(self, config):
        """Mock嵌入模型实例"""
        return MockEmbedding(config)
    
    def test_initialization(self, mock_embedding, config):
        """测试初始化"""
        assert mock_embedding.config == config
        assert not mock_embedding.is_initialized()
    
    @pytest.mark.asyncio
    async def test_initialize(self, mock_embedding):
        """测试初始化方法"""
        await mock_embedding.initialize()
        assert mock_embedding.is_initialized()
    
    @pytest.mark.asyncio
    async def test_cleanup(self, mock_embedding):
        """测试清理方法"""
        await mock_embedding.initialize()
        assert mock_embedding.is_initialized()
        
        await mock_embedding.cleanup()
        assert not mock_embedding.is_initialized()
    
    @pytest.mark.asyncio
    async def test_embed_text(self, mock_embedding):
        """测试单文本嵌入"""
        embedding = await mock_embedding.embed_text("test text")
        
        assert isinstance(embedding, list)
        assert len(embedding) == 768
        assert all(isinstance(x, float) for x in embedding)
    
    @pytest.mark.asyncio
    async def test_embed_texts(self, mock_embedding):
        """测试批量文本嵌入"""
        texts = ["text1", "text2", "text3"]
        embeddings = await mock_embedding.embed_texts(texts)
        
        assert isinstance(embeddings, list)
        assert len(embeddings) == 3
        assert all(len(emb) == 768 for emb in embeddings)
    
    @pytest.mark.asyncio
    async def test_embed_query(self, mock_embedding):
        """测试查询嵌入"""
        embedding = await mock_embedding.embed_query("test query")
        
        assert isinstance(embedding, list)
        assert len(embedding) == 768
        assert embedding[0] == 0.2  # 查询嵌入使用不同的值
    
    def test_get_embedding_dimension(self, mock_embedding):
        """测试获取嵌入维度"""
        dimension = mock_embedding.get_embedding_dimension()
        assert dimension == 768
    
    def test_sync_embed(self, mock_embedding):
        """测试同步嵌入方法"""
        embedding = mock_embedding.embed("test text")
        
        assert isinstance(embedding, list)
        assert len(embedding) == 768
    
    def test_sync_embed_batch(self, mock_embedding):
        """测试同步批量嵌入方法"""
        texts = ["text1", "text2"]
        embeddings = mock_embedding.embed_batch(texts)
        
        assert isinstance(embeddings, list)
        assert len(embeddings) == 2
        assert all(len(emb) == 768 for emb in embeddings)
    
    def test_get_dimension(self, mock_embedding):
        """测试获取维度（兼容方法）"""
        dimension = mock_embedding.get_dimension()
        assert dimension == 768
    
    def test_health_check(self, mock_embedding):
        """测试健康检查"""
        assert mock_embedding.health_check() is True
        
        mock_embedding.should_fail = True
        assert mock_embedding.health_check() is False
    
    def test_validate_text(self, mock_embedding):
        """测试文本验证"""
        # 有效文本
        assert mock_embedding._validate_text("valid text") is True
        
        # 无效文本
        assert mock_embedding._validate_text("") is False
        assert mock_embedding._validate_text("   ") is False
        assert mock_embedding._validate_text(None) is False
        assert mock_embedding._validate_text(123) is False
    
    def test_validate_texts(self, mock_embedding):
        """测试文本列表验证"""
        # 有效文本列表
        assert mock_embedding._validate_texts(["text1", "text2"]) is True
        
        # 无效文本列表
        assert mock_embedding._validate_texts([]) is False
        assert mock_embedding._validate_texts(None) is False
        assert mock_embedding._validate_texts("not a list") is False
        assert mock_embedding._validate_texts(["valid", ""]) is False
    
    def test_chunk_texts(self, mock_embedding):
        """测试文本分块"""
        mock_embedding.config.batch_size = 2
        texts = ["text1", "text2", "text3", "text4", "text5"]
        
        chunks = mock_embedding._chunk_texts(texts)
        
        assert len(chunks) == 3
        assert chunks[0] == ["text1", "text2"]
        assert chunks[1] == ["text3", "text4"]
        assert chunks[2] == ["text5"]
    
    @pytest.mark.asyncio
    async def test_get_model_info(self, mock_embedding):
        """测试获取模型信息"""
        info = await mock_embedding.get_model_info()
        
        assert isinstance(info, dict)
        assert info["provider"] == "test"
        assert info["model"] == "test-embedding"
        assert info["dimensions"] == 768
        assert "max_tokens" in info
        assert "batch_size" in info
    
    @pytest.mark.asyncio
    async def test_error_handling(self, mock_embedding):
        """测试错误处理"""
        mock_embedding.should_fail = True
        
        with pytest.raises(Exception, match="Mock initialization failed"):
            await mock_embedding.initialize()
        
        with pytest.raises(Exception, match="Mock embedding failed"):
            await mock_embedding.embed_text("test")
        
        with pytest.raises(Exception, match="Mock batch embedding failed"):
            await mock_embedding.embed_texts(["test"])
        
        with pytest.raises(Exception, match="Mock query embedding failed"):
            await mock_embedding.embed_query("test")
        
        with pytest.raises(Exception, match="Mock sync embedding failed"):
            mock_embedding.embed("test")
        
        with pytest.raises(Exception, match="Mock sync batch embedding failed"):
            mock_embedding.embed_batch(["test"])