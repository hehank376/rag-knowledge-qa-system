#!/usr/bin/env python3
"""
修复向量维度不匹配问题
"""
import os
import shutil
import sys
from pathlib import Path

def fix_vector_dimension_issue():
    print("🔧 修复向量维度不匹配问题...")
    
    # 1. 删除现有的Chroma数据库
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
    
    # 2. 删除SQLite数据库（如果存在）
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
    
    # 3. 清理上传目录
    uploads_path = Path("./uploads")
    if uploads_path.exists():
        print(f"📁 清理上传目录: {uploads_path}")
        try:
            shutil.rmtree(uploads_path)
            print("✓ 上传目录已清理")
        except Exception as e:
            print(f"✗ 清理上传目录失败: {e}")
    
    # 4. 清理数据目录
    data_path = Path("./data")
    if data_path.exists():
        print(f"📁 清理数据目录: {data_path}")
        try:
            shutil.rmtree(data_path)
            print("✓ 数据目录已清理")
        except Exception as e:
            print(f"✗ 清理数据目录失败: {e}")
    
    print("\n🎉 向量维度问题修复完成!")
    print("\n📋 修复说明:")
    print("1. ✓ 删除了现有的向量存储数据库")
    print("2. ✓ 清理了相关的数据文件")
    print("3. ✓ 系统将使用配置文件中指定的嵌入模型重新创建向量存储")
    print("\n🚀 下次上传文档时，系统将:")
    print("- 使用配置文件中的嵌入模型 (BAAI/bge-large-zh-v1.5, 1024维)")
    print("- 创建新的向量存储集合")
    print("- 确保向量维度一致性")
    
    return True

def check_config():
    """检查配置文件中的嵌入模型设置"""
    print("\n🔍 检查当前配置...")
    
    config_path = Path("config.yaml")
    if not config_path.exists():
        print("⚠️  config.yaml 文件不存在")
        return
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        print("📄 当前嵌入模型配置:")
        lines = content.split('\n')
        in_embeddings_section = False
        
        for line in lines:
            if line.strip().startswith('embeddings:'):
                in_embeddings_section = True
                print(f"  {line}")
            elif in_embeddings_section:
                if line.startswith('  ') and ':' in line:
                    print(f"  {line}")
                elif line.strip() and not line.startswith('  '):
                    break
                    
    except Exception as e:
        print(f"✗ 读取配置文件失败: {e}")

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

if __name__ == "__main__":
    print("🛠️  RAG系统向量维度修复工具")
    print("=" * 50)
    
    check_config()
    show_model_dimensions()
    
    print("\n" + "=" * 50)
    
    # 询问用户是否继续
    response = input("\n是否继续修复向量维度问题？这将删除现有数据 (y/N): ")
    
    if response.lower() in ['y', 'yes', '是']:
        if fix_vector_dimension_issue():
            print("\n✅ 修复完成！现在可以重新启动服务器并上传文档。")
        else:
            print("\n❌ 修复过程中出现错误，请检查权限或手动删除相关文件。")
    else:
        print("\n🚫 操作已取消。")
        
    print("\n💡 提示:")
    print("- 如果问题仍然存在，请检查配置文件中的嵌入模型设置")
    print("- 确保API密钥正确设置")
    print("- 重新启动服务器后再次尝试上传文档")