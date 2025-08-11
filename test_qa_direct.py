#!/usr/bin/env python3
"""
直接测试QA服务
"""
import asyncio
import os
from rag_system.services.qa_service import QAService

async def test_qa_service():
    """测试QA服务"""
    print("🧪 直接测试QA服务")
    
    # 配置QA服务
    config = {
        'vector_store_type': 'chroma',
        'vector_store_path': './chroma_db',
        'collection_name': 'documents',
        'embedding_provider': 'siliconflow',
        'embedding_model': 'BAAI/bge-large-zh-v1.5',
        'embedding_api_key': os.getenv('SILICONFLOW_API_KEY'),
        'embedding_api_base': 'https://api.siliconflow.cn/v1',
        'embedding_dimensions': 1024,
        'llm_provider': 'siliconflow',
        'llm_model': 'Qwen/Qwen3-8B',
        'llm_api_key': os.getenv('SILICONFLOW_API_KEY'),
        'llm_api_base': 'https://api.siliconflow.cn/v1',
        'similarity_threshold': 0.01,  # 很低的阈值
        'retrieval_top_k': 5,
        'database_url': 'sqlite:///./database/rag_system.db'
    }
    
    print(f"配置: {config}")
    
    # 初始化QA服务
    qa_service = QAService(config)
    await qa_service.initialize()
    
    # 测试问题
    questions = [
        "什么是人工智能？",
        "什么是机器学习？",
        "什么是RAG技术？"
    ]
    
    for question in questions:
        print(f"\n问题: {question}")
        try:
            response = await qa_service.answer_question(question)
            print(f"答案: {response.answer[:200]}...")
            print(f"源文档数量: {len(response.sources)}")
            print(f"置信度: {response.confidence_score}")
            
            if response.sources:
                print("找到相关内容 ✓")
                for i, source in enumerate(response.sources):
                    print(f"  源 {i+1}: {source.filename} (相似度: {source.similarity_score})")
            else:
                print("没有找到相关内容 ⚠")
                
        except Exception as e:
            print(f"错误: {str(e)}")
    
    await qa_service.cleanup()

if __name__ == "__main__":
    asyncio.run(test_qa_service())