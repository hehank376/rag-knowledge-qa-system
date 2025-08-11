#!/usr/bin/env python3
"""
调试节点内容问题
"""
import json
from rag_system.document_processing.splitters import HierarchicalSplitter, SplitConfig

def test_node_content():
    """测试节点内容"""
    print("🔍 调试节点内容问题...")
    
    # 创建简单测试文本
    test_text = """## 引言
人工智能是一个重要的技术领域。

### 1.1 发展历程
人工智能经历了多个发展阶段。"""
    
    print(f"📄 测试文本:")
    print(repr(test_text))
    
    # 创建分割器
    config = SplitConfig(
        chunk_size=400,
        chunk_overlap=50,
        min_chunk_size=10
    )
    
    splitter = HierarchicalSplitter(config)
    
    # 测试层次结构构建
    print("\n🏗️ 测试层次结构构建...")
    hierarchy = splitter._build_hierarchy(test_text)
    
    # 打印详细的层次结构
    print("详细层次结构:")
    print(json.dumps(hierarchy, indent=2, ensure_ascii=False))
    
    # 手动检查节点内容
    print("\n🔍 手动检查节点内容...")
    def check_node(node, level=0):
        indent = "  " * level
        print(f"{indent}节点类型: {node.get('type')}")
        print(f"{indent}标题: {repr(node.get('title', 'N/A'))}")
        content = node.get('content', '')
        print(f"{indent}内容: {repr(content)}")
        print(f"{indent}内容长度: {len(content)}")
        print(f"{indent}内容是否为空: {not content}")
        print(f"{indent}内容strip后是否为空: {not content.strip() if content else True}")
        print()
        
        for child in node.get('children', []):
            check_node(child, level + 1)
    
    check_node(hierarchy)
    
    # 直接测试_generate_hierarchical_chunks方法
    print("\n🔧 直接测试_generate_hierarchical_chunks方法...")
    import uuid
    test_doc_id = str(uuid.uuid4())
    chunks = splitter._generate_hierarchical_chunks(hierarchy, test_doc_id)
    
    print(f"✅ 直接调用成功: 生成 {len(chunks)} 个文本块")
    
    for i, chunk in enumerate(chunks):
        print(f"📝 块 {i+1}: 长度={len(chunk.content)}")
        print(f"   内容: {repr(chunk.content)}")
        print(f"   元数据: {chunk.metadata}")
        print()
    
    # 测试RecursiveTextSplitter
    print("\n🔄 测试RecursiveTextSplitter...")
    from rag_system.document_processing.splitters import RecursiveTextSplitter
    recursive_splitter = RecursiveTextSplitter(config)
    
    # 测试策略选择
    strategy = recursive_splitter._select_best_strategy(test_text)
    print(f"选择的策略: {strategy}")
    
    chunks3 = recursive_splitter.split(test_text, test_doc_id)
    
    print(f"✅ RecursiveTextSplitter成功: 生成 {len(chunks3)} 个文本块")
    
    for i, chunk in enumerate(chunks3):
        print(f"📝 块 {i+1}: 长度={len(chunk.content)}")
        print(f"   内容: {repr(chunk.content)}")
        print(f"   元数据: {chunk.metadata}")
        print()

if __name__ == "__main__":
    test_node_content()