"""
缓存管理器模块

提供高级的缓存管理功能：
- 缓存大小监控和内存管理
- 缓存配置的动态调整
- 缓存失效策略管理
- 缓存性能分析和优化建议
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from .cache_service import CacheService
from ..models.config import RetrievalConfig

logger = logging.getLogger(__name__)


@dataclass
class CachePolicy:
    """缓存策略配置"""
    max_memory_mb: int = 100  # 最大内存使用（MB）
    max_entries: int = 10000  # 最大缓存条目数
    default_ttl: int = 3600  # 默认TTL（秒）
    cleanup_interval: int = 300  # 清理间隔（秒）
    memory_threshold: float = 0.8  # 内存使用阈值
    hit_rate_threshold: float = 0.3  # 命中率阈值
    enable_auto_cleanup: bool = True  # 启用自动清理
    enable_adaptive_ttl: bool = False  # 启用自适应TTL


@dataclass
class CacheMetrics:
    """缓存指标"""
    total_memory_mb: float = 0.0
    used_memory_mb: float = 0.0
    memory_usage_percent: float = 0.0
    total_entries: int = 0
    hit_rate: float = 0.0
    miss_rate: float = 0.0
    error_rate: float = 0.0
    avg_response_time: float = 0.0
    last_cleanup_time: Optional[datetime] = None
    recommendations: List[str] = field(default_factory=list)


class CacheManager:
    """高级缓存管理器"""
    
    def __init__(self, cache_service: CacheService, policy: Optional[CachePolicy] = None):
        """
        初始化缓存管理器
        
        Args:
            cache_service: 缓存服务实例
            policy: 缓存策略配置
        """
        self.cache_service = cache_service
        self.policy = policy or CachePolicy()
        
        # 管理状态
        self.is_running = False
        self.cleanup_task = None
        self.last_metrics = CacheMetrics()
        
        # 性能历史记录
        self.metrics_history = []
        self.max_history_size = 100
        
        logger.info(f"缓存管理器初始化完成，策略: {self.policy}")
    
    async def start(self) -> None:
        """启动缓存管理器"""
        if self.is_running:
            logger.warning("缓存管理器已经在运行")
            return
        
        self.is_running = True
        
        # 启动自动清理任务
        if self.policy.enable_auto_cleanup:
            self.cleanup_task = asyncio.create_task(self._auto_cleanup_loop())
            logger.info("自动清理任务已启动")
        
        logger.info("缓存管理器已启动")
    
    async def stop(self) -> None:
        """停止缓存管理器"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # 停止自动清理任务
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            self.cleanup_task = None
        
        logger.info("缓存管理器已停止")
    
    async def get_metrics(self) -> CacheMetrics:
        """获取缓存指标"""
        try:
            # 获取基础缓存信息
            cache_info = await self.cache_service.get_cache_info()
            
            # 计算内存使用
            redis_memory = cache_info.get('redis_memory', {})
            used_memory_bytes = redis_memory.get('used_memory', 0)
            used_memory_mb = used_memory_bytes / (1024 * 1024)
            
            # 获取缓存条目数
            total_entries = cache_info.get('cached_queries', 0)
            
            # 计算内存使用百分比
            memory_usage_percent = 0.0
            if self.policy.max_memory_mb > 0:
                memory_usage_percent = used_memory_mb / self.policy.max_memory_mb
            
            # 创建指标对象
            metrics = CacheMetrics(
                used_memory_mb=used_memory_mb,
                memory_usage_percent=memory_usage_percent,
                total_entries=total_entries,
                hit_rate=cache_info.get('hit_rate', 0.0),
                miss_rate=cache_info.get('miss_rate', 0.0),
                error_rate=cache_info.get('error_rate', 0.0),
                last_cleanup_time=self.last_metrics.last_cleanup_time
            )
            
            # 生成优化建议
            metrics.recommendations = self._generate_recommendations(metrics)
            
            # 更新历史记录
            self.last_metrics = metrics
            self._update_metrics_history(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"获取缓存指标失败: {e}")
            return CacheMetrics()
    
    async def optimize_cache(self) -> Dict[str, Any]:
        """缓存优化"""
        try:
            metrics = await self.get_metrics()
            
            # 如果获取指标失败（返回默认值），则无法进行优化
            if metrics.hit_rate == 0.0 and metrics.memory_usage_percent == 0.0 and metrics.total_entries == 0:
                # 检查是否是因为缓存服务不可用
                try:
                    await self.cache_service.get_cache_info()
                except Exception as e:
                    return {
                        'success': False,
                        'error': f'缓存服务不可用，无法进行优化: {str(e)}'
                    }
            
            optimization_actions = []
            
            # 内存使用优化
            if metrics.memory_usage_percent > self.policy.memory_threshold:
                # 清理过期缓存
                deleted_count = await self._cleanup_expired_cache()
                optimization_actions.append(f"清理过期缓存: {deleted_count}个条目")
                
                # 如果内存使用仍然过高，清理最少使用的缓存
                updated_metrics = await self.get_metrics()
                if updated_metrics.memory_usage_percent > self.policy.memory_threshold:
                    lru_deleted = await self._cleanup_lru_cache()
                    optimization_actions.append(f"清理LRU缓存: {lru_deleted}个条目")
            
            # 命中率优化
            if metrics.hit_rate < self.policy.hit_rate_threshold:
                # 分析热点查询并预热
                hot_queries = await self._analyze_hot_queries()
                if hot_queries:
                    warmed_count = await self.cache_service.warm_up_cache(hot_queries)
                    optimization_actions.append(f"预热热点查询: {warmed_count}个查询")
            
            # 更新最后清理时间
            self.last_metrics.last_cleanup_time = datetime.now()
            
            return {
                'success': True,
                'actions': optimization_actions,
                'metrics_before': metrics,
                'metrics_after': await self.get_metrics()
            }
            
        except Exception as e:
            logger.error(f"缓存优化失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def update_policy(self, new_policy: CachePolicy) -> bool:
        """动态更新缓存策略"""
        try:
            old_policy = self.policy
            self.policy = new_policy
            
            logger.info(f"缓存策略已更新: {old_policy} -> {new_policy}")
            
            # 如果自动清理设置发生变化，重启管理器
            if old_policy.enable_auto_cleanup != new_policy.enable_auto_cleanup:
                await self.stop()
                await self.start()
            
            return True
            
        except Exception as e:
            logger.error(f"更新缓存策略失败: {e}")
            return False
    
    async def analyze_performance(self, days: int = 7) -> Dict[str, Any]:
        """分析缓存性能"""
        try:
            # 获取当前指标
            current_metrics = await self.get_metrics()
            
            # 分析历史趋势
            history_analysis = self._analyze_metrics_history()
            
            # 生成性能报告
            report = {
                'current_metrics': current_metrics,
                'history_analysis': history_analysis,
                'performance_score': self._calculate_performance_score(current_metrics),
                'optimization_suggestions': self._generate_optimization_suggestions(current_metrics),
                'trend_analysis': self._analyze_trends()
            }
            
            return report
            
        except Exception as e:
            logger.error(f"性能分析失败: {e}")
            return {'error': str(e)}
    
    async def _auto_cleanup_loop(self) -> None:
        """自动清理循环"""
        while self.is_running:
            try:
                await asyncio.sleep(self.policy.cleanup_interval)
                
                if not self.is_running:
                    break
                
                # 检查是否需要清理
                metrics = await self.get_metrics()
                
                if (metrics.memory_usage_percent > self.policy.memory_threshold or
                    metrics.total_entries > self.policy.max_entries):
                    
                    logger.info("触发自动缓存清理")
                    await self.optimize_cache()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"自动清理循环错误: {e}")
                await asyncio.sleep(60)  # 错误后等待1分钟再继续
    
    async def _cleanup_expired_cache(self) -> int:
        """清理过期缓存"""
        try:
            # 这里需要Redis支持，实际实现可能需要使用Redis的SCAN和TTL命令
            # 目前简化实现，清理所有缓存
            deleted_count = await self.cache_service.clear_cache()
            logger.info(f"清理过期缓存完成: {deleted_count}个条目")
            return deleted_count
            
        except Exception as e:
            logger.error(f"清理过期缓存失败: {e}")
            return 0
    
    async def _cleanup_lru_cache(self) -> int:
        """清理最少使用的缓存"""
        try:
            # 简化实现：清理一半的缓存
            # 实际实现需要Redis的LRU支持或自定义LRU逻辑
            cache_info = await self.cache_service.get_cache_info()
            total_entries = cache_info.get('cached_queries', 0)
            
            if total_entries > self.policy.max_entries:
                # 清理超出限制的条目
                excess_entries = total_entries - self.policy.max_entries
                # 这里需要实现LRU清理逻辑
                logger.info(f"需要清理LRU缓存: {excess_entries}个条目")
                return excess_entries
            
            return 0
            
        except Exception as e:
            logger.error(f"清理LRU缓存失败: {e}")
            return 0
    
    async def _analyze_hot_queries(self) -> List[Dict[str, Any]]:
        """分析热点查询"""
        try:
            # 这里需要实现查询频率分析
            # 简化实现：返回一些常见查询
            hot_queries = [
                {
                    'query': '什么是人工智能？',
                    'config': {
                        'search_mode': 'semantic',
                        'top_k': 5,
                        'enable_cache': True
                    }
                },
                {
                    'query': '机器学习的应用',
                    'config': {
                        'search_mode': 'hybrid',
                        'top_k': 10,
                        'enable_cache': True
                    }
                }
            ]
            
            return hot_queries
            
        except Exception as e:
            logger.error(f"分析热点查询失败: {e}")
            return []
    
    def _generate_recommendations(self, metrics: CacheMetrics) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        # 内存使用建议
        if metrics.memory_usage_percent > 0.9:
            recommendations.append("内存使用过高，建议增加内存或清理缓存")
        elif metrics.memory_usage_percent > 0.7:
            recommendations.append("内存使用较高，建议监控内存使用情况")
        
        # 命中率建议
        if metrics.hit_rate < 0.3:
            recommendations.append("缓存命中率较低，建议分析查询模式并优化缓存策略")
        elif metrics.hit_rate < 0.5:
            recommendations.append("缓存命中率中等，可以考虑预热常见查询")
        
        # 错误率建议
        if metrics.error_rate > 0.1:
            recommendations.append("缓存错误率较高，建议检查Redis连接和配置")
        
        # 条目数建议
        if metrics.total_entries > self.policy.max_entries * 0.9:
            recommendations.append("缓存条目数接近上限，建议启用自动清理")
        
        return recommendations
    
    def _generate_optimization_suggestions(self, metrics: CacheMetrics) -> List[str]:
        """生成优化建议"""
        suggestions = []
        
        if metrics.hit_rate < 0.5:
            suggestions.append("考虑增加缓存TTL以提高命中率")
            suggestions.append("分析查询模式，预热常见查询")
        
        if metrics.memory_usage_percent > 0.8:
            suggestions.append("考虑增加Redis内存或启用内存优化")
            suggestions.append("调整缓存策略，减少不必要的缓存")
        
        if metrics.error_rate > 0.05:
            suggestions.append("检查Redis连接稳定性")
            suggestions.append("优化缓存错误处理逻辑")
        
        return suggestions
    
    def _calculate_performance_score(self, metrics: CacheMetrics) -> float:
        """计算性能评分（0-100）"""
        score = 0.0
        
        # 命中率权重40%
        hit_rate_score = min(metrics.hit_rate * 100, 100) * 0.4
        
        # 内存使用权重30%（使用率适中得分高）
        memory_score = 0.0
        if metrics.memory_usage_percent < 0.8:
            memory_score = (1 - abs(metrics.memory_usage_percent - 0.5) * 2) * 100 * 0.3
        
        # 错误率权重20%
        error_score = max(0, (1 - metrics.error_rate * 10)) * 100 * 0.2
        
        # 响应时间权重10%
        response_score = max(0, (1 - metrics.avg_response_time / 1000)) * 100 * 0.1
        
        score = hit_rate_score + memory_score + error_score + response_score
        return min(max(score, 0), 100)
    
    def _update_metrics_history(self, metrics: CacheMetrics) -> None:
        """更新指标历史记录"""
        self.metrics_history.append({
            'timestamp': datetime.now(),
            'metrics': metrics
        })
        
        # 保持历史记录大小
        if len(self.metrics_history) > self.max_history_size:
            self.metrics_history = self.metrics_history[-self.max_history_size:]
    
    def _analyze_metrics_history(self) -> Dict[str, Any]:
        """分析指标历史"""
        if len(self.metrics_history) < 2:
            return {'message': '历史数据不足'}
        
        # 计算趋势
        recent_metrics = [h['metrics'] for h in self.metrics_history[-10:]]
        
        hit_rate_trend = self._calculate_trend([m.hit_rate for m in recent_metrics])
        memory_trend = self._calculate_trend([m.memory_usage_percent for m in recent_metrics])
        error_trend = self._calculate_trend([m.error_rate for m in recent_metrics])
        
        return {
            'hit_rate_trend': hit_rate_trend,
            'memory_usage_trend': memory_trend,
            'error_rate_trend': error_trend,
            'data_points': len(self.metrics_history)
        }
    
    def _calculate_trend(self, values: List[float]) -> str:
        """计算趋势"""
        if len(values) < 2:
            return 'stable'
        
        # 简单的趋势计算
        first_half = sum(values[:len(values)//2]) / (len(values)//2)
        second_half = sum(values[len(values)//2:]) / (len(values) - len(values)//2)
        
        diff = second_half - first_half
        
        if abs(diff) < 0.05:
            return 'stable'
        elif diff > 0:
            return 'increasing'
        else:
            return 'decreasing'
    
    def _analyze_trends(self) -> Dict[str, Any]:
        """分析趋势"""
        if len(self.metrics_history) < 5:
            return {'message': '数据不足以分析趋势'}
        
        # 分析最近的趋势
        recent_history = self.metrics_history[-10:]
        
        trends = {
            'hit_rate': self._calculate_trend([h['metrics'].hit_rate for h in recent_history]),
            'memory_usage': self._calculate_trend([h['metrics'].memory_usage_percent for h in recent_history]),
            'error_rate': self._calculate_trend([h['metrics'].error_rate for h in recent_history])
        }
        
        return trends
    
    def get_policy(self) -> CachePolicy:
        """获取当前缓存策略"""
        return self.policy
    
    def get_status(self) -> Dict[str, Any]:
        """获取管理器状态"""
        return {
            'is_running': self.is_running,
            'policy': self.policy,
            'last_metrics': self.last_metrics,
            'history_size': len(self.metrics_history)
        }