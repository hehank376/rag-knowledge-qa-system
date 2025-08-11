#!/usr/bin/env python3
"""
重排序集成功能演示脚本

演示重排序功能与检索流程的集成：
- 对比启用和禁用重排序的检索结果
- 展示重排序对结果排序的影响
- 显示性能监控和统计信息
"""

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, Mock

from rag_system.services.enhanced_retrieval_service import EnhancedRetrievalService
from rag_system.models.config import RetrievalConfig
from rag_system.models.vector import SearchResult


async def create_mock_enhanced_service():
    """创建模拟的增强检索服务"""
    config = {
        'default_top_k': 5,
        'similarity_threshold': 0.7,
        'search_mode': 'semantic',
        'enable_rerank': True,
        'enable_cache': False,
        'model_name': 'cross-encoder/ms-marco-MiniLM-L-6-v2',
        'batch_size': 32,
        'timeout': 30.0
    }
    
    service = EnhancedRetrievalService(config)
    
    # 创建示例检索结果
    import uuid
    sample_results = [
        SearchResult(
            chunk_id=str(uuid.uuid4()),
            document_id=str(uuid.uuid4()),
            content=f"这是关于人工智能的文档{i}，包含机器学习和深度学习的内容。",
            similarity_score=0.85 - i * 0.05,
            metadata={"source": f"ai_doc_{i}.txt", "topic": "AI", "length": 150 + i * 20}
        ) for i in range(5)
    ]
    
    # 模拟搜索路由器
    service.search_router.search_with_mode = AsyncMock(return_value=sample_results)
    service.search_router.get_usage_statistics = Mock(return_value={
        'semantic_searches': 2,
        'keyword_searches': 0,
        'hybrid_searches': 0,
        'total_searches': 2
    })
    
    # 模拟缓存服务
    service.cache_service.get_cached_results = AsyncMock(return_value=None)
    service.cache_service.cache_results = AsyncMock()
    service.cache_service.get_cache_info = AsyncMock(return_value={
        'enabled': False,
        'hit_rate': 0.0
    })
    
    # 模拟重排序服务
    async def mock_rerank(query, results, config):
        """模拟重排序逻辑"""
        if not config.enable_rerank:
            return results
        
        # 模拟重排序：根据查询内容调整分数
        reranked_results = []
        for i, result in enumerate(results):
            # 模拟交叉编码器给出的新分数
            new_score = 0.95 - i * 0.08  # 重排序后的分数
            
            reranked_result = SearchResult(
                chunk_id=result.chunk_id,
                document_id=result.document_id,
                content=result.content,
                similarity_score=new_score,
                metadata={
                    **result.metadata,
                    'original_score': result.similarity_score,
                    'rerank_score': new_score,
                    'rerank_rank': i + 1
                }
            )
            reranked_results.append(reranked_result)
        
        # 按新分数排序（这里为了演示，我们反转顺序）
        reranked_results.reverse()
        
        # 更新最终排名
        for i, result in enumerate(reranked_results):
            result.metadata['final_rank'] = i + 1
        
        return reranked_results
    
    service.reranking_service.rerank_results = mock_rerank
    service.reranking_service.get_metrics = Mock(return_value={
        'model_loaded': True,
        'model_name': 'cross-encoder/ms-marco-MiniLM-L-6-v2',
        'total_requests': 1,
        'successful_requests': 1,
        'failed_requests': 0,
        'success_rate': 1.0,
        'average_processing_time': 0.125
    })
    
    return service


async def demonstrate_reranking_integration():
    """演示重排序集成功能"""
    print("🚀 重排序集成功能演示")
    print("=" * 60)
    
    # 创建增强检索服务
    service = await create_mock_enhanced_service()
    
    # 测试查询
    test_query = "人工智能和机器学习的最新发展"
    
    print(f"📝 测试查询: {test_query}")
    print()
    
    # 1. 不启用重排序的搜索
    print("1️⃣ 不启用重排序的搜索结果:")
    print("-" * 40)
    
    config_no_rerank = RetrievalConfig(
        search_mode='semantic',
        enable_rerank=False,
        enable_cache=False,
        top_k=5
    )
    
    start_time = datetime.now()
    results_no_rerank = await service.search_with_config(test_query, config_no_rerank)
    no_rerank_time = (datetime.now() - start_time).total_seconds()
    
    for i, result in enumerate(results_no_rerank):
        print(f"  {i+1}. 分数: {result.similarity_score:.3f} | {result.content[:50]}...")
    
    print(f"⏱️  搜索耗时: {no_rerank_time:.3f}秒")
    print()
    
    # 2. 启用重排序的搜索
    print("2️⃣ 启用重排序的搜索结果:")
    print("-" * 40)
    
    config_with_rerank = RetrievalConfig(
        search_mode='semantic',
        enable_rerank=True,
        enable_cache=False,
        top_k=5
    )
    
    start_time = datetime.now()
    results_with_rerank = await service.search_with_config(test_query, config_with_rerank)
    rerank_time = (datetime.now() - start_time).total_seconds()
    
    for i, result in enumerate(results_with_rerank):
        original_score = result.metadata.get('original_score', 'N/A')
        rerank_score = result.metadata.get('rerank_score', result.similarity_score)
        print(f"  {i+1}. 重排序分数: {rerank_score:.3f} (原始: {original_score}) | {result.content[:50]}...")
    
    print(f"⏱️  搜索耗时: {rerank_time:.3f}秒")
    print()
    
    # 3. 对比分析
    print("3️⃣ 对比分析:")
    print("-" * 40)
    
    print(f"📊 结果数量对比:")
    print(f"   - 无重排序: {len(results_no_rerank)} 个结果")
    print(f"   - 有重排序: {len(results_with_rerank)} 个结果")
    print()
    
    print(f"⏱️  性能对比:")
    print(f"   - 无重排序耗时: {no_rerank_time:.3f}秒")
    print(f"   - 有重排序耗时: {rerank_time:.3f}秒")
    print(f"   - 重排序开销: {rerank_time - no_rerank_time:.3f}秒")
    print()
    
    print(f"🔄 排序变化:")
    if len(results_no_rerank) == len(results_with_rerank):
        for i in range(len(results_no_rerank)):
            no_rerank_id = results_no_rerank[i].chunk_id
            rerank_id = results_with_rerank[i].chunk_id
            if no_rerank_id != rerank_id:
                print(f"   - 位置 {i+1}: 结果发生变化")
            else:
                print(f"   - 位置 {i+1}: 结果保持不变")
    print()
    
    # 4. 获取统计信息
    print("4️⃣ 服务统计信息:")
    print("-" * 40)
    
    stats = service.get_search_statistics()
    
    print(f"🔍 搜索统计:")
    router_stats = stats.get('router_statistics', {})
    print(f"   - 总搜索次数: {router_stats.get('total_searches', 0)}")
    print(f"   - 语义搜索: {router_stats.get('semantic_searches', 0)}")
    print()
    
    print(f"🔄 重排序统计:")
    rerank_stats = stats.get('reranking_statistics', {})
    print(f"   - 重排序请求: {rerank_stats.get('total_rerank_requests', 0)}")
    print(f"   - 成功重排序: {rerank_stats.get('successful_reranks', 0)}")
    print(f"   - 失败重排序: {rerank_stats.get('failed_reranks', 0)}")
    print(f"   - 成功率: {rerank_stats.get('rerank_success_rate', 0):.1%}")
    print(f"   - 平均耗时: {rerank_stats.get('avg_rerank_time', 0):.3f}秒")
    print()
    
    # 5. 重排序服务指标
    print("5️⃣ 重排序服务指标:")
    print("-" * 40)
    
    rerank_metrics = await service.get_reranking_metrics()
    print(f"🤖 模型状态:")
    print(f"   - 模型已加载: {rerank_metrics.get('model_loaded', False)}")
    print(f"   - 模型名称: {rerank_metrics.get('model_name', 'N/A')}")
    print()
    
    print(f"📈 性能指标:")
    print(f"   - 总请求数: {rerank_metrics.get('total_requests', 0)}")
    print(f"   - 成功请求: {rerank_metrics.get('successful_requests', 0)}")
    print(f"   - 失败请求: {rerank_metrics.get('failed_requests', 0)}")
    print(f"   - 成功率: {rerank_metrics.get('success_rate', 0):.1%}")
    print(f"   - 平均处理时间: {rerank_metrics.get('average_processing_time', 0):.3f}秒")
    print()
    
    # 6. 健康检查
    print("6️⃣ 系统健康检查:")
    print("-" * 40)
    
    health = await service.health_check()
    print(f"🏥 整体状态: {health.get('status', 'unknown')}")
    
    components = health.get('components', {})
    for component_name, component_health in components.items():
        if isinstance(component_health, dict):
            status = component_health.get('status', 'unknown')
        else:
            status = component_health
        print(f"   - {component_name}: {status}")
    print()
    
    print("✅ 重排序集成功能演示完成！")
    print("=" * 60)


async def main():
    """主函数"""
    try:
        await demonstrate_reranking_integration()
    except Exception as e:
        print(f"❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())