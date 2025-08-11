"""
健康监控系统集成测试
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from rag_system.utils.health_checker import ModelHealthChecker, ModelHealthCheckConfig
from rag_system.services.health_monitoring_service import HealthMonitoringService, AlertLevel
from rag_system.api.health_api import initialize_health_checker
from rag_system.llm.base import LLMConfig
from rag_system.embeddings.base import EmbeddingConfig


class TestHealthMonitoringIntegration:
    """健康监控系统集成测试"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.llm_configs = [
            LLMConfig(provider="mock", model="test-llm-1", api_key="key1"),
            LLMConfig(provider="mock", model="test-llm-2", api_key="key2")
        ]
        self.embedding_configs = [
            EmbeddingConfig(provider="mock", model="test-embedding", api_key="key3")
        ]
    
    @pytest.mark.asyncio
    async def test_end_to_end_health_monitoring(self):
        """端到端健康监控测试"""
        # 1. 创建健康检查器
        config = ModelHealthCheckConfig(
            check_interval=1,  # 1秒检查一次（测试用）
            timeout=5,
            enable_periodic_check=True
        )
        health_checker = ModelHealthChecker(config)
        
        # 2. 创建监控服务
        alert_handler = Mock()
        monitoring_service = HealthMonitoringService(
            health_checker=health_checker,
            llm_configs=self.llm_configs,
            embedding_configs=self.embedding_configs,
            alert_handlers=[alert_handler]
        )
        monitoring_service.monitoring_interval = 1  # 1秒监控间隔
        
        # 3. Mock模型工厂以模拟不同的健康状态
        with patch('rag_system.utils.health_checker.LLMFactory.create_llm') as mock_llm_factory, \
             patch('rag_system.utils.health_checker.EmbeddingFactory.create_embedding') as mock_embedding_factory:
            
            # Mock健康的LLM
            healthy_llm = AsyncMock()
            healthy_llm.generate.return_value = "Test response"
            
            # Mock不健康的LLM
            unhealthy_llm = AsyncMock()
            unhealthy_llm.generate.side_effect = Exception("Connection failed")
            
            # Mock健康的嵌入模型
            healthy_embedding = AsyncMock()
            healthy_embedding.embed_text.return_value = [0.1, 0.2, 0.3]
            
            def llm_factory_side_effect(config):
                if config.model == "test-llm-1":
                    return healthy_llm
                else:
                    return unhealthy_llm
            
            mock_llm_factory.side_effect = llm_factory_side_effect
            mock_embedding_factory.return_value = healthy_embedding
            
            try:
                # 4. 启动监控
                await monitoring_service.start_monitoring()
                
                # 5. 等待几次检查周期
                await asyncio.sleep(3)
                
                # 6. 验证健康检查结果
                report = health_checker.generate_health_report()
                
                # 应该有3个模型（2个LLM + 1个嵌入模型）
                assert report["total_models"] == 3
                
                # 应该有2个健康模型（1个LLM + 1个嵌入模型）
                assert report["healthy_models"] == 2
                
                # 应该有1个不健康模型
                assert report["unhealthy_models"] == 1
                
                # 整体状态应该是降级
                assert report["overall_status"] == "degraded"
                
                # 7. 验证告警生成
                active_alerts = monitoring_service.get_active_alerts()
                
                # 应该有告警生成
                assert len(active_alerts) > 0
                
                # 应该有系统级告警（因为有不健康的模型）
                system_alerts = [a for a in active_alerts if a.component == "system"]
                assert len(system_alerts) > 0
                
                # 应该有模型级告警
                model_alerts = [a for a in active_alerts if "mock/test-llm-2" in a.component]
                assert len(model_alerts) > 0
                
                # 验证告警处理器被调用
                assert alert_handler.call_count > 0
                
                # 8. 验证API集成
                # 模拟修复不健康的模型
                unhealthy_llm.generate.side_effect = None
                unhealthy_llm.generate.return_value = "Fixed response"
                
                # 等待下一次检查
                await asyncio.sleep(2)
                
                # 验证状态改善
                new_report = health_checker.generate_health_report()
                assert new_report["healthy_models"] >= report["healthy_models"]
                
            finally:
                # 9. 清理
                await monitoring_service.stop_monitoring()
                health_checker.cleanup()
    
    @pytest.mark.asyncio
    async def test_alert_lifecycle(self):
        """测试告警生命周期"""
        # 创建健康检查器和监控服务
        health_checker = ModelHealthChecker()
        monitoring_service = HealthMonitoringService(
            health_checker=health_checker,
            llm_configs=self.llm_configs,
            embedding_configs=[]
        )
        
        # 1. 创建告警
        await monitoring_service._create_alert(
            alert_id="test_alert",
            level=AlertLevel.ERROR,
            title="测试告警",
            message="测试消息",
            component="test_component"
        )
        
        # 验证告警创建
        active_alerts = monitoring_service.get_active_alerts()
        assert len(active_alerts) == 1
        assert active_alerts[0].id == "test_alert"
        assert not active_alerts[0].resolved
        
        # 2. 解决告警
        await monitoring_service._resolve_alert("test_alert")
        
        # 验证告警解决
        alert = monitoring_service.active_alerts["test_alert"]
        assert alert.resolved
        assert alert.resolved_at is not None
        
        # 活跃告警列表应该为空
        active_alerts = monitoring_service.get_active_alerts()
        assert len(active_alerts) == 0
    
    @pytest.mark.asyncio
    async def test_alert_cooldown(self):
        """测试告警冷却机制"""
        health_checker = ModelHealthChecker()
        monitoring_service = HealthMonitoringService(
            health_checker=health_checker,
            llm_configs=[],
            embedding_configs=[]
        )
        monitoring_service.alert_cooldown = 2  # 2秒冷却时间
        
        alert_handler = Mock()
        monitoring_service.add_alert_handler(alert_handler)
        
        # 1. 创建第一个告警
        await monitoring_service._create_alert(
            alert_id="cooldown_test",
            level=AlertLevel.ERROR,
            title="冷却测试",
            message="第一次告警",
            component="test"
        )
        
        # 2. 立即尝试创建相同告警
        await monitoring_service._create_alert(
            alert_id="cooldown_test",
            level=AlertLevel.ERROR,
            title="冷却测试",
            message="第二次告警",
            component="test"
        )
        
        # 验证处理器只被调用一次（第二次被冷却阻止）
        assert alert_handler.call_count == 1
        
        # 3. 等待冷却时间过去
        await asyncio.sleep(2.1)
        
        # 4. 解决第一个告警
        await monitoring_service._resolve_alert("cooldown_test")
        
        # 5. 再次创建告警
        await monitoring_service._create_alert(
            alert_id="cooldown_test",
            level=AlertLevel.ERROR,
            title="冷却测试",
            message="冷却后告警",
            component="test"
        )
        
        # 验证处理器被再次调用
        assert alert_handler.call_count == 2
    
    @pytest.mark.asyncio
    async def test_health_api_integration(self):
        """测试健康检查API集成"""
        # 初始化健康检查器
        health_checker = initialize_health_checker(
            self.llm_configs,
            self.embedding_configs
        )
        
        # Mock模型工厂
        with patch('rag_system.utils.health_checker.LLMFactory.create_llm') as mock_llm_factory, \
             patch('rag_system.utils.health_checker.EmbeddingFactory.create_embedding') as mock_embedding_factory:
            
            # Mock健康的模型
            healthy_llm = AsyncMock()
            healthy_llm.generate.return_value = "Test response"
            
            healthy_embedding = AsyncMock()
            healthy_embedding.embed_text.return_value = [0.1, 0.2, 0.3]
            
            mock_llm_factory.return_value = healthy_llm
            mock_embedding_factory.return_value = healthy_embedding
            
            try:
                # 等待一次健康检查
                await asyncio.sleep(1)
                
                # 验证健康检查器状态
                report = health_checker.generate_health_report()
                assert report["total_models"] >= 0  # 可能还没有检查完成
                
                # 手动触发检查
                await health_checker.check_all_models(
                    self.llm_configs,
                    self.embedding_configs
                )
                
                # 验证检查结果
                report = health_checker.generate_health_report()
                assert report["total_models"] == 3
                assert report["healthy_models"] == 3
                assert report["unhealthy_models"] == 0
                assert report["overall_status"] == "healthy"
                
            finally:
                # 清理
                await health_checker.stop_periodic_check()
                health_checker.cleanup()
    
    def test_alert_handlers_integration(self):
        """测试告警处理器集成"""
        from rag_system.services.health_monitoring_service import (
            console_alert_handler, file_alert_handler
        )
        from rag_system.services.health_monitoring_service import Alert, AlertLevel
        
        # 创建测试告警
        alert = Alert(
            id="handler_test",
            level=AlertLevel.WARNING,
            title="处理器测试",
            message="测试告警处理器",
            component="test",
            timestamp=datetime.now()
        )
        
        # 测试控制台处理器（不会抛出异常）
        try:
            console_alert_handler(alert)
        except Exception as e:
            pytest.fail(f"控制台告警处理器失败: {str(e)}")
        
        # 测试文件处理器
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            log_file = f.name
        
        try:
            file_alert_handler(alert, log_file)
            
            # 验证日志文件内容
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                assert "处理器测试" in content
                assert "WARNING" in content
                
        finally:
            # 清理临时文件
            if os.path.exists(log_file):
                os.unlink(log_file)