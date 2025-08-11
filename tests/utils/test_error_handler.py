"""
错误处理中间件单元测试
测试任务9.1：统一错误处理机制
"""
import pytest
import json
import logging
from unittest.mock import Mock, patch
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

from rag_system.utils.error_handler import (
    ErrorHandler, ErrorHandlerMiddleware, create_error_response,
    handle_api_error, ErrorLogger, global_error_handler
)
from rag_system.utils.exceptions import (
    RAGSystemError, ErrorCode, DocumentNotFoundError, QATimeoutError,
    ConfigurationError, ValidationError
)


class TestErrorHandler:
    """错误处理器测试"""
    
    def setup_method(self):
        """测试前设置"""
        self.logger = Mock(spec=logging.Logger)
        self.error_handler = ErrorHandler(self.logger)
        self.mock_request = Mock(spec=Request)
        self.mock_request.method = "GET"
        self.mock_request.url = "http://test.com/api/test"
        self.mock_request.client.host = "127.0.0.1"
        self.mock_request.headers = {"user-agent": "test-client"}
    
    def test_handle_rag_system_error(self):
        """测试处理RAG系统异常"""
        error = DocumentNotFoundError("doc123")
        result = self.error_handler.handle_exception(error, self.mock_request)
        
        assert result["status_code"] == status.HTTP_404_NOT_FOUND
        assert result["response"]["success"] is False
        assert result["response"]["error"]["type"] == "DocumentNotFoundError"
        assert result["response"]["error"]["code"] == "DOCUMENT_NOT_FOUND"
        assert "doc123" in result["response"]["error"]["message"]
        assert "timestamp" in result["response"]["error"]
    
    def test_handle_http_exception(self):
        """测试处理HTTP异常"""
        error = HTTPException(status_code=400, detail="Bad Request")
        result = self.error_handler.handle_exception(error, self.mock_request)
        
        assert result["status_code"] == 400
        assert result["response"]["error"]["type"] == "HTTPException"
        assert result["response"]["error"]["code"] == "HTTP_400"
        assert result["response"]["error"]["message"] == "Bad Request"
    
    def test_handle_validation_error(self):
        """测试处理验证错误"""
        error = ValueError("Invalid input")
        result = self.error_handler.handle_exception(error, self.mock_request)
        
        assert result["status_code"] == status.HTTP_400_BAD_REQUEST
        assert result["response"]["error"]["type"] == "ValidationError"
        assert result["response"]["error"]["code"] == "VALIDATION_ERROR"
        assert "Invalid input" in result["response"]["error"]["message"]
    
    def test_handle_file_not_found_error(self):
        """测试处理文件未找到错误"""
        error = FileNotFoundError("File not found")
        result = self.error_handler.handle_exception(error, self.mock_request)
        
        assert result["status_code"] == status.HTTP_404_NOT_FOUND
        assert result["response"]["error"]["type"] == "FileNotFoundError"
        assert result["response"]["error"]["code"] == "DOCUMENT_NOT_FOUND"
    
    def test_handle_permission_error(self):
        """测试处理权限错误"""
        error = PermissionError("Access denied")
        result = self.error_handler.handle_exception(error, self.mock_request)
        
        assert result["status_code"] == status.HTTP_403_FORBIDDEN
        assert result["response"]["error"]["type"] == "PermissionError"
        assert result["response"]["error"]["code"] == "AUTHORIZATION_ERROR"
    
    def test_handle_timeout_error(self):
        """测试处理超时错误"""
        error = TimeoutError("Request timeout")
        result = self.error_handler.handle_exception(error, self.mock_request)
        
        assert result["status_code"] == status.HTTP_408_REQUEST_TIMEOUT
        assert result["response"]["error"]["type"] == "TimeoutError"
        assert result["response"]["error"]["code"] == "QA_TIMEOUT_ERROR"
    
    def test_handle_unknown_error(self):
        """测试处理未知错误"""
        error = RuntimeError("Unknown error")
        result = self.error_handler.handle_exception(error, self.mock_request)
        
        assert result["status_code"] == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert result["response"]["error"]["type"] == "InternalServerError"
        assert result["response"]["error"]["code"] == "UNKNOWN_ERROR"
        assert result["response"]["error"]["message"] == "服务器内部错误，请稍后重试"
    
    def test_error_logging(self):
        """测试错误日志记录"""
        error = DocumentNotFoundError("doc123")
        self.error_handler.handle_exception(error, self.mock_request)
        
        # 验证日志记录被调用
        assert self.logger.warning.called
        
        # 获取日志调用参数
        call_args = self.logger.warning.call_args
        assert "业务错误" in call_args[0]
        
        # 验证日志包含错误信息
        log_extra = call_args[1]["extra"]
        assert log_extra["error_type"] == "DocumentNotFoundError"
        assert log_extra["error_code"] == "DOCUMENT_NOT_FOUND"
        assert log_extra["method"] == "GET"
        assert log_extra["url"] == "http://test.com/api/test"
    
    def test_status_code_mapping(self):
        """测试错误代码到HTTP状态码的映射"""
        test_cases = [
            (ErrorCode.VALIDATION_ERROR, status.HTTP_400_BAD_REQUEST),
            (ErrorCode.AUTHENTICATION_ERROR, status.HTTP_401_UNAUTHORIZED),
            (ErrorCode.AUTHORIZATION_ERROR, status.HTTP_403_FORBIDDEN),
            (ErrorCode.DOCUMENT_NOT_FOUND, status.HTTP_404_NOT_FOUND),
            (ErrorCode.DOCUMENT_SIZE_ERROR, status.HTTP_413_REQUEST_ENTITY_TOO_LARGE),
            (ErrorCode.QA_TIMEOUT_ERROR, status.HTTP_408_REQUEST_TIMEOUT),
            (ErrorCode.RATE_LIMIT_ERROR, status.HTTP_429_TOO_MANY_REQUESTS),
            (ErrorCode.UNKNOWN_ERROR, status.HTTP_500_INTERNAL_SERVER_ERROR),
        ]
        
        for error_code, expected_status in test_cases:
            actual_status = self.error_handler._get_status_code_for_error_code(error_code)
            assert actual_status == expected_status


class TestErrorHandlerMiddleware:
    """错误处理中间件测试"""
    
    def setup_method(self):
        """测试前设置"""
        self.app = FastAPI()
        self.logger = Mock(spec=logging.Logger)
        self.app.add_middleware(ErrorHandlerMiddleware, logger=self.logger)
        
        @self.app.get("/test-success")
        async def test_success():
            return {"message": "success"}
        
        @self.app.get("/test-rag-error")
        async def test_rag_error():
            raise DocumentNotFoundError("doc123")
        
        @self.app.get("/test-http-error")
        async def test_http_error():
            raise HTTPException(status_code=403, detail="权限不足")
        
        @self.app.get("/test-unknown-error")
        async def test_unknown_error():
            raise RuntimeError("Unknown error")
        
        self.client = TestClient(self.app)
    
    def test_successful_request(self):
        """测试成功请求"""
        response = self.client.get("/test-success")
        
        assert response.status_code == 200
        assert response.json() == {"message": "success"}
    
    def test_rag_system_error_handling(self):
        """测试RAG系统异常处理"""
        response = self.client.get("/test-rag-error")
        
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert data["error"]["type"] == "DocumentNotFoundError"
        assert data["error"]["code"] == "DOCUMENT_NOT_FOUND"
        assert "doc123" in data["error"]["message"]
    
    def test_http_exception_handling(self):
        """测试HTTP异常处理"""
        response = self.client.get("/test-http-error")
        
        assert response.status_code == 403
        data = response.json()
        # FastAPI自动处理HTTPException，返回标准格式
        assert "detail" in data
        assert data["detail"] == "权限不足"
    
    def test_unknown_error_handling(self):
        """测试未知异常处理"""
        response = self.client.get("/test-unknown-error")
        
        assert response.status_code == 500
        data = response.json()
        assert data["success"] is False
        assert data["error"]["type"] == "InternalServerError"
        assert data["error"]["code"] == "UNKNOWN_ERROR"
        assert data["error"]["message"] == "服务器内部错误，请稍后重试"


class TestCreateErrorResponse:
    """创建错误响应测试"""
    
    def test_create_error_response_basic(self):
        """测试基础错误响应创建"""
        response = create_error_response(
            ErrorCode.VALIDATION_ERROR,
            "验证失败"
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        # 解析响应内容
        content = json.loads(response.body.decode())
        assert content["success"] is False
        assert content["error"]["type"] == "APIError"
        assert content["error"]["code"] == "VALIDATION_ERROR"
        assert content["error"]["message"] == "验证失败"
        assert content["error"]["details"] == {}
        assert "timestamp" in content["error"]
    
    def test_create_error_response_with_details(self):
        """测试带详情的错误响应创建"""
        details = {"field": "email", "value": "invalid"}
        response = create_error_response(
            ErrorCode.VALIDATION_ERROR,
            "邮箱格式不正确",
            details=details,
            status_code=422
        )
        
        assert response.status_code == 422
        
        content = json.loads(response.body.decode())
        assert content["error"]["details"] == details


class TestHandleApiErrorDecorator:
    """API错误处理装饰器测试"""
    
    @pytest.mark.asyncio
    async def test_successful_function(self):
        """测试成功执行的函数"""
        @handle_api_error
        async def test_func():
            return {"result": "success"}
        
        result = await test_func()
        assert result == {"result": "success"}
    
    @pytest.mark.asyncio
    async def test_function_with_exception(self):
        """测试抛出异常的函数"""
        @handle_api_error
        async def test_func():
            raise DocumentNotFoundError("doc123")
        
        result = await test_func()
        
        # 结果应该是JSONResponse对象
        assert isinstance(result, JSONResponse)
        assert result.status_code == 404
        
        # 解析响应内容
        content = json.loads(result.body.decode())
        assert content["success"] is False
        assert content["error"]["code"] == "DOCUMENT_NOT_FOUND"


class TestErrorLogger:
    """错误日志记录器测试"""
    
    def setup_method(self):
        """测试前设置"""
        with patch('logging.getLogger') as mock_get_logger:
            self.mock_logger = Mock(spec=logging.Logger)
            self.mock_logger.handlers = []  # 模拟没有处理器
            mock_get_logger.return_value = self.mock_logger
            
            self.error_logger = ErrorLogger("test_logger")
    
    def test_log_error_basic(self):
        """测试基础错误日志记录"""
        error = ValueError("Test error")
        self.error_logger.log_error(error)
        
        # 验证日志记录被调用
        assert self.mock_logger.error.called
        
        # 获取日志调用参数
        call_args = self.mock_logger.error.call_args[0][0]
        assert "ValueError" in call_args
        assert "Test error" in call_args
    
    def test_log_error_with_context(self):
        """测试带上下文的错误日志记录"""
        error = DocumentNotFoundError("doc123")
        context = {"user_id": "user456", "action": "get_document"}
        
        self.error_logger.log_error(error, context=context, level="warning")
        
        # 验证警告级别日志被调用
        assert self.mock_logger.warning.called
        
        call_args = self.mock_logger.warning.call_args[0][0]
        assert "DocumentNotFoundError" in call_args
        assert "user456" in call_args
        assert "get_document" in call_args
    
    def test_log_rag_system_error(self):
        """测试RAG系统异常日志记录"""
        error = QATimeoutError("什么是AI？", 30)
        self.error_logger.log_error(error)
        
        call_args = self.mock_logger.error.call_args[0][0]
        assert "QA_TIMEOUT_ERROR" in call_args
        assert "什么是AI？" in call_args


class TestGlobalErrorHandler:
    """全局错误处理器测试"""
    
    def test_global_error_handler_exists(self):
        """测试全局错误处理器存在"""
        assert global_error_handler is not None
        assert isinstance(global_error_handler, ErrorHandler)
    
    def test_global_error_handler_functionality(self):
        """测试全局错误处理器功能"""
        error = ValidationError("测试验证错误")
        result = global_error_handler.handle_exception(error)
        
        assert result["status_code"] == status.HTTP_400_BAD_REQUEST
        assert result["response"]["error"]["code"] == "VALIDATION_ERROR"


class TestErrorHandlerIntegration:
    """错误处理器集成测试"""
    
    def test_error_chain_handling(self):
        """测试错误链处理"""
        # 创建错误链：原始错误 -> 包装错误
        original_error = ValueError("原始验证错误")
        wrapped_error = ConfigurationError(
            "配置验证失败",
            cause=original_error
        )
        
        error_handler = ErrorHandler()
        result = error_handler.handle_exception(wrapped_error)
        
        assert result["status_code"] == status.HTTP_400_BAD_REQUEST
        assert result["response"]["error"]["type"] == "ConfigurationError"
        assert "配置验证失败" in result["response"]["error"]["message"]
        
        # 验证错误详情包含原始错误信息
        error_dict = wrapped_error.to_dict()
        assert error_dict["cause"] == "原始验证错误"
        assert error_dict["traceback"] is not None
    
    def test_multiple_error_types_handling(self):
        """测试多种错误类型处理"""
        error_handler = ErrorHandler()
        
        test_errors = [
            (DocumentNotFoundError("doc1"), 404),
            (QATimeoutError("问题", 30), 408),
            (ConfigurationError("配置错误"), 400),
            (ValidationError("验证错误"), 400),
            (RuntimeError("运行时错误"), 500)
        ]
        
        for error, expected_status in test_errors:
            result = error_handler.handle_exception(error)
            assert result["status_code"] == expected_status
            assert result["response"]["success"] is False
            assert "timestamp" in result["response"]["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])