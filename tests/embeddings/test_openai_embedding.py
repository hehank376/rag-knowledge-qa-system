"""
OpenAI嵌入测试
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, Mock, patch
import aiohttp

from rag_system.embeddings.openai_embedding import OpenAIEmbedding
from rag_system.embeddings.base import EmbeddingConfig
from rag_system.utils.exceptions import ConfigurationError, ProcessingError


@pytest_asyncio.fixture
def openai_config():
    """OpenAI配置fixture"""
    return EmbeddingConfig(
        provider="openai",
        model="text-embedding-ada-002",
        api_key="test-api-key",
        api_base="https://api.openai.com/v1",
        dimensions=1536,
        batch_size=100,
        timeout=30,
        retry_attempts=3
    )


@pytest_asyncio.fixture
async def openai_embedding(openai_config):
    """OpenAI嵌入fixture"""
    embedding = OpenAIEmbedding(openai_config)
    yield embedding
    await embedding.cleanup()


class TestOpenAIEmbedding:
    """OpenAI嵌入测试"""
    
    def test_initialization(self, openai_config):
        """测试初始化"""
        embedding = OpenAIEmbedding(openai_config)
        
        assert embedding.config == openai_config
        assert not embedding.is_initialized()
        assert embedding._session is None
    
    def test_missing_api_key(self):
        """测试缺少API密钥"""
        config = EmbeddingConfig(
            provider="openai",
            model="text-embedding-ada-002"
            # 缺少api_key
        )
        
        with pytest.raises(ConfigurationError) as exc_info:
            OpenAIEmbedding(config)
        
        assert "API密钥不能为空" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_initialize_and_cleanup(self, openai_embedding):
        """测试初始化和清理"""
        # 初始化
        await openai_embedding.initialize()
        
        assert openai_embedding.is_initialized()
        assert openai_embedding._session is not None
        assert isinstance(openai_embedding._session, aiohttp.ClientSession)
        
        # 清理
        await openai_embedding.cleanup()
        
        assert not openai_embedding.is_initialized()
        assert openai_embedding._session is None
    
    @pytest.mark.asyncio
    async def test_multiple_initialize(self, openai_embedding):
        """测试多次初始化"""
        await openai_embedding.initialize()
        session1 = openai_embedding._session
        
        # 再次初始化应该先清理旧会话
        await openai_embedding.initialize()
        session2 = openai_embedding._session
        
        assert session1 != session2
        assert openai_embedding.is_initialized()
        
        await openai_embedding.cleanup()
    
    def test_get_embedding_dimension(self, openai_embedding):
        """测试获取嵌入维度"""
        dimension = openai_embedding.get_embedding_dimension()
        assert dimension == 1536  # 配置的维度
    
    @pytest.mark.asyncio
    async def test_get_model_info(self, openai_embedding):
        """测试获取模型信息"""
        await openai_embedding.initialize()
        
        model_info = await openai_embedding.get_model_info()
        
        assert model_info['provider'] == 'openai'
        assert model_info['model'] == 'text-embedding-ada-002'
        assert model_info['dimensions'] == 1536
        assert model_info['api_base'] == 'https://api.openai.com/v1'
        assert model_info['batch_size'] == 100
        
        await openai_embedding.cleanup()
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.post')
    async def test_embed_text_success(self, mock_post, openai_embedding):
        """测试单个文本嵌入成功"""
        # 模拟API响应
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'data': [{'embedding': [0.1, 0.2, 0.3]}],
            'usage': {'total_tokens': 10}
        })
        mock_post.return_value.__aenter__.return_value = mock_response
        
        await openai_embedding.initialize()
        
        embedding = await openai_embedding.embed_text("测试文本")
        
        assert embedding == [0.1, 0.2, 0.3]
        mock_post.assert_called_once()
        
        await openai_embedding.cleanup()
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.post')
    async def test_embed_texts_success(self, mock_post, openai_embedding):
        """测试批量文本嵌入成功"""
        # 模拟API响应
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'data': [
                {'embedding': [0.1, 0.2, 0.3]},
                {'embedding': [0.4, 0.5, 0.6]}
            ],
            'usage': {'total_tokens': 20}
        })
        mock_post.return_value.__aenter__.return_value = mock_response
        
        await openai_embedding.initialize()
        
        texts = ["文本1", "文本2"]
        embeddings = await openai_embedding.embed_texts(texts)
        
        assert len(embeddings) == 2
        assert embeddings[0] == [0.1, 0.2, 0.3]
        assert embeddings[1] == [0.4, 0.5, 0.6]
        
        await openai_embedding.cleanup()
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.post')
    async def test_embed_query_success(self, mock_post, openai_embedding):
        """测试查询嵌入成功"""
        # 模拟API响应
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'data': [{'embedding': [0.7, 0.8, 0.9]}],
            'usage': {'total_tokens': 5}
        })
        mock_post.return_value.__aenter__.return_value = mock_response
        
        await openai_embedding.initialize()
        
        embedding = await openai_embedding.embed_query("查询文本")
        
        assert embedding == [0.7, 0.8, 0.9]
        
        await openai_embedding.cleanup()
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.post')
    async def test_api_error_handling(self, mock_post, openai_embedding):
        """测试API错误处理"""
        # 模拟API错误响应
        mock_response = Mock()
        mock_response.status = 401
        mock_response.json = AsyncMock(return_value={
            'error': {'message': 'Invalid API key'}
        })
        mock_post.return_value.__aenter__.return_value = mock_response
        
        await openai_embedding.initialize()
        
        with pytest.raises(ProcessingError) as exc_info:
            await openai_embedding.embed_text("测试文本")
        
        assert "OpenAI API调用失败" in str(exc_info.value)
        assert "401" in str(exc_info.value)
        
        await openai_embedding.cleanup()
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.post')
    async def test_network_error_handling(self, mock_post, openai_embedding):
        """测试网络错误处理"""
        # 模拟网络错误
        mock_post.side_effect = aiohttp.ClientError("Network error")
        
        await openai_embedding.initialize()
        
        with pytest.raises(ProcessingError) as exc_info:
            await openai_embedding.embed_text("测试文本")
        
        assert "网络请求失败" in str(exc_info.value)
        
        await openai_embedding.cleanup()
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.post')
    async def test_retry_mechanism(self, mock_post, openai_embedding):
        """测试重试机制"""
        # 前两次调用失败，第三次成功
        mock_responses = [
            # 第一次失败
            Mock(status=500, json=AsyncMock(return_value={'error': {'message': 'Server error'}})),
            # 第二次失败
            Mock(status=500, json=AsyncMock(return_value={'error': {'message': 'Server error'}})),
            # 第三次成功
            Mock(status=200, json=AsyncMock(return_value={
                'data': [{'embedding': [0.1, 0.2, 0.3]}],
                'usage': {'total_tokens': 10}
            }))
        ]
        
        mock_post.return_value.__aenter__.side_effect = mock_responses
        
        await openai_embedding.initialize()
        
        # 应该在第三次重试后成功
        embedding = await openai_embedding.embed_text("测试文本")
        assert embedding == [0.1, 0.2, 0.3]
        
        # 验证调用了3次
        assert mock_post.call_count == 3
        
        await openai_embedding.cleanup()
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.post')
    async def test_batch_processing(self, mock_post, openai_embedding):
        """测试批量处理"""
        # 创建大量文本（超过batch_size）
        texts = [f"文本{i}" for i in range(150)]  # 超过默认batch_size=100
        
        # 模拟API响应
        def create_mock_response(batch_size):
            return Mock(
                status=200,
                json=AsyncMock(return_value={
                    'data': [{'embedding': [0.1, 0.2, 0.3]} for _ in range(batch_size)],
                    'usage': {'total_tokens': batch_size * 5}
                })
            )
        
        # 第一批100个，第二批50个
        mock_post.return_value.__aenter__.side_effect = [
            create_mock_response(100),
            create_mock_response(50)
        ]
        
        await openai_embedding.initialize()
        
        embeddings = await openai_embedding.embed_texts(texts)
        
        assert len(embeddings) == 150
        assert all(emb == [0.1, 0.2, 0.3] for emb in embeddings)
        
        # 验证调用了2次（分批处理）
        assert mock_post.call_count == 2
        
        await openai_embedding.cleanup()
    
    @pytest.mark.asyncio
    async def test_operations_without_initialization(self, openai_embedding):
        """测试未初始化时的操作"""
        with pytest.raises(ProcessingError) as exc_info:
            await openai_embedding.embed_text("测试文本")
        
        assert "OpenAI嵌入服务未初始化" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_empty_text_handling(self, openai_embedding):
        """测试空文本处理"""
        await openai_embedding.initialize()
        
        with pytest.raises(ProcessingError) as exc_info:
            await openai_embedding.embed_text("")
        
        assert "文本内容不能为空" in str(exc_info.value)
        
        await openai_embedding.cleanup()


class TestOpenAIEmbeddingConfiguration:
    """OpenAI嵌入配置测试"""
    
    def test_custom_api_base(self):
        """测试自定义API基础URL"""
        config = EmbeddingConfig(
            provider="openai",
            model="text-embedding-ada-002",
            api_key="test-key",
            api_base="https://custom-api.example.com/v1"
        )
        
        embedding = OpenAIEmbedding(config)
        assert embedding.config.api_base == "https://custom-api.example.com/v1"
    
    def test_custom_dimensions(self):
        """测试自定义维度"""
        config = EmbeddingConfig(
            provider="openai",
            model="text-embedding-3-small",
            api_key="test-key",
            dimensions=512
        )
        
        embedding = OpenAIEmbedding(config)
        assert embedding.get_embedding_dimension() == 512
    
    def test_custom_batch_size(self):
        """测试自定义批量大小"""
        config = EmbeddingConfig(
            provider="openai",
            model="text-embedding-ada-002",
            api_key="test-key",
            batch_size=50
        )
        
        embedding = OpenAIEmbedding(config)
        assert embedding.config.batch_size == 50
    
    def test_custom_timeout(self):
        """测试自定义超时"""
        config = EmbeddingConfig(
            provider="openai",
            model="text-embedding-ada-002",
            api_key="test-key",
            timeout=60
        )
        
        embedding = OpenAIEmbedding(config)
        assert embedding.config.timeout == 60