"""
重排序集成测试模块

测试重排序功能与检索流程的集成：
- 重排序在检索流程中的正确集成
- 根据配置决定是否启用重排序
- 重排序性能监控和统计
- 重排序错误处理和降级机制
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from rag_system.services.enhanced_retrieval_service import EnhancedRetrievalService
from rag_system.services.reranking_service import RerankingService
from rag_system.models.config import RetrievalConfig
from rag_system.models.vector import SearchResult


class TestRerankingIntegration:
    """重排序集成测试"""
    
    @pytest.fixture
    def enhanced_config(self):
        """增强检索服务配置"""
        return {
            'default_top_k': 5,
            'similarity_threshold': 0.7,
            'search_mode': 'semantic',
            'enable_rerank': True,
            'enable_cache': False,  # 禁用缓存以简化测试
            'model_name': 'test-rerank-model',
            'batch_size': 16,
            'timeout': 10.0
        }
    
    @pytest.fixture
    def enhanced_service(self, enhanced_config):
        """增强检索服务fixture"""
        return EnhancedRetrievalService(enhanced_config)
    
    @pytest.fixture
    def sample_results(self):
        """示例检索结果"""
        import uuid
        return [
            SearchResult(
                chunk_id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content=f"集成测试文档{i}的内容，包含相关信息",
                similarity_score=0.9 - i * 0.1,
                metadata={"source": f"test{i}.txt", "type": "document"}
            ) for i in range(5)
        ]
    
    @pytest.mark.asyncio
    async def test_service_initialization_with_reranking(self, enhanced_service):
        """测试服务初始化包含重排序组件"""
        # 模拟所有依赖服务的初始化
        with patch.object(enhanced_service.base_retrieval_service, 'initialize') as mock_base_init, \
             patch.object(enhanced_service.search_router, 'initialize') as mock_router_init, \
             patch.object(enhanced_service.cache_service, 'initialize') as mock_cache_init, \
             patch.object(enhanced_service.reranking_service, 'initialize') as mock_rerank_init:
            
            await enhanced_service.initialize()
            
            # 验证所有服务都被初始化
            mock_base_init.assert_called_once()
            mock_router_init.assert_called_once()
            mock_cache_init.assert_called_once()
            mock_rerank_init.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_with_reranking_enabled(self, enhanced_service, sample_results):
        """测试启用重排序的搜索"""
        # 模拟依赖服务
        enhanced_service.search_router.search_with_mode = AsyncMock(return_value=sample_results)
        enhanced_service.cache_service.get_cached_results = AsyncMock(return_value=None)
        enhanced_service.cache_service.cache_results = AsyncMock()
        
        # 模拟重排序结果
        reranked_results = sample_results.copy()
        reranked_results.reverse()  # 反转顺序模拟重排序
        for i, result in enumerate(reranked_results):
            result.similarity_score = 0.95 - i * 0.05
            result.metadata['rerank_score'] = result.similarity_score
            result.metadata['original_score'] = sample_results[i].similarity_score
        
        enhanced_service.reranking_service.rerank_results = AsyncMock(return_value=reranked_results)
        
        # 执行搜索
        config = RetrievalConfig(enable_rerank=True, enable_cache=False)
        results = await enhanced_service.search_with_config("测试查询", config)
        
        # 验证重排序被调用
        enhanced_service.reranking_service.rerank_results.assert_called_once()
        
        # 验证结果
        assert len(results) == len(sample_results)
        assert results == reranked_results
        
        # 验证统计信息更新
        assert enhanced_service.rerank_stats['total_rerank_requests'] == 1
        assert enhanced_service.rerank_stats['successful_reranks'] == 1
        assert enhanced_service.rerank_stats['failed_reranks'] == 0
    
    @pytest.mark.asyncio
    async def test_search_with_reranking_disabled(self, enhanced_service, sample_results):
        """测试禁用重排序的搜索"""
        # 模拟依赖服务
        enhanced_service.search_router.search_with_mode = AsyncMock(return_value=sample_results)
        enhanced_service.cache_service.get_cached_results = AsyncMock(return_value=None)
        enhanced_service.cache_service.cache_results = AsyncMock()
        enhanced_service.reranking_service.rerank_results = AsyncMock()
        
        # 执行搜索
        config = RetrievalConfig(enable_rerank=False, enable_cache=False)
        results = await enhanced_service.search_with_config("测试查询", config)
        
        # 验证重排序未被调用
        enhanced_service.reranking_service.rerank_results.assert_not_called()
        
        # 验证结果
        assert len(results) == len(sample_results)
        assert results == sample_results
        
        # 验证统计信息未更新
        assert enhanced_service.rerank_stats['total_rerank_requests'] == 0
    
    @pytest.mark.asyncio
    async def test_reranking_error_handling(self, enhanced_service, sample_results):
        """测试重排序错误处理和降级"""
        # 模拟依赖服务
        enhanced_service.search_router.search_with_mode = AsyncMock(return_value=sample_results)
        enhanced_service.cache_service.get_cached_results = AsyncMock(return_value=None)
        enhanced_service.cache_service.cache_results = AsyncMock()
        
        # 模拟重排序失败
        enhanced_service.reranking_service.rerank_results = AsyncMock(
            side_effect=Exception("重排序模型失败")
        )
        
        # 执行搜索
        config = RetrievalConfig(enable_rerank=True, enable_cache=False)
        results = await enhanced_service.search_with_config("测试查询", config)
        
        # 验证重排序被调用
        enhanced_service.reranking_service.rerank_results.assert_called_once()
        
        # 验证返回原始结果（降级）
        assert len(results) == len(sample_results)
        assert results == sample_results
        
        # 验证错误统计更新
        assert enhanced_service.rerank_stats['total_rerank_requests'] == 1
        assert enhanced_service.rerank_stats['successful_reranks'] == 0
        assert enhanced_service.rerank_stats['failed_reranks'] == 1
    
    @pytest.mark.asyncio
    async def test_reranking_performance_monitoring(self, enhanced_service, sample_results):
        """测试重排序性能监控"""
        # 模拟依赖服务
        enhanced_service.search_router.search_with_mode = AsyncMock(return_value=sample_results)
        enhanced_service.cache_service.get_cached_results = AsyncMock(return_value=None)
        enhanced_service.cache_service.cache_results = AsyncMock()
        
        # 模拟重排序结果（添加延迟）
        async def mock_rerank(*args, **kwargs):
            await asyncio.sleep(0.1)  # 模拟处理时间
            return sample_results
        
        enhanced_service.reranking_service.rerank_results = mock_rerank
        
        # 执行多次搜索
        config = RetrievalConfig(enable_rerank=True, enable_cache=False)
        
        for i in range(3):
            await enhanced_service.search_with_config(f"测试查询{i}", config)
        
        # 验证性能统计
        stats = enhanced_service.rerank_stats
        assert stats['total_rerank_requests'] == 3
        assert stats['successful_reranks'] == 3
        assert stats['failed_reranks'] == 0
        assert stats['total_rerank_time'] > 0.0
        assert stats['avg_rerank_time'] > 0.0
        assert stats['avg_rerank_time'] == stats['total_rerank_time'] / 3
    
    @pytest.mark.asyncio
    async def test_reranking_with_empty_results(self, enhanced_service):
        """测试空结果的重排序处理"""
        # 模拟依赖服务返回空结果
        enhanced_service.search_router.search_with_mode = AsyncMock(return_value=[])
        enhanced_service.cache_service.get_cached_results = AsyncMock(return_value=None)
        enhanced_service.cache_service.cache_results = AsyncMock()
        enhanced_service.reranking_service.rerank_results = AsyncMock()
        
        # 执行搜索
        config = RetrievalConfig(enable_rerank=True, enable_cache=False)
        results = await enhanced_service.search_with_config("测试查询", config)
        
        # 验证重排序未被调用（因为结果为空）
        enhanced_service.reranking_service.rerank_results.assert_not_called()
        
        # 验证返回空结果
        assert len(results) == 0
        
        # 验证统计信息未更新
        assert enhanced_service.rerank_stats['total_rerank_requests'] == 0
    
    @pytest.mark.asyncio
    async def test_get_reranking_metrics(self, enhanced_service):
        """测试获取重排序指标"""
        # 模拟重排序服务指标
        mock_metrics = {
            'model_loaded': True,
            'total_requests': 10,
            'successful_requests': 8,
            'failed_requests': 2,
            'success_rate': 0.8,
            'average_processing_time': 0.15
        }
        
        enhanced_service.reranking_service.get_metrics = Mock(return_value=mock_metrics)
        
        # 获取指标
        metrics = await enhanced_service.get_reranking_metrics()
        
        # 验证指标
        assert metrics == mock_metrics
        enhanced_service.reranking_service.get_metrics.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_preload_reranking_model(self, enhanced_service):
        """测试预加载重排序模型"""
        # 模拟预加载成功
        enhanced_service.reranking_service.preload_model = AsyncMock(return_value=True)
        
        # 执行预加载
        result = await enhanced_service.preload_reranking_model()
        
        # 验证结果
        assert result is True
        enhanced_service.reranking_service.preload_model.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_preload_reranking_model_failure(self, enhanced_service):
        """测试预加载重排序模型失败"""
        # 模拟预加载失败
        enhanced_service.reranking_service.preload_model = AsyncMock(
            side_effect=Exception("模型加载失败")
        )
        
        # 执行预加载
        result = await enhanced_service.preload_reranking_model()
        
        # 验证结果
        assert result is False
    
    @pytest.mark.asyncio
    async def test_health_check_with_reranking(self, enhanced_service):
        """测试包含重排序服务的健康检查"""
        # 模拟各服务的健康状态
        enhanced_service.search_router.health_check = AsyncMock(return_value={'status': 'healthy'})
        enhanced_service.cache_service.get_cache_info = AsyncMock(return_value={'enabled': True})
        enhanced_service.reranking_service.health_check = AsyncMock(return_value={
            'status': 'healthy',
            'model_loaded': True
        })
        
        # 执行健康检查
        health = await enhanced_service.health_check()
        
        # 验证健康状态
        assert health['status'] == 'healthy'
        assert 'reranking_service' in health['components']
        assert health['components']['reranking_service']['status'] == 'healthy'
        assert 'reranking_statistics' in health
    
    @pytest.mark.asyncio
    async def test_statistics_integration(self, enhanced_service, sample_results):
        """测试统计信息集成"""
        # 模拟依赖服务
        enhanced_service.search_router.search_with_mode = AsyncMock(return_value=sample_results)
        enhanced_service.search_router.get_usage_statistics = Mock(return_value={
            'semantic_searches': 1,
            'total_searches': 1
        })
        enhanced_service.cache_service.get_cached_results = AsyncMock(return_value=None)
        enhanced_service.cache_service.cache_results = AsyncMock()
        enhanced_service.reranking_service.rerank_results = AsyncMock(return_value=sample_results)
        enhanced_service.reranking_service.get_metrics = Mock(return_value={
            'total_requests': 1,
            'successful_requests': 1
        })
        
        # 执行搜索
        config = RetrievalConfig(enable_rerank=True, enable_cache=False)
        await enhanced_service.search_with_config("测试查询", config)
        
        # 获取统计信息
        stats = enhanced_service.get_search_statistics()
        
        # 验证统计信息包含重排序数据
        assert 'reranking_statistics' in stats
        rerank_stats = stats['reranking_statistics']
        assert rerank_stats['total_rerank_requests'] == 1
        assert rerank_stats['successful_reranks'] == 1
        assert rerank_stats['rerank_success_rate'] == 1.0
        assert 'reranking_service_metrics' in rerank_stats
    
    @pytest.mark.asyncio
    async def test_reset_statistics_with_reranking(self, enhanced_service):
        """测试重置统计信息包含重排序统计"""
        # 设置一些统计数据
        enhanced_service.rerank_stats['total_rerank_requests'] = 5
        enhanced_service.rerank_stats['successful_reranks'] = 4
        enhanced_service.rerank_stats['failed_reranks'] = 1
        
        # 模拟依赖服务的重置方法
        enhanced_service.search_router.reset_statistics = Mock()
        enhanced_service.cache_service.reset_stats = Mock()
        enhanced_service.reranking_service.reset_metrics = Mock()
        
        # 重置统计信息
        enhanced_service.reset_statistics()
        
        # 验证重排序统计被重置
        assert enhanced_service.rerank_stats['total_rerank_requests'] == 0
        assert enhanced_service.rerank_stats['successful_reranks'] == 0
        assert enhanced_service.rerank_stats['failed_reranks'] == 0
        
        # 验证所有服务的统计都被重置
        enhanced_service.search_router.reset_statistics.assert_called_once()
        enhanced_service.cache_service.reset_stats.assert_called_once()
        enhanced_service.reranking_service.reset_metrics.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup_with_reranking(self, enhanced_service):
        """测试清理资源包含重排序服务"""
        # 模拟各服务的清理方法
        enhanced_service.cache_service.close = AsyncMock()
        enhanced_service.reranking_service.close = AsyncMock()
        enhanced_service.search_router.cleanup = AsyncMock()
        enhanced_service.base_retrieval_service.cleanup = AsyncMock()
        
        # 执行清理
        await enhanced_service.cleanup()
        
        # 验证所有服务都被清理
        enhanced_service.cache_service.close.assert_called_once()
        enhanced_service.reranking_service.close.assert_called_once()
        enhanced_service.search_router.cleanup.assert_called_once()
        enhanced_service.base_retrieval_service.cleanup.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_test_search_with_reranking(self, enhanced_service, sample_results):
        """测试搜索测试功能包含重排序测试"""
        # 模拟依赖服务
        enhanced_service.search_router.search_with_mode = AsyncMock(return_value=sample_results)
        enhanced_service.cache_service.get_cached_results = AsyncMock(return_value=None)
        enhanced_service.cache_service.cache_results = AsyncMock()
        
        # 模拟重排序结果
        reranked_results = sample_results.copy()
        for result in reranked_results:
            result.metadata['rerank_score'] = result.similarity_score
        
        enhanced_service.reranking_service.rerank_results = AsyncMock(return_value=reranked_results)
        
        # 模拟服务统计方法
        enhanced_service.get_service_stats = AsyncMock(return_value={'test': 'stats'})
        enhanced_service.get_cache_info = AsyncMock(return_value={'cache': 'info'})
        enhanced_service.get_reranking_metrics = AsyncMock(return_value={'rerank': 'metrics'})
        
        # 执行测试搜索
        test_result = await enhanced_service.test_search("测试查询")
        
        # 验证测试结果
        assert test_result['success'] is True
        assert 'test_results' in test_result
        assert 'reranking_metrics' in test_result
        
        # 验证包含重排序开启和关闭的测试
        test_results = test_result['test_results']
        assert any('rerank_off' in key for key in test_results.keys())
        assert any('rerank_on' in key for key in test_results.keys())


if __name__ == "__main__":
    pytest.main([__file__])