#!/usr/bin/env python3
"""
验证重排序功能是否正常工作
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rag_system.config.loader import ConfigLoader
from rag_system.services.enhanced_retrieval_service import EnhancedRetrievalService
from rag_system.models.config import RetrievalConfig

async def test_reranking_functionality():
    """测试重排序功能"""
    print("🔍 验证重排序功能...")
    
    try:
        # 1. 加载配置
        config_loader = ConfigLoader()
        app_config = config_loader.load_config()
        
        print(f"📋 当前重排序配置:")
        print(f"   - 启用重排序: {app_config.retrieval.enable_rerank}")
        print(f"   - 重排序提供商: {app_config.reranking.provider}")
        print(f"   - 重排序模型: {app_config.reranking.model}")
        print(f"   - API密钥: {'已设置' if app_config.reranking.api_key else '未设置'}")
        
        # 2. 初始化增强检索服务
        retrieval_config = {
            'default_top_k': app_config.retrieval.top_k,
            'similarity_threshold': app_config.retrieval.similarity_threshold,
            'search_mode': app_config.retrieval.search_mode,
            'enable_rerank': app_config.retrieval.enable_rerank,
            'enable_cache': app_config.retrieval.enable_cache
        }
        
        enhanced_retrieval = EnhancedRetrievalService(retrieval_config)
        await enhanced_retrieval.initialize()
        
        print("✅ 增强检索服务初始化成功")
        
        # 3. 测试重排序服务可用性
        reranking_service = enhanced_retrieval._get_reranking_service()
        if reranking_service:
            print("✅ 重排序服务可用")
            
            # 检查重排序服务健康状态
            health = await reranking_service.health_check()
            print(f"📊 重排序服务健康状态: {health}")
            
            # 获取重排序服务指标
            metrics = reranking_service.get_metrics()
            print(f"📈 重排序服务指标: {metrics}")
        else:
            print("❌ 重排序服务不可用")
            return False
        
        # 4. 测试不同配置下的检索结果
        test_query = "什么是人工智能"
        
        print(f"\n🔍 测试查询: '{test_query}'")
        
        # 4.1 不启用重排序的检索
        config_without_rerank = RetrievalConfig(
            top_k=10,
            similarity_threshold=0.1,
            search_mode='semantic',
            enable_rerank=False,
            enable_cache=False
        )
        
        print("\n📋 测试1: 不启用重排序")
        try:
            results_without_rerank = await enhanced_retrieval.search_with_config(
                query=test_query,
                config=config_without_rerank
            )
            print(f"   - 结果数量: {len(results_without_rerank)}")
            if results_without_rerank:
                print(f"   - 最高相似度: {results_without_rerank[0].similarity_score:.4f}")
                print(f"   - 最低相似度: {results_without_rerank[-1].similarity_score:.4f}")
                print("   - 前3个结果的相似度:")
                for i, result in enumerate(results_without_rerank[:3]):
                    print(f"     {i+1}. {result.similarity_score:.4f} - {result.content[:50]}...")
        except Exception as e:
            print(f"   ❌ 无重排序检索失败: {str(e)}")
            results_without_rerank = []
        
        # 4.2 启用重排序的检索
        config_with_rerank = RetrievalConfig(
            top_k=10,
            similarity_threshold=0.1,
            search_mode='semantic',
            enable_rerank=True,
            enable_cache=False
        )
        
        print("\n📋 测试2: 启用重排序")
        try:
            results_with_rerank = await enhanced_retrieval.search_with_config(
                query=test_query,
                config=config_with_rerank
            )
            print(f"   - 结果数量: {len(results_with_rerank)}")
            if results_with_rerank:
                print(f"   - 最高相似度: {results_with_rerank[0].similarity_score:.4f}")
                print(f"   - 最低相似度: {results_with_rerank[-1].similarity_score:.4f}")
                print("   - 前3个结果的相似度:")
                for i, result in enumerate(results_with_rerank[:3]):
                    print(f"     {i+1}. {result.similarity_score:.4f} - {result.content[:50]}...")
                    
                # 检查是否有重排序元数据
                if hasattr(result, 'metadata') and result.metadata:
                    rerank_score = result.metadata.get('rerank_score')
                    if rerank_score is not None:
                        print(f"        重排序分数: {rerank_score:.4f}")
        except Exception as e:
            print(f"   ❌ 重排序检索失败: {str(e)}")
            results_with_rerank = []
        
        # 5. 比较结果
        print("\n📊 结果比较:")
        if results_without_rerank and results_with_rerank:
            # 比较结果顺序是否发生变化
            same_order = True
            if len(results_without_rerank) == len(results_with_rerank):
                for i in range(min(5, len(results_without_rerank))):  # 比较前5个结果
                    if (results_without_rerank[i].chunk_id != results_with_rerank[i].chunk_id):
                        same_order = False
                        break
            else:
                same_order = False
            
            if same_order:
                print("   ⚠️  结果顺序相同，重排序可能未生效")
            else:
                print("   ✅ 结果顺序发生变化，重排序已生效")
                
            # 显示顺序变化
            print("   📋 顺序对比 (前5个结果):")
            print("      无重排序 -> 有重排序")
            for i in range(min(5, len(results_without_rerank), len(results_with_rerank))):
                without_id = results_without_rerank[i].chunk_id
                with_id = results_with_rerank[i].chunk_id
                change_indicator = "→" if without_id != with_id else "="
                print(f"      {i+1}. {without_id} {change_indicator} {with_id}")
        
        # 6. 获取服务统计信息
        print("\n📈 服务统计信息:")
        stats = enhanced_retrieval.get_search_statistics()
        if 'reranking' in stats:
            rerank_stats = stats['reranking']
            print(f"   - 重排序调用次数: {rerank_stats.get('total_rerank_calls', 0)}")
            print(f"   - 平均重排序时间: {rerank_stats.get('avg_rerank_time', 0):.4f}s")
            print(f"   - 总重排序时间: {rerank_stats.get('total_rerank_time', 0):.4f}s")
        
        # 7. 健康检查
        print("\n🏥 系统健康检查:")
        health_status = await enhanced_retrieval.health_check()
        print(f"   - 整体状态: {health_status.get('status', 'unknown')}")
        if 'services' in health_status:
            services = health_status['services']
            if 'reranking_service' in services:
                rerank_health = services['reranking_service']
                print(f"   - 重排序服务状态: {rerank_health.get('status', 'unknown')}")
        
        print("\n🎉 重排序功能验证完成！")
        return True
        
    except Exception as e:
        print(f"❌ 验证失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_reranking_functionality())
    sys.exit(0 if success else 1)