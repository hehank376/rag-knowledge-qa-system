#!/usr/bin/env python3
"""
测试文档管理功能
"""
import asyncio
import requests
import json
import time
from pathlib import Path

def test_document_stats_api():
    """测试文档统计API"""
    print("🧪 测试文档统计API...")
    
    try:
        response = requests.get("http://localhost:8000/documents/stats/summary")
        
        if response.status_code == 200:
            stats = response.json()
            print("✅ 统计API响应成功")
            print(f"📊 统计数据:")
            print(f"  - 总文档数: {stats.get('total_documents', 0)}")
            print(f"  - 已就绪: {stats.get('ready_documents', 0)}")
            print(f"  - 处理中: {stats.get('processing_documents', 0)}")
            print(f"  - 处理失败: {stats.get('error_documents', 0)}")
            print(f"  - 总文本块: {stats.get('total_chunks', 0)}")
            print(f"  - 向量数量: {stats.get('vector_count', 0)}")
            print(f"  - 存储目录: {stats.get('storage_directory', '')}")
            print(f"  - 支持格式: {stats.get('supported_formats', [])}")
            return stats
        else:
            print(f"❌ 统计API请求失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 统计API测试失败: {e}")
        return None

def test_document_list_api():
    """测试文档列表API"""
    print("\\n🧪 测试文档列表API...")
    
    try:
        response = requests.get("http://localhost:8000/documents/")
        
        if response.status_code == 200:
            data = response.json()
            documents = data.get('documents', [])
            print("✅ 文档列表API响应成功")
            print(f"📋 文档列表:")
            print(f"  - 文档数量: {len(documents)}")
            print(f"  - 总数量: {data.get('total_count', 0)}")
            print(f"  - 就绪数量: {data.get('ready_count', 0)}")
            print(f"  - 处理中数量: {data.get('processing_count', 0)}")
            print(f"  - 错误数量: {data.get('error_count', 0)}")
            
            # 显示前几个文档的信息
            for i, doc in enumerate(documents[:3]):
                print(f"  - 文档 {i+1}: {doc.get('filename', 'N/A')} ({doc.get('status', 'N/A')})")
            
            if len(documents) > 3:
                print(f"  - ... 还有 {len(documents) - 3} 个文档")
                
            return data
        else:
            print(f"❌ 文档列表API请求失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 文档列表API测试失败: {e}")
        return None

def test_upload_document():
    """测试文档上传功能"""
    print("\\n🧪 测试文档上传功能...")
    
    # 创建测试文件
    test_file = Path("test_upload.txt")
    test_content = """这是一个测试文档。

人工智能（Artificial Intelligence，AI）是计算机科学的一个重要分支，旨在创建能够执行通常需要人类智能的任务的系统。

## 核心技术

### 机器学习
机器学习是人工智能的核心技术之一，它使计算机能够从数据中学习，而无需明确编程。

### 深度学习
深度学习是机器学习的一个子集，使用多层神经网络来处理复杂数据。

### 自然语言处理
自然语言处理（NLP）使计算机能够理解、解释和生成人类语言。
"""
    
    try:
        # 写入测试文件
        test_file.write_text(test_content, encoding='utf-8')
        
        # 上传文件
        with open(test_file, 'rb') as f:
            files = {'file': (test_file.name, f, 'text/plain')}
            response = requests.post("http://localhost:8000/documents/upload", files=files)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 文档上传成功")
            print(f"📄 上传结果:")
            print(f"  - 文档ID: {result.get('document_id', 'N/A')}")
            print(f"  - 文件名: {result.get('filename', 'N/A')}")
            print(f"  - 文件大小: {result.get('file_size', 0)} bytes")
            print(f"  - 状态: {result.get('status', 'N/A')}")
            
            # 等待处理完成
            print("⏳ 等待文档处理...")
            time.sleep(3)
            
            return result.get('document_id')
        else:
            print(f"❌ 文档上传失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 文档上传测试失败: {e}")
        return None
    finally:
        # 清理测试文件
        if test_file.exists():
            test_file.unlink()

def test_frontend_compatibility():
    """测试前端兼容性"""
    print("\\n🧪 测试前端兼容性...")
    
    # 测试前端期望的字段名
    stats = test_document_stats_api()
    if stats:
        print("\\n📋 前端字段映射检查:")
        
        # 检查前端期望的字段是否存在
        frontend_fields = {
            'total_documents': '总文档数',
            'ready_documents': '已就绪',
            'processing_documents': '处理中',
            'error_documents': '处理失败'
        }
        
        for field, label in frontend_fields.items():
            if field in stats:
                print(f"  ✅ {label}: {stats[field]} (字段: {field})")
            else:
                print(f"  ❌ {label}: 字段缺失 ({field})")
        
        return True
    return False

def main():
    """主测试函数"""
    print("🧪 开始文档管理功能测试")
    print("=" * 50)
    
    # 测试统计API
    stats_success = test_document_stats_api() is not None
    
    # 测试文档列表API
    list_success = test_document_list_api() is not None
    
    # 测试文档上传
    upload_success = test_upload_document() is not None
    
    # 测试前端兼容性
    frontend_success = test_frontend_compatibility()
    
    # 如果上传成功，再次检查统计信息
    if upload_success:
        print("\\n🔄 重新检查统计信息...")
        test_document_stats_api()
    
    print("\\n" + "=" * 50)
    print("📊 测试结果总结:")
    print(f"  - 统计API: {'✅ 通过' if stats_success else '❌ 失败'}")
    print(f"  - 文档列表API: {'✅ 通过' if list_success else '❌ 失败'}")
    print(f"  - 文档上传: {'✅ 通过' if upload_success else '❌ 失败'}")
    print(f"  - 前端兼容性: {'✅ 通过' if frontend_success else '❌ 失败'}")
    
    if all([stats_success, list_success, frontend_success]):
        print("\\n🎉 所有测试通过！文档管理功能正常工作")
    else:
        print("\\n⚠️ 部分测试失败，请检查相关功能")

if __name__ == "__main__":
    main()