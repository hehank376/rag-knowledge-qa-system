"""
缓存管理器测试

测试高级缓存管理功能：
- 缓存策略管理
- 缓存指标收集和分析
- 缓存优化功能
- 性能分析和建议
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from rag_system.services.cache_manager import CacheManager, CachePolicy, CacheMetrics
from rag_system.services.cache_service import CacheService


class TestCacheManager:
    """缓存管理器测试类"""
    
    @pytest.fixture
    def cache_service(self):
        """模拟缓存服务"""
        service = AsyncMock(spec=CacheService)
        service.get_cache_info.return_value = {
            'enabled': True,
            'hit_rate': 0.75,
            'miss_rate': 0.25,
            'error_rate': 0.01,
            'cached_queries': 1000,
            'redis_memory': {
                'used_memory': 50 * 1024 * 1024,  # 50MB
                'used_memory_human': '50M'
            }
        }
        service.clear_cache.return_value = 100
        service.warm_up_cache.return_value = 5
        return service
    
    @pytest.fixture
    def cache_policy(self):
        """缓存策略配置"""
        return CachePolicy(
            max_memory_mb=100,
            max_entries=5000,
            default_ttl=3600,
            cleanup_interval=300,
            memory_threshold=0.8,
            hit_rate_threshold=0.5,
            enable_auto_cleanup=True
        )
    
    @pytest.fixture
    def cache_manager(self, cache_service, cache_policy):
        """缓存管理器fixture"""
        return CacheManager(cache_service, cache_policy)
    
    def test_cache_manager_initialization(self, cache_service, cache_policy):
        """测试缓存管理器初始化"""
        manager = CacheManager(cache_service, cache_policy)
        
        assert manager.cache_service == cache_service
        assert manager.policy == cache_policy
        assert manager.is_running is False
        assert manager.cleanup_task is None
        assert len(manager.metrics_history) == 0
    
    def test_cache_manager_default_policy(self, cache_service):
        """测试默认缓存策略"""
        manager = CacheManager(cache_service)
        
        assert manager.policy.max_memory_mb == 100
        assert manager.policy.max_entries == 10000
        assert manager.policy.enable_auto_cleanup is True
    
    @pytest.mark.asyncio
    async def test_start_and_stop_manager(self, cache_manager):
        """测试启动和停止管理器"""
        # 启动管理器
        await cache_manager.start()
        
        assert cache_manager.is_running is True
        assert cache_manager.cleanup_task is not None
        
        # 停止管理器
        await cache_manager.stop()
        
        assert cache_manager.is_running is False
        assert cache_manager.cleanup_task is None
    
    @pytest.mark.asyncio
    async def test_get_metrics(self, cache_manager):
        """测试获取缓存指标"""
        metrics = await cache_manager.get_metrics()
        
        assert isinstance(metrics, CacheMetrics)
        assert metrics.used_memory_mb == 50.0  # 50MB
        assert metrics.memory_usage_percent == 0.5  # 50/100
        assert metrics.total_entries == 1000
        assert metrics.hit_rate == 0.75
        assert metrics.miss_rate == 0.25
        assert metrics.error_rate == 0.01
        assert isinstance(metrics.recommendations, list)  # 建议可能为空，这是正常的
    
    @pytest.mark.asyncio
    async def test_optimize_cache_memory_cleanup(self, cache_manager):
        """测试内存过高时的缓存优化"""
        # 模拟内存使用过高
        cache_manager.cache_service.get_cache_info.return_value = {
            'enabled': True,
            'hit_rate': 0.75,
            'miss_rate': 0.25,
            'error_rate': 0.01,
            'cached_queries': 1000,
            'redis_memory': {
                'used_memory': 90 * 1024 * 1024,  # 90MB，超过80%阈值
                'used_memory_human': '90M'
            }
        }
        
        result = await cache_manager.optimize_cache()
        
        assert result['success'] is True
        assert len(result['actions']) > 0
        assert '清理过期缓存' in result['actions'][0]
        
        # 验证清理方法被调用
        cache_manager.cache_service.clear_cache.assert_called()
    
    @pytest.mark.asyncio
    async def test_optimize_cache_hit_rate_improvement(self, cache_manager):
        """测试命中率低时的缓存优化"""
        # 模拟命中率过低
        cache_manager.cache_service.get_cache_info.return_value = {
            'enabled': True,
            'hit_rate': 0.2,  # 低于0.3阈值
            'miss_rate': 0.8,
            'error_rate': 0.01,
            'cached_queries': 1000,
            'redis_memory': {
                'used_memory': 30 * 1024 * 1024,  # 30MB
                'used_memory_human': '30M'
            }
        }
        
        result = await cache_manager.optimize_cache()
        
        assert result['success'] is True
        assert any('预热热点查询' in action for action in result['actions'])
        
        # 验证预热方法被调用
        cache_manager.cache_service.warm_up_cache.assert_called()
    
    @pytest.mark.asyncio
    async def test_update_policy(self, cache_manager):
        """测试动态更新缓存策略"""
        new_policy = CachePolicy(
            max_memory_mb=200,
            max_entries=20000,
            enable_auto_cleanup=False
        )
        
        result = await cache_manager.update_policy(new_policy)
        
        assert result is True
        assert cache_manager.policy.max_memory_mb == 200
        assert cache_manager.policy.max_entries == 20000
        assert cache_manager.policy.enable_auto_cleanup is False
    
    @pytest.mark.asyncio
    async def test_analyze_performance(self, cache_manager):
        """测试性能分析"""
        # 添加一些历史数据
        for i in range(5):
            await cache_manager.get_metrics()
        
        report = await cache_manager.analyze_performance()
        
        assert 'current_metrics' in report
        assert 'history_analysis' in report
        assert 'performance_score' in report
        assert 'optimization_suggestions' in report
        assert 'trend_analysis' in report
        
        # 验证性能评分
        assert 0 <= report['performance_score'] <= 100
    
    def test_generate_recommendations(self, cache_manager):
        """测试生成优化建议"""
        # 测试高内存使用的建议
        high_memory_metrics = CacheMetrics(
            memory_usage_percent=0.95,
            hit_rate=0.8,
            error_rate=0.01,
            total_entries=1000
        )
        
        recommendations = cache_manager._generate_recommendations(high_memory_metrics)
        assert any('内存使用过高' in rec for rec in recommendations)
        
        # 测试低命中率的建议
        low_hit_rate_metrics = CacheMetrics(
            memory_usage_percent=0.5,
            hit_rate=0.2,
            error_rate=0.01,
            total_entries=1000
        )
        
        recommendations = cache_manager._generate_recommendations(low_hit_rate_metrics)
        assert any('命中率较低' in rec for rec in recommendations)
        
        # 测试高错误率的建议
        high_error_metrics = CacheMetrics(
            memory_usage_percent=0.5,
            hit_rate=0.8,
            error_rate=0.15,
            total_entries=1000
        )
        
        recommendations = cache_manager._generate_recommendations(high_error_metrics)
        assert any('错误率较高' in rec for rec in recommendations)
    
    def test_calculate_performance_score(self, cache_manager):
        """测试性能评分计算"""
        # 测试高性能指标
        high_performance_metrics = CacheMetrics(
            memory_usage_percent=0.6,
            hit_rate=0.9,
            error_rate=0.01,
            avg_response_time=50.0
        )
        
        score = cache_manager._calculate_performance_score(high_performance_metrics)
        assert score > 80  # 高性能应该得到高分
        
        # 测试低性能指标
        low_performance_metrics = CacheMetrics(
            memory_usage_percent=0.95,
            hit_rate=0.2,
            error_rate=0.2,
            avg_response_time=1000.0
        )
        
        score = cache_manager._calculate_performance_score(low_performance_metrics)
        assert score < 50  # 低性能应该得到低分
    
    def test_calculate_trend(self, cache_manager):
        """测试趋势计算"""
        # 测试上升趋势
        increasing_values = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
        trend = cache_manager._calculate_trend(increasing_values)
        assert trend == 'increasing'
        
        # 测试下降趋势
        decreasing_values = [0.6, 0.5, 0.4, 0.3, 0.2, 0.1]
        trend = cache_manager._calculate_trend(decreasing_values)
        assert trend == 'decreasing'
        
        # 测试稳定趋势
        stable_values = [0.5, 0.51, 0.49, 0.5, 0.52, 0.48]
        trend = cache_manager._calculate_trend(stable_values)
        assert trend == 'stable'
    
    def test_update_metrics_history(self, cache_manager):
        """测试指标历史更新"""
        metrics = CacheMetrics(hit_rate=0.8, memory_usage_percent=0.6)
        
        # 添加指标到历史
        cache_manager._update_metrics_history(metrics)
        
        assert len(cache_manager.metrics_history) == 1
        assert cache_manager.metrics_history[0]['metrics'] == metrics
        
        # 测试历史大小限制
        cache_manager.max_history_size = 3
        for i in range(5):
            test_metrics = CacheMetrics(hit_rate=0.8 + i * 0.01)
            cache_manager._update_metrics_history(test_metrics)
        
        assert len(cache_manager.metrics_history) == 3  # 应该限制在最大大小
    
    def test_get_policy_and_status(self, cache_manager):
        """测试获取策略和状态"""
        policy = cache_manager.get_policy()
        assert isinstance(policy, CachePolicy)
        assert policy.max_memory_mb == 100
        
        status = cache_manager.get_status()
        assert 'is_running' in status
        assert 'policy' in status
        assert 'last_metrics' in status
        assert 'history_size' in status
    
    @pytest.mark.asyncio
    async def test_auto_cleanup_trigger(self, cache_manager):
        """测试自动清理触发"""
        # 模拟内存使用过高的情况
        cache_manager.cache_service.get_cache_info.return_value = {
            'enabled': True,
            'hit_rate': 0.75,
            'miss_rate': 0.25,
            'error_rate': 0.01,
            'cached_queries': 6000,  # 超过max_entries
            'redis_memory': {
                'used_memory': 90 * 1024 * 1024,  # 90MB，超过阈值
                'used_memory_human': '90M'
            }
        }
        
        # 启动管理器
        await cache_manager.start()
        
        # 等待一小段时间让自动清理有机会运行
        await asyncio.sleep(0.1)
        
        # 停止管理器
        await cache_manager.stop()
        
        # 验证管理器状态
        assert cache_manager.is_running is False
    
    @pytest.mark.asyncio
    async def test_error_handling_in_optimization(self, cache_manager):
        """测试优化过程中的错误处理"""
        # 模拟缓存服务抛出异常
        cache_manager.cache_service.get_cache_info.side_effect = Exception("Redis连接失败")
        
        result = await cache_manager.optimize_cache()
        
        assert result['success'] is False
        assert 'error' in result
        assert 'Redis连接失败' in result['error']
    
    @pytest.mark.asyncio
    async def test_metrics_with_error_handling(self, cache_manager):
        """测试指标获取的错误处理"""
        # 模拟缓存服务抛出异常
        cache_manager.cache_service.get_cache_info.side_effect = Exception("获取信息失败")
        
        metrics = await cache_manager.get_metrics()
        
        # 应该返回默认的空指标
        assert isinstance(metrics, CacheMetrics)
        assert metrics.hit_rate == 0.0
        assert metrics.memory_usage_percent == 0.0


class TestCachePolicy:
    """缓存策略测试类"""
    
    def test_cache_policy_defaults(self):
        """测试缓存策略默认值"""
        policy = CachePolicy()
        
        assert policy.max_memory_mb == 100
        assert policy.max_entries == 10000
        assert policy.default_ttl == 3600
        assert policy.cleanup_interval == 300
        assert policy.memory_threshold == 0.8
        assert policy.hit_rate_threshold == 0.3
        assert policy.enable_auto_cleanup is True
        assert policy.enable_adaptive_ttl is False
    
    def test_cache_policy_custom_values(self):
        """测试自定义缓存策略值"""
        policy = CachePolicy(
            max_memory_mb=200,
            max_entries=20000,
            default_ttl=7200,
            cleanup_interval=600,
            memory_threshold=0.9,
            hit_rate_threshold=0.4,
            enable_auto_cleanup=False,
            enable_adaptive_ttl=True
        )
        
        assert policy.max_memory_mb == 200
        assert policy.max_entries == 20000
        assert policy.default_ttl == 7200
        assert policy.cleanup_interval == 600
        assert policy.memory_threshold == 0.9
        assert policy.hit_rate_threshold == 0.4
        assert policy.enable_auto_cleanup is False
        assert policy.enable_adaptive_ttl is True


class TestCacheMetrics:
    """缓存指标测试类"""
    
    def test_cache_metrics_defaults(self):
        """测试缓存指标默认值"""
        metrics = CacheMetrics()
        
        assert metrics.total_memory_mb == 0.0
        assert metrics.used_memory_mb == 0.0
        assert metrics.memory_usage_percent == 0.0
        assert metrics.total_entries == 0
        assert metrics.hit_rate == 0.0
        assert metrics.miss_rate == 0.0
        assert metrics.error_rate == 0.0
        assert metrics.avg_response_time == 0.0
        assert metrics.last_cleanup_time is None
        assert len(metrics.recommendations) == 0
    
    def test_cache_metrics_custom_values(self):
        """测试自定义缓存指标值"""
        cleanup_time = datetime.now()
        recommendations = ["建议1", "建议2"]
        
        metrics = CacheMetrics(
            total_memory_mb=100.0,
            used_memory_mb=75.0,
            memory_usage_percent=0.75,
            total_entries=5000,
            hit_rate=0.8,
            miss_rate=0.2,
            error_rate=0.01,
            avg_response_time=50.0,
            last_cleanup_time=cleanup_time,
            recommendations=recommendations
        )
        
        assert metrics.total_memory_mb == 100.0
        assert metrics.used_memory_mb == 75.0
        assert metrics.memory_usage_percent == 0.75
        assert metrics.total_entries == 5000
        assert metrics.hit_rate == 0.8
        assert metrics.miss_rate == 0.2
        assert metrics.error_rate == 0.01
        assert metrics.avg_response_time == 50.0
        assert metrics.last_cleanup_time == cleanup_time
        assert metrics.recommendations == recommendations


if __name__ == "__main__":
    pytest.main([__file__])