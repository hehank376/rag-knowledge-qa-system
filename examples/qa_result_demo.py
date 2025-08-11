#!/usr/bin/env python3
"""
问答结果处理和展示演示
演示任务6.3的功能实现
"""
import asyncio
import sys
import os
from datetime import datetime
from typing import List

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from rag_system.services.result_processor import ResultProcessor
from rag_system.models.qa import QAResponse, SourceInfo, QAStatus


async def demo_result_processing():
    """演示问答结果处理功能"""
    print("=" * 60)
    print("问答结果处理和展示功能演示")
    print("=" * 60)
    
    # 初始化结果处理器
    config = {
        'max_answer_length': 2000,
        'max_source_content_length': 200,
        'show_confidence_score': True,
        'show_processing_time': True,
        'highlight_keywords': True,
        'max_sources_display': 5,
        'sort_sources_by_relevance': True,
        'group_sources_by_document': False
    }
    
    processor = ResultProcessor(config)
    await processor.initialize()
    
    print(f"✓ 结果处理器初始化完成")
    print(f"  - 最大答案长度: {config['max_answer_length']}")
    print(f"  - 最大源内容长度: {config['max_source_content_length']}")
    print(f"  - 显示置信度分数: {config['show_confidence_score']}")
    print(f"  - 关键词高亮: {config['highlight_keywords']}")
    print()
    
    # 创建示例QA响应
    sources = [
        SourceInfo(
            document_id="550e8400-e29b-41d4-a716-446655440001",
            document_name="人工智能基础教程.pdf",
            chunk_id="550e8400-e29b-41d4-a716-446655440002",
            chunk_content="人工智能（Artificial Intelligence，AI）是计算机科学的一个分支，它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。",
            chunk_index=0,
            similarity_score=0.95
        ),
        SourceInfo(
            document_id="550e8400-e29b-41d4-a716-446655440003",
            document_name="机器学习概论.docx",
            chunk_id="550e8400-e29b-41d4-a716-446655440004",
            chunk_content="机器学习是人工智能的一个重要分支，它通过算法让计算机系统能够自动学习和改进，而无需明确编程。主要包括监督学习、无监督学习和强化学习三大类。",
            chunk_index=1,
            similarity_score=0.88
        ),
        SourceInfo(
            document_id="550e8400-e29b-41d4-a716-446655440005",
            document_name="深度学习应用.md",
            chunk_id="550e8400-e29b-41d4-a716-446655440006",
            chunk_content="深度学习是机器学习的一个子集，它模仿人脑神经网络的结构和功能。在图像识别、自然语言处理、语音识别等领域取得了突破性进展。",
            chunk_index=0,
            similarity_score=0.82
        )
    ]
    
    qa_response = QAResponse(
        question="什么是人工智能？它有哪些主要应用领域？",
        answer="人工智能（AI）是计算机科学的一个分支，旨在创建能够执行通常需要人类智能的任务的系统。它包括机器学习、深度学习、自然语言处理等技术。主要应用领域包括：1）图像识别和计算机视觉；2）自然语言处理和理解；3）语音识别和合成；4）推荐系统；5）自动驾驶；6）医疗诊断；7）金融风控等。这些技术正在改变我们的生活和工作方式。",
        sources=sources,
        confidence_score=0.92,
        processing_time=1.35,
        status=QAStatus.COMPLETED
    )
    
    print("📝 示例问答响应:")
    print(f"  问题: {qa_response.question}")
    print(f"  答案长度: {len(qa_response.answer)} 字符")
    print(f"  源文档数量: {len(qa_response.sources)}")
    print(f"  置信度分数: {qa_response.confidence_score}")
    print(f"  处理时间: {qa_response.processing_time}秒")
    print()
    
    # 演示答案格式化
    print("🔧 答案格式化处理:")
    formatted_answer = processor.format_answer(qa_response.answer, qa_response.question)
    print(f"  原始答案长度: {len(qa_response.answer)}")
    print(f"  格式化后长度: {len(formatted_answer)}")
    print(f"  格式化答案预览: {formatted_answer[:100]}...")
    print()
    
    # 演示关键词提取和高亮（通过格式化答案间接演示）
    print("🔍 关键词提取和高亮:")
    print("  关键词提取和高亮功能已集成在答案格式化中")
    print("  格式化过程中会自动提取关键词并进行高亮处理")
    print()
    
    # 演示源文档处理
    print("📚 源文档信息处理:")
    processed_sources = processor.process_sources(qa_response.sources)
    print(f"  处理后源文档数量: {len(processed_sources)}")
    
    for i, source in enumerate(processed_sources, 1):
        print(f"  源文档 {i}:")
        print(f"    - 文档名: {source.document_name}")
        print(f"    - 相似度: {source.similarity_score:.3f}")
        print(f"    - 内容长度: {len(source.chunk_content)}")
    print()
    
    # 演示完整响应格式化
    print("✨ 完整响应格式化:")
    formatted_response = processor.format_qa_response(qa_response)
    
    print(f"  响应ID: {formatted_response['id']}")
    print(f"  问题: {formatted_response['question']}")
    print(f"  答案长度: {len(formatted_response['answer'])}")
    print(f"  包含源文档: {formatted_response['has_sources']}")
    print(f"  源文档数量: {formatted_response['source_count']}")
    print(f"  置信度分数: {formatted_response['confidence_score']}")
    print(f"  处理时间: {formatted_response['processing_time']}秒")
    print(f"  状态: {formatted_response['status']}")
    print(f"  时间戳: {formatted_response['timestamp']}")
    print(f"  元数据键: {list(formatted_response['metadata'].keys())}")
    print()
    
    # 演示无答案响应处理
    print("❌ 无答案响应处理:")
    no_answer_cases = [
        ("没有找到相关内容的问题", "no_relevant_content"),
        ("置信度过低的问题", "low_confidence"),
        ("处理过程中出错的问题", "processing_error")
    ]
    
    for question, reason in no_answer_cases:
        no_answer_response = processor.create_no_answer_response(question, reason)
        print(f"  场景: {reason}")
        print(f"    - 问题: {question}")
        print(f"    - 回答: {no_answer_response['answer'][:50]}...")
        print(f"    - 建议数量: {len(no_answer_response['suggestions'])}")
        print(f"    - 置信度: {no_answer_response['confidence_score']}")
        print()
    
    # 演示统计信息
    print("📊 服务统计信息:")
    stats = processor.get_service_stats()
    print(f"  服务名称: {stats['service_name']}")
    print(f"  最大答案长度: {stats['max_answer_length']}")
    print(f"  最大源内容长度: {stats['max_source_content_length']}")
    print(f"  最大源文档显示数: {stats['max_sources_display']}")
    print(f"  显示置信度分数: {stats['show_confidence_score']}")
    print(f"  显示处理时间: {stats['show_processing_time']}")
    print(f"  关键词高亮: {stats['highlight_keywords']}")
    print(f"  按相关性排序: {stats['sort_sources_by_relevance']}")
    print(f"  按文档分组: {stats['group_sources_by_document']}")
    print()
    
    # 演示错误处理
    print("⚠️  错误处理演示:")
    try:
        # 创建一个有错误的响应
        error_response = QAResponse(
            question="测试错误处理",
            answer="",
            sources=[],
            confidence_score=0.0,
            processing_time=0.0,
            status=QAStatus.FAILED,
            error_message="模拟的处理错误"
        )
        
        formatted_error = processor.format_qa_response(error_response)
        print(f"  错误响应处理成功")
        print(f"  错误信息: {formatted_error.get('error_message', 'N/A')}")
        print(f"  状态: {formatted_error['status']}")
        
    except Exception as e:
        print(f"  错误处理异常: {str(e)}")
    
    print()
    print("=" * 60)
    print("演示完成！")
    print("=" * 60)
    
    # 清理资源
    await processor.cleanup()


async def demo_api_integration():
    """演示API集成功能"""
    print("\n" + "=" * 60)
    print("API集成功能演示")
    print("=" * 60)
    
    try:
        from fastapi.testclient import TestClient
        from rag_system.api.qa_api import router
        from fastapi import FastAPI
        
        # 创建测试应用
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        
        print("✓ FastAPI应用创建成功")
        
        # 测试健康检查
        response = client.get("/qa/health")
        if response.status_code == 200:
            health_data = response.json()
            print(f"✓ 健康检查通过: {health_data['status']}")
            print(f"  服务: {health_data['service']}")
            print(f"  版本: {health_data['version']}")
        else:
            print(f"✗ 健康检查失败: {response.status_code}")
        
        print("\n📡 API端点列表:")
        print("  - POST /qa/ask - 问答接口")
        print("  - POST /qa/no-answer-help - 无答案帮助")
        print("  - GET  /qa/stats - 统计信息")
        print("  - POST /qa/test - 系统测试")
        print("  - POST /qa/format-response - 响应格式化")
        print("  - GET  /qa/health - 健康检查")
        
    except ImportError as e:
        print(f"✗ API集成演示跳过（缺少依赖）: {str(e)}")
    except Exception as e:
        print(f"✗ API集成演示失败: {str(e)}")


if __name__ == "__main__":
    print("🚀 启动问答结果处理和展示功能演示...")
    
    # 运行演示
    asyncio.run(demo_result_processing())
    asyncio.run(demo_api_integration())
    
    print("\n🎉 演示程序执行完成！")
    print("\n💡 提示:")
    print("  - 结果处理器支持多种配置选项")
    print("  - 支持答案格式化、关键词高亮、源文档处理")
    print("  - 提供完整的API接口用于集成")
    print("  - 包含错误处理和统计功能")
    print("  - 所有功能都经过全面测试")