#!/usr/bin/env python3
"""
通过API清空向量存储
"""

import requests

def clear_vector_store():
    """清空向量存储"""
    print("🗑️ 清空向量存储...")
    
    try:
        # 尝试通过API清空（如果有这样的端点）
        response = requests.delete("http://localhost:8000/documents/", timeout=30)
        
        if response.status_code == 200:
            print("✓ 向量存储清空成功")
            return True
        else:
            print(f"⚠ API清空失败: {response.status_code}")
            
    except Exception as e:
        print(f"⚠ API清空异常: {str(e)}")
    
    # 如果API方法不行，尝试直接操作Chroma
    try:
        import chromadb
        
        print("🔄 尝试直接清空Chroma集合...")
        client = chromadb.PersistentClient(path="./chroma_db")
        
        # 获取所有集合
        collections = client.list_collections()
        
        for collection in collections:
            print(f"  删除集合: {collection.name}")
            client.delete_collection(collection.name)
        
        print("✓ Chroma集合清空成功")
        return True
        
    except Exception as e:
        print(f"✗ Chroma清空失败: {str(e)}")
        return False

def main():
    """主函数"""
    print("🧹 清空向量存储工具")
    print("=" * 30)
    
    if clear_vector_store():
        print("\n✅ 向量存储已清空")
        print("现在可以重新上传文档了")
        print("\n🚀 下一步:")
        print("python test_fixed_embedding.py")
    else:
        print("\n❌ 清空失败")
        print("可能需要重启服务器后手动删除")

if __name__ == "__main__":
    main()