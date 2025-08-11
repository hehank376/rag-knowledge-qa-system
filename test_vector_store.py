#!/usr/bin/env python3
"""
测试向量存储是否有数据
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_vector_store():
    """测试向量存储"""
    print("🔍 测试向量存储数据")
    print("=" * 40)
    
    try:
        # 直接使用Chroma客户端检查
        import chromadb
        
        # 连接到持久化的Chroma数据库
        client = chromadb.PersistentClient(path="./chroma_db")
        
        # 列出所有集合
        collections = client.list_collections()
        print(f"✓ 找到 {len(collections)} 个集合:")
        
        for collection in collections:
            print(f"  - 集合名称: {collection.name}")
            print(f"    文档数量: {collection.count()}")
            
            # 获取一些示例数据
            if collection.count() > 0:
                results = collection.peek(limit=3)
                print(f"    示例文档:")
                for i, (doc_id, document, metadata, embedding) in enumerate(zip(
                    results['ids'], 
                    results['documents'], 
                    results['metadatas'],
                    results['embeddings']  # 新增：获取向量值
                )):
                    print(f"      {i+1}. ID: {doc_id}")
                    print(f"         内容: {document[:100]}...")
                    print(f"         元数据: {metadata}")
                    # 显示向量的前10个元素（向量通常很长，完整显示无必要）
                    print(f"         向量前10元素: {embedding[:10]}...")
                    print(f"         向量维度: {len(embedding)}")  # 显示向量维度
                
                
            print()
    
    except Exception as e:
        print(f"✗ 向量存储测试失败: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_vector_store())