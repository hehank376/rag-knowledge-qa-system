#!/usr/bin/env python3
"""
启动生产就绪的RAG系统服务器
"""
import uvicorn
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from rag_system.api.main import app

def check_environment():
    """检查环境配置"""
    print("🔍 检查环境配置...")
    
    # 检查API密钥
    api_keys = []
    if os.getenv("SILICONFLOW_API_KEY"):
        api_keys.append("SiliconFlow")
    if os.getenv("OPENAI_API_KEY"):
        api_keys.append("OpenAI")
    
    if api_keys:
        print(f"✓ 已配置API密钥: {', '.join(api_keys)}")
    else:
        print("⚠️  未检测到API密钥，将使用Mock模式")
    
    # 检查配置文件
    config_path = Path("config.yaml")
    if config_path.exists():
        print("✓ 配置文件存在")
    else:
        print("⚠️  配置文件不存在，将使用默认配置")
    
    # 检查数据目录
    data_dirs = ["./chroma_db", "./uploads", "./data"]
    for dir_path in data_dirs:
        if Path(dir_path).exists():
            print(f"📁 数据目录存在: {dir_path}")
        else:
            print(f"📁 数据目录将自动创建: {dir_path}")

if __name__ == "__main__":
    print("🚀 启动生产就绪的RAG系统服务器...")
    print("=" * 60)
    
    check_environment()
    
    print("\n📍 服务地址:")
    print("  • 前端界面: http://localhost:8000")
    print("  • API文档: http://localhost:8000/docs")
    print("  • 健康检查: http://localhost:8000/health")
    
    print("\n🧪 测试工具:")
    print("  • 真实模型连接测试: python test_real_model_connection.py")
    print("  • API端点测试: python test_api_endpoints.py")
    print("  • 配置API测试: python test_config_api.py")
    
    print("\n🔧 问题修复工具:")
    print("  • 文档上传问题修复: python fix_document_upload_issues.py")
    print("  • 向量维度问题修复: python fix_vector_dimension_mismatch.py")
    
    print("\n✅ 已修复的问题:")
    print("  ✓ JavaScript语法错误和通知系统")
    print("  ✓ API路径不匹配和配置保存")
    print("  ✓ 连接测试功能和真实模型验证")
    print("  ✓ 向量维度不匹配处理")
    print("  ✓ 文档状态枚举错误处理")
    
    print("\n🎯 支持的功能:")
    print("  • 文档上传和处理")
    print("  • 向量化和存储")
    print("  • 智能问答")
    print("  • 系统配置管理")
    print("  • 连接测试和健康检查")
    
    print("\n⚠️  按 Ctrl+C 停止服务")
    print("=" * 60)
    
    # 启动服务器
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )