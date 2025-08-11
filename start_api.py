#!/usr/bin/env python3
"""
RAG Knowledge QA System API Server Startup Script
启动RAG知识问答系统API服务器
"""

import os
import sys
import uvicorn
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """启动API服务器"""
    print("🚀 启动RAG知识问答系统API服务器...")
    print(f"📁 项目根目录: {project_root}")
    print(f"🐍 Python路径: {sys.path[0]}")
    
    # 设置环境变量
    os.environ.setdefault("ENVIRONMENT", "development")
    os.environ.setdefault("LOG_LEVEL", "INFO")
    
    # 启动配置
    config = {
        "app": "rag_system.api.main:app",
        "host": "0.0.0.0",
        "port": 8000,
        "reload": True,
        "log_level": "info",
        "access_log": True
    }
    
    print(f"🌐 服务地址: http://{config['host']}:{config['port']}")
    print(f"📚 API文档: http://{config['host']}:{config['port']}/docs")
    print(f"🔄 自动重载: {config['reload']}")
    print("=" * 50)
    
    try:
        # 启动服务器
        uvicorn.run(**config)
    except KeyboardInterrupt:
        print("\n⏹️ 服务器已停止")
    except Exception as e:
        print(f"\n💥 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()