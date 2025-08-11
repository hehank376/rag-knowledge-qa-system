"""
搜索模式集成测试 - 端到端功能验证
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import uuid

from rag_system.services.qa_service import QAService
from rag_system.services.enhanced_retrieval_service import EnhancedRetrievalService
from rag_system.services.search_mode_router import SearchModeRouter
from rag_system.models.config import RetrievalConfig
from rag_system.models.vector import SearchResult
from rag_system.models.qa import QAResponse
from rag_system.utils.exceptions import ProcessingError, QAError


class TestSearchModeIntegration:
    """搜索模式集成测试类"""
    
    @pytest.fixture
    def mock_base_retrieval_service(self):
        """模拟基础检索服务"""
        service = Mock()
        service.initialize = AsyncMock()
        service.cleanup = AsyncMock()
        service.search_similar_documents = AsyncMock()
        service.search_by_keywords = AsyncMock()
        service.hybrid_search = AsyncMock()
        service.get_service_stats = AsyncMock()
        return service
    
    @pytest.fixture
    def sample_search_results(self):
        """示例搜索结果"""
        return [
            SearchResult(
                chunk_id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content="这是语义搜索找到的相关内容，包含了用户查询的核心信息。",
                similarity_score=0.92,
                metadata={'document_name': 'semantic_doc.txt', 'chunk_index': 0}
            ),
            SearchResult(
                chunk_id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content="这是另一个相关的文档片段，提供了补充信息。",
                similarity_score=0.87,
                metadata={'document_name': 'semantic_doc2.txt', 'chunk_index': 1}
            )
        ]
    
    @pytest.fixture
    def keyword_search_results(self):
        """关键词搜索结果"""
        return [
            SearchResult(
                chunk_id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content="关键词搜索找到的匹配内容，包含了精确的关键词匹配。",
                similarity_score=0.85,
                metadata={'document_name': 'keyword_doc.txt', 'chunk_index': 0}
            ),
            SearchResult(
                chunk_id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content="另一个关键词匹配的文档内容。",
                similarity_score=0.78,
                metadata={'document_name': 'keyword_doc2.txt', 'chunk_index': 1}
            )
        ]
    
    @pytest.fixture
    def hybrid_search_results(self):
        """混合搜索结果"""
        return [
            SearchResult(
                chunk_id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content="混合搜索结合了语义和关键词的优势，找到了最相关的内容。",
                similarity_score=0.95,
                metadata={'document_name': 'hybrid_doc.txt', 'chunk_index': 0}
            ),
            SearchResult(
                chunk_id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content="混合搜索的另一个高质量结果。",
                similarity_score=0.89,
                metadata={'document_name': 'hybrid_doc2.txt', 'chunk_index': 1}
            )
        ]
    
    @pytest.mark.asyncio
    async def test_semantic_search_mode_end_to_end(self, mock_base_retrieval_service, sample_search_results):
        """测试语义搜索模式的端到端流程"""
        # 设置模拟返回值
        mock_base_retrieval_service.search_similar_documents.return_value = sample_search_results
        
        # 创建搜索路由器
        router = SearchModeRouter(mock_base_retrieval_service)
        await router.initialize()
        
        # 创建语义搜索配置
        config = RetrievalConfig(
            top_k=5,
            similarity_threshold=0.7,
            search_mode='semantic',
            enable_rerank=False,
            enable_cache=False
        )
        
        # 执行搜索
        results = await router.search_with_mode("测试查询", config)
        
        # 验证结果
        assert len(results) == 2
        assert results[0].similarity_score == 0.92
        assert "语义搜索" in results[0].content
        
        # 验证调用了正确的搜索方法
        mock_base_retrieval_service.search_similar_documents.assert_called_once()
        
        # 验证统计信息
        stats = router.get_usage_statistics()
        assert stats['mode_usage']['semantic'] == 1
        assert stats['total_requests'] == 1
        
        await router.cleanup()
    
    @pytest.mark.asyncio
    async def test_keyword_search_mode_end_to_end(self, mock_base_retrieval_service, keyword_search_results):
        """测试关键词搜索模式的端到端流程"""
        # 设置模拟返回值
        mock_base_retrieval_service.search_by_keywords.return_value = keyword_search_results
        
        # 创建搜索路由器
        router = SearchModeRouter(mock_base_retrieval_service)
        await router.initialize()
        
        # 创建关键词搜索配置
        config = RetrievalConfig(
            top_k=5,
            similarity_threshold=0.7,
            search_mode='keyword',
            enable_rerank=False,
            enable_cache=False
        )
        
        # 执行搜索
        results = await router.search_with_mode("测试 查询 关键词", config)
        
        # 验证结果
        assert len(results) == 2
        assert results[0].similarity_score == 0.85
        assert "关键词搜索" in results[0].content
        
        # 验证调用了正确的搜索方法
        mock_base_retrieval_service.search_by_keywords.assert_called_once()
        
        # 验证统计信息
        stats = router.get_usage_statistics()
        assert stats['mode_usage']['keyword'] == 1
        
        await router.cleanup()
    
    @pytest.mark.asyncio
    async def test_hybrid_search_mode_end_to_end(self, mock_base_retrieval_service, hybrid_search_results):
        """测试混合搜索模式的端到端流程"""
        # 设置模拟返回值
        mock_base_retrieval_service.hybrid_search.return_value = hybrid_search_results
        
        # 创建搜索路由器
        router = SearchModeRouter(mock_base_retrieval_service)
        await router.initialize()
        
        # 创建混合搜索配置
        config = RetrievalConfig(
            top_k=5,
            similarity_threshold=0.7,
            search_mode='hybrid',
            enable_rerank=False,
            enable_cache=False
        )
        
        # 执行搜索
        results = await router.search_with_mode("测试查询", config)
        
        # 验证结果
        assert len(results) == 2
        assert results[0].similarity_score == 0.95
        assert "混合搜索" in results[0].content
        
        # 验证调用了正确的搜索方法
        mock_base_retrieval_service.hybrid_search.assert_called_once()
        
        # 验证统计信息
        stats = router.get_usage_statistics()
        assert stats['mode_usage']['hybrid'] == 1
        
        await router.cleanup()
    
    @pytest.mark.asyncio
    async def test_search_mode_fallback_mechanism(self, mock_base_retrieval_service, sample_search_results):
        """测试搜索模式降级机制"""
        # 设置关键词搜索失败，语义搜索成功
        mock_base_retrieval_service.search_by_keywords.side_effect = Exception("关键词搜索服务不可用")
        mock_base_retrieval_service.search_similar_documents.return_value = sample_search_results
        
        # 创建搜索路由器
        router = SearchModeRouter(mock_base_retrieval_service)
        await router.initialize()
        
        # 创建关键词搜索配置
        config = RetrievalConfig(
            top_k=5,
            similarity_threshold=0.7,
            search_mode='keyword',
            enable_rerank=False,
            enable_cache=False
        )
        
        # 执行搜索（应该降级到语义搜索）
        results = await router.search_with_mode("测试查询", config)
        
        # 验证结果（应该是语义搜索的结果）
        assert len(results) == 2
        assert results[0].similarity_score == 0.92
        
        # 验证调用了两个方法（先关键词，后语义）
        mock_base_retrieval_service.search_by_keywords.assert_called_once()
        mock_base_retrieval_service.search_similar_documents.assert_called_once()
        
        # 验证统计信息记录了错误和降级
        stats = router.get_usage_statistics()
        assert stats['mode_usage']['keyword'] == 1
        assert 'error:keyword' in stats['error_stats']
        assert 'semantic_fallback' in stats['performance_stats']
        
        await router.cleanup()
    
    @pytest.mark.asyncio
    async def test_enhanced_retrieval_service_integration(self, mock_base_retrieval_service, sample_search_results):
        """测试增强检索服务的集成"""
        # 设置模拟返回值
        mock_base_retrieval_service.search_similar_documents.return_value = sample_search_results
        
        # 创建增强检索服务
        config = {
            'default_top_k': 5,
            'similarity_threshold': 0.7,
            'search_mode': 'semantic',
            'enable_rerank': False,
            'enable_cache': False
        }
        
        enhanced_service = EnhancedRetrievalService(config)
        
        # 模拟基础服务和搜索路由器
        mock_search_router = Mock()
        mock_search_router.initialize = AsyncMock()
        mock_search_router.cleanup = AsyncMock()
        mock_search_router.search_with_mode = AsyncMock(return_value=sample_search_results)
        mock_search_router.get_usage_statistics = Mock(return_value={'total_requests': 1})
        
        with patch.object(enhanced_service, 'base_retrieval_service', mock_base_retrieval_service), \
             patch.object(enhanced_service, 'search_router', mock_search_router):
            await enhanced_service.initialize()
            
            # 测试配置化搜索
            retrieval_config = RetrievalConfig(
                top_k=8,
                similarity_threshold=0.8,
                search_mode='semantic',
                enable_rerank=False,
                enable_cache=False
            )
            
            results = await enhanced_service.search_with_config("测试查询", retrieval_config)
            
            # 验证结果
            assert len(results) == 2
            assert results[0].similarity_score == 0.92
            
            # 验证统计信息
            stats = enhanced_service.get_search_statistics()
            assert stats['service_name'] == 'EnhancedRetrievalService'
            assert 'router_statistics' in stats
            
            await enhanced_service.cleanup()
    
    @pytest.mark.asyncio
    async def test_qa_service_search_mode_integration(self, mock_base_retrieval_service, sample_search_results):
        """测试QA服务的搜索模式集成"""
        # 设置模拟返回值
        mock_base_retrieval_service.search_similar_documents.return_value = sample_search_results
        
        # 创建QA服务配置
        qa_config = {
            'retrieval_top_k': 5,
            'similarity_threshold': 0.7,
            'search_mode': 'semantic',
            'enable_rerank': False,
            'enable_cache': False,
            'llm_provider': 'mock',
            'llm_model': 'mock-model'
        }
        
        qa_service = QAService(qa_config)
        
        # 模拟LLM
        mock_llm = Mock()
        mock_llm.generate_response = AsyncMock(return_value="基于检索内容生成的答案")
        mock_llm.health_check = Mock(return_value=True)
        
        # 模拟增强检索服务
        mock_enhanced_service = Mock()
        mock_enhanced_service.search_with_config = AsyncMock(return_value=sample_search_results)
        mock_enhanced_service.update_default_config = AsyncMock()
        mock_enhanced_service.get_search_statistics = Mock(return_value={'total_requests': 1})
        mock_enhanced_service.health_check = AsyncMock(return_value={'status': 'healthy'})
        
        # 模拟服务
        with patch.object(qa_service, 'retrieval_service', mock_enhanced_service), \
             patch.object(qa_service, 'llm', mock_llm):
            
            # 测试问答
            response = await qa_service.answer_question("测试问题")
            
            # 验证响应
            assert isinstance(response, QAResponse)
            assert response.question == "测试问题"
            assert len(response.sources) == 2
            assert response.confidence_score > 0
            
            # 验证使用了配置化检索
            mock_enhanced_service.search_with_config.assert_called_once()
            call_args = mock_enhanced_service.search_with_config.call_args
            assert call_args.kwargs['query'] == "测试问题"
            assert 'config' in call_args.kwargs
    
    @pytest.mark.asyncio
    async def test_search_mode_switching(self, mock_base_retrieval_service, sample_search_results, keyword_search_results, hybrid_search_results):
        """测试搜索模式切换"""
        # 设置不同模式的模拟返回值
        mock_base_retrieval_service.search_similar_documents.return_value = sample_search_results
        mock_base_retrieval_service.search_by_keywords.return_value = keyword_search_results
        mock_base_retrieval_service.hybrid_search.return_value = hybrid_search_results
        
        # 创建搜索路由器
        router = SearchModeRouter(mock_base_retrieval_service)
        await router.initialize()
        
        # 测试不同搜索模式
        test_modes = [
            ('semantic', sample_search_results, 0.92),
            ('keyword', keyword_search_results, 0.85),
            ('hybrid', hybrid_search_results, 0.95)
        ]
        
        for mode, expected_results, expected_score in test_modes:
            config = RetrievalConfig(
                top_k=5,
                similarity_threshold=0.7,
                search_mode=mode,
                enable_rerank=False,
                enable_cache=False
            )
            
            results = await router.search_with_mode(f"测试{mode}查询", config)
            
            # 验证结果
            assert len(results) == 2
            assert results[0].similarity_score == expected_score
            # 验证内容匹配（根据模拟数据调整断言）
            if mode == 'semantic':
                assert '语义搜索' in results[0].content
            elif mode == 'keyword':
                assert '关键词搜索' in results[0].content
            elif mode == 'hybrid':
                assert '混合搜索' in results[0].content
        
        # 验证统计信息
        stats = router.get_usage_statistics()
        assert stats['total_requests'] == 3
        assert stats['mode_usage']['semantic'] == 1
        assert stats['mode_usage']['keyword'] == 1
        assert stats['mode_usage']['hybrid'] == 1
        
        await router.cleanup()
    
    @pytest.mark.asyncio
    async def test_performance_metrics_collection(self, mock_base_retrieval_service, sample_search_results):
        """测试性能指标收集"""
        # 设置模拟返回值
        mock_base_retrieval_service.search_similar_documents.return_value = sample_search_results
        
        # 创建搜索路由器
        router = SearchModeRouter(mock_base_retrieval_service)
        await router.initialize()
        
        # 创建配置
        config = RetrievalConfig(
            top_k=5,
            similarity_threshold=0.7,
            search_mode='semantic',
            enable_rerank=False,
            enable_cache=False
        )
        
        # 执行多次搜索
        for i in range(3):
            await router.search_with_mode(f"测试查询{i}", config)
        
        # 验证性能统计
        stats = router.get_usage_statistics()
        
        # 验证基本统计
        assert stats['total_requests'] == 3
        assert stats['mode_usage']['semantic'] == 3
        
        # 验证性能指标
        semantic_perf = stats['performance_stats']['semantic']
        assert semantic_perf['total_requests'] == 3
        assert semantic_perf['avg_time'] >= 0  # 在模拟环境中可能为0
        assert semantic_perf['avg_results'] == 2.0  # 每次返回2个结果
        assert semantic_perf['min_time'] >= 0  # 在模拟环境中可能为0
        assert semantic_perf['max_time'] >= semantic_perf['min_time']
        
        await router.cleanup()
    
    @pytest.mark.asyncio
    async def test_configuration_parameter_passing(self, mock_base_retrieval_service, sample_search_results):
        """测试配置参数的正确传递"""
        # 设置模拟返回值
        mock_base_retrieval_service.search_similar_documents.return_value = sample_search_results
        
        # 创建搜索路由器
        router = SearchModeRouter(mock_base_retrieval_service)
        await router.initialize()
        
        # 测试不同的配置参数
        test_configs = [
            RetrievalConfig(top_k=3, similarity_threshold=0.8, search_mode='semantic'),
            RetrievalConfig(top_k=10, similarity_threshold=0.6, search_mode='semantic'),
            RetrievalConfig(top_k=7, similarity_threshold=0.75, search_mode='semantic')
        ]
        
        for config in test_configs:
            await router.search_with_mode("测试查询", config)
            
            # 验证参数传递
            call_args = mock_base_retrieval_service.search_similar_documents.call_args
            assert call_args.kwargs['top_k'] == config.top_k
            assert call_args.kwargs['similarity_threshold'] == config.similarity_threshold
        
        await router.cleanup()
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, mock_base_retrieval_service):
        """测试错误处理和恢复机制"""
        # 创建搜索路由器
        router = SearchModeRouter(mock_base_retrieval_service)
        await router.initialize()
        
        # 测试完全失败的情况
        mock_base_retrieval_service.search_similar_documents.side_effect = Exception("所有搜索方法都失败")
        mock_base_retrieval_service.search_by_keywords.side_effect = Exception("关键词搜索失败")
        mock_base_retrieval_service.hybrid_search.side_effect = Exception("混合搜索失败")
        
        config = RetrievalConfig(
            top_k=5,
            similarity_threshold=0.7,
            search_mode='keyword',
            enable_rerank=False,
            enable_cache=False
        )
        
        # 执行搜索，应该抛出异常
        with pytest.raises(ProcessingError) as exc_info:
            await router.search_with_mode("测试查询", config)
        
        assert "搜索失败" in str(exc_info.value)
        
        # 验证错误统计
        stats = router.get_usage_statistics()
        assert 'error:keyword' in stats['error_stats']
        assert 'fallback_failed' in stats['error_stats']
        
        await router.cleanup()
    
    @pytest.mark.asyncio
    async def test_health_check_integration(self, mock_base_retrieval_service):
        """测试健康检查集成"""
        # 创建搜索路由器
        router = SearchModeRouter(mock_base_retrieval_service)
        await router.initialize()
        
        # 测试健康状态
        health = await router.health_check()
        
        assert health['status'] == 'healthy'
        assert health['supported_modes'] == ['semantic', 'keyword', 'hybrid']
        assert 'total_requests' in health
        assert 'error_rate' in health
        
        # 测试不健康状态
        router.retrieval_service = None
        health = await router.health_check()
        
        assert health['status'] == 'unhealthy'
        assert '检索服务不可用' in health['error']
        
        await router.cleanup()


if __name__ == '__main__':
    pytest.main([__file__])