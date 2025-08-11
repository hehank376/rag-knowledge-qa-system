"""
缓存服务单元测试

测试缓存服务的各种功能：
- 缓存键生成逻辑
- 检索结果的序列化和反序列化
- 缓存存取功能
- 缓存过期和清理
- 错误处理和降级
- 统计信息收集
"""

import pytest
import json
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from rag_system.services.cache_service import CacheService, CacheKeyGenerator
from rag_system.models.config import RetrievalConfig
from rag_system.models.vector import SearchResult


class TestCacheService:
    """缓存服务测试类"""
    
    @pytest.fixture
    def cache_config(self):
        """缓存配置fixture"""
        return {
            'cache_ttl': 1800,  # 30分钟
            'redis_host': 'localhost',
            'redis_port': 6379,
            'redis_db': 1,
            'redis_password': None
        }
    
    @pytest.fixture
    def cache_service(self, cache_config):
        """缓存服务fixture"""
        return CacheService(cache_config)
    
    @pytest.fixture
    def sample_config(self):
        """示例检索配置"""
        return RetrievalConfig(
            search_mode='semantic',
            top_k=5,
            similarity_threshold=0.7,
            enable_rerank=True,
            enable_cache=True
        )
    
    @pytest.fixture
    def sample_results(self):
        """示例检索结果"""
        import uuid
        return [
            SearchResult(
                chunk_id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content="这是第一个测试文档的内容",
                similarity_score=0.95,
                metadata={"source": "doc1.txt", "page": 1}
            ),
            SearchResult(
                chunk_id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content="这是第二个测试文档的内容",
                similarity_score=0.88,
                metadata={"source": "doc2.txt", "page": 1}
            ),
            SearchResult(
                chunk_id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content="这是第三个测试文档的内容",
                similarity_score=0.82,
                metadata={"source": "doc3.txt", "page": 2}
            )
        ]
    
    def test_cache_service_initialization(self, cache_config):
        """测试缓存服务初始化"""
        service = CacheService(cache_config)
        
        assert service.cache_ttl == 1800
        assert service.redis_host == 'localhost'
        assert service.redis_port == 6379
        assert service.redis_db == 1
        assert service.cache_enabled is False  # 初始化前应该是False
        assert service.cache_stats['hits'] == 0
        assert service.cache_stats['misses'] == 0
    
    def test_cache_service_default_config(self):
        """测试缓存服务默认配置"""
        service = CacheService()
        
        assert service.cache_ttl == 3600  # 默认1小时
        assert service.redis_host == 'localhost'
        assert service.redis_port == 6379
        assert service.redis_db == 0
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, cache_service):
        """测试缓存服务成功初始化"""
        with patch('redis.asyncio.Redis') as mock_redis_class:
            mock_redis = AsyncMock()
            mock_redis.ping.return_value = True
            mock_redis_class.return_value = mock_redis
            
            await cache_service.initialize()
            
            assert cache_service.cache_enabled is True
            assert cache_service.redis_client is not None
            mock_redis.ping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_redis_unavailable(self, cache_service):
        """测试Redis不可用时的初始化"""
        with patch('redis.asyncio.Redis') as mock_redis_class:
            mock_redis = AsyncMock()
            mock_redis.ping.side_effect = Exception("Redis连接失败")
            mock_redis_class.return_value = mock_redis
            
            await cache_service.initialize()
            
            assert cache_service.cache_enabled is False
    
    @pytest.mark.asyncio
    async def test_initialize_redis_not_installed(self, cache_service):
        """测试Redis库未安装时的初始化"""
        with patch('redis.asyncio.Redis', side_effect=ImportError("No module named 'redis'")):
            await cache_service.initialize()
            
            assert cache_service.cache_enabled is False
    
    def test_generate_cache_key(self, cache_service, sample_config):
        """测试缓存键生成"""
        query = "测试查询"
        
        cache_key = cache_service._generate_cache_key(query, sample_config)
        
        assert cache_key.startswith("retrieval:")
        assert len(cache_key) == 42  # "retrieval:" + 32位MD5哈希
        
        # 相同参数应该生成相同的键
        cache_key2 = cache_service._generate_cache_key(query, sample_config)
        assert cache_key == cache_key2
        
        # 不同参数应该生成不同的键
        different_config = RetrievalConfig(
            search_mode='keyword',
            top_k=10,
            similarity_threshold=0.8,
            enable_rerank=False,
            enable_cache=True
        )
        cache_key3 = cache_service._generate_cache_key(query, different_config)
        assert cache_key != cache_key3
    
    def test_generate_cache_key_with_kwargs(self, cache_service, sample_config):
        """测试带额外参数的缓存键生成"""
        query = "测试查询"
        
        cache_key1 = cache_service._generate_cache_key(query, sample_config)
        cache_key2 = cache_service._generate_cache_key(
            query, sample_config, user_id="user123", department="tech"
        )
        
        # 额外参数应该影响缓存键
        assert cache_key1 != cache_key2
        
        # 相同的额外参数应该生成相同的键
        cache_key3 = cache_service._generate_cache_key(
            query, sample_config, user_id="user123", department="tech"
        )
        assert cache_key2 == cache_key3
    
    def test_serialize_results(self, cache_service, sample_results):
        """测试检索结果序列化"""
        serialized = cache_service._serialize_results(sample_results)
        
        assert isinstance(serialized, str)
        
        # 验证JSON格式
        data = json.loads(serialized)
        assert 'results' in data
        assert 'cached_at' in data
        assert 'count' in data
        assert data['count'] == 3
        assert len(data['results']) == 3
        
        # 验证结果内容
        first_result = data['results'][0]
        assert first_result['content'] == "这是第一个测试文档的内容"
        assert first_result['similarity_score'] == 0.95
        assert 'chunk_id' in first_result
        assert 'document_id' in first_result
    
    def test_deserialize_results(self, cache_service, sample_results):
        """测试检索结果反序列化"""
        # 先序列化
        serialized = cache_service._serialize_results(sample_results)
        
        # 再反序列化
        deserialized = cache_service._deserialize_results(serialized)
        
        assert len(deserialized) == 3
        assert isinstance(deserialized[0], SearchResult)
        assert deserialized[0].content == "这是第一个测试文档的内容"
        assert deserialized[0].similarity_score == 0.95
        assert deserialized[1].similarity_score == 0.88
        assert deserialized[2].similarity_score == 0.82
    
    def test_serialize_deserialize_roundtrip(self, cache_service, sample_results):
        """测试序列化-反序列化往返"""
        # 序列化后再反序列化，应该得到相同的结果
        serialized = cache_service._serialize_results(sample_results)
        deserialized = cache_service._deserialize_results(serialized)
        
        assert len(deserialized) == len(sample_results)
        
        for original, restored in zip(sample_results, deserialized):
            assert original.content == restored.content
            assert original.similarity_score == restored.similarity_score
            assert original.metadata == restored.metadata
            assert original.chunk_id == restored.chunk_id
            assert original.document_id == restored.document_id
    
    @pytest.mark.asyncio
    async def test_get_cached_results_cache_disabled(self, cache_service, sample_config):
        """测试缓存禁用时的获取操作"""
        cache_service.cache_enabled = False
        
        result = await cache_service.get_cached_results("测试查询", sample_config)
        
        assert result is None
        assert cache_service.cache_stats['total_requests'] == 0
    
    @pytest.mark.asyncio
    async def test_get_cached_results_config_disabled(self, cache_service):
        """测试配置禁用缓存时的获取操作"""
        cache_service.cache_enabled = True
        config = RetrievalConfig(enable_cache=False)
        
        result = await cache_service.get_cached_results("测试查询", config)
        
        assert result is None
        assert cache_service.cache_stats['total_requests'] == 0
    
    @pytest.mark.asyncio
    async def test_get_cached_results_hit(self, cache_service, sample_config, sample_results):
        """测试缓存命中"""
        cache_service.cache_enabled = True
        
        # 模拟Redis客户端
        mock_redis = AsyncMock()
        serialized_data = cache_service._serialize_results(sample_results)
        mock_redis.get.return_value = serialized_data
        cache_service.redis_client = mock_redis
        
        result = await cache_service.get_cached_results("测试查询", sample_config)
        
        assert result is not None
        assert len(result) == 3
        assert result[0].content == "这是第一个测试文档的内容"
        assert cache_service.cache_stats['hits'] == 1
        assert cache_service.cache_stats['total_requests'] == 1
    
    @pytest.mark.asyncio
    async def test_get_cached_results_miss(self, cache_service, sample_config):
        """测试缓存未命中"""
        cache_service.cache_enabled = True
        
        # 模拟Redis客户端返回None
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        cache_service.redis_client = mock_redis
        
        result = await cache_service.get_cached_results("测试查询", sample_config)
        
        assert result is None
        assert cache_service.cache_stats['misses'] == 1
        assert cache_service.cache_stats['total_requests'] == 1
    
    @pytest.mark.asyncio
    async def test_get_cached_results_error(self, cache_service, sample_config):
        """测试缓存读取错误"""
        cache_service.cache_enabled = True
        
        # 模拟Redis客户端抛出异常
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = Exception("Redis读取失败")
        cache_service.redis_client = mock_redis
        
        result = await cache_service.get_cached_results("测试查询", sample_config)
        
        assert result is None
        assert cache_service.cache_stats['errors'] == 1
        assert cache_service.cache_stats['total_requests'] == 1
    
    @pytest.mark.asyncio
    async def test_cache_results_success(self, cache_service, sample_config, sample_results):
        """测试缓存写入成功"""
        cache_service.cache_enabled = True
        
        # 模拟Redis客户端
        mock_redis = AsyncMock()
        cache_service.redis_client = mock_redis
        
        await cache_service.cache_results("测试查询", sample_config, sample_results)
        
        # 验证Redis写入调用
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == 1800  # TTL
        
        # 验证序列化的数据
        serialized_data = call_args[0][2]
        data = json.loads(serialized_data)
        assert data['count'] == 3
    
    @pytest.mark.asyncio
    async def test_cache_results_disabled(self, cache_service, sample_results):
        """测试缓存禁用时的写入操作"""
        cache_service.cache_enabled = False
        config = RetrievalConfig(enable_cache=True)
        
        # 不应该有任何Redis操作
        await cache_service.cache_results("测试查询", config, sample_results)
        
        # 没有Redis客户端，所以不会有错误
        assert cache_service.cache_stats['errors'] == 0
    
    @pytest.mark.asyncio
    async def test_cache_results_config_disabled(self, cache_service, sample_results):
        """测试配置禁用缓存时的写入操作"""
        cache_service.cache_enabled = True
        config = RetrievalConfig(enable_cache=False)
        
        await cache_service.cache_results("测试查询", config, sample_results)
        
        # 不应该有Redis操作
        assert cache_service.redis_client is None
    
    @pytest.mark.asyncio
    async def test_cache_results_empty_results(self, cache_service, sample_config):
        """测试缓存空结果"""
        cache_service.cache_enabled = True
        
        await cache_service.cache_results("测试查询", sample_config, [])
        
        # 空结果不应该被缓存
        assert cache_service.redis_client is None
    
    @pytest.mark.asyncio
    async def test_cache_results_error(self, cache_service, sample_config, sample_results):
        """测试缓存写入错误"""
        cache_service.cache_enabled = True
        
        # 模拟Redis客户端抛出异常
        mock_redis = AsyncMock()
        mock_redis.setex.side_effect = Exception("Redis写入失败")
        cache_service.redis_client = mock_redis
        
        await cache_service.cache_results("测试查询", sample_config, sample_results)
        
        assert cache_service.cache_stats['errors'] == 1
    
    @pytest.mark.asyncio
    async def test_clear_cache(self, cache_service):
        """测试缓存清理"""
        cache_service.cache_enabled = True
        
        # 模拟Redis客户端
        mock_redis = AsyncMock()
        mock_redis.keys.return_value = ['retrieval:key1', 'retrieval:key2', 'retrieval:key3']
        mock_redis.delete.return_value = 3
        cache_service.redis_client = mock_redis
        
        deleted_count = await cache_service.clear_cache()
        
        assert deleted_count == 3
        mock_redis.keys.assert_called_once_with("retrieval:*")
        mock_redis.delete.assert_called_once_with('retrieval:key1', 'retrieval:key2', 'retrieval:key3')
    
    @pytest.mark.asyncio
    async def test_clear_cache_with_pattern(self, cache_service):
        """测试按模式清理缓存"""
        cache_service.cache_enabled = True
        
        # 模拟Redis客户端
        mock_redis = AsyncMock()
        mock_redis.keys.return_value = ['user_retrieval:key1']
        mock_redis.delete.return_value = 1
        cache_service.redis_client = mock_redis
        
        deleted_count = await cache_service.clear_cache("user_retrieval:*")
        
        assert deleted_count == 1
        mock_redis.keys.assert_called_once_with("user_retrieval:*")
    
    @pytest.mark.asyncio
    async def test_clear_cache_no_keys(self, cache_service):
        """测试清理缓存时没有匹配的键"""
        cache_service.cache_enabled = True
        
        # 模拟Redis客户端
        mock_redis = AsyncMock()
        mock_redis.keys.return_value = []
        cache_service.redis_client = mock_redis
        
        deleted_count = await cache_service.clear_cache()
        
        assert deleted_count == 0
        mock_redis.delete.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_cache_info(self, cache_service):
        """测试获取缓存信息"""
        # 设置一些统计数据
        cache_service.cache_stats = {
            'hits': 80,
            'misses': 20,
            'errors': 2,
            'total_requests': 102
        }
        cache_service.cache_enabled = True
        
        # 模拟Redis客户端
        mock_redis = AsyncMock()
        mock_redis.info.return_value = {
            'used_memory': 1024000,
            'used_memory_human': '1000K',
            'maxmemory': 10240000
        }
        mock_redis.keys.return_value = ['retrieval:key1', 'retrieval:key2']
        cache_service.redis_client = mock_redis
        
        info = await cache_service.get_cache_info()
        
        assert info['enabled'] is True
        assert info['ttl'] == cache_service.cache_ttl
        assert info['hit_rate'] == 80/102
        assert info['miss_rate'] == 20/102
        assert info['error_rate'] == 2/102
        assert info['cached_queries'] == 2
        assert 'redis_memory' in info
    
    @pytest.mark.asyncio
    async def test_get_cache_info_disabled(self, cache_service):
        """测试缓存禁用时的信息获取"""
        cache_service.cache_enabled = False
        
        info = await cache_service.get_cache_info()
        
        assert info['enabled'] is False
        assert info['hit_rate'] == 0.0
        assert 'redis_memory' not in info
    
    @pytest.mark.asyncio
    async def test_warm_up_cache(self, cache_service):
        """测试缓存预热"""
        cache_service.cache_enabled = True
        
        # 模拟Redis客户端
        mock_redis = AsyncMock()
        mock_redis.exists.return_value = False  # 假设缓存不存在
        cache_service.redis_client = mock_redis
        
        common_queries = [
            {
                'query': '什么是人工智能？',
                'config': {'search_mode': 'semantic', 'top_k': 5}
            },
            {
                'query': '机器学习的应用',
                'config': {'search_mode': 'hybrid', 'top_k': 10}
            }
        ]
        
        warmed_count = await cache_service.warm_up_cache(common_queries)
        
        assert warmed_count == 2
        assert mock_redis.exists.call_count == 2
    
    @pytest.mark.asyncio
    async def test_close(self, cache_service):
        """测试关闭缓存服务"""
        # 模拟Redis客户端
        mock_redis = AsyncMock()
        cache_service.redis_client = mock_redis
        
        await cache_service.close()
        
        mock_redis.close.assert_called_once()
    
    def test_reset_stats(self, cache_service):
        """测试重置统计信息"""
        # 设置一些统计数据
        cache_service.cache_stats = {
            'hits': 50,
            'misses': 30,
            'errors': 5,
            'total_requests': 85
        }
        
        cache_service.reset_stats()
        
        assert cache_service.cache_stats['hits'] == 0
        assert cache_service.cache_stats['misses'] == 0
        assert cache_service.cache_stats['errors'] == 0
        assert cache_service.cache_stats['total_requests'] == 0


class TestCacheKeyGenerator:
    """缓存键生成器测试类"""
    
    def test_generate_user_key(self):
        """测试生成用户特定缓存键"""
        config = RetrievalConfig(search_mode='semantic', top_k=5)
        
        key = CacheKeyGenerator.generate_user_key("user123", "测试查询", config)
        
        assert key.startswith("user_retrieval:")
        assert len(key) == 47  # "user_retrieval:" + 32位MD5哈希
        
        # 相同参数应该生成相同的键
        key2 = CacheKeyGenerator.generate_user_key("user123", "测试查询", config)
        assert key == key2
        
        # 不同用户应该生成不同的键
        key3 = CacheKeyGenerator.generate_user_key("user456", "测试查询", config)
        assert key != key3
    
    def test_generate_department_key(self):
        """测试生成部门特定缓存键"""
        config = RetrievalConfig(search_mode='semantic', top_k=5)
        
        key = CacheKeyGenerator.generate_department_key("dept123", "测试查询", config)
        
        assert key.startswith("dept_retrieval:")
        assert len(key) == 47  # "dept_retrieval:" + 32位MD5哈希
        
        # 相同参数应该生成相同的键
        key2 = CacheKeyGenerator.generate_department_key("dept123", "测试查询", config)
        assert key == key2
        
        # 不同部门应该生成不同的键
        key3 = CacheKeyGenerator.generate_department_key("dept456", "测试查询", config)
        assert key != key3


@pytest.mark.asyncio
async def test_cache_retrieval_results_decorator():
    """测试缓存装饰器"""
    # 创建模拟的缓存服务
    mock_cache_service = AsyncMock()
    mock_cache_service.get_cached_results.return_value = None  # 缓存未命中
    
    from rag_system.services.cache_service import cache_retrieval_results
    
    # 创建被装饰的函数
    @cache_retrieval_results(mock_cache_service)
    async def mock_retrieval_function(self, query: str, config: RetrievalConfig, **kwargs):
        import uuid
        return [SearchResult(
            chunk_id=str(uuid.uuid4()),
            document_id=str(uuid.uuid4()),
            content=f"结果: {query}", 
            metadata={}, 
            similarity_score=0.9
        )]
    
    # 创建模拟的self对象
    mock_self = Mock()
    config = RetrievalConfig(enable_cache=True)
    
    # 调用装饰后的函数
    results = await mock_retrieval_function(mock_self, "测试查询", config)
    
    # 验证缓存操作
    mock_cache_service.get_cached_results.assert_called_once_with("测试查询", config)
    mock_cache_service.cache_results.assert_called_once()
    
    # 验证结果
    assert len(results) == 1
    assert results[0].content == "结果: 测试查询"


if __name__ == "__main__":
    pytest.main([__file__])