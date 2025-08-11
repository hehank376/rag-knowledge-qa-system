"""
错误恢复和降级机制测试
"""
import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta

from rag_system.utils.error_recovery import (
    RetryStrategy, FallbackStrategy, RetryConfig, FallbackConfig,
    ErrorStats, CircuitBreaker, RetryManager, ErrorRecoveryManager,
    get_global_recovery_manager, set_global_recovery_manager,
    with_error_recovery
)
from rag_system.utils.model_exceptions import (
    ModelError, ModelConnectionError, ModelRateLimitError,
    ModelTimeoutError, ModelAuthenticationError, ErrorCode
)


class TestRetryConfig:
    """重试配置测试"""
    
    def test_default_retry_config(self):
        """测试默认重试配置"""
        config = RetryConfig()
        
        assert config.max_attempts == 3
        assert config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.backoff_multiplier == 2.0
        assert config.jitter is True
        assert ModelConnectionError in config.retryable_errors
        assert ModelTimeoutError in config.retryable_errors
        assert ModelRateLimitError in config.retryable_errors
    
    def test_custom_retry_config(self):
        """测试自定义重试配置"""
        config = RetryConfig(
            max_attempts=5,
            strategy=RetryStrategy.FIXED_DELAY,
            base_delay=2.0,
            max_delay=30.0,
            jitter=False
        )
        
        assert config.max_attempts == 5
        assert config.strategy == RetryStrategy.FIXED_DELAY
        assert config.base_delay == 2.0
        assert config.max_delay == 30.0
        assert config.jitter is False


class TestFallbackConfig:
    """降级配置测试"""
    
    def test_default_fallback_config(self):
        """测试默认降级配置"""
        config = FallbackConfig()
        
        assert config.strategy == FallbackStrategy.BACKUP_MODEL
        assert config.backup_providers == []
        assert config.cache_ttl == 300
        assert config.enable_circuit_breaker is True
        assert config.circuit_breaker_threshold == 5
        assert config.circuit_breaker_timeout == 60
    
    def test_custom_fallback_config(self):
        """测试自定义降级配置"""
        config = FallbackConfig(
            strategy=FallbackStrategy.CACHED_RESPONSE,
            backup_providers=["mock", "openai"],
            cache_ttl=600,
            enable_circuit_breaker=False
        )
        
        assert config.strategy == FallbackStrategy.CACHED_RESPONSE
        assert config.backup_providers == ["mock", "openai"]
        assert config.cache_ttl == 600
        assert config.enable_circuit_breaker is False


class TestCircuitBreaker:
    """熔断器测试"""
    
    def test_circuit_breaker_closed_state(self):
        """测试熔断器关闭状态"""
        breaker = CircuitBreaker(failure_threshold=3, timeout=60)
        
        # 初始状态应该是关闭的
        assert breaker.state == "closed"
        assert breaker.failure_count == 0
        
        # 成功调用
        def success_func():
            return "success"
        
        result = breaker.call(success_func)
        assert result == "success"
        assert breaker.state == "closed"
    
    def test_circuit_breaker_open_state(self):
        """测试熔断器开启状态"""
        breaker = CircuitBreaker(failure_threshold=2, timeout=60)
        
        def failing_func():
            raise ModelConnectionError("连接失败")
        
        # 第一次失败
        with pytest.raises(ModelConnectionError):
            breaker.call(failing_func)
        assert breaker.state == "closed"
        assert breaker.failure_count == 1
        
        # 第二次失败，应该开启熔断器
        with pytest.raises(ModelConnectionError):
            breaker.call(failing_func)
        assert breaker.state == "open"
        assert breaker.failure_count == 2
        
        # 熔断器开启后，直接抛出ModelError
        with pytest.raises(ModelError) as exc_info:
            breaker.call(failing_func)
        assert "熔断器开启" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_async(self):
        """测试异步熔断器"""
        breaker = CircuitBreaker(failure_threshold=2, timeout=1)
        
        async def failing_func():
            raise ModelConnectionError("连接失败")
        
        # 触发熔断器开启
        with pytest.raises(ModelConnectionError):
            await breaker.acall(failing_func)
        with pytest.raises(ModelConnectionError):
            await breaker.acall(failing_func)
        
        assert breaker.state == "open"
        
        # 等待超时后应该进入半开状态
        await asyncio.sleep(1.1)
        
        async def success_func():
            return "success"
        
        result = await breaker.acall(success_func)
        assert result == "success"
        assert breaker.state == "closed"
    
    def test_circuit_breaker_state_info(self):
        """测试熔断器状态信息"""
        breaker = CircuitBreaker(failure_threshold=3, timeout=60)
        
        state = breaker.get_state()
        assert state["state"] == "closed"
        assert state["failure_count"] == 0
        assert state["failure_threshold"] == 3
        assert state["timeout"] == 60
        assert state["last_failure_time"] is None


class TestRetryManager:
    """重试管理器测试"""
    
    def test_should_retry_logic(self):
        """测试重试判断逻辑"""
        config = RetryConfig(max_attempts=3)
        manager = RetryManager(config)
        
        # 可重试的错误
        connection_error = ModelConnectionError("连接失败")
        assert manager.should_retry(connection_error, 1) is True
        assert manager.should_retry(connection_error, 3) is False  # 超过最大次数
        
        # 不可重试的错误
        auth_error = ModelAuthenticationError("认证失败")
        assert manager.should_retry(auth_error, 1) is False
        
        # 限流错误总是可重试
        rate_limit_error = ModelRateLimitError("限流")
        assert manager.should_retry(rate_limit_error, 1) is True
    
    def test_calculate_delay_strategies(self):
        """测试不同的延迟计算策略"""
        # 固定延迟
        config = RetryConfig(strategy=RetryStrategy.FIXED_DELAY, base_delay=2.0, jitter=False)
        manager = RetryManager(config)
        assert manager.calculate_delay(1) == 2.0
        assert manager.calculate_delay(3) == 2.0
        
        # 指数退避
        config = RetryConfig(
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF, 
            base_delay=1.0, 
            backoff_multiplier=2.0,
            jitter=False
        )
        manager = RetryManager(config)
        assert manager.calculate_delay(1) == 1.0
        assert manager.calculate_delay(2) == 2.0
        assert manager.calculate_delay(3) == 4.0
        
        # 线性退避
        config = RetryConfig(strategy=RetryStrategy.LINEAR_BACKOFF, base_delay=1.0, jitter=False)
        manager = RetryManager(config)
        assert manager.calculate_delay(1) == 1.0
        assert manager.calculate_delay(2) == 2.0
        assert manager.calculate_delay(3) == 3.0
        
        # 斐波那契退避
        config = RetryConfig(strategy=RetryStrategy.FIBONACCI_BACKOFF, base_delay=1.0, jitter=False)
        manager = RetryManager(config)
        assert manager.calculate_delay(1) == 1.0
        assert manager.calculate_delay(2) == 1.0
        assert manager.calculate_delay(3) == 2.0
        assert manager.calculate_delay(4) == 3.0
    
    def test_calculate_delay_with_rate_limit(self):
        """测试限流错误的延迟计算"""
        config = RetryConfig(jitter=False)
        manager = RetryManager(config)
        
        # 带重试时间的限流错误
        rate_limit_error = ModelRateLimitError("限流", retry_after=30)
        delay = manager.calculate_delay(1, rate_limit_error)
        assert delay == 30
        
        # 不带重试时间的限流错误
        rate_limit_error = ModelRateLimitError("限流")
        delay = manager.calculate_delay(1, rate_limit_error)
        assert delay == config.base_delay
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_success(self):
        """测试重试成功场景"""
        config = RetryConfig(max_attempts=3)
        manager = RetryManager(config)
        
        call_count = 0
        
        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ModelConnectionError("连接失败")
            return "success"
        
        result = await manager.execute_with_retry(flaky_func)
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_failure(self):
        """测试重试失败场景"""
        config = RetryConfig(max_attempts=2, base_delay=0.01)
        manager = RetryManager(config)
        
        call_count = 0
        
        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise ModelConnectionError("连接失败")
        
        with pytest.raises(ModelConnectionError):
            await manager.execute_with_retry(always_fail)
        
        assert call_count == 2  # 应该重试2次


class TestErrorRecoveryManager:
    """错误恢复管理器测试"""
    
    def test_error_recovery_manager_initialization(self):
        """测试错误恢复管理器初始化"""
        manager = ErrorRecoveryManager()
        
        assert manager.retry_config is not None
        assert manager.fallback_config is not None
        assert manager.retry_manager is not None
        assert len(manager.circuit_breakers) > 0
        assert isinstance(manager.error_stats, ErrorStats)
    
    @pytest.mark.asyncio
    async def test_execute_with_recovery_success(self):
        """测试错误恢复成功场景"""
        manager = ErrorRecoveryManager()
        
        async def success_func():
            return "success"
        
        result = await manager.execute_with_recovery(success_func, provider="openai")
        assert result == "success"
        assert manager.error_stats.consecutive_failures == 0
    
    @pytest.mark.asyncio
    async def test_execute_with_recovery_with_fallback(self):
        """测试使用降级的错误恢复"""
        retry_config = RetryConfig(max_attempts=1)  # 不重试
        fallback_config = FallbackConfig(strategy=FallbackStrategy.BACKUP_MODEL)
        manager = ErrorRecoveryManager(retry_config, fallback_config)
        
        async def failing_func():
            raise ModelConnectionError("连接失败")
        
        async def fallback_func():
            return "fallback_success"
        
        result = await manager.execute_with_recovery(
            failing_func, 
            provider="openai",
            fallback_func=fallback_func
        )
        
        assert result == "fallback_success"
        assert manager.error_stats.total_errors == 1
        assert manager.error_stats.successful_recoveries == 1
    
    @pytest.mark.asyncio
    async def test_execute_with_recovery_with_cache(self):
        """测试使用缓存的错误恢复"""
        retry_config = RetryConfig(max_attempts=1)
        fallback_config = FallbackConfig(strategy=FallbackStrategy.CACHED_RESPONSE)
        manager = ErrorRecoveryManager(retry_config, fallback_config)
        
        # 先缓存一个响应
        cache_key = "test_key"
        manager._cache_response(cache_key, "cached_result")
        
        async def failing_func():
            raise ModelConnectionError("连接失败")
        
        result = await manager.execute_with_recovery(
            failing_func,
            provider="openai",
            cache_key=cache_key
        )
        
        assert result == "cached_result"
        assert manager.error_stats.successful_recoveries == 1
    
    @pytest.mark.asyncio
    async def test_execute_with_recovery_simplified_response(self):
        """测试简化响应降级"""
        retry_config = RetryConfig(max_attempts=1)
        fallback_config = FallbackConfig(strategy=FallbackStrategy.SIMPLIFIED_RESPONSE)
        manager = ErrorRecoveryManager(retry_config, fallback_config)
        
        async def failing_func():
            raise ModelConnectionError("连接失败")
        
        result = await manager.execute_with_recovery(failing_func, provider="openai")
        
        assert isinstance(result, dict)
        assert result["status"] == "degraded"
        assert "服务暂时不可用" in result["message"]
        assert manager.error_stats.successful_recoveries == 1
    
    def test_error_stats_recording(self):
        """测试错误统计记录"""
        manager = ErrorRecoveryManager()
        
        # 记录错误
        error1 = ModelConnectionError("连接失败", provider="openai")
        manager._record_error(error1, "openai")
        
        error2 = ModelTimeoutError("超时", provider="siliconflow")
        manager._record_error(error2, "siliconflow")
        
        error3 = ModelConnectionError("连接失败", provider="openai")
        manager._record_error(error3, "openai")
        
        # 检查统计
        assert manager.error_stats.total_errors == 3
        assert manager.error_stats.consecutive_failures == 3
        assert manager.error_stats.error_by_type["ModelConnectionError"] == 2
        assert manager.error_stats.error_by_type["ModelTimeoutError"] == 1
        assert manager.error_stats.error_by_provider["openai"] == 2
        assert manager.error_stats.error_by_provider["siliconflow"] == 1
        
        # 记录成功
        manager._record_success("openai")
        assert manager.error_stats.consecutive_failures == 0
    
    def test_response_caching(self):
        """测试响应缓存"""
        manager = ErrorRecoveryManager()
        
        # 缓存响应
        cache_key = "test_key"
        response = {"result": "test"}
        manager._cache_response(cache_key, response)
        
        # 获取缓存
        cached = manager._get_cached_response(cache_key)
        assert cached == response
        
        # 测试缓存过期
        manager.fallback_config.cache_ttl = 0
        manager._cache_response(cache_key, response)
        time.sleep(0.01)
        cached = manager._get_cached_response(cache_key)
        assert cached is None
    
    def test_get_error_stats(self):
        """测试获取错误统计"""
        manager = ErrorRecoveryManager()
        
        # 记录一些错误和恢复
        manager._record_error(ModelConnectionError("错误"), "openai")
        manager.error_stats.recovery_attempts = 2
        manager.error_stats.successful_recoveries = 1
        
        stats = manager.get_error_stats()
        
        assert stats["total_errors"] == 1
        assert stats["consecutive_failures"] == 1
        assert stats["recovery_attempts"] == 2
        assert stats["successful_recoveries"] == 1
        assert stats["success_rate"] == 0.5
        assert "last_error_time" in stats
    
    def test_get_circuit_breaker_stats(self):
        """测试获取熔断器统计"""
        manager = ErrorRecoveryManager()
        
        stats = manager.get_circuit_breaker_stats()
        
        assert isinstance(stats, dict)
        assert "openai" in stats
        assert "siliconflow" in stats
        assert stats["openai"]["state"] == "closed"
    
    def test_reset_and_clear(self):
        """测试重置和清理"""
        manager = ErrorRecoveryManager()
        
        # 添加一些数据
        manager._record_error(ModelConnectionError("错误"), "openai")
        manager._cache_response("key", "value")
        
        # 重置统计
        manager.reset_stats()
        assert manager.error_stats.total_errors == 0
        assert len(manager.response_cache) == 0
        
        # 重新添加缓存
        manager._cache_response("key", "value")
        assert len(manager.response_cache) == 1
        
        # 清理缓存
        manager.clear_cache()
        assert len(manager.response_cache) == 0


class TestGlobalRecoveryManager:
    """全局错误恢复管理器测试"""
    
    def test_global_recovery_manager(self):
        """测试全局错误恢复管理器"""
        # 获取全局管理器
        manager1 = get_global_recovery_manager()
        manager2 = get_global_recovery_manager()
        
        # 应该是同一个实例
        assert manager1 is manager2
        
        # 设置新的全局管理器
        new_manager = ErrorRecoveryManager()
        set_global_recovery_manager(new_manager)
        
        manager3 = get_global_recovery_manager()
        assert manager3 is new_manager
        assert manager3 is not manager1


class TestErrorRecoveryDecorator:
    """错误恢复装饰器测试"""
    
    @pytest.mark.asyncio
    async def test_async_decorator(self):
        """测试异步装饰器"""
        call_count = 0
        
        @with_error_recovery(
            provider="openai",
            retry_config=RetryConfig(max_attempts=3, base_delay=0.01)
        )
        async def flaky_async_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ModelConnectionError("连接失败")
            return "success"
        
        result = await flaky_async_func()
        assert result == "success"
        assert call_count == 3
    
    def test_sync_decorator(self):
        """测试同步装饰器"""
        call_count = 0
        
        @with_error_recovery(
            provider="openai",
            retry_config=RetryConfig(max_attempts=3, base_delay=0.01)
        )
        def flaky_sync_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ModelConnectionError("连接失败")
            return "success"
        
        result = flaky_sync_func()
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_decorator_with_cache_key(self):
        """测试带缓存键的装饰器"""
        def cache_key_func(*args, **kwargs):
            return "same_cache_key"  # 使用相同的缓存键
        
        @with_error_recovery(
            provider="openai",
            retry_config=RetryConfig(max_attempts=1),
            fallback_config=FallbackConfig(strategy=FallbackStrategy.CACHED_RESPONSE),
            cache_key_func=cache_key_func
        )
        async def test_func(param):
            if param == "fail":
                raise ModelConnectionError("连接失败")
            return f"success_{param}"
        
        # 第一次成功调用，会缓存结果
        result1 = await test_func("test")
        assert result1 == "success_test"
        
        # 第二次失败调用，应该返回缓存结果
        result2 = await test_func("fail")
        assert result2 == "success_test"  # 应该返回缓存的结果


if __name__ == "__main__":
    pytest.main([__file__, "-v"])