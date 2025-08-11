#!/usr/bin/env python3
"""
自定义异常类
"""

class RAGSystemException(Exception):
    """RAG系统基础异常类"""
    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

class AuthenticationError(RAGSystemException):
    """认证错误"""
    def __init__(self, message: str = "认证失败"):
        super().__init__(message, "AUTH_ERROR")

class AuthorizationError(RAGSystemException):
    """授权错误"""
    def __init__(self, message: str = "权限不足"):
        super().__init__(message, "AUTHZ_ERROR")

class ValidationError(RAGSystemException):
    """验证错误"""
    def __init__(self, message: str = "数据验证失败"):
        super().__init__(message, "VALIDATION_ERROR")

class NotFoundError(RAGSystemException):
    """资源不存在错误"""
    def __init__(self, message: str = "资源不存在"):
        super().__init__(message, "NOT_FOUND")

class ConflictError(RAGSystemException):
    """冲突错误"""
    def __init__(self, message: str = "资源冲突"):
        super().__init__(message, "CONFLICT")

class ConfigurationError(RAGSystemException):
    """配置错误"""
    def __init__(self, message: str = "配置错误"):
        super().__init__(message, "CONFIG_ERROR")

class ServiceUnavailableError(RAGSystemException):
    """服务不可用错误"""
    def __init__(self, message: str = "服务暂时不可用"):
        super().__init__(message, "SERVICE_UNAVAILABLE")

class RateLimitError(RAGSystemException):
    """频率限制错误"""
    def __init__(self, message: str = "请求频率过高"):
        super().__init__(message, "RATE_LIMIT")

class DatabaseError(RAGSystemException):
    """数据库错误"""
    def __init__(self, message: str = "数据库操作失败"):
        super().__init__(message, "DATABASE_ERROR")

class CacheError(RAGSystemException):
    """缓存错误"""
    def __init__(self, message: str = "缓存操作失败"):
        super().__init__(message, "CACHE_ERROR")

class EmbeddingError(RAGSystemException):
    """嵌入向量错误"""
    def __init__(self, message: str = "嵌入向量处理失败"):
        super().__init__(message, "EMBEDDING_ERROR")

class RetrievalError(RAGSystemException):
    """检索错误"""
    def __init__(self, message: str = "检索操作失败"):
        super().__init__(message, "RETRIEVAL_ERROR")

class RerankingError(RAGSystemException):
    """重排序错误"""
    def __init__(self, message: str = "重排序操作失败"):
        super().__init__(message, "RERANKING_ERROR")

# 为了向后兼容，添加一些常用的异常类别名
class RAGSystemError(RAGSystemException):
    """RAG系统错误（别名）"""
    pass

class DocumentError(RAGSystemException):
    """文档处理错误"""
    def __init__(self, message: str = "文档处理失败"):
        super().__init__(message, "DOCUMENT_ERROR")

class VectorStoreError(RAGSystemException):
    """向量存储错误"""
    def __init__(self, message: str = "向量存储操作失败"):
        super().__init__(message, "VECTOR_STORE_ERROR")

class QAError(RAGSystemException):
    """问答错误"""
    def __init__(self, message: str = "问答处理失败"):
        super().__init__(message, "QA_ERROR")

class SessionError(RAGSystemException):
    """会话错误"""
    def __init__(self, message: str = "会话处理失败"):
        super().__init__(message, "SESSION_ERROR")

class ProcessingError(RAGSystemException):
    """处理错误"""
    def __init__(self, message: str = "处理操作失败"):
        super().__init__(message, "PROCESSING_ERROR")

# 检索特定异常类
class SearchModeError(RetrievalError):
    """搜索模式错误"""
    def __init__(self, message: str = "搜索模式执行失败", search_mode: str = None):
        super().__init__(message)
        self.error_code = "SEARCH_MODE_ERROR"
        self.search_mode = search_mode
        self.severity = ErrorCode.SEVERITY_MEDIUM

class SearchFallbackError(RetrievalError):
    """搜索降级错误"""
    def __init__(self, message: str = "搜索降级失败", original_mode: str = None, fallback_mode: str = None):
        super().__init__(message)
        self.error_code = "SEARCH_FALLBACK_ERROR"
        self.original_mode = original_mode
        self.fallback_mode = fallback_mode
        self.severity = ErrorCode.SEVERITY_HIGH

class RerankingModelError(RerankingError):
    """重排序模型错误"""
    def __init__(self, message: str = "重排序模型加载或初始化失败", model_name: str = None):
        super().__init__(message)
        self.error_code = "RERANKING_MODEL_ERROR"
        self.model_name = model_name
        self.severity = ErrorCode.SEVERITY_MEDIUM

class RerankingComputeError(RerankingError):
    """重排序计算错误"""
    def __init__(self, message: str = "重排序计算失败", query: str = None, doc_count: int = None):
        super().__init__(message)
        self.error_code = "RERANKING_COMPUTE_ERROR"
        self.query = query
        self.doc_count = doc_count
        self.severity = ErrorCode.SEVERITY_LOW

class CacheConnectionError(CacheError):
    """缓存连接错误"""
    def __init__(self, message: str = "缓存服务连接失败", cache_type: str = "redis"):
        super().__init__(message)
        self.error_code = "CACHE_CONNECTION_ERROR"
        self.cache_type = cache_type
        self.severity = ErrorCode.SEVERITY_MEDIUM

class CacheOperationError(CacheError):
    """缓存操作错误"""
    def __init__(self, message: str = "缓存操作失败", operation: str = None, cache_key: str = None):
        super().__init__(message)
        self.error_code = "CACHE_OPERATION_ERROR"
        self.operation = operation
        self.cache_key = cache_key
        self.severity = ErrorCode.SEVERITY_LOW

class ConfigLoadError(ConfigurationError):
    """配置加载错误"""
    def __init__(self, message: str = "配置加载失败", config_path: str = None):
        super().__init__(message)
        self.error_code = "CONFIG_LOAD_ERROR"
        self.config_path = config_path
        self.severity = ErrorCode.SEVERITY_HIGH

class ConfigValidationError(ConfigurationError):
    """配置验证错误"""
    def __init__(self, message: str = "配置验证失败", config_field: str = None, config_value: str = None):
        super().__init__(message)
        self.error_code = "CONFIG_VALIDATION_ERROR"
        self.config_field = config_field
        self.config_value = config_value
        self.severity = ErrorCode.SEVERITY_MEDIUM

class ErrorCode:
    """错误代码常量"""
    SYSTEM_ERROR = "SYSTEM_ERROR"
    DOCUMENT_ERROR = "DOCUMENT_ERROR"
    VECTOR_STORE_ERROR = "VECTOR_STORE_ERROR"
    QA_ERROR = "QA_ERROR"
    SESSION_ERROR = "SESSION_ERROR"
    PROCESSING_ERROR = "PROCESSING_ERROR"
    
    # 检索相关错误代码
    SEARCH_MODE_ERROR = "SEARCH_MODE_ERROR"
    SEARCH_FALLBACK_ERROR = "SEARCH_FALLBACK_ERROR"
    RERANKING_MODEL_ERROR = "RERANKING_MODEL_ERROR"
    RERANKING_COMPUTE_ERROR = "RERANKING_COMPUTE_ERROR"
    CACHE_CONNECTION_ERROR = "CACHE_CONNECTION_ERROR"
    CACHE_OPERATION_ERROR = "CACHE_OPERATION_ERROR"
    CONFIG_LOAD_ERROR = "CONFIG_LOAD_ERROR"
    CONFIG_VALIDATION_ERROR = "CONFIG_VALIDATION_ERROR"
    
    # 错误严重程度
    SEVERITY_LOW = "LOW"
    SEVERITY_MEDIUM = "MEDIUM"
    SEVERITY_HIGH = "HIGH"
    SEVERITY_CRITICAL = "CRITICAL"