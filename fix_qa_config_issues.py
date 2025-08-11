#!/usr/bin/env python3
"""
修复QA系统配置问题
1. 修复数据库配置（使用SQLite而不是PostgreSQL）
2. 修复模型配置（使用真实模型而不是mock）
3. 设置日志配置
"""

import os
import sys
import yaml
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def setup_logging():
    """设置日志配置"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('qa_system.log')
        ]
    )

def fix_config_file():
    """修复配置文件"""
    config_file = Path("config.yaml")
    
    if not config_file.exists():
        print("❌ 配置文件 config.yaml 不存在")
        return False
    
    print("🔧 修复配置文件...")
    
    # 读取当前配置
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 修复数据库配置
    if 'database' not in config:
        config['database'] = {}
    
    # 确保使用SQLite数据库
    config['database']['url'] = "sqlite:///./database/rag_system.db"
    config['database']['echo'] = True
    
    # 修复向量存储配置
    if 'vector_store' not in config:
        config['vector_store'] = {}
    
    config['vector_store']['type'] = "chroma"
    config['vector_store']['persist_directory'] = "./chroma_db"
    config['vector_store']['collection_name'] = "documents"  # 使用实际的集合名称
    
    # 修复嵌入模型配置
    if 'embeddings' not in config:
        config['embeddings'] = {}
    
    # 检查是否有API密钥
    siliconflow_key = os.getenv('SILICONFLOW_API_KEY')
    
    if siliconflow_key:
        print("✓ 检测到 SILICONFLOW_API_KEY，使用真实模型")
        config['embeddings']['provider'] = "siliconflow"
        config['embeddings']['model'] = "BAAI/bge-large-zh-v1.5"
        
        # 修复LLM配置
        if 'llm' not in config:
            config['llm'] = {}
        config['llm']['provider'] = "siliconflow"
        config['llm']['model'] = "Qwen/Qwen2.5-7B-Instruct"
    else:
        print("⚠ 未检测到 SILICONFLOW_API_KEY，使用mock模型")
        config['embeddings']['provider'] = "mock"
        config['embeddings']['model'] = "mock-embedding"
        
        # 修复LLM配置
        if 'llm' not in config:
            config['llm'] = {}
        config['llm']['provider'] = "mock"
        config['llm']['model'] = "mock-model"
    
    config['embeddings']['chunk_size'] = 1000
    config['embeddings']['chunk_overlap'] = 200
    
    config['llm']['temperature'] = 0.1
    config['llm']['max_tokens'] = 1000
    
    # 修复检索配置
    if 'retrieval' not in config:
        config['retrieval'] = {}
    
    config['retrieval']['top_k'] = 5
    config['retrieval']['similarity_threshold'] = 0.7
    
    # 修复API配置
    if 'api' not in config:
        config['api'] = {}
    
    config['api']['host'] = "0.0.0.0"
    config['api']['port'] = 8000
    config['api']['cors_origins'] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]
    
    # 修复应用配置
    if 'app' not in config:
        config['app'] = {}
    
    config['app']['name'] = "RAG Knowledge QA System"
    config['app']['version'] = "1.0.0"
    config['app']['debug'] = True
    
    # 保存修复后的配置
    with open(config_file, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, indent=2)
    
    print("✓ 配置文件修复完成")
    return True

def create_logging_config():
    """创建日志配置文件"""
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            },
            'detailed': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'INFO',
                'formatter': 'standard',
                'stream': 'ext://sys.stdout'
            },
            'file': {
                'class': 'logging.FileHandler',
                'level': 'DEBUG',
                'formatter': 'detailed',
                'filename': 'qa_system.log',
                'mode': 'a',
                'encoding': 'utf-8'
            }
        },
        'loggers': {
            'rag_system': {
                'level': 'DEBUG',
                'handlers': ['console', 'file'],
                'propagate': False
            },
            'uvicorn': {
                'level': 'INFO',
                'handlers': ['console', 'file'],
                'propagate': False
            }
        },
        'root': {
            'level': 'INFO',
            'handlers': ['console', 'file']
        }
    }
    
    with open('logging_config.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(logging_config, f, default_flow_style=False, allow_unicode=True, indent=2)
    
    print("✓ 日志配置文件创建完成")

def test_config_loading():
    """测试配置加载"""
    print("\n🧪 测试配置加载...")
    
    try:
        from rag_system.config.loader import ConfigLoader
        
        config_loader = ConfigLoader()
        config = config_loader.load_config()
        
        print("✓ 配置加载成功")
        print(f"  - 应用名称: {config.name}")
        print(f"  - 数据库URL: {config.database.url}")
        print(f"  - 向量存储类型: {config.vector_store.type}")
        print(f"  - 向量存储路径: {config.vector_store.persist_directory}")
        print(f"  - 集合名称: {config.vector_store.collection_name}")
        print(f"  - 嵌入模型: {config.embeddings.provider}/{config.embeddings.model}")
        print(f"  - LLM模型: {config.llm.provider}/{config.llm.model}")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置加载失败: {str(e)}")
        return False

def check_vector_store():
    """检查向量存储状态"""
    print("\n🔍 检查向量存储状态...")
    
    chroma_dir = Path("./chroma_db")
    if chroma_dir.exists():
        print(f"✓ 向量存储目录存在: {chroma_dir}")
        
        # 列出目录内容
        files = list(chroma_dir.rglob("*"))
        print(f"  - 文件数量: {len(files)}")
        
        if files:
            print("  - 主要文件:")
            for file in files[:5]:  # 只显示前5个文件
                print(f"    {file.relative_to(chroma_dir)}")
    else:
        print(f"⚠ 向量存储目录不存在: {chroma_dir}")

def create_startup_script():
    """创建启动脚本"""
    startup_script = '''#!/usr/bin/env python3
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
    logging_config_file = Path("logging_config.yaml")
    
    if logging_config_file.exists():
        with open(logging_config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logging.config.dictConfig(config)
    else:
        # 回退到基本日志配置
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('qa_system.log')
            ]
        )

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
'''
    
    with open('start_rag_system.py', 'w', encoding='utf-8') as f:
        f.write(startup_script)
    
    print("✓ 启动脚本创建完成: start_rag_system.py")

def main():
    """主函数"""
    print("🔧 QA系统配置修复工具")
    print("=" * 50)
    
    # 设置日志
    setup_logging()
    
    # 1. 修复配置文件
    if not fix_config_file():
        print("❌ 配置文件修复失败")
        return
    
    # 2. 创建日志配置
    create_logging_config()
    
    # 3. 测试配置加载
    if not test_config_loading():
        print("❌ 配置测试失败")
        return
    
    # 4. 检查向量存储
    check_vector_store()
    
    # 5. 创建启动脚本
    create_startup_script()
    
    print("\n" + "=" * 50)
    print("🎉 配置修复完成！")
    
    print("\n📋 修复总结:")
    print("1. ✓ 修复了数据库配置（使用SQLite）")
    print("2. ✓ 修复了向量存储配置")
    print("3. ✓ 修复了模型配置")
    print("4. ✓ 创建了日志配置")
    print("5. ✓ 创建了启动脚本")
    
    print("\n🚀 下一步操作:")
    print("1. 设置环境变量（可选）:")
    print("   export SILICONFLOW_API_KEY=your_api_key")
    print("2. 重启服务器:")
    print("   python start_rag_system.py")
    print("3. 测试问答功能")
    
    print("\n💡 注意事项:")
    print("- 如果没有API密钥，系统将使用mock模型")
    print("- mock模型会返回标准的'无相关内容'响应")
    print("- 要获得真实答案，需要设置API密钥并上传相关文档")
    print("- 日志文件: qa_system.log")

if __name__ == "__main__":
    main()