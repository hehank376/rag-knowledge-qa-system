#!/usr/bin/env python3
"""
测试日志配置修复
"""
import os
import sys
import logging
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
        return True
    except Exception as e:
        print(f"⚠ 专业日志配置失败: {e}")
        # 回退到基本日志配置
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('logs/test.log', encoding='utf-8')
            ]
        )
        print("✓ 使用基本日志配置")
        return False

def test_logging():
    """测试日志输出"""
    # 创建日志目录
    Path("logs").mkdir(exist_ok=True)
    
    # 设置日志
    professional_config = setup_logging()
    
    # 获取不同的logger
    main_logger = logging.getLogger(__name__)
    service_logger = logging.getLogger("rag_system.services.test")
    embedding_logger = logging.getLogger("rag_system.services.embedding_service")
    
    print("\\n🧪 开始测试日志输出...")
    
    # 测试不同级别的日志
    main_logger.debug("这是一个DEBUG级别的日志")
    main_logger.info("这是一个INFO级别的日志")
    main_logger.warning("这是一个WARNING级别的日志")
    main_logger.error("这是一个ERROR级别的日志")
    
    service_logger.info("服务层日志测试")
    embedding_logger.info("嵌入服务日志测试")
    
    print("\\n📁 检查日志文件...")
    log_files = list(Path("logs").glob("*.log"))
    for log_file in log_files:
        print(f"  - {log_file.name}: {log_file.stat().st_size} bytes")
        
    print("\\n✅ 日志测试完成！")
    print("请检查控制台输出和logs目录中的日志文件")

if __name__ == "__main__":
    test_logging()