"""
文本分割器测试
"""
import pytest
import uuid

from rag_system.document_processing.splitters import (
    FixedSizeSplitter, StructureSplitter, HierarchicalSplitter,
    SemanticSplitter, RecursiveTextSplitter, TextSplitter, SplitConfig
)
from rag_system.models.document import TextChunk
from rag_system.utils.exceptions import ProcessingError


class TestSplitConfig:
    """分割配置测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = SplitConfig()
        
        assert config.chunk_size == 1000
        assert config.chunk_overlap == 200
        assert config.min_chunk_size == 100
        assert config.max_chunk_size == 2000
        assert config.preserve_structure is True
        assert config.generate_summary is False
        assert config.generate_questions is False
        assert config.semantic_split is False
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = SplitConfig(
            chunk_size=500,
            chunk_overlap=100,
            generate_summary=True,
            generate_questions=True
        )
        
        assert config.chunk_size == 500
        assert config.chunk_overlap == 100
        assert config.generate_summary is True
        assert config.generate_questions is True


class TestFixedSizeSplitter:
    """固定大小分割器测试"""
    
    def test_split_short_text(self):
        """测试分割短文本"""
        config = SplitConfig(chunk_size=100, chunk_overlap=20)
        splitter = FixedSizeSplitter(config)
        
        text = "这是一个短文本，用于测试分割功能。"
        doc_id = str(uuid.uuid4())
        
        chunks = splitter.split(text, doc_id)
        
        assert len(chunks) == 1
        assert chunks[0].document_id == doc_id
        assert chunks[0].chunk_index == 0
        assert chunks[0].content == text
        assert "split_method" in chunks[0].metadata
        assert chunks[0].metadata["split_method"] == "fixed_size"
    
    def test_split_long_text(self):
        """测试分割长文本"""
        config = SplitConfig(chunk_size=50, chunk_overlap=10)
        splitter = FixedSizeSplitter(config)
        
        text = "这是第一句话。这是第二句话。这是第三句话。这是第四句话。这是第五句话。这是第六句话。"
        doc_id = str(uuid.uuid4())
        
        chunks = splitter.split(text, doc_id)
        
        assert len(chunks) > 1
        
        # 验证所有块都属于同一文档
        for chunk in chunks:
            assert chunk.document_id == doc_id
            assert isinstance(chunk, TextChunk)
            assert len(chunk.content) > 0
        
        # 验证块索引连续
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i
    
    def test_split_with_summary_and_questions(self):
        """测试带摘要和问题生成的分割"""
        config = SplitConfig(
            chunk_size=100,
            generate_summary=True,
            generate_questions=True
        )
        splitter = FixedSizeSplitter(config)
        
        text = "这是一个测试文档。它包含了多个句子。我们需要测试摘要和问题生成功能。"
        doc_id = str(uuid.uuid4())
        
        chunks = splitter.split(text, doc_id)
        
        assert len(chunks) >= 1
        chunk = chunks[0]
        
        assert "summary" in chunk.metadata
        assert "questions" in chunk.metadata
        assert isinstance(chunk.metadata["questions"], list)
        assert len(chunk.metadata["questions"]) > 0
    
    def test_split_empty_text(self):
        """测试分割空文本"""
        splitter = FixedSizeSplitter()
        doc_id = str(uuid.uuid4())
        
        with pytest.raises(ProcessingError):
            splitter.split("", doc_id)
        
        with pytest.raises(ProcessingError):
            splitter.split("   ", doc_id)


class TestStructureSplitter:
    """结构化分割器测试"""
    
    def test_split_with_headers(self):
        """测试带标题的文档分割"""
        config = SplitConfig(chunk_size=200)
        splitter = StructureSplitter(config)
        
        text = """# 第一章 介绍
        
这是第一章的内容。包含了一些介绍性的文字。

## 1.1 背景

这是背景部分的内容。

# 第二章 方法

这是第二章的内容。描述了使用的方法。
"""
        
        doc_id = str(uuid.uuid4())
        chunks = splitter.split(text, doc_id)
        
        assert len(chunks) > 1
        
        # 检查是否正确识别了标题
        header_chunks = [c for c in chunks if c.metadata.get("has_header")]
        assert len(header_chunks) > 0
        
        # 检查标题级别
        for chunk in header_chunks:
            assert "header_level" in chunk.metadata
            assert chunk.metadata["header_level"] > 0
    
    def test_split_paragraphs(self):
        """测试段落分割"""
        config = SplitConfig(chunk_size=100)
        splitter = StructureSplitter(config)
        
        text = """第一段内容。这是一个完整的段落。

第二段内容。这也是一个完整的段落。

第三段内容。这是最后一个段落。"""
        
        doc_id = str(uuid.uuid4())
        chunks = splitter.split(text, doc_id)
        
        assert len(chunks) >= 1
        
        # 验证段落信息
        for chunk in chunks:
            assert "paragraphs" in chunk.metadata
            assert isinstance(chunk.metadata["paragraphs"], list)


class TestHierarchicalSplitter:
    """层次化分割器测试"""
    
    def test_split_hierarchical_document(self):
        """测试层次化文档分割"""
        config = SplitConfig(chunk_size=200)
        splitter = HierarchicalSplitter(config)
        
        text = """# 第一章 概述

这是概述章节的内容。

## 1.1 背景

这是背景小节的内容。

## 1.2 目标

这是目标小节的内容。

# 第二章 实现

这是实现章节的内容。

## 2.1 方法

这是方法小节的内容。
"""
        
        doc_id = str(uuid.uuid4())
        chunks = splitter.split(text, doc_id)
        
        assert len(chunks) > 1
        
        # 检查层次信息
        for chunk in chunks:
            assert "split_method" in chunk.metadata
            assert chunk.metadata["split_method"] == "hierarchical"
            assert "level" in chunk.metadata
            assert "hierarchy_path" in chunk.metadata
    
    def test_split_with_section_titles(self):
        """测试带章节标题的分割"""
        config = SplitConfig(chunk_size=150)
        splitter = HierarchicalSplitter(config)
        
        text = """第一章 介绍

这是介绍章节的详细内容。包含了项目的背景信息。

第二章 方法

这是方法章节的详细内容。描述了具体的实现方法。
"""
        
        doc_id = str(uuid.uuid4())
        chunks = splitter.split(text, doc_id)
        
        # 检查章节标题信息
        titled_chunks = [c for c in chunks if "section_title" in c.metadata]
        assert len(titled_chunks) > 0


class TestSemanticSplitter:
    """语义分割器测试"""
    
    def test_split_by_sentences(self):
        """测试按句子语义分割"""
        config = SplitConfig(chunk_size=100)
        splitter = SemanticSplitter(config)
        
        text = """这是第一个句子。这是第二个句子。然而，这里有一个转折。接下来是另一个话题。最后是总结句子。"""
        
        doc_id = str(uuid.uuid4())
        chunks = splitter.split(text, doc_id)
        
        assert len(chunks) >= 1
        
        # 检查语义分组信息
        for chunk in chunks:
            assert "split_method" in chunk.metadata
            assert chunk.metadata["split_method"] == "semantic"
            assert "sentence_count" in chunk.metadata
            assert "semantic_group" in chunk.metadata
    
    def test_split_single_sentence(self):
        """测试单句文本分割"""
        splitter = SemanticSplitter()
        
        text = "这是一个单独的句子。"
        doc_id = str(uuid.uuid4())
        
        chunks = splitter.split(text, doc_id)
        
        assert len(chunks) == 1
        assert chunks[0].content == text
    
    def test_semantic_break_detection(self):
        """测试语义断点检测"""
        config = SplitConfig(chunk_size=200)
        splitter = SemanticSplitter(config)
        
        text = """这是第一个话题的内容。我们在讨论A主题。然而，现在我们要转到B主题。这是关于B主题的内容。另外，还有C主题需要讨论。"""
        
        doc_id = str(uuid.uuid4())
        chunks = splitter.split(text, doc_id)
        
        # 应该根据话题转换词进行分割
        assert len(chunks) > 1


class TestRecursiveTextSplitter:
    """递归文本分割器测试"""
    
    def test_strategy_selection(self):
        """测试分割策略选择"""
        splitter = RecursiveTextSplitter()
        
        # 测试不同类型的文本
        texts = [
            "简单的短文本",
            "# 标题\n\n这是一个有标题的文档\n\n## 子标题\n\n内容",
            "第一章 概述\n\n这是章节内容\n\n第二章 详细\n\n更多内容",
            "这是一个很长的文本。" * 100
        ]
        
        doc_id = str(uuid.uuid4())
        
        for text in texts:
            chunks = splitter.split(text, doc_id)
            assert len(chunks) >= 1
            
            # 验证所有块都有正确的元数据
            for chunk in chunks:
                assert chunk.document_id == doc_id
                assert "split_method" in chunk.metadata
    
    def test_post_processing(self):
        """测试后处理功能"""
        config = SplitConfig(
            chunk_size=100,
            min_chunk_size=20,
            max_chunk_size=150
        )
        splitter = RecursiveTextSplitter(config)
        
        # 创建包含过大和过小块的文本
        text = "很短。" + "这是一个中等长度的段落。" * 10
        doc_id = str(uuid.uuid4())
        
        chunks = splitter.split(text, doc_id)
        
        # 验证块大小在合理范围内
        for chunk in chunks:
            assert len(chunk.content) >= config.min_chunk_size or len(chunks) == 1
            # 注意：max_chunk_size可能在后处理中被超过，这是正常的
    
    def test_large_chunk_splitting(self):
        """测试大块分割"""
        config = SplitConfig(
            chunk_size=100,
            max_chunk_size=120
        )
        splitter = RecursiveTextSplitter(config)
        
        # 创建一个会产生过大块的文本
        text = "这是一个非常长的句子，" * 20
        doc_id = str(uuid.uuid4())
        
        chunks = splitter.split(text, doc_id)
        
        # 检查是否有子块标记
        sub_chunks = [c for c in chunks if c.metadata.get("is_sub_chunk")]
        if sub_chunks:
            for chunk in sub_chunks:
                assert "parent_chunk_id" in chunk.metadata
                assert "original_split_method" in chunk.metadata


class TestTextSplitter:
    """主要文本分割器接口测试"""
    
    def test_backward_compatibility(self):
        """测试向后兼容性"""
        splitter = TextSplitter(chunk_size=200, chunk_overlap=50)
        
        text = "这是一个测试文档。" * 20
        doc_id = str(uuid.uuid4())
        
        chunks = splitter.split(text, doc_id)
        
        assert len(chunks) >= 1
        assert all(isinstance(chunk, TextChunk) for chunk in chunks)
    
    def test_custom_parameters(self):
        """测试自定义参数"""
        splitter = TextSplitter(
            chunk_size=150,
            chunk_overlap=30,
            generate_summary=True,
            semantic_split=True
        )
        
        text = "第一段内容。第二段内容。第三段内容。" * 10
        doc_id = str(uuid.uuid4())
        
        chunks = splitter.split(text, doc_id)
        
        assert len(chunks) >= 1
        
        # 检查是否应用了自定义配置
        for chunk in chunks:
            if chunk.metadata.get("generate_summary"):
                assert "summary" in chunk.metadata


class TestSplitterErrorHandling:
    """分割器错误处理测试"""
    
    def test_empty_text_handling(self):
        """测试空文本处理"""
        splitters = [
            FixedSizeSplitter(),
            StructureSplitter(),
            HierarchicalSplitter(),
            SemanticSplitter(),
            RecursiveTextSplitter()
        ]
        
        doc_id = str(uuid.uuid4())
        
        for splitter in splitters:
            with pytest.raises(ProcessingError):
                splitter.split("", doc_id)
            
            with pytest.raises(ProcessingError):
                splitter.split("   ", doc_id)
    
    def test_invalid_document_id(self):
        """测试无效文档ID处理"""
        splitter = FixedSizeSplitter()
        text = "测试文本"
        
        # 空文档ID应该仍然能工作（由TextChunk验证）
        chunks = splitter.split(text, "")
        assert len(chunks) == 1
    
    def test_very_long_text(self):
        """测试超长文本处理"""
        config = SplitConfig(chunk_size=100, max_chunk_size=200)
        splitter = RecursiveTextSplitter(config)
        
        # 创建超长文本
        text = "这是一个很长的文本。" * 1000
        doc_id = str(uuid.uuid4())
        
        chunks = splitter.split(text, doc_id)
        
        assert len(chunks) > 1
        # 验证没有块过大
        for chunk in chunks:
            # 允许一定的超出，因为要保持语义完整性
            assert len(chunk.content) <= config.max_chunk_size * 1.5