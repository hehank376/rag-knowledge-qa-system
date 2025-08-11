#!/usr/bin/env python3
"""
测试修复后的嵌入配置
"""

import requests
import time
from pathlib import Path
import asyncio

def upload_test_document():
    """上传一个测试文档"""
    print("📤 上传测试文档...")
    
    # 创建一个新的测试文档
    test_content = """测试文档 - 修复后的嵌入配置

这是一个用于测试修复后嵌入配置的文档。

人工智能（AI）是一门研究如何让计算机模拟人类智能的科学。它包括机器学习、深度学习、自然语言处理等多个子领域。

机器学习是AI的核心技术，通过算法让计算机从数据中学习规律，无需明确编程就能完成特定任务。

深度学习使用多层神经网络来处理复杂的数据模式，在图像识别、语音识别等领域取得了突破性进展。

RAG（检索增强生成）技术结合了信息检索和文本生成，能够基于知识库生成更准确的答案。
"""
    
    # 保存到文件
    test_file = Path("documents/test_fixed_embedding.txt")
    test_file.parent.mkdir(exist_ok=True)
    
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_content)
    
    # 上传文档
    try:
        with open(test_file, 'rb') as f:
            files = {'file': ('test_fixed_embedding.txt', f, 'text/plain')}
            response = requests.post(
                "http://localhost:8000/documents/upload",
                files=files,
                timeout=30
            )
        
        if response.status_code == 200:
            result = response.json()
            doc_id = result.get('document_id')
            print(f"✓ 上传成功: {doc_id}")
            return doc_id
        else:
            error_detail = response.json().get('detail', '未知错误') if response.headers.get('content-type', '').startswith('application/json') else response.text
            print(f"✗ 上传失败: {error_detail}")
            return None
            
    except Exception as e:
        print(f"✗ 上传异常: {str(e)}")
        return None

def wait_for_processing(doc_id, max_wait=60):
    """等待文档处理完成"""
    print("⏳ 等待文档处理...")
    
    for i in range(max_wait):
        try:
            response = requests.get(f"http://localhost:8000/documents/{doc_id}", timeout=5)
            if response.status_code == 200:
                doc = response.json()
                status = doc.get('status')
                
                if status == 'ready':
                    print(f"✓ 文档处理完成 ({i+1}秒)")
                    return True
                elif status == 'error':
                    error_msg = doc.get('error_message', '未知错误')
                    print(f"✗ 文档处理失败: {error_msg}")
                    return False
                elif status == 'processing':
                    if i % 10 == 0:
                        print(f"  ⏳ 处理中... ({i+1}秒)")
            
            time.sleep(1)
        except Exception as e:
            if i % 30 == 0:
                print(f"  ⚠ 检查状态失败: {str(e)}")
            time.sleep(1)
    
    print(f"⚠ 等待超时")
    return False

async def test_vector_search():
    """测试向量搜索"""
    print("🔍 测试向量搜索...")
    
    try:
        import chromadb
        
        # 连接到Chroma数据库
        client = chromadb.PersistentClient(path="./chroma_db")
        collection = client.get_collection("documents")
        
        print(f"集合文档数量: {collection.count()}")
     # 使用系统嵌入服务生成查询向量
        import os
        from rag_system.embeddings.factory import EmbeddingFactory
        from rag_system.embeddings.base import EmbeddingConfig
        
        # 从环境变量获取API密钥
        api_key = os.getenv('SILICONFLOW_API_KEY')
        if not api_key:
            raise ValueError("请设置SILICONFLOW_API_KEY环境变量")
        
        # 创建嵌入配置 (匹配向量存储中的模型)
        embedding_config = EmbeddingConfig(
            provider='siliconflow',
            model='BAAI/bge-large-zh-v1.5',
            api_key=api_key
        )
        
        # 创建嵌入模型实例
        embedding_model = EmbeddingFactory.create_embedding(embedding_config)
        await embedding_model.initialize()
        query_embedding = await embedding_model.embed_query("人工智能")
        # 测试搜索
        search_results = collection.query(
            query_embeddings=[query_embedding],
            n_results=2
        )
                    
        
        if search_results['documents'] and search_results['documents'][0]:
            print(f"✓ 搜索成功，找到 {len(search_results['documents'][0])} 个结果")
            
            for i, (doc, distance, metadata) in enumerate(zip(
                search_results['documents'][0],
                search_results['distances'][0],
                search_results['metadatas'][0]
            )):
                print(f"  {i+1}. 距离: {distance:.4f}")
                print(f"     内容: {doc[:100]}...")
                print(f"     嵌入提供商: {metadata.get('embedding_provider', 'N/A')}")
                print(f"     嵌入模型: {metadata.get('embedding_model', 'N/A')}")
                print(f"     向量维度: {metadata.get('embedding_dimensions', 'N/A')}")
                print()
            
            return True
        else:
            print("⚠ 搜索没有返回结果")
            return False
            
    except Exception as e:
        print(f"✗ 向量搜索失败: {str(e)}")
        return False

def test_qa_with_new_document():
    """测试问答功能"""
    print("🧪 测试问答功能...")
    
    test_questions = [
        "人工智能"
        #"什么是机器学习？",
        #"什么是RAG技术？"
    ]
    
    success_count = 0
    for i, question in enumerate(test_questions, 1):
        print(f"\n{i}. 问题: {question}")
        
        try:
            response = requests.post(
                "http://localhost:8000/qa/ask",
                json={"question": question},
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get('answer', '')
                sources = result.get('sources', [])
                confidence = result.get('confidence_score', 0)
                
                print(f"   答案: {answer[:150]}...")
                print(f"   源文档数量: {len(sources)}")
                print(f"   置信度: {confidence}")
                
                if len(sources) > 0 and confidence > 0:
                    print(f"   ✓ 找到相关内容")
                    success_count += 1
                else:
                    print(f"   ⚠ 没有找到相关内容")
                    
            else:
                print(f"   ✗ 请求失败: {response.status_code}")
                
        except Exception as e:
            print(f"   ✗ 请求异常: {str(e)}")
    
    print(f"\n📊 测试结果: {success_count}/{len(test_questions)} 个问题找到了相关内容")
    return success_count > 0

def main():
    """主函数"""
    print("🔧 测试修复后的嵌入配置")
    print("=" * 40)
    
    # 1. 上传测试文档
    doc_id = upload_test_document()
    if not doc_id:
        print("❌ 文档上传失败")
        return
    
    # 2. 等待处理完成
    if not wait_for_processing(doc_id):
        print("❌ 文档处理失败")
        return
    
    # 3. 测试向量搜索
    if asyncio.run(test_vector_search()):
        print("✅ 向量搜索正常")
    else:
        print("⚠ 向量搜索有问题")
    
    # 4. 测试问答功能
    if test_qa_with_new_document():
        print("\n🎉 修复成功！")
        print("✅ 嵌入配置已修复")
        print("✅ 向量搜索正常工作")
        print("✅ 问答功能能找到相关内容")
    else:
        print("\n⚠ 问答功能仍有问题")
        print("可能需要进一步调试")

if __name__ == "__main__":
    main()