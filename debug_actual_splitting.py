#!/usr/bin/env python3
"""
调试实际的分割过程
"""
import asyncio
from rag_system.api.document_api import get_document_service

async def test_actual_splitting():
    """测试实际的分割过程"""
    print("🔍 测试实际的分割过程...")
    
    try:
        # 获取文档服务
        service = await get_document_service()
        processor = service.document_processor
        
        # 创建测试文本（类似于实际的大文档）
        test_text = """
# 深度学习与人工智能技术全面解析

## 引言
人工智能（Artificial Intelligence，AI）作为21世纪最具革命性的技术之一，正在深刻改变着我们的生活方式、工作模式和社会结构。从早期的符号主义AI到现代的深度学习，人工智能技术经历了多次重大突破和发展。

## 第一章：人工智能发展历程

### 1.1 早期发展阶段（1950-1980年代）
人工智能的概念最早可以追溯到1950年，当时英国数学家阿兰·图灵提出了著名的"图灵测试"，为判断机器是否具有智能提供了一个标准。在这个阶段，研究者们主要关注符号推理、专家系统和知识表示等领域。

专家系统是这一时期的重要成果，它通过将人类专家的知识编码到计算机程序中，使计算机能够在特定领域内进行推理和决策。然而，由于知识获取的困难性和推理能力的局限性，专家系统的应用范围相对有限。

### 1.2 机器学习兴起（1980-2000年代）
随着计算能力的提升和数据量的增加，机器学习逐渐成为人工智能研究的主流方向。这一时期出现了许多重要的机器学习算法，包括决策树、支持向量机、神经网络等。

神经网络虽然在1980年代就已经出现，但由于计算资源的限制和训练算法的不成熟，其发展一度陷入低谷。直到反向传播算法的提出和完善，神经网络才重新获得关注。

## 第二章：深度学习核心技术

### 2.1 神经网络基础
神经网络是深度学习的基础，它模拟了人脑神经元的工作原理。一个基本的神经网络由输入层、隐藏层和输出层组成，每一层包含多个神经元（节点），神经元之间通过权重连接。

神经网络的学习过程主要包括前向传播和反向传播两个阶段。在前向传播中，输入数据通过网络层层传递，最终产生输出结果。在反向传播中，网络根据输出结果与真实标签之间的误差，调整各层的权重参数。

### 2.2 卷积神经网络（CNN）
卷积神经网络是专门用于处理具有网格结构数据（如图像）的深度学习模型。CNN通过卷积操作、池化操作和全连接层的组合，能够有效提取图像的局部特征和全局特征。

卷积层是CNN的核心组件，它使用可学习的滤波器（卷积核）在输入数据上进行卷积操作，提取不同的特征。池化层则用于降低特征图的空间维度，减少计算量并提高模型的鲁棒性。
""" * 3  # 重复3次以创建更大的文档
        
        print(f"📄 测试文本长度: {len(test_text)} 字符")
        
        # 测试文本分割
        print("\n✂️ 测试文本分割...")
        import uuid
        test_doc_id = str(uuid.uuid4())
        
        chunks = processor.split_text(test_text, test_doc_id)
        
        print(f"✅ 分割成功: 生成 {len(chunks)} 个文本块")
        
        for i, chunk in enumerate(chunks[:5]):  # 只显示前5个块
            print(f"📝 块 {i+1}: 长度={len(chunk.content)}")
            print(f"   内容预览: {chunk.content[:100]}...")
            print(f"   元数据: {chunk.metadata.get('split_method', 'unknown')}")
            print()
        
        if len(chunks) > 5:
            print(f"... 还有 {len(chunks) - 5} 个块")
        
        # 清理
        await service.cleanup()
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_actual_splitting())