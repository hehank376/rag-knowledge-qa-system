#!/usr/bin/env python3
"""
监控和健康检查功能演示脚本
演示任务9.2：日志和监控功能的使用
"""
import asyncio
import time
import json
from fastapi import FastAPI
from fastapi.testclient import TestClient

from rag_system.api.monitoring_api import router
from rag_system.utils.monitoring import (
    MetricsCollector, HealthChecker, PerformanceMonitor,
    performance_monitor_middleware
)


def create_demo_app():
    """创建演示应用"""
    app = FastAPI(title="RAG System Monitoring Demo")
    
    # 创建指标收集器
    metrics_collector = MetricsCollector()
    
    # 添加性能监控中间件
    app.add_middleware(performance_monitor_middleware(metrics_collector))
    
    # 添加监控API路由
    app.include_router(router)
    
    # 添加一些测试端点
    @app.get("/test/fast")
    async def fast_endpoint():
        return {"message": "快速响应", "response_time": "< 100ms"}
    
    @app.get("/test/slow")
    async def slow_endpoint():
        await asyncio.sleep(1)  # 模拟慢响应
        return {"message": "慢响应", "response_time": "> 1s"}
    
    @app.get("/test/error")
    async def error_endpoint():
        raise Exception("测试错误")
    
    return app


def demo_metrics_collector():
    """演示指标收集器功能"""
    print("=" * 60)
    print("指标收集器演示")
    print("=" * 60)
    
    collector = MetricsCollector()
    
    # 模拟一些请求
    print("\n1. 模拟请求记录")
    print("-" * 30)
    
    services = ["api/documents", "api/qa", "api/config"]
    
    for i in range(20):
        service = services[i % len(services)]
        response_time = 0.1 + (i % 5) * 0.2  # 0.1-1.1秒
        success = i % 10 != 0  # 10%失败率
        error_type = "TimeoutError" if not success else None
        
        collector.record_request(service, response_time, success, error_type)
        print(f"记录请求: {service}, {response_time:.2f}s, {'成功' if success else '失败'}")
    
    # 获取系统指标
    print("\n2. 系统性能指标")
    print("-" * 30)
    
    system_metrics = collector.get_system_metrics()
    print(f"CPU使用率: {system_metrics.cpu_usage:.1f}%")
    print(f"内存使用率: {system_metrics.memory_usage:.1f}%")
    print(f"磁盘使用率: {system_metrics.disk_usage:.1f}%")
    print(f"请求数量: {system_metrics.request_count}")
    print(f"错误数量: {system_metrics.error_count}")
    print(f"平均响应时间: {system_metrics.avg_response_time:.3f}s")
    
    # 获取服务指标
    print("\n3. 服务指标")
    print("-" * 30)
    
    for service in services:
        metrics = collector.get_service_metrics(service)
        print(f"\n服务: {service}")
        print(f"  总请求数: {metrics.total_requests}")
        print(f"  成功请求: {metrics.successful_requests}")
        print(f"  失败请求: {metrics.failed_requests}")
        print(f"  成功率: {metrics.successful_requests/metrics.total_requests:.1%}")
        print(f"  平均响应时间: {metrics.avg_response_time:.3f}s")
        print(f"  最小响应时间: {metrics.min_response_time:.3f}s")
        print(f"  最大响应时间: {metrics.max_response_time:.3f}s")


async def demo_health_checker():
    """演示健康检查器功能"""
    print("\n" + "=" * 60)
    print("健康检查器演示")
    print("=" * 60)
    
    health_checker = HealthChecker()
    
    # 注册一些测试健康检查
    def healthy_service():
        return {"status": "healthy", "details": {"connection": "ok"}}
    
    def degraded_service():
        return {"status": "degraded", "details": {"connection": "slow", "latency": "high"}}
    
    def unhealthy_service():
        raise Exception("服务不可用")
    
    async def async_healthy_service():
        await asyncio.sleep(0.1)  # 模拟异步检查
        return {"status": "healthy", "details": {"async_check": "passed"}}
    
    health_checker.register_check("service_a", healthy_service)
    health_checker.register_check("service_b", degraded_service)
    health_checker.register_check("service_c", unhealthy_service)
    health_checker.register_check("service_d", async_healthy_service)
    
    # 执行健康检查
    print("\n1. 单个服务健康检查")
    print("-" * 30)
    
    for service in ["service_a", "service_b", "service_c", "service_d"]:
        health_status = await health_checker.check_health(service)
        print(f"\n服务: {service}")
        print(f"  状态: {health_status.status}")
        print(f"  响应时间: {health_status.response_time:.3f}s" if health_status.response_time else "  响应时间: N/A")
        print(f"  错误信息: {health_status.error_message}" if health_status.error_message else "  错误信息: 无")
        print(f"  详情: {health_status.details}" if health_status.details else "  详情: 无")
    
    # 执行所有健康检查
    print("\n2. 所有服务健康检查")
    print("-" * 30)
    
    all_health = await health_checker.check_all_health()
    overall_status = health_checker.get_overall_status(all_health)
    
    print(f"整体健康状态: {overall_status}")
    print(f"健康服务数: {len([h for h in all_health.values() if h.status == 'healthy'])}")
    print(f"降级服务数: {len([h for h in all_health.values() if h.status == 'degraded'])}")
    print(f"不健康服务数: {len([h for h in all_health.values() if h.status == 'unhealthy'])}")


def demo_performance_monitor():
    """演示性能监控器功能"""
    print("\n" + "=" * 60)
    print("性能监控器演示")
    print("=" * 60)
    
    collector = MetricsCollector()
    monitor = PerformanceMonitor(collector)
    
    # 模拟一些高负载情况
    print("\n1. 模拟高负载请求")
    print("-" * 30)
    
    for i in range(50):
        # 模拟高响应时间和错误
        response_time = 2.0 + (i % 10) * 0.5  # 2-6.5秒
        success = i % 3 != 0  # 33%失败率
        
        collector.record_request("high_load_service", response_time, success, "HighLoadError")
    
    # 获取系统指标并检查阈值
    print("\n2. 性能阈值检查")
    print("-" * 30)
    
    # 设置较低的阈值以触发告警
    monitor.set_threshold('avg_response_time', 1.0)  # 1秒
    monitor.set_threshold('error_rate', 0.1)  # 10%
    monitor.set_threshold('cpu_usage', 50.0)  # 50%
    
    system_metrics = collector.get_system_metrics()
    alerts = monitor.check_thresholds(system_metrics)
    
    print(f"检查到 {len(alerts)} 个告警:")
    for alert in alerts:
        print(f"  - {alert['type']}: {alert['message']} (严重程度: {alert['severity']})")
    
    # 获取最近告警
    print("\n3. 最近告警历史")
    print("-" * 30)
    
    recent_alerts = monitor.get_recent_alerts(60)
    print(f"最近60分钟内的告警数: {len(recent_alerts)}")
    
    for alert in recent_alerts[-5:]:  # 显示最近5个
        print(f"  - {alert['timestamp'].strftime('%H:%M:%S')}: {alert['message']}")


def demo_monitoring_api():
    """演示监控API功能"""
    print("\n" + "=" * 60)
    print("监控API演示")
    print("=" * 60)
    
    # 创建测试应用
    app = create_demo_app()
    client = TestClient(app)
    
    # 生成一些测试流量
    print("\n1. 生成测试流量")
    print("-" * 30)
    
    endpoints = ["/test/fast", "/test/slow", "/test/error"]
    
    for i in range(15):
        endpoint = endpoints[i % len(endpoints)]
        try:
            response = client.get(endpoint)
            print(f"请求 {endpoint}: {response.status_code}")
        except Exception as e:
            print(f"请求 {endpoint}: 异常 - {type(e).__name__}")
    
    # 测试健康检查API
    print("\n2. 健康检查API")
    print("-" * 30)
    
    try:
        response = client.get("/monitoring/health")
        if response.status_code == 200:
            data = response.json()
            print(f"整体健康状态: {data['overall_status']}")
            print(f"检查的服务数: {len(data['services'])}")
            
            for service, status in data['services'].items():
                print(f"  - {service}: {status['status']}")
        else:
            print(f"健康检查失败: {response.status_code}")
    except Exception as e:
        print(f"健康检查API调用失败: {e}")
    
    # 测试指标API
    print("\n3. 性能指标API")
    print("-" * 30)
    
    try:
        response = client.get("/monitoring/metrics")
        if response.status_code == 200:
            data = response.json()
            system_metrics = data['system_metrics']
            
            print(f"CPU使用率: {system_metrics['cpu_usage']:.1f}%")
            print(f"内存使用率: {system_metrics['memory_usage']:.1f}%")
            print(f"请求数量: {system_metrics['request_count']}")
            print(f"错误数量: {system_metrics['error_count']}")
            print(f"平均响应时间: {system_metrics['avg_response_time']:.3f}s")
            
            print(f"\n服务指标数: {len(data['service_metrics'])}")
            for service, metrics in data['service_metrics'].items():
                if metrics['total_requests'] > 0:
                    print(f"  - {service}: {metrics['total_requests']} 请求, "
                          f"{metrics['avg_response_time']:.3f}s 平均响应时间")
        else:
            print(f"指标获取失败: {response.status_code}")
    except Exception as e:
        print(f"指标API调用失败: {e}")
    
    # 测试告警API
    print("\n4. 告警API")
    print("-" * 30)
    
    try:
        response = client.get("/monitoring/alerts")
        if response.status_code == 200:
            data = response.json()
            print(f"告警总数: {data['total_count']}")
            print(f"严重告警: {data['critical_count']}")
            print(f"警告告警: {data['warning_count']}")
            
            if data['alerts']:
                print("\n最近告警:")
                for alert in data['alerts'][-3:]:  # 显示最近3个
                    print(f"  - {alert.get('type', 'unknown')}: {alert.get('message', 'no message')}")
        else:
            print(f"告警获取失败: {response.status_code}")
    except Exception as e:
        print(f"告警API调用失败: {e}")
    
    # 测试系统状态概览API
    print("\n5. 系统状态概览API")
    print("-" * 30)
    
    try:
        response = client.get("/monitoring/status")
        if response.status_code == 200:
            data = response.json()
            print(f"整体健康状态: {data['overall_health']}")
            
            perf = data['system_performance']
            print(f"系统性能:")
            print(f"  - CPU: {perf['cpu_usage']:.1f}%")
            print(f"  - 内存: {perf['memory_usage']:.1f}%")
            print(f"  - 磁盘: {perf['disk_usage']:.1f}%")
            print(f"  - 平均响应时间: {perf['avg_response_time']:.3f}s")
            
            summary = data['service_summary']
            print(f"服务概览:")
            print(f"  - 总服务数: {summary['total_services']}")
            print(f"  - 健康服务数: {summary['healthy_services']}")
            print(f"  - 总请求数: {summary['total_requests']}")
            print(f"  - 错误率: {summary['error_rate']:.2%}")
            
            alerts = data['alerts_summary']
            print(f"告警概览:")
            print(f"  - 总告警数: {alerts['total_alerts']}")
            print(f"  - 严重告警数: {alerts['critical_alerts']}")
            print(f"  - 有严重告警: {'是' if alerts['has_critical'] else '否'}")
        else:
            print(f"状态概览获取失败: {response.status_code}")
    except Exception as e:
        print(f"状态概览API调用失败: {e}")


async def main():
    """主演示函数"""
    print("RAG系统监控和健康检查功能演示")
    print("=" * 80)
    
    try:
        # 1. 指标收集器演示
        demo_metrics_collector()
        
        # 2. 健康检查器演示
        await demo_health_checker()
        
        # 3. 性能监控器演示
        demo_performance_monitor()
        
        # 4. 监控API演示
        demo_monitoring_api()
        
        print("\n" + "=" * 80)
        print("监控和健康检查功能演示完成")
        print("=" * 80)
        
    except Exception as e:
        print(f"演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())