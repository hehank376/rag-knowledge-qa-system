#!/usr/bin/env python3
"""
测试新文档的名称显示
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_new_document_name():
    """测试新文档的名称显示"""
    print("🔍 测试新文档的名称显示...")
    
    # 询问新文档的特定内容
    response = requests.post(f"{BASE_URL}/qa/ask", json={
        'question': '测试文档名称显示中提到了什么内容？'
    })
    
    if response.status_code == 200:
        data = response.json()
        sources = data.get('sources', [])
        print(f'问题: 测试文档名称显示中提到了什么内容？')
        print(f'源信息数量: {len(sources)}')
        
        for i, source in enumerate(sources, 1):
            document_name = source.get('document_name', 'N/A')
            similarity_score = source.get('similarity_score', 0)
            print(f'源 {i}: {document_name} (相似度: {similarity_score:.3f})')
            
            if '测试文档名称显示.txt' in document_name:
                print(f'  ✅ 找到新文档，名称显示正确！')
                return True
        
        print(f'❌ 没有找到新文档或名称显示不正确')
        return False
    else:
        print(f'❌ 请求失败: {response.status_code}')
        return False

if __name__ == "__main__":
    test_new_document_name()