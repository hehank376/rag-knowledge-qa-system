#!/usr/bin/env python3
"""
启动修复后的RAG系统服务器
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
    print("🚀 启动修复后的RAG系统API服务器...")
    print("📍 前端访问地址: http://localhost:8000")
    print("📖 API文档地址: http://localhost:8000/docs")
    print("🔍 健康检查: http://localhost:8000/health")
    print("⚠️  按 Ctrl+C 停止服务")
    print()
    print("🔧 修复的问题:")
    print("  ✓ 修复了history.js的语法错误")
    print("  ✓ 添加了formatDate函数")
    print("  ✓ 修复了API路径问题")
    print("  ✓ 添加了会话API占位符")
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