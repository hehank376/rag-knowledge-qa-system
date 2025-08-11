"""
异常类单元测试
测试任务9.1：统一错误处理机制
"""
import pytest
from rag_system.utils.exceptions import (
    RAGSystemError, ErrorCode, DocumentError, DocumentNotFoundError,
    DocumentUploadError, DocumentFormatError, VectorStoreError,
    VectorStoreConnectionError, VectorEmbeddingError, QAError,
    QANoRelevantContentError, QALLMError, QATimeoutError,
    ConfigurationError, ConfigNotFoundError, SessionError,
    SessionNotFoundError, SessionExpiredError, ProcessingError,
    DatabaseError, DatabaseConnectionError, ValidationError
)


class TestRAGSystemError:
    """RAG系统基础异常测试"""
    
    def test_basic_error_creation(self):
        """测试基础异常创建"""
        error = RAGSystemError("测试错误")
        
        assert str(error) == "[UNKNOWN_ERROR] 测试错误"
        assert error.message == "测试错误"
        assert error.error_code == ErrorCode.UNKNOWN_ERROR
        assert error.details == {}
        assert error.cause is None
    
    def test_error_with_code_and_details(self):
        """测试带错误代码和详情的异常"""
        details = {"key": "value", "number": 123}
        error = RAGSystemError(
            "测试错误",
            error_code=ErrorCode.VALIDATION_ERROR,
            details=details
        )
        
        assert error.error_code == ErrorCode.VALIDATION_ERROR
        assert error.details == details
        assert str(error) == "[VALIDATION_ERROR] 测试错误"
    
    def test_error_with_cause(self):
        """测试带原因的异常"""
        cause = ValueError("原始错误")
        error = RAGSystemError("包装错误", cause=cause)
        
        assert error.cause == cause
        assert error.traceback_str is not None
    
    def test_error_to_dict(self):
        """测试异常转换为字典"""
        details = {"field": "value"}
        cause = ValueError("原始错误")
        error = RAGSystemError(
            "测试错误",
            error_code=ErrorCode.VALIDATION_ERROR,
            details=details,
            cause=cause
        )
        
        error_dict = error.to_dict()
        
        assert error_dict["error_type"] == "RAGSystemError"
        assert error_dict["message"] == "测试错误"
        assert error_dict["error_code"] == "VALIDATION_ERROR"
        assert error_dict["details"] == details
        assert error_dict["cause"] == "原始错误"
        assert "traceback" in error_dict


class TestDocumentErrors:
    """文档相关异常测试"""
    
    def test_document_error_basic(self):
        """测试基础文档异常"""
        error = DocumentError("文档处理失败")
        
        assert error.error_code == ErrorCode.DOCUMENT_PROCESSING_ERROR
        assert error.message == "文档处理失败"
    
    def test_document_error_with_details(self):
        """测试带详情的文档异常"""
        error = DocumentError(
            "文档处理失败",
            document_id="doc123",
            filename="test.pdf"
        )
        
        assert error.details["document_id"] == "doc123"
        assert error.details["filename"] == "test.pdf"
    
    def test_document_not_found_error(self):
        """测试文档未找到异常"""
        error = DocumentNotFoundError("doc123")
        
        assert error.error_code == ErrorCode.DOCUMENT_NOT_FOUND
        assert "doc123" in error.message
        assert error.details["document_id"] == "doc123"
    
    def test_document_upload_error(self):
        """测试文档上传异常"""
        error = DocumentUploadError("test.pdf", "文件太大")
        
        assert error.error_code == ErrorCode.DOCUMENT_UPLOAD_ERROR
        assert "test.pdf" in error.message
        assert "文件太大" in error.message
        assert error.details["reason"] == "文件太大"
    
    def test_document_format_error(self):
        """测试文档格式异常"""
        error = DocumentFormatError("test.xyz", "PDF")
        
        assert error.error_code == ErrorCode.DOCUMENT_FORMAT_ERROR
        assert "test.xyz" in error.message
        assert "PDF" in error.message
        assert error.details["expected_format"] == "PDF"


class TestVectorStoreErrors:
    """向量存储相关异常测试"""
    
    def test_vector_store_error_basic(self):
        """测试基础向量存储异常"""
        error = VectorStoreError("向量存储操作失败")
        
        assert error.error_code == ErrorCode.VECTOR_STORE_OPERATION_ERROR
        assert error.message == "向量存储操作失败"
    
    def test_vector_store_connection_error(self):
        """测试向量存储连接异常"""
        error = VectorStoreConnectionError("chroma")
        
        assert error.error_code == ErrorCode.VECTOR_STORE_CONNECTION_ERROR
        assert "chroma" in error.message
        assert error.details["store_type"] == "chroma"
    
    def test_vector_embedding_error(self):
        """测试向量嵌入异常"""
        long_text = "这是一段很长的文本" * 20
        error = VectorEmbeddingError(long_text)
        
        assert error.error_code == ErrorCode.VECTOR_EMBEDDING_ERROR
        assert "向量嵌入处理失败" in error.message
        assert error.details["text_preview"] is not None
        assert len(error.details["text_preview"]) <= 100


class TestQAErrors:
    """问答相关异常测试"""
    
    def test_qa_error_basic(self):
        """测试基础问答异常"""
        error = QAError("问答处理失败")
        
        assert error.error_code == ErrorCode.QA_PROCESSING_ERROR
        assert error.message == "问答处理失败"
    
    def test_qa_no_relevant_content_error(self):
        """测试无相关内容异常"""
        question = "什么是人工智能？"
        error = QANoRelevantContentError(question)
        
        assert error.error_code == ErrorCode.QA_NO_RELEVANT_CONTENT
        assert question in error.message
        assert error.details["question"] == question
    
    def test_qa_llm_error(self):
        """测试LLM处理异常"""
        question = "什么是机器学习？"
        llm_error = "API调用失败"
        error = QALLMError(question, llm_error)
        
        assert error.error_code == ErrorCode.QA_LLM_ERROR
        assert llm_error in error.message
        assert error.details["question"] == question
        assert error.details["llm_error"] == llm_error
    
    def test_qa_timeout_error(self):
        """测试问答超时异常"""
        question = "复杂问题"
        timeout = 30
        error = QATimeoutError(question, timeout)
        
        assert error.error_code == ErrorCode.QA_TIMEOUT_ERROR
        assert question in error.message
        assert str(timeout) in error.message
        assert error.details["timeout_seconds"] == timeout


class TestConfigurationErrors:
    """配置相关异常测试"""
    
    def test_configuration_error_basic(self):
        """测试基础配置异常"""
        error = ConfigurationError("配置验证失败")
        
        assert error.error_code == ErrorCode.CONFIG_VALIDATION_ERROR
        assert error.message == "配置验证失败"
    
    def test_config_not_found_error(self):
        """测试配置未找到异常"""
        config_key = "database.url"
        error = ConfigNotFoundError(config_key)
        
        assert error.error_code == ErrorCode.CONFIG_NOT_FOUND
        assert config_key in error.message
        assert error.details["config_key"] == config_key


class TestSessionErrors:
    """会话相关异常测试"""
    
    def test_session_error_basic(self):
        """测试基础会话异常"""
        error = SessionError("会话创建失败")
        
        assert error.error_code == ErrorCode.SESSION_CREATION_ERROR
        assert error.message == "会话创建失败"
    
    def test_session_not_found_error(self):
        """测试会话未找到异常"""
        session_id = "session123"
        error = SessionNotFoundError(session_id)
        
        assert error.error_code == ErrorCode.SESSION_NOT_FOUND
        assert session_id in error.message
        assert error.details["session_id"] == session_id
    
    def test_session_expired_error(self):
        """测试会话过期异常"""
        session_id = "session456"
        error = SessionExpiredError(session_id)
        
        assert error.error_code == ErrorCode.SESSION_EXPIRED
        assert session_id in error.message
        assert error.details["session_id"] == session_id


class TestDatabaseErrors:
    """数据库相关异常测试"""
    
    def test_database_error_basic(self):
        """测试基础数据库异常"""
        error = DatabaseError("数据库操作失败")
        
        assert error.error_code == ErrorCode.DATABASE_OPERATION_ERROR
        assert error.message == "数据库操作失败"
    
    def test_database_connection_error(self):
        """测试数据库连接异常"""
        database_url = "postgresql://user:pass@localhost/db"
        error = DatabaseConnectionError(database_url)
        
        assert error.error_code == ErrorCode.DATABASE_CONNECTION_ERROR
        assert "数据库连接失败" in error.message
        # 确保敏感信息被隐藏
        assert "pass" not in error.message
        assert "localhost/db" in error.message


class TestValidationError:
    """验证异常测试"""
    
    def test_validation_error_basic(self):
        """测试基础验证异常"""
        error = ValidationError("字段验证失败")
        
        assert error.error_code == ErrorCode.VALIDATION_ERROR
        assert error.message == "字段验证失败"
    
    def test_validation_error_with_field(self):
        """测试带字段信息的验证异常"""
        error = ValidationError(
            "邮箱格式不正确",
            field="email",
            value="invalid-email"
        )
        
        assert error.details["field"] == "email"
        assert error.details["value"] == "invalid-email"


class TestErrorCode:
    """错误代码枚举测试"""
    
    def test_error_code_values(self):
        """测试错误代码值"""
        assert ErrorCode.UNKNOWN_ERROR.value == "UNKNOWN_ERROR"
        assert ErrorCode.DOCUMENT_NOT_FOUND.value == "DOCUMENT_NOT_FOUND"
        assert ErrorCode.QA_TIMEOUT_ERROR.value == "QA_TIMEOUT_ERROR"
    
    def test_error_code_categories(self):
        """测试错误代码分类"""
        # 文档相关错误
        document_errors = [
            ErrorCode.DOCUMENT_NOT_FOUND,
            ErrorCode.DOCUMENT_UPLOAD_ERROR,
            ErrorCode.DOCUMENT_PROCESSING_ERROR,
            ErrorCode.DOCUMENT_FORMAT_ERROR,
            ErrorCode.DOCUMENT_SIZE_ERROR
        ]
        
        for error_code in document_errors:
            assert "DOCUMENT" in error_code.value
        
        # 问答相关错误
        qa_errors = [
            ErrorCode.QA_PROCESSING_ERROR,
            ErrorCode.QA_NO_RELEVANT_CONTENT,
            ErrorCode.QA_LLM_ERROR,
            ErrorCode.QA_TIMEOUT_ERROR
        ]
        
        for error_code in qa_errors:
            assert "QA" in error_code.value


if __name__ == "__main__":
    pytest.main([__file__, "-v"])