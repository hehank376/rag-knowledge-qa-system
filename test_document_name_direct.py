#!/usr/bin/env python3
"""
直接测试文档名称修复
"""

import requests
import json
import tempfile
import os
import time

BASE_URL = "http://localhost:8000"

def test_document_name_direct():
    """直接测试文档名称修复"""
    print("🔍 直接测试文档名称修复...")
    
    # 1. 创建包含独特内容的测试文档
    print("\n1. 创建测试文档...")
    
    test_content = """
# 文档名称修复测试专用文档

这是一个专门用于测试文档名称修复功能的文档。

## 独特标识内容

文档名称修复测试标识符：DOCUMENT_NAME_FIX_TEST_2025

这个文档包含了独特的标识符，用于确保问答时能够检索到这个特定的文档。

## 测试内容

当用户询问关于"文档名称修复测试标识符"的问题时，应该能够检索到这个文档，
并且在源信息中显示正确的文档名称，而不是系统生成的ID。

测试关键词：文档名称修复功能验证
"""
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(test_content)
        temp_file_path = f.name
    
    try:
        # 2. 上传测试文档
        print("\n2. 上传测试文档...")
        
        with open(temp_file_path, 'rb') as f:
            files = {'file': ('文档名称修复测试.txt', f, 'text/plain')}
            response = requests.post(f"{BASE_URL}/documents/upload", files=files)
        
        if response.status_code != 200:
            print(f"❌ 文档上传失败: {response.status_code}")
            print(response.text)
            return False
        
        upload_data = response.json()
        doc_id = upload_data.get('document_id')
        print(f"✅ 文档上传成功: {doc_id}")
        print(f"   文档名称: 文档名称修复测试.txt")
        
        # 3. 等待文档处理完成
        print("\n3. 等待文档处理完成...")
        
        max_wait = 60
        wait_time = 0
        
        while wait_time < max_wait:
            doc_response = requests.get(f"{BASE_URL}/documents/{doc_id}")
            if doc_response.status_code == 200:
                doc_data = doc_response.json()
                status = doc_data.get('status')
                print(f"   文档状态: {status} (等待时间: {wait_time}s)")
                
                if status == 'ready':
                    print(f"✅ 文档处理完成")
                    break
                elif status == 'error':
                    print(f"❌ 文档处理失败: {doc_data.get('error_message', '未知错误')}")
                    return False
            
            time.sleep(5)
            wait_time += 5
        
        if wait_time >= max_wait:
            print(f"❌ 文档处理超时")
            return False
        
        # 4. 使用独特的关键词进行问答测试
        print("\n4. 测试问答，使用独特关键词...")
        
        qa_response = requests.post(f"{BASE_URL}/qa/ask", json={
            "question": "什么是文档名称修复测试标识符？"
        })
        
        if qa_response.status_code != 200:
            print(f"❌ 问答请求失败: {qa_response.status_code}")
            print(qa_response.text)
            return False
        
        qa_data = qa_response.json()
        print(f"✅ 问答请求成功")
        print(f"   答案: {qa_data.get('answer', '')[:200]}...")
        
        # 检查源信息
        sources = qa_data.get('sources', [])
        print(f"   源信息数量: {len(sources)}")
        
        found_test_doc = False
        for i, source in enumerate(sources, 1):
            document_name = source.get('document_name', 'N/A')
            document_id = source.get('document_id', 'N/A')
            similarity_score = source.get('similarity_score', 0)
            
            print(f"   源 {i}:")
            print(f"     文档ID: {document_id}")
            print(f"     文档名称: {document_name}")
            print(f"     相似度: {similarity_score:.3f}")
            
            # 检查是否是我们的测试文档
            if document_id == doc_id:
                found_test_doc = True
                print(f"     ✅ 找到测试文档！")
                
                if document_name == '文档名称修复测试.txt':
                    print(f"     ✅ 文档名称显示正确！")
                    return True
                else:
                    print(f"     ❌ 文档名称显示不正确，期望: 文档名称修复测试.txt，实际: {document_name}")
                    return False
        
        if not found_test_doc:
            print(f"   ❌ 没有找到测试文档在源信息中")
            return False
        
    finally:
        # 清理临时文件
        try:
            os.unlink(temp_file_path)
        except:
            pass

if __name__ == "__main__":
    try:
        success = test_document_name_direct()
        
        if success:
            print(f"\n🎉 文档名称修复测试成功！")
        else:
            print(f"\n❌ 文档名称修复测试失败")
            print(f"\n💡 可能的原因:")
            print(f"   1. 服务器需要重启以使代码修改生效")
            print(f"   2. 向量检索没有找到新文档")
            print(f"   3. 代码修改没有正确应用")
            
    except Exception as e:
        print(f"❌ 测试异常: {str(e)}")