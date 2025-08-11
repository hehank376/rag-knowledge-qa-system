"""
测试SiliconFlow嵌入模型实现
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import httpx

from rag_system.embeddings.siliconflow_embedding import SiliconFlowEmbedding
from rag_system.embeddings.base import EmbeddingConfig, EmbeddingResult
from rag_system.utils.exceptions import ProcessingError
from rag_system.utils.model_exceptions import (
    ModelConnectionError, ModelResponseError, ModelAuthenticationError,
    ModelRateLimitError, ModelTimeoutError
)


class TestSiliconFlowEmbedding:
    """测试SiliconFlow嵌入模型"""
    
    @pytest.fixture
    def config(self):
        """测试配置"""
        return EmbeddingConfig(
            provider="siliconflow",
            model="BAAI/bge-large-zh-v1.5",
            api_key="test-api-key",
            base_url="https://api.siliconflow.cn/v1",
            dimension=1024,
            batch_size=100,
            timeout=60
        )
    
    @pytest.fixture
    def embedding(self, config):
        """SiliconFlow嵌入模型实例"""
        return SiliconFlowEmbedding(config)
    
    def test_initialization(self, config):
        """测试初始化"""
        embedding = SiliconFlowEmbedding(config)
        
        assert embedding.api_key == "test-api-key"
        assert embedding.base_url == "https://api.siliconflow.cn/v1"
        assert embedding.model == "BAAI/bge-large-zh-v1.5"
        assert embedding.dimension == 1024
        assert embedding.batch_size == 100
        assert embedding.timeout == 60
    
    def test_initialization_without_api_key(self):
        """测试没有API密钥的初始化"""
        config = EmbeddingConfig(provider="siliconflow", model="test-model")
        
        with pytest.raises(ValueError, match="SiliconFlow API key is required"):
            SiliconFlowEmbedding(config)
    
    def test_default_values(self):
        """测试默认值"""
        config = EmbeddingConfig(
            provider="siliconflow",
            api_key="test-key"
        )
        embedding = SiliconFlowEmbedding(config)
        
        assert embedding.base_url == "https://api.siliconflow.cn/v1"
        # 如果config没有指定model，会使用SiliconFlow的默认模型
        assert embedding.model == "BAAI/bge-large-zh-v1.5"
        assert embedding.dimension == 1024
    
    def test_model_dimensions_mapping(self):
        """测试模型维度映射"""
        # 创建没有指定dimension的配置来测试模型维度映射
        config = EmbeddingConfig(
            provider="siliconflow",
            api_key="test-key"
        )
        embedding = SiliconFlowEmbedding(config)
        
        # 测试已知模型的维度
        embedding.model = "BAAI/bge-base-zh-v1.5"
        embedding.dimension = None  # 清除配置的维度
        assert embedding.get_embedding_dimension() == 768
        
        embedding.model = "BAAI/bge-small-zh-v1.5"
        assert embedding.get_embedding_dimension() == 512
        
        embedding.model = "sentence-transformers/all-MiniLM-L6-v2"
        assert embedding.get_embedding_dimension() == 384
        
        # 测试未知模型使用默认维度
        embedding.model = "unknown-model"
        assert embedding.get_embedding_dimension() == 1024
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, embedding):
        """测试成功初始化"""
        with patch.object(embedding, '_test_connection', new_callable=AsyncMock):
            await embedding.initialize()
            
            assert embedding.is_initialized()
            assert embedding._client is not None
    
    @pytest.mark.asyncio
    async def test_initialize_with_test_key(self, config):
        """测试使用测试密钥初始化（跳过连接测试）"""
        config.api_key = "test-skip-connection"
        embedding = SiliconFlowEmbedding(config)
        
        await embedding.initialize()
        assert embedding.is_initialized()
    
    @pytest.mark.asyncio
    async def test_initialize_connection_failure(self):
        """测试初始化时连接失败"""
        config = EmbeddingConfig(
            provider="siliconflow",
            model="test-model",
            api_key="real-api-key",  # 不以test-开头，会触发连接测试
            base_url="https://api.siliconflow.cn/v1"
        )
        embedding = SiliconFlowEmbedding(config)
        
        with patch.object(embedding, '_test_connection', side_effect=ModelConnectionError("Connection failed", "siliconflow", "test")):
            with pytest.raises(ProcessingError, match="SiliconFlow嵌入模型初始化失败"):
                await embedding.initialize()
    
    @pytest.mark.asyncio
    async def test_embed_text_success(self, embedding):
        """测试成功嵌入单个文本"""
        mock_embeddings = [[0.1, 0.2, 0.3] * 341 + [0.1]]  # 1024维向量
        
        with patch.object(embedding, '_create_embeddings', return_value=mock_embeddings):
            embedding._initialized = True
            
            result = await embedding.embed_text("test text")
            
            assert isinstance(result, list)
            assert len(result) == 1024
            assert result == mock_embeddings[0]
    
    @pytest.mark.asyncio
    async def test_embed_text_not_initialized(self, embedding):
        """测试未初始化时嵌入文本"""
        with pytest.raises(ProcessingError, match="SiliconFlow嵌入服务未初始化"):
            await embedding.embed_text("test text")
    
    @pytest.mark.asyncio
    async def test_embed_text_invalid_input(self, embedding):
        """测试无效输入"""
        embedding._initialized = True
        
        with pytest.raises(ProcessingError, match="无效的文本输入"):
            await embedding.embed_text("")
    
    @pytest.mark.asyncio
    async def test_embed_texts_success(self, embedding):
        """测试成功批量嵌入文本"""
        texts = ["text1", "text2", "text3"]
        mock_embeddings = [
            [0.1] * 1024,
            [0.2] * 1024,
            [0.3] * 1024
        ]
        
        with patch.object(embedding, '_create_embeddings', return_value=mock_embeddings):
            embedding._initialized = True
            
            result = await embedding.embed_texts(texts)
            
            assert isinstance(result, list)
            assert len(result) == 3
            assert all(len(emb) == 1024 for emb in result)
    
    @pytest.mark.asyncio
    async def test_embed_texts_chunking(self, embedding):
        """测试文本分块处理"""
        embedding.config.batch_size = 2  # 修改config中的batch_size
        texts = ["text1", "text2", "text3", "text4", "text5"]
        
        # 使用AsyncMock并设置side_effect
        mock_create_embeddings = AsyncMock()
        mock_create_embeddings.side_effect = [
            [[0.1] * 1024, [0.2] * 1024],  # 第一批：2个文本
            [[0.3] * 1024, [0.4] * 1024],  # 第二批：2个文本
            [[0.5] * 1024]                  # 第三批：1个文本
        ]
        
        with patch.object(embedding, '_create_embeddings', mock_create_embeddings):
            with patch('asyncio.sleep'):  # 跳过等待时间
                embedding._initialized = True
                
                result = await embedding.embed_texts(texts)
                
                assert len(result) == 5
                assert all(len(emb) == 1024 for emb in result)
                # 验证调用了3次（3个批次）
                assert mock_create_embeddings.call_count == 3
    
    @pytest.mark.asyncio
    async def test_embed_query(self, embedding):
        """测试查询嵌入"""
        mock_embeddings = [[0.1] * 1024]
        
        with patch.object(embedding, '_create_embeddings', return_value=mock_embeddings):
            embedding._initialized = True
            
            result = await embedding.embed_query("test query")
            
            assert isinstance(result, list)
            assert len(result) == 1024
    
    @pytest.mark.asyncio
    async def test_create_embeddings_success(self, embedding):
        """测试成功创建嵌入"""
        mock_response_data = {
            'data': [
                {'embedding': [0.1] * 1024},
                {'embedding': [0.2] * 1024}
            ]
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        embedding._client = mock_client
        
        texts = ["text1", "text2"]
        result = await embedding._create_embeddings(texts)
        
        assert len(result) == 2
        assert result[0] == [0.1] * 1024
        assert result[1] == [0.2] * 1024
        mock_client.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_embeddings_auth_error(self, embedding):
        """测试认证错误"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        embedding._client = mock_client
        
        texts = ["text1"]
        
        with pytest.raises(ModelAuthenticationError):
            await embedding._create_embeddings(texts)
    
    @pytest.mark.asyncio
    async def test_create_embeddings_rate_limit(self, embedding):
        """测试限流错误"""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        embedding._client = mock_client
        embedding.retry_attempts = 1  # 减少重试次数
        
        texts = ["text1"]
        
        with pytest.raises(ModelRateLimitError):
            await embedding._create_embeddings(texts)
    
    @pytest.mark.asyncio
    async def test_create_embeddings_timeout(self, embedding):
        """测试超时错误"""
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.TimeoutException("Timeout")
        embedding._client = mock_client
        embedding.retry_attempts = 1  # 减少重试次数
        
        texts = ["text1"]
        
        with pytest.raises(ModelTimeoutError):
            await embedding._create_embeddings(texts)
    
    @pytest.mark.asyncio
    async def test_create_embeddings_retry_success(self, embedding):
        """测试重试成功"""
        mock_response_data = {
            'data': [{'embedding': [0.1] * 1024}]
        }
        
        # 第一次失败，第二次成功
        mock_response_fail = Mock()
        mock_response_fail.status_code = 500
        mock_response_fail.text = "Server error"
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = mock_response_data
        
        mock_client = AsyncMock()
        mock_client.post.side_effect = [mock_response_fail, mock_response_success]
        embedding._client = mock_client
        
        texts = ["text1"]
        
        with patch('asyncio.sleep'):  # 跳过等待时间
            result = await embedding._create_embeddings(texts)
            assert result == [[0.1] * 1024]
    
    def test_sync_embed(self, embedding):
        """测试同步嵌入方法"""
        with patch('asyncio.run', return_value=[0.1] * 1024):
            result = embedding.embed("test text")
            
            assert isinstance(result, list)
            assert len(result) == 1024
    
    def test_sync_embed_batch(self, embedding):
        """测试同步批量嵌入方法"""
        mock_embeddings = [[0.1] * 1024, [0.2] * 1024]
        
        with patch('asyncio.run', return_value=mock_embeddings):
            result = embedding.embed_batch(["text1", "text2"])
            
            assert isinstance(result, list)
            assert len(result) == 2
            assert all(len(emb) == 1024 for emb in result)
    
    def test_sync_embed_error(self, embedding):
        """测试同步嵌入错误"""
        with patch('asyncio.run', side_effect=Exception("Embedding failed")):
            with pytest.raises(ProcessingError, match="同步嵌入生成失败"):
                embedding.embed("test")
    
    def test_get_dimension(self, embedding):
        """测试获取维度方法"""
        assert embedding.get_dimension() == 1024
    
    def test_health_check_success(self, embedding):
        """测试健康检查成功"""
        with patch('asyncio.run', return_value=[0.1] * 1024):
            assert embedding.health_check() is True
    
    def test_health_check_failure(self, embedding):
        """测试健康检查失败"""
        with patch('asyncio.run', side_effect=Exception("Health check failed")):
            assert embedding.health_check() is False
    
    def test_health_check_wrong_dimension(self, embedding):
        """测试健康检查维度不匹配"""
        with patch('asyncio.run', return_value=[0.1] * 512):  # 错误的维度
            assert embedding.health_check() is False
    
    @pytest.mark.asyncio
    async def test_cleanup(self, embedding):
        """测试资源清理"""
        mock_client = AsyncMock()
        embedding._client = mock_client
        embedding._initialized = True
        
        await embedding.cleanup()
        
        mock_client.aclose.assert_called_once()
        assert embedding._client is None
        assert not embedding.is_initialized()
    
    @pytest.mark.asyncio
    async def test_get_model_info(self, embedding):
        """测试获取模型信息"""
        info = await embedding.get_model_info()
        
        assert info['provider'] == 'siliconflow'
        assert info['model'] == 'BAAI/bge-large-zh-v1.5'
        assert info['dimensions'] == 1024
        assert info['batch_size'] == 100
        assert info['base_url'] == 'https://api.siliconflow.cn/v1'
    
    def test_get_available_models(self, embedding):
        """测试获取可用模型列表"""
        models = embedding.get_available_models()
        
        assert isinstance(models, list)
        assert len(models) > 0
        assert 'BAAI/bge-large-zh-v1.5' in models
        assert 'BAAI/bge-base-zh-v1.5' in models
        assert 'sentence-transformers/all-MiniLM-L6-v2' in models
    
    @pytest.mark.asyncio
    async def test_payload_construction(self, embedding):
        """测试请求载荷构造"""
        mock_response_data = {
            'data': [{'embedding': [0.1] * 1024}]
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        embedding._client = mock_client
        
        texts = ["test text"]
        await embedding._create_embeddings(texts)
        
        # 验证调用参数
        call_args = mock_client.post.call_args
        payload = call_args[1]['json']
        
        assert payload['model'] == 'BAAI/bge-large-zh-v1.5'
        assert payload['input'] == texts
        assert payload['encoding_format'] == 'float'
    
    def test_dimension_config_priority(self):
        """测试维度配置优先级"""
        # dimension优先于dimensions
        config = EmbeddingConfig(
            provider="siliconflow",
            api_key="test-key",
            dimension=512,
            dimensions=1024
        )
        embedding = SiliconFlowEmbedding(config)
        assert embedding.dimension == 512
        
        # 使用dimensions作为备选
        config = EmbeddingConfig(
            provider="siliconflow",
            api_key="test-key",
            dimensions=768
        )
        embedding = SiliconFlowEmbedding(config)
        assert embedding.dimension == 768