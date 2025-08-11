#!/usr/bin/env python3
"""
测试嵌入模型修复
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rag_system.services.embedding_service import EmbeddingService
from rag_system.config.loader import ConfigLoader

async def test_embedding_fix():
    """测试嵌入模型修复"""
    print("🔧 测试嵌入模型修复...")
    
    try:
        # 加载配置
        config_loader = ConfigLoader()
        app_config = config_loader.load_config()
        
        # 获取嵌入配置
        embedding_config = app_config.embeddings
        print(f"📋 嵌入配置: {embedding_config}")
        print(f"🤖 模型名称: {embedding_config.model}")
        print(f"🔧 提供商: {embedding_config.provider}")
        
        # 将配置对象转换为字典
        embedding_config_dict = {
            'provider': embedding_config.provider,
            'model': embedding_config.model,
            'api_key': embedding_config.api_key,
            'base_url': embedding_config.base_url,
            'batch_size': embedding_config.batch_size,
            'dimensions': embedding_config.dimensions,
            'timeout': embedding_config.timeout,
            'retry_attempts': embedding_config.retry_attempts
        }
        
        # 初始化嵌入服务
        embedding_service = EmbeddingService(embedding_config_dict)
        await embedding_service.initialize()
        
        print("✅ 嵌入服务初始化成功！")
        
        # 测试嵌入生成
        test_text = "这是一个测试文本"
        embeddings = await embedding_service.embed_text(test_text)
        
        print(f"📊 嵌入维度: {len(embeddings)}")
        print(f"📈 嵌入前5个值: {embeddings[:5]}")
        
        print("🎉 嵌入模型修复成功！")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_embedding_fix())
    sys.exit(0 if success else 1)