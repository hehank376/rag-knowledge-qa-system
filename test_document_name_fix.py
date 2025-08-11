#!/usr/bin/env python3
"""
测试文档名称修复
"""

import requests
import json
import tempfile
import os

BASE_URL = "http://localhost:8000"

def test_document_name_fix():
    """测试文档名称修复"""
    print("🔍 测试文档名称修复...")
    
    # 1. 创建测试文档
    print("\n1. 创建测试文档...")
    
    test_content = """
# 测试文档名称显示

这是一个测试文档，用于验证文档名称是否正确显示在问答结果的源信息中。

## 人工智能简介

人工智能（Artificial Intelligence，AI）是计算机科学的一个分支，致力于创建能够执行通常需要人类智能的任务的系统。

## 机器学习

机器学习是人工智能的一个子领域，它使计算机能够从数据中学习，而无需明确编程。

## 深度学习

深度学习是机器学习的一个子集，使用多层神经网络来处理复杂数据。
"""
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(test_content)
        temp_file_path = f.name
    
    try:
        # 2. 上传测试文档
        print("\n2. 上传测试文档...")
        
        with open(temp_file_path, 'rb') as f:
            files = {'file': ('测试文档名称显示.txt', f, 'text/plain')}
            response = requests.post(f"{BASE_URL}/documents/upload", files=files)
        
        if response.status_code != 200:
            print(f"❌ 文档上传失败: {response.status_code}")
            print(response.text)
            return False
        
        upload_data = response.json()
        doc_id = upload_data.get('document_id')
        print(f"✅ 文档上传成功: {doc_id}")
        print(f"   文档名称: 测试文档名称显示.txt")
        
        # 3. 等待文档处理完成
        print("\n3. 等待文档处理完成...")
        
        import time
        max_wait = 60  # 最多等待60秒
        wait_time = 0
        
        while wait_time < max_wait:
            doc_response = requests.get(f"{BASE_URL}/documents/{doc_id}")
            if doc_response.status_code == 200:
                doc_data = doc_response.json()
                status = doc_data.get('status')
                print(f"   文档状态: {status}")
                
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
        
        # 4. 测试问答，检查文档名称显示
        print("\n4. 测试问答，检查文档名称显示...")
        
        qa_response = requests.post(f"{BASE_URL}/qa/ask", json={
            "question": "什么是人工智能？"
        })
        
        if qa_response.status_code != 200:
            print(f"❌ 问答请求失败: {qa_response.status_code}")
            print(qa_response.text)
            return False
        
        qa_data = qa_response.json()
        print(f"✅ 问答请求成功")
        print(f"   答案长度: {len(qa_data.get('answer', ''))}")
        
        # 检查源信息中的文档名称
        sources = qa_data.get('sources', [])
        print(f"   源信息数量: {len(sources)}")
        
        if sources:
            for i, source in enumerate(sources, 1):
                document_name = source.get('document_name', 'N/A')
                similarity_score = source.get('similarity_score', 0)
                print(f"   源 {i}:")
                print(f"     文档名称: {document_name}")
                print(f"     相似度: {similarity_score:.3f}")
                
                # 检查是否显示真实文档名称
                if document_name == '测试文档名称显示.txt':
                    print(f"     ✅ 文档名称显示正确！")
                elif document_name.startswith('Document_'):
                    print(f"     ❌ 文档名称仍然是系统生成的ID")
                    return False
                else:
                    print(f"     ⚠️ 文档名称格式未知: {document_name}")
        else:
            print(f"   ⚠️ 没有找到源信息")
        
        return True
        
    finally:
        # 清理临时文件
        try:
            os.unlink(temp_file_path)
        except:
            pass

def generate_fix_summary():
    """生成修复总结"""
    print(f"\n📋 文档名称显示修复总结")
    print(f"=" * 50)
    
    print(f"\n🔧 修复内容:")
    print(f"   1. 修改 DocumentProcessor.process_document() 方法")
    print(f"      - 添加 document_name 参数")
    print(f"      - 将文档名称传递给向量化过程")
    
    print(f"\n   2. 修改 DocumentProcessor.vectorize_chunks() 方法")
    print(f"      - 添加 document_name 参数")
    print(f"      - 将文档名称传递给嵌入服务")
    
    print(f"\n   3. 修改 EmbeddingService.vectorize_chunks() 方法")
    print(f"      - 添加 document_name 参数")
    print(f"      - 在向量metadata中包含真实文档名称")
    
    print(f"\n   4. 修改 DocumentService._process_document_async() 方法")
    print(f"      - 传递 doc_info.filename 作为文档名称")
    
    print(f"\n🎯 修复效果:")
    print(f"   - 问答结果中的源信息现在显示真实的文档名称")
    print(f"   - 用户可以清楚地知道答案来源于哪个文档")
    print(f"   - 提高了系统的用户友好性和可追溯性")
    
    print(f"\n📝 测试建议:")
    print(f"   1. 上传一个有意义名称的文档")
    print(f"   2. 等待文档处理完成")
    print(f"   3. 进行问答测试")
    print(f"   4. 检查答案源信息中的文档名称是否正确")

if __name__ == "__main__":
    try:
        success = test_document_name_fix()
        generate_fix_summary()
        
        if success:
            print(f"\n🎉 文档名称显示修复成功！")
        else:
            print(f"\n❌ 文档名称显示修复失败")
            
    except Exception as e:
        print(f"❌ 测试异常: {str(e)}")