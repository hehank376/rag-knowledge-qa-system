#!/usr/bin/env python3
"""
轻量级检索性能监控和指标收集
实现任务6.2：检索性能监控和指标收集
对应需求13：性能和监控（验收标准13.1-13.7）
不包含系统资源监控，避免阻塞问题
"""
import asyncio
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
import json
import statistics
from threading import Lock

from .logging_config import get_simple_logger as get_logger

logger = get_logger(__name__)


class OperationType(str, Enum):
    """操作类型枚举"""
    SEARCH = "search"
    CACHE_READ = "cache_read"
    CACHE_WRITE = "cache_write"
    RERANKING = "reranking"
    FULL_RETRIEVAL = "full_retrieval"


class SearchMode(str, Enum):
    """搜索模式枚举"""
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"


@dataclass
class PerformanceMetric:
    """性能指标数据模型"""
    query_id: str
    operation_type: OperationType
    search_mode: Optional[SearchMode] = None
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    success: bool = True
    result_count: int = 0
    error_details: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def complete(self, success: bool = True, result_count: int = 0, error_details: Optional[str] = None):
        """完成性能指标记录"""
        self.end_time = datetime.now()
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.success = success
        self.result_count = result_count
        self.error_details = error_details


@dataclass
class ResponseTimeStats:
    """响应时间统计（需求13.1）"""
    average_ms: float = 0.0
    median_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    min_ms: float = 0.0
    max_ms: float = 0.0
    total_queries: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "average_ms": self.average_ms,
            "median_ms": self.median_ms,
            "p95_ms": self.p95_ms,
            "p99_ms": self.p99_ms,
            "min_ms": self.min_ms,
            "max_ms": self.max_ms,
            "total_queries": self.total_queries
        }


@dataclass
class CacheStats:
    """缓存统计（需求13.2）"""
    hit_count: int = 0
    miss_count: int = 0
    hit_rate: float = 0.0
    average_hit_duration_ms: float = 0.0
    average_miss_duration_ms: float = 0.0
    
    def update_hit_rate(self):
        """更新缓存命中率"""
        total = self.hit_count + self.miss_count
        self.hit_rate = self.hit_count / total if total > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "hit_rate": self.hit_rate,
            "average_hit_duration_ms": self.average_hit_duration_ms,
            "average_miss_duration_ms": self.average_miss_duration_ms
        }


@dataclass
class RerankingStats:
    """重排序统计（需求13.3）"""
    total_operations: int = 0
    success_count: int = 0
    success_rate: float = 0.0
    average_duration_ms: float = 0.0
    average_documents_processed: float = 0.0
    
    def update_success_rate(self):
        """更新重排序成功率"""
        self.success_rate = self.success_count / self.total_operations if self.total_operations > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_operations": self.total_operations,
            "success_count": self.success_count,
            "success_rate": self.success_rate,
            "average_duration_ms": self.average_duration_ms,
            "average_documents_processed": self.average_documents_processed
        }


@dataclass
class SearchModeStats:
    """搜索模式统计（需求13.4）"""
    mode_usage: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    mode_performance: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    mode_success_rate: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    
    def get_usage_distribution(self) -> Dict[str, float]:
        """获取使用分布百分比"""
        total = sum(self.mode_usage.values())
        if total == 0:
            return {}
        return {mode: count / total for mode, count in self.mode_usage.items()}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode_usage": dict(self.mode_usage),
            "mode_performance": dict(self.mode_performance),
            "mode_success_rate": dict(self.mode_success_rate),
            "usage_distribution": self.get_usage_distribution()
        }


@dataclass
class SystemStabilityStats:
    """系统稳定性统计（需求13.5）"""
    cpu_usage_percent: float = 0.0
    memory_usage_percent: float = 0.0
    active_queries: int = 0
    error_rate: float = 0.0
    stability_score: float = 100.0  # 0-100分
    
    def calculate_stability_score(self):
        """计算稳定性评分"""
        # 基础分数100分
        score = 100.0
        
        # 错误率影响（每1%错误率扣5分）
        score -= self.error_rate * 5
        
        self.stability_score = max(0.0, min(100.0, score))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "cpu_usage_percent": self.cpu_usage_percent,
            "memory_usage_percent": self.memory_usage_percent,
            "active_queries": self.active_queries,
            "error_rate": self.error_rate,
            "stability_score": self.stability_score
        }


@dataclass
class ExceptionSummary:
    """异常摘要（需求13.7）"""
    total_exceptions: int = 0
    exception_types: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    recent_exceptions: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_exception(self, exception_type: str, details: Dict[str, Any]):
        """添加异常记录"""
        self.total_exceptions += 1
        self.exception_types[exception_type] += 1
        
        # 保留最近50个异常
        self.recent_exceptions.append({
            "type": exception_type,
            "timestamp": datetime.now().isoformat(),
            "details": details
        })
        
        if len(self.recent_exceptions) > 50:
            self.recent_exceptions.pop(0)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_exceptions": self.total_exceptions,
            "exception_types": dict(self.exception_types),
            "recent_exceptions": self.recent_exceptions
        }


@dataclass
class PerformanceReport:
    """性能报告（需求13.6）"""
    timestamp: datetime = field(default_factory=datetime.now)
    time_range_minutes: int = 60
    response_time_stats: ResponseTimeStats = field(default_factory=ResponseTimeStats)
    cache_stats: CacheStats = field(default_factory=CacheStats)
    reranking_stats: RerankingStats = field(default_factory=RerankingStats)
    search_mode_stats: SearchModeStats = field(default_factory=SearchModeStats)
    system_stability: SystemStabilityStats = field(default_factory=SystemStabilityStats)
    exception_summary: ExceptionSummary = field(default_factory=ExceptionSummary)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "time_range_minutes": self.time_range_minutes,
            "response_time_stats": self.response_time_stats.to_dict(),
            "cache_stats": self.cache_stats.to_dict(),
            "reranking_stats": self.reranking_stats.to_dict(),
            "search_mode_stats": self.search_mode_stats.to_dict(),
            "system_stability": self.system_stability.to_dict(),
            "exception_summary": self.exception_summary.to_dict()
        }


class LitePerformanceMonitor:
    """轻量级检索性能监控器（无系统资源监控）"""
    
    def __init__(self, max_metrics_history: int = 10000):
        self.max_metrics_history = max_metrics_history
        self.metrics_history: deque = deque(maxlen=max_metrics_history)
        self.active_metrics: Dict[str, PerformanceMetric] = {}
        
        # 统计数据
        self.response_times: deque = deque(maxlen=1000)  # 最近1000次查询的响应时间
        self.cache_stats = CacheStats()
        self.reranking_stats = RerankingStats()
        self.search_mode_stats = SearchModeStats()
        self.system_stability = SystemStabilityStats()
        self.exception_summary = ExceptionSummary()
        
        # 线程安全锁
        self._lock = Lock()
        
        logger.info("轻量级性能监控器已初始化")
    
    def start_operation(self, query_id: str, operation_type: OperationType, 
                       search_mode: Optional[SearchMode] = None, 
                       metadata: Optional[Dict[str, Any]] = None) -> str:
        """开始记录操作性能（需求13.1）"""
        with self._lock:
            metric = PerformanceMetric(
                query_id=query_id,
                operation_type=operation_type,
                search_mode=search_mode,
                metadata=metadata or {}
            )
            
            metric_key = f"{query_id}:{operation_type.value}"
            self.active_metrics[metric_key] = metric
            
            logger.debug(f"开始监控操作: {metric_key}")
            return metric_key
    
    def complete_operation(self, metric_key: str, success: bool = True, 
                          result_count: int = 0, error_details: Optional[str] = None):
        """完成操作记录（需求13.1）"""
        with self._lock:
            if metric_key not in self.active_metrics:
                logger.warning(f"未找到活跃指标: {metric_key}")
                return
            
            metric = self.active_metrics.pop(metric_key)
            metric.complete(success, result_count, error_details)
            
            # 存储到历史记录
            self.metrics_history.append(metric)
            
            # 更新统计数据
            self._update_statistics(metric)
            
            logger.debug(f"完成操作监控: {metric_key}, 耗时: {metric.duration_ms:.2f}ms")
    
    def record_cache_operation(self, hit: bool, duration_ms: float):
        """记录缓存操作（需求13.2）"""
        with self._lock:
            if hit:
                self.cache_stats.hit_count += 1
                # 更新平均命中时间
                if self.cache_stats.hit_count == 1:
                    self.cache_stats.average_hit_duration_ms = duration_ms
                else:
                    self.cache_stats.average_hit_duration_ms = (
                        (self.cache_stats.average_hit_duration_ms * (self.cache_stats.hit_count - 1) + duration_ms) 
                        / self.cache_stats.hit_count
                    )
            else:
                self.cache_stats.miss_count += 1
                # 更新平均未命中时间
                if self.cache_stats.miss_count == 1:
                    self.cache_stats.average_miss_duration_ms = duration_ms
                else:
                    self.cache_stats.average_miss_duration_ms = (
                        (self.cache_stats.average_miss_duration_ms * (self.cache_stats.miss_count - 1) + duration_ms)
                        / self.cache_stats.miss_count
                    )
            
            self.cache_stats.update_hit_rate()
            logger.debug(f"缓存操作记录: hit={hit}, duration={duration_ms:.2f}ms, hit_rate={self.cache_stats.hit_rate:.3f}")
    
    def record_reranking_operation(self, success: bool, duration_ms: float, document_count: int = 0):
        """记录重排序操作（需求13.3）"""
        with self._lock:
            self.reranking_stats.total_operations += 1
            
            if success:
                self.reranking_stats.success_count += 1
            
            # 更新平均耗时
            if self.reranking_stats.total_operations == 1:
                self.reranking_stats.average_duration_ms = duration_ms
                self.reranking_stats.average_documents_processed = document_count
            else:
                total = self.reranking_stats.total_operations
                self.reranking_stats.average_duration_ms = (
                    (self.reranking_stats.average_duration_ms * (total - 1) + duration_ms) / total
                )
                self.reranking_stats.average_documents_processed = (
                    (self.reranking_stats.average_documents_processed * (total - 1) + document_count) / total
                )
            
            self.reranking_stats.update_success_rate()
            logger.debug(f"重排序操作记录: success={success}, duration={duration_ms:.2f}ms, docs={document_count}")
    
    def record_search_mode_usage(self, mode: SearchMode, duration_ms: float, success: bool):
        """记录搜索模式使用情况（需求13.4）"""
        with self._lock:
            mode_str = mode.value
            self.search_mode_stats.mode_usage[mode_str] += 1
            
            # 更新平均性能
            current_count = self.search_mode_stats.mode_usage[mode_str]
            if current_count == 1:
                self.search_mode_stats.mode_performance[mode_str] = duration_ms
                self.search_mode_stats.mode_success_rate[mode_str] = 1.0 if success else 0.0
            else:
                # 更新平均耗时
                current_avg = self.search_mode_stats.mode_performance[mode_str]
                self.search_mode_stats.mode_performance[mode_str] = (
                    (current_avg * (current_count - 1) + duration_ms) / current_count
                )
                
                # 更新成功率
                current_success_rate = self.search_mode_stats.mode_success_rate[mode_str]
                success_count = current_success_rate * (current_count - 1) + (1 if success else 0)
                self.search_mode_stats.mode_success_rate[mode_str] = success_count / current_count
            
            logger.debug(f"搜索模式使用记录: mode={mode_str}, duration={duration_ms:.2f}ms, success={success}")
    
    def log_exception_details(self, exception: Exception, context: Dict[str, Any]):
        """记录异常详情（需求13.7）"""
        with self._lock:
            exception_details = {
                "message": str(exception),
                "type": exception.__class__.__name__,
                "context": context
            }
            
            self.exception_summary.add_exception(
                exception.__class__.__name__,
                exception_details
            )
            
            logger.error(f"异常记录: {exception.__class__.__name__}: {str(exception)}", extra=context)
    
    def get_detailed_performance_stats(self, time_range_minutes: int = 60) -> PerformanceReport:
        """获取详细性能统计（需求13.6）"""
        with self._lock:
            # 过滤指定时间范围内的指标
            cutoff_time = datetime.now() - timedelta(minutes=time_range_minutes)
            recent_metrics = [m for m in self.metrics_history if m.start_time >= cutoff_time]
            
            # 生成响应时间统计
            response_times = [m.duration_ms for m in recent_metrics if m.duration_ms is not None and m.success]
            response_time_stats = self._calculate_response_time_stats(response_times)
            
            # 更新系统稳定性
            self._update_system_stability(recent_metrics)
            
            # 生成报告
            report = PerformanceReport(
                time_range_minutes=time_range_minutes,
                response_time_stats=response_time_stats,
                cache_stats=self.cache_stats,
                reranking_stats=self.reranking_stats,
                search_mode_stats=self.search_mode_stats,
                system_stability=self.system_stability,
                exception_summary=self.exception_summary
            )
            
            logger.info(f"生成性能报告: 时间范围={time_range_minutes}分钟, 指标数量={len(recent_metrics)}")
            return report
    
    def _update_statistics(self, metric: PerformanceMetric):
        """更新统计数据"""
        if metric.duration_ms is not None:
            self.response_times.append(metric.duration_ms)
        
        # 根据操作类型更新相应统计
        if metric.operation_type == OperationType.SEARCH and metric.search_mode:
            self.record_search_mode_usage(metric.search_mode, metric.duration_ms or 0, metric.success)
    
    def _calculate_response_time_stats(self, response_times: List[float]) -> ResponseTimeStats:
        """计算响应时间统计"""
        if not response_times:
            return ResponseTimeStats()
        
        sorted_times = sorted(response_times)
        stats = ResponseTimeStats()
        stats.total_queries = len(response_times)
        stats.average_ms = statistics.mean(response_times)
        stats.median_ms = statistics.median(response_times)
        stats.min_ms = min(response_times)
        stats.max_ms = max(response_times)
        
        # 计算百分位数
        if len(sorted_times) >= 20:  # 至少20个样本才计算百分位数
            stats.p95_ms = sorted_times[int(len(sorted_times) * 0.95)]
            stats.p99_ms = sorted_times[int(len(sorted_times) * 0.99)]
        else:
            stats.p95_ms = stats.max_ms
            stats.p99_ms = stats.max_ms
        
        return stats
    
    def _update_system_stability(self, recent_metrics: List[PerformanceMetric]):
        """更新系统稳定性指标（需求13.5）"""
        # 更新活跃查询数
        self.system_stability.active_queries = len(self.active_metrics)
        
        # 计算错误率
        if recent_metrics:
            error_count = sum(1 for m in recent_metrics if not m.success)
            self.system_stability.error_rate = (error_count / len(recent_metrics)) * 100
        
        # 重新计算稳定性评分
        self.system_stability.calculate_stability_score()
    
    def export_metrics(self, format: str = "json", time_range_minutes: int = 60) -> str:
        """导出性能指标"""
        report = self.get_detailed_performance_stats(time_range_minutes)
        
        if format.lower() == "json":
            return json.dumps(report.to_dict(), indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"不支持的导出格式: {format}")
    
    def reset_statistics(self):
        """重置统计数据"""
        with self._lock:
            self.cache_stats = CacheStats()
            self.reranking_stats = RerankingStats()
            self.search_mode_stats = SearchModeStats()
            self.exception_summary = ExceptionSummary()
            self.response_times.clear()
            logger.info("性能统计数据已重置")


# 全局轻量级性能监控器实例
global_lite_monitor = LitePerformanceMonitor()


# 便捷函数
def start_lite_monitoring(query_id: str, operation_type: OperationType, 
                         search_mode: Optional[SearchMode] = None,
                         metadata: Optional[Dict[str, Any]] = None) -> str:
    """开始轻量级性能监控的便捷函数"""
    return global_lite_monitor.start_operation(query_id, operation_type, search_mode, metadata)


def complete_lite_monitoring(metric_key: str, success: bool = True, 
                            result_count: int = 0, error_details: Optional[str] = None):
    """完成轻量级性能监控的便捷函数"""
    global_lite_monitor.complete_operation(metric_key, success, result_count, error_details)


def record_lite_cache_hit(hit: bool, duration_ms: float):
    """记录缓存命中的便捷函数"""
    global_lite_monitor.record_cache_operation(hit, duration_ms)


def record_lite_reranking_performance(success: bool, duration_ms: float, document_count: int = 0):
    """记录重排序性能的便捷函数"""
    global_lite_monitor.record_reranking_operation(success, duration_ms, document_count)


def record_lite_search_mode_performance(mode: SearchMode, duration_ms: float, success: bool):
    """记录搜索模式性能的便捷函数"""
    global_lite_monitor.record_search_mode_usage(mode, duration_ms, success)


def log_lite_performance_exception(exception: Exception, context: Dict[str, Any]):
    """记录性能相关异常的便捷函数"""
    global_lite_monitor.log_exception_details(exception, context)


def get_lite_performance_report(time_range_minutes: int = 60) -> PerformanceReport:
    """获取性能报告的便捷函数"""
    return global_lite_monitor.get_detailed_performance_stats(time_range_minutes)