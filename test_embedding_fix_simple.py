#!/usr/bin/env python3
"""
测试嵌入修复 - 简化版本
"""
import requests
import time
from pathlib import Path

def create_simple_test_document():
    """创建一个简单的测试文档"""
    content = """
# 人工智能技术简介

人工智能（Artificial Intelligence，AI）是计算机科学的一个重要分支。

## 机器学习
机器学习是人工智能的核心技术之一，它使计算机能够从数据中学习。

## 深度学习
深度学习是机器学习的一个子集，使用多层神经网络来处理复杂数据。

## 自然语言处理
自然语言处理（NLP）使计算机能够理解、解释和生成人类语言。

## 应用领域
人工智能技术广泛应用于多个领域：
- 智能客服和聊天机器人
- 推荐系统
- 自动驾驶
- 医疗诊断

## 技术挑战
- 数据质量和隐私
- 模型可解释性
- 计算资源需求
- 鲁棒性与安全性

## 未来发展趋势
- 大型语言模型的发展
- 多模态人工智能
- 具身智能
- 神经符号结合

人工智能技术正在快速发展，为各行各业带来革命性的变化。
"""
    
    test_file = Path("simple_test_document.txt")
    test_file.write_text(content, encoding='utf-8')
    return test_file, len(content)

def test_simple_document_upload():
    """测试简单文档上传"""
    print("🧪 测试简单文档处理...")
    
    # 创建测试文档
    test_file, content_size = create_simple_test_document()
    print(f"📄 创建测试文档: {test_file.name}")
    print(f"📏 文档大小: {content_size:,} 字符")
    
    try:
        # 上传文档
        print("📤 上传文档...")
        with open(test_file, 'rb') as f:
            files = {'file': (test_file.name, f, 'text/plain')}
            response = requests.post("http://localhost:8000/documents/upload", files=files)
        
        if response.status_code == 200:
            result = response.json()
            document_id = result.get('document_id')
            print(f"✅ 文档上传成功")
            print(f"   文档ID: {document_id}")
            print(f"   状态: {result.get('status')}")
            
            # 等待处理完成
            print("⏳ 等待文档处理...")
            max_wait = 120  # 最多等待2分钟
            wait_time = 0
            
            while wait_time < max_wait:
                time.sleep(5)
                wait_time += 5
                
                # 检查处理状态
                doc_response = requests.get(f"http://localhost:8000/documents/{document_id}")
                if doc_response.status_code == 200:
                    doc_data = doc_response.json()
                    status = doc_data.get('status')
                    print(f"   状态: {status} (等待时间: {wait_time}s)")
                    
                    if status == 'ready':
                        print("✅ 文档处理完成")
                        print(f"   文本块数: {doc_data.get('chunk_count', 0)}")
                        print(f"   向量数: {doc_data.get('vector_count', 0)}")
                        
                        # 测试查询
                        if doc_data.get('vector_count', 0) > 0:
                            print("🔍 测试查询功能...")
                            query_data = {
                                "query": "什么是机器学习？",
                                "top_k": 3
                            }
                            query_response = requests.post("http://localhost:8000/qa/query", json=query_data)
                            if query_response.status_code == 200:
                                query_result = query_response.json()
                                print(f"✅ 查询成功")
                                print(f"   找到 {len(query_result.get('results', []))} 个相关结果")
                                if query_result.get('results'):
                                    print(f"   最高相似度: {query_result['results'][0].get('similarity', 0):.3f}")
                            else:
                                print(f"❌ 查询失败: {query_response.status_code}")
                        else:
                            print("⚠️ 没有向量数据，跳过查询测试")
                        
                        break
                    elif status == 'error':
                        print("❌ 文档处理失败")
                        print(f"   错误信息: {doc_data.get('error_message', 'Unknown error')}")
                        break
                else:
                    print(f"⚠️ 无法获取文档状态: {doc_response.status_code}")
            
            if wait_time >= max_wait:
                print("⏰ 等待超时")
                
        else:
            print(f"❌ 文档上传失败: {response.status_code}")
            print(f"   响应: {response.text}")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
    finally:
        # 清理测试文件
        if test_file.exists():
            test_file.unlink()
            print(f"🗑️ 清理测试文件: {test_file.name}")

def main():
    """主函数"""
    print("🚀 开始简单文档处理测试")
    print("=" * 50)
    test_simple_document_upload()
    print("=" * 50)
    print("✅ 测试完成")

if __name__ == "__main__":
    main()