#!/usr/bin/env python3
"""
模型健康检查器演示脚本
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import json
from datetime import datetime

from rag_system.utils.health_checker import ModelHealthChecker, ModelHealthCheckConfig
from rag_system.llm.base import LLMConfig
from rag_system.embeddings.base import EmbeddingConfig


async def demo_model_health_checker():
    """演示模型健康检查器功能"""
    print("=== 模型健康检查器演示 ===\n")
    
    # 1. 创建健康检查配置
    print("1. 创建健康检查配置")
    config = ModelHealthCheckConfig(
        check_interval=60,  # 1分钟检查一次
        timeout=10,         # 10秒超时
        max_consecutive_failures=3,
        test_prompt="Hello, this is a health check.",
        test_text="This is a test document for embedding.",
        enable_startup_check=True,
        enable_periodic_check=False  # 演示时禁用定期检查
    )
    print(f"   检查间隔: {config.check_interval}秒")
    print(f"   超时时间: {config.timeout}秒")
    print(f"   测试提示: {config.test_prompt}")
    print()
    
    # 2. 创建健康检查器
    print("2. 创建模型健康检查器")
    checker = ModelHealthChecker(config)
    print("   健康检查器已创建")
    print()
    
    # 3. 配置要检查的模型
    print("3. 配置要检查的模型")
    llm_configs = [
        LLMConfig(
            provider="mock",
            model="mock-gpt-4",
            api_key="mock-key-1"
        ),
        LLMConfig(
            provider="mock", 
            model="mock-claude-3",
            api_key="mock-key-2"
        )
    ]
    
    embedding_configs = [
        EmbeddingConfig(
            provider="mock",
            model="mock-text-embedding",
            api_key="mock-key-3"
        )
    ]
    
    print(f"   配置了 {len(llm_configs)} 个LLM模型")
    print(f"   配置了 {len(embedding_configs)} 个嵌入模型")
    print()
    
    # 4. 执行启动时健康检查
    print("4. 执行启动时健康检查")
    try:
        startup_success = await checker.startup_health_check(llm_configs, embedding_configs)
        print(f"   启动时健康检查结果: {'成功' if startup_success else '失败'}")
    except Exception as e:
        print(f"   启动时健康检查异常: {str(e)}")
    print()
    
    # 5. 执行完整的模型健康检查
    print("5. 执行完整的模型健康检查")
    try:
        results = await checker.check_all_models(llm_configs, embedding_configs)
        print(f"   检查了 {len(results)} 个模型")
        
        for model_key, status in results.items():
            health_status = "健康" if status.is_healthy else "不健康"
            print(f"   - {model_key}: {health_status}")
            if status.response_time:
                print(f"     响应时间: {status.response_time:.3f}秒")
            if status.error_message:
                print(f"     错误信息: {status.error_message}")
    except Exception as e:
        print(f"   健康检查异常: {str(e)}")
    print()
    
    # 6. 查询特定模型状态
    print("6. 查询特定模型状态")
    mock_llm_status = checker.get_model_status("mock", "mock-gpt-4", "llm")
    if mock_llm_status:
        print(f"   mock-gpt-4 状态: {'健康' if mock_llm_status.is_healthy else '不健康'}")
        print(f"   总检查次数: {mock_llm_status.total_checks}")
        print(f"   成功率: {mock_llm_status.success_rate:.2%}")
        print(f"   连续失败次数: {mock_llm_status.consecutive_failures}")
    else:
        print("   未找到 mock-gpt-4 的状态信息")
    print()
    
    # 7. 获取提供商状态
    print("7. 获取提供商状态")
    mock_provider_status = checker.get_provider_status("mock")
    print(f"   Mock提供商有 {len(mock_provider_status)} 个模型")
    for model_key, status in mock_provider_status.items():
        print(f"   - {status.model_name} ({status.model_type}): {'健康' if status.is_healthy else '不健康'}")
    print()
    
    # 8. 获取不健康的模型
    print("8. 获取不健康的模型")
    unhealthy_models = checker.get_unhealthy_models()
    if unhealthy_models:
        print(f"   发现 {len(unhealthy_models)} 个不健康的模型:")
        for model_key, status in unhealthy_models.items():
            print(f"   - {model_key}: {status.error_message}")
    else:
        print("   所有模型都健康")
    print()
    
    # 9. 获取整体健康状态
    print("9. 获取整体健康状态")
    overall_status = checker.get_overall_health_status()
    print(f"   整体健康状态: {overall_status.value}")
    print()
    
    # 10. 生成健康检查报告
    print("10. 生成健康检查报告")
    report = checker.generate_health_report()
    print("   健康检查报告:")
    print(f"   - 整体状态: {report['overall_status']}")
    print(f"   - 总模型数: {report['total_models']}")
    print(f"   - 健康模型数: {report['healthy_models']}")
    print(f"   - 不健康模型数: {report['unhealthy_models']}")
    print(f"   - 最后检查时间: {report['last_check']}")
    
    if report['alerts']:
        print(f"   - 告警数量: {len(report['alerts'])}")
        for alert in report['alerts']:
            print(f"     * [{alert['level'].upper()}] {alert['message']}")
    else:
        print("   - 无告警")
    print()
    
    # 11. 演示定期健康检查（短时间）
    print("11. 演示定期健康检查（运行10秒）")
    try:
        # 临时启用定期检查
        checker.config.enable_periodic_check = True
        checker.config.check_interval = 3  # 3秒检查一次
        
        await checker.start_periodic_check(llm_configs, embedding_configs)
        print("   定期健康检查已启动，运行10秒...")
        
        # 运行10秒
        await asyncio.sleep(10)
        
        await checker.stop_periodic_check()
        print("   定期健康检查已停止")
    except Exception as e:
        print(f"   定期健康检查异常: {str(e)}")
    print()
    
    # 12. 清理资源
    print("12. 清理资源")
    checker.cleanup()
    print("   资源已清理")
    print()
    
    print("=== 演示完成 ===")


async def demo_health_report_json():
    """演示生成JSON格式的健康报告"""
    print("\n=== JSON健康报告演示 ===\n")
    
    # 创建检查器并添加一些模拟状态
    checker = ModelHealthChecker()
    
    # 模拟一些健康检查结果
    llm_configs = [
        LLMConfig(provider="mock", model="healthy-model", api_key="key1"),
        LLMConfig(provider="mock", model="unhealthy-model", api_key="key2")
    ]
    
    try:
        # 执行检查
        await checker.check_all_models(llm_configs, [])
        
        # 手动设置一个模型为不健康状态（用于演示）
        unhealthy_key = "mock:llm:unhealthy-model"
        if unhealthy_key in checker.model_status:
            checker.model_status[unhealthy_key].update_failure("模拟连接失败")
        
        # 生成报告
        report = checker.generate_health_report()
        
        # 输出JSON格式报告
        print("健康检查报告 (JSON格式):")
        print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
        
    except Exception as e:
        print(f"生成报告时出错: {str(e)}")
    
    print("\n=== JSON报告演示完成 ===")


if __name__ == "__main__":
    # 运行演示
    asyncio.run(demo_model_health_checker())
    asyncio.run(demo_health_report_json())