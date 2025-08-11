"""
文档文本提取器测试
"""
import pytest
import tempfile
import os
from pathlib import Path

from rag_system.document_processing.extractors import (
    TxtExtractor, MarkdownExtractor, TextExtractorFactory
)
from rag_system.utils.exceptions import DocumentError


class TestTxtExtractor:
    """TXT文件提取器测试"""
    
    def test_extract_utf8_text(self):
        """测试提取UTF-8编码的文本"""
        extractor = TxtExtractor()
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            test_content = "这是一个测试文件\n包含中文内容\nThis is English content"
            f.write(test_content)
            temp_path = f.name
        
        try:
            result = extractor.extract(temp_path)
            assert result == test_content
        finally:
            os.unlink(temp_path)
    
    def test_extract_gbk_text(self):
        """测试提取GBK编码的文本"""
        extractor = TxtExtractor()
        
        # 创建GBK编码的临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='gbk') as f:
            test_content = "这是GBK编码的测试文件"
            f.write(test_content)
            temp_path = f.name
        
        try:
            result = extractor.extract(temp_path)
            assert test_content in result
        finally:
            os.unlink(temp_path)
    
    def test_extract_nonexistent_file(self):
        """测试提取不存在的文件"""
        extractor = TxtExtractor()
        
        with pytest.raises(DocumentError) as exc_info:
            extractor.extract("nonexistent.txt")
        assert "文件不存在" in str(exc_info.value)
    
    def test_extract_unsupported_extension(self):
        """测试不支持的文件扩展名"""
        extractor = TxtExtractor()
        
        with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as f:
            temp_path = f.name
        
        try:
            with pytest.raises(DocumentError) as exc_info:
                extractor.extract(temp_path)
            assert "不支持的文件格式" in str(exc_info.value)
        finally:
            os.unlink(temp_path)
    
    def test_get_supported_extensions(self):
        """测试获取支持的扩展名"""
        extractor = TxtExtractor()
        extensions = extractor.get_supported_extensions()
        assert '.txt' in extensions


class TestMarkdownExtractor:
    """Markdown文件提取器测试"""
    
    def test_extract_markdown(self):
        """测试提取Markdown文件"""
        extractor = MarkdownExtractor()
        
        markdown_content = """# 标题1
        
这是一个段落。

## 标题2

这是**粗体**和*斜体*文本。

- 列表项1
- 列表项2

[链接文本](http://example.com)

```python
print("代码块")
```

> 引用文本
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(markdown_content)
            temp_path = f.name
        
        try:
            result = extractor.extract(temp_path)
            
            # 验证Markdown格式被清理
            assert "# 标题1" not in result
            assert "标题1" in result
            assert "**粗体**" not in result
            assert "粗体" in result
            assert "[链接文本]" not in result
            assert "链接文本" in result
            assert "```python" not in result
            assert "- 列表项1" not in result
            assert "列表项1" in result
            
        finally:
            os.unlink(temp_path)
    
    def test_get_supported_extensions(self):
        """测试获取支持的扩展名"""
        extractor = MarkdownExtractor()
        extensions = extractor.get_supported_extensions()
        assert '.md' in extensions
        assert '.markdown' in extensions


class TestTextExtractorFactory:
    """文本提取器工厂测试"""
    
    def test_factory_initialization(self):
        """测试工厂初始化"""
        factory = TextExtractorFactory()
        supported_formats = factory.get_supported_formats()
        
        # 至少应该支持TXT和Markdown
        assert '.txt' in supported_formats
        assert '.md' in supported_formats
    
    def test_get_extractor(self):
        """测试获取提取器"""
        factory = TextExtractorFactory()
        
        # 创建临时TXT文件
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            temp_path = f.name
        
        try:
            extractor = factory.get_extractor(temp_path)
            assert extractor is not None
            assert isinstance(extractor, TxtExtractor)
        finally:
            os.unlink(temp_path)
    
    def test_get_extractor_unsupported(self):
        """测试获取不支持格式的提取器"""
        factory = TextExtractorFactory()
        
        with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as f:
            temp_path = f.name
        
        try:
            extractor = factory.get_extractor(temp_path)
            assert extractor is None
        finally:
            os.unlink(temp_path)
    
    def test_extract_text_txt(self):
        """测试通过工厂提取TXT文本"""
        factory = TextExtractorFactory()
        
        test_content = "这是测试内容"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(test_content)
            temp_path = f.name
        
        try:
            result = factory.extract_text(temp_path)
            assert result == test_content
        finally:
            os.unlink(temp_path)
    
    def test_extract_text_markdown(self):
        """测试通过工厂提取Markdown文本"""
        factory = TextExtractorFactory()
        
        markdown_content = "# 标题\n\n这是内容"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(markdown_content)
            temp_path = f.name
        
        try:
            result = factory.extract_text(temp_path)
            assert "标题" in result
            assert "这是内容" in result
            assert "# 标题" not in result  # Markdown格式应该被清理
        finally:
            os.unlink(temp_path)
    
    def test_extract_text_unsupported(self):
        """测试提取不支持格式的文件"""
        factory = TextExtractorFactory()
        
        with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as f:
            temp_path = f.name
        
        try:
            with pytest.raises(DocumentError) as exc_info:
                factory.extract_text(temp_path)
            assert "不支持的文件格式" in str(exc_info.value)
        finally:
            os.unlink(temp_path)
    
    def test_detect_file_type(self):
        """测试文件类型检测"""
        factory = TextExtractorFactory()
        
        # 测试通过扩展名检测
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            temp_path = f.name
        
        try:
            file_type = factory.detect_file_type(temp_path)
            assert file_type == '.txt'
        finally:
            os.unlink(temp_path)
    
    def test_is_supported(self):
        """测试文件支持检查"""
        factory = TextExtractorFactory()
        
        # 支持的格式
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            temp_path = f.name
        
        try:
            assert factory.is_supported(temp_path) is True
        finally:
            os.unlink(temp_path)
        
        # 不支持的格式
        with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as f:
            temp_path = f.name
        
        try:
            assert factory.is_supported(temp_path) is False
        finally:
            os.unlink(temp_path)
    
    def test_register_custom_extractor(self):
        """测试注册自定义提取器"""
        factory = TextExtractorFactory()
        
        # 创建自定义提取器
        class CustomExtractor(TxtExtractor):
            def get_supported_extensions(self):
                return ['.custom']
        
        custom_extractor = CustomExtractor()
        factory.register_extractor('.custom', custom_extractor)
        
        # 验证注册成功
        supported_formats = factory.get_supported_formats()
        assert '.custom' in supported_formats
        
        # 创建测试文件
        with tempfile.NamedTemporaryFile(suffix='.custom', delete=False) as f:
            temp_path = f.name
        
        try:
            extractor = factory.get_extractor(temp_path)
            assert extractor is custom_extractor
        finally:
            os.unlink(temp_path)


class TestPDFExtractor:
    """PDF提取器测试（需要PyPDF2）"""
    
    def test_pdf_extractor_dependency_check(self):
        """测试PDF提取器依赖检查"""
        try:
            from rag_system.document_processing.extractors import PDFExtractor
            extractor = PDFExtractor()
            extensions = extractor.get_supported_extensions()
            assert '.pdf' in extensions
        except DocumentError as e:
            # 如果没有安装PyPDF2，应该抛出相应错误
            assert "PDF处理需要安装" in str(e)


class TestDocxExtractor:
    """DOCX提取器测试（需要python-docx）"""
    
    def test_docx_extractor_dependency_check(self):
        """测试DOCX提取器依赖检查"""
        try:
            from rag_system.document_processing.extractors import DocxExtractor
            extractor = DocxExtractor()
            extensions = extractor.get_supported_extensions()
            assert '.docx' in extensions
        except DocumentError as e:
            # 如果没有安装python-docx，应该抛出相应错误
            assert "DOCX处理需要安装" in str(e)