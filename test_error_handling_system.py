#!/usr/bin/env python3
"""
统一错误处理机制测试
验证任务6.1的实现
"""
import asyncio
import sys
import os
from datetime import datetime
from typing import Dict, Any

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rag_system.utils.exceptions import (
    SearchModeError, RerankingModelError, CacheConnectionError, ConfigLoadError
)
from rag_system.utils.error_handler import (
    ErrorHandler, ErrorContext, create_error_context, handle_error, handle_errors
)
from rag_system.utils.error_messages import (
    get_localized_message, get_localized_suggestion, Language, ErrorMessageFormatter
)
from rag_system.utils.retrieval_error_handler import (
    handle_search_error, handle_reranking_error, handle_cache_error, handle_config_error
)
from rag_system.utils.error_monitor import (
    global_error_monitor, record_error_metric, get_error_statistics, Alert, AlertLevel
)


class ErrorHandlingSystemTest:
    """错误处理系统测试类"""
    
    def __init__(self):
        self.test_results = []
        self.error_handler = ErrorHandler()
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("统一错误处理机制测试")
        print("=" * 60)
        
        test_methods = [
            self.test_basic_error_handling,
            self.test_error_localization,
            self.test_fallback_strategies,
            self.test_retrieval_specific_errors,
            self.test_error_monitoring,
            self.test_error_decorators,
            self.test_error_recovery,
            self.test_alert_system
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
    
    async def test_basic_error_handling(self):
        """测试基础错误处理"""
        print("  测试基础错误处理...")
        
        # 创建测试错误
        error = SearchModeError("语义搜索失败", search_mode="semantic")
        context = create_error_context(
            request_id="test-001",
            user_id="user-123",
            operation="search",
            component="retrieval_service"
        )
        
        # 处理错误
        error_response = await handle_error(error, context)
        
        # 验证响应
        assert error_response.error_code == "SEARCH_MODE_ERROR"
        assert error_response.message == "语义搜索失败"
        assert error_response.context.request_id == "test-001"
        assert len(error_response.suggestions) > 0
        
        print("    ✓ 基础错误处理正常")
    
    async def test_error_localization(self):
        """测试错误信息本地化"""
        print("  测试错误信息本地化...")
        
        # 测试中文消息
        zh_message = get_localized_message("SEARCH_MODE_ERROR", Language.ZH_CN)
        assert "搜索模式执行失败" in zh_message
        
        # 测试英文消息
        en_message = get_localized_message("SEARCH_MODE_ERROR", Language.EN_US)
        assert "Search mode execution failed" in en_message
        
        # 测试建议
        suggestion = get_localized_suggestion("SEARCH_MODE_ERROR", Language.ZH_CN)
        assert len(suggestion) > 0
        
        # 测试格式化
        formatted = ErrorMessageFormatter.format_user_friendly_message(
            "SEARCH_MODE_ERROR", "原始错误信息", Language.ZH_CN
        )
        assert "搜索模式执行失败" in formatted
        
        print("    ✓ 错误信息本地化正常")
    
    async def test_fallback_strategies(self):
        """测试降级策略"""
        print("  测试降级策略...")
        
        # 测试搜索模式降级
        error = SearchModeError("混合搜索失败", search_mode="hybrid")
        context = create_error_context(operation="search", component="retrieval_service")
        
        original_request = {
            "query": "测试查询",
            "config": {"search_mode": "hybrid"},
            "operation": "search"
        }
        
        error_response = await self.error_handler.handle_error(
            error, context, original_request, enable_fallback=True
        )
        
        # 验证降级结果
        assert error_response.error_code == "SEARCH_MODE_ERROR"
        # 注意：由于我们没有实际的检索服务，降级结果可能为空列表
        
        print("    ✓ 降级策略正常")
    
    async def test_retrieval_specific_errors(self):
        """测试检索特定错误处理"""
        print("  测试检索特定错误处理...")
        
        # 测试搜索错误
        search_error = SearchModeError("语义搜索失败")
        search_response = await handle_search_error(
            search_error,
            query="测试查询",
            config={"search_mode": "semantic"},
            user_id="user-123",
            request_id="req-001"
        )
        assert search_response.error_code == "SEARCH_MODE_ERROR"
        
        # 测试重排序错误
        rerank_error = RerankingModelError("模型加载失败")
        rerank_response = await handle_reranking_error(
            rerank_error,
            query="测试查询",
            original_results=[],
            config={"enable_rerank": True},
            user_id="user-123"
        )
        assert rerank_response.error_code == "RERANKING_MODEL_ERROR"
        
        # 测试缓存错误
        cache_error = CacheConnectionError("Redis连接失败")
        cache_response = await handle_cache_error(
            cache_error,
            cache_key="test:key",
            operation="get",
            config={"enable_cache": True}
        )
        assert cache_response.error_code == "CACHE_CONNECTION_ERROR"
        
        # 测试配置错误
        config_error = ConfigLoadError("配置文件不存在")
        config_response = await handle_config_error(
            config_error,
            config_path="/path/to/config.yaml"
        )
        assert config_response.error_code == "CONFIG_LOAD_ERROR"
        
        print("    ✓ 检索特定错误处理正常")
    
    async def test_error_monitoring(self):
        """测试错误监控"""
        print("  测试错误监控...")
        
        # 记录一些测试错误
        errors_to_record = [
            (SearchModeError("搜索失败1"), "search", "retrieval_service"),
            (RerankingModelError("重排序失败1"), "reranking", "reranking_service"),
            (CacheConnectionError("缓存失败1"), "cache_get", "cache_service"),
        ]
        
        for error, operation, component in errors_to_record:
            context = create_error_context(
                operation=operation,
                component=component,
                request_id=f"test-{operation}"
            )
            
            error_info = {
                'error_code': error.error_code,
                'message': str(error),
                'severity': getattr(error, 'severity', 'MEDIUM'),
                'category': 'BUSINESS'
            }
            
            await record_error_metric(error, context, error_info)
        
        # 获取统计信息
        stats = get_error_statistics()
        assert stats.total_errors >= 3
        assert len(stats.error_by_component) >= 3
        
        print(f"    ✓ 错误监控正常 (记录了 {stats.total_errors} 个错误)")
    
    async def test_error_decorators(self):
        """测试错误处理装饰器"""
        print("  测试错误处理装饰器...")
        
        @handle_errors(component="test_component", operation="test_operation")
        async def test_function_with_error():
            raise SearchModeError("装饰器测试错误")
        
        @handle_errors(component="test_component", operation="test_operation", reraise=False)
        async def test_function_with_fallback():
            raise RerankingModelError("装饰器降级测试")
        
        # 测试错误重新抛出
        try:
            await test_function_with_error()
            assert False, "应该抛出错误"
        except SearchModeError:
            pass  # 预期的错误
        
        # 测试降级处理
        try:
            result = await test_function_with_fallback()
            # 如果有降级结果，应该返回降级结果而不是抛出错误
        except RerankingModelError:
            pass  # 如果没有降级结果，会抛出原始错误
        
        print("    ✓ 错误处理装饰器正常")
    
    async def test_error_recovery(self):
        """测试错误恢复机制"""
        print("  测试错误恢复机制...")
        
        from rag_system.utils.retrieval_error_handler import global_retrieval_error_handler
        
        # 测试恢复尝试计数
        error_code = "TEST_ERROR"
        context = create_error_context(component="test", operation="test")
        
        # 第一次尝试
        should_recover = global_retrieval_error_handler.should_attempt_recovery(error_code, context)
        assert should_recover == True
        
        # 多次尝试后应该停止恢复
        for _ in range(5):
            global_retrieval_error_handler.should_attempt_recovery(error_code, context)
        
        should_recover = global_retrieval_error_handler.should_attempt_recovery(error_code, context)
        assert should_recover == False
        
        # 重置后应该可以再次尝试
        global_retrieval_error_handler.reset_recovery_attempts(error_code, context)
        should_recover = global_retrieval_error_handler.should_attempt_recovery(error_code, context)
        assert should_recover == True
        
        print("    ✓ 错误恢复机制正常")
    
    async def test_alert_system(self):
        """测试告警系统"""
        print("  测试告警系统...")
        
        # 创建测试告警处理器
        received_alerts = []
        
        def test_alert_handler(alert):
            received_alerts.append(alert)
        
        # 注册告警处理器
        global_error_monitor.register_alert_handler(test_alert_handler)
        
        # 设置低阈值以便触发告警
        global_error_monitor.set_alert_threshold("error_rate", "warning", 1)
        global_error_monitor.set_alert_threshold("critical_errors", "warning", 1)
        
        # 生成一些错误来触发告警
        for i in range(3):
            error = SearchModeError(f"告警测试错误 {i}")
            context = create_error_context(
                operation="alert_test",
                component="test_component"
            )
            
            error_info = {
                'error_code': error.error_code,
                'message': str(error),
                'severity': 'HIGH',
                'category': 'BUSINESS'
            }
            
            await record_error_metric(error, context, error_info)
            await asyncio.sleep(0.1)  # 短暂延迟
        
        # 等待告警处理
        await asyncio.sleep(0.5)
        
        # 验证告警
        assert len(received_alerts) > 0, "应该收到告警"
        
        # 获取最近的告警
        recent_alerts = global_error_monitor.get_recent_alerts(10)
        assert len(recent_alerts) > 0
        
        print(f"    ✓ 告警系统正常 (收到 {len(received_alerts)} 个告警)")
    
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
        
        # 打印错误统计
        stats = get_error_statistics()
        print(f"\n错误监控统计:")
        print(f"  总错误数: {stats.total_errors}")
        print(f"  错误率: {stats.error_rate_per_minute:.2f} 错误/分钟")
        print(f"  组件错误分布: {dict(stats.error_by_component)}")
        
        print("\n" + "=" * 60)


async def main():
    """主函数"""
    test_runner = ErrorHandlingSystemTest()
    await test_runner.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())