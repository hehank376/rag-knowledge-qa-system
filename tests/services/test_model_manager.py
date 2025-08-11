"""
统一模型管理器测试模块

测试模型管理器的各种功能：
- 模型配置管理
- 模型加载和卸载
- 模型切换
- 健康检查
- 统计信息收集
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from rag_system.services.model_manager import (
    ModelManager, 
    ModelConfig, 
    ModelStatus, 
    ModelType,
    initialize_global_model_manager,
    get_model_manager,
    cleanup_global_model_manager
)
from rag_system.services.embedding_service import EmbeddingService
from rag_system.services.reranking_service import RerankingService


class TestModelConfig:
    """模型配置测试"""
    
    def test_model_config_creation(self):
        """测试模型配置创建"""
        config = ModelConfig(
            model_type=ModelType.EMBEDDING,
            name="test_embedding",
            provider="openai",
            model_name="text-embedding-ada-002",
            config={"api_key": "test_key"},
            enabled=True,
            priority=10
        )
        
        assert config.model_type == ModelType.EMBEDDING
        assert config.name == "test_embedding"
        assert config.provider == "openai"
        assert config.model_name == "text-embedding-ada-002"
        assert config.config["api_key"] == "test_key"
        assert config.enabled is True
        assert config.priority == 10
    
    def test_model_config_to_dict(self):
        """测试模型配置转换为字典"""
        config = ModelConfig(
            model_type=ModelType.RERANKING,
            name="test_reranking",
            provider="sentence_transformers",
            model_name="cross-encoder/ms-marco-MiniLM-L-6-v2"
        )
        
        config_dict = config.to_dict()
        
        assert config_dict['model_type'] == 'reranking'
        assert config_dict['name'] == 'test_reranking'
        assert config_dict['provider'] == 'sentence_transformers'
        assert config_dict['model_name'] == 'cross-encoder/ms-marco-MiniLM-L-6-v2'
        assert 'created_at' in config_dict
        assert 'updated_at' in config_dict
    
    def test_model_config_from_dict(self):
        """测试从字典创建模型配置"""
        config_dict = {
            'model_type': 'embedding',
            'name': 'test_embedding',
            'provider': 'openai',
            'model_name': 'text-embedding-ada-002',
            'config': {'api_key': 'test_key'},
            'enabled': True,
            'priority': 5,
            'created_at': '2024-01-01T00:00:00',
            'updated_at': '2024-01-01T00:00:00'
        }
        
        config = ModelConfig.from_dict(config_dict)
        
        assert config.model_type == ModelType.EMBEDDING
        assert config.name == 'test_embedding'
        assert config.provider == 'openai'
        assert config.model_name == 'text-embedding-ada-002'
        assert config.config['api_key'] == 'test_key'


class TestModelStatus:
    """模型状态测试"""
    
    def test_model_status_creation(self):
        """测试模型状态创建"""
        status = ModelStatus(
            name="test_model",
            model_type=ModelType.EMBEDDING,
            status="ready",
            health="healthy",
            load_time=1.5,
            last_used=datetime.now(),
            metrics={"requests": 100}
        )
        
        assert status.name == "test_model"
        assert status.model_type == ModelType.EMBEDDING
        assert status.status == "ready"
        assert status.health == "healthy"
        assert status.load_time == 1.5
        assert status.metrics["requests"] == 100
    
    def test_model_status_to_dict(self):
        """测试模型状态转换为字典"""
        status = ModelStatus(
            name="test_model",
            model_type=ModelType.RERANKING,
            status="loading",
            health="unknown"
        )
        
        status_dict = status.to_dict()
        
        assert status_dict['name'] == 'test_model'
        assert status_dict['model_type'] == 'reranking'
        assert status_dict['status'] == 'loading'
        assert status_dict['health'] == 'unknown'


class TestModelManager:
    """模型管理器测试"""
    
    @pytest.fixture
    def manager_config(self):
        """管理器配置fixture"""
        return {
            'auto_load_models': False,  # 禁用自动加载以便测试
            'enable_model_switching': True,
            'model_cache_size': 2,
            'health_check_interval': 60,
            'default_embedding_models': [
                {
                    'name': 'test_embedding',
                    'provider': 'mock',
                    'model_name': 'mock-embedding',
                    'config': {'dimensions': 768},
                    'enabled': True,
                    'priority': 10
                }
            ],
            'default_reranking_models': [
                {
                    'name': 'test_reranking',
                    'provider': 'sentence_transformers',
                    'model_name': 'test-rerank-model',
                    'config': {'batch_size': 16},
                    'enabled': True,
                    'priority': 10
                }
            ]
        }
    
    @pytest.fixture
    def model_manager(self, manager_config):
        """模型管理器fixture"""
        return ModelManager(manager_config)
    
    @pytest.mark.asyncio
    async def test_manager_initialization(self, model_manager):
        """测试管理器初始化"""
        with patch.object(model_manager, '_auto_load_models') as mock_auto_load:
            await model_manager.initialize()
            
            # 验证默认配置已加载
            assert len(model_manager.model_configs) == 2
            assert 'test_embedding' in model_manager.model_configs
            assert 'test_reranking' in model_manager.model_configs
            
            # 验证统计信息
            assert model_manager.stats['total_models'] == 2
    
    @pytest.mark.asyncio
    async def test_register_model(self, model_manager):
        """测试注册模型配置"""
        await model_manager.initialize()
        
        new_config = ModelConfig(
            model_type=ModelType.EMBEDDING,
            name="new_embedding",
            provider="openai",
            model_name="text-embedding-ada-002",
            config={"api_key": "test_key"}
        )
        
        result = await model_manager.register_model(new_config)
        
        assert result is True
        assert 'new_embedding' in model_manager.model_configs
        assert 'new_embedding' in model_manager.model_statuses
        assert model_manager.model_statuses['new_embedding'].status == 'registered'
    
    @pytest.mark.asyncio
    async def test_load_embedding_model(self, model_manager):
        """测试加载embedding模型"""
        await model_manager.initialize()
        
        with patch.object(model_manager, '_load_embedding_model', return_value=True) as mock_load:
            result = await model_manager.load_model('test_embedding')
            
            assert result is True
            mock_load.assert_called_once()
            assert model_manager.model_statuses['test_embedding'].status == 'ready'
            assert model_manager.model_statuses['test_embedding'].health == 'healthy'
            assert model_manager.stats['loaded_models'] == 1
    
    @pytest.mark.asyncio
    async def test_load_reranking_model(self, model_manager):
        """测试加载重排序模型"""
        await model_manager.initialize()
        
        with patch.object(model_manager, '_load_reranking_model', return_value=True) as mock_load:
            result = await model_manager.load_model('test_reranking')
            
            assert result is True
            mock_load.assert_called_once()
            assert model_manager.model_statuses['test_reranking'].status == 'ready'
            assert model_manager.model_statuses['test_reranking'].health == 'healthy'
    
    @pytest.mark.asyncio
    async def test_load_model_failure(self, model_manager):
        """测试模型加载失败"""
        await model_manager.initialize()
        
        with patch.object(model_manager, '_load_embedding_model', return_value=False) as mock_load:
            result = await model_manager.load_model('test_embedding')
            
            assert result is False
            assert model_manager.model_statuses['test_embedding'].status == 'error'
            assert model_manager.model_statuses['test_embedding'].health == 'unhealthy'
            assert model_manager.stats['failed_models'] == 1
    
    @pytest.mark.asyncio
    async def test_unload_model(self, model_manager):
        """测试卸载模型"""
        await model_manager.initialize()
        
        # 先加载模型
        with patch.object(model_manager, '_load_embedding_model', return_value=True):
            await model_manager.load_model('test_embedding')
            model_manager.active_embedding_model = 'test_embedding'
        
        # 模拟embedding服务
        mock_service = AsyncMock()
        model_manager.embedding_services['test_embedding'] = mock_service
        
        # 卸载模型
        result = await model_manager.unload_model('test_embedding')
        
        assert result is True
        assert 'test_embedding' not in model_manager.embedding_services
        assert model_manager.active_embedding_model is None
        assert model_manager.model_statuses['test_embedding'].status == 'unloaded'
        mock_service.cleanup.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_switch_active_model(self, model_manager):
        """测试切换活跃模型"""
        await model_manager.initialize()
        
        # 模拟模型已加载
        model_manager.model_statuses['test_embedding'] = ModelStatus(
            name='test_embedding',
            model_type=ModelType.EMBEDDING,
            status='ready',
            health='healthy'
        )
        
        result = await model_manager.switch_active_model(ModelType.EMBEDDING, 'test_embedding')
        
        assert result is True
        assert model_manager.active_embedding_model == 'test_embedding'
        assert model_manager.stats['model_switches'] == 1
    
    @pytest.mark.asyncio
    async def test_switch_active_model_with_loading(self, model_manager):
        """测试切换活跃模型时自动加载"""
        await model_manager.initialize()
        
        with patch.object(model_manager, 'load_model', return_value=True) as mock_load:
            result = await model_manager.switch_active_model(ModelType.EMBEDDING, 'test_embedding')
            
            assert result is True
            mock_load.assert_called_once_with('test_embedding')
            assert model_manager.active_embedding_model == 'test_embedding'
    
    def test_get_active_embedding_service(self, model_manager):
        """测试获取活跃embedding服务"""
        # 设置活跃模型和服务
        model_manager.active_embedding_model = 'test_embedding'
        mock_service = Mock()
        model_manager.embedding_services['test_embedding'] = mock_service
        model_manager.model_statuses['test_embedding'] = ModelStatus(
            name='test_embedding',
            model_type=ModelType.EMBEDDING,
            status='ready',
            health='healthy'
        )
        
        service = model_manager.get_active_embedding_service()
        
        assert service == mock_service
        assert model_manager.stats['embedding_requests'] == 1
        assert model_manager.stats['total_requests'] == 1
        assert model_manager.model_statuses['test_embedding'].last_used is not None
    
    def test_get_active_reranking_service(self, model_manager):
        """测试获取活跃重排序服务"""
        # 设置活跃模型和服务
        model_manager.active_reranking_model = 'test_reranking'
        mock_service = Mock()
        model_manager.reranking_services['test_reranking'] = mock_service
        model_manager.model_statuses['test_reranking'] = ModelStatus(
            name='test_reranking',
            model_type=ModelType.RERANKING,
            status='ready',
            health='healthy'
        )
        
        service = model_manager.get_active_reranking_service()
        
        assert service == mock_service
        assert model_manager.stats['reranking_requests'] == 1
        assert model_manager.stats['total_requests'] == 1
    
    def test_get_service_by_name(self, model_manager):
        """测试按名称获取服务"""
        mock_embedding_service = Mock()
        mock_reranking_service = Mock()
        
        model_manager.embedding_services['test_embedding'] = mock_embedding_service
        model_manager.reranking_services['test_reranking'] = mock_reranking_service
        
        assert model_manager.get_embedding_service('test_embedding') == mock_embedding_service
        assert model_manager.get_reranking_service('test_reranking') == mock_reranking_service
        assert model_manager.get_embedding_service('nonexistent') is None
        assert model_manager.get_reranking_service('nonexistent') is None
    
    @pytest.mark.asyncio
    async def test_health_check_embedding_service(self, model_manager):
        """测试embedding服务健康检查"""
        # 设置模拟服务
        mock_service = AsyncMock()
        mock_service.test_embedding.return_value = {'success': True}
        model_manager.embedding_services['test_embedding'] = mock_service
        model_manager.model_statuses['test_embedding'] = ModelStatus(
            name='test_embedding',
            model_type=ModelType.EMBEDDING,
            status='ready',
            health='unknown'
        )
        
        # 执行健康检查
        await model_manager._perform_health_checks()
        
        # 验证健康状态更新
        assert model_manager.model_statuses['test_embedding'].health == 'healthy'
        assert model_manager.model_statuses['test_embedding'].error_message is None
        mock_service.test_embedding.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_reranking_service(self, model_manager):
        """测试重排序服务健康检查"""
        # 设置模拟服务
        mock_service = AsyncMock()
        mock_service.health_check.return_value = {'status': 'healthy'}
        model_manager.reranking_services['test_reranking'] = mock_service
        model_manager.model_statuses['test_reranking'] = ModelStatus(
            name='test_reranking',
            model_type=ModelType.RERANKING,
            status='ready',
            health='unknown'
        )
        
        # 执行健康检查
        await model_manager._perform_health_checks()
        
        # 验证健康状态更新
        assert model_manager.model_statuses['test_reranking'].health == 'healthy'
        assert model_manager.model_statuses['test_reranking'].error_message is None
        mock_service.health_check.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_service_failure(self, model_manager):
        """测试服务健康检查失败"""
        # 设置模拟服务
        mock_service = AsyncMock()
        mock_service.test_embedding.side_effect = Exception("Service error")
        model_manager.embedding_services['test_embedding'] = mock_service
        model_manager.model_statuses['test_embedding'] = ModelStatus(
            name='test_embedding',
            model_type=ModelType.EMBEDDING,
            status='ready',
            health='healthy'
        )
        
        # 执行健康检查
        await model_manager._perform_health_checks()
        
        # 验证健康状态更新
        assert model_manager.model_statuses['test_embedding'].health == 'unhealthy'
        assert model_manager.model_statuses['test_embedding'].error_message == 'Service error'
    
    def test_get_manager_stats(self, model_manager):
        """测试获取管理器统计"""
        model_manager.active_embedding_model = 'test_embedding'
        model_manager.active_reranking_model = 'test_reranking'
        model_manager.stats['total_requests'] = 100
        
        stats = model_manager.get_manager_stats()
        
        assert stats['active_embedding_model'] == 'test_embedding'
        assert stats['active_reranking_model'] == 'test_reranking'
        assert stats['total_requests'] == 100
        assert 'total_embedding_services' in stats
        assert 'total_reranking_services' in stats
    
    @pytest.mark.asyncio
    async def test_get_comprehensive_status(self, model_manager):
        """测试获取综合状态"""
        await model_manager.initialize()
        
        # 设置模拟服务
        mock_embedding_service = AsyncMock()
        mock_embedding_service.get_service_stats.return_value = {'embedding': 'stats'}
        mock_reranking_service = Mock()
        mock_reranking_service.get_metrics.return_value = {'reranking': 'metrics'}
        
        model_manager.embedding_services['test_embedding'] = mock_embedding_service
        model_manager.reranking_services['test_reranking'] = mock_reranking_service
        
        status = await model_manager.get_comprehensive_status()
        
        assert 'manager_stats' in status
        assert 'model_configs' in status
        assert 'model_statuses' in status
        assert 'active_models' in status
        assert 'service_details' in status
        assert 'embedding_services' in status['service_details']
        assert 'reranking_services' in status['service_details']
    
    @pytest.mark.asyncio
    async def test_cleanup(self, model_manager):
        """测试清理资源"""
        # 设置模拟服务
        mock_embedding_service = AsyncMock()
        mock_reranking_service = AsyncMock()
        
        model_manager.embedding_services['test_embedding'] = mock_embedding_service
        model_manager.reranking_services['test_reranking'] = mock_reranking_service
        model_manager.active_embedding_model = 'test_embedding'
        model_manager.active_reranking_model = 'test_reranking'
        
        await model_manager.cleanup()
        
        # 验证服务被清理
        mock_embedding_service.cleanup.assert_called_once()
        mock_reranking_service.close.assert_called_once()
        
        # 验证数据被清理
        assert len(model_manager.embedding_services) == 0
        assert len(model_manager.reranking_services) == 0
        assert len(model_manager.model_statuses) == 0
        assert model_manager.active_embedding_model is None
        assert model_manager.active_reranking_model is None


class TestGlobalModelManager:
    """全局模型管理器测试"""
    
    @pytest.mark.asyncio
    async def test_initialize_global_model_manager(self):
        """测试初始化全局模型管理器"""
        # 清理可能存在的全局实例
        await cleanup_global_model_manager()
        
        config = {'auto_load_models': False}
        
        with patch('rag_system.services.model_manager.ModelManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager
            
            manager = await initialize_global_model_manager(config)
            
            assert manager == mock_manager
            mock_manager_class.assert_called_once_with(config)
            mock_manager.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_global_model_manager(self):
        """测试获取全局模型管理器"""
        # 清理可能存在的全局实例
        await cleanup_global_model_manager()
        
        # 初始状态应该返回None
        assert get_model_manager() is None
        
        # 初始化后应该返回实例
        with patch('rag_system.services.model_manager.ModelManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager
            
            await initialize_global_model_manager()
            assert get_model_manager() == mock_manager
    
    @pytest.mark.asyncio
    async def test_cleanup_global_model_manager(self):
        """测试清理全局模型管理器"""
        # 清理可能存在的全局实例
        await cleanup_global_model_manager()
        
        # 初始化全局实例
        with patch('rag_system.services.model_manager.ModelManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager
            
            await initialize_global_model_manager()
            assert get_model_manager() is not None
            
            # 清理全局实例
            await cleanup_global_model_manager()
            assert get_model_manager() is None
            mock_manager.cleanup.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])