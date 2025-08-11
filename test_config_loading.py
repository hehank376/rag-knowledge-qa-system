#!/usr/bin/env python3
"""
测试配置加载
"""
import asyncio
from rag_system.api.document_api import get_document_service

async def test_config_loading():
    """测试配置加载"""
    print("🔍 测试配置加载...")
    
    try:
        # 获取文档服务
        service = await get_document_service()
        
        # 检查配置
        processor = service.document_processor
        splitter = processor.text_splitter
        config = splitter.config
        
        print(f"✅ 配置加载成功")
        print(f"   chunk_size: {config.chunk_size}")
        print(f"   chunk_overlap: {config.chunk_overlap}")
        print(f"   min_chunk_size: {config.min_chunk_size}")
        print(f"   max_chunk_size: {config.max_chunk_size}")
        
        # 清理
        await service.cleanup()
        
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_config_loading())