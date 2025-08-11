#!/usr/bin/env python3
"""
错误处理系统集成演示
展示如何在实际检索服务中使用统一错误处理机制
"""
import asyncio
import sys
import os
from typing import Dict, Any, List, Optional

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rag_system.utils.exceptions import (
    SearchModeError, RerankingModelError, CacheConnectionError, ConfigLoadError
)
from rag_system.utils.error_handler import handle_errors, create_error_context
from rag_system.utils.retrieval_error_handler import (
    handle_search_error, handle_reranking_error, handle_cache_error
)
from rag_system.utils.error_monitor import global_error_monitor, get_error_statistics
from rag_system.utils.error_messages import Language, set_default_language


class MockSearchResult:
    """模拟搜索结果"""
    def __init__(self, content: str, score: float):
        self.content = content
        self.similarity_score = score
    
    def __str__(self):
        return f"SearchResult(content='{self.content[:50]}...', score={self.similarity_score})"


class EnhancedRetrievalServiceDemo:
    """增强检索服务演示（集成错误处理）"""
    
    def __init__(self):
        self.component_name = "enhanced_retrieval_service"
        self.cache_enabled = True
        self.rerank_enabled = True
        
        # 模拟一些故障场景
        self.simulate_search_failure = False
        self.simulate_rerank_failure = False
        self.simulate_cache_failure = False
    
    @handle_errors(component="enhanced_retrieval_service", operation="search_with_config")
    async def search_with_config(
        self,
        query: str,
        config: Dict[str, Any],
        user_id: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> List[MockSearchResult]:
        """使用配置进行检索的主要方法（集成错误处理）"""
        
        print(f"🔍 开始检索: '{query}'")
        print(f"📋 配置: {config}")
        
        # 1. 尝试从缓存获取结果
        cached_results = await self._get_cached_results(query, config, request_id)
        if cached_results:
            print("💾 缓存命中，返回缓存结果")
            return cached_results
        
        # 2. 执行搜索
        search_results = await self._execute_search(query, config, user_id, request_id)
        
        # 3. 重排序（如果启用）
        if config.get('enable_rerank', False):
            search_results = await self._rerank_results(query, search_results, config, user_id, request_id)
        
        # 4. 缓存结果
        if config.get('enable_cache', False):
            await self._cache_results(query, search_results, config, request_id)
        
        print(f"✅ 检索完成，返回 {len(search_results)} 个结果")
        return search_results
    
    async def _get_cached_results(
        self,
        query: str,
        config: Dict[str, Any],
        request_id: Optional[str] = None
    ) -> Optional[List[MockSearchResult]]:
        """从缓存获取结果"""
        if not config.get('enable_cache', False):
            return None
        
        if self.simulate_cache_failure:
            error = CacheConnectionError("模拟Redis连接失败")
            error_response = await handle_cache_error(
                error=error,
                cache_key=f"search:{hash(query)}",
                operation="get",
                config=config,
                request_id=request_id
            )
            
            # 如果有降级结果，使用降级结果
            if error_response.fallback_result is not None:
                return error_response.fallback_result
            
            # 否则继续正常流程（缓存失败不影响检索）
            return None
        
        # 模拟缓存未命中
        return None
    
    async def _execute_search(
        self,
        query: str,
        config: Dict[str, Any],
        user_id: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> List[MockSearchResult]:
        """执行搜索"""
        search_mode = config.get('search_mode', 'semantic')
        
        if self.simulate_search_failure:
            error = SearchModeError(f"{search_mode}搜索模拟失败", search_mode=search_mode)
            error_response = await handle_search_error(
                error=error,
                query=query,
                config=config,
                user_id=user_id,
                request_id=request_id
            )
            
            # 如果有降级结果，使用降级结果
            if error_response.fallback_result is not None:
                print(f"🔄 搜索降级成功: {search_mode} -> semantic")
                return error_response.fallback_result
            
            # 否则返回空结果
            print(f"❌ 搜索失败且无法降级")
            return []
        
        # 模拟正常搜索结果
        mock_results = [
            MockSearchResult(f"搜索结果1 - 关于'{query}'的内容", 0.95),
            MockSearchResult(f"搜索结果2 - 与'{query}'相关的信息", 0.87),
            MockSearchResult(f"搜索结果3 - '{query}'的详细说明", 0.82),
            MockSearchResult(f"搜索结果4 - '{query}'的应用案例", 0.78),
            MockSearchResult(f"搜索结果5 - '{query}'的最佳实践", 0.75),
        ]
        
        print(f"🎯 {search_mode}搜索完成，找到 {len(mock_results)} 个结果")
        return mock_results
    
    async def _rerank_results(
        self,
        query: str,
        results: List[MockSearchResult],
        config: Dict[str, Any],
        user_id: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> List[MockSearchResult]:
        """重排序结果"""
        if not results:
            return results
        
        if self.simulate_rerank_failure:
            error = RerankingModelError("模拟重排序模型加载失败")
            error_response = await handle_reranking_error(
                error=error,
                query=query,
                original_results=results,
                config=config,
                user_id=user_id,
                request_id=request_id
            )
            
            # 如果有降级结果，使用降级结果
            if error_response.fallback_result is not None:
                print("🔄 重排序降级成功，返回原始结果")
                return error_response.fallback_result
            
            # 否则返回原始结果
            print("❌ 重排序失败，返回原始结果")
            return results
        
        # 模拟重排序（简单地调整分数）
        for i, result in enumerate(results):
            # 模拟重排序调整分数
            result.similarity_score = result.similarity_score + (0.1 - i * 0.02)
        
        # 重新排序
        reranked_results = sorted(results, key=lambda x: x.similarity_score, reverse=True)
        print(f"🔀 重排序完成，调整了 {len(results)} 个结果的顺序")
        return reranked_results
    
    async def _cache_results(
        self,
        query: str,
        results: List[MockSearchResult],
        config: Dict[str, Any],
        request_id: Optional[str] = None
    ) -> None:
        """缓存结果"""
        if not config.get('enable_cache', False):
            return
        
        try:
            # 模拟缓存写入
            print(f"💾 缓存结果: {len(results)} 个结果")
        except Exception as e:
            # 缓存失败不影响主流程
            print(f"⚠️ 缓存写入失败: {e}")
    
    def set_failure_simulation(self, search: bool = False, rerank: bool = False, cache: bool = False):
        """设置故障模拟"""
        self.simulate_search_failure = search
        self.simulate_rerank_failure = rerank
        self.simulate_cache_failure = cache


async def demo_normal_operation():
    """演示正常操作"""
    print("\n" + "="*60)
    print("演示1: 正常操作")
    print("="*60)
    
    service = EnhancedRetrievalServiceDemo()
    
    config = {
        'search_mode': 'semantic',
        'enable_rerank': True,
        'enable_cache': True,
        'top_k': 5
    }
    
    results = await service.search_with_config(
        query="人工智能的发展历程",
        config=config,
        user_id="demo-user",
        request_id="demo-001"
    )
    
    print(f"\n📊 最终结果:")
    for i, result in enumerate(results, 1):
        print(f"  {i}. {result}")


async def demo_search_failure_recovery():
    """演示搜索失败和恢复"""
    print("\n" + "="*60)
    print("演示2: 搜索失败和降级恢复")
    print("="*60)
    
    service = EnhancedRetrievalServiceDemo()
    service.set_failure_simulation(search=True)  # 模拟搜索失败
    
    config = {
        'search_mode': 'hybrid',  # 混合搜索失败后会降级到语义搜索
        'enable_rerank': False,
        'enable_cache': False,
        'top_k': 5
    }
    
    results = await service.search_with_config(
        query="机器学习算法比较",
        config=config,
        user_id="demo-user",
        request_id="demo-002"
    )
    
    print(f"\n📊 降级后的结果:")
    for i, result in enumerate(results, 1):
        print(f"  {i}. {result}")


async def demo_reranking_failure():
    """演示重排序失败"""
    print("\n" + "="*60)
    print("演示3: 重排序失败处理")
    print("="*60)
    
    service = EnhancedRetrievalServiceDemo()
    service.set_failure_simulation(rerank=True)  # 模拟重排序失败
    
    config = {
        'search_mode': 'semantic',
        'enable_rerank': True,  # 重排序会失败
        'enable_cache': False,
        'top_k': 5
    }
    
    results = await service.search_with_config(
        query="深度学习框架对比",
        config=config,
        user_id="demo-user",
        request_id="demo-003"
    )
    
    print(f"\n📊 重排序失败后的结果:")
    for i, result in enumerate(results, 1):
        print(f"  {i}. {result}")


async def demo_cache_failure():
    """演示缓存失败"""
    print("\n" + "="*60)
    print("演示4: 缓存失败处理")
    print("="*60)
    
    service = EnhancedRetrievalServiceDemo()
    service.set_failure_simulation(cache=True)  # 模拟缓存失败
    
    config = {
        'search_mode': 'semantic',
        'enable_rerank': False,
        'enable_cache': True,  # 缓存会失败
        'top_k': 5
    }
    
    results = await service.search_with_config(
        query="自然语言处理技术",
        config=config,
        user_id="demo-user",
        request_id="demo-004"
    )
    
    print(f"\n📊 缓存失败后的结果:")
    for i, result in enumerate(results, 1):
        print(f"  {i}. {result}")


async def demo_multiple_failures():
    """演示多重故障"""
    print("\n" + "="*60)
    print("演示5: 多重故障处理")
    print("="*60)
    
    service = EnhancedRetrievalServiceDemo()
    service.set_failure_simulation(search=True, rerank=True, cache=True)  # 模拟所有组件失败
    
    config = {
        'search_mode': 'hybrid',
        'enable_rerank': True,
        'enable_cache': True,
        'top_k': 5
    }
    
    results = await service.search_with_config(
        query="计算机视觉应用",
        config=config,
        user_id="demo-user",
        request_id="demo-005"
    )
    
    print(f"\n📊 多重故障后的结果:")
    for i, result in enumerate(results, 1):
        print(f"  {i}. {result}")


async def demo_error_monitoring():
    """演示错误监控"""
    print("\n" + "="*60)
    print("演示6: 错误监控和统计")
    print("="*60)
    
    # 获取错误统计
    stats = get_error_statistics()
    
    print("📈 错误监控统计:")
    print(f"  总错误数: {stats.total_errors}")
    print(f"  错误率: {stats.error_rate_per_minute:.2f} 错误/分钟")
    print(f"  按严重程度分布:")
    for severity, count in stats.error_by_severity.items():
        print(f"    {severity.value}: {count}")
    print(f"  按组件分布:")
    for component, count in stats.error_by_component.items():
        print(f"    {component}: {count}")
    print(f"  按错误代码分布:")
    for code, count in stats.error_by_code.items():
        print(f"    {code}: {count}")
    
    # 获取最近的告警
    recent_alerts = global_error_monitor.get_recent_alerts(5)
    print(f"\n🚨 最近的告警 ({len(recent_alerts)} 个):")
    for alert in recent_alerts:
        print(f"  [{alert.level.value}] {alert.title}: {alert.message}")


async def main():
    """主演示函数"""
    print("🚀 错误处理系统集成演示")
    print("展示如何在实际检索服务中使用统一错误处理机制")
    
    # 设置中文错误消息
    set_default_language(Language.ZH_CN)
    
    # 运行各种演示场景
    await demo_normal_operation()
    await demo_search_failure_recovery()
    await demo_reranking_failure()
    await demo_cache_failure()
    await demo_multiple_failures()
    await demo_error_monitoring()
    
    print("\n" + "="*60)
    print("✅ 演示完成")
    print("="*60)
    print("\n主要特性展示:")
    print("1. ✅ 统一错误处理 - 所有错误都通过统一的处理机制")
    print("2. ✅ 智能降级策略 - 搜索模式、重排序、缓存的智能降级")
    print("3. ✅ 错误监控统计 - 实时错误统计和模式检测")
    print("4. ✅ 多语言支持 - 错误信息本地化")
    print("5. ✅ 告警系统 - 自动告警和通知")
    print("6. ✅ 错误恢复 - 自动错误恢复和重试机制")
    print("7. ✅ 装饰器支持 - 简化错误处理集成")
    print("8. ✅ 上下文记录 - 详细的错误上下文信息")


if __name__ == "__main__":
    asyncio.run(main())