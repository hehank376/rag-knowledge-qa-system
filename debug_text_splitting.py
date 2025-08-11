#!/usr/bin/env python3
"""
调试文本分割问题
"""
import asyncio
from rag_system.document_processing.splitters import RecursiveTextSplitter, SplitConfig
from rag_system.document_processing.preprocessors import TextPreprocessor, PreprocessConfig

def test_text_splitting():
    """测试文本分割"""
    print("🔍 调试文本分割问题...")
    
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
    
    print(f"📄 原始文本长度: {len(test_text)} 字符")
    print(f"📄 原始文本内容预览:")
    print(test_text[:200] + "...")
    
    # 测试预处理
    print("\n🔧 测试文本预处理...")
    preprocess_config = PreprocessConfig()
    preprocessor = TextPreprocessor(preprocess_config)
    
    preprocessed_text = preprocessor.process(test_text)
    print(f"📄 预处理后文本长度: {len(preprocessed_text)} 字符")
    print(f"📄 预处理后文本内容预览:")
    print(preprocessed_text[:200] + "...")
    
    if not preprocessed_text.strip():
        print("❌ 预处理后文本为空！")
        return
    
    # 测试分割
    print("\n✂️ 测试文本分割...")
    split_config = SplitConfig(
        chunk_size=400,
        chunk_overlap=50,
        min_chunk_size=100
    )
    
    splitter = RecursiveTextSplitter(split_config)
    
    try:
        import uuid
        test_doc_id = str(uuid.uuid4())
        chunks = splitter.split(preprocessed_text, test_doc_id)
        print(f"✅ 分割成功: 生成 {len(chunks)} 个文本块")
        
        for i, chunk in enumerate(chunks):
            print(f"📝 块 {i+1}: 长度={len(chunk.content)}, 内容预览: {chunk.content[:100]}...")
            
    except Exception as e:
        print(f"❌ 分割失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_text_splitting()