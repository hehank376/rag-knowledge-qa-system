"""
文档模型单元测试
"""
import pytest
from datetime import datetime
from pydantic import ValidationError
import uuid

from rag_system.models.document import DocumentInfo, TextChunk, DocumentStatus


class TestDocumentInfo:
    """DocumentInfo模型测试"""

    def test_create_document_info_with_defaults(self):
        """测试使用默认值创建文档信息"""
        doc = DocumentInfo(
            filename="test.pdf",
            file_type="pdf",
            file_size=1024
        )
        
        assert doc.filename == "test.pdf"
        assert doc.file_type == "pdf"
        assert doc.file_size == 1024
        assert doc.status == DocumentStatus.PROCESSING
        assert doc.chunk_count == 0
        assert doc.error_message == ""
        assert isinstance(doc.upload_time, datetime)
        # 验证ID是有效的UUID
        uuid.UUID(doc.id)

    def test_create_document_info_with_all_fields(self):
        """测试创建包含所有字段的文档信息"""
        upload_time = datetime.now()
        doc_id = str(uuid.uuid4())
        
        doc = DocumentInfo(
            id=doc_id,
            filename="document.docx",
            file_type="docx",
            file_size=2048,
            upload_time=upload_time,
            status=DocumentStatus.READY,
            chunk_count=5,
            error_message="No error"
        )
        
        assert doc.id == doc_id
        assert doc.filename == "document.docx"
        assert doc.file_type == "docx"
        assert doc.file_size == 2048
        assert doc.upload_time == upload_time
        assert doc.status == DocumentStatus.READY
        assert doc.chunk_count == 5
        assert doc.error_message == "No error"

    def test_filename_validation(self):
        """测试文件名验证"""
        # 测试空文件名
        with pytest.raises(ValidationError) as exc_info:
            DocumentInfo(filename="", file_type="pdf", file_size=1024)
        assert "String should have at least 1 character" in str(exc_info.value)
        
        # 测试包含非法字符的文件名
        illegal_chars = ['<', '>', ':', '"', '|', '?', '*']
        for char in illegal_chars:
            with pytest.raises(ValidationError) as exc_info:
                DocumentInfo(filename=f"test{char}.pdf", file_type="pdf", file_size=1024)
            assert "文件名包含非法字符" in str(exc_info.value)
        
        # 测试文件名长度限制
        long_filename = "a" * 256
        with pytest.raises(ValidationError):
            DocumentInfo(filename=long_filename, file_type="pdf", file_size=1024)

    def test_file_type_validation(self):
        """测试文件类型验证"""
        # 测试支持的文件类型
        supported_types = ['pdf', 'txt', 'docx', 'md']
        for file_type in supported_types:
            doc = DocumentInfo(filename="test.file", file_type=file_type, file_size=1024)
            assert doc.file_type == file_type.lower()
        
        # 测试大小写转换
        doc = DocumentInfo(filename="test.PDF", file_type="PDF", file_size=1024)
        assert doc.file_type == "pdf"
        
        # 测试不支持的文件类型
        with pytest.raises(ValidationError) as exc_info:
            DocumentInfo(filename="test.exe", file_type="exe", file_size=1024)
        assert "不支持的文件类型" in str(exc_info.value)

    def test_file_size_validation(self):
        """测试文件大小验证"""
        # 测试负数文件大小
        with pytest.raises(ValidationError):
            DocumentInfo(filename="test.pdf", file_type="pdf", file_size=-1)
        
        # 测试零文件大小
        with pytest.raises(ValidationError):
            DocumentInfo(filename="test.pdf", file_type="pdf", file_size=0)
        
        # 测试正常文件大小
        doc = DocumentInfo(filename="test.pdf", file_type="pdf", file_size=1)
        assert doc.file_size == 1

    def test_chunk_count_validation(self):
        """测试文本块数量验证"""
        # 测试负数文本块数量
        with pytest.raises(ValidationError):
            DocumentInfo(filename="test.pdf", file_type="pdf", file_size=1024, chunk_count=-1)
        
        # 测试零文本块数量
        doc = DocumentInfo(filename="test.pdf", file_type="pdf", file_size=1024, chunk_count=0)
        assert doc.chunk_count == 0

    def test_json_serialization(self):
        """测试JSON序列化"""
        doc = DocumentInfo(filename="test.pdf", file_type="pdf", file_size=1024)
        json_data = doc.model_dump()
        
        assert "id" in json_data
        assert json_data["filename"] == "test.pdf"
        assert json_data["file_type"] == "pdf"
        assert json_data["file_size"] == 1024
        assert json_data["status"] == "processing"
        assert json_data["chunk_count"] == 0


class TestTextChunk:
    """TextChunk模型测试"""

    def test_create_text_chunk_with_defaults(self):
        """测试使用默认值创建文本块"""
        doc_id = str(uuid.uuid4())
        chunk = TextChunk(
            document_id=doc_id,
            content="This is a test content",
            chunk_index=0
        )
        
        assert chunk.document_id == doc_id
        assert chunk.content == "This is a test content"
        assert chunk.chunk_index == 0
        assert chunk.metadata == {}
        # 验证ID是有效的UUID
        uuid.UUID(chunk.id)

    def test_create_text_chunk_with_all_fields(self):
        """测试创建包含所有字段的文本块"""
        doc_id = str(uuid.uuid4())
        chunk_id = str(uuid.uuid4())
        metadata = {"page": 1, "section": "introduction"}
        
        chunk = TextChunk(
            id=chunk_id,
            document_id=doc_id,
            content="Complete test content",
            chunk_index=2,
            metadata=metadata
        )
        
        assert chunk.id == chunk_id
        assert chunk.document_id == doc_id
        assert chunk.content == "Complete test content"
        assert chunk.chunk_index == 2
        assert chunk.metadata == metadata

    def test_content_validation(self):
        """测试内容验证"""
        doc_id = str(uuid.uuid4())
        
        # 测试空内容
        with pytest.raises(ValidationError) as exc_info:
            TextChunk(document_id=doc_id, content="", chunk_index=0)
        assert "String should have at least 1 character" in str(exc_info.value)
        
        # 测试只有空格的内容
        with pytest.raises(ValidationError) as exc_info:
            TextChunk(document_id=doc_id, content="   ", chunk_index=0)
        assert "文本内容不能为空" in str(exc_info.value)
        
        # 测试内容长度限制
        long_content = "a" * 10001
        with pytest.raises(ValidationError) as exc_info:
            TextChunk(document_id=doc_id, content=long_content, chunk_index=0)
        assert "文本块长度不能超过10000字符" in str(exc_info.value)
        
        # 测试内容自动去除空格
        chunk = TextChunk(document_id=doc_id, content="  test content  ", chunk_index=0)
        assert chunk.content == "test content"

    def test_document_id_validation(self):
        """测试文档ID验证"""
        # 测试无效的UUID格式
        with pytest.raises(ValidationError) as exc_info:
            TextChunk(document_id="invalid-uuid", content="test", chunk_index=0)
        assert "无效的文档ID格式" in str(exc_info.value)
        
        # 测试有效的UUID格式
        valid_uuid = str(uuid.uuid4())
        chunk = TextChunk(document_id=valid_uuid, content="test", chunk_index=0)
        assert chunk.document_id == valid_uuid

    def test_chunk_index_validation(self):
        """测试文本块索引验证"""
        doc_id = str(uuid.uuid4())
        
        # 测试负数索引
        with pytest.raises(ValidationError):
            TextChunk(document_id=doc_id, content="test", chunk_index=-1)
        
        # 测试零索引
        chunk = TextChunk(document_id=doc_id, content="test", chunk_index=0)
        assert chunk.chunk_index == 0
        
        # 测试正数索引
        chunk = TextChunk(document_id=doc_id, content="test", chunk_index=5)
        assert chunk.chunk_index == 5

    def test_json_serialization(self):
        """测试JSON序列化"""
        doc_id = str(uuid.uuid4())
        metadata = {"key": "value"}
        chunk = TextChunk(
            document_id=doc_id,
            content="test content",
            chunk_index=1,
            metadata=metadata
        )
        
        json_data = chunk.model_dump()
        assert "id" in json_data
        assert json_data["document_id"] == doc_id
        assert json_data["content"] == "test content"
        assert json_data["chunk_index"] == 1
        assert json_data["metadata"] == metadata


class TestDocumentStatus:
    """DocumentStatus枚举测试"""

    def test_document_status_values(self):
        """测试文档状态枚举值"""
        assert DocumentStatus.PROCESSING == "processing"
        assert DocumentStatus.READY == "ready"
        assert DocumentStatus.ERROR == "error"

    def test_document_status_in_model(self):
        """测试在模型中使用文档状态"""
        doc = DocumentInfo(
            filename="test.pdf",
            file_type="pdf",
            file_size=1024,
            status=DocumentStatus.READY
        )
        assert doc.status == DocumentStatus.READY
        
        # 测试序列化后的值
        json_data = doc.model_dump()
        assert json_data["status"] == "ready"