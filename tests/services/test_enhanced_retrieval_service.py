"""
增强检索服务测试
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from rag_system.services.enhanced_retrieval_service import EnhancedRetrievalService
from rag_system.models.config import RetrievalConfig
from rag_system.models.vector import SearchResult
from rag_system.utils.exceptions import ProcessingError


class TestEnhancedRetrievalService:
    """增强检索服务测试类"""
    
    @pytest.fixture
    def mock_base_service(self):
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
    def mock_search_router(self):
        """模拟搜索路由器"""
        router = Mock()
        router.initialize = AsyncMock()
        router.cleanup = AsyncMock()
        router.search_with_mode = AsyncMock()
        router.get_usage_statistics = Mock()
        router.reset_statistics = Mock()
        router.health_check = AsyncMock()
        return router
    
    @pytest.fixture
    def enhanced_service(self):
        """创建增强检索服务实例"""
        config = {
            'default_top_k': 5,
            'similarity_threshold': 0.7,
            'search_mode': 'semantic',
            'enable_rerank': False,
            'enable_cache': False
        }
        return EnhancedRetrievalService(config)
    
    @pytest.fixture
    def sample_config(self):
        """示例配置"""
        return RetrievalConfig(
            top_k=10,
            similarity_threshold=0.8,
            search_mode='hybrid',
            enable_rerank=True,
            enable_cache=True
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
    async def test_initialization(self, enhanced_service, mock_base_service, mock_search_router):
        """测试服务初始化"""
        # 模拟依赖服务
        with patch.object(enhanced_service, 'base_retrieval_service', mock_base_service), \
             patch.object(enhanced_service, 'search_router', mock_search_router):
            
            await enhanced_service.initialize()
            
            # 验证初始化调用
            mock_base_service.initialize.assert_called_once()
            mock_search_router.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup(self, enhanced_service, mock_base_service, mock_search_router):
        """测试资源清理"""
        # 模拟依赖服务
        with patch.object(enhanced_service, 'base_retrieval_service', mock_base_service), \
             patch.object(enhanced_service, 'search_router', mock_search_router):
            
            await enhanced_service.cleanup()
            
            # 验证清理调用
            mock_search_router.cleanup.assert_called_once()
            mock_base_service.cleanup.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_with_config(self, enhanced_service, mock_search_router, sample_config, sample_results):
        """测试配置化搜索"""
        # 设置模拟返回值
        mock_search_router.search_with_mode.return_value = sample_results
        
        # 模拟搜索路由器
        with patch.object(enhanced_service, 'search_router', mock_search_router):
            results = await enhanced_service.search_with_config("测试查询", sample_config)
            
            # 验证结果
            assert len(results) == 2
            assert results == sample_results
            
            # 验证调用
            mock_search_router.search_with_mode.assert_called_once_with(
                query="测试查询",
                config=sample_config
            )
    
    @pytest.mark.asyncio
    async def test_search_with_default_config(self, enhanced_service, mock_search_router, sample_results):
        """测试使用默认配置搜索"""
        # 设置模拟返回值
        mock_search_router.search_with_mode.return_value = sample_results
        
        # 模拟搜索路由器
        with patch.object(enhanced_service, 'search_router', mock_search_router):
            results = await enhanced_service.search_with_config("测试查询")
            
            # 验证结果
            assert len(results) == 2
            assert results == sample_results
            
            # 验证使用了默认配置
            call_args = mock_search_router.search_with_mode.call_args
            assert call_args.kwargs['query'] == "测试查询"
            assert call_args.kwargs['config'] == enhanced_service.default_config
    
    @pytest.mark.asyncio
    async def test_search_with_empty_query(self, enhanced_service):
        """测试空查询处理"""
        with pytest.raises(ProcessingError) as exc_info:
            await enhanced_service.search_with_config("")
        
        assert "查询内容不能为空" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_search_similar_documents_compatibility(self, enhanced_service, mock_search_router, sample_results):
        """测试兼容性方法"""
        # 设置模拟返回值
        mock_search_router.search_with_mode.return_value = sample_results
        
        # 模拟搜索路由器
        with patch.object(enhanced_service, 'search_router', mock_search_router):
            results = await enhanced_service.search_similar_documents(
                query="测试查询",
                top_k=8,
                similarity_threshold=0.75
            )
            
            # 验证结果
            assert len(results) == 2
            assert results == sample_results
            
            # 验证配置参数被正确传递
            call_args = mock_search_router.search_with_mode.call_args
            config = call_args.kwargs['config']
            assert config.top_k == 8
            assert config.similarity_threshold == 0.75
    
    @pytest.mark.asyncio
    async def test_update_default_config(self, enhanced_service, sample_config):
        """测试更新默认配置"""
        # 更新默认配置
        await enhanced_service.update_default_config(sample_config)
        
        # 验证配置已更新
        assert enhanced_service.default_config == sample_config
        assert enhanced_service.default_config.top_k == 10
        assert enhanced_service.default_config.search_mode == 'hybrid'
    
    @pytest.mark.asyncio
    async def test_update_invalid_config(self, enhanced_service):
        """测试更新无效配置"""
        # 创建无效配置
        invalid_config = RetrievalConfig(
            top_k=-1,  # 无效值
            similarity_threshold=1.5,  # 无效值
            search_mode='invalid'  # 无效值
        )
        
        with pytest.raises(ProcessingError) as exc_info:
            await enhanced_service.update_default_config(invalid_config)
        
        assert "配置验证失败" in str(exc_info.value)
    
    def test_get_default_config(self, enhanced_service):
        """测试获取默认配置"""
        config = enhanced_service.get_default_config()
        
        assert isinstance(config, RetrievalConfig)
        assert config.top_k == 5
        assert config.similarity_threshold == 0.7
        assert config.search_mode == 'semantic'
    
    def test_get_search_statistics(self, enhanced_service, mock_search_router):
        """测试获取搜索统计"""
        # 设置模拟统计数据
        mock_stats = {
            'total_requests': 100,
            'mode_usage': {'semantic': 60, 'keyword': 30, 'hybrid': 10}
        }
        mock_search_router.get_usage_statistics.return_value = mock_stats
        
        # 模拟搜索路由器
        with patch.object(enhanced_service, 'search_router', mock_search_router):
            stats = enhanced_service.get_search_statistics()
            
            # 验证统计信息
            assert stats['service_name'] == 'EnhancedRetrievalService'
            assert 'default_config' in stats
            assert stats['router_statistics'] == mock_stats
    
    def test_reset_statistics(self, enhanced_service, mock_search_router):
        """测试重置统计"""
        # 模拟搜索路由器
        with patch.object(enhanced_service, 'search_router', mock_search_router):
            enhanced_service.reset_statistics()
            
            # 验证重置调用
            mock_search_router.reset_statistics.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, enhanced_service, mock_search_router):
        """测试健康检查 - 健康状态"""
        # 设置健康的路由器
        mock_search_router.health_check.return_value = {'status': 'healthy'}
        
        # 模拟依赖服务
        with patch.object(enhanced_service, 'base_retrieval_service', Mock()), \
             patch.object(enhanced_service, 'search_router', mock_search_router):
            
            health = await enhanced_service.health_check()
            
            assert health['status'] == 'healthy'
            assert health['components']['base_retrieval_service'] == 'healthy'
            assert health['components']['search_router']['status'] == 'healthy'
    
    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, enhanced_service, mock_search_router):
        """测试健康检查 - 不健康状态"""
        # 设置不健康的路由器
        mock_search_router.health_check.return_value = {'status': 'unhealthy'}
        
        # 模拟依赖服务
        with patch.object(enhanced_service, 'base_retrieval_service', None), \
             patch.object(enhanced_service, 'search_router', mock_search_router):
            
            health = await enhanced_service.health_check()
            
            assert health['status'] == 'unhealthy'
            assert health['components']['base_retrieval_service'] == 'unhealthy'
            assert health['components']['search_router']['status'] == 'unhealthy'
    
    @pytest.mark.asyncio
    async def test_proxy_methods(self, enhanced_service, mock_base_service, sample_results):
        """测试代理方法"""
        # 设置模拟返回值
        mock_base_service.search_by_keywords = AsyncMock(return_value=sample_results)
        mock_base_service.hybrid_search = AsyncMock(return_value=sample_results)
        mock_base_service.get_document_statistics = AsyncMock(return_value={'doc_count': 10})
        
        # 模拟基础服务
        with patch.object(enhanced_service, 'base_retrieval_service', mock_base_service):
            # 测试关键词搜索代理
            results = await enhanced_service.search_by_keywords(['测试', '关键词'])
            assert results == sample_results
            mock_base_service.search_by_keywords.assert_called_once_with(['测试', '关键词'], None)
            
            # 测试混合搜索代理
            results = await enhanced_service.hybrid_search('测试查询', top_k=5)
            assert results == sample_results
            mock_base_service.hybrid_search.assert_called_once_with('测试查询', 5)
            
            # 测试文档统计代理
            stats = await enhanced_service.get_document_statistics('doc123')
            assert stats == {'doc_count': 10}
            mock_base_service.get_document_statistics.assert_called_once_with('doc123')
    
    @pytest.mark.asyncio
    async def test_get_service_stats(self, enhanced_service, mock_base_service, mock_search_router):
        """测试获取服务统计"""
        # 设置模拟统计数据
        base_stats = {'base_service': 'stats'}
        enhanced_stats = {'enhanced_service': 'stats'}
        
        mock_base_service.get_service_stats.return_value = base_stats
        mock_search_router.get_usage_statistics.return_value = enhanced_stats
        
        # 模拟依赖服务
        with patch.object(enhanced_service, 'base_retrieval_service', mock_base_service), \
             patch.object(enhanced_service, 'search_router', mock_search_router):
            
            stats = await enhanced_service.get_service_stats()
            
            assert stats['service_name'] == 'EnhancedRetrievalService'
            assert stats['base_service_stats'] == base_stats
            assert 'enhanced_service_stats' in stats
    
    @pytest.mark.asyncio
    async def test_test_search(self, enhanced_service, mock_search_router, sample_results):
        """测试搜索功能测试"""
        # 设置模拟返回值
        mock_search_router.search_with_mode.return_value = sample_results
        
        # 模拟依赖服务
        with patch.object(enhanced_service, 'search_router', mock_search_router), \
             patch.object(enhanced_service, 'get_service_stats', AsyncMock(return_value={'test': 'stats'})):
            
            result = await enhanced_service.test_search("测试查询")
            
            assert result['success'] is True
            assert result['test_query'] == "测试查询"
            assert result['result_count'] == 2
            assert 'processing_time' in result
            assert result['search_mode'] == 'semantic'
            assert result['top_similarity'] == 0.9
    
    @pytest.mark.asyncio
    async def test_test_search_failure(self, enhanced_service, mock_search_router):
        """测试搜索功能测试失败"""
        # 设置搜索失败
        mock_search_router.search_with_mode.side_effect = Exception("搜索失败")
        
        # 模拟搜索路由器
        with patch.object(enhanced_service, 'search_router', mock_search_router):
            result = await enhanced_service.test_search("测试查询")
            
            assert result['success'] is False
            assert "搜索失败" in result['error']
            assert result['test_query'] == "测试查询"
    
    @pytest.mark.asyncio
    async def test_search_with_config_failure(self, enhanced_service, mock_search_router):
        """测试配置化搜索失败"""
        # 设置搜索失败
        mock_search_router.search_with_mode.side_effect = Exception("路由器失败")
        
        # 模拟搜索路由器
        with patch.object(enhanced_service, 'search_router', mock_search_router):
            with pytest.raises(ProcessingError) as exc_info:
                await enhanced_service.search_with_config("测试查询")
            
            assert "配置化检索失败" in str(exc_info.value)
            assert "路由器失败" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_initialization_failure(self, enhanced_service, mock_base_service, mock_search_router):
        """测试初始化失败"""
        # 设置基础服务初始化失败
        mock_base_service.initialize.side_effect = Exception("基础服务初始化失败")
        
        # 模拟依赖服务
        with patch.object(enhanced_service, 'base_retrieval_service', mock_base_service), \
             patch.object(enhanced_service, 'search_router', mock_search_router):
            
            with pytest.raises(ProcessingError) as exc_info:
                await enhanced_service.initialize()
            
            assert "增强检索服务初始化失败" in str(exc_info.value)


if __name__ == '__main__':
    pytest.main([__file__])