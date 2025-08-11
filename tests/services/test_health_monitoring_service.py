"""
测试健康监控服务
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from rag_system.services.health_monitoring_service import (
    HealthMonitoringService, Alert, AlertLevel, console_alert_handler
)
from rag_system.utils.health_checker import ModelHealthChecker, ModelHealthCheckConfig
from rag_system.llm.base import LLMConfig
from rag_system.embeddings.base import EmbeddingConfig


class TestAlert:
    """测试告警类"""
    
    def test_alert_creation(self):
        """测试告警创建"""
        alert = Alert(
            id="test_alert",
            level=AlertLevel.ERROR,
            title="测试告警",
            message="这是一个测试告警",
            component="test_component",
            timestamp=datetime.now()
        )
        
        assert alert.id == "test_alert"
        assert alert.level == AlertLevel.ERROR
        assert alert.title == "测试告警"
        assert alert.message == "这是一个测试告警"
        assert alert.component == "test_component"
        assert not alert.resolved
        assert alert.resolved_at is None


class TestHealthMonitoringService:
    """测试健康监控服务"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.health_checker = Mock(spec=ModelHealthChecker)
        self.llm_configs = [
            LLMConfig(provider="mock", model="test-llm", api_key="key1")
        ]
        self.embedding_configs = [
            EmbeddingConfig(provider="mock", model="test-embedding", api_key="key2")
        ]
        
        self.service = HealthMonitoringService(
            health_checker=self.health_checker,
            llm_configs=self.llm_configs,
            embedding_configs=self.embedding_configs
        )
    
    def test_initialization(self):
        """测试初始化"""
        assert self.service.health_checker == self.health_checker
        assert self.service.llm_configs == self.llm_configs
        assert self.service.embedding_configs == self.embedding_configs
        assert len(self.service.alert_handlers) == 0
        assert len(self.service.active_alerts) == 0
        assert len(self.service.alert_history) == 0
        assert not self.service._running
    
    def test_add_alert_handler(self):
        """测试添加告警处理器"""
        handler = Mock()
        self.service.add_alert_handler(handler)
        
        assert handler in self.service.alert_handlers
    
    def test_remove_alert_handler(self):
        """测试移除告警处理器"""
        handler = Mock()
        self.service.add_alert_handler(handler)
        self.service.remove_alert_handler(handler)
        
        assert handler not in self.service.alert_handlers
    
    @pytest.mark.asyncio
    async def test_create_alert(self):
        """测试创建告警"""
        handler = Mock()
        self.service.add_alert_handler(handler)
        
        await self.service._create_alert(
            alert_id="test_alert",
            level=AlertLevel.ERROR,
            title="测试告警",
            message="测试消息",
            component="test_component"
        )
        
        # 验证告警已创建
        assert "test_alert" in self.service.active_alerts
        alert = self.service.active_alerts["test_alert"]
        assert alert.level == AlertLevel.ERROR
        assert alert.title == "测试告警"
        assert alert.message == "测试消息"
        assert alert.component == "test_component"
        assert not alert.resolved
        
        # 验证处理器被调用
        handler.assert_called_once_with(alert)
    
    @pytest.mark.asyncio
    async def test_create_duplicate_alert(self):
        """测试创建重复告警"""
        handler = Mock()
        self.service.add_alert_handler(handler)
        
        # 创建第一个告警
        await self.service._create_alert(
            alert_id="test_alert",
            level=AlertLevel.ERROR,
            title="测试告警",
            message="测试消息",
            component="test_component"
        )
        
        # 尝试创建相同ID的告警
        await self.service._create_alert(
            alert_id="test_alert",
            level=AlertLevel.WARNING,
            title="另一个告警",
            message="另一个消息",
            component="test_component"
        )
        
        # 验证只有一个告警
        assert len(self.service.active_alerts) == 1
        assert handler.call_count == 1  # 处理器只被调用一次
    
    @pytest.mark.asyncio
    async def test_resolve_alert(self):
        """测试解决告警"""
        # 创建告警
        await self.service._create_alert(
            alert_id="test_alert",
            level=AlertLevel.ERROR,
            title="测试告警",
            message="测试消息",
            component="test_component"
        )
        
        # 解决告警
        await self.service._resolve_alert("test_alert")
        
        # 验证告警已解决
        alert = self.service.active_alerts["test_alert"]
        assert alert.resolved
        assert alert.resolved_at is not None
    
    @pytest.mark.asyncio
    async def test_resolve_nonexistent_alert(self):
        """测试解决不存在的告警"""
        # 不应该抛出异常
        await self.service._resolve_alert("nonexistent_alert")
    
    def test_cleanup_resolved_alerts(self):
        """测试清理已解决的告警"""
        # 创建一个已解决的告警（1小时前解决）
        old_time = datetime.now() - timedelta(hours=2)
        alert = Alert(
            id="old_alert",
            level=AlertLevel.ERROR,
            title="旧告警",
            message="旧消息",
            component="test",
            timestamp=old_time,
            resolved=True,
            resolved_at=old_time + timedelta(minutes=5)
        )
        self.service.active_alerts["old_alert"] = alert
        
        # 创建一个最近解决的告警
        recent_time = datetime.now() - timedelta(minutes=30)
        recent_alert = Alert(
            id="recent_alert",
            level=AlertLevel.WARNING,
            title="最近告警",
            message="最近消息",
            component="test",
            timestamp=recent_time,
            resolved=True,
            resolved_at=recent_time + timedelta(minutes=5)
        )
        self.service.active_alerts["recent_alert"] = recent_alert
        
        # 执行清理
        self.service._cleanup_resolved_alerts()
        
        # 验证旧告警被移到历史记录
        assert "old_alert" not in self.service.active_alerts
        assert len(self.service.alert_history) == 1
        assert self.service.alert_history[0].id == "old_alert"
        
        # 验证最近的告警仍在活跃列表
        assert "recent_alert" in self.service.active_alerts
    
    def test_get_active_alerts(self):
        """测试获取活跃告警"""
        # 创建活跃告警
        active_alert = Alert(
            id="active_alert",
            level=AlertLevel.ERROR,
            title="活跃告警",
            message="活跃消息",
            component="test",
            timestamp=datetime.now()
        )
        self.service.active_alerts["active_alert"] = active_alert
        
        # 创建已解决告警
        resolved_alert = Alert(
            id="resolved_alert",
            level=AlertLevel.WARNING,
            title="已解决告警",
            message="已解决消息",
            component="test",
            timestamp=datetime.now(),
            resolved=True,
            resolved_at=datetime.now()
        )
        self.service.active_alerts["resolved_alert"] = resolved_alert
        
        # 获取活跃告警
        active_alerts = self.service.get_active_alerts()
        
        # 验证只返回未解决的告警
        assert len(active_alerts) == 1
        assert active_alerts[0].id == "active_alert"
    
    def test_get_alert_history(self):
        """测试获取告警历史"""
        # 添加历史告警
        for i in range(5):
            alert = Alert(
                id=f"history_alert_{i}",
                level=AlertLevel.INFO,
                title=f"历史告警 {i}",
                message=f"历史消息 {i}",
                component="test",
                timestamp=datetime.now()
            )
            self.service.alert_history.append(alert)
        
        # 获取历史记录
        history = self.service.get_alert_history(limit=3)
        
        # 验证返回最近的3个
        assert len(history) == 3
        assert history[0].id == "history_alert_2"
        assert history[1].id == "history_alert_3"
        assert history[2].id == "history_alert_4"
    
    @pytest.mark.asyncio
    async def test_check_overall_health_unhealthy(self):
        """测试检查整体健康状态 - 不健康"""
        report = {
            "overall_status": "unhealthy",
            "unhealthy_models": 3,
            "models": {},
            "providers": {}
        }
        
        await self.service._check_overall_health(report)
        
        # 验证创建了系统级告警
        assert "system_overall_health" in self.service.active_alerts
        alert = self.service.active_alerts["system_overall_health"]
        assert alert.level == AlertLevel.CRITICAL
        assert "系统整体健康状态异常" in alert.title
    
    @pytest.mark.asyncio
    async def test_check_overall_health_degraded(self):
        """测试检查整体健康状态 - 降级"""
        report = {
            "overall_status": "degraded",
            "unhealthy_models": 1,
            "models": {},
            "providers": {}
        }
        
        await self.service._check_overall_health(report)
        
        # 验证创建了警告级告警
        assert "system_overall_health" in self.service.active_alerts
        alert = self.service.active_alerts["system_overall_health"]
        assert alert.level == AlertLevel.WARNING
        assert "系统健康状态降级" in alert.title
    
    @pytest.mark.asyncio
    async def test_check_model_health_unhealthy(self):
        """测试检查模型健康状态 - 不健康"""
        report = {
            "models": {
                "test:llm:model1": {
                    "provider": "test",
                    "model_name": "model1",
                    "model_type": "llm",
                    "is_healthy": False,
                    "consecutive_failures": 3,
                    "success_rate": 0.5,
                    "total_checks": 10,
                    "error_message": "Connection failed"
                }
            }
        }
        
        await self.service._check_model_health(report)
        
        # 验证创建了模型告警
        assert "model_test:llm:model1" in self.service.active_alerts
        alert = self.service.active_alerts["model_test:llm:model1"]
        assert alert.level == AlertLevel.ERROR
        assert "model1 不健康" in alert.title
    
    @pytest.mark.asyncio
    async def test_check_model_health_low_success_rate(self):
        """测试检查模型健康状态 - 成功率低"""
        report = {
            "models": {
                "test:llm:model1": {
                    "provider": "test",
                    "model_name": "model1",
                    "model_type": "llm",
                    "is_healthy": True,
                    "consecutive_failures": 0,
                    "success_rate": 0.7,  # 低于0.8阈值
                    "total_checks": 20,
                    "error_message": None
                }
            }
        }
        
        await self.service._check_model_health(report)
        
        # 验证创建了成功率低告警
        assert "model_test:llm:model1_low_success_rate" in self.service.active_alerts
        alert = self.service.active_alerts["model_test:llm:model1_low_success_rate"]
        assert alert.level == AlertLevel.WARNING
        assert "成功率较低" in alert.title


class TestAlertHandlers:
    """测试告警处理器"""
    
    def test_console_alert_handler(self, capsys):
        """测试控制台告警处理器"""
        alert = Alert(
            id="test_alert",
            level=AlertLevel.ERROR,
            title="测试告警",
            message="测试消息",
            component="test",
            timestamp=datetime.now()
        )
        
        console_alert_handler(alert)
        
        captured = capsys.readouterr()
        assert "ERROR" in captured.out
        assert "测试告警" in captured.out
        assert "测试消息" in captured.out