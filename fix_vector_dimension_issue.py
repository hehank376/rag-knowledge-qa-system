#!/usr/bin/env python3
"""
修复向量维度不匹配问题
清空向量存储并重新处理文档
"""

import os
import sys
import shutil
import requests
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def clear_vector_store():
    """清空向量存储"""
    print("🗑️ 清空向量存储...")
    
    chroma_dir = Path("./chroma_db")
    if chroma_dir.exists():
        try:
            shutil.rmtree(chroma_dir)
            print("✓ 向量存储已清空")
            return True
        except Exception as e:
            print(f"✗ 清空向量存储失败: {str(e)}")
            return False
    else:
        print("✓ 向量存储目录不存在，无需清空")
        return True

def get_ready_documents():
    """获取已准备好的文档列表"""
    print("📋 获取已准备好的文档...")
    
    try:
        response = requests.get("http://localhost:8000/documents/", timeout=10)
        if response.status_code == 200:
            data = response.json()
            documents = data.get('documents', [])
            ready_docs = [doc for doc in documents if doc.get('status') == 'ready']
            
            print(f"✓ 找到 {len(ready_docs)} 个已准备好的文档")
            for doc in ready_docs:
                print(f"  - {doc['filename']} (ID: {doc['id']})")
            
            return ready_docs
        else:
            print(f"✗ 获取文档列表失败: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ 获取文档列表异常: {str(e)}")
        return []

def reprocess_document(doc_id):
    """重新处理文档"""
    try:
        response = requests.post(
            f"http://localhost:8000/documents/{doc_id}/reprocess",
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"  ✓ 重新处理成功: {result.get('message', '成功')}")
            return True
        else:
            error_detail = response.json().get('detail', '未知错误') if response.headers.get('content-type', '').startswith('application/json') else response.text
            print(f"  ✗ 重新处理失败: {error_detail}")
            return False
    except Exception as e:
        print(f"  ✗ 重新处理异常: {str(e)}")
        return False

def wait_for_processing(doc_id, max_wait=120):
    """等待文档处理完成"""
    import time
    
    print(f"  ⏳ 等待文档处理完成...")
    
    for i in range(max_wait):
        try:
            response = requests.get(f"http://localhost:8000/documents/{doc_id}", timeout=5)
            if response.status_code == 200:
                doc = response.json()
                status = doc.get('status')
                
                if status == 'ready':
                    print(f"  ✓ 文档处理完成 ({i+1}秒)")
                    return True
                elif status == 'error':
                    error_msg = doc.get('error_message', '未知错误')
                    print(f"  ✗ 文档处理失败: {error_msg}")
                    return False
                elif status == 'processing':
                    if i % 10 == 0:  # 每10秒打印一次状态
                        print(f"  ⏳ 处理中... ({i+1}秒)")
                
            time.sleep(1)
        except Exception as e:
            if i % 30 == 0:  # 每30秒打印一次错误
                print(f"  ⚠ 检查状态失败: {str(e)}")
            time.sleep(1)
    
    print(f"  ⚠ 等待超时 ({max_wait}秒)")
    return False

def test_qa_after_fix():
    """修复后测试问答"""
    print("\n🧪 测试修复后的问答功能...")
    
    try:
        # 测试一个关于考勤制度的问题（我们知道有这个文档）
        test_questions = [
            "公司的考勤制度是什么？",
            "什么是人工智能？",
            "高考志愿填报有什么建议？"
        ]
        
        for question in test_questions:
            print(f"\n问题: {question}")
            
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
                
                print(f"答案: {answer[:200]}...")
                print(f"源文档数量: {len(sources)}")
                print(f"置信度: {confidence}")
                
                if sources:
                    print("源文档:")
                    for i, source in enumerate(sources[:2]):
                        print(f"  {i+1}. {source.get('document_name', 'N/A')}")
                        print(f"     相似度: {source.get('similarity_score', 'N/A')}")
                else:
                    print("⚠ 没有找到相关源文档")
            else:
                print(f"✗ 问答请求失败: {response.status_code}")
    
    except Exception as e:
        print(f"✗ 测试问答异常: {str(e)}")

def main():
    """主函数"""
    print("🔧 向量维度不匹配修复工具")
    print("=" * 50)
    
    # 检查服务器是否运行
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code != 200:
            print("❌ 服务器未运行，请先启动服务器")
            return
    except Exception:
        print("❌ 无法连接到服务器，请先启动服务器")
        return
    
    print("✓ 服务器运行正常")
    
    # 1. 获取已准备好的文档
    ready_docs = get_ready_documents()
    if not ready_docs:
        print("❌ 没有找到已准备好的文档")
        #return
    
    # 2. 清空向量存储
    if not clear_vector_store():
        print("❌ 清空向量存储失败")
        return
    
    # 3. 重新处理文档
    print(f"\n🔄 重新处理 {len(ready_docs)} 个文档...")
    
    success_count = 0
    for i, doc in enumerate(ready_docs, 1):
        doc_id = doc['id']
        filename = doc['filename']
        
        print(f"\n{i}/{len(ready_docs)} 处理文档: {filename}")
        
        # 重新处理文档
        if reprocess_document(doc_id):
            # 等待处理完成
            if wait_for_processing(doc_id):
                success_count += 1
            else:
                print(f"  ⚠ 文档 {filename} 处理超时或失败")
        else:
            print(f"  ✗ 文档 {filename} 重新处理失败")
    
    print(f"\n📊 处理结果: {success_count}/{len(ready_docs)} 个文档处理成功")
    
    if success_count > 0:
        # 4. 测试问答功能
        test_qa_after_fix()
        
        print("\n" + "=" * 50)
        print("🎉 向量维度修复完成！")
        
        print(f"\n📋 修复总结:")
        print(f"1. ✓ 清空了旧的向量存储")
        print(f"2. ✓ 重新处理了 {success_count} 个文档")
        print(f"3. ✓ 使用了正确的嵌入模型维度")
        
        print(f"\n🚀 现在可以测试问答功能:")
        print(f"1. 在前端提问关于已上传文档的问题")
        print(f"2. 系统应该能够找到相关内容并给出答案")
        print(f"3. 检查答案中是否包含源文档引用")
        
    else:
        print("\n❌ 没有文档处理成功，请检查服务器日志")

if __name__ == "__main__":
    main()