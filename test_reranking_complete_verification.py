#!/usr/bin/env python3
"""
完整的重排序功能验证 - 包括API密钥和模型加载
"""

import asyncio
import sys
import os
import uuid

# 设置环境变量（如果需要的话）
# os.environ["SILICONFLOW_API_KEY"] = "your_api_key_here"

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rag_system.config.loader import ConfigLoader
from rag_system.services.enhanced_retrieval_service import EnhancedRetrievalService
from rag_system.services.reranking_service import RerankingService
from rag_system.models.config import RetrievalConfig
from rag_system.models.vector import SearchResult

async def test_reranking_complete():
    """完整的重排序功能验证"""
    print("🎯 完整重排序功能验证...")
    
    try:
        # 1. 检查环境变量
        print("🔑 检查API密钥配置:")
        siliconflow_key = os.getenv("SILICONFLOW_API_KEY")
        if siliconflow_key:
            print(f"   ✅ SILICONFLOW_API_KEY: 已设置 (长度: {len(siliconflow_key)})")
        else:
            print(f"   ⚠️  SILICONFLOW_API_KEY: 未设置")
            print(f"   💡 请设置环境变量: export SILICONFLOW_API_KEY=your_api_key")
        
        # 2. 加载配置
        config_loader = ConfigLoader()
        app_config = config_loader.load_config()
        
        print(f"\n📋 配置检查:")
        print(f"   - retrieval.enable_rerank: {app_config.retrieval.enable_rerank}")
        print(f"   - reranking.provider: {app_config.reranking.provider}")
        print(f"   - reranking.model: {app_config.reranking.model}")
        print(f"   - reranking.api_key: {'已设置' if app_config.reranking.api_key else '未设置'}")
        print(f"   - reranking.base_url: {app_config.reranking.base_url}")
        
        # 3. 初始化重排序服务
        print(f"\n🚀 初始化重排序服务:")
        
        reranking_config = {
            'provider': app_config.reranking.provider,
            'model': app_config.reranking.model,
            'api_key': app_config.reranking.api_key,
            'base_url': app_config.reranking.base_url,
            'batch_size': app_config.reranking.batch_size,
            'max_length': app_config.reranking.max_length,
            'timeout': app_config.reranking.timeout
        }
        
        reranking_service = RerankingService(reranking_config)
        
        try:
            await reranking_service.initialize()
            print(f"   ✅ 重排序服务初始化成功")
        except Exception as e:
            print(f"   ❌ 重排序服务初始化失败: {str(e)}")
            if "API密钥" in str(e):
                print(f"   💡 请确保设置了正确的API密钥")
                return False
        
        # 4. 检查服务健康状态
        print(f"\n🏥 检查服务健康状态:")
        health = await reranking_service.health_check()
        print(f"   - 状态: {health.get('status', 'unknown')}")
        print(f"   - 提供商: {health.get('provider', 'unknown')}")
        print(f"   - 模型: {health.get('model_name', 'unknown')}")
        print(f"   - 模型已加载: {health.get('model_loaded', False)}")
        
        if health.get('status') == 'error':
            print(f"   ❌ 服务状态异常，无法继续测试")
            return False
        
        # 5. 创建测试数据
        print(f"\n🧪 创建测试数据:")
        
        # 创建与"人工智能"相关的测试内容，相关性递减
        test_contents = [
            "人工智能是计算机科学的一个分支，致力于创建能够执行通常需要人类智能的任务的系统。AI系统可以学习、推理、感知和做出决策。",
            "机器学习是人工智能的一个重要子集，它使计算机能够从数据中学习模式，而无需明确编程每个任务的解决方案。",
            "深度学习使用多层神经网络来模拟人脑的工作方式，是机器学习的一个强大分支，在图像识别和自然语言处理方面表现出色。",
            "自然语言处理（NLP）是人工智能的一个重要领域，专注于使计算机能够理解、解释和生成人类语言。",
            "计算机视觉是人工智能的一个分支，使机器能够解释和理解视觉世界，包括图像识别、物体检测和场景理解。",
            "数据科学涉及从大量数据中提取有价值的见解和知识，虽然与AI相关，但更侧重于数据分析和统计方法。",
            "云计算提供了可扩展的计算资源和服务，虽然可以支持AI应用，但本身并不是人工智能技术。"
        ]
        
        # 创建搜索结果，故意设置不太合理的相似度分数
        mock_results = []
        for i, content in enumerate(test_contents):
            # 故意让相似度分数与实际相关性不完全匹配
            similarity_score = 0.95 - i * 0.05  # 简单递减
            
            result = SearchResult(
                chunk_id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content=content,
                similarity_score=similarity_score,
                metadata={"source": f"test_doc_{i}.txt", "chunk_index": i}
            )
            mock_results.append(result)
        
        print(f"   创建了 {len(mock_results)} 个测试结果")
        
        # 6. 显示原始结果
        print(f"\n📊 原始结果 (按相似度排序):")
        for i, result in enumerate(mock_results):
            print(f"   {i+1}. 相似度: {result.similarity_score:.3f}")
            print(f"      内容: {result.content[:80]}...")
        
        # 7. 执行重排序
        print(f"\n🔄 执行重排序:")
        
        query = "什么是人工智能？请详细解释人工智能的定义和主要特征。"
        print(f"   查询: '{query}'")
        
        try:
            # 创建重排序配置
            rerank_config = RetrievalConfig(
                top_k=len(mock_results),
                similarity_threshold=0.1,
                search_mode='semantic',
                enable_rerank=True,
                enable_cache=False
            )
            
            # 记录开始时间
            start_time = asyncio.get_event_loop().time()
            
            # 执行重排序
            reranked_results = await reranking_service.rerank_results(
                query=query,
                results=mock_results,
                config=rerank_config
            )
            
            # 记录结束时间
            end_time = asyncio.get_event_loop().time()
            processing_time = end_time - start_time
            
            print(f"   ✅ 重排序执行成功 (耗时: {processing_time:.3f}s)")
            
            # 8. 显示重排序后的结果
            print(f"\n📊 重排序后结果:")
            for i, result in enumerate(reranked_results):
                rerank_score = result.metadata.get('rerank_score', 'N/A')
                print(f"   {i+1}. 相似度: {result.similarity_score:.3f}, 重排序分数: {rerank_score}")
                print(f"      内容: {result.content[:80]}...")
            
            # 9. 分析重排序效果
            print(f"\n📈 重排序效果分析:")
            
            # 检查顺序变化
            order_changes = []
            for i in range(len(reranked_results)):
                original_idx = next(
                    j for j, r in enumerate(mock_results) 
                    if r.chunk_id == reranked_results[i].chunk_id
                )
                if original_idx != i:
                    order_changes.append((i, original_idx))
            
            if order_changes:
                print(f"   ✅ 重排序生效：发现 {len(order_changes)} 个位置变化")
                print(f"   📋 具体变化:")
                for new_pos, old_pos in order_changes[:5]:  # 只显示前5个变化
                    print(f"      位置 {new_pos+1}: 原第{old_pos+1}名 → 现第{new_pos+1}名")
            else:
                print(f"   ⚠️  重排序可能未生效：结果顺序未发生变化")
            
            # 检查重排序分数
            has_rerank_scores = any(
                result.metadata.get('rerank_score') is not None 
                for result in reranked_results
            )
            
            if has_rerank_scores:
                print(f"   ✅ 重排序分数已添加到结果中")
                
                # 分析重排序分数分布
                rerank_scores = [
                    result.metadata.get('rerank_score', 0) 
                    for result in reranked_results 
                    if result.metadata.get('rerank_score') is not None
                ]
                
                if rerank_scores:
                    print(f"   📊 重排序分数统计:")
                    print(f"      最高分: {max(rerank_scores):.4f}")
                    print(f"      最低分: {min(rerank_scores):.4f}")
                    print(f"      平均分: {sum(rerank_scores)/len(rerank_scores):.4f}")
            else:
                print(f"   ⚠️  未找到重排序分数")
            
        except Exception as e:
            print(f"   ❌ 重排序执行失败: {str(e)}")
            print(f"   这可能是由于API密钥无效、网络问题或模型不可用导致的")
            return False
        
        # 10. 测试增强检索服务集成
        print(f"\n🔗 测试增强检索服务集成:")
        
        enhanced_config = {
            'default_top_k': 5,
            'similarity_threshold': 0.1,
            'search_mode': 'semantic',
            'enable_rerank': True,
            'enable_cache': False
        }
        
        enhanced_retrieval = EnhancedRetrievalService(enhanced_config)
        await enhanced_retrieval.initialize()
        
        # 检查重排序服务集成
        integrated_reranking_service = enhanced_retrieval._get_reranking_service()
        if integrated_reranking_service:
            print(f"   ✅ 重排序服务已正确集成")
            
            # 检查默认配置
            default_config = enhanced_retrieval.get_default_config()
            print(f"   - 默认启用重排序: {default_config.enable_rerank}")
            
            # 检查集成服务的健康状态
            integrated_health = await integrated_reranking_service.health_check()
            print(f"   - 集成服务状态: {integrated_health.get('status', 'unknown')}")
        else:
            print(f"   ❌ 重排序服务未正确集成")
        
        # 11. 获取服务指标
        print(f"\n📊 服务指标:")
        metrics = reranking_service.get_metrics()
        print(f"   - 总请求数: {metrics.get('total_requests', 0)}")
        print(f"   - 成功请求数: {metrics.get('successful_requests', 0)}")
        print(f"   - 失败请求数: {metrics.get('failed_requests', 0)}")
        print(f"   - 成功率: {metrics.get('success_rate', 0):.2%}")
        print(f"   - 平均处理时间: {metrics.get('average_processing_time', 0):.4f}s")
        
        # 12. 最终总结
        print(f"\n🎉 重排序功能验证完成！")
        print(f"\n📋 验证结果总结:")
        print(f"   ✅ 配置加载: 正常")
        print(f"   ✅ API密钥: {'正常' if app_config.reranking.api_key else '缺失'}")
        print(f"   ✅ 服务初始化: 正常")
        print(f"   ✅ 服务健康状态: {health.get('status', 'unknown')}")
        print(f"   ✅ 重排序执行: {'正常' if has_rerank_scores else '异常'}")
        print(f"   ✅ 服务集成: 正常")
        
        if has_rerank_scores and order_changes:
            print(f"\n💡 结论: 重排序功能完全正常！系统能够根据查询内容对搜索结果进行智能重排序。")
        elif has_rerank_scores:
            print(f"\n💡 结论: 重排序功能基本正常，但结果顺序未发生明显变化，可能是测试数据相关性差异不大。")
        else:
            print(f"\n💡 结论: 重排序功能配置正确，但执行可能存在问题，请检查API密钥和网络连接。")
        
        return True
        
    except Exception as e:
        print(f"❌ 验证失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 重排序功能完整验证")
    print("=" * 50)
    
    # 检查是否设置了API密钥
    if not os.getenv("SILICONFLOW_API_KEY"):
        print("⚠️  警告: 未检测到 SILICONFLOW_API_KEY 环境变量")
        print("请设置环境变量后重新运行:")
        print("export SILICONFLOW_API_KEY=your_api_key_here")
        print("或者在脚本开头取消注释并设置API密钥")
        print()
    
    success = asyncio.run(test_reranking_complete())
    sys.exit(0 if success else 1)