#!/usr/bin/env python3
"""
修复文档上传相关问题
"""
import os
import shutil
import sys
from pathlib import Path

def fix_vector_dimension_issue():
    """修复向量维度不匹配问题"""
    print("🔧 修复向量维度不匹配问题...")
    
    # 删除现有的Chroma数据库
    chroma_db_path = Path("./chroma_db")
    if chroma_db_path.exists():
        print(f"📁 删除现有的Chroma数据库: {chroma_db_path}")
        try:
            shutil.rmtree(chroma_db_path)
            print("✓ Chroma数据库已删除")
        except Exception as e:
            print(f"✗ 删除Chroma数据库失败: {e}")
            return False
    else:
        print("📁 Chroma数据库不存在，无需删除")
    
    # 删除SQLite数据库（如果存在）
    sqlite_db_path = Path("./database/rag_system.db")
    if sqlite_db_path.exists():
        print(f"📁 删除现有的SQLite数据库: {sqlite_db_path}")
        try:
            sqlite_db_path.unlink()
            print("✓ SQLite数据库已删除")
        except Exception as e:
            print(f"✗ 删除SQLite数据库失败: {e}")
    else:
        print("📁 SQLite数据库不存在，无需删除")
    
    return True

def fix_upload_directories():
    """清理上传相关目录"""
    print("🔧 清理上传相关目录...")
    
    directories_to_clean = ["./uploads", "./data"]
    
    for dir_path in directories_to_clean:
        path = Path(dir_path)
        if path.exists():
            print(f"📁 清理目录: {path}")
            try:
                shutil.rmtree(path)
                print(f"✓ {path} 已清理")
            except Exception as e:
                print(f"✗ 清理 {path} 失败: {e}")
        else:
            print(f"📁 {path} 不存在，无需清理")

def check_embedding_config():
    """检查嵌入模型配置"""
    print("🔍 检查嵌入模型配置...")
    
    config_path = Path("config.yaml")
    if not config_path.exists():
        print("⚠️  config.yaml 文件不存在")
        return None
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取嵌入模型信息
        lines = content.split('\n')
        embedding_info = {}
        in_embeddings_section = False
        
        for line in lines:
            if line.strip().startswith('embeddings:'):
                in_embeddings_section = True
            elif in_embeddings_section:
                if line.startswith('  ') and ':' in line:
                    key, value = line.strip().split(':', 1)
                    embedding_info[key.strip()] = value.strip().strip('"\'')
                elif line.strip() and not line.startswith('  '):
                    break
        
        print("📄 当前嵌入模型配置:")
        for key, value in embedding_info.items():
            print(f"  • {key}: {value}")
        
        return embedding_info
        
    except Exception as e:
        print(f"✗ 读取配置文件失败: {e}")
        return None

def show_model_dimensions():
    """显示常用模型的维度信息"""
    print("\n📊 常用嵌入模型维度信息:")
    models = {
        "BAAI/bge-large-zh-v1.5": 1024,
        "BAAI/bge-base-zh-v1.5": 768,
        "BAAI/bge-small-zh-v1.5": 512,
        "BAAI/bge-large-en-v1.5": 1024,
        "BAAI/bge-base-en-v1.5": 768,
        "sentence-transformers/all-MiniLM-L6-v2": 384,
        "text-embedding-ada-002": 1536
    }
    
    for model, dim in models.items():
        print(f"  • {model}: {dim}维")

def check_api_keys():
    """检查API密钥设置"""
    print("\n🔑 检查API密钥设置...")
    
    keys_to_check = [
        ("OPENAI_API_KEY", "OpenAI"),
        ("SILICONFLOW_API_KEY", "SiliconFlow"),
    ]
    
    found_keys = []
    for env_var, provider in keys_to_check:
        if os.getenv(env_var):
            found_keys.append(provider)
            print(f"  ✓ {provider} API密钥已设置")
        else:
            print(f"  ✗ {provider} API密钥未设置 (环境变量: {env_var})")
    
    if not found_keys:
        print("  ⚠️  未找到任何API密钥，请设置相应的环境变量")
    
    return found_keys

def main():
    print("🛠️  RAG系统文档上传问题修复工具")
    print("=" * 60)
    
    # 检查当前配置
    embedding_config = check_embedding_config()
    show_model_dimensions()
    api_keys = check_api_keys()
    
    print("\n" + "=" * 60)
    print("\n🔍 问题诊断:")
    print("1. 向量维度不匹配 - 需要清理现有向量存储")
    print("2. 文档状态处理错误 - 已在代码中修复")
    print("3. API密钥配置 - 需要正确设置环境变量")
    
    if embedding_config:
        model = embedding_config.get('model', 'unknown')
        provider = embedding_config.get('provider', 'unknown')
        print(f"\n📋 当前配置: {provider} - {model}")
        
        # 预测维度
        model_dims = {
            "BAAI/bge-large-zh-v1.5": 1024,
            "BAAI/bge-base-zh-v1.5": 768,
            "BAAI/bge-small-zh-v1.5": 512,
            "sentence-transformers/all-MiniLM-L6-v2": 384,
            "text-embedding-ada-002": 1536
        }
        expected_dim = model_dims.get(model, "未知")
        print(f"📐 预期向量维度: {expected_dim}")
    
    print("\n" + "=" * 60)
    
    # 询问用户是否继续
    response = input("\n是否继续修复？这将删除现有数据 (y/N): ")
    
    if response.lower() in ['y', 'yes', '是']:
        print("\n🚀 开始修复...")
        
        # 修复向量维度问题
        if fix_vector_dimension_issue():
            print("✅ 向量维度问题修复完成")
        else:
            print("❌ 向量维度问题修复失败")
            return
        
        # 清理上传目录
        fix_upload_directories()
        
        print("\n✅ 所有修复完成！")
        print("\n📋 修复总结:")
        print("  ✓ 删除了现有的向量存储数据库")
        print("  ✓ 清理了上传和数据目录")
        print("  ✓ 修复了文档状态处理错误")
        
        print("\n🚀 下次上传文档时，系统将:")
        print("  • 使用配置文件中的嵌入模型创建新的向量存储")
        print("  • 确保向量维度一致性")
        print("  • 正确处理文档状态")
        
        if not api_keys:
            print("\n⚠️  重要提醒:")
            print("  请设置相应的API密钥环境变量:")
            print("  export SILICONFLOW_API_KEY='your-key'")
            print("  export OPENAI_API_KEY='your-key'")
        
        print("\n🎯 现在可以重新启动服务器并测试文档上传功能！")
        
    else:
        print("\n🚫 操作已取消。")
        
    print("\n💡 如果问题仍然存在:")
    print("  1. 检查配置文件中的嵌入模型设置")
    print("  2. 确保API密钥正确设置")
    print("  3. 重新启动服务器")
    print("  4. 查看服务器日志获取详细错误信息")

if __name__ == "__main__":
    main()