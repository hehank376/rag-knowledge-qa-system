#!/usr/bin/env python3
"""
调试层次化分割器
"""
import uuid
from rag_system.document_processing.splitters import HierarchicalSplitter, SplitConfig

def test_hierarchical_splitter():
    """测试层次化分割器"""
    print("🔍 调试层次化分割器...")
    
    # 创建测试文本
    test_text = """
# 深度学习与人工智能技术全面解析

## 引言
人工智能（Artificial Intelligence，AI）作为21世纪最具革命性的技术之一，正在深刻改变着我们的生活方式、工作模式和社会结构。

## 第一章：人工智能发展历程

### 1.1 早期发展阶段（1950-1980年代）
人工智能的概念最早可以追溯到1950年，当时英国数学家阿兰·图灵提出了著名的"图灵测试"。

### 1.2 机器学习兴起（1980-2000年代）
随着计算能力的提升和数据量的增加，机器学习逐渐成为人工智能研究的主流方向。

## 第二章：深度学习核心技术

### 2.1 神经网络基础
神经网络是深度学习的基础，它模拟了人脑神经元的工作原理。

### 2.2 卷积神经网络（CNN）
卷积神经网络是专门用于处理具有网格结构数据（如图像）的深度学习模型。
"""
    
    print(f"📄 测试文本长度: {len(test_text)} 字符")
    
    # 创建分割器
    config = SplitConfig(
        chunk_size=400,
        chunk_overlap=50,
        min_chunk_size=20  # 降低最小块大小以适应测试文本
    )
    
    splitter = HierarchicalSplitter(config)
    
    try:
        # 测试层次结构构建
        print("\n🏗️ 测试层次结构构建...")
        hierarchy = splitter._build_hierarchy(test_text)
        print(f"层次结构: {hierarchy}")
        
        # 检查节点内容
        print("\n🔍 检查节点内容...")
        def check_node(node, level=0):
            indent = "  " * level
            print(f"{indent}节点类型: {node.get('type')}")
            print(f"{indent}标题: {node.get('title', 'N/A')}")
            content = node.get('content', '')
            print(f"{indent}内容长度: {len(content)}")
            if content:
                print(f"{indent}内容预览: {content[:50]}...")
            print(f"{indent}子节点数: {len(node.get('children', []))}")
            print()
            
            for child in node.get('children', []):
                check_node(child, level + 1)
        
        check_node(hierarchy)
        
        # 测试分割
        print("\n✂️ 测试层次化分割...")
        test_doc_id = str(uuid.uuid4())
        chunks = splitter.split(test_text, test_doc_id)
        
        print(f"✅ 分割成功: 生成 {len(chunks)} 个文本块")
        
        for i, chunk in enumerate(chunks):
            print(f"📝 块 {i+1}: 长度={len(chunk.content)}")
            print(f"   内容预览: {chunk.content[:100]}...")
            print(f"   元数据: {chunk.metadata}")
            print()
            
    except Exception as e:
        print(f"❌ 分割失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_hierarchical_splitter()