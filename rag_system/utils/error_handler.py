#!/usr/bin/env python3
"""
统一错误处理机制
实现任务6.1：统一错误处理机制
"""
import traceback
from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

from .exceptions import (
    RAGSystemException, RetrievalError, RerankingError, CacheError,
    SearchModeError, SearchFallbackError, RerankingModelError, RerankingComputeError,
    CacheConnectionError, CacheOperationError, ConfigLoadError, ConfigValidationError,
    ErrorCode
)
from .logging_config import get_simple_logger as get_logger

logger = get_logger(__name__)


class ErrorSeverity(str, Enum):
    """错误严重程度枚举"""
    LOW = "LOW"           # 低级错误，不影响核心功能
    MEDIUM = "MEDIUM"     # 中级错误，影响部分功能
    HIGH = "HIGH"         # 高级错误，影响核心功能
    CRITICAL = "CRITICAL" # 严重错误，系统不可用


class ErrorCategory(str, Enum):
    """错误分类枚举"""
    SYSTEM = "SYSTEM"           # 系统级错误
    BUSINESS = "BUSINESS"       # 业务逻辑错误
    EXTERNAL = "EXTERNAL"       # 外部依赖错误
    USER_INPUT = "USER_INPUT"   # 用户输入错误
    CONFIGURATION = "CONFIGURATION"  # 配置错误


@dataclass
class ErrorContext:
    """错误上下文信息"""
    timestamp: datetime = field(default_factory=datetime.now)
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    operation: Optional[str] = None
    component: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "request_id": self.request_id,
            "user_id": self.user_id,
            "operation": self.operation,
            "component": self.component,
            "additional_data": self.additional_data
        }


@dataclass
class ErrorResponse:
    """标准化错误响应"""
    error_code: str
    message: str
    severity: ErrorSeverity
    category: ErrorCategory
    context: ErrorContext
    fallback_result: Optional[Any] = None
    suggestions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "severity": self.severity.value,
            "category": self.category.value,
            "context": self.context.to_dict(),
            "fallback_result": self.fallback_result,
            "suggestions": self.suggestions
        }


class FallbackStrategy(ABC):
    """降级策略抽象基类"""
    
    @abstractmethod
    def is_applicable(self, error: Exception, context: ErrorContext) -> bool:
        """判断策略是否适用于当前错误"""
        pass
    
    @abstractmethod
    async def execute(self, original_request: Dict[str, Any], error: Exception, context: ErrorContext) -> Any:
        """执行降级策略"""
        pass
    
    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """策略名称"""
        pass


class SearchModeFallbackStrategy(FallbackStrategy):
    """搜索模式降级策略"""
    
    def is_applicable(self, error: Exception, context: ErrorContext) -> bool:
        """适用于搜索模式错误"""
        return isinstance(error, (SearchModeError, SearchFallbackError))
    
    async def execute(self, original_request: Dict[str, Any], error: Exception, context: ErrorContext) -> Any:
        """降级到语义搜索"""
        from ..services.enhanced_retrieval_service import EnhancedRetrievalService
        
        logger.warning(f"搜索模式降级: {error}, 降级到语义搜索")
        
        # 修改请求配置，使用语义搜索
        fallback_config = original_request.get('config', {}).copy()
        fallback_config['search_mode'] = 'semantic'
        
        # 执行降级搜索
        retrieval_service = original_request.get('retrieval_service')
        if retrieval_service:
            return await retrieval_service._semantic_search(
                original_request.get('query', ''),
                fallback_config,
                **original_request.get('kwargs', {})
            )
        
        return []
    
    @property
    def strategy_name(self) -> str:
        return "search_mode_fallback"


class RerankingFallbackStrategy(FallbackStrategy):
    """重排序降级策略"""
    
    def is_applicable(self, error: Exception, context: ErrorContext) -> bool:
        """适用于重排序错误"""
        return isinstance(error, (RerankingModelError, RerankingComputeError))
    
    async def execute(self, original_request: Dict[str, Any], error: Exception, context: ErrorContext) -> Any:
        """跳过重排序，返回原始结果"""
        logger.warning(f"重排序降级: {error}, 跳过重排序")
        
        # 返回原始检索结果
        original_results = original_request.get('original_results', [])
        return original_results
    
    @property
    def strategy_name(self) -> str:
        return "reranking_fallback"


class CacheFallbackStrategy(FallbackStrategy):
    """缓存降级策略"""
    
    def is_applicable(self, error: Exception, context: ErrorContext) -> bool:
        """适用于缓存错误"""
        return isinstance(error, (CacheConnectionError, CacheOperationError))
    
    async def execute(self, original_request: Dict[str, Any], error: Exception, context: ErrorContext) -> Any:
        """跳过缓存，直接执行检索"""
        logger.warning(f"缓存降级: {error}, 跳过缓存直接检索")
        
        # 执行直接检索
        retrieval_service = original_request.get('retrieval_service')
        if retrieval_service:
            return await retrieval_service.search_without_cache(
                original_request.get('query', ''),
                original_request.get('config', {}),
                **original_request.get('kwargs', {})
            )
        
        return []
    
    @property
    def strategy_name(self) -> str:
        return "cache_fallback"


class ErrorHandler:
    """统一错误处理中心"""
    
    def __init__(self):
        self.fallback_strategies: List[FallbackStrategy] = [
            SearchModeFallbackStrategy(),
            RerankingFallbackStrategy(),
            CacheFallbackStrategy()
        ]
        self.error_monitors: List[Callable] = []
        self.error_statistics: Dict[str, int] = {}
        
    def register_fallback_strategy(self, strategy: FallbackStrategy) -> None:
        """注册降级策略"""
        self.fallback_strategies.append(strategy)
        logger.info(f"注册降级策略: {strategy.strategy_name}")
    
    def register_error_monitor(self, monitor: Callable) -> None:
        """注册错误监控器"""
        self.error_monitors.append(monitor)
        logger.info("注册错误监控器")
    
    async def handle_error(
        self, 
        error: Exception, 
        context: ErrorContext,
        original_request: Optional[Dict[str, Any]] = None,
        enable_fallback: bool = True
    ) -> ErrorResponse:
        """处理错误的主要方法"""
        
        # 分类和分析错误
        error_info = self._analyze_error(error)
        
        # 记录错误统计
        self._record_error_statistics(error_info['error_code'])
        
        # 记录详细错误日志
        self._log_error_with_context(error, context, error_info)
        
        # 通知错误监控器
        await self._notify_error_monitors(error, context, error_info)
        
        # 尝试执行降级策略
        fallback_result = None
        if enable_fallback and original_request:
            fallback_result = await self._execute_fallback(error, context, original_request)
        
        # 生成建议
        suggestions = self._generate_suggestions(error, context)
        
        # 构建错误响应
        error_response = ErrorResponse(
            error_code=error_info['error_code'],
            message=error_info['message'],
            severity=error_info['severity'],
            category=error_info['category'],
            context=context,
            fallback_result=fallback_result,
            suggestions=suggestions
        )
        
        return error_response
    
    def _analyze_error(self, error: Exception) -> Dict[str, Any]:
        """分析错误，提取错误信息"""
        error_info = {
            'error_code': 'UNKNOWN_ERROR',
            'message': str(error),
            'severity': ErrorSeverity.MEDIUM,
            'category': ErrorCategory.SYSTEM
        }
        
        if isinstance(error, RAGSystemException):
            error_info['error_code'] = error.error_code
            error_info['message'] = error.message
            
            # 根据异常类型确定严重程度
            if hasattr(error, 'severity'):
                error_info['severity'] = ErrorSeverity(error.severity)
            else:
                error_info['severity'] = self._determine_severity(error)
            
            # 根据异常类型确定分类
            error_info['category'] = self._determine_category(error)
        
        return error_info
    
    def _determine_severity(self, error: Exception) -> ErrorSeverity:
        """确定错误严重程度"""
        if isinstance(error, (SearchFallbackError, ConfigLoadError)):
            return ErrorSeverity.HIGH
        elif isinstance(error, (SearchModeError, RerankingModelError, ConfigValidationError)):
            return ErrorSeverity.MEDIUM
        elif isinstance(error, (RerankingComputeError, CacheOperationError)):
            return ErrorSeverity.LOW
        else:
            return ErrorSeverity.MEDIUM
    
    def _determine_category(self, error: Exception) -> ErrorCategory:
        """确定错误分类"""
        if isinstance(error, (CacheConnectionError, CacheOperationError)):
            return ErrorCategory.EXTERNAL
        elif isinstance(error, (ConfigLoadError, ConfigValidationError)):
            return ErrorCategory.CONFIGURATION
        elif isinstance(error, (SearchModeError, RerankingError)):
            return ErrorCategory.BUSINESS
        else:
            return ErrorCategory.SYSTEM
    
    def _record_error_statistics(self, error_code: str) -> None:
        """记录错误统计"""
        self.error_statistics[error_code] = self.error_statistics.get(error_code, 0) + 1
    
    def _log_error_with_context(self, error: Exception, context: ErrorContext, error_info: Dict[str, Any]) -> None:
        """记录带上下文的错误日志"""
        log_data = {
            'error_code': error_info['error_code'],
            'error_message': error_info['message'],
            'severity': error_info['severity'].value,
            'category': error_info['category'].value,
            'context': context.to_dict(),
            'traceback': traceback.format_exc()
        }
        
        # 根据严重程度选择日志级别
        if error_info['severity'] == ErrorSeverity.CRITICAL:
            logger.critical(f"严重错误: {error}", extra=log_data)
        elif error_info['severity'] == ErrorSeverity.HIGH:
            logger.error(f"高级错误: {error}", extra=log_data)
        elif error_info['severity'] == ErrorSeverity.MEDIUM:
            logger.warning(f"中级错误: {error}", extra=log_data)
        else:
            logger.info(f"低级错误: {error}", extra=log_data)
    
    async def _notify_error_monitors(self, error: Exception, context: ErrorContext, error_info: Dict[str, Any]) -> None:
        """通知错误监控器"""
        import asyncio
        
        for monitor in self.error_monitors:
            try:
                if asyncio.iscoroutinefunction(monitor):
                    await monitor(error, context, error_info)
                else:
                    monitor(error, context, error_info)
            except Exception as monitor_error:
                logger.error(f"错误监控器执行失败: {monitor_error}")
    
    async def _execute_fallback(self, error: Exception, context: ErrorContext, original_request: Dict[str, Any]) -> Optional[Any]:
        """执行降级策略"""
        for strategy in self.fallback_strategies:
            try:
                if strategy.is_applicable(error, context):
                    logger.info(f"执行降级策略: {strategy.strategy_name}")
                    result = await strategy.execute(original_request, error, context)
                    logger.info(f"降级策略执行成功: {strategy.strategy_name}")
                    return result
            except Exception as fallback_error:
                logger.error(f"降级策略执行失败: {strategy.strategy_name}, 错误: {fallback_error}")
        
        return None
    
    def _generate_suggestions(self, error: Exception, context: ErrorContext) -> List[str]:
        """生成错误处理建议"""
        suggestions = []
        
        if isinstance(error, SearchModeError):
            suggestions.extend([
                "检查搜索模式配置是否正确",
                "尝试使用语义搜索模式",
                "检查向量数据库连接状态"
            ])
        elif isinstance(error, RerankingModelError):
            suggestions.extend([
                "检查重排序模型是否正确安装",
                "尝试重新加载重排序模型",
                "考虑禁用重排序功能"
            ])
        elif isinstance(error, CacheConnectionError):
            suggestions.extend([
                "检查Redis服务是否正常运行",
                "验证缓存连接配置",
                "考虑禁用缓存功能"
            ])
        elif isinstance(error, ConfigLoadError):
            suggestions.extend([
                "检查配置文件是否存在",
                "验证配置文件格式",
                "使用默认配置重新启动"
            ])
        
        return suggestions
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        total_errors = sum(self.error_statistics.values())
        return {
            'total_errors': total_errors,
            'error_counts': self.error_statistics.copy(),
            'error_rates': {
                code: count / total_errors if total_errors > 0 else 0
                for code, count in self.error_statistics.items()
            }
        }
    
    def reset_statistics(self) -> None:
        """重置错误统计"""
        self.error_statistics.clear()
        logger.info("错误统计已重置")


# 全局错误处理器实例
global_error_handler = ErrorHandler()


# 便捷函数
async def handle_error(
    error: Exception,
    context: Optional[ErrorContext] = None,
    original_request: Optional[Dict[str, Any]] = None,
    enable_fallback: bool = True
) -> ErrorResponse:
    """处理错误的便捷函数"""
    if context is None:
        context = ErrorContext()
    
    return await global_error_handler.handle_error(
        error=error,
        context=context,
        original_request=original_request,
        enable_fallback=enable_fallback
    )


def create_error_context(
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    operation: Optional[str] = None,
    component: Optional[str] = None,
    **additional_data
) -> ErrorContext:
    """创建错误上下文的便捷函数"""
    return ErrorContext(
        request_id=request_id,
        user_id=user_id,
        operation=operation,
        component=component,
        additional_data=additional_data
    )


# 错误处理装饰器
def handle_errors(
    component: str = None,
    operation: str = None,
    enable_fallback: bool = True,
    reraise: bool = False
):
    """错误处理装饰器"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            context = create_error_context(
                operation=operation or func.__name__,
                component=component or func.__module__
            )
            
            try:
                return await func(*args, **kwargs)
            except Exception as error:
                error_response = await handle_error(
                    error=error,
                    context=context,
                    enable_fallback=enable_fallback
                )
                
                if reraise:
                    raise error
                
                # 如果有降级结果，返回降级结果
                if error_response.fallback_result is not None:
                    return error_response.fallback_result
                
                # 否则抛出原始错误
                raise error
        
        def sync_wrapper(*args, **kwargs):
            import asyncio
            return asyncio.run(async_wrapper(*args, **kwargs))
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator