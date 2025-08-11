#!/usr/bin/env python3
"""
错误监控和指标收集
实现任务6.1：错误的分类和优先级管理
"""
import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
import json

from .error_handler import ErrorContext, ErrorSeverity, ErrorCategory
from .exceptions import RAGSystemException
from .logging_config import get_simple_logger as get_logger

logger = get_logger(__name__)


@dataclass
class ErrorMetric:
    """错误指标"""
    error_code: str
    error_message: str
    severity: ErrorSeverity
    category: ErrorCategory
    component: str
    operation: str
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolution_time: Optional[datetime] = None


@dataclass
class ErrorStatistics:
    """错误统计信息"""
    total_errors: int = 0
    error_by_severity: Dict[ErrorSeverity, int] = field(default_factory=lambda: defaultdict(int))
    error_by_category: Dict[ErrorCategory, int] = field(default_factory=lambda: defaultdict(int))
    error_by_component: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    error_by_code: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    error_rate_per_minute: float = 0.0
    average_resolution_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "total_errors": self.total_errors,
            "error_by_severity": {k.value: v for k, v in self.error_by_severity.items()},
            "error_by_category": {k.value: v for k, v in self.error_by_category.items()},
            "error_by_component": dict(self.error_by_component),
            "error_by_code": dict(self.error_by_code),
            "error_rate_per_minute": self.error_rate_per_minute,
            "average_resolution_time": self.average_resolution_time
        }


class AlertLevel(str, Enum):
    """告警级别"""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class Alert:
    """告警信息"""
    level: AlertLevel
    title: str
    message: str
    component: str
    error_code: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "level": self.level.value,
            "title": self.title,
            "message": self.message,
            "component": self.component,
            "error_code": self.error_code,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


class ErrorMonitor:
    """错误监控器"""
    
    def __init__(self, max_metrics_history: int = 10000, alert_window_minutes: int = 5):
        self.max_metrics_history = max_metrics_history
        self.alert_window_minutes = alert_window_minutes
        
        # 错误指标存储
        self.error_metrics: deque = deque(maxlen=max_metrics_history)
        self.error_statistics = ErrorStatistics()
        
        # 告警相关
        self.alert_handlers: List[Callable] = []
        self.alert_thresholds: Dict[str, Dict[str, Any]] = {}
        self.recent_alerts: deque = deque(maxlen=1000)
        
        # 错误模式检测
        self.error_patterns: Dict[str, List[datetime]] = defaultdict(list)
        
        # 初始化默认告警阈值
        self._setup_default_thresholds()
    
    def _setup_default_thresholds(self) -> None:
        """设置默认告警阈值"""
        self.alert_thresholds = {
            "error_rate": {
                "warning": 10,    # 每分钟10个错误
                "critical": 50    # 每分钟50个错误
            },
            "critical_errors": {
                "warning": 1,     # 1个严重错误
                "critical": 5     # 5个严重错误
            },
            "component_failure": {
                "warning": 5,     # 组件5个错误
                "critical": 20    # 组件20个错误
            },
            "error_pattern": {
                "warning": 3,     # 相同错误3次
                "critical": 10    # 相同错误10次
            }
        }
    
    async def record_error(
        self,
        error: Exception,
        context: ErrorContext,
        error_info: Dict[str, Any]
    ) -> None:
        """记录错误指标"""
        try:
            # 创建错误指标
            metric = ErrorMetric(
                error_code=error_info.get('error_code', 'UNKNOWN_ERROR'),
                error_message=error_info.get('message', str(error)),
                severity=error_info.get('severity', ErrorSeverity.MEDIUM),
                category=error_info.get('category', ErrorCategory.SYSTEM),
                component=context.component or 'unknown',
                operation=context.operation or 'unknown',
                timestamp=context.timestamp,
                context=context.to_dict()
            )
            
            # 存储指标
            self.error_metrics.append(metric)
            
            # 更新统计信息
            await self._update_statistics(metric)
            
            # 检查告警条件
            await self._check_alert_conditions(metric)
            
            # 检测错误模式
            await self._detect_error_patterns(metric)
            
            logger.debug(f"错误指标已记录: {metric.error_code}")
            
        except Exception as monitor_error:
            logger.error(f"错误监控记录失败: {monitor_error}")
    
    async def _update_statistics(self, metric: ErrorMetric) -> None:
        """更新错误统计信息"""
        self.error_statistics.total_errors += 1
        self.error_statistics.error_by_severity[metric.severity] += 1
        self.error_statistics.error_by_category[metric.category] += 1
        self.error_statistics.error_by_component[metric.component] += 1
        self.error_statistics.error_by_code[metric.error_code] += 1
        
        # 计算错误率（每分钟）
        now = datetime.now()
        one_minute_ago = now - timedelta(minutes=1)
        recent_errors = [m for m in self.error_metrics if m.timestamp >= one_minute_ago]
        self.error_statistics.error_rate_per_minute = len(recent_errors)
        
        # 计算平均解决时间
        resolved_metrics = [m for m in self.error_metrics if m.resolved and m.resolution_time]
        if resolved_metrics:
            total_resolution_time = sum(
                (m.resolution_time - m.timestamp).total_seconds()
                for m in resolved_metrics
            )
            self.error_statistics.average_resolution_time = total_resolution_time / len(resolved_metrics)
    
    async def _check_alert_conditions(self, metric: ErrorMetric) -> None:
        """检查告警条件"""
        alerts = []
        
        # 检查错误率告警
        if self.error_statistics.error_rate_per_minute >= self.alert_thresholds["error_rate"]["critical"]:
            alerts.append(Alert(
                level=AlertLevel.CRITICAL,
                title="错误率过高",
                message=f"错误率达到 {self.error_statistics.error_rate_per_minute} 错误/分钟",
                component="system",
                error_code="HIGH_ERROR_RATE"
            ))
        elif self.error_statistics.error_rate_per_minute >= self.alert_thresholds["error_rate"]["warning"]:
            alerts.append(Alert(
                level=AlertLevel.WARNING,
                title="错误率告警",
                message=f"错误率达到 {self.error_statistics.error_rate_per_minute} 错误/分钟",
                component="system",
                error_code="ELEVATED_ERROR_RATE"
            ))
        
        # 检查严重错误告警
        if metric.severity == ErrorSeverity.CRITICAL:
            critical_count = self.error_statistics.error_by_severity[ErrorSeverity.CRITICAL]
            if critical_count >= self.alert_thresholds["critical_errors"]["critical"]:
                alerts.append(Alert(
                    level=AlertLevel.CRITICAL,
                    title="严重错误频发",
                    message=f"严重错误数量: {critical_count}",
                    component=metric.component,
                    error_code=metric.error_code
                ))
            elif critical_count >= self.alert_thresholds["critical_errors"]["warning"]:
                alerts.append(Alert(
                    level=AlertLevel.WARNING,
                    title="严重错误告警",
                    message=f"检测到严重错误: {metric.error_message}",
                    component=metric.component,
                    error_code=metric.error_code
                ))
        
        # 检查组件故障告警
        component_errors = self.error_statistics.error_by_component[metric.component]
        if component_errors >= self.alert_thresholds["component_failure"]["critical"]:
            alerts.append(Alert(
                level=AlertLevel.CRITICAL,
                title="组件故障",
                message=f"组件 {metric.component} 错误数量: {component_errors}",
                component=metric.component,
                error_code="COMPONENT_FAILURE"
            ))
        elif component_errors >= self.alert_thresholds["component_failure"]["warning"]:
            alerts.append(Alert(
                level=AlertLevel.WARNING,
                title="组件异常",
                message=f"组件 {metric.component} 错误数量: {component_errors}",
                component=metric.component,
                error_code="COMPONENT_ANOMALY"
            ))
        
        # 发送告警
        for alert in alerts:
            await self._send_alert(alert)
    
    async def _detect_error_patterns(self, metric: ErrorMetric) -> None:
        """检测错误模式"""
        pattern_key = f"{metric.error_code}:{metric.component}"
        now = datetime.now()
        
        # 记录错误时间
        self.error_patterns[pattern_key].append(now)
        
        # 清理旧的错误记录（只保留最近的时间窗口）
        window_start = now - timedelta(minutes=self.alert_window_minutes)
        self.error_patterns[pattern_key] = [
            timestamp for timestamp in self.error_patterns[pattern_key]
            if timestamp >= window_start
        ]
        
        # 检查错误模式
        pattern_count = len(self.error_patterns[pattern_key])
        if pattern_count >= self.alert_thresholds["error_pattern"]["critical"]:
            await self._send_alert(Alert(
                level=AlertLevel.CRITICAL,
                title="错误模式检测",
                message=f"检测到错误模式: {metric.error_code} 在 {self.alert_window_minutes} 分钟内出现 {pattern_count} 次",
                component=metric.component,
                error_code="ERROR_PATTERN_CRITICAL",
                metadata={"pattern_count": pattern_count, "window_minutes": self.alert_window_minutes}
            ))
        elif pattern_count >= self.alert_thresholds["error_pattern"]["warning"]:
            await self._send_alert(Alert(
                level=AlertLevel.WARNING,
                title="错误模式告警",
                message=f"错误 {metric.error_code} 在短时间内重复出现 {pattern_count} 次",
                component=metric.component,
                error_code="ERROR_PATTERN_WARNING",
                metadata={"pattern_count": pattern_count, "window_minutes": self.alert_window_minutes}
            ))
    
    async def _send_alert(self, alert: Alert) -> None:
        """发送告警"""
        try:
            # 避免重复告警
            if self._is_duplicate_alert(alert):
                return
            
            # 记录告警
            self.recent_alerts.append(alert)
            
            # 记录告警日志
            logger.warning(f"告警触发: {alert.title} - {alert.message}")
            
            # 调用告警处理器
            for handler in self.alert_handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(alert)
                    else:
                        handler(alert)
                except Exception as handler_error:
                    logger.error(f"告警处理器执行失败: {handler_error}")
        
        except Exception as alert_error:
            logger.error(f"发送告警失败: {alert_error}")
    
    def _is_duplicate_alert(self, alert: Alert) -> bool:
        """检查是否为重复告警"""
        # 检查最近5分钟内是否有相同的告警
        five_minutes_ago = datetime.now() - timedelta(minutes=5)
        recent_similar_alerts = [
            a for a in self.recent_alerts
            if (a.timestamp >= five_minutes_ago and
                a.error_code == alert.error_code and
                a.component == alert.component and
                a.level == alert.level)
        ]
        
        return len(recent_similar_alerts) > 0
    
    def register_alert_handler(self, handler: Callable) -> None:
        """注册告警处理器"""
        self.alert_handlers.append(handler)
        logger.info("告警处理器已注册")
    
    def set_alert_threshold(self, threshold_type: str, level: str, value: Any) -> None:
        """设置告警阈值"""
        if threshold_type not in self.alert_thresholds:
            self.alert_thresholds[threshold_type] = {}
        
        self.alert_thresholds[threshold_type][level] = value
        logger.info(f"告警阈值已设置: {threshold_type}.{level} = {value}")
    
    def get_statistics(self, time_range_minutes: Optional[int] = None) -> ErrorStatistics:
        """获取错误统计信息"""
        if time_range_minutes is None:
            return self.error_statistics
        
        # 计算指定时间范围内的统计信息
        cutoff_time = datetime.now() - timedelta(minutes=time_range_minutes)
        filtered_metrics = [m for m in self.error_metrics if m.timestamp >= cutoff_time]
        
        stats = ErrorStatistics()
        stats.total_errors = len(filtered_metrics)
        
        for metric in filtered_metrics:
            stats.error_by_severity[metric.severity] += 1
            stats.error_by_category[metric.category] += 1
            stats.error_by_component[metric.component] += 1
            stats.error_by_code[metric.error_code] += 1
        
        # 计算错误率
        stats.error_rate_per_minute = stats.total_errors / time_range_minutes if time_range_minutes > 0 else 0
        
        return stats
    
    def get_recent_alerts(self, limit: int = 100) -> List[Alert]:
        """获取最近的告警"""
        return list(self.recent_alerts)[-limit:]
    
    def get_error_trends(self, hours: int = 24) -> Dict[str, Any]:
        """获取错误趋势"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        filtered_metrics = [m for m in self.error_metrics if m.timestamp >= cutoff_time]
        
        # 按小时分组统计
        hourly_stats = defaultdict(int)
        for metric in filtered_metrics:
            hour_key = metric.timestamp.strftime("%Y-%m-%d %H:00")
            hourly_stats[hour_key] += 1
        
        return {
            "time_range_hours": hours,
            "total_errors": len(filtered_metrics),
            "hourly_distribution": dict(hourly_stats),
            "peak_hour": max(hourly_stats.items(), key=lambda x: x[1]) if hourly_stats else None
        }
    
    def mark_error_resolved(self, error_code: str, component: str, resolution_time: Optional[datetime] = None) -> None:
        """标记错误已解决"""
        if resolution_time is None:
            resolution_time = datetime.now()
        
        # 查找并标记相关错误为已解决
        for metric in reversed(self.error_metrics):
            if (metric.error_code == error_code and 
                metric.component == component and 
                not metric.resolved):
                metric.resolved = True
                metric.resolution_time = resolution_time
                logger.info(f"错误已标记为解决: {error_code} in {component}")
                break
    
    def export_metrics(self, format: str = "json") -> str:
        """导出错误指标"""
        if format.lower() == "json":
            metrics_data = {
                "statistics": self.error_statistics.to_dict(),
                "recent_alerts": [alert.to_dict() for alert in self.recent_alerts],
                "metrics_count": len(self.error_metrics),
                "export_time": datetime.now().isoformat()
            }
            return json.dumps(metrics_data, indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"不支持的导出格式: {format}")
    
    def clear_old_metrics(self, days: int = 7) -> int:
        """清理旧的错误指标"""
        cutoff_time = datetime.now() - timedelta(days=days)
        original_count = len(self.error_metrics)
        
        # 过滤掉旧的指标
        self.error_metrics = deque(
            [m for m in self.error_metrics if m.timestamp >= cutoff_time],
            maxlen=self.max_metrics_history
        )
        
        cleared_count = original_count - len(self.error_metrics)
        logger.info(f"清理了 {cleared_count} 个旧的错误指标")
        return cleared_count


# 全局错误监控器实例
global_error_monitor = ErrorMonitor()


# 便捷函数
async def record_error_metric(
    error: Exception,
    context: ErrorContext,
    error_info: Dict[str, Any]
) -> None:
    """记录错误指标的便捷函数"""
    await global_error_monitor.record_error(error, context, error_info)


def register_alert_handler(handler: Callable) -> None:
    """注册告警处理器的便捷函数"""
    global_error_monitor.register_alert_handler(handler)


def get_error_statistics(time_range_minutes: Optional[int] = None) -> ErrorStatistics:
    """获取错误统计的便捷函数"""
    return global_error_monitor.get_statistics(time_range_minutes)


# 示例告警处理器
async def console_alert_handler(alert: Alert) -> None:
    """控制台告警处理器"""
    print(f"[{alert.level.value}] {alert.title}: {alert.message}")


def email_alert_handler(alert: Alert) -> None:
    """邮件告警处理器（示例）"""
    # 这里可以集成邮件发送功能
    logger.info(f"邮件告警: {alert.title} - {alert.message}")


# 默认注册控制台告警处理器
register_alert_handler(console_alert_handler)