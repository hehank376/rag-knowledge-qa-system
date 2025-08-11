#!/usr/bin/env python3
"""
配置API调试测试
直接测试配置API的加载和返回
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from rag_system.services.config_service import ConfigService

def test_config_loading():
    """测试配置加载"""
    print("🔍 测试配置加载")
    
    try:
        config_service = ConfigService()
        config = config_service.get_config()
        
        print(f"✅ 配置加载成功")
        print(f"📋 配置类型: {type(config)}")
        
        # 检查重排序配置
        if hasattr(config, 'reranking'):
            print(f"✅ 重排序配置存在")
            print(f"📋 重排序配置类型: {type(config.reranking)}")
            
            if config.reranking:
                print(f"📋 重排序提供商: {getattr(config.reranking, 'provider', 'N/A')}")
                print(f"📋 重排序模型: {getattr(config.reranking, 'model', 'N/A')}")
                print(f"📋 重排序批处理大小: {getattr(config.reranking, 'batch_size', 'N/A')}")
                print(f"📋 重排序最大长度: {getattr(config.reranking, 'max_length', 'N/A')}")
                print(f"📋 重排序超时时间: {getattr(config.reranking, 'timeout', 'N/A')}")
            else:
                print("❌ 重排序配置为空")
        else:
            print("❌ 重排序配置不存在")
            
        return True
        
    except Exception as e:
        print(f"❌ 配置加载失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_config_api_logic():
    """测试配置API逻辑"""
    print("\n🔍 测试配置API逻辑")
    
    try:
        config_service = ConfigService()
        config = config_service.get_config()
        
        # 模拟配置API的逻辑
        reranking_config = {
            "provider": getattr(config.reranking, 'provider', 'sentence_transformers') if config.reranking else 'sentence_transformers',
            "model": getattr(config.reranking, 'model', 'cross-encoder/ms-marco-MiniLM-L-6-v2') if config.reranking else 'cross-encoder/ms-marco-MiniLM-L-6-v2',
            "model_name": getattr(config.reranking, 'model_name', getattr(config.reranking, 'model', 'cross-encoder/ms-marco-MiniLM-L-6-v2')) if config.reranking else 'cross-encoder/ms-marco-MiniLM-L-6-v2',
            "batch_size": getattr(config.reranking, 'batch_size', 32) if config.reranking else 32,
            "max_length": getattr(config.reranking, 'max_length', 512) if config.reranking else 512,
            "timeout": getattr(config.reranking, 'timeout', 30.0) if config.reranking else 30.0,
            "api_key": getattr(config.reranking, 'api_key', '') if config.reranking else '',
            "base_url": getattr(config.reranking, 'base_url', '') if config.reranking else ''
        } if config.reranking else None
        
        print(f"✅ 配置API逻辑测试成功")
        print(f"📋 重排序配置: {reranking_config}")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置API逻辑测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 配置API调试测试")
    
    success1 = test_config_loading()
    success2 = test_config_api_logic()
    
    if success1 and success2:
        print("\n🎉 所有测试通过！")
    else:
        print("\n❌ 部分测试失败")
        
    sys.exit(0 if (success1 and success2) else 1)