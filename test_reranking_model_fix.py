#!/usr/bin/env python3
"""
测试重排序模型配置修复
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rag_system.config.loader import ConfigLoader
from rag_system.services.enhanced_retrieval_service import EnhancedRetrievalService
from rag_system.services.reranking_service import RerankingService

async def test_reranking_model_fix():
    """测试重排序模型配置修复"""
    print("🔧 测试重排序模型配置修复...")
    
    try:
        # 1. 检查配置文件
        config_loader = ConfigLoader()
        app_config = config_loader.load_config()
        
        print(f"📋 配置文件中的重排序设置:")
        print(f"   - provider: {app_config.reranking.provider}")
        print(f"   - model: {app_config.reranking.model}")
        print(f"   - model_name: {app_config.reranking.model_name}")
        print(f"   - api_key: {'已设置' if app_config.reranking.api_key else '未设置'}")
        
        # 2. 测试直接创建重排序服务
        print(f"\n🧪 测试直接创建重排序服务:")
        
        reranking_config = {
            'provider': app_config.reranking.provider,
            'model': app_config.reranking.model,
            'model_name': app_config.reranking.model_name,
            'api_key': app_config.reranking.api_key,
            'base_url': app_config.reranking.base_url,
            'batch_size': app_config.reranking.batch_size,
            'max_length': app_config.reranking.max_length,
            'timeout': app_config.reranking.timeout
        }
        
        print(f"   传递给RerankingService的配置:")
        print(f"   - provider: {reranking_config['provider']}")
        print(f"   - model: {reranking_config['model']}")
        print(f"   - model_name: {reranking_config['model_name']}")
        
        reranking_service = RerankingService(reranking_config)
        print(f"   RerankingService实际使用的模型: {reranking_service.model_name}")
        print(f"   RerankingService实际使用的提供商: {reranking_service.provider}")
        
        # 检查是否使用了正确的模型
        expected_model = app_config.reranking.model
        if reranking_service.model_name == expected_model:
            print(f"   ✅ 模型名称正确: {reranking_service.model_name}")
        else:
            print(f"   ❌ 模型名称错误: 期望 {expected_model}, 实际 {reranking_service.model_name}")
        
        # 3. 测试增强检索服务中的重排序配置
        print(f"\n🔗 测试增强检索服务中的重排序配置:")
        
        enhanced_config = {
            'default_top_k': 5,
            'similarity_threshold': 0.1,
            'search_mode': 'semantic',
            'enable_rerank': True,
            'enable_cache': False
        }
        
        enhanced_retrieval = EnhancedRetrievalService(enhanced_config)
        
        # 检查重排序配置创建方法
        reranking_config_from_enhanced = enhanced_retrieval._create_reranking_config(enhanced_config)
        print(f"   增强检索服务创建的重排序配置:")
        print(f"   - provider: {reranking_config_from_enhanced['provider']}")
        print(f"   - model: {reranking_config_from_enhanced['model']}")
        print(f"   - model_name: {reranking_config_from_enhanced['model_name']}")
        
        # 初始化增强检索服务
        await enhanced_retrieval.initialize()
        
        # 获取重排序服务
        integrated_reranking_service = enhanced_retrieval._get_reranking_service()
        if integrated_reranking_service:
            print(f"   集成的重排序服务模型: {integrated_reranking_service.model_name}")
            print(f"   集成的重排序服务提供商: {integrated_reranking_service.provider}")
            
            # 检查是否使用了正确的模型
            if integrated_reranking_service.model_name == expected_model:
                print(f"   ✅ 集成服务模型名称正确")
            else:
                print(f"   ❌ 集成服务模型名称错误: 期望 {expected_model}, 实际 {integrated_reranking_service.model_name}")
        else:
            print(f"   ❌ 无法获取集成的重排序服务")
        
        # 4. 测试初始化
        print(f"\n🚀 测试重排序服务初始化:")
        
        try:
            await reranking_service.initialize()
            print(f"   ✅ 重排序服务初始化成功")
            
            # 检查健康状态
            health = await reranking_service.health_check()
            print(f"   - 健康状态: {health.get('status', 'unknown')}")
            print(f"   - 使用的模型: {health.get('model_name', 'unknown')}")
            print(f"   - 提供商: {health.get('provider', 'unknown')}")
            print(f"   - 模型已加载: {health.get('model_loaded', False)}")
            
        except Exception as e:
            print(f"   ❌ 重排序服务初始化失败: {str(e)}")
        
        # 5. 总结
        print(f"\n📋 修复验证总结:")
        
        config_correct = (reranking_config['model'] == expected_model)
        service_correct = (reranking_service.model_name == expected_model)
        integration_correct = (
            integrated_reranking_service and 
            integrated_reranking_service.model_name == expected_model
        )
        
        print(f"   ✅ 配置传递正确: {'是' if config_correct else '否'}")
        print(f"   ✅ 服务使用正确模型: {'是' if service_correct else '否'}")
        print(f"   ✅ 集成服务正确: {'是' if integration_correct else '否'}")
        
        if config_correct and service_correct and integration_correct:
            print(f"\n🎉 重排序模型配置修复成功！")
            print(f"现在系统会正确使用配置文件中指定的模型: {expected_model}")
        else:
            print(f"\n⚠️  重排序模型配置仍有问题，需要进一步检查")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_reranking_model_fix())
    sys.exit(0 if success else 1)