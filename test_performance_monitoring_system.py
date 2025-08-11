#!/usr/bin/env python3
"""
检索性能监控系统测试
验证任务6.2的实现（对应需求13：性能和监控）
"""
import asyncio
import sys
import os
import time
import random
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rag_system.utils.performance_monitor import (
    RetrievalPerformanceMonitor, OperationType, SearchMode,
    start_performance_monitoring, complete_performance_monitoring,
    record_cache_hit, record_reranking_performance, record_search_mode_performance,
    log_performance_exception, get_performance_report, monitor_performance
)


class PerformanceMonitoringTest:
    """性能监控系统测试类"""
    
    def __init__(self):
        self.test_results = []
        self.monitor = RetrievalPerformanceMonitor()
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("检索性能监控系统测试")
        print("对应需求13：性能和监控（验收标准13.1-13.7）")
        print("=" * 60)
        
        test_methods = [
            self.test_response_time_monitoring,      # 需求13.1
            self.test_cache_hit_rate_monitoring,     # 需求13.2
            self.test_reranking_performance_monitoring, # 需求13.3
            self.test_search_mode_usage_monitoring,  # 需求13.4
            self.test_system_stability_monitoring,   # 需求13.5
            self.test_detailed_performance_stats,    # 需求13.6
            self.test_exception_logging,             # 需求13.7
            self.test_performance_decorators,
            self.test_concurrent_monitoring
        ]
        
        for test_method in test_methods:
            try:
                print(f"\n运行测试: {test_method.__name__}")
                await test_method()
                self.test_results.append((test_method.__name__, "PASSED", None))
                print(f"✅ {test_method.__name__} 通过")
            except Exception as e:
                self.test_results.append((test_method.__name__, "FAILED", str(e)))
                print(f"❌ {test_method.__name__} 失败: {e}")
        
        self.print_test_summary()
    
    async def test_response_time_monitoring(self):
        """测试响应时间监控（需求13.1）"""
        print("  测试响应时间监控...")
        
        # 模拟多个查询操作
        query_times = []
        for i in range(10):
            query_id = f"test-query-{i}"
            metric_key = start_performance_monitoring(
                query_id=query_id,
                operation_type=OperationType.FULL_RETRIEVAL,
                search_mode=SearchMode.SEMANTIC
            )
            
            # 模拟不同的处理时间
            processing_time = random.uniform(0.1, 2.0)
            await asyncio.sleep(processing_time)
            query_times.append(processing_time * 1000)  # 转换为毫秒
            
            complete_performance_monitoring(
                metric_key=metric_key,
                success=True,
                result_count=random.randint(1, 10)
            )
        
        # 获取性能报告
        report = get_performance_report(time_range_minutes=1)
        
        # 验证响应时间统计
        assert report.response_time_stats.total_queries >= 10
        assert report.response_time_stats.average_ms > 0
        assert report.response_time_stats.min_ms > 0
        assert report.response_time_stats.max_ms > 0
        assert report.response_time_stats.median_ms > 0
        
        print(f"    ✓ 记录了 {report.response_time_stats.total_queries} 个查询")
        print(f"    ✓ 平均响应时间: {report.response_time_stats.average_ms:.2f}ms")
        print(f"    ✓ 中位数响应时间: {report.response_time_stats.median_ms:.2f}ms")
    
    async def test_cache_hit_rate_monitoring(self):
        """测试缓存命中率监控（需求13.2）"""
        print("  测试缓存命中率监控...")
        
        # 模拟缓存操作
        cache_operations = [
            (True, 10.5),   # 命中，10.5ms
            (False, 150.2), # 未命中，150.2ms
            (True, 8.3),    # 命中，8.3ms
            (True, 12.1),   # 命中，12.1ms
            (False, 145.8), # 未命中，145.8ms
            (True, 9.7),    # 命中，9.7ms
        ]
        
        for hit, duration in cache_operations:
            record_cache_hit(hit, duration)
        
        # 获取缓存统计
        report = get_performance_report(time_range_minutes=1)
        cache_stats = report.cache_stats
        
        # 验证缓存统计
        assert cache_stats.hit_count == 4
        assert cache_stats.miss_count == 2
        assert abs(cache_stats.hit_rate - 4/6) < 0.01  # 命中率应该是2/3
        assert cache_stats.average_hit_duration_ms > 0
        assert cache_stats.average_miss_duration_ms > 0
        
        print(f"    ✓ 缓存命中率: {cache_stats.hit_rate:.3f}")
        print(f"    ✓ 平均命中时间: {cache_stats.average_hit_duration_ms:.2f}ms")
        print(f"    ✓ 平均未命中时间: {cache_stats.average_miss_duration_ms:.2f}ms")
    
    async def test_reranking_performance_monitoring(self):
        """测试重排序性能监控（需求13.3）"""
        print("  测试重排序性能监控...")
        
        # 模拟重排序操作
        reranking_operations = [
            (True, 250.5, 10),   # 成功，250.5ms，10个文档
            (True, 180.3, 8),    # 成功，180.3ms，8个文档
            (False, 50.1, 0),    # 失败，50.1ms，0个文档
            (True, 320.7, 15),   # 成功，320.7ms，15个文档
            (True, 200.2, 12),   # 成功，200.2ms，12个文档
        ]
        
        for success, duration, doc_count in reranking_operations:
            record_reranking_performance(success, duration, doc_count)
        
        # 获取重排序统计
        report = get_performance_report(time_range_minutes=1)
        rerank_stats = report.reranking_stats
        
        # 验证重排序统计
        assert rerank_stats.total_operations == 5
        assert rerank_stats.success_count == 4
        assert abs(rerank_stats.success_rate - 0.8) < 0.01  # 成功率80%
        assert rerank_stats.average_duration_ms > 0
        assert rerank_stats.average_documents_processed > 0
        
        print(f"    ✓ 重排序成功率: {rerank_stats.success_rate:.3f}")
        print(f"    ✓ 平均重排序时间: {rerank_stats.average_duration_ms:.2f}ms")
        print(f"    ✓ 平均处理文档数: {rerank_stats.average_documents_processed:.1f}")
    
    async def test_search_mode_usage_monitoring(self):
        """测试搜索模式使用统计（需求13.4）"""
        print("  测试搜索模式使用统计...")
        
        # 模拟不同搜索模式的使用
        search_operations = [
            (SearchMode.SEMANTIC, 120.5, True),
            (SearchMode.SEMANTIC, 110.3, True),
            (SearchMode.KEYWORD, 80.7, True),
            (SearchMode.HYBRID, 200.1, True),
            (SearchMode.SEMANTIC, 130.2, False),  # 失败
            (SearchMode.KEYWORD, 75.8, True),
            (SearchMode.HYBRID, 180.9, True),
        ]
        
        for mode, duration, success in search_operations:
            record_search_mode_performance(mode, duration, success)
        
        # 获取搜索模式统计
        report = get_performance_report(time_range_minutes=1)
        mode_stats = report.search_mode_stats
        
        # 验证搜索模式统计
        assert mode_stats.mode_usage['semantic'] == 3
        assert mode_stats.mode_usage['keyword'] == 2
        assert mode_stats.mode_usage['hybrid'] == 2
        
        # 验证使用分布
        distribution = mode_stats.get_usage_distribution()
        assert abs(distribution['semantic'] - 3/7) < 0.01
        assert abs(distribution['keyword'] - 2/7) < 0.01
        assert abs(distribution['hybrid'] - 2/7) < 0.01
        
        print(f"    ✓ 语义搜索使用: {mode_stats.mode_usage['semantic']} 次")
        print(f"    ✓ 关键词搜索使用: {mode_stats.mode_usage['keyword']} 次")
        print(f"    ✓ 混合搜索使用: {mode_stats.mode_usage['hybrid']} 次")
        print(f"    ✓ 语义搜索成功率: {mode_stats.mode_success_rate['semantic']:.3f}")
    
    async def test_system_stability_monitoring(self):
        """测试系统稳定性监控（需求13.5）"""
        print("  测试系统稳定性监控...")
        
        # 获取系统稳定性统计
        report = get_performance_report(time_range_minutes=1)
        stability = report.system_stability
        
        # 验证系统稳定性指标
        assert 0 <= stability.cpu_usage_percent <= 100
        assert 0 <= stability.memory_usage_percent <= 100
        assert stability.active_queries >= 0
        assert 0 <= stability.error_rate <= 100
        assert 0 <= stability.stability_score <= 100
        
        print(f"    ✓ CPU使用率: {stability.cpu_usage_percent:.1f}%")
        print(f"    ✓ 内存使用率: {stability.memory_usage_percent:.1f}%")
        print(f"    ✓ 活跃查询数: {stability.active_queries}")
        print(f"    ✓ 错误率: {stability.error_rate:.2f}%")
        print(f"    ✓ 稳定性评分: {stability.stability_score:.1f}/100")
    
    async def test_detailed_performance_stats(self):
        """测试详细性能统计（需求13.6）"""
        print("  测试详细性能统计...")
        
        # 获取详细性能报告
        report = get_performance_report(time_range_minutes=5)
        
        # 验证报告结构
        assert report.timestamp is not None
        assert report.time_range_minutes == 5
        assert report.response_time_stats is not None
        assert report.cache_stats is not None
        assert report.reranking_stats is not None
        assert report.search_mode_stats is not None
        assert report.system_stability is not None
        assert report.exception_summary is not None
        
        # 测试报告导出
        report_dict = report.to_dict()
        assert 'timestamp' in report_dict
        assert 'response_time_stats' in report_dict
        assert 'cache_stats' in report_dict
        
        # 测试JSON导出
        json_export = self.monitor.export_metrics("json", 5)
        assert len(json_export) > 0
        assert '"timestamp"' in json_export
        
        print(f"    ✓ 生成了完整的性能报告")
        print(f"    ✓ 报告时间范围: {report.time_range_minutes} 分钟")
        print(f"    ✓ JSON导出长度: {len(json_export)} 字符")
    
    async def test_exception_logging(self):
        """测试异常日志记录（需求13.7）"""
        print("  测试异常日志记录...")
        
        # 模拟异常记录
        exceptions = [
            (ValueError("测试值错误"), {"operation": "search", "query": "test1"}),
            (ConnectionError("连接失败"), {"operation": "cache", "key": "test_key"}),
            (TimeoutError("操作超时"), {"operation": "rerank", "docs": 10}),
            (ValueError("另一个值错误"), {"operation": "search", "query": "test2"}),
        ]
        
        for exception, context in exceptions:
            log_performance_exception(exception, context)
        
        # 获取异常摘要
        report = get_performance_report(time_range_minutes=1)
        exception_summary = report.exception_summary
        
        # 验证异常统计
        assert exception_summary.total_exceptions == 4
        assert exception_summary.exception_types['ValueError'] == 2
        assert exception_summary.exception_types['ConnectionError'] == 1
        assert exception_summary.exception_types['TimeoutError'] == 1
        assert len(exception_summary.recent_exceptions) == 4
        
        print(f"    ✓ 记录了 {exception_summary.total_exceptions} 个异常")
        print(f"    ✓ ValueError: {exception_summary.exception_types['ValueError']} 次")
        print(f"    ✓ ConnectionError: {exception_summary.exception_types['ConnectionError']} 次")
        print(f"    ✓ TimeoutError: {exception_summary.exception_types['TimeoutError']} 次")
    
    async def test_performance_decorators(self):
        """测试性能监控装饰器"""
        print("  测试性能监控装饰器...")
        
        @monitor_performance(OperationType.SEARCH, SearchMode.SEMANTIC)
        async def mock_search_function(query: str):
            await asyncio.sleep(0.1)  # 模拟处理时间
            return [f"result_{i}" for i in range(5)]
        
        @monitor_performance(OperationType.RERANKING)
        async def mock_reranking_function(results):
            await asyncio.sleep(0.05)  # 模拟重排序时间
            if len(results) > 3:
                return sorted(results, reverse=True)
            else:
                raise ValueError("结果太少，无法重排序")
        
        # 测试成功的搜索
        results = await mock_search_function("test query")
        assert len(results) == 5
        
        # 测试成功的重排序
        reranked = await mock_reranking_function(results)
        assert len(reranked) == 5
        
        # 测试失败的重排序
        try:
            await mock_reranking_function(["a", "b"])
            assert False, "应该抛出异常"
        except ValueError:
            pass  # 预期的异常
        
        # 验证装饰器记录了性能数据
        report = get_performance_report(time_range_minutes=1)
        assert report.response_time_stats.total_queries > 0
        
        print("    ✓ 装饰器正确记录了性能数据")
    
    async def test_concurrent_monitoring(self):
        """测试并发监控"""
        print("  测试并发监控...")
        
        async def concurrent_operation(operation_id: int):
            query_id = f"concurrent-{operation_id}"
            metric_key = start_performance_monitoring(
                query_id=query_id,
                operation_type=OperationType.SEARCH,
                search_mode=SearchMode.SEMANTIC
            )
            
            # 模拟并发处理
            await asyncio.sleep(random.uniform(0.05, 0.2))
            
            complete_performance_monitoring(
                metric_key=metric_key,
                success=True,
                result_count=random.randint(1, 10)
            )
        
        # 启动20个并发操作
        tasks = [concurrent_operation(i) for i in range(20)]
        await asyncio.gather(*tasks)
        
        # 验证并发监控结果
        report = get_performance_report(time_range_minutes=1)
        assert report.response_time_stats.total_queries >= 20
        
        print(f"    ✓ 并发处理了 {report.response_time_stats.total_queries} 个操作")
    
    def print_test_summary(self):
        """打印测试摘要"""
        print("\n" + "=" * 60)
        print("测试摘要")
        print("=" * 60)
        
        passed = sum(1 for _, status, _ in self.test_results if status == "PASSED")
        failed = sum(1 for _, status, _ in self.test_results if status == "FAILED")
        total = len(self.test_results)
        
        print(f"总测试数: {total}")
        print(f"通过: {passed}")
        print(f"失败: {failed}")
        print(f"成功率: {passed/total*100:.1f}%")
        
        if failed > 0:
            print("\n失败的测试:")
            for name, status, error in self.test_results:
                if status == "FAILED":
                    print(f"  ❌ {name}: {error}")
        
        # 打印最终性能报告
        final_report = get_performance_report(time_range_minutes=10)
        print(f"\n最终性能统计:")
        print(f"  总查询数: {final_report.response_time_stats.total_queries}")
        print(f"  平均响应时间: {final_report.response_time_stats.average_ms:.2f}ms")
        print(f"  缓存命中率: {final_report.cache_stats.hit_rate:.3f}")
        print(f"  重排序成功率: {final_report.reranking_stats.success_rate:.3f}")
        print(f"  系统稳定性评分: {final_report.system_stability.stability_score:.1f}/100")
        print(f"  异常总数: {final_report.exception_summary.total_exceptions}")
        
        print("\n" + "=" * 60)


async def main():
    """主函数"""
    test_runner = PerformanceMonitoringTest()
    await test_runner.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())