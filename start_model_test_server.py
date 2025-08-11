#!/usr/bin/env python3
"""
启动模型测试服务器
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
    print("🚀 启动模型测试服务器...")
    print("📍 前端访问地址: http://localhost:8000")
    print("📖 API文档地址: http://localhost:8000/docs")
    print("🧪 真实模型测试: python test_real_model_connection.py")
    print("🔧 API端点测试: python test_api_endpoints.py")
    print("⚠️  按 Ctrl+C 停止服务")
    print()
    print("🔧 支持的连接测试:")
    print("  ✓ SiliconFlow LLM和嵌入模型")
    print("  ✓ OpenAI LLM和嵌入模型")
    print("  ✓ 真实API密钥验证")
    print("  ✓ 连接延迟测量")
    print("  ✓ 错误处理和诊断")
    print()
    print("🌟 环境变量设置:")
    print("  export SILICONFLOW_API_KEY='your-key'")
    print("  export OPENAI_API_KEY='your-key'")
    print()
    
    # 启动服务器
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )