"""
重排序服务测试模块

测试重排序服务的各种功能：
- 重排序模型的加载和初始化
- 查询-文档对的重排序计算
- 重排序结果的分数更新和排序
- 错误处理和降级机制
- 性能监控和指标收集
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from rag_system.services.reranking_service import (
    RerankingService, 
    RerankingServiceManager,
    RerankingMetrics,
    rerank_results
)
from rag_system.models.config import RetrievalConfig
from rag_system.models.vector import SearchResult


class TestRerankingMetrics:
    """重排序指标测试"""
    
    def test_metrics_initialization(self):
        """测试指标初始化"""
        metrics = RerankingMetrics()
        
        assert metrics.total_requests == 0
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 0
        assert metrics.total_processing_time == 0.0
        assert metrics.average_processing_time == 0.0
        assert metrics.success_rate == 0.0
        assert metrics.failure_rate == 0.0
    
    def test_metrics_update_success(self):
        """测试成功请求指标更新"""
        metrics = RerankingMetrics()
        
        # 更新成功请求
        metrics.update_request(0.5, success=True)
        metrics.update_request(1.0, success=True)
        
        assert metrics.total_requests == 2
        assert metrics.successful_requests == 2
        assert metrics.failed_requests == 0
        assert metrics.total_processing_time == 1.5
        assert metrics.average_processing_time == 0.75
        assert metrics.success_rate == 1.0
        assert metrics.failure_rate == 0.0
        assert metrics.last_updated is not None
    
    def test_metrics_update_failure(self):
        """测试失败请求指标更新"""
        metrics = RerankingMetrics()
        
        # 更新失败请求
        metrics.update_request(0.3, success=False)
        metrics.update_request(0.7, success=True)
        
        assert metrics.total_requests == 2
        assert metrics.successful_requests == 1
        assert metrics.failed_requests == 1
        assert metrics.success_rate == 0.5
        assert metrics.failure_rate == 0.5


class TestRerankingService:
    """重排序服务测试"""
    
    @pytest.fixture
    def reranking_config(self):
        """重排序配置fixture"""
        return {
            'model_name': 'test-model',
            'max_length': 256,
            'batch_size': 16,
            'timeout': 10.0,
            'rerank_top_k': 20
        }
    
    @pytest.fixture
    def reranking_service(self, reranking_config):
        """重排序服务fixture"""
        return RerankingService(reranking_config)
    
    @pytest.fixture
    def sample_results(self):
        """示例检索结果"""
        import uuid
        return [
            SearchResult(
                chunk_id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content=f"重排序测试文档{i}的内容，包含一些相关信息",
                similarity_score=0.9 - i * 0.1,
                metadata={"source": f"test{i}.txt", "type": "document"}
            ) for i in range(5)
        ]
    
    def test_service_initialization(self, reranking_service, reranking_config):
        """测试服务初始化"""
        assert reranking_service.model_name == reranking_config['model_name']
        assert reranking_service.max_length == reranking_config['max_length']
        assert reranking_service.batch_size == reranking_config['batch_size']
        assert reranking_service.timeout == reranking_config['timeout']
        assert reranking_service.model_loaded is False
        assert reranking_service.reranker_model is None
        assert isinstance(reranking_service.metrics, RerankingMetrics)
    
    @pytest.mark.asyncio
    async def test_model_initialization_success(self, reranking_service):
        """测试模型初始化成功"""
        # 模拟_load_model方法
        def mock_load_model():
            reranking_service.reranker_model = Mock()
            reranking_service.model_loaded = True
        
        with patch.object(reranking_service, '_load_model', side_effect=mock_load_model):
            await reranking_service.initialize()
        
        assert reranking_service.model_loaded is True
        assert reranking_service.reranker_model is not None
        assert reranking_service.metrics.model_load_time > 0
    
    @pytest.mark.asyncio
    async def test_model_initialization_import_error(self, reranking_service):
        """测试模型初始化时导入错误"""
        with patch.object(reranking_service, '_load_model', side_effect=ImportError("No module named 'sentence_transformers'")):
            await reranking_service.initialize()
            
            assert reranking_service.model_loaded is False
            assert reranking_service.reranker_model is None
    
    @pytest.mark.asyncio
    async def test_model_initialization_general_error(self, reranking_service):
        """测试模型初始化时一般错误"""
        with patch.object(reranking_service, '_load_model', side_effect=Exception("Model loading failed")):
            await reranking_service.initialize()
            
            assert reranking_service.model_loaded is False
            assert reranking_service.reranker_model is None
    
    @pytest.mark.asyncio
    async def test_rerank_results_disabled(self, reranking_service, sample_results):
        """测试重排序功能禁用时的行为"""
        config = RetrievalConfig(enable_rerank=False)
        
        results = await reranking_service.rerank_results("测试查询", sample_results, config)
        
        assert results == sample_results
        assert reranking_service.metrics.total_requests == 0
    
    @pytest.mark.asyncio
    async def test_rerank_results_model_not_loaded(self, reranking_service, sample_results):
        """测试模型未加载时的行为"""
        config = RetrievalConfig(enable_rerank=True)
        reranking_service.model_loaded = False
        
        results = await reranking_service.rerank_results("测试查询", sample_results, config)
        
        assert results == sample_results
        assert reranking_service.metrics.total_requests == 0
    
    @pytest.mark.asyncio
    async def test_rerank_results_empty_results(self, reranking_service):
        """测试空结果的处理"""
        config = RetrievalConfig(enable_rerank=True)
        reranking_service.model_loaded = True
        
        results = await reranking_service.rerank_results("测试查询", [], config)
        
        assert results == []
        assert reranking_service.metrics.total_requests == 0
    
    @pytest.mark.asyncio
    async def test_rerank_results_success(self, reranking_service, sample_results):
        """测试重排序成功"""
        config = RetrievalConfig(enable_rerank=True)
        reranking_service.model_loaded = True
        
        # 模拟重排序分数（反转原始顺序）
        mock_scores = [0.1, 0.3, 0.5, 0.7, 0.9]
        
        with patch.object(reranking_service, '_perform_reranking', return_value=sample_results) as mock_rerank:
            # 创建重排序后的结果
            reranked_results = []
            for i, (result, score) in enumerate(zip(sample_results, mock_scores)):
                new_result = SearchResult(
                    chunk_id=result.chunk_id,
                    document_id=result.document_id,
                    content=result.content,
                    similarity_score=score,
                    metadata={
                        **result.metadata,
                        'original_score': result.similarity_score,
                        'rerank_score': score,
                        'rerank_rank': i + 1
                    }
                )
                reranked_results.append(new_result)
            
            # 按分数排序
            reranked_results.sort(key=lambda x: x.similarity_score, reverse=True)
            mock_rerank.return_value = reranked_results
            
            results = await reranking_service.rerank_results("测试查询", sample_results, config)
            
            assert len(results) == len(sample_results)
            assert results[0].similarity_score == 0.9  # 最高分
            assert results[-1].similarity_score == 0.1  # 最低分
            assert reranking_service.metrics.total_requests == 1
            assert reranking_service.metrics.successful_requests == 1
    
    @pytest.mark.asyncio
    async def test_rerank_results_failure(self, reranking_service, sample_results):
        """测试重排序失败时的降级"""
        config = RetrievalConfig(enable_rerank=True)
        reranking_service.model_loaded = True
        
        with patch.object(reranking_service, '_perform_reranking', side_effect=Exception("Reranking failed")):
            results = await reranking_service.rerank_results("测试查询", sample_results, config)
            
            # 应该返回原始结果
            assert results == sample_results
            assert reranking_service.metrics.total_requests == 1
            assert reranking_service.metrics.failed_requests == 1
    
    @pytest.mark.asyncio
    async def test_perform_reranking(self, reranking_service, sample_results):
        """测试重排序计算"""
        # 设置模拟模型
        mock_model = Mock()
        mock_scores = [0.2, 0.8, 0.6, 0.4, 0.9]
        
        reranking_service.reranker_model = mock_model
        reranking_service.model_loaded = True
        
        with patch.object(reranking_service, '_compute_rerank_scores', return_value=mock_scores):
            results = await reranking_service._perform_reranking("测试查询", sample_results)
            
            assert len(results) == len(sample_results)
            
            # 验证结果按分数排序
            assert results[0].similarity_score == 0.9  # 最高分
            assert results[1].similarity_score == 0.8
            assert results[-1].similarity_score == 0.2  # 最低分
            
            # 验证元数据
            for i, result in enumerate(results):
                assert 'original_score' in result.metadata
                assert 'rerank_score' in result.metadata
                assert 'rerank_rank' in result.metadata
                assert 'final_rank' in result.metadata
                assert result.metadata['final_rank'] == i + 1
    
    @pytest.mark.asyncio
    async def test_perform_reranking_timeout(self, reranking_service, sample_results):
        """测试重排序计算超时"""
        reranking_service.model_loaded = True
        reranking_service.timeout = 0.1  # 很短的超时时间
        
        def slow_compute(*args):
            import time
            time.sleep(0.2)  # 超过超时时间
            return [0.5] * len(sample_results)
        
        with patch.object(reranking_service, '_compute_rerank_scores', side_effect=slow_compute):
            with pytest.raises(Exception, match="重排序计算超时"):
                await reranking_service._perform_reranking("测试查询", sample_results)
    
    def test_compute_rerank_scores_single_batch(self, reranking_service):
        """测试单批次重排序分数计算"""
        mock_model = Mock()
        mock_scores = [0.1, 0.3, 0.5]
        mock_model.predict.return_value = mock_scores
        
        reranking_service.reranker_model = mock_model
        reranking_service.batch_size = 10
        
        pairs = [("query", "doc1"), ("query", "doc2"), ("query", "doc3")]
        scores = reranking_service._compute_rerank_scores(pairs)
        
        assert scores == mock_scores
        mock_model.predict.assert_called_once_with(pairs)
    
    def test_compute_rerank_scores_multiple_batches(self, reranking_service):
        """测试多批次重排序分数计算"""
        mock_model = Mock()
        batch1_scores = [0.1, 0.3]
        batch2_scores = [0.5, 0.7]
        mock_model.predict.side_effect = [batch1_scores, batch2_scores]
        
        reranking_service.reranker_model = mock_model
        reranking_service.batch_size = 2
        
        pairs = [("query", "doc1"), ("query", "doc2"), ("query", "doc3"), ("query", "doc4")]
        scores = reranking_service._compute_rerank_scores(pairs)
        
        assert scores == batch1_scores + batch2_scores
        assert mock_model.predict.call_count == 2
    
    @pytest.mark.asyncio
    async def test_rerank_with_limit(self, reranking_service, sample_results):
        """测试限制重排序"""
        config = RetrievalConfig(enable_rerank=True)
        reranking_service.model_loaded = True
        
        # 创建更多结果用于测试
        import uuid
        extended_results = sample_results + [
            SearchResult(
                chunk_id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content=f"额外文档{i}",
                similarity_score=0.3 - i * 0.1,
                metadata={"source": f"extra{i}.txt"}
            ) for i in range(3)
        ]
        
        with patch.object(reranking_service, 'rerank_results', return_value=sample_results[:3]) as mock_rerank:
            results = await reranking_service.rerank_with_limit(
                "测试查询", extended_results, config, rerank_top_k=3
            )
            
            # 验证只对前3个结果重排序
            mock_rerank.assert_called_once()
            assert len(results) == len(extended_results)
    
    def test_get_metrics(self, reranking_service):
        """测试获取性能指标"""
        # 更新一些指标
        reranking_service.metrics.update_request(0.5, success=True)
        reranking_service.metrics.update_request(1.0, success=False)
        reranking_service.metrics.model_load_time = 2.5
        
        metrics = reranking_service.get_metrics()
        
        assert metrics['model_loaded'] is False
        assert metrics['model_name'] == 'test-model'
        assert metrics['total_requests'] == 2
        assert metrics['successful_requests'] == 1
        assert metrics['failed_requests'] == 1
        assert metrics['success_rate'] == 0.5
        assert metrics['failure_rate'] == 0.5
        assert metrics['model_load_time'] == 2.5
        assert 'config' in metrics
    
    def test_reset_metrics(self, reranking_service):
        """测试重置指标"""
        # 先更新一些指标
        reranking_service.metrics.update_request(0.5, success=True)
        
        # 重置指标
        reranking_service.reset_metrics()
        
        assert reranking_service.metrics.total_requests == 0
        assert reranking_service.metrics.successful_requests == 0
        assert reranking_service.metrics.failed_requests == 0
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, reranking_service):
        """测试健康检查 - 健康状态"""
        reranking_service.model_loaded = True
        reranking_service.metrics.update_request(0.5, success=True)
        
        health = await reranking_service.health_check()
        
        assert health['status'] == 'healthy'
        assert health['model_loaded'] is True
        assert health['model_name'] == 'test-model'
        assert 'last_check' in health
        assert 'metrics' in health
    
    @pytest.mark.asyncio
    async def test_health_check_unhealthy_with_recovery(self, reranking_service):
        """测试健康检查 - 不健康状态并尝试恢复"""
        reranking_service.model_loaded = False
        
        async def mock_initialize():
            reranking_service.model_loaded = True  # 模拟恢复成功
        
        with patch.object(reranking_service, 'initialize', side_effect=mock_initialize) as mock_init:
            health = await reranking_service.health_check()
            
            assert health['status'] == 'healthy'
            assert health['recovery_attempted'] is True
            mock_init.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_recovery_failed(self, reranking_service):
        """测试健康检查 - 恢复失败"""
        reranking_service.model_loaded = False
        
        with patch.object(reranking_service, 'initialize', side_effect=Exception("Recovery failed")):
            health = await reranking_service.health_check()
            
            assert health['status'] == 'unhealthy'
            assert 'recovery_error' in health
    
    @pytest.mark.asyncio
    async def test_preload_model_success(self, reranking_service):
        """测试模型预加载成功"""
        reranking_service.model_loaded = False  # 初始状态为未加载
        
        async def mock_initialize():
            reranking_service.model_loaded = True
        
        with patch.object(reranking_service, 'initialize', side_effect=mock_initialize) as mock_init:
            result = await reranking_service.preload_model()
            
            assert result is True
            mock_init.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_preload_model_already_loaded(self, reranking_service):
        """测试模型已加载时的预加载"""
        reranking_service.model_loaded = True
        
        with patch.object(reranking_service, 'initialize') as mock_init:
            result = await reranking_service.preload_model()
            
            assert result is True
            mock_init.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_preload_model_failure(self, reranking_service):
        """测试模型预加载失败"""
        with patch.object(reranking_service, 'initialize', side_effect=Exception("Preload failed")):
            result = await reranking_service.preload_model()
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_close_service(self, reranking_service):
        """测试关闭服务"""
        # 设置模拟模型
        mock_model = Mock()
        mock_model.close = Mock()
        reranking_service.reranker_model = mock_model
        reranking_service.model_loaded = True
        
        await reranking_service.close()
        
        assert reranking_service.reranker_model is None
        assert reranking_service.model_loaded is False
        mock_model.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_service_no_close_method(self, reranking_service):
        """测试关闭服务 - 模型没有close方法"""
        mock_model = Mock()
        del mock_model.close  # 删除close方法
        reranking_service.reranker_model = mock_model
        reranking_service.model_loaded = True
        
        await reranking_service.close()
        
        assert reranking_service.reranker_model is None
        assert reranking_service.model_loaded is False


class TestRerankingServiceManager:
    """重排序服务管理器测试"""
    
    @pytest.fixture
    def manager_config(self):
        """管理器配置fixture"""
        return {
            'default_service': 'primary',
            'services': {
                'primary': {
                    'model_name': 'primary-model',
                    'batch_size': 32
                },
                'secondary': {
                    'model_name': 'secondary-model',
                    'batch_size': 16
                }
            }
        }
    
    @pytest.fixture
    def service_manager(self, manager_config):
        """服务管理器fixture"""
        return RerankingServiceManager(manager_config)
    
    @pytest.mark.asyncio
    async def test_manager_initialization(self, service_manager):
        """测试管理器初始化"""
        with patch('rag_system.services.reranking_service.RerankingService') as mock_service_class:
            mock_service1 = AsyncMock()
            mock_service2 = AsyncMock()
            mock_service_class.side_effect = [mock_service1, mock_service2]
            
            await service_manager.initialize()
            
            assert len(service_manager.services) == 2
            assert 'primary' in service_manager.services
            assert 'secondary' in service_manager.services
            
            # 验证服务初始化被调用
            mock_service1.initialize.assert_called_once()
            mock_service2.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_manager_initialization_with_failure(self, service_manager):
        """测试管理器初始化时部分服务失败"""
        with patch('rag_system.services.reranking_service.RerankingService') as mock_service_class:
            mock_service1 = AsyncMock()
            mock_service2 = AsyncMock()
            mock_service2.initialize.side_effect = Exception("Service 2 failed")
            mock_service_class.side_effect = [mock_service1, mock_service2]
            
            await service_manager.initialize()
            
            # 只有成功的服务被添加
            assert len(service_manager.services) == 1
            assert 'primary' in service_manager.services
            assert 'secondary' not in service_manager.services
    
    def test_get_service_default(self, service_manager):
        """测试获取默认服务"""
        mock_service = Mock()
        service_manager.services['primary'] = mock_service
        
        service = service_manager.get_service()
        
        assert service == mock_service
    
    def test_get_service_by_name(self, service_manager):
        """测试按名称获取服务"""
        mock_service = Mock()
        service_manager.services['secondary'] = mock_service
        
        service = service_manager.get_service('secondary')
        
        assert service == mock_service
    
    def test_get_service_not_found(self, service_manager):
        """测试获取不存在的服务"""
        service = service_manager.get_service('nonexistent')
        
        assert service is None
    
    @pytest.mark.asyncio
    async def test_rerank_with_service(self, service_manager):
        """测试使用指定服务重排序"""
        mock_service = AsyncMock()
        mock_results = [Mock()]
        mock_service.rerank_results.return_value = mock_results
        service_manager.services['primary'] = mock_service
        
        config = RetrievalConfig(enable_rerank=True)
        results = await service_manager.rerank_with_service(
            "测试查询", [], config, 'primary'
        )
        
        assert results == mock_results
        mock_service.rerank_results.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_rerank_with_nonexistent_service(self, service_manager):
        """测试使用不存在的服务重排序"""
        original_results = [Mock()]
        config = RetrievalConfig(enable_rerank=True)
        
        results = await service_manager.rerank_with_service(
            "测试查询", original_results, config, 'nonexistent'
        )
        
        assert results == original_results
    
    def test_get_all_metrics(self, service_manager):
        """测试获取所有服务指标"""
        mock_service1 = Mock()
        mock_service2 = Mock()
        mock_metrics1 = {'requests': 10}
        mock_metrics2 = {'requests': 5}
        mock_service1.get_metrics.return_value = mock_metrics1
        mock_service2.get_metrics.return_value = mock_metrics2
        
        service_manager.services['primary'] = mock_service1
        service_manager.services['secondary'] = mock_service2
        
        all_metrics = service_manager.get_all_metrics()
        
        assert all_metrics['primary'] == mock_metrics1
        assert all_metrics['secondary'] == mock_metrics2
    
    @pytest.mark.asyncio
    async def test_health_check_all(self, service_manager):
        """测试所有服务健康检查"""
        mock_service1 = AsyncMock()
        mock_service2 = AsyncMock()
        mock_health1 = {'status': 'healthy'}
        mock_health2 = {'status': 'unhealthy'}
        mock_service1.health_check.return_value = mock_health1
        mock_service2.health_check.return_value = mock_health2
        
        service_manager.services['primary'] = mock_service1
        service_manager.services['secondary'] = mock_service2
        
        health_status = await service_manager.health_check_all()
        
        assert health_status['primary'] == mock_health1
        assert health_status['secondary'] == mock_health2
    
    @pytest.mark.asyncio
    async def test_health_check_all_with_error(self, service_manager):
        """测试健康检查时发生错误"""
        mock_service = AsyncMock()
        mock_service.health_check.side_effect = Exception("Health check failed")
        service_manager.services['primary'] = mock_service
        
        health_status = await service_manager.health_check_all()
        
        assert health_status['primary']['status'] == 'error'
        assert 'error' in health_status['primary']
    
    @pytest.mark.asyncio
    async def test_close_all(self, service_manager):
        """测试关闭所有服务"""
        mock_service1 = AsyncMock()
        mock_service2 = AsyncMock()
        service_manager.services['primary'] = mock_service1
        service_manager.services['secondary'] = mock_service2
        
        await service_manager.close_all()
        
        mock_service1.close.assert_called_once()
        mock_service2.close.assert_called_once()
        assert len(service_manager.services) == 0


class TestRerankingDecorator:
    """重排序装饰器测试"""
    
    @pytest.mark.asyncio
    async def test_rerank_decorator_enabled(self):
        """测试重排序装饰器启用时"""
        mock_service = AsyncMock()
        original_results = [Mock()]
        reranked_results = [Mock()]
        mock_service.rerank_results.return_value = reranked_results
        
        @rerank_results(mock_service)
        async def mock_search(self, query, config, **kwargs):
            return original_results
        
        config = RetrievalConfig(enable_rerank=True)
        results = await mock_search(None, "测试查询", config)
        
        assert results == reranked_results
        mock_service.rerank_results.assert_called_once_with("测试查询", original_results, config)
    
    @pytest.mark.asyncio
    async def test_rerank_decorator_disabled(self):
        """测试重排序装饰器禁用时"""
        mock_service = AsyncMock()
        original_results = [Mock()]
        
        @rerank_results(mock_service)
        async def mock_search(self, query, config, **kwargs):
            return original_results
        
        config = RetrievalConfig(enable_rerank=False)
        results = await mock_search(None, "测试查询", config)
        
        assert results == original_results
        mock_service.rerank_results.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__])