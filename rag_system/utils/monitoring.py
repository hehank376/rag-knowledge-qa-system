"""
性能监控和健康检查模块
实现任务9.2：日志和监控功能
"""
import time
import psutil
import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import threading
import logging

from .exceptions import RAGSystemError, ErrorCode


@dataclass
class HealthStatus:
    """健康状态数据类"""
    service: str
    status: str  # healthy, degraded, unhealthy
    timestamp: datetime
    response_time: Optional[float] = None
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    request_count: int
    error_count: int
    avg_response_time: float
    active_connections: int


@dataclass
class ServiceMetrics:
    """服务指标数据类"""
    service_name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    last_request_time: Optional[datetime] = None


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.request_times = deque(maxlen=max_history)
        self.error_counts = defaultdict(int)
        self.service_metrics = defaultdict(lambda: {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'response_times': deque(maxlen=100),
            'last_request_time': None
        })
        self.start_time = datetime.utcnow()
        self._lock = threading.Lock()
    
    def record_request(
        self, 
        service: str, 
        response_time: float, 
        success: bool = True,
        error_type: Optional[str] = None
    ):
        """记录请求指标"""
        with self._lock:
            current_time = datetime.utcnow()
            
            # 记录全局指标
            self.request_times.append((current_time, response_time))
            
            # 记录服务指标
            metrics = self.service_metrics[service]
            metrics['total_requests'] += 1
            metrics['response_times'].append(response_time)
            metrics['last_request_time'] = current_time
            
            if success:
                metrics['successful_requests'] += 1
            else:
                metrics['failed_requests'] += 1
                if error_type:
                    self.error_counts[error_type] += 1
    
    def get_system_metrics(self) -> PerformanceMetrics:
        """获取系统性能指标"""
        with self._lock:
            # CPU使用率
            cpu_usage = psutil.cpu_percent(interval=0.1)
            
            # 内存使用率
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            
            # 磁盘使用率
            disk = psutil.disk_usage('/')
            disk_usage = (disk.used / disk.total) * 100
            
            # 请求统计
            recent_requests = [
                (ts, rt) for ts, rt in self.request_times 
                if ts > datetime.utcnow() - timedelta(minutes=5)
            ]
            
            request_count = len(recent_requests)
            avg_response_time = (
                sum(rt for _, rt in recent_requests) / request_count
                if request_count > 0 else 0.0
            )
            
            # 错误统计
            error_count = sum(self.error_counts.values())
            
            return PerformanceMetrics(
                timestamp=datetime.utcnow(),
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                disk_usage=disk_usage,
                request_count=request_count,
                error_count=error_count,
                avg_response_time=avg_response_time,
                active_connections=0  # 可以通过其他方式获取
            )
    
    def get_service_metrics(self, service: str) -> ServiceMetrics:
        """获取特定服务的指标"""
        with self._lock:
            metrics = self.service_metrics[service]
            response_times = list(metrics['response_times'])
            
            return ServiceMetrics(
                service_name=service,
                total_requests=metrics['total_requests'],
                successful_requests=metrics['successful_requests'],
                failed_requests=metrics['failed_requests'],
                avg_response_time=(
                    sum(response_times) / len(response_times)
                    if response_times else 0.0
                ),
                min_response_time=min(response_times) if response_times else 0.0,
                max_response_time=max(response_times) if response_times else 0.0,
                last_request_time=metrics['last_request_time']
            )
    
    def get_all_service_metrics(self) -> Dict[str, ServiceMetrics]:
        """获取所有服务的指标"""
        return {
            service: self.get_service_metrics(service)
            for service in self.service_metrics.keys()
        }
    
    def reset_metrics(self):
        """重置指标"""
        with self._lock:
            self.request_times.clear()
            self.error_counts.clear()
            self.service_metrics.clear()
            self.start_time = datetime.utcnow()


class HealthChecker:
    """健康检查器"""
    
    def __init__(self):
        self.checks: Dict[str, Callable] = {}
        self.logger = logging.getLogger(__name__)
    
    def register_check(self, name: str, check_func: Callable):
        """注册健康检查函数"""
        self.checks[name] = check_func
    
    async def check_health(self, service: str) -> HealthStatus:
        """执行单个服务的健康检查"""
        if service not in self.checks:
            return HealthStatus(
                service=service,
                status="unknown",
                timestamp=datetime.utcnow(),
                error_message=f"No health check registered for {service}"
            )
        
        start_time = time.time()
        try:
            check_func = self.checks[service]
            
            # 支持同步和异步检查函数
            if asyncio.iscoroutinefunction(check_func):
                result = await check_func()
            else:
                result = check_func()
            
            response_time = time.time() - start_time
            
            if isinstance(result, dict):
                return HealthStatus(
                    service=service,
                    status=result.get('status', 'healthy'),
                    timestamp=datetime.utcnow(),
                    response_time=response_time,
                    details=result.get('details')
                )
            else:
                return HealthStatus(
                    service=service,
                    status='healthy' if result else 'unhealthy',
                    timestamp=datetime.utcnow(),
                    response_time=response_time
                )
                
        except Exception as e:
            response_time = time.time() - start_time
            self.logger.error(f"Health check failed for {service}: {str(e)}")
            
            return HealthStatus(
                service=service,
                status="unhealthy",
                timestamp=datetime.utcnow(),
                response_time=response_time,
                error_message=str(e)
            )
    
    async def check_all_health(self) -> Dict[str, HealthStatus]:
        """执行所有服务的健康检查"""
        results = {}
        
        for service in self.checks.keys():
            results[service] = await self.check_health(service)
        
        return results
    
    def get_overall_status(self, health_results: Dict[str, HealthStatus]) -> str:
        """获取整体健康状态"""
        if not health_results:
            return "unknown"
        
        statuses = [result.status for result in health_results.values()]
        
        if all(status == "healthy" for status in statuses):
            return "healthy"
        elif any(status == "unhealthy" for status in statuses):
            return "unhealthy"
        else:
            return "degraded"


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.logger = logging.getLogger(__name__)
        self.thresholds = {
            'cpu_usage': 80.0,
            'memory_usage': 85.0,
            'disk_usage': 90.0,
            'avg_response_time': 5.0,
            'error_rate': 0.05
        }
        self.alerts = deque(maxlen=100)
    
    def set_threshold(self, metric: str, value: float):
        """设置性能阈值"""
        self.thresholds[metric] = value
    
    def check_thresholds(self, metrics: PerformanceMetrics) -> List[Dict[str, Any]]:
        """检查性能阈值"""
        alerts = []
        
        # CPU使用率检查
        if metrics.cpu_usage > self.thresholds['cpu_usage']:
            alerts.append({
                'type': 'cpu_high',
                'message': f'CPU使用率过高: {metrics.cpu_usage:.1f}%',
                'value': metrics.cpu_usage,
                'threshold': self.thresholds['cpu_usage'],
                'severity': 'warning'
            })
        
        # 内存使用率检查
        if metrics.memory_usage > self.thresholds['memory_usage']:
            alerts.append({
                'type': 'memory_high',
                'message': f'内存使用率过高: {metrics.memory_usage:.1f}%',
                'value': metrics.memory_usage,
                'threshold': self.thresholds['memory_usage'],
                'severity': 'warning'
            })
        
        # 磁盘使用率检查
        if metrics.disk_usage > self.thresholds['disk_usage']:
            alerts.append({
                'type': 'disk_high',
                'message': f'磁盘使用率过高: {metrics.disk_usage:.1f}%',
                'value': metrics.disk_usage,
                'threshold': self.thresholds['disk_usage'],
                'severity': 'critical'
            })
        
        # 响应时间检查
        if metrics.avg_response_time > self.thresholds['avg_response_time']:
            alerts.append({
                'type': 'response_time_high',
                'message': f'平均响应时间过长: {metrics.avg_response_time:.2f}s',
                'value': metrics.avg_response_time,
                'threshold': self.thresholds['avg_response_time'],
                'severity': 'warning'
            })
        
        # 错误率检查
        if metrics.request_count > 0:
            error_rate = metrics.error_count / metrics.request_count
            if error_rate > self.thresholds['error_rate']:
                alerts.append({
                    'type': 'error_rate_high',
                    'message': f'错误率过高: {error_rate:.2%}',
                    'value': error_rate,
                    'threshold': self.thresholds['error_rate'],
                    'severity': 'critical'
                })
        
        # 记录告警
        for alert in alerts:
            alert['timestamp'] = datetime.utcnow()
            self.alerts.append(alert)
            self.logger.warning(f"Performance alert: {alert['message']}")
        
        return alerts
    
    def get_recent_alerts(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """获取最近的告警"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        return [
            alert for alert in self.alerts
            if alert['timestamp'] > cutoff_time
        ]


def performance_monitor_middleware(metrics_collector: MetricsCollector):
    """性能监控中间件工厂函数"""
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    
    class PerformanceMiddleware(BaseHTTPMiddleware):
        def __init__(self, app):
            super().__init__(app)
            self.metrics_collector = metrics_collector
        
        async def dispatch(self, request: Request, call_next):
            start_time = time.time()
            
            try:
                response = await call_next(request)
                response_time = time.time() - start_time
                
                # 记录成功请求
                self.metrics_collector.record_request(
                    service=request.url.path,
                    response_time=response_time,
                    success=response.status_code < 400
                )
                
                # 添加性能头
                response.headers["X-Response-Time"] = f"{response_time:.3f}s"
                
                return response
                
            except Exception as e:
                response_time = time.time() - start_time
                
                # 记录失败请求
                self.metrics_collector.record_request(
                    service=request.url.path,
                    response_time=response_time,
                    success=False,
                    error_type=type(e).__name__
                )
                
                raise
    
    return PerformanceMiddleware


# 全局实例
global_metrics_collector = MetricsCollector()
global_health_checker = HealthChecker()
global_performance_monitor = PerformanceMonitor(global_metrics_collector)