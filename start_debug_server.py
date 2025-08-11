#!/usr/bin/env python3
"""
启动调试版本的RAG系统服务器
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
    print("🚀 启动调试版本的RAG系统API服务器...")
    print("📍 前端访问地址: http://localhost:8000")
    print("🧪 通知测试页面: http://localhost:8000/test_notifications.html")
    print("📖 API文档地址: http://localhost:8000/docs")
    print("🔍 健康检查: http://localhost:8000/health")
    print("⚠️  按 Ctrl+C 停止服务")
    print()
    print("🔧 调试功能:")
    print("  ✓ 通知系统调试日志已启用")
    print("  ✓ 兼容旧式通知调用方式")
    print("  ✓ 自动测试通知系统")
    print()
    
    # 启动服务器
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )