#!/usr/bin/env python3
"""
调试简单层次结构
"""
import uuid
from rag_system.document_processing.splitters import HierarchicalSplitter, SplitConfig

def test_simple_hierarchy():
    """测试简单层次结构"""
    print("🔍 调试简单层次结构...")
    
    # 创建简单测试文本
    test_text = """## 引言
人工智能是一个重要的技术领域。

### 1.1 发展历程
人工智能经历了多个发展阶段。

这是一些普通的段落内容，不应该被识别为标题。"""
    
    print(f"📄 测试文本:")
    print(test_text)
    print(f"📄 测试文本长度: {len(test_text)} 字符")
    
    # 创建分割器
    config = SplitConfig(
        chunk_size=400,
        chunk_overlap=50,
        min_chunk_size=10
    )
    
    splitter = HierarchicalSplitter(config)
    
    # 测试段落分割
    print("\n📝 测试段落分割...")
    import re
    paragraphs = re.split(r'\n\s*\n', test_text)
    for i, para in enumerate(paragraphs):
        para = para.strip()
        if para:
            header_level = splitter._detect_header_level(para)
            print(f"段落 {i+1}: 标题级别={header_level}")
            print(f"内容: {para}")
            print()
    
    # 测试层次结构构建
    print("\n🏗️ 测试层次结构构建...")
    hierarchy = splitter._build_hierarchy(test_text)
    print(f"层次结构: {hierarchy}")
    
    # 测试分割
    print("\n✂️ 测试分割...")
    test_doc_id = str(uuid.uuid4())
    chunks = splitter.split(test_text, test_doc_id)
    
    print(f"✅ 分割成功: 生成 {len(chunks)} 个文本块")
    
    for i, chunk in enumerate(chunks):
        print(f"📝 块 {i+1}: 长度={len(chunk.content)}")
        print(f"   内容: {chunk.content}")
        print(f"   元数据: {chunk.metadata}")
        print()

if __name__ == "__main__":
    test_simple_hierarchy()