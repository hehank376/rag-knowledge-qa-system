"""
错误恢复和降级机制
"""
import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from .model_exceptions import (
    ModelError, ModelConnectionError, ModelRateLimitError, 
    ModelTimeoutError, ModelAuthenticationError, ErrorCode
)

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """重试策略枚举"""
    FIXED_DELAY = "fixed_delay"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIBONACCI_BACKOFF = "fibonacci_backoff"


class FallbackStrategy(Enum):
    """降级策略枚举"""
    NONE = "none"
    BACKUP_MODEL = "backup_model"
    CACHED_RESPONSE = "cached_response"
    SIMPLIFIED_RESPONSE = "simplified_response"


@dataclass
class RetryConfig:
    """重试配置"""
    max_attempts: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True
    retryable_errors: List[type] = field(default_factory=lambda: [
        ModelConnectionError, ModelTimeoutError, ModelRateLimitError
    ])


@dataclass
class FallbackConfig:
    """降级配置"""
    strategy: FallbackStrategy = FallbackStrategy.BACKUP_MODEL
    backup_providers: List[str] = field(default_factory=list)
    cache_ttl: int = 300  # 缓存生存时间（秒）
    enable_circuit_breaker: bool = True
    circuit_breaker_threshold: int = 5  # 连续失败次数阈值
    circuit_breaker_timeout: int = 60  # 熔断器超时时间（秒）


@dataclass
class ErrorStats:
    """错误统计"""
    total_errors: int = 0
    error_by_type: Dict[str, int] = field(default_factory=dict)
    error_by_provider: Dict[str, int] = field(default_factory=dict)
    consecutive_failures: int = 0
    last_error_time: Optional[datetime] = None
    recovery_attempts: int = 0
    successful_recoveries: int = 0


class CircuitBreaker:
    """熔断器"""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed, open, half_open
    
    def call(self, func: Callable, *args, **kwargs):
        """调用函数并处理熔断逻辑"""
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half_open"
            else:
                raise ModelError(
                    "熔断器开启，服务暂时不可用",
                    error_code=ErrorCode.MODEL_OVERLOADED
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    async def acall(self, func: Callable, *args, **kwargs):
        """异步调用函数并处理熔断逻辑"""
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half_open"
            else:
                raise ModelError(
                    "熔断器开启，服务暂时不可用",
                    error_code=ErrorCode.MODEL_OVERLOADED
                )
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """判断是否应该尝试重置熔断器"""
        if self.last_failure_time is None:
            return True
        
        return (datetime.now() - self.last_failure_time).total_seconds() > self.timeout
    
    def _on_success(self):
        """成功时的处理"""
        self.failure_count = 0
        self.state = "closed"
    
    def _on_failure(self):
        """失败时的处理"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
    
    def get_state(self) -> Dict[str, Any]:
        """获取熔断器状态"""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "timeout": self.timeout
        }


class RetryManager:
    """重试管理器"""
    
    def __init__(self, config: RetryConfig):
        self.config = config
        self._fibonacci_cache = [1, 1]
    
    def should_retry(self, error: Exception, attempt: int) -> bool:
        """判断是否应该重试"""
        if attempt >= self.config.max_attempts:
            return False
        
        # 检查错误类型是否可重试
        for retryable_error in self.config.retryable_errors:
            if isinstance(error, retryable_error):
                return True
        
        # 特殊处理限流错误
        if isinstance(error, ModelRateLimitError):
            return True
        
        return False
    
    def calculate_delay(self, attempt: int, error: Optional[Exception] = None) -> float:
        """计算重试延迟时间"""
        if isinstance(error, ModelRateLimitError) and hasattr(error, 'retry_after'):
            # 限流错误使用服务器指定的重试时间
            return min(error.retry_after or self.config.base_delay, self.config.max_delay)
        
        if self.config.strategy == RetryStrategy.FIXED_DELAY:
            delay = self.config.base_delay
        elif self.config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.config.base_delay * (self.config.backoff_multiplier ** (attempt - 1))
        elif self.config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.config.base_delay * attempt
        elif self.config.strategy == RetryStrategy.FIBONACCI_BACKOFF:
            delay = self.config.base_delay * self._get_fibonacci(attempt - 1)
        else:
            delay = self.config.base_delay
        
        # 应用最大延迟限制
        delay = min(delay, self.config.max_delay)
        
        # 添加抖动
        if self.config.jitter:
            import random
            delay = delay * (0.5 + random.random() * 0.5)
        
        return delay
    
    def _get_fibonacci(self, n: int) -> int:
        """获取斐波那契数列第n项"""
        if n < 0:
            return 1
        while len(self._fibonacci_cache) <= n:
            next_fib = self._fibonacci_cache[-1] + self._fibonacci_cache[-2]
            self._fibonacci_cache.append(next_fib)
        
        return self._fibonacci_cache[n]
    
    async def execute_with_retry(
        self, 
        func: Callable, 
        *args, 
        **kwargs
    ) -> Any:
        """执行函数并处理重试"""
        last_error = None
        
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                
                if not self.should_retry(e, attempt):
                    break
                
                if attempt < self.config.max_attempts:
                    delay = self.calculate_delay(attempt, e)
                    logger.warning(
                        f"第 {attempt} 次尝试失败: {str(e)}, "
                        f"等待 {delay:.2f}s 后重试"
                    )
                    await asyncio.sleep(delay)
        
        # 所有重试都失败了
        logger.error(f"重试 {self.config.max_attempts} 次后仍然失败: {str(last_error)}")
        raise last_error


class ErrorRecoveryManager:
    """错误恢复管理器"""
    
    def __init__(
        self, 
        retry_config: Optional[RetryConfig] = None,
        fallback_config: Optional[FallbackConfig] = None
    ):
        self.retry_config = retry_config or RetryConfig()
        self.fallback_config = fallback_config or FallbackConfig()
        self.retry_manager = RetryManager(self.retry_config)
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.error_stats = ErrorStats()
        self.response_cache: Dict[str, Dict[str, Any]] = {}
        
        # 初始化熔断器
        if self.fallback_config.enable_circuit_breaker:
            self._init_circuit_breakers()
    
    def _init_circuit_breakers(self):
        """初始化熔断器"""
        # 为每个提供商创建熔断器
        providers = ["openai", "siliconflow", "modelscope", "deepseek", "ollama"]
        for provider in providers:
            self.circuit_breakers[provider] = CircuitBreaker(
                failure_threshold=self.fallback_config.circuit_breaker_threshold,
                timeout=self.fallback_config.circuit_breaker_timeout
            )
    
    def get_circuit_breaker(self, provider: str) -> Optional[CircuitBreaker]:
        """获取指定提供商的熔断器"""
        return self.circuit_breakers.get(provider)
    
    async def execute_with_recovery(
        self,
        func: Callable,
        provider: str = "",
        fallback_func: Optional[Callable] = None,
        cache_key: Optional[str] = None,
        *args,
        **kwargs
    ) -> Any:
        """执行函数并处理错误恢复"""
        try:
            # 使用重试机制执行主要函数
            result = await self.retry_manager.execute_with_retry(func, *args, **kwargs)
            
            # 记录成功
            self._record_success(provider)
            
            # 缓存结果
            if cache_key:
                self._cache_response(cache_key, result)
            
            return result
            
        except Exception as e:
            # 记录错误
            self._record_error(e, provider)
            
            # 尝试降级处理
            return await self._handle_fallback(
                e, provider, fallback_func, cache_key, *args, **kwargs
            )
    
    async def _handle_fallback(
        self,
        error: Exception,
        provider: str,
        fallback_func: Optional[Callable],
        cache_key: Optional[str],
        *args,
        **kwargs
    ) -> Any:
        """处理降级逻辑"""
        logger.warning(f"主要服务失败，尝试降级处理: {str(error)}")
        
        # 策略1: 使用备用模型
        if (self.fallback_config.strategy == FallbackStrategy.BACKUP_MODEL and 
            fallback_func is not None):
            try:
                logger.info("尝试使用备用模型")
                if asyncio.iscoroutinefunction(fallback_func):
                    result = await fallback_func(*args, **kwargs)
                else:
                    result = fallback_func(*args, **kwargs)
                
                self.error_stats.successful_recoveries += 1
                return result
            except Exception as fallback_error:
                logger.error(f"备用模型也失败: {str(fallback_error)}")
        
        # 策略2: 使用缓存响应
        if (self.fallback_config.strategy == FallbackStrategy.CACHED_RESPONSE and 
            cache_key):
            cached_result = self._get_cached_response(cache_key)
            if cached_result is not None:
                logger.info("使用缓存响应")
                self.error_stats.successful_recoveries += 1
                return cached_result
        
        # 策略3: 简化响应
        if self.fallback_config.strategy == FallbackStrategy.SIMPLIFIED_RESPONSE:
            logger.info("返回简化响应")
            self.error_stats.successful_recoveries += 1
            return self._create_simplified_response(error)
        
        # 所有降级策略都失败，抛出原始错误
        logger.error("所有降级策略都失败")
        raise error
    
    def _record_error(self, error: Exception, provider: str = ""):
        """记录错误统计"""
        self.error_stats.total_errors += 1
        self.error_stats.consecutive_failures += 1
        self.error_stats.last_error_time = datetime.now()
        
        # 按错误类型统计
        error_type = type(error).__name__
        self.error_stats.error_by_type[error_type] = (
            self.error_stats.error_by_type.get(error_type, 0) + 1
        )
        
        # 按提供商统计
        if provider:
            self.error_stats.error_by_provider[provider] = (
                self.error_stats.error_by_provider.get(provider, 0) + 1
            )
    
    def _record_success(self, provider: str = ""):
        """记录成功统计"""
        self.error_stats.consecutive_failures = 0
    
    def _cache_response(self, cache_key: str, response: Any):
        """缓存响应"""
        self.response_cache[cache_key] = {
            'response': response,
            'timestamp': datetime.now(),
            'ttl': self.fallback_config.cache_ttl
        }
    
    def _get_cached_response(self, cache_key: str) -> Optional[Any]:
        """获取缓存响应"""
        if cache_key not in self.response_cache:
            return None
        
        cached_data = self.response_cache[cache_key]
        
        # 检查是否过期
        if (datetime.now() - cached_data['timestamp']).total_seconds() > cached_data['ttl']:
            del self.response_cache[cache_key]
            return None
        
        return cached_data['response']
    
    def _create_simplified_response(self, error: Exception) -> Dict[str, Any]:
        """创建简化响应"""
        return {
            'status': 'degraded',
            'message': '服务暂时不可用，请稍后重试',
            'error_type': type(error).__name__,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        return {
            'total_errors': self.error_stats.total_errors,
            'error_by_type': self.error_stats.error_by_type.copy(),
            'error_by_provider': self.error_stats.error_by_provider.copy(),
            'consecutive_failures': self.error_stats.consecutive_failures,
            'last_error_time': (
                self.error_stats.last_error_time.isoformat() 
                if self.error_stats.last_error_time else None
            ),
            'recovery_attempts': self.error_stats.recovery_attempts,
            'successful_recoveries': self.error_stats.successful_recoveries,
            'success_rate': (
                self.error_stats.successful_recoveries / max(self.error_stats.recovery_attempts, 1)
                if self.error_stats.recovery_attempts > 0 else 0
            )
        }
    
    def get_circuit_breaker_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取熔断器统计信息"""
        return {
            provider: breaker.get_state()
            for provider, breaker in self.circuit_breakers.items()
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self.error_stats = ErrorStats()
        self.response_cache.clear()
    
    def clear_cache(self):
        """清理缓存"""
        self.response_cache.clear()


# 全局错误恢复管理器实例
_global_recovery_manager: Optional[ErrorRecoveryManager] = None


def get_global_recovery_manager() -> ErrorRecoveryManager:
    """获取全局错误恢复管理器"""
    global _global_recovery_manager
    if _global_recovery_manager is None:
        _global_recovery_manager = ErrorRecoveryManager()
    return _global_recovery_manager


def set_global_recovery_manager(manager: ErrorRecoveryManager):
    """设置全局错误恢复管理器"""
    global _global_recovery_manager
    _global_recovery_manager = manager


# 装饰器函数
def with_error_recovery(
    provider: str = "",
    retry_config: Optional[RetryConfig] = None,
    fallback_config: Optional[FallbackConfig] = None,
    cache_key_func: Optional[Callable] = None
):
    """错误恢复装饰器"""
    # 创建共享的recovery_manager，这样缓存可以在多次调用间共享
    recovery_manager = ErrorRecoveryManager(retry_config, fallback_config)
    
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            cache_key = None
            if cache_key_func:
                cache_key = cache_key_func(*args, **kwargs)
            
            # 创建一个包装函数来传递参数
            if asyncio.iscoroutinefunction(func):
                async def wrapped_func():
                    return await func(*args, **kwargs)
            else:
                async def wrapped_func():
                    return func(*args, **kwargs)
            
            return await recovery_manager.execute_with_recovery(
                wrapped_func, provider, cache_key=cache_key
            )
        
        def sync_wrapper(*args, **kwargs):
            return asyncio.run(async_wrapper(*args, **kwargs))
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator