#!/usr/bin/env python3
"""
QA系统诊断脚本
检查问答系统各个组件的状态和配置
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('qa_diagnosis.log')
    ]
)

logger = logging.getLogger(__name__)

async def diagnose_qa_system():
    """诊断QA系统"""
    print("🔍 QA系统诊断工具")
    print("=" * 60)
    
    # 1. 检查配置文件
    print("\n1. 检查配置文件...")
    try:
        from rag_system.config.loader import ConfigLoader
        config_loader = ConfigLoader()
        config = config_loader.load_config()
        
        print(f"✓ 配置文件加载成功")
        print(f"  - 向量存储类型: {config.vector_store.type}")
        print(f"  - 向量存储路径: {config.vector_store.persist_directory}")
        print(f"  - 集合名称: {config.vector_store.collection_name}")
        print(f"  - 嵌入模型: {config.embeddings.provider}/{config.embeddings.model}")
        print(f"  - LLM模型: {config.llm.provider}/{config.llm.model}")
        
    except Exception as e:
        print(f"✗ 配置文件加载失败: {str(e)}")
        return
    
    # 2. 检查向量存储
    print("\n2. 检查向量存储...")
    try:
        from rag_system.vector_store.chroma_store import ChromaVectorStore
        
        vector_config = {
            'persist_directory': config.vector_store.persist_directory,
            'collection_name': config.vector_store.collection_name
        }
        
        vector_store = ChromaVectorStore(vector_config)
        await vector_store.initialize()
        
        # 检查集合状态
        collection_info = await vector_store.get_collection_info()
        print(f"✓ 向量存储连接成功")
        print(f"  - 集合名称: {collection_info.get('name', 'N/A')}")
        print(f"  - 文档数量: {collection_info.get('count', 0)}")
        print(f"  - 维度: {collection_info.get('dimension', 'N/A')}")
        
        # 尝试搜索测试
        if collection_info.get('count', 0) > 0:
            print("\n  测试向量搜索...")
            try:
                # 创建一个测试嵌入向量
                from rag_system.embeddings.siliconflow_embeddings import SiliconflowEmbeddings
                
                embedding_config = {
                    'model': config.embeddings.model,
                    'api_key': os.getenv('SILICONFLOW_API_KEY', 'test-key')
                }
                
                embeddings = SiliconflowEmbeddings(embedding_config)
                await embeddings.initialize()
                
                test_query = "什么是人工智能"
                query_embedding = await embeddings.embed_query(test_query)
                
                search_results = await vector_store.similarity_search_with_score(
                    query_embedding, k=3
                )
                
                print(f"  ✓ 向量搜索成功，找到 {len(search_results)} 个结果")
                for i, (doc, score) in enumerate(search_results[:2]):
                    print(f"    {i+1}. 相似度: {score:.4f}")
                    print(f"       内容: {doc.page_content[:100]}...")
                    print(f"       元数据: {doc.metadata}")
                
            except Exception as e:
                print(f"  ✗ 向量搜索测试失败: {str(e)}")
        else:
            print("  ⚠ 向量存储中没有文档")
            
    except Exception as e:
        print(f"✗ 向量存储检查失败: {str(e)}")
        logger.exception("向量存储检查异常")
    
    # 3. 检查嵌入服务
    print("\n3. 检查嵌入服务...")
    try:
        from rag_system.embeddings.siliconflow_embeddings import SiliconflowEmbeddings
        
        embedding_config = {
            'model': config.embeddings.model,
            'api_key': os.getenv('SILICONFLOW_API_KEY', 'test-key')
        }
        
        embeddings = SiliconflowEmbeddings(embedding_config)
        await embeddings.initialize()
        
        # 测试嵌入
        test_text = "这是一个测试文本"
        embedding = await embeddings.embed_query(test_text)
        
        print(f"✓ 嵌入服务正常")
        print(f"  - 模型: {config.embeddings.model}")
        print(f"  - 向量维度: {len(embedding)}")
        print(f"  - API密钥状态: {'已配置' if os.getenv('SILICONFLOW_API_KEY') else '未配置'}")
        
    except Exception as e:
        print(f"✗ 嵌入服务检查失败: {str(e)}")
        logger.exception("嵌入服务检查异常")
    
    # 4. 检查LLM服务
    print("\n4. 检查LLM服务...")
    try:
        from rag_system.llm.siliconflow_llm import SiliconflowLLM
        
        llm_config = {
            'model': config.llm.model,
            'api_key': os.getenv('SILICONFLOW_API_KEY', 'test-key'),
            'temperature': config.llm.temperature,
            'max_tokens': config.llm.max_tokens
        }
        
        llm = SiliconflowLLM(llm_config)
        await llm.initialize()
        
        # 测试LLM
        test_prompt = "请简单回答：什么是人工智能？"
        response = await llm.generate(test_prompt)
        
        print(f"✓ LLM服务正常")
        print(f"  - 模型: {config.llm.model}")
        print(f"  - 测试响应: {response[:100]}...")
        print(f"  - API密钥状态: {'已配置' if os.getenv('SILICONFLOW_API_KEY') else '未配置'}")
        
    except Exception as e:
        print(f"✗ LLM服务检查失败: {str(e)}")
        logger.exception("LLM服务检查异常")
    
    # 5. 检查QA服务
    print("\n5. 检查QA服务...")
    try:
        from rag_system.services.qa_service import QAService
        
        qa_config = {
            'vector_store_type': config.vector_store.type,
            'vector_store_path': config.vector_store.persist_directory,
            'embedding_provider': config.embeddings.provider,
            'embedding_model': config.embeddings.model,
            'llm_provider': config.llm.provider,
            'llm_model': config.llm.model,
            'database_url': config.database.url
        }
        
        qa_service = QAService(qa_config)
        await qa_service.initialize()
        
        print(f"✓ QA服务初始化成功")
        
        # 测试问答
        test_question = "什么是人工智能？"
        print(f"\n  测试问答: {test_question}")
        
        qa_response = await qa_service.answer_question(test_question)
        
        print(f"  ✓ 问答测试成功")
        print(f"    - 问题: {qa_response.question}")
        print(f"    - 答案: {qa_response.answer[:200]}...")
        print(f"    - 源文档数量: {len(qa_response.sources)}")
        print(f"    - 置信度: {qa_response.confidence_score}")
        print(f"    - 处理时间: {qa_response.processing_time}秒")
        
        if qa_response.sources:
            print(f"    - 源文档详情:")
            for i, source in enumerate(qa_response.sources[:2]):
                print(f"      {i+1}. 文档: {source.document_name}")
                print(f"         相似度: {source.similarity_score}")
                print(f"         内容: {source.chunk_content[:100]}...")
        
    except Exception as e:
        print(f"✗ QA服务检查失败: {str(e)}")
        logger.exception("QA服务检查异常")
    
    # 6. 检查数据库
    print("\n6. 检查数据库...")
    try:
        from rag_system.database.connection import DatabaseManager
        from rag_system.models.config import DatabaseConfig
        
        db_config = DatabaseConfig(
            url=config.database.url,
            echo=config.database.echo
        )
        
        db_manager = DatabaseManager(db_config)
        db_manager.initialize()
        
        print(f"✓ 数据库连接成功")
        print(f"  - 数据库URL: {config.database.url}")
        print(f"  - Echo模式: {config.database.echo}")
        
        # 检查文档表
        with db_manager.get_session_context() as db_session:
            from rag_system.database.models import DocumentModel
            doc_count = db_session.query(DocumentModel).count()
            ready_count = db_session.query(DocumentModel).filter(
                DocumentModel.status == 'ready'
            ).count()
            
            print(f"  - 文档总数: {doc_count}")
            print(f"  - 就绪文档数: {ready_count}")
        
    except Exception as e:
        print(f"✗ 数据库检查失败: {str(e)}")
        logger.exception("数据库检查异常")
    
    print("\n" + "=" * 60)
    print("🎯 诊断总结:")
    print("1. 检查日志文件 'qa_diagnosis.log' 获取详细信息")
    print("2. 确保 SILICONFLOW_API_KEY 环境变量已设置")
    print("3. 确认向量存储中有文档且维度匹配")
    print("4. 检查配置文件中的模型设置")
    
    print("\n💡 常见问题解决方案:")
    print("- 如果向量搜索失败，检查嵌入模型配置")
    print("- 如果LLM调用失败，检查API密钥和模型名称")
    print("- 如果没有找到文档，重新上传并处理文档")
    print("- 如果维度不匹配，清空向量存储重新处理文档")

if __name__ == "__main__":
    import asyncio
    asyncio.run(diagnose_qa_system())