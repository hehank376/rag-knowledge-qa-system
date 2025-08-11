#!/usr/bin/env python3
"""
诊断嵌入模型配置问题
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def diagnose_embedding_config():
    """诊断嵌入配置"""
    print("🔍 诊断嵌入模型配置")
    print("=" * 40)
    
    # 1. 检查配置加载
    print("1. 检查配置加载...")
    try:
        from rag_system.config.loader import ConfigLoader
        config_loader = ConfigLoader()
        config = config_loader.load_config()
        
        print(f"✓ 配置加载成功")
        print(f"  嵌入提供商: {config.embeddings.provider}")
        print(f"  嵌入模型: {config.embeddings.model}")
        print(f"  分块大小: {config.embeddings.chunk_size}")
        print(f"  分块重叠: {config.embeddings.chunk_overlap}")
        
    except Exception as e:
        print(f"✗ 配置加载失败: {str(e)}")
        return
    
    # 2. 检查嵌入服务初始化
    print("\n2. 检查嵌入服务...")
    try:
        from rag_system.services.embedding_service import EmbeddingService
        
        embedding_config = {
            'provider': config.embeddings.provider,
            'model': config.embeddings.model,
            'chunk_size': config.embeddings.chunk_size,
            'chunk_overlap': config.embeddings.chunk_overlap,
            'api_key': None,  # 会从环境变量获取
            'base_url': None,
            'timeout': 60,
            'retry_attempts': 3
        }
        
        embedding_service = EmbeddingService(embedding_config)
        await embedding_service.initialize()
        
        print(f"✓ 嵌入服务初始化成功")
        
        # 测试嵌入
        test_text = "这是一个测试文本"
        embedding = await embedding_service.embed_query(test_text)
        
        print(f"  测试嵌入成功")
        print(f"  向量维度: {len(embedding)}")
        print(f"  向量前5个值: {embedding[:5]}")
        
    except Exception as e:
        print(f"✗ 嵌入服务测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # 3. 检查QA服务配置
    print("\n3. 检查QA服务配置...")
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
        
        print(f"QA服务配置:")
        for key, value in qa_config.items():
            print(f"  {key}: {value}")
        
        # 不初始化QA服务，因为可能会失败
        print(f"✓ QA服务配置检查完成")
        
    except Exception as e:
        print(f"✗ QA服务配置检查失败: {str(e)}")
    
    # 4. 检查向量存储配置
    print("\n4. 检查向量存储配置...")
    try:
        from rag_system.vector_store.chroma_store import ChromaVectorStore
        
        vector_config = {
            'persist_directory': config.vector_store.persist_directory,
            'collection_name': config.vector_store.collection_name
        }
        
        print(f"向量存储配置:")
        for key, value in vector_config.items():
            print(f"  {key}: {value}")
        
        # 检查集合信息
        vector_store = ChromaVectorStore(vector_config)
        await vector_store.initialize()
        
        collection_info = await vector_store.get_collection_info()
        print(f"✓ 向量存储连接成功")
        print(f"  集合名称: {collection_info.get('name', 'N/A')}")
        print(f"  文档数量: {collection_info.get('count', 0)}")
        print(f"  维度: {collection_info.get('dimension', 'N/A')}")
        
    except Exception as e:
        print(f"✗ 向量存储检查失败: {str(e)}")
    
    # 5. 检查API配置
    print("\n5. 检查API密钥配置...")
    import os
    
    api_keys = {
        'SILICONFLOW_API_KEY': os.getenv('SILICONFLOW_API_KEY'),
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
    }
    
    for key, value in api_keys.items():
        if value:
            print(f"  ✓ {key}: 已设置 ({value[:10]}...)")
        else:
            print(f"  ✗ {key}: 未设置")
    
    print("\n" + "=" * 40)
    print("🎯 诊断总结:")
    print("1. 检查嵌入模型配置是否正确")
    print("2. 检查API密钥是否设置")
    print("3. 检查向量存储维度是否匹配")
    print("4. 如果配置正确但维度不匹配，需要重新生成向量")

if __name__ == "__main__":
    import asyncio
    asyncio.run(diagnose_embedding_config())