#!/usr/bin/env python3
"""
启动最终修复版本的RAG系统服务器
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
    print("🚀 启动最终修复版本的RAG系统服务器...")
    print("📍 前端访问地址: http://localhost:8000")
    print("📖 API文档地址: http://localhost:8000/docs")
    print("🧪 通知测试页面: http://localhost:8000/test_notifications.html")
    print("🔧 配置API测试: python test_config_api.py")
    print("⚠️  按 Ctrl+C 停止服务")
    print()
    print("✅ 已修复的问题:")
    print("  ✓ JavaScript语法错误 (history.js)")
    print("  ✓ formatDate函数未定义")
    print("  ✓ 通知系统显示问题")
    print("  ✓ API路径不匹配")
    print("  ✓ 配置保存失败 (Method Not Allowed)")
    print("  ✓ 连接测试失败 (404 Not Found)")
    print("  ✓ 配置加载失败 (API密钥验证)")
    print("  ✓ 配置节名称映射问题")
    print()
    print("🎯 现在可以正常使用:")
    print("  • 前端页面加载和显示")
    print("  • 通知系统显示消息")
    print("  • 系统设置保存")
    print("  • 连接测试功能")
    print("  • 所有API端点")
    print()
    
    # 启动服务器
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )