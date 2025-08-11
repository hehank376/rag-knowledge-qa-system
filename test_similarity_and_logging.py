#!/usr/bin/env python3
"""
测试相似度计算和日志输出
"""
import asyncio
import os
import logging
from pathlib import Path

# 设置日志
def setup_logging():
    """设置日志配置"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "test.log", encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

setup_logging()

from rag_system.services.embedding_service import EmbeddingService
from rag_system.vector_store.chroma_store import ChromaVectorStore
from rag_system.models.config import VectorStoreConfig

logger = logging.getLogger(__name__)

async def test_similarity_and_logging():
    """测试相似度计算和日志输出"""
    logger.info("🧪 开始测试相似度计算和日志输出")
    
    # 清理旧的向量存储
    import shutil
    if os.path.exists('./test_chroma'):
        shutil.rmtree('./test_chroma')
    
    # 初始化嵌入服务
    embedding_config = {
        'provider': 'siliconflow',
        'model': 'BAAI/bge-large-zh-v1.5',
        'api_key': os.getenv('SILICONFLOW_API_KEY'),
        'api_base': 'https://api.siliconflow.cn/v1',
        'batch_size': 50,
        'dimensions': 1024,
        'timeout': 30
    }
    
    logger.info("初始化嵌入服务...")
    embedding_service = EmbeddingService(embedding_config)
    await embedding_service.initialize()
    
    # 初始化向量存储
    logger.info("初始化向量存储...")
    config = VectorStoreConfig(type='chroma', persist_directory='./test_chroma', collection_name='test')
    store = ChromaVectorStore(config)
    await store.initialize()
    
    # 测试文本
    texts = [
        "人工智能是计算机科学的一个重要分支",
        "机器学习是人工智能的核心技术",
        "深度学习使用神经网络处理复杂数据",
        "自然语言处理让计算机理解人类语言"
    ]
    
    logger.info(f"开始向量化 {len(texts)} 个文本...")
    
    # 向量化文本
    embeddings = await embedding_service.vectorize_texts(texts)
    logger.info(f"向量化完成，生成了 {len(embeddings)} 个向量")
    
    # 创建向量对象并添加到存储
    from rag_system.models.vector import Vector
    import uuid
    
    vectors = []
    for i, (text, embedding) in enumerate(zip(texts, embeddings)):
        vector = Vector(
            id=str(uuid.uuid4()),
            document_id=str(uuid.uuid4()),
            chunk_id=str(uuid.uuid4()),
            embedding=embedding,
            metadata={
                "content": text,
                "index": i
            }
        )
        vectors.append(vector)
    
    logger.info("添加向量到存储...")
    await store.add_vectors(vectors)
    
    # 测试查询
    queries = [
        "什么是人工智能？",
        "机器学习的原理",
        "深度学习应用",
        "NLP技术"
    ]
    
    for query in queries:
        logger.info(f"\\n查询: {query}")
        
        # 向量化查询
        query_vector = await embedding_service.vectorize_query(query)
        logger.info(f"查询向量维度: {len(query_vector)}")
        
        # 搜索相似向量
        results = await store.search_similar(query_vector, top_k=3, similarity_threshold=0.0)
        logger.info(f"找到 {len(results)} 个结果")
        
        for i, result in enumerate(results):
            logger.info(f"  结果 {i+1}: 相似度={result.similarity_score:.4f}, 内容='{result.content[:50]}...'")
    
    # 清理资源
    await embedding_service.cleanup()
    await store.cleanup()
    
    logger.info("测试完成！")

if __name__ == "__main__":
    asyncio.run(test_similarity_and_logging())