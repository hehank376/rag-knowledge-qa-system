"""
缓存监控和告警模块
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class Alert:
    """告警信息"""
    level: AlertLevel
    title: str
    message: str
    component: str
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthCheck:
    """健康检查结果"""
    component: str
    status: HealthStatus
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    response_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class CacheMonitor:
    """缓存监控器"""
    
    def __init__(self, cache_service, config: Optional[Dict[str, Any]] = None):
        """初始化缓存监控器"""
        self.cache_service = cache_service
        self.config = config or {}
        
        # 监控配置
        self.check_interval = self.config.get('check_interval', 30)
        self.alert_thresholds = self.config.get('alert_thresholds', {
            'error_rate': 0.1,
            'response_time': 1000,
            'memory_usage': 0.9,
            'connection_failures': 5
        })
        
        # 监控状态
        self.is_monitoring = False
        self.monitor_task = None
        self.last_health_check = None
        
        # 告警管理
        self.active_alerts = []
        self.alert_handlers = []
        self.max_alerts = 100
        
        # 错误统计
        self.error_stats = {
            'connection_failures': 0,
            'read_errors': 0,
            'write_errors': 0,
            'timeout_errors': 0,
            'total_errors': 0
        }
        
        # 性能统计
        self.performance_stats = {
            'avg_response_time': 0.0,
            'max_response_time': 0.0,
            'min_response_time': float('inf'),
            'total_requests': 0,
            'successful_requests': 0
        }
        
        logger.info("缓存监控器初始化完成")
    
    async def start_monitoring(self) -> None:
        """启动监控"""
        if self.is_monitoring:
            logger.warning("缓存监控已经在运行")
            return
        
        self.is_monitoring = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        logger.info("缓存监控已启动")
    
    async def stop_monitoring(self) -> None:
        """停止监控"""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
            self.monitor_task = None
        
        logger.info("缓存监控已停止")
    
    async def health_check(self) -> HealthCheck:
        """执行健康检查"""
        start_time = datetime.now()
        
        try:
            # 检查缓存服务基本功能
            if not self.cache_service.cache_enabled:
                return HealthCheck(
                    component="cache_service",
                    status=HealthStatus.UNHEALTHY,
                    message="缓存服务未启用",
                    response_time=0.0
                )
            
            # 检查Redis连接
            test_key = "health_check_test"
            test_value = f"test_{datetime.now().timestamp()}"
            
            # 测试写入
            await self.cache_service.redis_client.set(test_key, test_value, ex=10)
            
            # 测试读取
            retrieved_value = await self.cache_service.redis_client.get(test_key)
            
            # 清理测试数据
            await self.cache_service.redis_client.delete(test_key)
            
            # 计算响应时间
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # 判断健康状态
            status = HealthStatus.HEALTHY
            message = "缓存服务运行正常"
            
            if response_time > self.alert_thresholds['response_time']:
                status = HealthStatus.DEGRADED
                message = f"缓存响应时间过长: {response_time:.2f}ms"
            
            # 检查读写是否成功（允许一定的时间差异）
            test_successful = retrieved_value is not None and str(retrieved_value).startswith("test_")
            if not test_successful:
                status = HealthStatus.UNHEALTHY
                message = "缓存读写测试失败"
            
            # 更新性能统计
            self._update_performance_stats(response_time, True)
            
            health_check = HealthCheck(
                component="cache_service",
                status=status,
                message=message,
                response_time=response_time,
                metadata={
                    'redis_connected': True,
                    'test_successful': test_successful
                }
            )
            
            self.last_health_check = health_check
            return health_check
            
        except Exception as e:
            # 更新错误统计
            self._update_error_stats('connection_failures')
            self._update_performance_stats(0, False)
            
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            health_check = HealthCheck(
                component="cache_service",
                status=HealthStatus.UNHEALTHY,
                message=f"缓存健康检查失败: {str(e)}",
                response_time=response_time,
                metadata={
                    'redis_connected': False,
                    'error': str(e)
                }
            )
            
            self.last_health_check = health_check
            return health_check
    
    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计"""
        total_requests = self.performance_stats['total_requests']
        error_rate = 0.0
        
        if total_requests > 0:
            error_rate = self.error_stats['total_errors'] / total_requests
        
        return {
            **self.error_stats,
            'error_rate': error_rate,
            'performance_stats': self.performance_stats
        }
    
    def _update_error_stats(self, error_type: str) -> None:
        """更新错误统计"""
        if error_type in self.error_stats:
            self.error_stats[error_type] += 1
    
    def _update_performance_stats(self, response_time: float, success: bool) -> None:
        """更新性能统计"""
        self.performance_stats['total_requests'] += 1
        
        if success:
            self.performance_stats['successful_requests'] += 1
    
    async def _monitoring_loop(self) -> None:
        """监控循环"""
        while self.is_monitoring:
            try:
                await self.health_check()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"监控循环错误: {e}")
                await asyncio.sleep(self.check_interval)


class CacheCircuitBreaker:
    """缓存熔断器"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        """初始化熔断器"""
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"
    
    async def call(self, func, *args, **kwargs):
        """通过熔断器调用函数"""
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
            else:
                raise Exception("缓存熔断器开启，拒绝请求")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """是否应该尝试重置"""
        if self.last_failure_time is None:
            return False
        return (datetime.now() - self.last_failure_time).total_seconds() > self.recovery_timeout
    
    def _on_success(self) -> None:
        """成功时的处理"""
        self.failure_count = 0
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
    
    def _on_failure(self) -> None:
        """失败时的处理"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
    
    def get_state(self) -> Dict[str, Any]:
        """获取熔断器状态"""
        return {
            'state': self.state,
            'failure_count': self.failure_count,
            'failure_threshold': self.failure_threshold,
            'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None,
            'recovery_timeout': self.recovery_timeout
        }


def default_alert_handler(alert: Alert) -> None:
    """默认告警处理器"""
    logger.warning(f"[{alert.level.value.upper()}] {alert.title}: {alert.message}")


def console_alert_handler(alert: Alert) -> None:
    """控制台告警处理器"""
    print(f"🚨 [{alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] "
          f"[{alert.level.value.upper()}] {alert.component}: {alert.title}")
    print(f"   {alert.message}")


def create_cache_monitor(cache_service, config: Optional[Dict[str, Any]] = None) -> CacheMonitor:
    """创建缓存监控器"""
    return CacheMonitor(cache_service, config)