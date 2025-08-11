#!/usr/bin/env python3
"""
健康监控系统演示脚本
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import json
from datetime import datetime

from rag_system.utils.health_checker import ModelHealthChecker, ModelHealthCheckConfig
from rag_system.services.health_monitoring_service import (
    HealthMonitoringService, AlertLevel, console_alert_handler, file_alert_handler
)
from rag_system.llm.base import LLMConfig
from rag_system.embeddings.base import EmbeddingConfig


async def demo_health_monitoring_system():
    """演示健康监控系统"""
    print("=== 健康监控系统演示 ===\n")
    
    # 1. 配置模型
    print("1. 配置模型")
    llm_configs = [
        LLMConfig(provider="mock", model="healthy-llm", api_key="key1"),
        LLMConfig(provider="mock", model="unhealthy-llm", api_key="key2"),
        LLMConfig(provider="mock", model="slow-llm", api_key="key3")
    ]
    
    embedding_configs = [
        EmbeddingConfig(provider="mock", model="healthy-embedding", api_key="key4"),
        EmbeddingConfig(provider="mock", model="unhealthy-embedding", api_key="key5")
    ]
    
    print(f"   配置了 {len(llm_configs)} 个LLM模型")
    print(f"   配置了 {len(embedding_configs)} 个嵌入模型")
    print()
    
    # 2. 创建健康检查器
    print("2. 创建健康检查器")
    config = ModelHealthCheckConfig(
        check_interval=3,  # 3秒检查一次
        timeout=2,
        enable_periodic_check=True,
        max_consecutive_failures=2
    )
    health_checker = ModelHealthChecker(config)
    print("   健康检查器已创建")
    print()
    
    # 3. 创建监控服务
    print("3. 创建健康监控服务")
    
    # 创建告警处理器
    def custom_alert_handler(alert):
        print(f"   🚨 [{alert.level.value.upper()}] {alert.title}")
        print(f"      组件: {alert.component}")
        print(f"      消息: {alert.message}")
        print(f"      时间: {alert.timestamp.strftime('%H:%M:%S')}")
        print()
    
    monitoring_service = HealthMonitoringService(
        health_checker=health_checker,
        llm_configs=llm_configs,
        embedding_configs=embedding_configs,
        alert_handlers=[custom_alert_handler, console_alert_handler]
    )
    monitoring_service.monitoring_interval = 2  # 2秒监控间隔
    
    print("   监控服务已创建，配置了自定义告警处理器")
    print()
    
    # 4. 启动监控
    print("4. 启动健康监控")
    try:
        await monitoring_service.start_monitoring()
        print("   监控服务已启动")
        print()
        
        # 5. 运行监控一段时间
        print("5. 运行监控系统（15秒）...")
        print("   观察健康检查和告警生成：")
        print()
        
        await asyncio.sleep(15)
        
        # 6. 查看监控结果
        print("\n6. 监控结果分析")
        
        # 获取健康报告
        report = health_checker.generate_health_report()
        print(f"   整体状态: {report['overall_status']}")
        print(f"   总模型数: {report['total_models']}")
        print(f"   健康模型: {report['healthy_models']}")
        print(f"   不健康模型: {report['unhealthy_models']}")
        print()
        
        # 显示模型详细状态
        print("   模型详细状态:")
        for model_key, model_info in report['models'].items():
            status_icon = "✅" if model_info['is_healthy'] else "❌"
            print(f"   {status_icon} {model_key}")
            print(f"      成功率: {model_info['success_rate']:.2%}")
            print(f"      连续失败: {model_info['consecutive_failures']} 次")
            if model_info['error_message']:
                print(f"      错误: {model_info['error_message']}")
        print()
        
        # 显示活跃告警
        active_alerts = monitoring_service.get_active_alerts()
        print(f"   活跃告警数量: {len(active_alerts)}")
        for alert in active_alerts:
            level_icon = {"error": "🔴", "warning": "🟡", "info": "🔵"}.get(alert.level.value, "⚪")
            print(f"   {level_icon} {alert.title}")
            print(f"      级别: {alert.level.value}")
            print(f"      组件: {alert.component}")
        print()
        
        # 7. 演示告警解决
        print("7. 演示告警解决机制")
        print("   模拟修复部分模型...")
        
        # 这里可以模拟修复模型，但由于使用mock模型，我们直接演示解决告警
        if active_alerts:
            first_alert = active_alerts[0]
            await monitoring_service._resolve_alert(first_alert.id)
            print(f"   已解决告警: {first_alert.title}")
        
        # 等待一个监控周期
        await asyncio.sleep(3)
        
        new_active_alerts = monitoring_service.get_active_alerts()
        print(f"   解决后活跃告警数量: {len(new_active_alerts)}")
        print()
        
        # 8. 显示告警历史
        print("8. 告警历史")
        alert_history = monitoring_service.get_alert_history(limit=5)
        print(f"   历史告警数量: {len(alert_history)}")
        for alert in alert_history[-3:]:  # 显示最近3个
            print(f"   - {alert.title} ({alert.level.value})")
            print(f"     时间: {alert.timestamp.strftime('%H:%M:%S')}")
            if alert.resolved:
                print(f"     已解决: {alert.resolved_at.strftime('%H:%M:%S')}")
        print()
        
        # 9. 生成JSON报告
        print("9. 生成详细JSON报告")
        json_report = health_checker.generate_health_report()
        
        # 保存到文件
        report_file = "health_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(json_report, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"   报告已保存到: {report_file}")
        print(f"   报告大小: {len(json.dumps(json_report))} 字符")
        print()
        
        # 10. 演示API集成
        print("10. API集成演示")
        print("    健康检查API端点:")
        print("    - GET /health/ - 获取系统整体健康状态")
        print("    - GET /health/models - 获取所有模型健康状态")
        print("    - GET /health/providers/{provider} - 获取特定提供商状态")
        print("    - GET /health/alerts - 获取健康告警")
        print("    - GET /health/status - 获取简化健康状态")
        print("    - POST /health/check - 手动触发健康检查")
        print()
        
        # 模拟API调用结果
        print("    模拟API调用结果:")
        print(f"    GET /health/status -> {{\"status\": \"{report['overall_status']}\", \"code\": 200}}")
        print(f"    GET /health/alerts -> {{\"total_alerts\": {len(report['alerts'])}}}")
        print()
        
    finally:
        # 11. 清理资源
        print("11. 清理资源")
        await monitoring_service.stop_monitoring()
        health_checker.cleanup()
        print("   监控服务已停止")
        print("   资源已清理")
        print()
    
    print("=== 演示完成 ===")


async def demo_alert_handlers():
    """演示告警处理器"""
    print("\n=== 告警处理器演示 ===\n")
    
    from rag_system.services.health_monitoring_service import Alert
    
    # 创建测试告警
    test_alert = Alert(
        id="demo_alert",
        level=AlertLevel.ERROR,
        title="演示告警",
        message="这是一个演示用的告警消息",
        component="demo_component",
        timestamp=datetime.now(),
        metadata={"demo": True, "severity": "high"}
    )
    
    print("1. 控制台告警处理器")
    console_alert_handler(test_alert)
    
    print("\n2. 文件告警处理器")
    log_file = "demo_alerts.log"
    file_alert_handler(test_alert, log_file)
    print(f"   告警已写入文件: {log_file}")
    
    # 读取并显示文件内容
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            print(f"   文件内容: {content.strip()}")
    except Exception as e:
        print(f"   读取文件失败: {str(e)}")
    
    print("\n3. 自定义告警处理器示例")
    
    def webhook_simulator(alert):
        """模拟Webhook告警处理器"""
        payload = {
            "alert_id": alert.id,
            "level": alert.level.value,
            "title": alert.title,
            "message": alert.message,
            "component": alert.component,
            "timestamp": alert.timestamp.isoformat(),
            "metadata": alert.metadata
        }
        print(f"   📡 Webhook调用模拟:")
        print(f"   POST /webhook/alerts")
        print(f"   Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    
    webhook_simulator(test_alert)
    
    print("\n=== 告警处理器演示完成 ===")


if __name__ == "__main__":
    # 运行演示
    asyncio.run(demo_health_monitoring_system())
    asyncio.run(demo_alert_handlers())