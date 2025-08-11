"""
模型异常类单元测试
"""
import pytest
import json
from datetime import datetime

from rag_system.utils.model_exceptions import (
    ErrorCode, ModelError, ModelConfigError, ModelConnectionError,
    ModelResponseError, UnsupportedProviderError, ModelAuthenticationError,
    ModelRateLimitError, ModelTimeoutError, ModelDimensionError,
    ModelBatchSizeError, ModelExceptionFactory, handle_model_exception,
    format_exception_for_user, log_model_exception
)


class TestErrorCode:
    """错误码测试"""
    
    def test_error_code_ranges(self):
        """测试错误码范围"""
        # 通用错误码 (1000-1999)
        assert 1000 <= ErrorCode.UNKNOWN_ERROR < 2000
        assert 1000 <= ErrorCode.INVALID_PARAMETER < 2000
        
        # 配置错误码 (2000-2999)
        assert 2000 <= ErrorCode.CONFIG_INVALID < 3000
        assert 2000 <= ErrorCode.API_KEY_MISSING < 3000
        
        # 连接错误码 (3000-3999)
        assert 3000 <= ErrorCode.CONNECTION_FAILED < 4000
        assert 3000 <= ErrorCode.CONNECTION_TIMEOUT < 4000
        
        # 认证错误码 (4000-4999)
        assert 4000 <= ErrorCode.AUTHENTICATION_FAILED < 5000
        assert 4000 <= ErrorCode.AUTHORIZATION_FAILED < 5000
        
        # 限流错误码 (5000-5999)
        assert 5000 <= ErrorCode.RATE_LIMIT_EXCEEDED < 6000
        assert 5000 <= ErrorCode.QUOTA_EXCEEDED < 6000
        
        # 响应错误码 (6000-6999)
        assert 6000 <= ErrorCode.INVALID_RESPONSE < 7000
        assert 6000 <= ErrorCode.RESPONSE_TIMEOUT < 7000
        
        # 业务逻辑错误码 (7000-7999)
        assert 7000 <= ErrorCode.DIMENSION_MISMATCH < 8000
        assert 7000 <= ErrorCode.BATCH_SIZE_EXCEEDED < 8000


class TestModelError:
    """模型错误基类测试"""
    
    def test_basic_model_error(self):
        """测试基础模型错误"""
        error = ModelError("测试错误", "openai", "gpt-4")
        
        assert error.message == "测试错误"
        assert error.provider == "openai"
        assert error.model == "gpt-4"
        assert error.error_code == ErrorCode.UNKNOWN_ERROR
        assert isinstance(error.timestamp, datetime)
        
        # 测试字符串表示
        assert "[openai:gpt-4]" in str(error)
        assert "测试错误" in str(error)
        assert str(error.error_code) in str(error)
    
    def test_model_error_with_details(self):
        """测试带详细信息的模型错误"""
        details = {"request_id": "12345", "status": "failed"}
        suggestions = ["检查配置", "重试请求"]
        
        error = ModelError(
            "详细错误",
            provider="siliconflow",
            model="qwen",
            error_code=ErrorCode.CONFIG_INVALID,
            details=details,
            suggestions=suggestions
        )
        
        assert error.details["request_id"] == "12345"
        assert error.details["provider"] == "siliconflow"
        assert error.suggestions == suggestions
    
    def test_model_error_serialization(self):
        """测试模型错误序列化"""
        error = ModelError("序列化测试", "openai", "gpt-4")
        
        # 测试转换为字典
        error_dict = error.to_dict()
        assert error_dict["error_type"] == "ModelError"
        assert error_dict["message"] == "序列化测试"
        assert error_dict["provider"] == "openai"
        assert error_dict["model"] == "gpt-4"
        
        # 测试转换为JSON
        error_json = error.to_json()
        parsed = json.loads(error_json)
        assert parsed["message"] == "序列化测试"
    
    def test_add_suggestion_and_detail(self):
        """测试添加建议和详细信息"""
        error = ModelError("测试错误")
        
        # 添加建议
        error.add_suggestion("建议1")
        error.add_suggestion("建议2")
        error.add_suggestion("建议1")  # 重复建议不应添加
        
        assert len(error.suggestions) == 2
        assert "建议1" in error.suggestions
        assert "建议2" in error.suggestions
        
        # 添加详细信息
        error.add_detail("key1", "value1")
        error.add_detail("key2", {"nested": "value"})
        
        assert error.details["key1"] == "value1"
        assert error.details["key2"]["nested"] == "value"
    
    def test_user_friendly_message(self):
        """测试用户友好消息"""
        error = ModelError("基础错误")
        assert error.get_user_friendly_message() == "基础错误"
        
        error.add_suggestion("建议1")
        error.add_suggestion("建议2")
        
        friendly_message = error.get_user_friendly_message()
        assert "基础错误" in friendly_message
        assert "建议解决方案:" in friendly_message
        assert "- 建议1" in friendly_message
        assert "- 建议2" in friendly_message


class TestModelConfigError:
    """模型配置错误测试"""
    
    def test_config_error_basic(self):
        """测试基础配置错误"""
        error = ModelConfigError(
            "API密钥缺失",
            provider="openai",
            model="gpt-4",
            config_field="api_key",
            error_code=ErrorCode.API_KEY_MISSING
        )
        
        assert error.config_field == "api_key"
        assert error.error_code == ErrorCode.API_KEY_MISSING
        assert error.details["config_field"] == "api_key"
        
        # 检查是否有相关建议
        suggestions_text = " ".join(error.suggestions)
        assert "API密钥" in suggestions_text or "配置文件" in suggestions_text
    
    def test_config_error_suggestions(self):
        """测试配置错误建议"""
        # API密钥缺失错误
        error = ModelConfigError("", error_code=ErrorCode.API_KEY_MISSING)
        assert any("API密钥" in s for s in error.suggestions)
        
        # 模型未找到错误
        error = ModelConfigError("", error_code=ErrorCode.MODEL_NOT_FOUND)
        assert any("模型名称" in s for s in error.suggestions)
        
        # 提供商不支持错误
        error = ModelConfigError("", error_code=ErrorCode.PROVIDER_NOT_SUPPORTED)
        assert any("提供商" in s for s in error.suggestions)


class TestModelConnectionError:
    """模型连接错误测试"""
    
    def test_connection_error_basic(self):
        """测试基础连接错误"""
        error = ModelConnectionError(
            "连接失败",
            provider="siliconflow",
            model="qwen",
            endpoint="https://api.siliconflow.cn/v1",
            error_code=ErrorCode.CONNECTION_FAILED
        )
        
        assert error.endpoint == "https://api.siliconflow.cn/v1"
        assert error.error_code == ErrorCode.CONNECTION_FAILED
        assert error.details["endpoint"] == "https://api.siliconflow.cn/v1"
    
    def test_connection_error_suggestions(self):
        """测试连接错误建议"""
        # 连接失败错误
        error = ModelConnectionError("", error_code=ErrorCode.CONNECTION_FAILED)
        assert any("网络连接" in s for s in error.suggestions)
        
        # 连接超时错误
        error = ModelConnectionError("", error_code=ErrorCode.CONNECTION_TIMEOUT)
        assert any("超时时间" in s for s in error.suggestions)
        
        # DNS解析失败错误
        error = ModelConnectionError("", error_code=ErrorCode.DNS_RESOLUTION_FAILED)
        assert any("DNS" in s for s in error.suggestions)


class TestModelResponseError:
    """模型响应错误测试"""
    
    def test_response_error_basic(self):
        """测试基础响应错误"""
        error = ModelResponseError(
            "响应格式错误",
            provider="openai",
            model="gpt-4",
            status_code=400,
            response_data='{"error": "invalid request"}',
            error_code=ErrorCode.INVALID_RESPONSE
        )
        
        assert error.status_code == 400
        assert error.response_data == '{"error": "invalid request"}'
        assert error.details["status_code"] == 400
    
    def test_response_error_suggestions(self):
        """测试响应错误建议"""
        # 无效响应错误
        error = ModelResponseError("", error_code=ErrorCode.INVALID_RESPONSE)
        assert any("响应格式" in s for s in error.suggestions)
        
        # 响应超时错误
        error = ModelResponseError("", error_code=ErrorCode.RESPONSE_TIMEOUT)
        assert any("超时时间" in s for s in error.suggestions)
        
        # 模型过载错误
        error = ModelResponseError("", error_code=ErrorCode.MODEL_OVERLOADED)
        assert any("重试" in s for s in error.suggestions)


class TestUnsupportedProviderError:
    """不支持提供商错误测试"""
    
    def test_unsupported_provider_error(self):
        """测试不支持提供商错误"""
        available_providers = ["openai", "siliconflow", "modelscope"]
        error = UnsupportedProviderError(
            "不支持的提供商",
            provider="unknown",
            available_providers=available_providers
        )
        
        assert error.available_providers == available_providers
        assert error.details["available_providers"] == available_providers
        assert error.error_code == ErrorCode.PROVIDER_NOT_SUPPORTED
        
        # 检查建议中是否包含可用提供商
        suggestions_text = " ".join(error.suggestions)
        assert "openai" in suggestions_text
        assert "siliconflow" in suggestions_text


class TestModelAuthenticationError:
    """模型认证错误测试"""
    
    def test_auth_error_suggestions(self):
        """测试认证错误建议"""
        # 认证失败错误
        error = ModelAuthenticationError("", error_code=ErrorCode.AUTHENTICATION_FAILED)
        assert any("API密钥" in s for s in error.suggestions)
        
        # 授权失败错误
        error = ModelAuthenticationError("", error_code=ErrorCode.AUTHORIZATION_FAILED)
        assert any("权限" in s for s in error.suggestions)
        
        # 令牌过期错误
        error = ModelAuthenticationError("", error_code=ErrorCode.TOKEN_EXPIRED)
        assert any("令牌" in s or "密钥" in s for s in error.suggestions)


class TestModelRateLimitError:
    """模型限流错误测试"""
    
    def test_rate_limit_error_with_retry_after(self):
        """测试带重试时间的限流错误"""
        error = ModelRateLimitError(
            "请求过于频繁",
            provider="openai",
            model="gpt-4",
            retry_after=60
        )
        
        assert error.retry_after == 60
        assert error.details["retry_after"] == 60
        
        # 检查建议中是否包含重试时间
        suggestions_text = " ".join(error.suggestions)
        assert "60 秒" in suggestions_text
    
    def test_rate_limit_error_suggestions(self):
        """测试限流错误建议"""
        # 速率限制错误
        error = ModelRateLimitError("", error_code=ErrorCode.RATE_LIMIT_EXCEEDED)
        assert any("请求频率" in s for s in error.suggestions)
        
        # 配额超限错误
        error = ModelRateLimitError("", error_code=ErrorCode.QUOTA_EXCEEDED)
        assert any("配额" in s for s in error.suggestions)
        
        # 并发限制错误
        error = ModelRateLimitError("", error_code=ErrorCode.CONCURRENT_LIMIT_EXCEEDED)
        assert any("并发" in s for s in error.suggestions)


class TestModelTimeoutError:
    """模型超时错误测试"""
    
    def test_timeout_error_with_duration(self):
        """测试带超时时长的超时错误"""
        error = ModelTimeoutError(
            "请求超时",
            provider="siliconflow",
            model="qwen",
            timeout_duration=30.0
        )
        
        assert error.timeout_duration == 30.0
        assert error.details["timeout_duration"] == 30.0
        
        # 检查建议中是否包含超时时长
        suggestions_text = " ".join(error.suggestions)
        assert "30.0秒" in suggestions_text


class TestModelDimensionError:
    """模型维度错误测试"""
    
    def test_dimension_error(self):
        """测试维度错误"""
        error = ModelDimensionError(
            "向量维度不匹配",
            provider="siliconflow",
            model="bge-large",
            expected_dimension=1024,
            actual_dimension=768
        )
        
        assert error.expected_dimension == 1024
        assert error.actual_dimension == 768
        assert error.details["expected_dimension"] == 1024
        assert error.details["actual_dimension"] == 768
        
        # 检查建议中是否包含维度信息
        suggestions_text = " ".join(error.suggestions)
        assert "1024" in suggestions_text
        assert "768" in suggestions_text


class TestModelBatchSizeError:
    """模型批处理大小错误测试"""
    
    def test_batch_size_error(self):
        """测试批处理大小错误"""
        error = ModelBatchSizeError(
            "批处理大小超限",
            provider="openai",
            model="text-embedding-ada-002",
            max_batch_size=100,
            requested_batch_size=200
        )
        
        assert error.max_batch_size == 100
        assert error.requested_batch_size == 200
        assert error.details["max_batch_size"] == 100
        assert error.details["requested_batch_size"] == 200
        
        # 检查建议中是否包含批处理大小信息
        suggestions_text = " ".join(error.suggestions)
        assert "100" in suggestions_text


class TestModelExceptionFactory:
    """模型异常工厂测试"""
    
    def test_create_config_error(self):
        """测试创建配置错误"""
        error = ModelExceptionFactory.create_config_error(
            "配置错误",
            provider="openai",
            model="gpt-4",
            config_field="api_key",
            error_code=ErrorCode.API_KEY_MISSING
        )
        
        assert isinstance(error, ModelConfigError)
        assert error.config_field == "api_key"
        assert error.error_code == ErrorCode.API_KEY_MISSING
    
    def test_create_connection_error(self):
        """测试创建连接错误"""
        error = ModelExceptionFactory.create_connection_error(
            "连接错误",
            provider="siliconflow",
            endpoint="https://api.siliconflow.cn/v1"
        )
        
        assert isinstance(error, ModelConnectionError)
        assert error.endpoint == "https://api.siliconflow.cn/v1"
    
    def test_create_dimension_error(self):
        """测试创建维度错误"""
        error = ModelExceptionFactory.create_dimension_error(
            "维度错误",
            expected_dimension=1024,
            actual_dimension=768
        )
        
        assert isinstance(error, ModelDimensionError)
        assert error.expected_dimension == 1024
        assert error.actual_dimension == 768


class TestExceptionUtilities:
    """异常工具函数测试"""
    
    def test_handle_model_exception_decorator(self):
        """测试模型异常处理装饰器"""
        
        @handle_model_exception
        def function_with_model_error():
            raise ModelConfigError("配置错误")
        
        @handle_model_exception
        def function_with_generic_error():
            raise ValueError("普通错误")
        
        # 模型异常应该直接抛出
        with pytest.raises(ModelConfigError):
            function_with_model_error()
        
        # 普通异常应该被包装为模型异常
        with pytest.raises(ModelError) as exc_info:
            function_with_generic_error()
        
        assert "未预期的错误" in str(exc_info.value)
        assert exc_info.value.error_code == ErrorCode.UNKNOWN_ERROR
    
    def test_format_exception_for_user(self):
        """测试格式化异常信息"""
        error = ModelConfigError("配置错误")
        error.add_suggestion("检查配置文件")
        
        formatted = format_exception_for_user(error)
        assert "配置错误" in formatted
        assert "建议解决方案:" in formatted
        assert "检查配置文件" in formatted
    
    def test_log_model_exception(self):
        """测试记录模型异常"""
        from unittest.mock import Mock
        
        logger = Mock()
        error = ModelError("测试错误", "openai", "gpt-4")
        
        log_model_exception(error, logger)
        
        # 验证日志记录被调用
        logger.error.assert_called_once()
        logger.debug.assert_called_once()
        
        # 验证日志内容
        error_call = logger.error.call_args[0][0]
        debug_call = logger.debug.call_args[0][0]
        
        assert "测试错误" in error_call
        assert "异常详情" in debug_call


if __name__ == "__main__":
    pytest.main([__file__, "-v"])