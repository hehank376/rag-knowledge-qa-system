"""
嵌入服务测试
"""
import pytest
import pytest_asyncio
import uuid
from typing import List

from rag_system.services.embedding_service import EmbeddingService
from rag_system.models.document import TextChunk
from rag_system.models.vector import Vector
from rag_system.utils.exceptions import ProcessingError, ConfigurationError


@pytest_asyncio.fixture
async def mock_embedding_service():
    """模拟嵌入服务fixture"""
    config = {
        'provider': 'mock',
        'model': 'test-model',
        'dimensions': 384,
        'batch_size': 10
    }
    
    service = EmbeddingService(config)
    await service.initialize()
    
    yield service
    
    await service.cleanup()


@pytest_asyncio.fixture
def sample_text_chunks():
    """示例文本块fixture"""
    doc_id = str(uuid.uuid4())
    
    chunks = []
    for i in range(3):
        chunk = TextChunk(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            content=f"这是第{i+1}个测试文本块的内容。包含了一些测试数据。",
            chunk_index=i,
            metadata={"test": True}
        )
        chunks.append(chunk)
    
    return chunks


class TestEmbeddingService:
    """嵌入服务测试"""
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """测试服务初始化"""
        config = {
            'provider': 'mock',
            'model': 'test-model',
            'dimensions': 256
        }
        
        service = EmbeddingService(config)
        await service.initialize()
        
        try:
            # 验证服务已初始化
            dimension = service.get_embedding_dimension()
            assert dimension == 256
            
            # 验证模型信息
            model_info = await service.get_model_info()
            assert model_info['provider'] == 'mock'
            assert model_info['model'] == 'test-model'
            assert model_info['dimensions'] == 256
            
        finally:
            await service.cleanup()
    
    @pytest.mark.asyncio
    async def test_invalid_provider(self):
        """测试无效的提供商"""
        config = {
            'provider': 'invalid_provider',
            'model': 'test-model'
        }
        
        service = EmbeddingService(config)
        
        with pytest.raises(ConfigurationError):
            await service.initialize()
    
    @pytest.mark.asyncio
    async def test_vectorize_text(self, mock_embedding_service):
        """测试单个文本向量化"""
        text = "这是一个测试文本"
        
        embedding = await mock_embedding_service.vectorize_text(text)
        
        assert isinstance(embedding, list)
        assert len(embedding) == 384  # 配置的维度
        assert all(isinstance(x, float) for x in embedding)
    
    @pytest.mark.asyncio
    async def test_vectorize_empty_text(self, mock_embedding_service):
        """测试空文本向量化"""
        with pytest.raises(ProcessingError):
            await mock_embedding_service.vectorize_text("")
        
        with pytest.raises(ProcessingError):
            await mock_embedding_service.vectorize_text("   ")
    
    @pytest.mark.asyncio
    async def test_vectorize_texts(self, mock_embedding_service):
        """测试批量文本向量化"""
        texts = [
            "第一个测试文本",
            "第二个测试文本", 
            "第三个测试文本"
        ]
        
        embeddings = await mock_embedding_service.vectorize_texts(texts)
        
        assert len(embeddings) == len(texts)
        assert all(isinstance(emb, list) for emb in embeddings)
        assert all(len(emb) == 384 for emb in embeddings)
        
        # 验证不同文本生成不同向量
        assert embeddings[0] != embeddings[1]
        assert embeddings[1] != embeddings[2]
    
    @pytest.mark.asyncio
    async def test_vectorize_chunks(self, mock_embedding_service, sample_text_chunks):
        """测试文本块向量化"""
        vectors = await mock_embedding_service.vectorize_chunks(sample_text_chunks)
        
        assert len(vectors) == len(sample_text_chunks)
        assert all(isinstance(vector, Vector) for vector in vectors)
        
        # 验证向量属性
        for i, vector in enumerate(vectors):
            chunk = sample_text_chunks[i]
            
            assert vector.document_id == chunk.document_id
            assert vector.chunk_id == chunk.id
            assert len(vector.embedding) == 384
            assert vector.metadata['chunk_index'] == chunk.chunk_index
            assert vector.metadata['embedding_model'] == 'test-model'
            assert vector.metadata['embedding_provider'] == 'mock'
    
    @pytest.mark.asyncio
    async def test_test_embedding(self, mock_embedding_service):
        """测试嵌入功能测试"""
        result = await mock_embedding_service.test_embedding()
        
        assert result['success'] is True
        assert 'embedding_dimension' in result
        assert 'processing_time' in result
        assert 'model_info' in result
        assert result['embedding_dimension'] == 384