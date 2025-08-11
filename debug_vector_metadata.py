#!/usr/bin/env python3
"""
调试向量metadata
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def debug_vector_metadata():
    """调试向量metadata"""
    print("🔍 调试向量metadata...")
    
    # 1. 获取文档列表
    print("\n1. 获取文档列表...")
    
    docs_response = requests.get(f"{BASE_URL}/documents/")
    if docs_response.status_code != 200:
        print(f"❌ 获取文档列表失败: {docs_response.status_code}")
        return
    
    docs_data = docs_response.json()
    documents = docs_data.get('documents', [])
    
    print(f"✅ 找到 {len(documents)} 个文档")
    
    # 找到最新的文档
    latest_doc = None
    for doc in documents:
        if '测试文档名称显示.txt' in doc.get('filename', ''):
            latest_doc = doc
            break
    
    if not latest_doc:
        print(f"❌ 没有找到测试文档")
        return
    
    print(f"✅ 找到测试文档:")
    print(f"   ID: {latest_doc.get('id')}")
    print(f"   文件名: {latest_doc.get('filename')}")
    print(f"   状态: {latest_doc.get('status')}")
    print(f"   块数: {latest_doc.get('chunk_count', 0)}")
    
    # 2. 测试问答并查看详细的源信息
    print(f"\n2. 测试问答并查看源信息...")
    
    qa_response = requests.post(f"{BASE_URL}/qa/ask", json={
        'question': '这个测试文档是关于什么的？'
    })
    
    if qa_response.status_code != 200:
        print(f"❌ 问答请求失败: {qa_response.status_code}")
        return
    
    qa_data = qa_response.json()
    sources = qa_data.get('sources', [])
    
    print(f"✅ 问答成功，找到 {len(sources)} 个源")
    
    for i, source in enumerate(sources, 1):
        print(f"\n源 {i}:")
        print(f"   文档ID: {source.get('document_id', 'N/A')}")
        print(f"   文档名称: {source.get('document_name', 'N/A')}")
        print(f"   块ID: {source.get('chunk_id', 'N/A')}")
        print(f"   相似度: {source.get('similarity_score', 0):.3f}")
        print(f"   内容预览: {source.get('chunk_content', 'N/A')[:100]}...")
        
        # 检查是否是我们的测试文档
        if source.get('document_id') == latest_doc.get('id'):
            print(f"   ✅ 这是我们的测试文档！")
            if source.get('document_name') == '测试文档名称显示.txt':
                print(f"   ✅ 文档名称显示正确！")
            else:
                print(f"   ❌ 文档名称显示不正确")

if __name__ == "__main__":
    debug_vector_metadata()