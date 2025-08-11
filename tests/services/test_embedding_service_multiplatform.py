"""
多平台嵌入服务集成测试
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

from rag_system.services.embedding_service import EmbeddingService
from rag_system.embeddings.base import EmbeddingConfig
from rag_system.embeddings.factory import EmbeddingFactory
from rag_system.models.document import TextChunk
from rag_system.utils.exceptions import ProcessingError
from rag_system.utils.model_exceptions import ModelConnectionError, ModelResponseError


class TestEmbeddingServiceMultiPlatform:
    """多平台嵌入服务测试"""
    
    @pytest.fixture
    def embedding_config(self):
        """嵌入服务配置"""
        return {
            'provider': 'siliconflow',
            'model': 'BAAI/bge-large-zh-v1.5',
            'api_key': 'test-key',
            'base_url': 'https://api.siliconflow.cn/v1',
            'max_tokens': 8192,
            'batch_size': 100,
            'dimensions': 1024,
            'timeout': 30,
            'retry_attempts': 3,
            'enable_embedding_fallback': True
        }
    
    @pytest.fixture
    def sample_text_chunks(self):
        """示例文本块"""
        return [
            TextChunk(
                id="12345678-1234-5678-9abc-123456789abc",
                document_id="87654321-4321-8765-cba9-987654321cba",
                content="这是第一个文本块的内容。",
                chunk_index=0,
                start_char=0,
                end_char=12,
                metadata={"section": "introduction"}
            ),
            TextChunk(
                id="11111111-2222-3333-4444-555555555555",
                document_id="66666666-7777-8888-9999-aaaaaaaaaaaa",
                content="这是第二个文本块的内容。",
                chunk_index=1,
                start_char=13,
                end_char=25,
                metadata={"section": "content"}
            )
        ]
    
    @pytest.mark.asyncio
    async def test_embedding_service_initialization_with_multiplatform(self, embedding_config):
        """测试多平台嵌入服务初始化"""
        with patch.object(EmbeddingFactory, 'create_embedding') as mock_create_embedding:
            # 模拟主要嵌入模型
            mock_main_embedding = AsyncMock()
            mock_main_embedding.initialize = AsyncMock()
            mock_main_embedding.cleanup = AsyncMock()
            mock_main_embedding.get_embedding_dimension = Mock(return_value=1024)
            
            # 模拟备用嵌入模型
            mock_fallback_embedding = AsyncMock()
            mock_fallback_embedding.initialize = AsyncMock()
            mock_fallback_embedding.cleanup = AsyncMock()
            mock_fallback_embedding.get_embedding_dimension = Mock(return_value=768)
            
            # 根据配置返回不同的嵌入实例
            def create_embedding_side_effect(config):
                if config.provider == 'siliconflow':
                    return mock_main_embedding
                elif config.provider == 'mock':
                    return mock_fallback_embedding
                return mock_main_embedding
            
            mock_create_embedding.side_effect = create_embedding_side_effect
            
            embedding_service = EmbeddingService(embedding_config)
            await embedding_service.initialize()
            
            # 验证初始化
            assert embedding_service._embedding_model is not None
            assert embedding_service._fallback_model is not None
            assert embedding_service._embedding_config.provider == 'siliconflow'
            assert embedding_service._fallback_config.provider == 'mock'
            
            # 验证嵌入模型初始化被调用
            mock_main_embedding.initialize.assert_called_once()
            mock_fallback_embedding.initialize.assert_called_once()
            
            # 验证维度缓存
            assert embedding_service._dimension_cache['siliconflow'] == 1024
            assert embedding_service._dimension_cache['mock'] == 768
            
            await embedding_service.cleanup()
    
    @pytest.mark.asyncio
    async def test_vectorize_text_with_main_embedding(self, embedding_config):
        """测试使用主要嵌入模型向量化文本"""
        with patch.object(EmbeddingFactory, 'create_embedding') as mock_create_embedding:
            # 模拟主要嵌入模型
            mock_main_embedding = AsyncMock()
            mock_main_embedding.initialize = AsyncMock()
            mock_main_embedding.cleanup = AsyncMock()
            mock_main_embedding.get_embedding_dimension = Mock(return_value=1024)
            mock_main_embedding.embed_text = AsyncMock(return_value=[0.1] * 1024)
            
            mock_create_embedding.return_value = mock_main_embedding
            
            embedding_service = EmbeddingService(embedding_config)
            await embedding_service.initialize()
            
            # 测试文本向量化
            text = "这是一个测试文本"
            embedding = await embedding_service.vectorize_text(text)
            
            # 验证结果
            assert len(embedding) == 1024
            assert all(isinstance(x, float) for x in embedding)
            
            # 验证嵌入模型被调用
            mock_main_embedding.embed_text.assert_called_once_with(text)
            
            await embedding_service.cleanup()
    
    @pytest.mark.asyncio
    async def test_vectorize_texts_batch_processing(self, embedding_config):
        """测试批量文本向量化"""
        with patch.object(EmbeddingFactory, 'create_embedding') as mock_create_embedding:
            # 模拟主要嵌入模型
            mock_main_embedding = AsyncMock()
            mock_main_embedding.initialize = AsyncMock()
            mock_main_embedding.cleanup = AsyncMock()
            mock_main_embedding.get_embedding_dimension = Mock(return_value=1024)
            mock_main_embedding.embed_texts = AsyncMock(return_value=[[0.1] * 1024, [0.2] * 1024])
            
            mock_create_embedding.return_value = mock_main_embedding
            
            embedding_service = EmbeddingService(embedding_config)
            await embedding_service.initialize()
            
            # 测试批量向量化
            texts = ["第一个文本", "第二个文本"]
            embeddings = await embedding_service.vectorize_texts(texts)
            
            # 验证结果
            assert len(embeddings) == 2
            assert all(len(emb) == 1024 for emb in embeddings)
            
            # 验证嵌入模型被调用
            mock_main_embedding.embed_texts.assert_called_once_with(texts)
            
            await embedding_service.cleanup()
    
    @pytest.mark.asyncio
    async def test_fallback_to_backup_embedding_on_error(self, embedding_config):
        """测试主要嵌入模型失败时切换到备用模型"""
        with patch.object(EmbeddingFactory, 'create_embedding') as mock_create_embedding:
            # 模拟主要嵌入模型（会失败）
            mock_main_embedding = AsyncMock()
            mock_main_embedding.initialize = AsyncMock()
            mock_main_embedding.cleanup = AsyncMock()
            mock_main_embedding.get_embedding_dimension = Mock(return_value=1024)
            mock_main_embedding.embed_text = AsyncMock(
                side_effect=ModelConnectionError("连接失败", "siliconflow", "BAAI/bge-large-zh-v1.5")
            )
            
            # 模拟备用嵌入模型（成功）
            mock_fallback_embedding = AsyncMock()
            mock_fallback_embedding.initialize = AsyncMock()
            mock_fallback_embedding.cleanup = AsyncMock()
            mock_fallback_embedding.get_embedding_dimension = Mock(return_value=768)
            mock_fallback_embedding.embed_text = AsyncMock(return_value=[0.3] * 768)
            
            def create_embedding_side_effect(config):
                if config.provider == 'siliconflow':
                    return mock_main_embedding
                elif config.provider == 'mock':
                    return mock_fallback_embedding
                return mock_main_embedding
            
            mock_create_embedding.side_effect = create_embedding_side_effect
            
            embedding_service = EmbeddingService(embedding_config)
            await embedding_service.initialize()
            
            # 测试向量化（应该切换到备用模型）
            text = "测试文本"
            embedding = await embedding_service.vectorize_text(text)
            
            # 验证结果
            assert len(embedding) == 768
            assert all(x == 0.3 for x in embedding)
            
            # 验证主要模型被调用但失败
            mock_main_embedding.embed_text.assert_called_once()
            # 验证备用模型被调用
            mock_fallback_embedding.embed_text.assert_called_once()
            
            await embedding_service.cleanup()
    
    @pytest.mark.asyncio
    async def test_dimension_compatibility_check(self, embedding_config):
        """测试向量维度兼容性检查"""
        with patch.object(EmbeddingFactory, 'create_embedding') as mock_create_embedding:
            # 模拟返回错误维度的嵌入模型
            mock_main_embedding = AsyncMock()
            mock_main_embedding.initialize = AsyncMock()
            mock_main_embedding.cleanup = AsyncMock()
            mock_main_embedding.get_embedding_dimension = Mock(return_value=1024)
            mock_main_embedding.embed_texts = AsyncMock(return_value=[[0.1] * 512])  # 错误维度
            
            # 模拟备用嵌入模型
            mock_fallback_embedding = AsyncMock()
            mock_fallback_embedding.initialize = AsyncMock()
            mock_fallback_embedding.cleanup = AsyncMock()
            mock_fallback_embedding.get_embedding_dimension = Mock(return_value=768)
            mock_fallback_embedding.embed_texts = AsyncMock(return_value=[[0.2] * 768])
            
            def create_embedding_side_effect(config):
                if config.provider == 'siliconflow':
                    return mock_main_embedding
                elif config.provider == 'mock':
                    return mock_fallback_embedding
                return mock_main_embedding
            
            mock_create_embedding.side_effect = create_embedding_side_effect
            
            embedding_service = EmbeddingService(embedding_config)
            await embedding_service.initialize()
            
            # 测试批量向量化（应该检测到维度不匹配并切换到备用模型）
            texts = ["测试文本"]
            embeddings = await embedding_service.vectorize_texts(texts)
            
            # 验证结果使用了备用模型
            assert len(embeddings) == 1
            assert len(embeddings[0]) == 768
            
            await embedding_service.cleanup()
    
    @pytest.mark.asyncio
    async def test_vectorize_chunks_with_metadata(self, embedding_config, sample_text_chunks):
        """测试文本块向量化并包含元数据"""
        with patch.object(EmbeddingFactory, 'create_embedding') as mock_create_embedding:
            # 模拟嵌入模型
            mock_embedding = AsyncMock()
            mock_embedding.initialize = AsyncMock()
            mock_embedding.cleanup = AsyncMock()
            mock_embedding.get_embedding_dimension = Mock(return_value=1024)
            mock_embedding.embed_texts = AsyncMock(return_value=[[0.1] * 1024, [0.2] * 1024])
            
            mock_create_embedding.return_value = mock_embedding
            
            embedding_service = EmbeddingService(embedding_config)
            await embedding_service.initialize()
            
            # 测试文本块向量化
            document_name = "测试文档"
            vectors = await embedding_service.vectorize_chunks(sample_text_chunks, document_name)
            
            # 验证结果
            assert len(vectors) == 2
            
            for i, vector in enumerate(vectors):
                assert vector.document_id == sample_text_chunks[i].document_id
                assert vector.chunk_id == sample_text_chunks[i].id
                assert len(vector.embedding) == 1024
                assert vector.metadata['document_name'] == document_name
                assert vector.metadata['chunk_index'] == i
                assert vector.metadata['embedding_provider'] == 'siliconflow'
                assert vector.metadata['embedding_model'] == 'BAAI/bge-large-zh-v1.5'
                assert vector.metadata['embedding_dimensions'] == 1024
            
            await embedding_service.cleanup()
    
    @pytest.mark.asyncio
    async def test_dynamic_provider_switching(self, embedding_config):
        """测试动态嵌入提供商切换"""
        with patch.object(EmbeddingFactory, 'create_embedding') as mock_create_embedding:
            # 模拟不同的嵌入实例
            mock_siliconflow_embedding = AsyncMock()
            mock_siliconflow_embedding.initialize = AsyncMock()
            mock_siliconflow_embedding.cleanup = AsyncMock()
            mock_siliconflow_embedding.get_embedding_dimension = Mock(return_value=1024)
            
            mock_openai_embedding = AsyncMock()
            mock_openai_embedding.initialize = AsyncMock()
            mock_openai_embedding.cleanup = AsyncMock()
            mock_openai_embedding.get_embedding_dimension = Mock(return_value=1536)
            
            def create_embedding_side_effect(config):
                if config.provider == 'siliconflow':
                    return mock_siliconflow_embedding
                elif config.provider == 'openai':
                    return mock_openai_embedding
                return mock_siliconflow_embedding
            
            mock_create_embedding.side_effect = create_embedding_side_effect
            
            embedding_service = EmbeddingService(embedding_config)
            await embedding_service.initialize()
            
            # 验证初始配置
            assert embedding_service._embedding_config.provider == 'siliconflow'
            assert embedding_service._dimension_cache['siliconflow'] == 1024
            
            # 切换到OpenAI
            new_config = EmbeddingConfig(
                provider='openai',
                model='text-embedding-ada-002',
                api_key='test-openai-key',
                dimensions=1536,
                batch_size=50
            )
            
            success = await embedding_service.switch_provider(new_config)
            
            # 验证切换成功
            assert success is True
            assert embedding_service._embedding_config.provider == 'openai'
            assert embedding_service._embedding_config.model == 'text-embedding-ada-002'
            assert embedding_service._dimension_cache['openai'] == 1536
            
            # 验证旧模型被清理，新模型被初始化
            mock_siliconflow_embedding.cleanup.assert_called_once()
            mock_openai_embedding.initialize.assert_called_once()
            
            await embedding_service.cleanup()
    
    @pytest.mark.asyncio
    async def test_embedding_connection_testing(self, embedding_config):
        """测试嵌入模型连接测试功能"""
        with patch.object(EmbeddingFactory, 'create_embedding') as mock_create_embedding:
            # 模拟健康的嵌入模型
            mock_healthy_embedding = AsyncMock()
            mock_healthy_embedding.initialize = AsyncMock()
            mock_healthy_embedding.cleanup = AsyncMock()
            mock_healthy_embedding.health_check = Mock(return_value=True)
            mock_healthy_embedding.embed_text = AsyncMock(return_value=[0.1] * 1024)
            
            mock_create_embedding.return_value = mock_healthy_embedding
            
            embedding_service = EmbeddingService(embedding_config)
            await embedding_service.initialize()
            
            # 测试当前嵌入模型连接
            result = await embedding_service.test_embedding_connection()
            
            # 验证测试结果
            assert result['success'] is True
            assert result['provider'] == 'siliconflow'
            assert result['dimension'] == 1024
            assert result['status'] == 'healthy'
            
            # 测试其他配置
            test_config = EmbeddingConfig(
                provider='openai',
                model='text-embedding-ada-002',
                api_key='test-key',
                dimensions=1536
            )
            
            result = await embedding_service.test_embedding_connection(test_config)
            assert result['provider'] == 'openai'
            
            await embedding_service.cleanup()
    
    @pytest.mark.asyncio
    async def test_service_stats_with_multiplatform_info(self, embedding_config):
        """测试多平台服务统计信息"""
        with patch.object(EmbeddingFactory, 'create_embedding') as mock_create_embedding:
            with patch.object(EmbeddingFactory, 'get_available_providers', return_value=['openai', 'siliconflow', 'mock']):
                mock_embedding = AsyncMock()
                mock_embedding.initialize = AsyncMock()
                mock_embedding.cleanup = AsyncMock()
                mock_embedding.get_embedding_dimension = Mock(return_value=1024)
                
                mock_create_embedding.return_value = mock_embedding
                
                embedding_service = EmbeddingService(embedding_config)
                await embedding_service.initialize()
                
                # 获取服务统计
                stats = await embedding_service.get_service_stats()
                
                # 验证统计信息
                assert stats['service_name'] == 'EmbeddingService'
                assert 'main_embedding' in stats
                assert stats['main_embedding']['provider'] == 'siliconflow'
                assert stats['main_embedding']['model'] == 'BAAI/bge-large-zh-v1.5'
                assert stats['main_embedding']['dimension'] == 1024
                assert stats['main_embedding']['status'] == 'available'
                
                assert 'fallback_embedding' in stats
                assert stats['fallback_embedding']['provider'] == 'mock'
                assert stats['fallback_embedding']['enabled'] is True
                
                assert 'available_providers' in stats
                assert 'openai' in stats['available_providers']
                assert 'siliconflow' in stats['available_providers']
                
                assert stats['fallback_enabled'] is True
                assert stats['batch_size'] == 100
                assert stats['max_tokens'] == 8192
                
                await embedding_service.cleanup()
    
    @pytest.mark.asyncio
    async def test_query_vectorization(self, embedding_config):
        """测试查询向量化"""
        with patch.object(EmbeddingFactory, 'create_embedding') as mock_create_embedding:
            # 模拟嵌入模型
            mock_embedding = AsyncMock()
            mock_embedding.initialize = AsyncMock()
            mock_embedding.cleanup = AsyncMock()
            mock_embedding.get_embedding_dimension = Mock(return_value=1024)
            mock_embedding.embed_query = AsyncMock(return_value=[0.5] * 1024)
            
            mock_create_embedding.return_value = mock_embedding
            
            embedding_service = EmbeddingService(embedding_config)
            await embedding_service.initialize()
            
            # 测试查询向量化
            query = "什么是人工智能？"
            embedding = await embedding_service.vectorize_query(query)
            
            # 验证结果
            assert len(embedding) == 1024
            assert all(x == 0.5 for x in embedding)
            
            # 验证嵌入模型被调用
            mock_embedding.embed_query.assert_called_once_with(query)
            
            await embedding_service.cleanup()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])