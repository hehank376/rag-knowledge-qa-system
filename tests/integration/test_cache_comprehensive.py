"""
缓存功能综合测试套件

测试缓存功能的完整性和性能：
- 缓存存取和过期机制测试
- 缓存键生成正确性和唯一性测试
- 缓存失败时的降级行为测试
- 缓存性能测试和命中率验证
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from rag_system.services.cache_service import CacheService
from rag_system.services.cache_manager import CacheManager, CachePolicy
from rag_system.services.cache_monitor import CacheMonitor
from rag_system.services.enhanced_retrieval_service import EnhancedRetrievalService
from rag_system.models.config import RetrievalConfig
from rag_system.models.vector import SearchResult


class TestCacheStorageAndExpiration:
    """缓存存取和过期机制测试"""
    
    @pytest.fixture
    def cache_service(self):
        """缓存服务fixture"""
        config = {
            'cache_ttl': 2,  # 2秒TTL用于测试
            'redis_host': 'localhost',
            'redis_port': 6379,
            'redis_db': 1
        }
        return CacheService(config)
    
    @pytest.fixture
    def sample_results(self):
        """示例检索结果"""
        import uuid
        return [
            SearchResult(
                chunk_id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content="缓存测试文档1",
                similarity_score=0.95,
                metadata={"source": "test1.txt"}
            ),
            SearchResult(
                chunk_id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content="缓存测试文档2",
                similarity_score=0.88,
                metadata={"source": "test2.txt"}
            )
        ]
    
    @pytest.mark.asyncio
    async def test_cache_storage_and_retrieval(self, cache_service, sample_results):
        """测试缓存的正确存储和检索"""
        with patch('redis.asyncio.Redis') as mock_redis_class:
            mock_redis = AsyncMock()
            mock_redis.ping.return_value = True
            mock_redis_class.return_value = mock_redis
            
            await cache_service.initialize()
            
            config = RetrievalConfig(
                search_mode='semantic',
                enable_cache=True,
                top_k=5
            )
            
            query = "测试缓存存储"
            
            # 第一次获取 - 缓存未命中
            mock_redis.get.return_value = None
            cached_results = await cache_service.get_cached_results(query, config)
            assert cached_results is None
            
            # 缓存结果
            await cache_service.cache_results(query, config, sample_results)
            mock_redis.setex.assert_called_once()
            
            # 验证TTL设置
            call_args = mock_redis.setex.call_args
            assert call_args[0][1] == 2  # TTL为2秒
            
            # 第二次获取 - 缓存命中
            serialized_data = cache_service._serialize_results(sample_results)
            mock_redis.get.return_value = serialized_data
            
            cached_results = await cache_service.get_cached_results(query, config)
            assert cached_results is not None
            assert len(cached_results) == 2
            assert cached_results[0].content == "缓存测试文档1"
    
    @pytest.mark.asyncio
    async def test_cache_expiration_mechanism(self, cache_service, sample_results):
        """测试缓存过期机制"""
        with patch('redis.asyncio.Redis') as mock_redis_class:
            mock_redis = AsyncMock()
            mock_redis.ping.return_value = True
            mock_redis_class.return_value = mock_redis
            
            await cache_service.initialize()
            
            config = RetrievalConfig(enable_cache=True)
            query = "测试缓存过期"
            
            # 缓存结果
            await cache_service.cache_results(query, config, sample_results)
            
            # 验证使用了正确的TTL
            mock_redis.setex.assert_called_once()
            call_args = mock_redis.setex.call_args
            assert call_args[0][1] == 2  # 配置的TTL
    
    @pytest.mark.asyncio
    async def test_cache_data_integrity(self, cache_service, sample_results):
        """测试缓存数据完整性"""
        # 测试序列化和反序列化的数据完整性
        serialized = cache_service._serialize_results(sample_results)
        deserialized = cache_service._deserialize_results(serialized)
        
        assert len(deserialized) == len(sample_results)
        
        for original, restored in zip(sample_results, deserialized):
            assert original.content == restored.content
            assert original.similarity_score == restored.similarity_score
            assert original.metadata == restored.metadata
            assert original.chunk_id == restored.chunk_id
            assert original.document_id == restored.document_id


class TestCacheKeyGeneration:
    """缓存键生成正确性和唯一性测试"""
    
    @pytest.fixture
    def cache_service(self):
        """缓存服务fixture"""
        return CacheService()
    
    def test_cache_key_uniqueness(self, cache_service):
        """测试缓存键的唯一性"""
        # 相同参数应该生成相同的键
        config1 = RetrievalConfig(
            search_mode='semantic',
            top_k=5,
            similarity_threshold=0.7,
            enable_rerank=True
        )
        
        config2 = RetrievalConfig(
            search_mode='semantic',
            top_k=5,
            similarity_threshold=0.7,
            enable_rerank=True
        )
        
        query = "测试查询"
        
        key1 = cache_service._generate_cache_key(query, config1)
        key2 = cache_service._generate_cache_key(query, config2)
        
        assert key1 == key2
        assert key1.startswith("retrieval:")
        assert len(key1) == 42  # "retrieval:" + 32位MD5哈希
    
    def test_cache_key_differentiation(self, cache_service):
        """测试不同参数生成不同的缓存键"""
        base_config = RetrievalConfig(
            search_mode='semantic',
            top_k=5,
            similarity_threshold=0.7,
            enable_rerank=False
        )
        
        query = "测试查询"
        base_key = cache_service._generate_cache_key(query, base_config)
        
        # 测试不同查询
        different_query_key = cache_service._generate_cache_key("不同查询", base_config)
        assert base_key != different_query_key
        
        # 测试不同搜索模式
        different_mode_config = RetrievalConfig(
            search_mode='keyword',
            top_k=5,
            similarity_threshold=0.7,
            enable_rerank=False
        )
        different_mode_key = cache_service._generate_cache_key(query, different_mode_config)
        assert base_key != different_mode_key
        
        # 测试不同top_k
        different_topk_config = RetrievalConfig(
            search_mode='semantic',
            top_k=10,
            similarity_threshold=0.7,
            enable_rerank=False
        )
        different_topk_key = cache_service._generate_cache_key(query, different_topk_config)
        assert base_key != different_topk_key
        
        # 测试不同相似度阈值
        different_threshold_config = RetrievalConfig(
            search_mode='semantic',
            top_k=5,
            similarity_threshold=0.8,
            enable_rerank=False
        )
        different_threshold_key = cache_service._generate_cache_key(query, different_threshold_config)
        assert base_key != different_threshold_key
        
        # 测试不同重排序设置
        different_rerank_config = RetrievalConfig(
            search_mode='semantic',
            top_k=5,
            similarity_threshold=0.7,
            enable_rerank=True
        )
        different_rerank_key = cache_service._generate_cache_key(query, different_rerank_config)
        assert base_key != different_rerank_key
    
    def test_cache_key_with_additional_params(self, cache_service):
        """测试带额外参数的缓存键生成"""
        config = RetrievalConfig(search_mode='semantic')
        query = "测试查询"
        
        # 无额外参数
        key1 = cache_service._generate_cache_key(query, config)
        
        # 有额外参数
        key2 = cache_service._generate_cache_key(query, config, user_id="user123")
        key3 = cache_service._generate_cache_key(query, config, user_id="user456")
        key4 = cache_service._generate_cache_key(query, config, user_id="user123", department="tech")
        
        # 所有键都应该不同
        keys = [key1, key2, key3, key4]
        assert len(set(keys)) == 4
        
        # 相同额外参数应该生成相同的键
        key5 = cache_service._generate_cache_key(query, config, user_id="user123")
        assert key2 == key5
    
    def test_cache_key_consistency(self, cache_service):
        """测试缓存键生成的一致性"""
        config = RetrievalConfig(search_mode='hybrid', top_k=10)
        query = "一致性测试查询"
        
        # 多次生成应该得到相同的键
        keys = []
        for _ in range(10):
            key = cache_service._generate_cache_key(query, config)
            keys.append(key)
        
        # 所有键都应该相同
        assert len(set(keys)) == 1
        
        # 键应该是有效的格式
        key = keys[0]
        assert key.startswith("retrieval:")
        assert len(key) == 42
        
        # 哈希部分应该是有效的十六进制
        hash_part = key[10:]  # 去掉"retrieval:"前缀
        assert len(hash_part) == 32
        assert all(c in '0123456789abcdef' for c in hash_part)


class TestCacheFallbackBehavior:
    """缓存失败时的降级行为测试"""
    
    @pytest.fixture
    def enhanced_service(self):
        """增强检索服务fixture"""
        config = {
            'cache_ttl': 3600,
            'redis_host': 'localhost',
            'redis_port': 6379
        }
        return EnhancedRetrievalService(config)
    
    @pytest.fixture
    def sample_results(self):
        """示例检索结果"""
        import uuid
        return [
            SearchResult(
                chunk_id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content="降级测试文档",
                similarity_score=0.9,
                metadata={"source": "fallback_test.txt"}
            )
        ]
    
    @pytest.mark.asyncio
    async def test_cache_disabled_fallback(self, enhanced_service, sample_results):
        """测试缓存禁用时的降级行为"""
        with patch('rag_system.services.retrieval_service.RetrievalService') as mock_retrieval:
            # 设置检索服务模拟
            mock_retrieval_instance = AsyncMock()
            mock_retrieval.return_value = mock_retrieval_instance
            
            # 设置搜索路由器模拟
            enhanced_service.search_router = AsyncMock()
            enhanced_service.search_router.search_with_mode.return_value = sample_results
            
            # 缓存服务未初始化（cache_enabled = False）
            config = RetrievalConfig(
                search_mode='semantic',
                enable_cache=False,  # 配置禁用缓存
                top_k=5
            )
            
            results = await enhanced_service.search_with_config("测试查询", config)
            
            # 验证结果正常返回
            assert len(results) == 1
            assert results[0].content == "降级测试文档"
            
            # 验证搜索路由器被调用（因为缓存被禁用）
            enhanced_service.search_router.search_with_mode.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_redis_connection_failure_fallback(self, enhanced_service, sample_results):
        """测试Redis连接失败时的降级行为"""
        with patch('rag_system.services.retrieval_service.RetrievalService') as mock_retrieval:
            with patch('redis.asyncio.Redis') as mock_redis_class:
                # 设置Redis连接失败
                mock_redis = AsyncMock()
                mock_redis.ping.side_effect = Exception("Redis连接失败")
                mock_redis_class.return_value = mock_redis
                
                # 设置检索服务模拟
                mock_retrieval_instance = AsyncMock()
                mock_retrieval.return_value = mock_retrieval_instance
                
                # 设置搜索路由器模拟
                enhanced_service.search_router = AsyncMock()
                enhanced_service.search_router.search_with_mode.return_value = sample_results
                
                await enhanced_service.initialize()
                
                # 验证缓存服务未启用
                assert enhanced_service.cache_service.cache_enabled is False
                
                config = RetrievalConfig(
                    search_mode='semantic',
                    enable_cache=True,  # 配置启用但服务不可用
                    top_k=5
                )
                
                results = await enhanced_service.search_with_config("测试查询", config)
                
                # 验证结果正常返回（降级到直接检索）
                assert len(results) == 1
                assert results[0].content == "降级测试文档"
                
                # 验证搜索路由器被调用
                enhanced_service.search_router.search_with_mode.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cache_read_error_fallback(self, enhanced_service, sample_results):
        """测试缓存读取错误时的降级行为"""
        with patch('rag_system.services.retrieval_service.RetrievalService') as mock_retrieval:
            with patch('redis.asyncio.Redis') as mock_redis_class:
                # 设置Redis模拟
                mock_redis = AsyncMock()
                mock_redis.ping.return_value = True
                mock_redis.get.side_effect = Exception("Redis读取失败")
                mock_redis_class.return_value = mock_redis
                
                # 设置检索服务模拟
                mock_retrieval_instance = AsyncMock()
                mock_retrieval.return_value = mock_retrieval_instance
                
                # 设置搜索路由器模拟
                enhanced_service.search_router = AsyncMock()
                enhanced_service.search_router.search_with_mode.return_value = sample_results
                
                await enhanced_service.initialize()
                
                config = RetrievalConfig(
                    search_mode='semantic',
                    enable_cache=True,
                    top_k=5
                )
                
                results = await enhanced_service.search_with_config("测试查询", config)
                
                # 验证结果正常返回（降级到直接检索）
                assert len(results) == 1
                assert results[0].content == "降级测试文档"
                
                # 验证搜索路由器被调用
                enhanced_service.search_router.search_with_mode.assert_called_once()
                
                # 验证缓存错误被记录
                assert enhanced_service.cache_service.cache_stats['errors'] >= 1
    
    @pytest.mark.asyncio
    async def test_cache_write_error_fallback(self, enhanced_service, sample_results):
        """测试缓存写入错误时的降级行为"""
        with patch('rag_system.services.retrieval_service.RetrievalService') as mock_retrieval:
            with patch('redis.asyncio.Redis') as mock_redis_class:
                # 设置Redis模拟
                mock_redis = AsyncMock()
                mock_redis.ping.return_value = True
                mock_redis.get.return_value = None  # 缓存未命中
                mock_redis.setex.side_effect = Exception("Redis写入失败")
                mock_redis_class.return_value = mock_redis
                
                # 设置检索服务模拟
                mock_retrieval_instance = AsyncMock()
                mock_retrieval.return_value = mock_retrieval_instance
                
                # 设置搜索路由器模拟
                enhanced_service.search_router = AsyncMock()
                enhanced_service.search_router.search_with_mode.return_value = sample_results
                
                await enhanced_service.initialize()
                
                config = RetrievalConfig(
                    search_mode='semantic',
                    enable_cache=True,
                    top_k=5
                )
                
                results = await enhanced_service.search_with_config("测试查询", config)
                
                # 验证结果正常返回（即使缓存写入失败）
                assert len(results) == 1
                assert results[0].content == "降级测试文档"
                
                # 验证搜索路由器被调用
                enhanced_service.search_router.search_with_mode.assert_called_once()
                
                # 验证缓存写入被尝试
                mock_redis.setex.assert_called_once()


class TestCachePerformanceAndHitRate:
    """缓存性能测试和命中率验证"""
    
    @pytest.fixture
    def cache_service(self):
        """缓存服务fixture"""
        return CacheService({'cache_ttl': 3600})
    
    @pytest.fixture
    def enhanced_service(self):
        """增强检索服务fixture"""
        return EnhancedRetrievalService({'cache_ttl': 3600})
    
    @pytest.fixture
    def sample_results(self):
        """示例检索结果"""
        import uuid
        return [
            SearchResult(
                chunk_id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content=f"性能测试文档{i}",
                similarity_score=0.9 - i * 0.1,
                metadata={"source": f"perf_test_{i}.txt"}
            ) for i in range(5)
        ]
    
    @pytest.mark.asyncio
    async def test_cache_hit_rate_calculation(self, enhanced_service, sample_results):
        """测试缓存命中率计算"""
        with patch('rag_system.services.retrieval_service.RetrievalService') as mock_retrieval:
            with patch('redis.asyncio.Redis') as mock_redis_class:
                # 设置Redis模拟
                mock_redis = AsyncMock()
                mock_redis.ping.return_value = True
                mock_redis_class.return_value = mock_redis
                
                # 设置检索服务模拟
                mock_retrieval_instance = AsyncMock()
                mock_retrieval.return_value = mock_retrieval_instance
                
                # 设置搜索路由器模拟
                enhanced_service.search_router = AsyncMock()
                enhanced_service.search_router.search_with_mode.return_value = sample_results
                enhanced_service.search_router.get_usage_statistics.return_value = {}
                
                await enhanced_service.initialize()
                
                config = RetrievalConfig(
                    search_mode='semantic',
                    enable_cache=True,
                    top_k=5
                )
                
                # 模拟多次查询
                queries = ["查询1", "查询2", "查询3", "查询1", "查询2", "查询1"]
                
                # 设置缓存行为：前3次未命中，后3次命中
                serialized_data = enhanced_service.cache_service._serialize_results(sample_results)
                mock_redis.get.side_effect = [None, None, None, serialized_data, serialized_data, serialized_data]
                
                # 执行查询
                for query in queries:
                    await enhanced_service.search_with_config(query, config)
                
                # 获取统计信息
                stats = enhanced_service.get_search_statistics()
                cache_stats = stats['cache_statistics']
                
                # 验证统计信息
                assert cache_stats['total_requests'] == 6
                assert cache_stats['cache_hits'] == 3
                assert cache_stats['cache_misses'] == 3
                assert cache_stats['cache_hit_rate'] == 0.5  # 50%命中率
                assert cache_stats['cache_miss_rate'] == 0.5  # 50%未命中率
    
    @pytest.mark.asyncio
    async def test_cache_performance_metrics(self, cache_service):
        """测试缓存性能指标"""
        # 重置统计信息
        cache_service.reset_stats()
        
        # 模拟一些缓存操作统计
        cache_service.cache_stats['hits'] = 3
        cache_service.cache_stats['misses'] = 1
        cache_service.cache_stats['errors'] = 0
        cache_service.cache_stats['total_requests'] = 4
        
        # 获取缓存信息
        cache_info = await cache_service.get_cache_info()
        
        # 验证统计信息
        assert cache_info['stats']['total_requests'] == 4
        assert cache_info['hit_rate'] == 0.75  # 3/4命中
        assert cache_info['miss_rate'] == 0.25  # 1/4未命中
        assert cache_info['error_rate'] == 0.0  # 0错误
    
    @pytest.mark.asyncio
    async def test_cache_response_time_improvement(self, enhanced_service, sample_results):
        """测试缓存对响应时间的改善"""
        with patch('rag_system.services.retrieval_service.RetrievalService') as mock_retrieval:
            with patch('redis.asyncio.Redis') as mock_redis_class:
                # 设置Redis模拟
                mock_redis = AsyncMock()
                mock_redis.ping.return_value = True
                mock_redis_class.return_value = mock_redis
                
                # 设置检索服务模拟
                mock_retrieval_instance = AsyncMock()
                mock_retrieval.return_value = mock_retrieval_instance
                
                # 设置搜索路由器模拟（模拟慢速检索）
                async def slow_search(*args, **kwargs):
                    await asyncio.sleep(0.1)  # 模拟100ms的检索时间
                    return sample_results
                
                enhanced_service.search_router = AsyncMock()
                enhanced_service.search_router.search_with_mode.side_effect = slow_search
                enhanced_service.search_router.get_usage_statistics.return_value = {}
                
                await enhanced_service.initialize()
                
                config = RetrievalConfig(
                    search_mode='semantic',
                    enable_cache=True,
                    top_k=5
                )
                
                query = "性能测试查询"
                
                # 第一次查询（缓存未命中）
                mock_redis.get.return_value = None
                start_time = time.time()
                results1 = await enhanced_service.search_with_config(query, config)
                first_query_time = time.time() - start_time
                
                # 第二次查询（缓存命中）
                serialized_data = enhanced_service.cache_service._serialize_results(sample_results)
                mock_redis.get.return_value = serialized_data
                start_time = time.time()
                results2 = await enhanced_service.search_with_config(query, config)
                second_query_time = time.time() - start_time
                
                # 验证结果一致
                assert len(results1) == len(results2) == 5
                assert results1[0].content == results2[0].content
                
                # 验证缓存提升了性能（第二次查询应该更快）
                assert second_query_time < first_query_time
                
                # 验证统计信息
                stats = enhanced_service.get_search_statistics()
                cache_stats = stats['cache_statistics']
                assert cache_stats['cache_hits'] == 1
                assert cache_stats['cache_misses'] == 1
    
    def test_cache_memory_efficiency(self, cache_service, sample_results):
        """测试缓存内存效率"""
        # 测试序列化效率
        original_size = sum(len(result.content.encode('utf-8')) for result in sample_results)
        
        # 序列化数据
        serialized = cache_service._serialize_results(sample_results)
        serialized_size = len(serialized.encode('utf-8'))
        
        # 验证序列化数据包含必要信息
        assert 'results' in serialized
        assert 'cached_at' in serialized
        assert 'count' in serialized
        
        # 验证序列化效率（应该不会过度膨胀）
        # 由于JSON格式和元数据，序列化后的大小会比原始内容大，但不应该过度膨胀
        assert serialized_size > original_size  # 包含了元数据
        # 由于包含了完整的SearchResult结构和元数据，允许更大的膨胀率
        assert serialized_size < original_size * 15  # 允许合理的膨胀
        
        # 测试反序列化正确性
        deserialized = cache_service._deserialize_results(serialized)
        assert len(deserialized) == len(sample_results)
        
        # 验证数据完整性
        for original, restored in zip(sample_results, deserialized):
            assert original.content == restored.content
            assert original.similarity_score == restored.similarity_score


if __name__ == "__main__":
    pytest.main([__file__])