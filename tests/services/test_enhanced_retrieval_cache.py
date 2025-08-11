"""
增强检索服务缓存集成测试

测试增强检索服务与缓存服务的集成：
- 缓存命中和未命中的流程
- 缓存统计信息收集
- 缓存管理功能
- 错误处理和降级
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from rag_system.services.enhanced_retrieval_service import EnhancedRetrievalService
from rag_system.models.config import RetrievalConfig
from rag_system.models.vector import SearchResult


class TestEnhancedRetrievalServiceCache:
    """增强检索服务缓存集成测试类"""
    
    @pytest.fixture
    def service_config(self):
        """服务配置"""
        return {
            'cache_ttl': 1800,
            'redis_host': 'localhost',
            'redis_port': 6379,
            'redis_db': 1,
            'enable_cache': True
        }
    
    @pytest.fixture
    def enhanced_service(self, service_config):
        """增强检索服务fixture"""
        return EnhancedRetrievalService(service_config)
    
    @pytest.fixture
    def sample_results(self):
        """示例检索结果"""
        import uuid
        return [
            SearchResult(
                chunk_id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content="缓存集成测试文档1",
                similarity_score=0.95,
                metadata={"source": "cache_test1.txt"}
            ),
            SearchResult(
                chunk_id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content="缓存集成测试文档2",
                similarity_score=0.88,
                metadata={"source": "cache_test2.txt"}
            )
        ]
    
    @pytest.mark.asyncio
    async def test_cache_integration_initialization(self, enhanced_service):
        """测试缓存集成初始化"""
        with patch('rag_system.services.retrieval_service.RetrievalService') as mock_retrieval:
            with patch('redis.asyncio.Redis') as mock_redis_class:
                mock_redis = AsyncMock()
                mock_redis.ping.return_value = True
                mock_redis_class.return_value = mock_redis
                
                mock_retrieval_instance = AsyncMock()
                mock_retrieval.return_value = mock_retrieval_instance
                
                await enhanced_service.initialize()
                
                # 验证缓存服务已初始化
                assert enhanced_service.cache_service is not None
                assert enhanced_service.cache_service.cache_enabled is True
    
    @pytest.mark.asyncio
    async def test_search_with_cache_miss(self, enhanced_service, sample_results):
        """测试缓存未命中的搜索流程"""
        with patch('rag_system.services.retrieval_service.RetrievalService') as mock_retrieval:
            with patch('redis.asyncio.Redis') as mock_redis_class:
                # 设置Redis模拟
                mock_redis = AsyncMock()
                mock_redis.ping.return_value = True
                mock_redis.get.return_value = None  # 缓存未命中
                mock_redis_class.return_value = mock_redis
                
                # 设置检索服务模拟
                mock_retrieval_instance = AsyncMock()
                mock_retrieval.return_value = mock_retrieval_instance
                
                # 设置搜索路由器模拟
                enhanced_service.search_router = AsyncMock()
                enhanced_service.search_router.search_with_mode.return_value = sample_results
                
                await enhanced_service.initialize()
                
                # 执行搜索
                config = RetrievalConfig(
                    search_mode='semantic',
                    enable_cache=True,
                    top_k=5
                )
                
                results = await enhanced_service.search_with_config("测试查询", config)
                
                # 验证结果
                assert len(results) == 2
                assert results[0].content == "缓存集成测试文档1"
                
                # 验证统计信息
                assert enhanced_service.cache_stats['total_requests'] == 1
                assert enhanced_service.cache_stats['cache_misses'] == 1
                assert enhanced_service.cache_stats['cache_hits'] == 0
                
                # 验证缓存写入被调用
                mock_redis.setex.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_with_cache_hit(self, enhanced_service, sample_results):
        """测试缓存命中的搜索流程"""
        with patch('rag_system.services.retrieval_service.RetrievalService') as mock_retrieval:
            with patch('redis.asyncio.Redis') as mock_redis_class:
                # 设置Redis模拟
                mock_redis = AsyncMock()
                mock_redis.ping.return_value = True
                
                # 模拟缓存命中
                serialized_data = enhanced_service.cache_service._serialize_results(sample_results)
                mock_redis.get.return_value = serialized_data
                mock_redis_class.return_value = mock_redis
                
                # 设置检索服务模拟
                mock_retrieval_instance = AsyncMock()
                mock_retrieval.return_value = mock_retrieval_instance
                
                # 设置搜索路由器模拟（不应该被调用）
                enhanced_service.search_router = AsyncMock()
                enhanced_service.search_router.search_with_mode = AsyncMock()
                
                await enhanced_service.initialize()
                
                # 执行搜索
                config = RetrievalConfig(
                    search_mode='semantic',
                    enable_cache=True,
                    top_k=5
                )
                
                results = await enhanced_service.search_with_config("测试查询", config)
                
                # 验证结果
                assert len(results) == 2
                assert results[0].content == "缓存集成测试文档1"
                
                # 验证统计信息
                assert enhanced_service.cache_stats['total_requests'] == 1
                assert enhanced_service.cache_stats['cache_hits'] == 1
                assert enhanced_service.cache_stats['cache_misses'] == 0
                
                # 验证搜索路由器没有被调用
                enhanced_service.search_router.search_with_mode.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_search_with_cache_disabled(self, enhanced_service, sample_results):
        """测试缓存禁用时的搜索流程"""
        with patch('rag_system.services.retrieval_service.RetrievalService') as mock_retrieval:
            # 设置检索服务模拟
            mock_retrieval_instance = AsyncMock()
            mock_retrieval.return_value = mock_retrieval_instance
            
            # 设置搜索路由器模拟
            enhanced_service.search_router = AsyncMock()
            enhanced_service.search_router.search_with_mode.return_value = sample_results
            
            # 缓存服务未初始化（cache_enabled = False）
            
            # 执行搜索
            config = RetrievalConfig(
                search_mode='semantic',
                enable_cache=False,  # 配置禁用缓存
                top_k=5
            )
            
            results = await enhanced_service.search_with_config("测试查询", config)
            
            # 验证结果
            assert len(results) == 2
            assert results[0].content == "缓存集成测试文档1"
            
            # 验证统计信息
            assert enhanced_service.cache_stats['total_requests'] == 1
            assert enhanced_service.cache_stats['cache_hits'] == 0
            assert enhanced_service.cache_stats['cache_misses'] == 1  # 缓存未命中
    
    @pytest.mark.asyncio
    async def test_cache_error_handling(self, enhanced_service, sample_results):
        """测试缓存错误处理"""
        with patch('rag_system.services.retrieval_service.RetrievalService') as mock_retrieval:
            with patch('redis.asyncio.Redis') as mock_redis_class:
                # 设置Redis模拟
                mock_redis = AsyncMock()
                mock_redis.ping.return_value = True
                mock_redis.get.side_effect = Exception("Redis读取失败")
                mock_redis.setex.side_effect = Exception("Redis写入失败")
                mock_redis_class.return_value = mock_redis
                
                # 设置检索服务模拟
                mock_retrieval_instance = AsyncMock()
                mock_retrieval.return_value = mock_retrieval_instance
                
                # 设置搜索路由器模拟
                enhanced_service.search_router = AsyncMock()
                enhanced_service.search_router.search_with_mode.return_value = sample_results
                
                await enhanced_service.initialize()
                
                # 执行搜索
                config = RetrievalConfig(
                    search_mode='semantic',
                    enable_cache=True,
                    top_k=5
                )
                
                results = await enhanced_service.search_with_config("测试查询", config)
                
                # 验证结果仍然正常返回
                assert len(results) == 2
                assert results[0].content == "缓存集成测试文档1"
                
                # 验证错误统计（缓存服务的错误统计）
                cache_service_stats = enhanced_service.cache_service.cache_stats
                assert cache_service_stats['errors'] >= 1
    
    @pytest.mark.asyncio
    async def test_cache_statistics_collection(self, enhanced_service, sample_results):
        """测试缓存统计信息收集"""
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
                enhanced_service.search_router.get_usage_statistics.return_value = {'test': 'stats'}
                
                await enhanced_service.initialize()
                
                # 执行多次搜索
                config = RetrievalConfig(
                    search_mode='semantic',
                    enable_cache=True,
                    top_k=5
                )
                
                # 第一次搜索 - 缓存未命中
                mock_redis.get.return_value = None
                await enhanced_service.search_with_config("查询1", config)
                
                # 第二次搜索 - 缓存命中
                serialized_data = enhanced_service.cache_service._serialize_results(sample_results)
                mock_redis.get.return_value = serialized_data
                await enhanced_service.search_with_config("查询1", config)
                
                # 第三次搜索 - 不同查询，缓存未命中
                mock_redis.get.return_value = None
                await enhanced_service.search_with_config("查询2", config)
                
                # 获取统计信息
                stats = enhanced_service.get_search_statistics()
                
                # 验证统计信息
                cache_stats = stats['cache_statistics']
                assert cache_stats['total_requests'] == 3
                assert cache_stats['cache_hits'] == 1
                assert cache_stats['cache_misses'] == 2
                assert cache_stats['cache_hit_rate'] == 1/3
                assert cache_stats['cache_miss_rate'] == 2/3
    
    @pytest.mark.asyncio
    async def test_cache_management_functions(self, enhanced_service):
        """测试缓存管理功能"""
        with patch('rag_system.services.retrieval_service.RetrievalService') as mock_retrieval:
            with patch('redis.asyncio.Redis') as mock_redis_class:
                # 设置Redis模拟
                mock_redis = AsyncMock()
                mock_redis.ping.return_value = True
                mock_redis.keys.return_value = ['retrieval:key1', 'retrieval:key2']
                mock_redis.delete.return_value = 2
                mock_redis.info.return_value = {'used_memory': 1024}
                mock_redis_class.return_value = mock_redis
                
                # 设置检索服务模拟
                mock_retrieval_instance = AsyncMock()
                mock_retrieval.return_value = mock_retrieval_instance
                
                await enhanced_service.initialize()
                
                # 测试获取缓存信息
                cache_info = await enhanced_service.get_cache_info()
                assert cache_info['enabled'] is True
                
                # 测试清理缓存
                deleted_count = await enhanced_service.clear_cache()
                assert deleted_count == 2
                mock_redis.delete.assert_called_once()
                
                # 测试重置统计
                enhanced_service.cache_stats['cache_hits'] = 10
                enhanced_service.reset_statistics()
                assert enhanced_service.cache_stats['cache_hits'] == 0
    
    @pytest.mark.asyncio
    async def test_cache_warm_up(self, enhanced_service, sample_results):
        """测试缓存预热功能"""
        with patch('rag_system.services.retrieval_service.RetrievalService') as mock_retrieval:
            with patch('redis.asyncio.Redis') as mock_redis_class:
                # 设置Redis模拟
                mock_redis = AsyncMock()
                mock_redis.ping.return_value = True
                mock_redis.get.return_value = None  # 缓存不存在
                mock_redis_class.return_value = mock_redis
                
                # 设置检索服务模拟
                mock_retrieval_instance = AsyncMock()
                mock_retrieval.return_value = mock_retrieval_instance
                
                # 设置搜索路由器模拟
                enhanced_service.search_router = AsyncMock()
                enhanced_service.search_router.search_with_mode.return_value = sample_results
                
                await enhanced_service.initialize()
                
                # 预热查询列表
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
                
                # 执行预热
                warmed_count = await enhanced_service.warm_up_cache(common_queries)
                
                # 验证预热结果
                assert warmed_count == 2
                assert enhanced_service.search_router.search_with_mode.call_count == 2
    
    @pytest.mark.asyncio
    async def test_health_check_with_cache(self, enhanced_service):
        """测试包含缓存状态的健康检查"""
        with patch('rag_system.services.retrieval_service.RetrievalService') as mock_retrieval:
            with patch('redis.asyncio.Redis') as mock_redis_class:
                # 设置Redis模拟
                mock_redis = AsyncMock()
                mock_redis.ping.return_value = True
                mock_redis.info.return_value = {'used_memory': 1024}
                mock_redis.keys.return_value = ['retrieval:key1']
                mock_redis_class.return_value = mock_redis
                
                # 设置检索服务模拟
                mock_retrieval_instance = AsyncMock()
                mock_retrieval.return_value = mock_retrieval_instance
                
                # 设置搜索路由器模拟
                enhanced_service.search_router = AsyncMock()
                enhanced_service.search_router.health_check.return_value = {'status': 'healthy'}
                
                await enhanced_service.initialize()
                
                # 执行健康检查
                health_status = await enhanced_service.health_check()
                
                # 验证健康状态
                assert health_status['status'] == 'healthy'
                assert 'cache_service' in health_status['components']
                assert health_status['components']['cache_service']['status'] == 'healthy'
                assert health_status['components']['cache_service']['enabled'] is True
    
    @pytest.mark.asyncio
    async def test_test_search_with_cache(self, enhanced_service, sample_results):
        """测试搜索测试功能（包含缓存测试）"""
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
                enhanced_service.search_router.get_usage_statistics.return_value = {'test': 'stats'}
                
                await enhanced_service.initialize()
                
                # 第一次调用返回None（缓存未命中），第二次返回缓存数据（缓存命中）
                serialized_data = enhanced_service.cache_service._serialize_results(sample_results)
                mock_redis.get.side_effect = [None, serialized_data]
                
                # 执行测试搜索
                test_result = await enhanced_service.test_search("测试查询")
                
                # 验证测试结果
                assert test_result['success'] is True
                assert test_result['result_count'] == 2
                assert 'first_search_time' in test_result
                assert 'second_search_time' in test_result
                assert 'cache_hit_likely' in test_result
                assert 'cache_info' in test_result


if __name__ == "__main__":
    pytest.main([__file__])