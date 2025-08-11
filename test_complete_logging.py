#!/usr/bin/env python3
"""
完整的日志系统测试
"""
import asyncio
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
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('logs/complete_test.log', encoding='utf-8')
            ]
        )
        return False

async def test_document_processing():
    """测试文档处理服务的日志"""
    print("\\n🧪 测试文档处理服务日志...")
    
    try:
        from rag_system.services.document_processor import DocumentProcessor
        
        # 创建文档处理器
        config = {
            'chunk_size': 400,
            'chunk_overlap': 50,
            'embedding_provider': 'siliconflow',
            'embedding_model': 'BAAI/bge-large-zh-v1.5',
            'embedding_api_key': os.getenv('SILICONFLOW_API_KEY'),
            'embedding_api_base': 'https://api.siliconflow.cn/v1',
            'embedding_dimensions': 1024,
        }
        
        processor = DocumentProcessor(config)
        await processor.initialize()
        
        # 测试文本处理
        test_text = "这是一个测试文档。人工智能是计算机科学的重要分支。"
        
        # 创建临时文件
        test_file = Path("test_document.txt")
        test_file.write_text(test_text, encoding='utf-8')
        
        try:
            # 处理文档
            result = await processor.process_document(str(test_file), "test_doc")
            print(f"✓ 文档处理完成，生成 {result.chunk_count} 个文本块")
            
        finally:
            # 清理临时文件
            if test_file.exists():
                test_file.unlink()
        
        await processor.cleanup()
        
    except Exception as e:
        print(f"✗ 文档处理测试失败: {e}")

async def test_embedding_service():
    """测试嵌入服务的日志"""
    print("\\n🧪 测试嵌入服务日志...")
    
    try:
        from rag_system.services.embedding_service import EmbeddingService
        
        config = {
            'provider': 'siliconflow',
            'model': 'BAAI/bge-large-zh-v1.5',
            'api_key': os.getenv('SILICONFLOW_API_KEY'),
            'api_base': 'https://api.siliconflow.cn/v1',
            'batch_size': 50,
            'dimensions': 1024,
            'timeout': 30
        }
        
        service = EmbeddingService(config)
        await service.initialize()
        
        # 测试向量化
        texts = ["人工智能", "机器学习", "深度学习"]
        embeddings = await service.vectorize_texts(texts)
        print(f"✓ 向量化完成，生成 {len(embeddings)} 个向量")
        
        await service.cleanup()
        
    except Exception as e:
        print(f"✗ 嵌入服务测试失败: {e}")

async def test_vector_store():
    """测试向量存储的日志"""
    print("\\n🧪 测试向量存储日志...")
    
    try:
        from rag_system.vector_store.chroma_store import ChromaVectorStore
        from rag_system.models.config import VectorStoreConfig
        
        config = VectorStoreConfig(
            type='chroma',
            persist_directory='./test_chroma_logs',
            collection_name='test_logs'
        )
        
        store = ChromaVectorStore(config)
        await store.initialize()
        
        count = await store.get_vector_count()
        print(f"✓ 向量存储初始化完成，当前向量数量: {count}")
        
        await store.cleanup()
        
        # 清理测试目录
        import shutil
        if os.path.exists('./test_chroma_logs'):
            shutil.rmtree('./test_chroma_logs')
        
    except Exception as e:
        print(f"✗ 向量存储测试失败: {e}")

async def main():
    """主测试函数"""
    print("🧪 开始完整的日志系统测试...")
    
    # 创建日志目录
    Path("logs").mkdir(exist_ok=True)
    
    # 设置日志
    setup_logging()
    
    # 获取各种logger
    main_logger = logging.getLogger(__name__)
    api_logger = logging.getLogger("rag_system.api")
    service_logger = logging.getLogger("rag_system.services")
    
    main_logger.info("🚀 开始完整日志测试")
    api_logger.info("API模块日志测试")
    service_logger.info("服务模块日志测试")
    
    # 测试各个服务的日志
    await test_embedding_service()
    await test_vector_store()
    await test_document_processing()
    
    main_logger.info("✅ 完整日志测试完成")
    
    print("\\n📁 检查生成的日志文件...")
    log_files = list(Path("logs").glob("*.log"))
    for log_file in log_files:
        size = log_file.stat().st_size
        print(f"  - {log_file.name}: {size} bytes")
        
        # 显示最后几行日志
        if size > 0:
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if lines:
                        print(f"    最后一行: {lines[-1].strip()}")
            except Exception as e:
                print(f"    读取失败: {e}")
    
    print("\\n✅ 完整日志系统测试完成！")
    print("请检查logs目录中的日志文件内容")

if __name__ == "__main__":
    asyncio.run(main())