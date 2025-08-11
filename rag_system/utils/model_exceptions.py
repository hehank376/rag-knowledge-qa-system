"""
模型相关异常定义
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import json


class ErrorCode:
    """错误码定义"""
    # 通用错误码 (1000-1999)
    UNKNOWN_ERROR = 1000
    INVALID_PARAMETER = 1001
    MISSING_PARAMETER = 1002
    
    # 配置错误码 (2000-2999)
    CONFIG_INVALID = 2000
    CONFIG_MISSING = 2001
    API_KEY_MISSING = 2002
    API_KEY_INVALID = 2003
    MODEL_NOT_FOUND = 2004
    PROVIDER_NOT_SUPPORTED = 2005
    
    # 连接错误码 (3000-3999)
    CONNECTION_FAILED = 3000
    CONNECTION_TIMEOUT = 3001
    NETWORK_ERROR = 3002
    DNS_RESOLUTION_FAILED = 3003
    SSL_ERROR = 3004
    
    # 认证错误码 (4000-4999)
    AUTHENTICATION_FAILED = 4000
    AUTHORIZATION_FAILED = 4001
    TOKEN_EXPIRED = 4002
    INVALID_CREDENTIALS = 4003
    
    # 限流错误码 (5000-5999)
    RATE_LIMIT_EXCEEDED = 5000
    QUOTA_EXCEEDED = 5001
    CONCURRENT_LIMIT_EXCEEDED = 5002
    
    # 响应错误码 (6000-6999)
    INVALID_RESPONSE = 6000
    RESPONSE_TIMEOUT = 6001
    RESPONSE_TOO_LARGE = 6002
    RESPONSE_MALFORMED = 6003
    MODEL_OVERLOADED = 6004
    
    # 业务逻辑错误码 (7000-7999)
    DIMENSION_MISMATCH = 7000
    DATA_INVALID = 7001
    BATCH_SIZE_EXCEEDED = 7001
    TEXT_TOO_LONG = 7002
    UNSUPPORTED_OPERATION = 7003


class ModelError(Exception):
    """模型相关错误基类"""
    
    def __init__(
        self, 
        message: str, 
        provider: str = "", 
        model: str = "",
        error_code: int = ErrorCode.UNKNOWN_ERROR,
        details: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message)
        self.provider = provider
        self.model = model
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.suggestions = suggestions or []
        self.original_error = original_error
        self.timestamp = datetime.now()
        
        # 添加基础详细信息
        self.details.update({
            'provider': provider,
            'model': model,
            'error_code': error_code,
            'timestamp': self.timestamp.isoformat(),
            'error_type': self.__class__.__name__
        })
        
        if original_error:
            self.details['original_error'] = str(original_error)
            self.details['original_error_type'] = type(original_error).__name__
    
    def __str__(self):
        if self.provider and self.model:
            return f"[{self.provider}:{self.model}] {self.message} (错误码: {self.error_code})"
        elif self.provider:
            return f"[{self.provider}] {self.message} (错误码: {self.error_code})"
        else:
            return f"{self.message} (错误码: {self.error_code})"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'provider': self.provider,
            'model': self.model,
            'error_code': self.error_code,
            'details': self.details,
            'suggestions': self.suggestions,
            'timestamp': self.timestamp.isoformat()
        }
    
    def to_json(self) -> str:
        """转换为JSON格式"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    def get_user_friendly_message(self) -> str:
        """获取用户友好的错误信息"""
        base_message = self.message
        if self.suggestions:
            suggestions_text = "\n建议解决方案:\n" + "\n".join(f"- {s}" for s in self.suggestions)
            return f"{base_message}\n{suggestions_text}"
        return base_message
    
    def add_suggestion(self, suggestion: str) -> None:
        """添加修复建议"""
        if suggestion not in self.suggestions:
            self.suggestions.append(suggestion)
    
    def add_detail(self, key: str, value: Any) -> None:
        """添加详细信息"""
        self.details[key] = value


class ModelConfigError(ModelError):
    """模型配置错误"""
    
    def __init__(self, message: str, provider: str = "", model: str = "", 
                 config_field: str = "", **kwargs):
        error_code = kwargs.pop('error_code', ErrorCode.CONFIG_INVALID)
        super().__init__(
            message, provider, model, 
            error_code=error_code,
            **kwargs
        )
        self.config_field = config_field
        self.add_detail('config_field', config_field)
        
        # 添加通用配置错误建议
        self._add_config_suggestions()
    
    def _add_config_suggestions(self):
        """添加配置相关的修复建议"""
        if self.error_code == ErrorCode.API_KEY_MISSING:
            self.add_suggestion("请在配置文件中设置API密钥")
            self.add_suggestion("检查环境变量是否正确设置")
        elif self.error_code == ErrorCode.API_KEY_INVALID:
            self.add_suggestion("验证API密钥是否正确")
            self.add_suggestion("检查API密钥是否已过期")
        elif self.error_code == ErrorCode.MODEL_NOT_FOUND:
            self.add_suggestion("检查模型名称是否正确")
            self.add_suggestion("确认该模型在当前提供商下可用")
        elif self.error_code == ErrorCode.PROVIDER_NOT_SUPPORTED:
            self.add_suggestion("使用支持的提供商: openai, siliconflow, modelscope, deepseek, ollama")
            self.add_suggestion("检查提供商名称拼写是否正确")


class ModelConnectionError(ModelError):
    """模型连接错误"""
    
    def __init__(self, message: str, provider: str = "", model: str = "", 
                 endpoint: str = "", **kwargs):
        error_code = kwargs.pop('error_code', ErrorCode.CONNECTION_FAILED)
        super().__init__(
            message, provider, model,
            error_code=error_code,
            **kwargs
        )
        self.endpoint = endpoint
        self.add_detail('endpoint', endpoint)
        
        # 添加连接错误建议
        self._add_connection_suggestions()
    
    def _add_connection_suggestions(self):
        """添加连接相关的修复建议"""
        if self.error_code == ErrorCode.CONNECTION_FAILED:
            self.add_suggestion("检查网络连接是否正常")
            self.add_suggestion("验证API端点URL是否正确")
            self.add_suggestion("检查防火墙设置")
        elif self.error_code == ErrorCode.CONNECTION_TIMEOUT:
            self.add_suggestion("增加连接超时时间")
            self.add_suggestion("检查网络延迟")
            self.add_suggestion("尝试重新连接")
        elif self.error_code == ErrorCode.DNS_RESOLUTION_FAILED:
            self.add_suggestion("检查DNS设置")
            self.add_suggestion("尝试使用IP地址直接连接")
        elif self.error_code == ErrorCode.SSL_ERROR:
            self.add_suggestion("检查SSL证书")
            self.add_suggestion("更新CA证书")


class ModelResponseError(ModelError):
    """模型响应错误"""
    
    def __init__(self, message: str, provider: str = "", model: str = "",
                 status_code: Optional[int] = None, response_data: Optional[str] = None,
                 **kwargs):
        error_code = kwargs.pop('error_code', ErrorCode.INVALID_RESPONSE)
        super().__init__(
            message, provider, model,
            error_code=error_code,
            **kwargs
        )
        self.status_code = status_code
        self.response_data = response_data
        self.add_detail('status_code', status_code)
        self.add_detail('response_data', response_data)
        
        # 添加响应错误建议
        self._add_response_suggestions()
    
    def _add_response_suggestions(self):
        """添加响应相关的修复建议"""
        if self.error_code == ErrorCode.INVALID_RESPONSE:
            self.add_suggestion("检查API响应格式")
            self.add_suggestion("验证模型是否正常工作")
        elif self.error_code == ErrorCode.RESPONSE_TIMEOUT:
            self.add_suggestion("增加响应超时时间")
            self.add_suggestion("减少请求复杂度")
        elif self.error_code == ErrorCode.RESPONSE_TOO_LARGE:
            self.add_suggestion("减少max_tokens参数")
            self.add_suggestion("分批处理大量数据")
        elif self.error_code == ErrorCode.MODEL_OVERLOADED:
            self.add_suggestion("稍后重试")
            self.add_suggestion("使用其他可用模型")


class UnsupportedProviderError(ModelError):
    """不支持的提供商错误"""
    
    def __init__(self, message: str, provider: str = "", available_providers: Optional[List[str]] = None, **kwargs):
        super().__init__(
            message, provider, "",
            error_code=ErrorCode.PROVIDER_NOT_SUPPORTED,
            **kwargs
        )
        self.available_providers = available_providers or []
        self.add_detail('available_providers', self.available_providers)
        
        # 添加提供商相关建议
        self._add_provider_suggestions()
    
    def _add_provider_suggestions(self):
        """添加提供商相关的修复建议"""
        if self.available_providers:
            providers_text = ", ".join(self.available_providers)
            self.add_suggestion(f"使用支持的提供商: {providers_text}")
        self.add_suggestion("检查提供商名称拼写")
        self.add_suggestion("确认提供商插件已正确安装")


class ModelAuthenticationError(ModelError):
    """模型认证错误"""
    
    def __init__(self, message: str, provider: str = "", model: str = "", **kwargs):
        error_code = kwargs.pop('error_code', ErrorCode.AUTHENTICATION_FAILED)
        super().__init__(
            message, provider, model,
            error_code=error_code,
            **kwargs
        )
        
        # 添加认证错误建议
        self._add_auth_suggestions()
    
    def _add_auth_suggestions(self):
        """添加认证相关的修复建议"""
        if self.error_code == ErrorCode.AUTHENTICATION_FAILED:
            self.add_suggestion("检查API密钥是否正确")
            self.add_suggestion("确认API密钥未过期")
        elif self.error_code == ErrorCode.AUTHORIZATION_FAILED:
            self.add_suggestion("检查账户权限")
            self.add_suggestion("确认有访问该模型的权限")
        elif self.error_code == ErrorCode.TOKEN_EXPIRED:
            self.add_suggestion("刷新访问令牌")
            self.add_suggestion("重新获取API密钥")


class ModelRateLimitError(ModelError):
    """模型限流错误"""
    
    def __init__(self, message: str, provider: str = "", model: str = "",
                 retry_after: Optional[int] = None, **kwargs):
        error_code = kwargs.pop('error_code', ErrorCode.RATE_LIMIT_EXCEEDED)
        super().__init__(
            message, provider, model,
            error_code=error_code,
            **kwargs
        )
        self.retry_after = retry_after
        self.add_detail('retry_after', retry_after)
        
        # 添加限流错误建议
        self._add_rate_limit_suggestions()
    
    def _add_rate_limit_suggestions(self):
        """添加限流相关的修复建议"""
        if self.retry_after:
            self.add_suggestion(f"等待 {self.retry_after} 秒后重试")
        else:
            self.add_suggestion("稍后重试")
        
        if self.error_code == ErrorCode.RATE_LIMIT_EXCEEDED:
            self.add_suggestion("减少请求频率")
            self.add_suggestion("实现指数退避重试策略")
        elif self.error_code == ErrorCode.QUOTA_EXCEEDED:
            self.add_suggestion("检查账户配额")
            self.add_suggestion("升级账户套餐")
        elif self.error_code == ErrorCode.CONCURRENT_LIMIT_EXCEEDED:
            self.add_suggestion("减少并发请求数量")
            self.add_suggestion("实现请求队列")


class ModelTimeoutError(ModelError):
    """模型超时错误"""
    
    def __init__(self, message: str, provider: str = "", model: str = "",
                 timeout_duration: Optional[float] = None, **kwargs):
        super().__init__(
            message, provider, model,
            error_code=ErrorCode.RESPONSE_TIMEOUT,
            **kwargs
        )
        self.timeout_duration = timeout_duration
        self.add_detail('timeout_duration', timeout_duration)
        
        # 添加超时错误建议
        self._add_timeout_suggestions()
    
    def _add_timeout_suggestions(self):
        """添加超时相关的修复建议"""
        self.add_suggestion("增加超时时间设置")
        self.add_suggestion("检查网络连接稳定性")
        self.add_suggestion("减少请求复杂度")
        if self.timeout_duration:
            self.add_suggestion(f"当前超时设置: {self.timeout_duration}秒，建议增加到更大值")


class ModelDimensionError(ModelError):
    """模型维度错误"""
    
    def __init__(self, message: str, provider: str = "", model: str = "",
                 expected_dimension: Optional[int] = None, 
                 actual_dimension: Optional[int] = None, **kwargs):
        super().__init__(
            message, provider, model,
            error_code=ErrorCode.DIMENSION_MISMATCH,
            **kwargs
        )
        self.expected_dimension = expected_dimension
        self.actual_dimension = actual_dimension
        self.add_detail('expected_dimension', expected_dimension)
        self.add_detail('actual_dimension', actual_dimension)
        
        # 添加维度错误建议
        self._add_dimension_suggestions()
    
    def _add_dimension_suggestions(self):
        """添加维度相关的修复建议"""
        self.add_suggestion("检查嵌入模型配置")
        self.add_suggestion("确认向量存储的维度设置")
        if self.expected_dimension and self.actual_dimension:
            self.add_suggestion(f"期望维度: {self.expected_dimension}, 实际维度: {self.actual_dimension}")
        self.add_suggestion("重新初始化向量存储")


class ModelBatchSizeError(ModelError):
    """模型批处理大小错误"""
    
    def __init__(self, message: str, provider: str = "", model: str = "",
                 max_batch_size: Optional[int] = None, 
                 requested_batch_size: Optional[int] = None, **kwargs):
        super().__init__(
            message, provider, model,
            error_code=ErrorCode.BATCH_SIZE_EXCEEDED,
            **kwargs
        )
        self.max_batch_size = max_batch_size
        self.requested_batch_size = requested_batch_size
        self.add_detail('max_batch_size', max_batch_size)
        self.add_detail('requested_batch_size', requested_batch_size)
        
        # 添加批处理大小错误建议
        self._add_batch_size_suggestions()
    
    def _add_batch_size_suggestions(self):
        """添加批处理大小相关的修复建议"""
        if self.max_batch_size:
            self.add_suggestion(f"减少批处理大小到 {self.max_batch_size} 以下")
        self.add_suggestion("分批处理大量数据")
        self.add_suggestion("调整配置中的batch_size参数")


# 异常工厂类
class ModelExceptionFactory:
    """模型异常工厂类"""
    
    @staticmethod
    def create_config_error(message: str, provider: str = "", model: str = "", 
                          config_field: str = "", error_code: int = ErrorCode.CONFIG_INVALID) -> ModelConfigError:
        """创建配置错误"""
        return ModelConfigError(message, provider, model, config_field, error_code=error_code)
    
    @staticmethod
    def create_connection_error(message: str, provider: str = "", model: str = "",
                              endpoint: str = "", error_code: int = ErrorCode.CONNECTION_FAILED) -> ModelConnectionError:
        """创建连接错误"""
        return ModelConnectionError(message, provider, model, endpoint, error_code=error_code)
    
    @staticmethod
    def create_auth_error(message: str, provider: str = "", model: str = "",
                         error_code: int = ErrorCode.AUTHENTICATION_FAILED) -> ModelAuthenticationError:
        """创建认证错误"""
        return ModelAuthenticationError(message, provider, model, error_code=error_code)
    
    @staticmethod
    def create_rate_limit_error(message: str, provider: str = "", model: str = "",
                               retry_after: Optional[int] = None) -> ModelRateLimitError:
        """创建限流错误"""
        return ModelRateLimitError(message, provider, model, retry_after=retry_after)
    
    @staticmethod
    def create_dimension_error(message: str, provider: str = "", model: str = "",
                             expected_dimension: Optional[int] = None,
                             actual_dimension: Optional[int] = None) -> ModelDimensionError:
        """创建维度错误"""
        return ModelDimensionError(message, provider, model, 
                                 expected_dimension=expected_dimension,
                                 actual_dimension=actual_dimension)


# 异常处理工具函数
def handle_model_exception(func):
    """模型异常处理装饰器"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ModelError:
            # 重新抛出模型异常
            raise
        except Exception as e:
            # 将其他异常包装为模型异常
            raise ModelError(
                f"未预期的错误: {str(e)}",
                error_code=ErrorCode.UNKNOWN_ERROR,
                original_error=e
            )
    return wrapper


def format_exception_for_user(exception: ModelError) -> str:
    """格式化异常信息供用户查看"""
    return exception.get_user_friendly_message()


def log_model_exception(exception: ModelError, logger) -> None:
    """记录模型异常到日志"""
    logger.error(f"模型异常: {exception}")
    logger.debug(f"异常详情: {exception.to_json()}")