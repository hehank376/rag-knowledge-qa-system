#!/usr/bin/env python3
"""
启动修复配置API问题后的RAG系统服务器
"""
import uvicorn
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from rag_system.api.main import app

if __name__ == "__main__":
    print("🚀 启动修复配置API后的RAG系统服务器...")
    print("📍 前端访问地址: http://localhost:8000")
    print("📖 API文档地址: http://localhost:8000/docs")
    print("🔧 配置API测试: python test_config_api.py")
    print("⚠️  按 Ctrl+C 停止服务")
    print()
    print("🔧 修复的配置问题:")
    print("  ✓ 添加了连接测试API端点")
    print("  ✓ 修复了API路径问题")
    print("  ✓ 支持'all'配置节更新")
    print("  ✓ 修复了前端配置数据映射")
    print("  ✓ 改进了错误处理")
    print()
    
    # 启动服务器
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )