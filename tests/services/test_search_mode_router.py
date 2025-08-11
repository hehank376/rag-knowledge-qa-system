"""
搜索模式路由器测试
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from rag_system.services.search_mode_router import SearchModeRouter
from rag_system.models.config import RetrievalConfig
from rag_system.models.vector import SearchResult
from rag_system.utils.exceptions import ProcessingError


class TestSearchModeRouter:
    """搜索模式路由器测试类"""
    
    @pytest.fixture
    def mock_retrieval_service(self):
        """模拟检索服务"""
        service = Mock()
        service.search_similar_documents = AsyncMock()
        service.search_by_keywords = AsyncMock()
        service.hybrid_search = AsyncMock()
        return service
    
    @pytest.fixture
    def router(self, mock_retrieval_service):
        """创建搜索模式路由器实例"""
        return SearchModeRouter(mock_retrieval_service)
    
    @pytest.fixture
    def sample_config(self):
        """示例配置"""
        return RetrievalConfig(
            top_k=5,
            similarity_threshold=0.7,
            search_mode='semantic'
        )
    
    @pytest.fixture
    def sample_results(self):
        """示例搜索结果"""
        import uuid
        return [
            SearchResult(
                chunk_id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content="测试内容1",
                similarity_score=0.9,
                metadata={}
            ),
            SearchResult(
                chunk_id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content="测试内容2",
                similarity_score=0.8,
                metadata={}
            )
        ]
    
    @pytest.mark.asyncio
    async def test_semantic_search_mode(self, router, mock_retrieval_service, sample_config, sample_results):
        """测试语义搜索模式"""
        # 设置模拟返回值
        mock_retrieval_service.search_similar_documents.return_value = sample_results
        
        # 执行搜索
        config = sample_config
        config.search_mode = 'semantic'
        results = await router.search_with_mode("测试查询", config)
        
        # 验证结果
        assert len(results) == 2
        assert results == sample_results
        
        # 验证调用
        mock_retrieval_service.search_similar_documents.assert_called_once_with(
            query="测试查询",
            top_k=5,
            similarity_threshold=0.7
        )
        
        # 验证统计
        stats = router.get_usage_statistics()
        assert stats['mode_usage']['semantic'] == 1
        assert stats['total_requests'] == 1
    
    @pytest.mark.asyncio
    async def test_keyword_search_mode(self, router, mock_retrieval_service, sample_config, sample_results):
        """测试关键词搜索模式"""
        # 设置模拟返回值
        mock_retrieval_service.search_by_keywords.return_value = sample_results
        
        # 执行搜索
        config = sample_config
        config.search_mode = 'keyword'
        results = await router.search_with_mode("测试查询关键词", config)
        
        # 验证结果
        assert len(results) == 2
        assert results == sample_results
        
        # 验证调用（关键词应该被提取）
        mock_retrieval_service.search_by_keywords.assert_called_once()
        call_args = mock_retrieval_service.search_by_keywords.call_args
        assert 'keywords' in call_args.kwargs
        assert 'top_k' in call_args.kwargs
        assert call_args.kwargs['top_k'] == 5
        
        # 验证统计
        stats = router.get_usage_statistics()
        assert stats['mode_usage']['keyword'] == 1
    
    @pytest.mark.asyncio
    async def test_hybrid_search_mode(self, router, mock_retrieval_service, sample_config, sample_results):
        """测试混合搜索模式"""
        # 设置模拟返回值
        mock_retrieval_service.hybrid_search.return_value = sample_results
        
        # 执行搜索
        config = sample_config
        config.search_mode = 'hybrid'
        results = await router.search_with_mode("测试查询", config)
        
        # 验证结果
        assert len(results) == 2
        assert results == sample_results
        
        # 验证调用
        mock_retrieval_service.hybrid_search.assert_called_once_with(
            query="测试查询",
            top_k=5,
            semantic_weight=0.7,
            keyword_weight=0.3
        )
        
        # 验证统计
        stats = router.get_usage_statistics()
        assert stats['mode_usage']['hybrid'] == 1
    
    @pytest.mark.asyncio
    async def test_unsupported_mode_fallback(self, router, mock_retrieval_service, sample_config, sample_results):
        """测试不支持的搜索模式降级"""
        # 设置模拟返回值
        mock_retrieval_service.search_similar_documents.return_value = sample_results
        
        # 执行搜索（使用不支持的模式）
        config = sample_config
        config.search_mode = 'unsupported_mode'
        results = await router.search_with_mode("测试查询", config)
        
        # 验证结果（应该降级到语义搜索）
        assert len(results) == 2
        assert results == sample_results
        
        # 验证调用了语义搜索
        mock_retrieval_service.search_similar_documents.assert_called_once()
        
        # 验证统计（应该记录语义搜索和错误）
        stats = router.get_usage_statistics()
        assert stats['mode_usage']['semantic'] == 1
        assert 'unsupported_mode:unsupported_mode' in stats['error_stats']
    
    @pytest.mark.asyncio
    async def test_search_failure_fallback(self, router, mock_retrieval_service, sample_config, sample_results):
        """测试搜索失败时的降级机制"""
        # 设置关键词搜索失败，语义搜索成功
        mock_retrieval_service.search_by_keywords.side_effect = Exception("关键词搜索失败")
        mock_retrieval_service.search_similar_documents.return_value = sample_results
        
        # 执行搜索
        config = sample_config
        config.search_mode = 'keyword'
        results = await router.search_with_mode("测试查询", config)
        
        # 验证结果（应该降级到语义搜索）
        assert len(results) == 2
        assert results == sample_results
        
        # 验证调用了两个方法
        mock_retrieval_service.search_by_keywords.assert_called_once()
        mock_retrieval_service.search_similar_documents.assert_called_once()
        
        # 验证统计
        stats = router.get_usage_statistics()
        assert stats['mode_usage']['keyword'] == 1
        assert 'error:keyword' in stats['error_stats']
        assert 'semantic_fallback' in stats['performance_stats']
    
    @pytest.mark.asyncio
    async def test_complete_search_failure(self, router, mock_retrieval_service, sample_config):
        """测试完全搜索失败"""
        # 设置所有搜索方法都失败
        mock_retrieval_service.search_by_keywords.side_effect = Exception("关键词搜索失败")
        mock_retrieval_service.search_similar_documents.side_effect = Exception("语义搜索失败")
        
        # 执行搜索，应该抛出异常
        config = sample_config
        config.search_mode = 'keyword'
        
        with pytest.raises(ProcessingError) as exc_info:
            await router.search_with_mode("测试查询", config)
        
        assert "搜索失败" in str(exc_info.value)
        
        # 验证统计
        stats = router.get_usage_statistics()
        assert 'error:keyword' in stats['error_stats']
        assert 'fallback_failed' in stats['error_stats']
    
    @pytest.mark.asyncio
    async def test_semantic_search_direct_failure(self, router, mock_retrieval_service, sample_config):
        """测试语义搜索直接失败"""
        # 设置语义搜索失败
        mock_retrieval_service.search_similar_documents.side_effect = Exception("语义搜索失败")
        
        # 执行搜索，应该抛出异常
        config = sample_config
        config.search_mode = 'semantic'
        
        with pytest.raises(ProcessingError) as exc_info:
            await router.search_with_mode("测试查询", config)
        
        assert "搜索失败" in str(exc_info.value)
    
    def test_extract_keywords(self, router):
        """测试关键词提取"""
        # 测试中文文本（用空格分隔的）
        keywords = router._extract_keywords("测试 查询 关键词")
        assert len(keywords) > 0
        assert '测试' in keywords
        assert '查询' in keywords
        assert '关键词' in keywords
        
        # 测试英文文本
        keywords = router._extract_keywords("This is a test query with keywords")
        assert 'test' in keywords
        assert 'query' in keywords
        assert 'keywords' in keywords
        
        # 验证停用词被过滤
        assert 'this' not in keywords
        assert 'is' not in keywords
        assert 'a' not in keywords
        
        # 测试空文本
        keywords = router._extract_keywords("")
        assert len(keywords) == 0
        
        # 测试只有停用词的文本
        keywords = router._extract_keywords("的 了 在 是 我 有 和")
        assert len(keywords) == 0
        
        # 测试混合中英文
        keywords = router._extract_keywords("python 编程 test 代码")
        assert 'python' in keywords
        assert '编程' in keywords
        assert 'test' in keywords
        assert '代码' in keywords
    
    def test_performance_recording(self, router):
        """测试性能记录"""
        # 记录一些性能数据
        router._record_performance('semantic', 0.5, 10)
        router._record_performance('semantic', 0.3, 8)
        router._record_performance('keyword', 0.8, 5)
        
        # 验证统计数据
        stats = router.get_usage_statistics()
        
        semantic_stats = stats['performance_stats']['semantic']
        assert semantic_stats['total_requests'] == 2
        assert semantic_stats['avg_time'] == 0.4  # (0.5 + 0.3) / 2
        assert semantic_stats['avg_results'] == 9.0  # (10 + 8) / 2
        assert semantic_stats['min_time'] == 0.3
        assert semantic_stats['max_time'] == 0.5
        
        keyword_stats = stats['performance_stats']['keyword']
        assert keyword_stats['total_requests'] == 1
        assert keyword_stats['avg_time'] == 0.8
        assert keyword_stats['avg_results'] == 5.0
    
    def test_usage_statistics(self, router):
        """测试使用统计"""
        # 模拟一些使用数据
        router.mode_usage_stats['semantic'] = 10
        router.mode_usage_stats['keyword'] = 5
        router.mode_usage_stats['hybrid'] = 3
        router.mode_error_stats['error:keyword'] = 2
        
        stats = router.get_usage_statistics()
        
        assert stats['total_requests'] == 18
        assert stats['mode_usage']['semantic'] == 10
        assert stats['mode_usage']['keyword'] == 5
        assert stats['mode_usage']['hybrid'] == 3
        
        # 验证百分比计算
        assert abs(stats['mode_usage_percentage']['semantic'] - 55.56) < 0.01
        assert abs(stats['mode_usage_percentage']['keyword'] - 27.78) < 0.01
        assert abs(stats['mode_usage_percentage']['hybrid'] - 16.67) < 0.01
        
        assert stats['error_stats']['error:keyword'] == 2
        assert stats['supported_modes'] == ['semantic', 'keyword', 'hybrid']
    
    def test_reset_statistics(self, router):
        """测试统计重置"""
        # 添加一些统计数据
        router.mode_usage_stats['semantic'] = 5
        router.mode_error_stats['error:test'] = 1
        router._record_performance('semantic', 0.5, 10)
        
        # 重置统计
        router.reset_statistics()
        
        # 验证统计被清空
        stats = router.get_usage_statistics()
        assert stats['total_requests'] == 0
        assert len(stats['mode_usage']) == 0
        assert len(stats['error_stats']) == 0
        assert len(stats['performance_stats']) == 0
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, router, mock_retrieval_service):
        """测试健康检查 - 健康状态"""
        # 添加一些统计数据
        router.mode_usage_stats['semantic'] = 10
        router.mode_error_stats['error:test'] = 1
        
        health = await router.health_check()
        
        assert health['status'] == 'healthy'
        assert health['supported_modes'] == ['semantic', 'keyword', 'hybrid']
        assert health['total_requests'] == 10
        assert health['error_rate'] == 10.0  # 1/10 * 100
    
    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, router):
        """测试健康检查 - 不健康状态"""
        # 设置检索服务为None
        router.retrieval_service = None
        
        health = await router.health_check()
        
        assert health['status'] == 'unhealthy'
        assert '检索服务不可用' in health['error']
    
    @pytest.mark.asyncio
    async def test_similarity_threshold_filtering(self, router, mock_retrieval_service, sample_config):
        """测试相似度阈值过滤"""
        # 创建包含不同相似度分数的结果
        import uuid
        results_with_scores = [
            SearchResult(
                chunk_id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()), 
                content="高相似度内容",
                similarity_score=0.9,  # 高于阈值
                metadata={}
            ),
            SearchResult(
                chunk_id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content="低相似度内容", 
                similarity_score=0.5,  # 低于阈值
                metadata={}
            )
        ]
        
        mock_retrieval_service.search_by_keywords.return_value = results_with_scores
        mock_retrieval_service.hybrid_search.return_value = results_with_scores
        
        # 测试关键词搜索的过滤
        config = sample_config
        config.search_mode = 'keyword'
        config.similarity_threshold = 0.7
        
        results = await router.search_with_mode("测试查询", config)
        
        # 应该只返回高相似度的结果
        assert len(results) == 1
        assert results[0].similarity_score == 0.9
        
        # 测试混合搜索的过滤
        config.search_mode = 'hybrid'
        results = await router.search_with_mode("测试查询", config)
        
        # 应该只返回高相似度的结果
        assert len(results) == 1
        assert results[0].similarity_score == 0.9
    
    @pytest.mark.asyncio
    async def test_keyword_extraction_fallback(self, router, mock_retrieval_service, sample_config, sample_results):
        """测试关键词提取失败时的降级"""
        # 模拟关键词提取返回空列表
        with patch.object(router, '_extract_keywords', return_value=[]):
            mock_retrieval_service.search_similar_documents.return_value = sample_results
            
            config = sample_config
            config.search_mode = 'keyword'
            
            results = await router.search_with_mode("测试查询", config)
            
            # 应该降级到语义搜索
            assert len(results) == 2
            mock_retrieval_service.search_similar_documents.assert_called_once()
            mock_retrieval_service.search_by_keywords.assert_not_called()


if __name__ == '__main__':
    pytest.main([__file__])