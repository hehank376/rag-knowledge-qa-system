#!/usr/bin/env python3
"""
综合系统诊断脚本
检查问答检索和日志输出问题
"""

import os
import sys
import logging
import asyncio
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def diagnose_system():
    """综合系统诊断"""
    print("🔍 综合系统诊断")
    print("=" * 60)
    
    # 1. 检查日志配置和输出
    print("\n1. 检查日志配置...")
    check_logging_config()
    
    # 2. 检查向量存储状态
    print("\n2. 检查向量存储状态...")
    await check_vector_store()
    
    # 3. 检查嵌入配置一致性
    print("\n3. 检查嵌入配置一致性...")
    await check_embedding_consistency()
    
    # 4. 检查QA服务配置
    print("\n4. 检查QA服务配置...")
    await check_qa_service_config()
    
    # 5. 测试完整的检索流程
    print("\n5. 测试完整检索流程...")
    await test_retrieval_pipeline()

def check_logging_config():
    """检查日志配置"""
    try:
        # 检查日志配置文件
        logging_config_file = Path("logging_config.yaml")
        if logging_config_file.exists():
            print("✓ 日志配置文件存在")
            
            import yaml
            with open(logging_config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 检查文件处理器
            handlers = config.get('handlers', {})
            file_handler = handlers.get('file', {})
            if file_handler:
                log_file = file_handler.get('filename', 'qa_system.log')
                print(f"  - 日志文件: {log_file}")
                
                # 检查日志文件是否存在
                if Path(log_file).exists():
                    size = Path(log_file).stat().st_size
                    print(f"  - 日志文件大小: {size} bytes")
                else:
                    print("  ⚠ 日志文件不存在")
            else:
                print("  ⚠ 未配置文件处理器")
        else:
            print("⚠ 日志配置文件不存在")
        
        # 测试日志输出
        print("\n  测试日志输出...")
        test_logger = logging.getLogger("test_logger")
        test_logger.info("这是一条测试日志信息")
        test_logger.error("这是一条测试错误信息")
        print("  ✓ 日志测试完成")
        
    except Exception as e:
        print(f"✗ 日志配置检查失败: {str(e)}")

async def check_vector_store():
    """检查向量存储状态"""
    try:
        import chromadb
        
        # 连接到Chroma数据库
        client = chromadb.PersistentClient(path="./chroma_db")
        collections = client.list_collections()
        
        print(f"✓ 找到 {len(collections)} 个集合")
        
        for collection in collections:
            print(f"  - 集合: {collection.name}")
            print(f"    文档数量: {collection.count()}")
            
            if collection.count() > 0:
                # 获取示例数据
                results = collection.peek(limit=2)
                if results and results.get('metadatas'):
                    metadata = results['metadatas'][0]
                    print(f"    嵌入提供商: {metadata.get('embedding_provider', 'N/A')}")
                    print(f"    嵌入模型: {metadata.get('embedding_model', 'N/A')}")
                    print(f"    向量维度: {metadata.get('embedding_dimensions', 'N/A')}")
                
                # 测试搜索功能
                print(f"    测试搜索...")
                try:
                    search_results = collection.query(
                        query_texts=["测试查询"],
                        n_results=1
                    )
                    if search_results.get('documents') and search_results['documents'][0]:
                        print(f"    ✓ 搜索成功")
                    else:
                        print(f"    ⚠ 搜索无结果")
                except Exception as e:
                    print(f"    ✗ 搜索失败: {str(e)}")
            else:
                print(f"    ⚠ 集合为空")
        
    except Exception as e:
        print(f"✗ 向量存储检查失败: {str(e)}")

async def check_embedding_consistency():
    """检查嵌入配置一致性"""
    try:
        from rag_system.config.loader import ConfigLoader
        
        config_loader = ConfigLoader()
        config = config_loader.load_config()
        
        print("配置文件中的嵌入设置:")
        print(f"  - 提供商: {config.embeddings.provider}")
        print(f"  - 模型: {config.embeddings.model}")
        
        # 检查API密钥
        api_key = os.getenv('SILICONFLOW_API_KEY')
        if api_key:
            print(f"  - API密钥: 已设置 ({api_key[:10]}...)")
        else:
            print(f"  - API密钥: 未设置")
        
        # 检查文档API配置
        print("\n检查文档API配置...")
        try:
            from rag_system.api.document_api import get_document_service
            # 这里不能直接调用，因为它是async函数
            print("  ✓ 文档API配置可访问")
        except Exception as e:
            print(f"  ✗ 文档API配置错误: {str(e)}")
        
        # 检查QA API配置
        print("\n检查QA API配置...")
        try:
            from rag_system.api.qa_api import get_qa_service
            print("  ✓ QA API配置可访问")
        except Exception as e:
            print(f"  ✗ QA API配置错误: {str(e)}")
        
    except Exception as e:
        print(f"✗ 嵌入配置检查失败: {str(e)}")

async def check_qa_service_config():
    """检查QA服务配置"""
    try:
        from rag_system.config.loader import ConfigLoader
        from rag_system.services.qa_service import QAService
        
        config_loader = ConfigLoader()
        app_config = config_loader.load_config()
        
        # 构建QA服务配置
        config = {
            'vector_store_type': app_config.vector_store.type,
            'vector_store_path': app_config.vector_store.persist_directory,
            'collection_name': app_config.vector_store.collection_name,
            'embedding_provider': app_config.embeddings.provider,
            'embedding_model': app_config.embeddings.model,
            'embedding_api_key': os.getenv('SILICONFLOW_API_KEY'),
            'llm_provider': app_config.llm.provider,
            'llm_model': app_config.llm.model,
            'llm_api_key': os.getenv('SILICONFLOW_API_KEY'),
            'database_url': app_config.database.url
        }
        
        print("QA服务配置:")
        for key, value in config.items():
            if 'api_key' in key and value:
                print(f"  - {key}: {value[:10]}...")
            else:
                print(f"  - {key}: {value}")
        
        # 尝试初始化QA服务
        print("\n尝试初始化QA服务...")
        try:
            qa_service = QAService(config)
            await qa_service.initialize()
            print("✓ QA服务初始化成功")
            
            # 测试问答
            print("\n测试问答功能...")
            test_question = "什么是人工智能？"
            qa_response = await qa_service.answer_question(test_question)
            
            print(f"  问题: {test_question}")
            print(f"  答案: {qa_response.answer[:100]}...")
            print(f"  源文档数量: {len(qa_response.sources)}")
            print(f"  置信度: {qa_response.confidence_score}")
            
            if len(qa_response.sources) > 0:
                print("  ✓ 找到相关源文档")
            else:
                print("  ⚠ 未找到相关源文档")
            
            await qa_service.cleanup()
            
        except Exception as e:
            print(f"✗ QA服务测试失败: {str(e)}")
            import traceback
            traceback.print_exc()
        
    except Exception as e:
        print(f"✗ QA服务配置检查失败: {str(e)}")

async def test_retrieval_pipeline():
    """测试完整检索流程"""
    try:
        print("测试完整的检索流程...")
        
        # 1. 测试嵌入服务
        print("\n1. 测试嵌入服务...")
        from rag_system.services.embedding_service import EmbeddingService
        from rag_system.config.loader import ConfigLoader
        
        config_loader = ConfigLoader()
        app_config = config_loader.load_config()
        
        embedding_config = {
            'provider': app_config.embeddings.provider,
            'model': app_config.embeddings.model,
            'api_key': os.getenv('SILICONFLOW_API_KEY'),
            'timeout': 60,
            'retry_attempts': 3
        }
        
        embedding_service = EmbeddingService(embedding_config)
        await embedding_service.initialize()
        
        test_text = "什么是人工智能？"
        query_embedding = await embedding_service.vectorize_query(test_text)
        print(f"  ✓ 查询向量化成功，维度: {len(query_embedding)}")
        
        # 2. 测试向量存储搜索
        print("\n2. 测试向量存储搜索...")
        from rag_system.vector_store.chroma_store import ChromaVectorStore
        from rag_system.models.config import VectorStoreConfig
        
        vector_config = VectorStoreConfig(
            type=app_config.vector_store.type,
            persist_directory=app_config.vector_store.persist_directory,
            collection_name=app_config.vector_store.collection_name
        )
        
        vector_store = ChromaVectorStore(vector_config)
        await vector_store.initialize()
        
        search_results = await vector_store.search_similar(
            query_embedding, 
            top_k=3, 
            similarity_threshold=0.0
        )
        
        print(f"  ✓ 向量搜索完成，找到 {len(search_results)} 个结果")
        
        for i, result in enumerate(search_results[:2]):
            print(f"    {i+1}. 相似度: {result.similarity_score:.4f}")
            print(f"       文档ID: {result.document_id}")
            print(f"       内容: {result.content[:50]}...")
        
        await embedding_service.cleanup()
        await vector_store.cleanup()
        
        if len(search_results) > 0:
            print("  ✓ 检索流程正常")
        else:
            print("  ⚠ 检索流程无结果")
        
    except Exception as e:
        print(f"✗ 检索流程测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

def create_logging_fix():
    """创建日志修复脚本"""
    print("\n" + "=" * 60)
    print("🔧 创建日志修复方案...")
    
    # 创建改进的日志配置
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            },
            'detailed': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'INFO',
                'formatter': 'standard',
                'stream': 'ext://sys.stdout'
            },
            'file': {
                'class': 'logging.FileHandler',
                'level': 'DEBUG',
                'formatter': 'detailed',
                'filename': 'qa_system.log',
                'mode': 'a',
                'encoding': 'utf-8'
            },
            'error_file': {
                'class': 'logging.FileHandler',
                'level': 'ERROR',
                'formatter': 'detailed',
                'filename': 'qa_errors.log',
                'mode': 'a',
                'encoding': 'utf-8'
            }
        },
        'loggers': {
            'rag_system': {
                'level': 'DEBUG',
                'handlers': ['console', 'file', 'error_file'],
                'propagate': False
            },
            'uvicorn': {
                'level': 'INFO',
                'handlers': ['console', 'file'],
                'propagate': False
            },
            'chromadb': {
                'level': 'WARNING',
                'handlers': ['file'],
                'propagate': False
            }
        },
        'root': {
            'level': 'INFO',
            'handlers': ['console', 'file']
        }
    }
    
    import yaml
    with open('improved_logging_config.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(logging_config, f, default_flow_style=False, allow_unicode=True, indent=2)
    
    print("✓ 创建了改进的日志配置: improved_logging_config.yaml")

if __name__ == "__main__":
    asyncio.run(diagnose_system())
    create_logging_fix()
    
    print("\n" + "=" * 60)
    print("🎯 诊断总结:")
    print("1. 检查日志文件是否生成和写入")
    print("2. 检查向量存储中的数据和维度")
    print("3. 检查嵌入配置的一致性")
    print("4. 测试完整的检索流程")
    
    print("\n💡 修复建议:")
    print("1. 使用改进的日志配置: improved_logging_config.yaml")
    print("2. 确保所有服务使用相同的嵌入模型配置")
    print("3. 检查API密钥设置")
    print("4. 重新上传文档以确保向量一致性")