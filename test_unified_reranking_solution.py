#!/usr/bin/env python3
"""
统一重排序解决方案测试脚本

测试新的重排序架构是否正常工作，包括：
- 工厂模式创建
- 配置管理
- API和本地模型支持
- 服务层集成
"""

import asyncio
import sys
from pathlib import Path
import yaml

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from rag_system.reranking import RerankingFactory, RerankingConfig
from rag_system.services.reranking_service import RerankingService
from rag_system.models.vector import SearchResult
from rag_system.models.config import RetrievalConfig


def print_section(title: str):
    """打印格式化的章节"""
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print(f"{'='*60}")


async def test_reranking_factory():
    """测试重排序工厂"""
    print_section("测试重排序工厂")
    
    # 1. 测试Mock重排序
    print("1. 测试Mock重排序")
    try:
        mock_config = RerankingConfig(
            provider="mock",
            model="mock-reranking"
        )
        
        mock_reranking = RerankingFactory.create_reranking(mock_config)
        await mock_reranking.initialize()
        
        # 测试重排序
        scores = await mock_reranking.rerank("test query", ["doc1", "doc2", "doc3"])
        print(f"   ✅ Mock重排序成功: {scores}")
        
        await mock_reranking.cleanup()
        
    except Exception as e:
        print(f"   ❌ Mock重排序失败: {str(e)}")
    
    # 2. 测试本地重排序（如果可用）
    print("2. 测试本地重排序")
    try:
        local_config = RerankingConfig(
            provider="local",
            model="cross-encoder/ms-marco-MiniLM-L-6-v2",
            device="cpu"
        )
        
        local_reranking = RerankingFactory.create_reranking(local_config)
        await local_reranking.initialize()
        
        # 测试重排序
        scores = await local_reranking.rerank("artificial intelligence", [
            "AI is transforming technology",
            "The weather is nice today",
            "Machine learning is a subset of AI"
        ])
        print(f"   ✅ 本地重排序成功: {scores}")
        
        await local_reranking.cleanup()
        
    except Exception as e:
        print(f"   ⚠️  本地重排序跳过: {str(e)}")
    
    # 3. 测试SiliconFlow重排序（如果配置可用）
    print("3. 测试SiliconFlow重排序")
    try:
        # 读取配置文件
        config_path = Path("config/development.yaml")
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            reranking_config = config.get('reranking', {})
            if reranking_config.get('api_key') and reranking_config.get('base_url'):
                sf_config = RerankingConfig(
                    provider="siliconflow",
                    model=reranking_config.get('model', 'BAAI/bge-reranker-v2-m3'),
                    api_key=reranking_config['api_key'],
                    base_url=reranking_config['base_url']
                )
                
                sf_reranking = RerankingFactory.create_reranking(sf_config)
                await sf_reranking.initialize()
                
                # 测试重排序
                scores = await sf_reranking.rerank("人工智能", [
                    "人工智能正在改变世界",
                    "今天天气很好",
                    "机器学习是AI的一个分支"
                ])
                print(f"   ✅ SiliconFlow重排序成功: {scores}")
                
                await sf_reranking.cleanup()
            else:
                print("   ⚠️  SiliconFlow配置不完整，跳过测试")
        else:
            print("   ⚠️  配置文件不存在，跳过SiliconFlow测试")
            
    except Exception as e:
        print(f"   ⚠️  SiliconFlow重排序跳过: {str(e)}")


async def test_reranking_service():
    """测试重排序服务"""
    print_section("测试重排序服务")
    
    # 1. 测试Mock服务
    print("1. 测试Mock重排序服务")
    try:
        mock_service_config = {
            'provider': 'mock',
            'model': 'mock-reranking',
            'enable_fallback': True
        }
        
        service = RerankingService(mock_service_config)
        await service.initialize()
        
        # 创建测试数据
        test_results = [
            SearchResult(
                chunk_id="550e8400-e29b-41d4-a716-446655440001",
                document_id="550e8400-e29b-41d4-a716-446655440011",
                content="人工智能是计算机科学的一个分支",
                similarity_score=0.8,
                metadata={}
            ),
            SearchResult(
                chunk_id="550e8400-e29b-41d4-a716-446655440002",
                document_id="550e8400-e29b-41d4-a716-446655440012",
                content="今天的天气非常好",
                similarity_score=0.6,
                metadata={}
            ),
            SearchResult(
                chunk_id="550e8400-e29b-41d4-a716-446655440003",
                document_id="550e8400-e29b-41d4-a716-446655440013",
                content="机器学习是AI的重要组成部分",
                similarity_score=0.7,
                metadata={}
            )
        ]
        
        # 测试重排序
        retrieval_config = RetrievalConfig(enable_rerank=True)
        reranked_results = await service.rerank_results("人工智能", test_results, retrieval_config)
        
        print(f"   ✅ 重排序服务成功，处理了 {len(reranked_results)} 个结果")
        for i, result in enumerate(reranked_results):
            print(f"      {i+1}. 分数: {result.similarity_score:.3f}, 内容: {result.content[:30]}...")
        
        # 测试健康检查
        health = await service.health_check()
        print(f"   ✅ 健康检查: {health['status']}")
        
        # 测试指标
        metrics = service.get_metrics()
        print(f"   ✅ 服务指标: 总请求 {metrics['service_metrics']['total_requests']}")
        
        await service.cleanup()
        
    except Exception as e:
        print(f"   ❌ Mock重排序服务失败: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # 2. 测试配置自动检测
    print("2. 测试配置自动检测")
    try:
        # 读取实际配置
        config_path = Path("config/development.yaml")
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            reranking_config = config.get('reranking', {})
            
            # 创建服务（自动检测提供商）
            service = RerankingService(reranking_config)
            print(f"   ✅ 自动检测提供商: {service._reranking_config.provider}")
            print(f"   ✅ 模型: {service._reranking_config.get_model_name()}")
            print(f"   ✅ 是否API提供商: {service._reranking_config.is_api_provider()}")
            print(f"   ✅ 是否本地提供商: {service._reranking_config.is_local_provider()}")
            
        else:
            print("   ⚠️  配置文件不存在，跳过自动检测测试")
            
    except Exception as e:
        print(f"   ❌ 配置自动检测失败: {str(e)}")


async def test_provider_info():
    """测试提供商信息"""
    print_section("测试提供商信息")
    
    try:
        # 获取可用提供商
        providers = RerankingFactory.get_available_providers()
        print(f"✅ 可用提供商: {providers}")
        
        # 获取每个提供商的详细信息
        for provider in providers:
            try:
                info = RerankingFactory.get_provider_info(provider)
                if info:
                    print(f"   📋 {provider}: {info.get('description', 'N/A')}")
                    print(f"      类型: {info.get('type', 'N/A')}")
                    print(f"      支持API: {info.get('supports_api', False)}")
                    print(f"      支持本地: {info.get('supports_local', False)}")
                else:
                    print(f"   ❌ {provider}: 无法获取信息")
            except Exception as e:
                print(f"   ❌ {provider}: {str(e)}")
                
    except Exception as e:
        print(f"❌ 获取提供商信息失败: {str(e)}")


async def test_configuration_validation():
    """测试配置验证"""
    print_section("测试配置验证")
    
    # 1. 测试有效配置
    print("1. 测试有效配置")
    try:
        valid_config = RerankingConfig(
            provider="mock",
            model="test-model",
            max_length=512,
            batch_size=32
        )
        print(f"   ✅ 有效配置创建成功: {valid_config.provider}")
    except Exception as e:
        print(f"   ❌ 有效配置创建失败: {str(e)}")
    
    # 2. 测试无效提供商
    print("2. 测试无效提供商")
    try:
        invalid_config = RerankingConfig(
            provider="invalid_provider",
            model="test-model"
        )
        print(f"   ❌ 应该失败但成功了: {invalid_config.provider}")
    except Exception as e:
        print(f"   ✅ 正确拒绝无效提供商: {str(e)}")
    
    # 3. 测试配置转换
    print("3. 测试配置转换")
    try:
        config = RerankingConfig(provider="mock", model="test")
        config_dict = config.to_dict()
        print(f"   ✅ 配置转换成功: {len(config_dict)} 个字段")
    except Exception as e:
        print(f"   ❌ 配置转换失败: {str(e)}")


async def main():
    """主函数"""
    print("🚀 统一重排序解决方案测试")
    print("测试新的重排序架构是否正常工作")
    
    try:
        # 1. 测试重排序工厂
        await test_reranking_factory()
        
        # 2. 测试重排序服务
        await test_reranking_service()
        
        # 3. 测试提供商信息
        await test_provider_info()
        
        # 4. 测试配置验证
        await test_configuration_validation()
        
        print_section("测试总结")
        print("✅ 统一重排序架构测试完成")
        print("🎯 新架构的优势:")
        print("   - 统一的工厂模式和配置管理")
        print("   - 支持多种提供商（API和本地模型）")
        print("   - 完善的错误处理和降级机制")
        print("   - 与嵌入模型架构保持一致")
        print("   - 易于扩展和维护")
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())