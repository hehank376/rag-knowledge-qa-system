"""
文档处理器测试
"""
import pytest
import pytest_asyncio
import tempfile
import os
import uuid
from pathlib import Path

from rag_system.services.document_processor import DocumentProcessor, ProcessResult
from rag_system.models.document import TextChunk
from rag_system.models.vector import Vector
from rag_system.utils.exceptions import DocumentError, ProcessingError


@pytest_asyncio.fixture
async def document_processor():
    """文档处理器fixture"""
    config = {
        'chunk_size': 500,
        'chunk_overlap': 100,
        'embedding_provider': 'mock',
        'embedding_model': 'test-model',
        'embedding_dimensions': 384
    }
    
    processor = DocumentProcessor(config)
    await processor.initialize()
    
    yield processor
    
    await processor.cleanup()


class TestDocumentProcessor:
    """文档处理器测试"""
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """测试初始化"""
        processor = DocumentProcessor()
        await processor.initialize()
        
        # 验证支持的格式
        supported_formats = processor.get_supported_formats()
        assert '.txt' in supported_formats
        assert '.md' in supported_formats
        
        await processor.cleanup()
    
    def test_extract_text_txt(self, document_processor):
        """测试提取TXT文本"""
        test_content = "这是一个测试文档\n包含多行内容\n用于测试文本提取功能"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(test_content)
            temp_path = f.name
        
        try:
            result = document_processor.extract_text(temp_path)
            assert result == test_content
        finally:
            os.unlink(temp_path)
    
    def test_extract_text_markdown(self, document_processor):
        """测试提取Markdown文本"""
        markdown_content = """# 测试文档

这是一个**测试**文档。

## 子标题

- 列表项1
- 列表项2

[链接](http://example.com)
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(markdown_content)
            temp_path = f.name
        
        try:
            result = document_processor.extract_text(temp_path)
            
            # 验证Markdown格式被清理
            assert "测试文档" in result
            assert "测试" in result  # 粗体标记应该被移除
            assert "列表项1" in result
            assert "链接" in result
            assert "# 测试文档" not in result  # 标题标记应该被移除
            
        finally:
            os.unlink(temp_path)
    
    def test_extract_text_nonexistent_file(self, document_processor):
        """测试提取不存在的文件"""
        with pytest.raises(DocumentError) as exc_info:
            document_processor.extract_text("nonexistent.txt")
        assert "文件不存在" in str(exc_info.value)
    
    def test_extract_text_unsupported_format(self, document_processor):
        """测试提取不支持的文件格式"""
        with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as f:
            temp_path = f.name
        
        try:
            with pytest.raises(DocumentError) as exc_info:
                document_processor.extract_text(temp_path)
            assert "不支持的文件格式" in str(exc_info.value)
        finally:
            os.unlink(temp_path)
    
    def test_extract_text_empty_file(self, document_processor):
        """测试提取空文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("")  # 空内容
            temp_path = f.name
        
        try:
            with pytest.raises(DocumentError) as exc_info:
                document_processor.extract_text(temp_path)
            assert "没有可提取的文本内容" in str(exc_info.value)
        finally:
            os.unlink(temp_path)
    
    def test_split_text_simple(self, document_processor):
        """测试简单文本分割"""
        doc_id = str(uuid.uuid4())
        text = "这是第一段。\n\n这是第二段。\n\n这是第三段。"
        
        chunks = document_processor.split_text(text, doc_id)
        
        assert len(chunks) > 0
        assert all(isinstance(chunk, TextChunk) for chunk in chunks)
        assert all(chunk.document_id == doc_id for chunk in chunks)
        
        # 验证块索引
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i
            assert chunk.id is not None
            assert len(chunk.content) > 0
    
    def test_split_text_long_content(self, document_processor):
        """测试长文本分割"""
        doc_id = str(uuid.uuid4())
        
        # 创建超过chunk_size的长文本
        long_paragraph = "这是一个很长的段落。" * 50  # 约500字符
        text = f"{long_paragraph}\n\n{long_paragraph}\n\n{long_paragraph}"
        
        chunks = document_processor.split_text(text, doc_id)
        
        assert len(chunks) > 1  # 应该被分割成多个块
        
        # 验证每个块的大小
        for chunk in chunks:
            assert len(chunk.content) <= document_processor._chunk_size + document_processor._chunk_overlap
    
    def test_split_text_empty(self, document_processor):
        """测试分割空文本"""
        doc_id = str(uuid.uuid4())
        
        with pytest.raises(ProcessingError) as exc_info:
            document_processor.split_text("", doc_id)
        assert "文本内容为空" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_vectorize_chunks(self, document_processor):
        """测试向量化文本块"""
        doc_id = str(uuid.uuid4())
        
        chunks = [
            TextChunk(
                id=str(uuid.uuid4()),
                document_id=doc_id,
                content="这是第一个文本块",
                chunk_index=0,
                metadata={}
            ),
            TextChunk(
                id=str(uuid.uuid4()),
                document_id=doc_id,
                content="这是第二个文本块",
                chunk_index=1,
                metadata={}
            )
        ]
        
        vectors = await document_processor.vectorize_chunks(chunks)
        
        assert len(vectors) == len(chunks)
        assert all(isinstance(vector, Vector) for vector in vectors)
        
        for i, vector in enumerate(vectors):
            assert vector.document_id == doc_id
            assert vector.chunk_id == chunks[i].id
            assert len(vector.embedding) == 384  # 配置的维度
            assert isinstance(vector.embedding, list)
            assert all(isinstance(x, float) for x in vector.embedding)
            assert 'embedding_model' in vector.metadata
            assert 'embedding_provider' in vector.metadata
            assert vector.metadata['embedding_provider'] == 'mock'
    
    @pytest.mark.asyncio
    async def test_process_document_complete_flow(self, document_processor):
        """测试完整的文档处理流程"""
        doc_id = str(uuid.uuid4())
        
        test_content = """# 测试文档

这是一个测试文档，用于验证完整的处理流程。

## 第一部分

这里是第一部分的内容，包含一些测试文本。

## 第二部分

这里是第二部分的内容，也包含一些测试文本。
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(test_content)
            temp_path = f.name
        
        try:
            result = await document_processor.process_document(temp_path, doc_id)
            
            assert isinstance(result, ProcessResult)
            assert result.success is True
            assert result.error_message == ""
            assert result.processing_time >= 0
            assert result.chunk_count > 0
            
            # 验证文本块
            assert len(result.chunks) > 0
            assert all(chunk.document_id == doc_id for chunk in result.chunks)
            
            # 验证向量
            assert len(result.vectors) == len(result.chunks)
            assert all(vector.document_id == doc_id for vector in result.vectors)
            
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_process_document_nonexistent_file(self, document_processor):
        """测试处理不存在的文件"""
        doc_id = str(uuid.uuid4())
        
        result = await document_processor.process_document("nonexistent.txt", doc_id)
        
        assert isinstance(result, ProcessResult)
        assert result.success is False
        assert "文件不存在" in result.error_message
        assert len(result.chunks) == 0
        assert len(result.vectors) == 0
    
    @pytest.mark.asyncio
    async def test_process_document_unsupported_format(self, document_processor):
        """测试处理不支持的文件格式"""
        doc_id = str(uuid.uuid4())
        
        with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as f:
            temp_path = f.name
        
        try:
            result = await document_processor.process_document(temp_path, doc_id)
            
            assert isinstance(result, ProcessResult)
            assert result.success is False
            assert "不支持的文件格式" in result.error_message
            
        finally:
            os.unlink(temp_path)
    
    def test_get_supported_formats(self, document_processor):
        """测试获取支持的格式"""
        formats = document_processor.get_supported_formats()
        
        assert isinstance(formats, list)
        assert '.txt' in formats
        assert '.md' in formats
    
    def test_is_supported_file(self, document_processor):
        """测试文件支持检查"""
        # 支持的格式
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            temp_path = f.name
        
        try:
            assert document_processor.is_supported_file(temp_path) is True
        finally:
            os.unlink(temp_path)
        
        # 不支持的格式
        with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as f:
            temp_path = f.name
        
        try:
            assert document_processor.is_supported_file(temp_path) is False
        finally:
            os.unlink(temp_path)
    
    def test_detect_file_type(self, document_processor):
        """测试文件类型检测"""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            temp_path = f.name
        
        try:
            file_type = document_processor.detect_file_type(temp_path)
            assert file_type == '.txt'
        finally:
            os.unlink(temp_path)
    
    def test_get_file_info(self, document_processor):
        """测试获取文件信息"""
        test_content = "测试内容"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(test_content)
            temp_path = f.name
        
        try:
            info = document_processor.get_file_info(temp_path)
            
            assert isinstance(info, dict)
            assert 'file_path' in info
            assert 'file_name' in info
            assert 'file_size' in info
            assert 'file_extension' in info
            assert 'detected_type' in info
            assert 'is_supported' in info
            assert 'supported_formats' in info
            
            assert info['file_extension'] == '.txt'
            assert info['detected_type'] == '.txt'
            assert info['is_supported'] is True
            assert info['file_size'] > 0
            
        finally:
            os.unlink(temp_path)
    
    def test_get_file_info_nonexistent(self, document_processor):
        """测试获取不存在文件的信息"""
        with pytest.raises(DocumentError) as exc_info:
            document_processor.get_file_info("nonexistent.txt")
        assert "文件不存在" in str(exc_info.value)


class TestDocumentProcessorConfiguration:
    """文档处理器配置测试"""
    
    @pytest.mark.asyncio
    async def test_custom_chunk_size(self):
        """测试自定义块大小"""
        config = {
            'chunk_size': 200,
            'chunk_overlap': 50
        }
        
        processor = DocumentProcessor(config)
        await processor.initialize()
        
        try:
            assert processor._chunk_size == 200
            assert processor._chunk_overlap == 50
            
            # 测试分割
            doc_id = str(uuid.uuid4())
            long_text = "这是一个测试段落。" * 30  # 约300字符
            
            chunks = processor.split_text(long_text, doc_id)
            
            # 验证块大小限制
            for chunk in chunks:
                assert len(chunk.content) <= 200 + 50  # chunk_size + overlap
                
        finally:
            await processor.cleanup()
    
    @pytest.mark.asyncio
    async def test_default_configuration(self):
        """测试默认配置"""
        processor = DocumentProcessor()
        await processor.initialize()
        
        try:
            assert processor._chunk_size == 1000  # 默认值
            assert processor._chunk_overlap == 200  # 默认值
            # 验证嵌入服务配置
            assert processor.embedding_service is not None
        finally:
            await processor.cleanup()
    
    @pytest.mark.asyncio
    async def test_embedding_service_integration(self):
        """测试嵌入服务集成"""
        config = {
            'embedding_provider': 'mock',
            'embedding_model': 'test-embedding-model',
            'embedding_dimensions': 512
        }
        
        processor = DocumentProcessor(config)
        await processor.initialize()
        
        try:
            # 验证嵌入服务配置
            assert processor.embedding_service is not None
            assert processor.embedding_service.get_embedding_dimension() == 512
            
            # 测试嵌入功能
            doc_id = str(uuid.uuid4())
            chunks = [
                TextChunk(
                    id=str(uuid.uuid4()),
                    document_id=doc_id,
                    content="测试嵌入服务集成",
                    chunk_index=0,
                    metadata={}
                )
            ]
            
            vectors = await processor.vectorize_chunks(chunks)
            
            assert len(vectors) == 1
            assert len(vectors[0].embedding) == 512
            assert vectors[0].metadata['embedding_model'] == 'test-embedding-model'
            
        finally:
            await processor.cleanup()


class TestDeprecatedInterface:
    """已弃用接口测试"""
    
    def test_deprecated_interface(self):
        """测试已弃用的接口"""
        from rag_system.services.document_processor import DocumentProcessorInterface
        
        # 应该发出弃用警告
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            interface = DocumentProcessorInterface()
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "已弃用" in str(w[0].message)