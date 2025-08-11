"""
缓存监控器测试
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from rag_system.services.cache_monitor import (
    CacheMonitor, CacheCircuitBreaker, AlertLevel, HealthStatus,
    Alert, HealthCheck, default_alert_handler, console_alert_handler
)


class TestCacheMonitor:
    """缓存监控器测试类"""
    
    @pytest.fixture
    def cache_service(self):
        """模拟缓存服务"""
        service = AsyncMock()
        service.cache_enabled = True
        service.redis_client = AsyncMock()
        service.redis_client.set = AsyncMock()
        service.redis_client.get = AsyncMock()
        service.redis_client.delete = AsyncMock()
        service.redis_client.ping = AsyncMock()
        return service
    
    @pytest.fixture
    def monitor_config(self):
        """监控配置"""
        return {
            'check_interval': 1,
            'alert_thresholds': {
                'error_rate': 0.1,
                'response_time': 500,
                'memory_usage': 0.8,
                'connection_failures': 3
            }
        }
    
    @pytest.fixture
    def cache_monitor(self, cache_service, monitor_config):
        """缓存监控器fixture"""
        return CacheMonitor(cache_service, monitor_config)
    
    def test_cache_monitor_initialization(self, cache_service, monitor_config):
        """测试缓存监控器初始化"""
        monitor = CacheMonitor(cache_service, monitor_config)
        
        assert monitor.cache_service == cache_service
        assert monitor.config == monitor_config
        assert monitor.check_interval == 1
        assert monitor.is_monitoring is False
        assert monitor.monitor_task is None
        assert len(monitor.active_alerts) == 0
        assert len(monitor.alert_handlers) == 0
    
    @pytest.mark.asyncio
    async def test_start_and_stop_monitoring(self, cache_monitor):
        """测试启动和停止监控"""
        # 启动监控
        await cache_monitor.start_monitoring()
        
        assert cache_monitor.is_monitoring is True
        assert cache_monitor.monitor_task is not None
        
        # 停止监控
        await cache_monitor.stop_monitoring()
        
        assert cache_monitor.is_monitoring is False
        assert cache_monitor.monitor_task is None
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, cache_monitor):
        """测试健康检查成功"""
        # 设置模拟返回值 - 需要动态返回写入的值
        def mock_get(key):
            if key == "health_check_test":
                # 返回一个包含时间戳的值，模拟写入的值
                return f"test_{datetime.now().timestamp()}"
            return None
        
        cache_monitor.cache_service.redis_client.get.side_effect = mock_get
        
        # 执行健康检查
        health_check = await cache_monitor.health_check()
        
        assert isinstance(health_check, HealthCheck)
        assert health_check.component == "cache_service"
        assert health_check.status == HealthStatus.HEALTHY
        assert health_check.message == "缓存服务运行正常"
        assert health_check.response_time >= 0  # 模拟环境中可能为0
        assert health_check.metadata['redis_connected'] is True
        assert health_check.metadata['test_successful'] is True
    
    @pytest.mark.asyncio
    async def test_health_check_cache_disabled(self, cache_monitor):
        """测试缓存禁用时的健康检查"""
        cache_monitor.cache_service.cache_enabled = False
        
        health_check = await cache_monitor.health_check()
        
        assert health_check.status == HealthStatus.UNHEALTHY
        assert health_check.message == "缓存服务未启用"
        assert health_check.response_time == 0.0
    
    @pytest.mark.asyncio
    async def test_health_check_redis_failure(self, cache_monitor):
        """测试Redis连接失败时的健康检查"""
        # 模拟Redis操作失败
        cache_monitor.cache_service.redis_client.set.side_effect = Exception("Redis连接失败")
        
        health_check = await cache_monitor.health_check()
        
        assert health_check.status == HealthStatus.UNHEALTHY
        assert "缓存健康检查失败" in health_check.message
        assert health_check.metadata['redis_connected'] is False
        assert 'error' in health_check.metadata
        
        # 验证错误统计被更新
        assert cache_monitor.error_stats['connection_failures'] == 1
    
    def test_get_error_stats(self, cache_monitor):
        """测试获取错误统计"""
        # 设置一些错误统计
        cache_monitor.error_stats['connection_failures'] = 5
        cache_monitor.error_stats['total_errors'] = 10
        cache_monitor.performance_stats['total_requests'] = 100
        
        stats = cache_monitor.get_error_stats()
        
        assert stats['connection_failures'] == 5
        assert stats['total_errors'] == 10
        assert stats['error_rate'] == 0.1  # 10/100
        assert 'performance_stats' in stats


class TestCacheCircuitBreaker:
    """缓存熔断器测试类"""
    
    @pytest.fixture
    def circuit_breaker(self):
        """熔断器fixture"""
        return CacheCircuitBreaker(failure_threshold=3, recovery_timeout=5)
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_success(self, circuit_breaker):
        """测试熔断器成功调用"""
        async def success_func():
            return "success"
        
        result = await circuit_breaker.call(success_func)
        
        assert result == "success"
        assert circuit_breaker.state == "CLOSED"
        assert circuit_breaker.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_failure(self, circuit_breaker):
        """测试熔断器失败处理"""
        async def failure_func():
            raise Exception("测试失败")
        
        # 连续失败直到熔断器开启
        for i in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failure_func)
        
        assert circuit_breaker.state == "OPEN"
        assert circuit_breaker.failure_count == 3
        
        # 熔断器开启后应该拒绝请求
        with pytest.raises(Exception, match="缓存熔断器开启"):
            await circuit_breaker.call(failure_func)
    
    def test_circuit_breaker_get_state(self, circuit_breaker):
        """测试获取熔断器状态"""
        state = circuit_breaker.get_state()
        
        assert state['state'] == "CLOSED"
        assert state['failure_count'] == 0
        assert state['failure_threshold'] == 3
        assert state['recovery_timeout'] == 5
        assert state['last_failure_time'] is None


class TestAlertHandlers:
    """告警处理器测试类"""
    
    def test_default_alert_handler(self):
        """测试默认告警处理器"""
        alert = Alert(
            AlertLevel.WARNING,
            "测试告警",
            "测试消息",
            "test_component"
        )
        
        # 应该不抛出异常
        default_alert_handler(alert)
    
    def test_console_alert_handler(self, capsys):
        """测试控制台告警处理器"""
        alert = Alert(
            AlertLevel.ERROR,
            "测试告警",
            "测试消息",
            "test_component",
            metadata={'key': 'value'}
        )
        
        console_alert_handler(alert)
        
        captured = capsys.readouterr()
        assert "🚨" in captured.out
        assert "ERROR" in captured.out
        assert "测试告警" in captured.out
        assert "测试消息" in captured.out
        assert "test_component" in captured.out


if __name__ == "__main__":
    pytest.main([__file__])