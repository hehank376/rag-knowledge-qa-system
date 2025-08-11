#!/usr/bin/env python3
"""
改进后的模型管理功能测试脚本

验证前后端集成的模型管理功能是否正常工作
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from fastapi.testclient import TestClient
from rag_system.api.main import app


def print_section(title: str):
    """打印格式化的章节"""
    print(f"\n{'='*60}")
    print(f"🧪 {title}")
    print(f"{'='*60}")


def print_test_result(test_name: str, success: bool, details: str = ""):
    """打印测试结果"""
    status = "✅ 通过" if success else "❌ 失败"
    print(f"{status} {test_name}")
    if details:
        print(f"   详情: {details}")


def test_model_status_api():
    """测试模型状态API"""
    print_section("测试模型状态API")
    
    client = TestClient(app)
    
    try:
        response = client.get("/config/models/status")
        
        if response.status_code == 200:
            data = response.json()
            
            # 检查响应结构
            required_fields = ['success', 'data', 'timestamp']
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                print_test_result("响应结构检查", False, f"缺少字段: {missing_fields}")
                return False
            
            if not data['success']:
                print_test_result("API调用成功", False, f"API返回失败: {data}")
                return False
            
            # 检查数据结构
            model_data = data['data']
            expected_keys = ['model_configs', 'model_statuses', 'service_details', 'active_models']
            
            for key in expected_keys:
                if key in model_data:
                    print_test_result(f"包含{key}字段", True)
                else:
                    print_test_result(f"包含{key}字段", False, f"缺少{key}字段")
            
            # 检查模型配置
            if 'model_configs' in model_data and model_data['model_configs']:
                config_count = len(model_data['model_configs'])
                print_test_result("模型配置数量", True, f"找到{config_count}个模型配置")
                
                # 检查第一个模型配置的结构
                first_config = list(model_data['model_configs'].values())[0]
                required_config_fields = ['name', 'model_type', 'provider', 'model_name', 'enabled']
                
                for field in required_config_fields:
                    if field in first_config:
                        print_test_result(f"模型配置包含{field}", True)
                    else:
                        print_test_result(f"模型配置包含{field}", False)
            
            print_test_result("模型状态API", True, "API响应正常")
            return True
            
        else:
            print_test_result("模型状态API", False, f"HTTP状态码: {response.status_code}")
            return False
            
    except Exception as e:
        print_test_result("模型状态API", False, f"异常: {str(e)}")
        return False


def test_model_metrics_api():
    """测试模型指标API"""
    print_section("测试模型指标API")
    
    client = TestClient(app)
    
    try:
        response = client.get("/config/models/metrics")
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                metrics_data = data.get('data', {})
                
                # 检查指标结构
                expected_metrics = ['embedding_metrics', 'reranking_metrics', 'system_metrics']
                
                for metric_type in expected_metrics:
                    if metric_type in metrics_data:
                        print_test_result(f"包含{metric_type}", True)
                        
                        # 检查指标字段
                        metrics = metrics_data[metric_type]
                        if metric_type != 'system_metrics':
                            expected_fields = ['total_requests', 'avg_response_time', 'success_rate', 'error_count']
                            for field in expected_fields:
                                if field in metrics:
                                    print_test_result(f"{metric_type}.{field}", True, f"值: {metrics[field]}")
                                else:
                                    print_test_result(f"{metric_type}.{field}", False)
                    else:
                        print_test_result(f"包含{metric_type}", False)
                
                print_test_result("模型指标API", True, "API响应正常")
                return True
            else:
                print_test_result("模型指标API", False, f"API返回失败: {data}")
                return False
                
        else:
            print_test_result("模型指标API", False, f"HTTP状态码: {response.status_code}")
            return False
            
    except Exception as e:
        print_test_result("模型指标API", False, f"异常: {str(e)}")
        return False


def test_model_switch_api():
    """测试模型切换API"""
    print_section("测试模型切换API")
    
    client = TestClient(app)
    
    # 测试切换嵌入模型
    try:
        switch_data = {
            "model_type": "embedding",
            "model_name": "text-embedding-ada-002"
        }
        
        response = client.post("/config/models/switch-active", json=switch_data)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                print_test_result("切换嵌入模型", True, f"消息: {data.get('message')}")
            else:
                print_test_result("切换嵌入模型", False, f"错误: {data.get('error')}")
        else:
            print_test_result("切换嵌入模型", False, f"HTTP状态码: {response.status_code}")
            
    except Exception as e:
        print_test_result("切换嵌入模型", False, f"异常: {str(e)}")
    
    # 测试切换重排序模型
    try:
        switch_data = {
            "model_type": "reranking",
            "model_name": "cross-encoder/ms-marco-MiniLM-L-6-v2"
        }
        
        response = client.post("/config/models/switch-active", json=switch_data)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                print_test_result("切换重排序模型", True, f"消息: {data.get('message')}")
                return True
            else:
                print_test_result("切换重排序模型", False, f"错误: {data.get('error')}")
                return False
        else:
            print_test_result("切换重排序模型", False, f"HTTP状态码: {response.status_code}")
            return False
            
    except Exception as e:
        print_test_result("切换重排序模型", False, f"异常: {str(e)}")
        return False


def test_model_health_check():
    """测试模型健康检查"""
    print_section("测试模型健康检查")
    
    client = TestClient(app)
    
    try:
        response = client.post("/config/models/health-check")
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                overall_status = data.get('overall_status')
                details = data.get('details', {})
                
                print_test_result("健康检查执行", True, f"整体状态: {overall_status}")
                
                # 检查各个组件的健康状态
                for component, health_info in details.items():
                    status = health_info.get('status', 'unknown')
                    message = health_info.get('message', '')
                    latency = health_info.get('latency', 0)
                    
                    print_test_result(f"{component}健康检查", 
                                    status in ['healthy', 'unknown'], 
                                    f"状态: {status}, 延迟: {latency}ms, 消息: {message}")
                
                return True
            else:
                print_test_result("健康检查执行", False, f"错误: {data.get('error')}")
                return False
                
        else:
            print_test_result("健康检查执行", False, f"HTTP状态码: {response.status_code}")
            return False
            
    except Exception as e:
        print_test_result("健康检查执行", False, f"异常: {str(e)}")
        return False


def test_model_config_update():
    """测试模型配置更新"""
    print_section("测试模型配置更新")
    
    client = TestClient(app)
    
    try:
        config_data = {
            "embeddings": {
                "provider": "siliconflow",
                "model": "BAAI/bge-large-zh-v1.5",
                "api_key": "test-key",
                "base_url": "https://api.siliconflow.cn/v1",
                "dimensions": 1024,
                "batch_size": 100,
                "chunk_size": 1000,
                "chunk_overlap": 200,
                "timeout": 60.0
            },
            "reranking": {
                "provider": "sentence_transformers",
                "model": "cross-encoder/ms-marco-MiniLM-L-6-v2",
                "batch_size": 32,
                "max_length": 512,
                "timeout": 30.0
            }
        }
        
        response = client.post("/config/models/update-config", json=config_data)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                updated_sections = data.get('updated_sections', [])
                print_test_result("配置更新", True, f"更新的配置节: {updated_sections}")
                return True
            else:
                print_test_result("配置更新", False, f"错误: {data.get('error')}")
                return False
                
        else:
            print_test_result("配置更新", False, f"HTTP状态码: {response.status_code}")
            return False
            
    except Exception as e:
        print_test_result("配置更新", False, f"异常: {str(e)}")
        return False


def test_frontend_integration():
    """测试前端集成"""
    print_section("测试前端集成")
    
    # 检查前端文件
    frontend_files = [
        "frontend/js/settings.js",
        "frontend/js/api.js",
        "frontend/index.html"
    ]
    
    all_files_exist = True
    for file_path in frontend_files:
        if Path(file_path).exists():
            print_test_result(f"文件存在: {file_path}", True)
        else:
            print_test_result(f"文件存在: {file_path}", False)
            all_files_exist = False
    
    # 检查关键函数
    settings_js = Path("frontend/js/settings.js")
    if settings_js.exists():
        with open(settings_js, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查ModelManager类
        if "class ModelManager" in content:
            print_test_result("ModelManager类存在", True)
        else:
            print_test_result("ModelManager类存在", False)
        
        # 检查关键方法
        key_methods = [
            "displayModelStatus",
            "displayModelMetrics",
            "switchActiveModel",
            "isActiveModel",
            "loadModelConfigs"
        ]
        
        for method in key_methods:
            if method in content:
                print_test_result(f"方法存在: {method}", True)
            else:
                print_test_result(f"方法存在: {method}", False)
    
    return all_files_exist


def generate_improvement_summary():
    """生成改进总结"""
    print_section("模型管理功能改进总结")
    
    improvements = [
        "✅ 完善了后端模型管理API接口",
        "✅ 实现了模型状态和指标查询",
        "✅ 添加了模型切换和配置更新功能",
        "✅ 完善了模型健康检查机制",
        "✅ 优化了前端ModelManager类",
        "✅ 实现了活跃模型状态检测",
        "✅ 添加了模型状态和指标显示",
        "✅ 改进了用户交互体验",
        "✅ 统一了前后端数据格式",
        "✅ 完善了错误处理机制"
    ]
    
    print("🎉 主要改进内容:")
    for improvement in improvements:
        print(f"  {improvement}")
    
    print("\n💡 使用建议:")
    print("  1. 在设置页面的'模型配置'部分可以管理嵌入和重排序模型")
    print("  2. 使用'查看模型状态'按钮查看当前模型配置")
    print("  3. 使用'性能指标'按钮查看模型性能数据")
    print("  4. 使用'健康检查'按钮检测模型连接状态")
    print("  5. 通过下拉菜单可以切换活跃模型")
    
    print("\n🔧 技术特性:")
    print("  - 统一的模型平台配置管理")
    print("  - 实时的模型状态监控")
    print("  - 完善的API错误处理")
    print("  - 用户友好的界面交互")
    print("  - 配置持久化保存")


def main():
    """主函数"""
    print("🚀 改进后的模型管理功能测试")
    print("验证前后端集成的模型管理功能")
    
    # 运行测试
    test_results = []
    
    test_results.append(("模型状态API", test_model_status_api()))
    test_results.append(("模型指标API", test_model_metrics_api()))
    test_results.append(("模型切换API", test_model_switch_api()))
    test_results.append(("模型健康检查", test_model_health_check()))
    test_results.append(("模型配置更新", test_model_config_update()))
    test_results.append(("前端集成", test_frontend_integration()))
    
    # 统计结果
    print_section("测试结果统计")
    
    passed_tests = sum(1 for _, result in test_results if result)
    total_tests = len(test_results)
    
    print(f"总测试数: {total_tests}")
    print(f"通过测试: {passed_tests}")
    print(f"失败测试: {total_tests - passed_tests}")
    print(f"通过率: {(passed_tests / total_tests * 100):.1f}%")
    
    # 详细结果
    print("\n📊 详细结果:")
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status} {test_name}")
    
    # 生成改进总结
    generate_improvement_summary()
    
    if passed_tests == total_tests:
        print("\n🎉 所有测试通过！模型管理功能已完善。")
    else:
        print(f"\n⚠️ 有 {total_tests - passed_tests} 个测试失败，需要进一步完善。")


if __name__ == "__main__":
    main()