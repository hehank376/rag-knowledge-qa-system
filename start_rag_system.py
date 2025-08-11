#!/usr/bin/env python3
"""
RAG系统启动脚本
包含完整的日志配置和错误处理
"""

import os
import sys
import logging
import logging.config
import yaml
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def setup_logging():
    """设置日志配置"""
    try:
        # 使用我们的专业日志配置模块
        from rag_system.utils.logging_config import setup_logging as setup_rag_logging
        setup_rag_logging(
            log_level="DEBUG",
            log_dir="logs",
            enable_file_logging=True,
            enable_console_logging=True
        )
        print("✓ 使用专业日志配置")
    except ImportError:
        # 回退到基本日志配置
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('qa_system.log', encoding='utf-8')
            ]
        )
        print("⚠ 使用基本日志配置")

def main():
    """主函数"""
    # 设置日志
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("🚀 启动RAG知识问答系统...")
    
    # 检查环境变量
    if not os.getenv('SILICONFLOW_API_KEY'):
        logger.warning("⚠ 未设置 SILICONFLOW_API_KEY，将使用mock模型")
    
    try:
        # 导入并启动应用
        from rag_system.api.main import app
        import uvicorn
        
        # 配置
        host = os.getenv("API_HOST", "0.0.0.0")
        port = int(os.getenv("API_PORT", "8000"))
        reload = os.getenv("RELOAD", "true").lower() == "true"
        
        logger.info(f"🌐 启动服务器: {host}:{port}")
        logger.info(f"🔄 自动重载: {reload}")
        
        # 启动服务器
        if reload:
            # 使用模块字符串启动以支持reload
            uvicorn.run(
                "rag_system.api.main:app",
                host=host,
                port=port,
                reload=reload,
                log_level="info"
            )
        else:
            # 直接使用app对象
            uvicorn.run(
                app,
                host=host,
                port=port,
                reload=reload,
                log_level="info"
            )
        
    except Exception as e:
        logger.error(f"❌ 启动失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
