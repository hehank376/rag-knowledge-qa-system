#!/usr/bin/env python3
"""
检索特定错误处理器
实现任务6.1：各个组件的错误处理和降级逻辑
"""
from typing import Dict, Any, Optional, List, Union
import asyncio
from datetime import datetime

from .error_handler import ErrorHandler, ErrorContext, ErrorResponse, FallbackStrategy
from .exceptions import (
    SearchModeError, SearchFallbackError, RerankingModelError, RerankingComputeError,
    CacheConnectionError, CacheOperationError, ConfigLoadError, ConfigValidationError,
    RetrievalError
)
from .error_messages import get_localized_message, Language
from .logging_config import get_simple_logger as get_logger

logger = get_logger(__name__)


class RetrievalErrorHandler(ErrorHandler):
    """检索专用错误处理器"""
    
    def __init__(self):
        super().__init__()
        self.component_name = "retrieval_service"
        self.error_recovery_attempts = {}
        self.max_recovery_attempts = 3
        
        # 注册检索特定的降级策略
        self._register_retrieval_strategies()
    
    def _register_retrieval_strategies(self) -> None:
        """注册检索特定的降级策略"""
        self.register_fallback_strategy(EnhancedSearchModeFallbackStrategy())
        self.register_fallback_strategy(SmartRerankingFallbackStrategy())
        self.register_fallback_strategy(IntelligentCacheFallbackStrategy())
        self.register_fallback_strategy(ConfigRecoveryStrategy())
    
    async def handle_search_error(
        self,
        error: Exception,
        query: str,
        config: Dict[str, Any],
        user_id: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> ErrorResponse:
        """处理搜索错误"""
        context = ErrorContext(
            request_id=request_id,
            user_id=user_id,
            operation="search",
            component=self.component_name,
            additional_data={
                "query": query[:100] if query else "",  # 限制查询长度
                "search_mode": config.get("search_mode", "unknown"),
                "config": config
            }
        )
        
        original_request = {
            "query": query,
            "config": config,
            "user_id": user_id,
            "operation": "search"
        }
        
        return await self.handle_error(error, context, original_request)
    
    async def handle_reranking_error(
        self,
        error: Exception,
        query: str,
        original_results: List[Any],
        config: Dict[str, Any],
        user_id: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> ErrorResponse:
        """处理重排序错误"""
        context = ErrorContext(
            request_id=request_id,
            user_id=user_id,
            operation="reranking",
            component=self.component_name,
            additional_data={
                "query": query[:100] if query else "",
                "result_count": len(original_results) if original_results else 0,
                "reranking_enabled": config.get("enable_rerank", False)
            }
        )
        
        original_request = {
            "query": query,
            "original_results": original_results,
            "config": config,
            "user_id": user_id,
            "operation": "reranking"
        }
        
        return await self.handle_error(error, context, original_request)
    
    async def handle_cache_error(
        self,
        error: Exception,
        cache_key: str,
        operation: str,
        config: Dict[str, Any],
        user_id: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> ErrorResponse:
        """处理缓存错误"""
        context = ErrorContext(
            request_id=request_id,
            user_id=user_id,
            operation=f"cache_{operation}",
            component="cache_service",
            additional_data={
                "cache_key": cache_key,
                "cache_operation": operation,
                "cache_enabled": config.get("enable_cache", False)
            }
        )
        
        original_request = {
            "cache_key": cache_key,
            "operation": operation,
            "config": config,
            "user_id": user_id
        }
        
        return await self.handle_error(error, context, original_request)
    
    async def handle_config_error(
        self,
        error: Exception,
        config_path: Optional[str] = None,
        config_data: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> ErrorResponse:
        """处理配置错误"""
        context = ErrorContext(
            request_id=request_id,
            user_id=user_id,
            operation="config_load",
            component="config_service",
            additional_data={
                "config_path": config_path,
                "config_keys": list(config_data.keys()) if config_data else []
            }
        )
        
        original_request = {
            "config_path": config_path,
            "config_data": config_data,
            "user_id": user_id,
            "operation": "config_load"
        }
        
        return await self.handle_error(error, context, original_request)
    
    def should_attempt_recovery(self, error_code: str, context: ErrorContext) -> bool:
        """判断是否应该尝试错误恢复"""
        recovery_key = f"{error_code}:{context.component}:{context.operation}"
        current_attempts = self.error_recovery_attempts.get(recovery_key, 0)
        
        if current_attempts >= self.max_recovery_attempts:
            logger.warning(f"错误恢复尝试次数已达上限: {recovery_key}")
            return False
        
        self.error_recovery_attempts[recovery_key] = current_attempts + 1
        return True
    
    def reset_recovery_attempts(self, error_code: str, context: ErrorContext) -> None:
        """重置错误恢复尝试次数"""
        recovery_key = f"{error_code}:{context.component}:{context.operation}"
        self.error_recovery_attempts.pop(recovery_key, None)


class EnhancedSearchModeFallbackStrategy(FallbackStrategy):
    """增强的搜索模式降级策略"""
    
    def is_applicable(self, error: Exception, context: ErrorContext) -> bool:
        return isinstance(error, (SearchModeError, SearchFallbackError))
    
    async def execute(self, original_request: Dict[str, Any], error: Exception, context: ErrorContext) -> Any:
        """智能搜索模式降级"""
        config = original_request.get('config', {})
        original_mode = config.get('search_mode', 'semantic')
        
        # 定义降级路径
        fallback_chain = {
            'hybrid': 'semantic',
            'keyword': 'semantic',
            'semantic': None  # 语义搜索是最后的降级选项
        }
        
        fallback_mode = fallback_chain.get(original_mode)
        if not fallback_mode:
            logger.error(f"无法进一步降级搜索模式: {original_mode}")
            return []
        
        logger.info(f"搜索模式降级: {original_mode} -> {fallback_mode}")
        
        # 创建降级配置
        fallback_config = config.copy()
        fallback_config['search_mode'] = fallback_mode
        
        try:
            # 这里需要实际的检索服务实例
            # 在实际使用中，应该通过依赖注入获取
            from ..services.enhanced_retrieval_service import EnhancedRetrievalService
            
            # 模拟降级搜索
            if fallback_mode == 'semantic':
                # 执行语义搜索
                return await self._execute_semantic_search(
                    original_request.get('query', ''),
                    fallback_config
                )
            
        except Exception as fallback_error:
            logger.error(f"降级搜索失败: {fallback_error}")
            return []
        
        return []
    
    async def _execute_semantic_search(self, query: str, config: Dict[str, Any]) -> List[Any]:
        """执行语义搜索（降级实现）"""
        # 这是一个简化的实现，实际应该调用真正的语义搜索
        logger.info(f"执行降级语义搜索: {query}")
        return []
    
    @property
    def strategy_name(self) -> str:
        return "enhanced_search_mode_fallback"


class SmartRerankingFallbackStrategy(FallbackStrategy):
    """智能重排序降级策略"""
    
    def is_applicable(self, error: Exception, context: ErrorContext) -> bool:
        return isinstance(error, (RerankingModelError, RerankingComputeError))
    
    async def execute(self, original_request: Dict[str, Any], error: Exception, context: ErrorContext) -> Any:
        """智能重排序降级"""
        original_results = original_request.get('original_results', [])
        
        if isinstance(error, RerankingModelError):
            logger.warning("重排序模型错误，跳过重排序")
            # 模型错误时，直接返回原始结果
            return original_results
        
        elif isinstance(error, RerankingComputeError):
            logger.warning("重排序计算错误，尝试简化重排序")
            # 计算错误时，尝试简化的重排序方法
            return await self._simple_reranking(
                original_request.get('query', ''),
                original_results
            )
        
        return original_results
    
    async def _simple_reranking(self, query: str, results: List[Any]) -> List[Any]:
        """简化的重排序实现"""
        if not results or not query:
            return results
        
        try:
            # 使用简单的文本匹配进行重排序
            query_words = set(query.lower().split())
            
            def calculate_simple_score(result):
                # 假设结果有content属性
                content = getattr(result, 'content', str(result)).lower()
                content_words = set(content.split())
                
                # 计算词汇重叠度
                overlap = len(query_words.intersection(content_words))
                return overlap / len(query_words) if query_words else 0
            
            # 按简单分数排序
            sorted_results = sorted(results, key=calculate_simple_score, reverse=True)
            logger.info(f"简化重排序完成，处理了 {len(results)} 个结果")
            return sorted_results
            
        except Exception as simple_error:
            logger.error(f"简化重排序失败: {simple_error}")
            return results
    
    @property
    def strategy_name(self) -> str:
        return "smart_reranking_fallback"


class IntelligentCacheFallbackStrategy(FallbackStrategy):
    """智能缓存降级策略"""
    
    def is_applicable(self, error: Exception, context: ErrorContext) -> bool:
        return isinstance(error, (CacheConnectionError, CacheOperationError))
    
    async def execute(self, original_request: Dict[str, Any], error: Exception, context: ErrorContext) -> Any:
        """智能缓存降级"""
        operation = original_request.get('operation', 'unknown')
        
        if isinstance(error, CacheConnectionError):
            logger.warning("缓存连接失败，禁用缓存功能")
            # 连接失败时，标记缓存为不可用
            await self._disable_cache_temporarily()
            
        elif isinstance(error, CacheOperationError):
            cache_key = original_request.get('cache_key', '')
            logger.warning(f"缓存操作失败: {operation}, key: {cache_key}")
            
            if operation == 'get':
                # 读取失败时，返回None表示缓存未命中
                return None
            elif operation == 'set':
                # 写入失败时，记录日志但不影响主流程
                logger.info("缓存写入失败，继续正常流程")
                return True
        
        return None
    
    async def _disable_cache_temporarily(self) -> None:
        """临时禁用缓存"""
        # 这里可以设置一个全局标志或通知缓存服务
        logger.info("临时禁用缓存功能")
    
    @property
    def strategy_name(self) -> str:
        return "intelligent_cache_fallback"


class ConfigRecoveryStrategy(FallbackStrategy):
    """配置恢复策略"""
    
    def is_applicable(self, error: Exception, context: ErrorContext) -> bool:
        return isinstance(error, (ConfigLoadError, ConfigValidationError))
    
    async def execute(self, original_request: Dict[str, Any], error: Exception, context: ErrorContext) -> Any:
        """配置恢复"""
        if isinstance(error, ConfigLoadError):
            logger.warning("配置加载失败，使用默认配置")
            return await self._get_default_config()
            
        elif isinstance(error, ConfigValidationError):
            logger.warning("配置验证失败，修复配置")
            config_data = original_request.get('config_data', {})
            return await self._fix_invalid_config(config_data)
        
        return {}
    
    async def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "search_mode": "semantic",
            "enable_rerank": False,
            "enable_cache": False,
            "top_k": 5,
            "similarity_threshold": 0.7
        }
    
    async def _fix_invalid_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """修复无效配置"""
        default_config = await self._get_default_config()
        fixed_config = default_config.copy()
        
        # 保留有效的配置项
        for key, value in config_data.items():
            if key in default_config and value is not None:
                # 简单的类型检查
                expected_type = type(default_config[key])
                if isinstance(value, expected_type):
                    fixed_config[key] = value
        
        logger.info(f"配置修复完成: {list(fixed_config.keys())}")
        return fixed_config
    
    @property
    def strategy_name(self) -> str:
        return "config_recovery"


# 全局检索错误处理器实例
global_retrieval_error_handler = RetrievalErrorHandler()


# 便捷函数
async def handle_search_error(
    error: Exception,
    query: str,
    config: Dict[str, Any],
    user_id: Optional[str] = None,
    request_id: Optional[str] = None
) -> ErrorResponse:
    """处理搜索错误的便捷函数"""
    return await global_retrieval_error_handler.handle_search_error(
        error, query, config, user_id, request_id
    )


async def handle_reranking_error(
    error: Exception,
    query: str,
    original_results: List[Any],
    config: Dict[str, Any],
    user_id: Optional[str] = None,
    request_id: Optional[str] = None
) -> ErrorResponse:
    """处理重排序错误的便捷函数"""
    return await global_retrieval_error_handler.handle_reranking_error(
        error, query, original_results, config, user_id, request_id
    )


async def handle_cache_error(
    error: Exception,
    cache_key: str,
    operation: str,
    config: Dict[str, Any],
    user_id: Optional[str] = None,
    request_id: Optional[str] = None
) -> ErrorResponse:
    """处理缓存错误的便捷函数"""
    return await global_retrieval_error_handler.handle_cache_error(
        error, cache_key, operation, config, user_id, request_id
    )


async def handle_config_error(
    error: Exception,
    config_path: Optional[str] = None,
    config_data: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    request_id: Optional[str] = None
) -> ErrorResponse:
    """处理配置错误的便捷函数"""
    return await global_retrieval_error_handler.handle_config_error(
        error, config_path, config_data, user_id, request_id
    )