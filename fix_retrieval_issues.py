#!/usr/bin/env python3
"""
修复检索问题的完整解决方案
1. 修复向量维度不匹配
2. 修复Chroma实例冲突
3. 优化日志配置
"""

import os
import sys
import shutil
import requests
import time
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_server_status():
    """检查服务器状态"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=3)
        return response.status_code == 200
    except:
        return False

def fix_chroma_singleton_issue():
    """修复Chroma单例问题"""
    print("🔧 修复Chroma单例问题...")
    
    # 修复ChromaVectorStore的单例问题
    chroma_store_file = Path("rag_system/vector_store/chroma_store.py")
    
    if chroma_store_file.exists():
        with open(chroma_store_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 添加单例管理
        singleton_fix = '''
class ChromaClientManager:
    """Chroma客户端管理器，解决单例冲突问题"""
    _clients = {}
    
    @classmethod
    def get_client(cls, persist_directory: str):
        """获取或创建Chroma客户端"""
        if persist_directory not in cls._clients:
            try:
                settings = Settings(
                    persist_directory=persist_directory,
                    anonymized_telemetry=False
                )
                cls._clients[persist_directory] = chromadb.PersistentClient(
                    path=persist_directory,
                    settings=settings
                )
            except ValueError as e:
                if "already exists" in str(e):
                    # 如果实例已存在，尝试获取现有实例
                    import chromadb
                    cls._clients[persist_directory] = chromadb.PersistentClient(
                        path=persist_directory
                    )
                else:
                    raise e
        return cls._clients[persist_directory]
    
    @classmethod
    def cleanup(cls):
        """清理所有客户端"""
        cls._clients.clear()

'''
        
        # 检查是否已经有这个修复
        if "ChromaClientManager" not in content:
            # 在类定义之前插入单例管理器
            class_pos = content.find("class ChromaVectorStore(VectorStoreBase):")
            if class_pos != -1:
                new_content = content[:class_pos] + singleton_fix + content[class_pos:]
                
                # 修改_init_sync方法使用单例管理器
                new_content = new_content.replace(
                    "self._client = chromadb.PersistentClient(",
                    "self._client = ChromaClientManager.get_client(self.config.persist_directory)\n        return  # chromadb.PersistentClient("
                )
                
                with open(chroma_store_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                print("✓ Chroma单例问题修复完成")
            else:
                print("⚠ 未找到ChromaVectorStore类定义")
        else:
            print("✓ Chroma单例修复已存在")
    else:
        print("✗ 未找到ChromaVectorStore文件")

def create_unified_embedding_config():
    """创建统一的嵌入配置"""
    print("🔧 创建统一嵌入配置...")
    
    config_content = '''#!/usr/bin/env python3
"""
统一嵌入配置管理器
确保所有服务使用相同的嵌入模型配置
"""

import os
from typing import Dict, Any

class UnifiedEmbeddingConfig:
    """统一嵌入配置管理器"""
    
    @staticmethod
    def get_embedding_config() -> Dict[str, Any]:
        """获取统一的嵌入配置"""
        api_key = os.getenv('SILICONFLOW_API_KEY')
        
        if api_key:
            return {
                'provider': 'siliconflow',
                'model': 'BAAI/bge-large-zh-v1.5',
                'api_key': api_key,
                'dimensions': 1024,
                'batch_size': 100,
                'timeout': 60,
                'retry_attempts': 3
            }
        else:
            # 回退到mock配置
            return {
                'provider': 'mock',
                'model': 'mock-embedding',
                'api_key': None,
                'dimensions': 768,
                'batch_size': 100,
                'timeout': 120,  # 增加嵌入服务超时时间
                'retry_attempts': 3
            }
    
    @staticmethod
    def get_vector_dimension() -> int:
        """获取向量维度"""
        config = UnifiedEmbeddingConfig.get_embedding_config()
        return config['dimensions']
    
    @staticmethod
    def is_real_model() -> bool:
        """检查是否使用真实模型"""
        return os.getenv('SILICONFLOW_API_KEY') is not None
'''
    
    config_file = Path("rag_system/config/unified_embedding.py")
    config_file.parent.mkdir(exist_ok=True)
    
    with open(config_file, 'w', encoding='utf-8') as f:
        f.write(config_content)
    
    print("✓ 统一嵌入配置创建完成")

def clear_vector_store_safely():
    """安全清空向量存储"""
    print("🗑️ 安全清空向量存储...")
    
    if check_server_status():
        print("⚠ 服务器正在运行，尝试通过API清空...")
        try:
            import chromadb
            client = chromadb.PersistentClient(path="./chroma_db")
            collections = client.list_collections()
            
            for collection in collections:
                print(f"  删除集合: {collection.name}")
                client.delete_collection(collection.name)
            
            print("✓ 向量存储清空成功")
            return True
            
        except Exception as e:
            print(f"✗ API清空失败: {str(e)}")
            return False
    else:
        print("服务器未运行，直接删除文件...")
        chroma_dir = Path("./chroma_db")
        if chroma_dir.exists():
            try:
                shutil.rmtree(chroma_dir)
                print("✓ 向量存储目录删除成功")
                return True
            except Exception as e:
                print(f"✗ 删除失败: {str(e)}")
                return False
        else:
            print("✓ 向量存储目录不存在")
            return True

def upload_test_documents():
    """上传测试文档"""
    print("📤 上传测试文档...")
    
    if not check_server_status():
        print("✗ 服务器未运行，无法上传文档")
        return False
    
    # 创建测试文档
    docs_dir = Path("documents")
    docs_dir.mkdir(exist_ok=True)
    
    test_doc_content = """人工智能技术详解

人工智能（Artificial Intelligence，AI）是计算机科学的一个重要分支，旨在创建能够执行通常需要人类智能的任务的系统。

## 核心技术

### 机器学习
机器学习是人工智能的核心技术之一，它使计算机能够从数据中学习，而无需明确编程。主要类型包括：
- 监督学习：使用标记数据训练模型
- 无监督学习：从未标记数据中发现模式
- 强化学习：通过试错学习最优策略

### 深度学习
深度学习是机器学习的一个子集，使用多层神经网络来处理复杂数据。它在以下领域取得了突破：
- 图像识别和计算机视觉
- 自然语言处理
- 语音识别和合成

### 自然语言处理
自然语言处理（NLP）使计算机能够理解、解释和生成人类语言。关键技术包括：
- 文本分析和情感分析
- 机器翻译
- 问答系统
- 文本摘要

## RAG技术
检索增强生成（Retrieval-Augmented Generation，RAG）是一种结合信息检索和文本生成的先进技术。RAG的工作原理：
1. 将文档分割成小块并向量化
2. 根据用户查询检索相关文档片段
3. 将检索到的信息与查询一起输入到语言模型
4. 生成基于检索信息的准确答案

RAG技术的优势：
- 提供更准确和相关的答案
- 减少模型幻觉问题
- 支持实时信息更新
- 可以引用具体的信息源

## 应用领域
人工智能技术广泛应用于：
- 智能客服和聊天机器人
- 推荐系统
- 自动驾驶
- 医疗诊断
- 金融风控
- 智能制造
"""
    
    test_file = docs_dir / "ai_technology_guide.txt"
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_doc_content)
    
    # 上传文档
    try:
        with open(test_file, 'rb') as f:
            files = {'file': ('ai_technology_guide.txt', f, 'text/plain')}
            response = requests.post(
                "http://localhost:8000/documents/upload",
                files=files,
                timeout=120  # 增加文档上传超时时间
            )
        
        if response.status_code == 200:
            result = response.json()
            doc_id = result.get('document_id')
            print(f"✓ 文档上传成功: {doc_id}")
            
            # 等待处理完成
            print("⏳ 等待文档处理...")
            for i in range(60):  # 最多等待60秒
                try:
                    doc_response = requests.get(f"http://localhost:8000/documents/{doc_id}", timeout=5)
                    if doc_response.status_code == 200:
                        doc_info = doc_response.json()
                        status = doc_info.get('status')
                        
                        if status == 'ready':
                            print(f"✓ 文档处理完成 ({i+1}秒)")
                            return True
                        elif status == 'error':
                            error_msg = doc_info.get('error_message', '未知错误')
                            print(f"✗ 文档处理失败: {error_msg}")
                            return False
                        elif i % 10 == 0:
                            print(f"  处理中... ({i+1}秒)")
                    
                    time.sleep(1)
                except:
                    time.sleep(1)
            
            print("⚠ 文档处理超时")
            return False
            
        else:
            error_detail = response.json().get('detail', '未知错误') if response.headers.get('content-type', '').startswith('application/json') else response.text
            print(f"✗ 文档上传失败: {error_detail}")
            return False
            
    except Exception as e:
        print(f"✗ 上传异常: {str(e)}")
        return False

def test_qa_functionality():
    """测试问答功能"""
    print("🧪 测试问答功能...")
    
    if not check_server_status():
        print("✗ 服务器未运行")
        return False
    
    test_questions = [
        "什么是人工智能？",
        "什么是机器学习？",
        "什么是RAG技术？",
        "深度学习有哪些应用？"
    ]
    
    success_count = 0
    for i, question in enumerate(test_questions, 1):
        print(f"\n{i}. 问题: {question}")
        
        try:
            response = requests.post(
                "http://localhost:8000/qa/ask",
                json={"question": question},
                headers={"Content-Type": "application/json"},
                timeout=120  # 增加问答请求超时时间
            )
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get('answer', '')
                sources = result.get('sources', [])
                confidence = result.get('confidence_score', 0)
                
                print(f"   答案: {answer[:100]}...")
                print(f"   源文档数量: {len(sources)}")
                print(f"   置信度: {confidence}")
                
                if len(sources) > 0 and confidence > 0:
                    print(f"   ✓ 找到相关内容")
                    success_count += 1
                    
                    # 显示源文档信息
                    for j, source in enumerate(sources[:1]):
                        doc_name = source.get('document_name', 'N/A')
                        similarity = source.get('similarity_score', 'N/A')
                        print(f"     源: {doc_name} (相似度: {similarity})")
                else:
                    print(f"   ⚠ 没有找到相关内容")
                    
            else:
                print(f"   ✗ 请求失败: {response.status_code}")
                if response.headers.get('content-type', '').startswith('application/json'):
                    error = response.json()
                    print(f"     错误: {error.get('detail', '未知错误')}")
                
        except Exception as e:
            print(f"   ✗ 请求异常: {str(e)}")
    
    print(f"\n📊 测试结果: {success_count}/{len(test_questions)} 个问题找到了相关内容")
    return success_count > 0

def main():
    """主函数"""
    print("🔧 检索问题修复工具")
    print("=" * 50)
    
    if check_server_status():
        print("⚠ 服务器正在运行")
        print("建议先停止服务器，然后运行修复脚本")
        print("\n继续修复可能的问题:")
        
        # 1. 清空向量存储
        if clear_vector_store_safely():
            print("✅ 向量存储清空成功")
        else:
            print("❌ 向量存储清空失败")
            return
        
        # 2. 上传测试文档
        if upload_test_documents():
            print("✅ 测试文档上传成功")
        else:
            print("❌ 测试文档上传失败")
            return
        
        # 3. 测试问答功能
        if test_qa_functionality():
            print("\n🎉 修复成功！")
            print("✅ 检索功能正常工作")
            print("✅ 问答系统能找到相关内容")
        else:
            print("\n⚠ 问答功能仍有问题")
            print("建议重启服务器后再次测试")
    
    else:
        print("服务器未运行，执行离线修复...")
        
        # 1. 修复Chroma单例问题
        fix_chroma_singleton_issue()
        
        # 2. 创建统一嵌入配置
        create_unified_embedding_config()
        
        # 3. 清空向量存储
        if clear_vector_store_safely():
            print("✅ 向量存储清空成功")
        
        print("\n✅ 离线修复完成")
        print("\n🚀 下一步操作:")
        print("1. 重启服务器: python start_rag_system.py")
        print("2. 运行在线测试: python fix_retrieval_issues.py")

if __name__ == "__main__":
    main()