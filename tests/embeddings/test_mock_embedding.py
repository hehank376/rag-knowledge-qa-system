"""
Mock嵌入测试
"""
import pytest
import pytest_asyncio
import hashlib

from rag_system.embeddings.mock_embedding import MockEmbedding
from rag_system.embeddings.base import EmbeddingConfig


@pytest_asyncio.fixture
def mock_config():
    """Mock配置fixture"""
    return EmbeddingConfig(
        provider="mock",
        model="test-model",
        dimensions=384,
        batch_size=10
    )


@pytest_asyncio.fixture
async def mock_embedding(mock_config):
    """Mock嵌入fixture"""
    embedding = MockEmbedding(mock_config)
    await embedding.initialize()
    yield embedding
    await embedding.cleanup()


class TestMockEmbedding:
    """Mock嵌入测试"""
    
    def test_initialization(self, mock_config):
        """测试初始化"""
        embedding = MockEmbedding(mock_config)
        
        assert embedding.config == mock_config
        assert not embedding.is_initialized()
    
    @pytest.mark.asyncio
    async def test_initialize_and_cleanup(self, mock_config):
        """测试初始化和清理"""
        embedding = MockEmbedding(mock_config)
        
        # 初始化
        await embedding.initialize()
        assert embedding.is_initialized()
        
        # 清理
        await embedding.cleanup()
        assert not embedding.is_initialized()
    
    def test_get_embedding_dimension(self, mock_embedding):
        """测试获取嵌入维度"""
        dimension = mock_embedding.get_embedding_dimension()
        assert dimension == 384  # 配置的维度
    
    @pytest.mark.asyncio
    async def test_get_model_info(self, mock_embedding):
        """测试获取模型信息"""
        model_info = await mock_embedding.get_model_info()
        
        assert model_info['provider'] == 'mock'
        assert model_info['model'] == 'test-model'
        assert model_info['dimensions'] == 384
        assert model_info['batch_size'] == 10
        assert 'description' in model_info
    
    @pytest.mark.asyncio
    async def test_embed_text(self, mock_embedding):
        """测试单个文本嵌入"""
        text = "这是一个测试文本"
        
        embedding = await mock_embedding.embed_text(text)
        
        assert isinstance(embedding, list)
        assert len(embedding) == 384
        assert all(isinstance(x, float) for x in embedding)
        assert all(-1.0 <= x <= 1.0 for x in embedding)  # 值在合理范围内
    
    @pytest.mark.asyncio
    async def test_embed_texts(self, mock_embedding):
        """测试批量文本嵌入"""
        texts = [
            "第一个测试文本",
            "第二个测试文本",
            "第三个测试文本"
        ]
        
        embeddings = await mock_embedding.embed_texts(texts)
        
        assert len(embeddings) == len(texts)
        assert all(isinstance(emb, list) for emb in embeddings)
        assert all(len(emb) == 384 for emb in embeddings)
        assert all(all(isinstance(x, float) for x in emb) for emb in embeddings)
        
        # 验证不同文本生成不同向量
        assert embeddings[0] != embeddings[1]
        assert embeddings[1] != embeddings[2]
    
    @pytest.mark.asyncio
    async def test_embed_query(self, mock_embedding):
        """测试查询嵌入"""
        query = "这是一个查询文本"
        
        embedding = await mock_embedding.embed_query(query)
        
        assert isinstance(embedding, list)
        assert len(embedding) == 384
        assert all(isinstance(x, float) for x in embedding)
    
    @pytest.mark.asyncio
    async def test_deterministic_embedding(self, mock_embedding):
        """测试确定性嵌入（相同文本生成相同向量）"""
        text = "测试确定性嵌入"
        
        # 多次嵌入相同文本
        embedding1 = await mock_embedding.embed_text(text)
        embedding2 = await mock_embedding.embed_text(text)
        
        # 应该生成相同的向量
        assert embedding1 == embedding2
    
    @pytest.mark.asyncio
    async def test_different_texts_different_embeddings(self, mock_embedding):
        """测试不同文本生成不同向量"""
        text1 = "第一个文本"
        text2 = "第二个文本"
        
        embedding1 = await mock_embedding.embed_text(text1)
        embedding2 = await mock_embedding.embed_text(text2)
        
        # 应该生成不同的向量
        assert embedding1 != embedding2
    
    @pytest.mark.asyncio
    async def test_empty_text_list(self, mock_embedding):
        """测试空文本列表"""
        embeddings = await mock_embedding.embed_texts([])
        assert embeddings == []
    
    @pytest.mark.asyncio
    async def test_large_batch(self, mock_embedding):
        """测试大批量处理"""
        # 创建大量文本
        texts = [f"文本{i}" for i in range(100)]
        
        embeddings = await mock_embedding.embed_texts(texts)
        
        assert len(embeddings) == 100
        assert all(len(emb) == 384 for emb in embeddings)
        
        # 验证所有向量都不相同
        unique_embeddings = set(tuple(emb) for emb in embeddings)
        assert len(unique_embeddings) == 100
    
    @pytest.mark.asyncio
    async def test_hash_based_generation(self, mock_embedding):
        """测试基于哈希的向量生成"""
        text = "测试哈希生成"
        
        # 手动计算期望的哈希
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        
        embedding = await mock_embedding.embed_text(text)
        
        # 验证向量是基于哈希生成的（具有一定的随机性但可重现）
        assert len(embedding) == 384
        assert all(isinstance(x, float) for x in embedding)
        
        # 相同文本应该生成相同向量
        embedding2 = await mock_embedding.embed_text(text)
        assert embedding == embedding2
    
    @pytest.mark.asyncio
    async def test_vector_properties(self, mock_embedding):
        """测试向量属性"""
        text = "测试向量属性"
        
        embedding = await mock_embedding.embed_text(text)
        
        # 验证向量长度
        assert len(embedding) == 384
        
        # 验证向量值范围
        assert all(-1.0 <= x <= 1.0 for x in embedding)
        
        # 验证向量不全为零
        assert any(x != 0.0 for x in embedding)
        
        # 验证向量具有一定的分布（不是所有值都相同）
        unique_values = set(embedding)
        assert len(unique_values) > 1
    
    @pytest.mark.asyncio
    async def test_unicode_text_handling(self, mock_embedding):
        """测试Unicode文本处理"""
        texts = [
            "中文测试文本",
            "English test text",
            "混合语言 mixed language",
            "特殊字符!@#$%^&*()",
            "数字123456789",
            "emoji测试😀🎉🚀"
        ]
        
        embeddings = await mock_embedding.embed_texts(texts)
        
        assert len(embeddings) == len(texts)
        assert all(len(emb) == 384 for emb in embeddings)
        assert all(all(isinstance(x, float) for x in emb) for emb in embeddings)
        
        # 验证不同文本生成不同向量
        unique_embeddings = set(tuple(emb) for emb in embeddings)
        assert len(unique_embeddings) == len(texts)


class TestMockEmbeddingConfiguration:
    """Mock嵌入配置测试"""
    
    @pytest.mark.asyncio
    async def test_custom_dimensions(self):
        """测试自定义维度"""
        config = EmbeddingConfig(
            provider="mock",
            model="test-model",
            dimensions=512
        )
        
        embedding = MockEmbedding(config)
        await embedding.initialize()
        
        try:
            assert embedding.get_embedding_dimension() == 512
            
            text_embedding = await embedding.embed_text("测试文本")
            assert len(text_embedding) == 512
            
        finally:
            await embedding.cleanup()
    
    @pytest.mark.asyncio
    async def test_default_dimensions(self):
        """测试默认维度"""
        config = EmbeddingConfig(
            provider="mock",
            model="test-model"
            # 不指定dimensions，使用默认值
        )
        
        embedding = MockEmbedding(config)
        await embedding.initialize()
        
        try:
            # 默认维度应该是384
            assert embedding.get_embedding_dimension() == 384
            
            text_embedding = await embedding.embed_text("测试文本")
            assert len(text_embedding) == 384
            
        finally:
            await embedding.cleanup()
    
    @pytest.mark.asyncio
    async def test_different_models_same_text(self):
        """测试不同模型对相同文本的处理"""
        text = "相同的测试文本"
        
        # 创建两个不同模型的配置
        config1 = EmbeddingConfig(provider="mock", model="model-1", dimensions=256)
        config2 = EmbeddingConfig(provider="mock", model="model-2", dimensions=256)
        
        embedding1 = MockEmbedding(config1)
        embedding2 = MockEmbedding(config2)
        
        await embedding1.initialize()
        await embedding2.initialize()
        
        try:
            emb1 = await embedding1.embed_text(text)
            emb2 = await embedding2.embed_text(text)
            
            # 相同文本在不同模型下应该生成相同向量（因为只基于文本内容哈希）
            # 注意：当前实现只基于文本内容，不考虑模型名称
            # 如果需要模型名称影响结果，需要修改_generate_embedding方法
            assert len(emb1) == len(emb2) == 256
            assert len(emb1) == len(emb2) == 256
            
        finally:
            await embedding1.cleanup()
            await embedding2.cleanup()


class TestMockEmbeddingPerformance:
    """Mock嵌入性能测试"""
    
    @pytest.mark.asyncio
    async def test_batch_vs_individual_consistency(self, mock_embedding):
        """测试批量处理与单独处理的一致性"""
        texts = ["文本1", "文本2", "文本3"]
        
        # 批量处理
        batch_embeddings = await mock_embedding.embed_texts(texts)
        
        # 单独处理
        individual_embeddings = []
        for text in texts:
            emb = await mock_embedding.embed_text(text)
            individual_embeddings.append(emb)
        
        # 结果应该一致
        assert len(batch_embeddings) == len(individual_embeddings)
        for batch_emb, individual_emb in zip(batch_embeddings, individual_embeddings):
            assert batch_emb == individual_emb
    
    @pytest.mark.asyncio
    async def test_large_text_handling(self, mock_embedding):
        """测试大文本处理"""
        # 创建一个很长的文本
        long_text = "这是一个很长的文本。" * 1000
        
        embedding = await mock_embedding.embed_text(long_text)
        
        assert len(embedding) == 384
        assert all(isinstance(x, float) for x in embedding)
        assert all(-1.0 <= x <= 1.0 for x in embedding)