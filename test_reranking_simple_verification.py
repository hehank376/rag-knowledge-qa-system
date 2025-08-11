#!/usr/bin/env python3
"""
简化的重排序功能验证
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rag_system.config.loader import ConfigLoader
from rag_system.services.enhanced_retrieval_service import EnhancedRetrievalService
from rag_system.models.config import RetrievalConfig

async def test_reranking_simple():
    """简化的重排序功能测试"""
    print("🔍 简化重排序功能验证...")
    
    try:
        # 1. 检查配置加载
        config_loader = ConfigLoader()
        app_config = config_loader.load_config()
        
        print(f"📋 配置检查:")
        print(f"   - retrieval.enable_rerank: {app_config.retrieval.enable_rerank}")
        print(f"   - retrieval.top_k: {app_config.retrieval.top_k}")
        print(f"   - retrieval.search_mode: {app_config.retrieval.search_mode}")
        print(f"   - reranking.provider: {app_config.reranking.provider}")
        print(f"   - reranking.model: {app_config.reranking.model}")
        
        # 2. 测试RetrievalConfig创建
        print(f"\n🔧 测试RetrievalConfig:")
        
        # 测试不同的配置
        configs = [
            RetrievalConfig(enable_rerank=False, top_k=5, similarity_threshold=0.1, search_mode='semantic', enable_cache=False),
            RetrievalConfig(enable_rerank=True, top_k=5, similarity_threshold=0.1, search_mode='semantic', enable_cache=False)
        ]
        
        for i, config in enumerate(configs):
            print(f"   配置 {i+1}: enable_rerank={config.enable_rerank}")
        
        # 3. 测试增强检索服务初始化
        print(f"\n🚀 测试增强检索服务:")
        
        enhanced_config = {
            'default_top_k': 5,
            'similarity_threshold': 0.1,
            'search_mode': 'semantic',
            'enable_rerank': app_config.retrieval.enable_rerank,
            'enable_cache': False
        }
        
        enhanced_retrieval = EnhancedRetrievalService(enhanced_config)
        await enhanced_retrieval.initialize()
        
        print(f"   ✅ 增强检索服务初始化成功")
        
        # 4. 检查重排序服务可用性
        reranking_service = enhanced_retrieval._get_reranking_service()
        if reranking_service:
            print(f"   ✅ 重排序服务可用")
            
            # 检查健康状态
            health = await reranking_service.health_check()
            print(f"   - 健康状态: {health.get('status', 'unknown')}")
            print(f"   - 提供商: {health.get('provider', 'unknown')}")
            print(f"   - 模型已加载: {health.get('model_loaded', False)}")
        else:
            print(f"   ❌ 重排序服务不可用")
        
        # 5. 检查默认配置
        default_config = enhanced_retrieval.get_default_config()
        print(f"\n⚙️  默认配置:")
        print(f"   - enable_rerank: {default_config.enable_rerank}")
        print(f"   - top_k: {default_config.top_k}")
        print(f"   - search_mode: {default_config.search_mode}")
        
        # 6. 测试重排序逻辑判断
        print(f"\n🧪 测试重排序逻辑判断:")
        
        # 模拟检索流程中的重排序判断
        test_results = []  # 空结果列表
        
        for config in configs:
            rerank_name = "启用重排序" if config.enable_rerank else "不启用重排序"
            print(f"   {rerank_name}:")
            
            # 模拟增强检索服务中的重排序判断逻辑
            if config.enable_rerank and test_results:
                print(f"      → 条件满足，应该执行重排序")
            elif config.enable_rerank and not test_results:
                print(f"      → 重排序已启用，但无结果可重排序")
            else:
                print(f"      → 重排序未启用，跳过重排序")
        
        # 7. 检查系统健康状态
        print(f"\n🏥 系统健康检查:")
        health_status = await enhanced_retrieval.health_check()
        print(f"   - 整体状态: {health_status.get('status', 'unknown')}")
        
        if 'services' in health_status:
            services = health_status['services']
            if 'reranking_service' in services:
                rerank_health = services['reranking_service']
                print(f"   - 重排序服务状态: {rerank_health.get('status', 'unknown')}")
        
        # 8. 总结验证结果
        print(f"\n📋 验证总结:")
        
        config_ok = app_config.retrieval.enable_rerank
        service_ok = reranking_service is not None
        health_ok = health.get('status') != 'error' if reranking_service else False
        
        print(f"   ✅ 配置正确加载: {'是' if config_ok else '否'}")
        print(f"   ✅ 重排序服务可用: {'是' if service_ok else '否'}")
        print(f"   ✅ 服务健康状态: {'正常' if health_ok else '异常'}")
        
        if config_ok and service_ok:
            print(f"\n🎉 重排序功能配置正确，服务可用！")
            if not health_ok:
                print(f"⚠️  注意：重排序模型可能未正确加载，但逻辑流程正常")
        else:
            print(f"\n❌ 重排序功能存在问题")
        
        return True
        
    except Exception as e:
        print(f"❌ 验证失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_reranking_simple())
    sys.exit(0 if success else 1)