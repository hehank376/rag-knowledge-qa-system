"""
缓存功能集成测试

测试缓存服务与检索系统的集成：
- 缓存功能的端到端测试
- 缓存命中和未命中的场景
- 缓存与不同搜索模式的集成
- 缓存性能和统计信息
- 缓存错误处理和降级
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from rag_system.services.cache_service import CacheService
from rag_system.services.search_mode_router import SearchModeRouter
from rag_system.services.enhanced_retrieval_service import EnhancedRetrievalService
from rag_system.models.config import RetrievalConfig
from rag_system.models.vector import SearchResult


class TestCacheIntegration:
    """缓存集成测试类"""
    
    @pytest.fixture
    def cache_config(self):
        """缓存配置"""
        return {
            'cache_ttl': 1800,
            'redis_host': 'localhost',
            'redis_port': 6379,
            'redis_db': 1
        }
    
    @pytest.fixture
    def cache_service(self, cache_config):
        """缓存服务fixture"""
        return CacheService(cache_config)
    
    @pytest.fixture
    def mock_retrieval_service(self):
        """模拟检索服务"""
        service = Mock()
        service.search_similar_documents = AsyncMock()
        service.search_by_keywords = AsyncMock()
        service.hybrid_search = AsyncMock()
        return service
    
    @pytest.fixture
    def search_router(self, mock_retrieval_service):
        """搜索路由器"""
        return SearchModeRouter(mock_retrieval_service)
    
    @pytest.fixture
    def sample_results(self):
        """示例检索结果"""
        import uuid
        return [
            SearchResult(
                chunk_id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content="缓存测试文档1的内容",
                similarity_score=0.95,
                metadata={"source": "cache_test1.txt"}
            ),
            SearchResult(
                chunk_id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content="缓存测试文档2的内容",
                similarity_score=0.88,
                metadata={"source": "cache_test2.txt"}
            )
        ]
    
    @pytest.mark.asyncio
    async def test_cache_enabled_end_to_end(self, cache_service, sample_results):
        """测试缓存启用时的端到端流程"""
        # 初始化缓存服务
        with patch('redis.asyncio.Redis') as mock_redis_class:
            mock_redis = AsyncMock()
            mock_redis.ping.return_value = True
            mock_redis.get.return_value = None  # 第一次缓存未命中
            mock_redis_class.return_value = mock_redis
            
            await cache_service.initialize()
            
            # 配置
            config = RetrievalConfig(
                search_mode='semantic',
                enable_cache=True,
                top_k=5
            )
            
            query = "测试缓存查询"
            
            # 第一次查询 - 缓存未命中
            cached_results = await cache_service.get_cached_results(query, config)
            assert cached_results is None
            assert cache_service.cache_stats['misses'] == 1
            
            # 缓存结果
            await cache_service.cache_results(query, config, sample_results)
            mock_redis.setex.assert_called_once()
            
            # 第二次查询 - 缓存命中
            serialized_data = cache_service._serialize_results(sample_results)
            mock_redis.get.return_value = serialized_data
            
            cached_results = await cache_service.get_cached_results(query, config)
            assert cached_results is not None
            assert len(cached_results) == 2
            assert cached_results[0].content == "缓存测试文档1的内容"
            assert cache_service.cache_stats['hits'] == 1
    
    @pytest.mark.asyncio
    async def test_cache_disabled_flow(self, cache_service, sample_results):
        """测试缓存禁用时的流程"""
        # 缓存服务未初始化，cache_enabled = False
        config = RetrievalConfig(
            search_mode='semantic',
            enable_cache=True,  # 配置启用但服务未启用
            top_k=5
        )
        
        query = "测试缓存禁用查询"
        
        # 获取缓存结果应该返回None
        cached_results = await cache_service.get_cached_results(query, config)
        assert cached_results is None
        assert cache_service.cache_stats['total_requests'] == 0
        
        # 缓存结果应该不执行任何操作
        await cache_service.cache_results(query, config, sample_results)
        # 没有Redis客户端，不会有错误
    
    @pytest.mark.asyncio
    async def test_cache_config_disabled(self, cache_service, sample_results):
        """测试配置禁用缓存时的流程"""
        # 初始化缓存服务
        with patch('redis.asyncio.Redis') as mock_redis_class:
            mock_redis = AsyncMock()
            mock_redis.ping.return_value = True
            mock_redis_class.return_value = mock_redis
            
            await cache_service.initialize()
            
            # 配置禁用缓存
            config = RetrievalConfig(
                search_mode='semantic',
                enable_cache=False,  # 配置禁用缓存
                top_k=5
            )
            
            query = "测试配置禁用缓存查询"
            
            # 获取缓存结果应该返回None
            cached_results = await cache_service.get_cached_results(query, config)
            assert cached_results is None
            assert cache_service.cache_stats['total_requests'] == 0
            
            # 缓存结果应该不执行任何操作
            await cache_service.cache_results(query, config, sample_results)
            mock_redis.setex.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_cache_key_generation_consistency(self, cache_service):
        """测试缓存键生成的一致性"""
        config1 = RetrievalConfig(
            search_mode='semantic',
            top_k=5,
            similarity_threshold=0.7,
            enable_rerank=True,
            enable_cache=True
        )
        
        config2 = RetrievalConfig(
            search_mode='semantic',
            top_k=5,
            similarity_threshold=0.7,
            enable_rerank=True,
            enable_cache=True
        )
        
        query = "测试缓存键一致性"
        
        # 相同配置应该生成相同的缓存键
        key1 = cache_service._generate_cache_key(query, config1)
        key2 = cache_service._generate_cache_key(query, config2)
        assert key1 == key2
        
        # 不同配置应该生成不同的缓存键
        config3 = RetrievalConfig(
            search_mode='keyword',  # 不同的搜索模式
            top_k=5,
            similarity_threshold=0.7,
            enable_rerank=True,
            enable_cache=True
        )
        
        key3 = cache_service._generate_cache_key(query, config3)
        assert key1 != key3
    
    @pytest.mark.asyncio
    async def test_cache_with_different_search_modes(self, cache_service, sample_results):
        """测试不同搜索模式的缓存"""
        with patch('redis.asyncio.Redis') as mock_redis_class:
            mock_redis = AsyncMock()
            mock_redis.ping.return_value = True
            mock_redis.get.return_value = None
            mock_redis_class.return_value = mock_redis
            
            await cache_service.initialize()
            
            query = "测试搜索模式缓存"
            
            # 语义搜索缓存
            semantic_config = RetrievalConfig(
                search_mode='semantic',
                enable_cache=True
            )
            
            await cache_service.cache_results(query, semantic_config, sample_results)
            
            # 关键词搜索缓存
            keyword_config = RetrievalConfig(
                search_mode='keyword',
                enable_cache=True
            )
            
            await cache_service.cache_results(query, keyword_config, sample_results)
            
            # 混合搜索缓存
            hybrid_config = RetrievalConfig(
                search_mode='hybrid',
                enable_cache=True
            )
            
            await cache_service.cache_results(query, hybrid_config, sample_results)
            
            # 应该有3次缓存写入调用
            assert mock_redis.setex.call_count == 3
            
            # 验证不同的缓存键
            call_args_list = mock_redis.setex.call_args_list
            cache_keys = [call[0][0] for call in call_args_list]
            
            # 所有缓存键应该不同
            assert len(set(cache_keys)) == 3
    
    @pytest.mark.asyncio
    async def test_cache_error_handling(self, cache_service, sample_results):
        """测试缓存错误处理"""
        with patch('redis.asyncio.Redis') as mock_redis_class:
            mock_redis = AsyncMock()
            mock_redis.ping.return_value = True
            mock_redis_class.return_value = mock_redis
            
            await cache_service.initialize()
            
            config = RetrievalConfig(
                search_mode='semantic',
                enable_cache=True
            )
            
            query = "测试缓存错误处理"
            
            # 模拟Redis读取错误
            mock_redis.get.side_effect = Exception("Redis读取失败")
            
            cached_results = await cache_service.get_cached_results(query, config)
            assert cached_results is None
            assert cache_service.cache_stats['errors'] == 1
            
            # 模拟Redis写入错误
            mock_redis.setex.side_effect = Exception("Redis写入失败")
            
            await cache_service.cache_results(query, config, sample_results)
            assert cache_service.cache_stats['errors'] == 2
    
    @pytest.mark.asyncio
    async def test_cache_statistics_collection(self, cache_service, sample_results):
        """测试缓存统计信息收集"""
        with patch('redis.asyncio.Redis') as mock_redis_class:
            mock_redis = AsyncMock()
            mock_redis.ping.return_value = True
            mock_redis_class.return_value = mock_redis
            
            await cache_service.initialize()
            
            config = RetrievalConfig(
                search_mode='semantic',
                enable_cache=True
            )
            
            # 模拟多次查询
            queries = ["查询1", "查询2", "查询3", "查询1"]  # 查询1重复
            
            # 第一轮：所有查询都未命中
            mock_redis.get.return_value = None
            
            for query in queries[:3]:  # 前3个查询
                result = await cache_service.get_cached_results(query, config)
                assert result is None
                await cache_service.cache_results(query, config, sample_results)
            
            # 第二轮：查询1命中缓存
            serialized_data = cache_service._serialize_results(sample_results)
            mock_redis.get.return_value = serialized_data
            
            result = await cache_service.get_cached_results("查询1", config)
            assert result is not None
            
            # 验证统计信息
            stats = cache_service.cache_stats
            assert stats['total_requests'] == 4
            assert stats['hits'] == 1
            assert stats['misses'] == 3
            assert stats['errors'] == 0
            
            # 获取缓存信息
            mock_redis.info.return_value = {'used_memory': 1024, 'used_memory_human': '1K'}
            mock_redis.keys.return_value = ['retrieval:key1', 'retrieval:key2']
            
            cache_info = await cache_service.get_cache_info()
            assert cache_info['enabled'] is True
            assert cache_info['hit_rate'] == 0.25  # 1/4
            assert cache_info['miss_rate'] == 0.75  # 3/4
            assert cache_info['cached_queries'] == 2
    
    @pytest.mark.asyncio
    async def test_cache_ttl_configuration(self, cache_service, sample_results):
        """测试缓存TTL配置"""
        with patch('redis.asyncio.Redis') as mock_redis_class:
            mock_redis = AsyncMock()
            mock_redis.ping.return_value = True
            mock_redis_class.return_value = mock_redis
            
            await cache_service.initialize()
            
            config = RetrievalConfig(
                search_mode='semantic',
                enable_cache=True
            )
            
            query = "测试TTL配置"
            
            await cache_service.cache_results(query, config, sample_results)
            
            # 验证TTL设置
            mock_redis.setex.assert_called_once()
            call_args = mock_redis.setex.call_args
            assert call_args[0][1] == 1800  # 配置的TTL值
    
    @pytest.mark.asyncio
    async def test_cache_clear_functionality(self, cache_service):
        """测试缓存清理功能"""
        with patch('redis.asyncio.Redis') as mock_redis_class:
            mock_redis = AsyncMock()
            mock_redis.ping.return_value = True
            mock_redis.keys.return_value = ['retrieval:key1', 'retrieval:key2', 'retrieval:key3']
            mock_redis.delete.return_value = 3
            mock_redis_class.return_value = mock_redis
            
            await cache_service.initialize()
            
            # 清理所有检索缓存
            deleted_count = await cache_service.clear_cache()
            
            assert deleted_count == 3
            mock_redis.keys.assert_called_once_with("retrieval:*")
            mock_redis.delete.assert_called_once_with('retrieval:key1', 'retrieval:key2', 'retrieval:key3')
    
    @pytest.mark.asyncio
    async def test_cache_warm_up(self, cache_service):
        """测试缓存预热功能"""
        with patch('redis.asyncio.Redis') as mock_redis_class:
            mock_redis = AsyncMock()
            mock_redis.ping.return_value = True
            mock_redis.exists.return_value = False  # 缓存不存在
            mock_redis_class.return_value = mock_redis
            
            await cache_service.initialize()
            
            # 常见查询列表
            common_queries = [
                {
                    'query': '什么是人工智能？',
                    'config': {
                        'search_mode': 'semantic',
                        'top_k': 5,
                        'enable_cache': True
                    }
                },
                {
                    'query': '机器学习的应用',
                    'config': {
                        'search_mode': 'hybrid',
                        'top_k': 10,
                        'enable_cache': True
                    }
                }
            ]
            
            warmed_count = await cache_service.warm_up_cache(common_queries)
            
            assert warmed_count == 2
            assert mock_redis.exists.call_count == 2
    
    @pytest.mark.asyncio
    async def test_cache_service_lifecycle(self, cache_service):
        """测试缓存服务生命周期"""
        with patch('redis.asyncio.Redis') as mock_redis_class:
            mock_redis = AsyncMock()
            mock_redis.ping.return_value = True
            mock_redis_class.return_value = mock_redis
            
            # 初始化
            await cache_service.initialize()
            assert cache_service.cache_enabled is True
            
            # 重置统计
            cache_service.cache_stats['hits'] = 10
            cache_service.reset_stats()
            assert cache_service.cache_stats['hits'] == 0
            
            # 关闭服务
            await cache_service.close()
            mock_redis.close.assert_called_once()


class TestCacheWithEnhancedRetrievalService:
    """测试缓存与增强检索服务的集成"""
    
    @pytest.fixture
    def enhanced_service_config(self):
        """增强检索服务配置"""
        return {
            'cache_ttl': 1800,
            'redis_host': 'localhost',
            'redis_port': 6379,
            'redis_db': 1
        }
    
    @pytest.mark.asyncio
    async def test_enhanced_service_with_cache(self, enhanced_service_config):
        """测试增强检索服务的缓存集成"""
        # 这个测试需要等待EnhancedRetrievalService完全实现后再完善
        # 目前只是一个占位符测试
        
        # 模拟增强检索服务
        with patch('rag_system.services.enhanced_retrieval_service.EnhancedRetrievalService') as MockService:
            mock_service = MockService.return_value
            mock_service.initialize = AsyncMock()
            mock_service.search_with_config = AsyncMock()
            
            # 创建服务实例
            service = MockService(enhanced_service_config)
            await service.initialize()
            
            # 验证初始化调用
            service.initialize.assert_called_once()
            
            # 这里可以添加更多的集成测试
            # 当EnhancedRetrievalService实现后


if __name__ == "__main__":
    pytest.main([__file__])