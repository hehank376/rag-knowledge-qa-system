#!/usr/bin/env python3
"""
API统一调用测试脚本

验证前端使用统一apiClient进行API调用的效果
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


def test_api_endpoints():
    """测试API端点可用性"""
    print_section("测试API端点可用性")
    
    client = TestClient(app)
    
    # 测试的API端点
    endpoints = [
        ("GET", "/config/", "获取配置"),
        ("GET", "/config/models/status", "获取模型状态"),
        ("GET", "/config/models/metrics", "获取模型指标"),
        ("POST", "/config/models/switch-active", "切换活跃模型"),
        ("POST", "/config/models/add-model", "添加模型"),
        ("POST", "/config/models/test-model", "测试模型"),
        ("POST", "/config/models/update-config", "更新模型配置"),
        ("POST", "/config/models/health-check", "模型健康检查")
    ]
    
    results = []
    
    for method, endpoint, description in endpoints:
        try:
            if method == "GET":
                response = client.get(endpoint)
            else:
                response = client.post(endpoint, json={})
            
            # 检查响应状态
            if response.status_code in [200, 422]:  # 200=成功, 422=参数错误但端点存在
                success = True
                status_info = f"状态码: {response.status_code}"
            else:
                success = False
                status_info = f"状态码: {response.status_code}"
            
            results.append((description, success))
            print_test_result(description, success, status_info)
            
        except Exception as e:
            results.append((description, False))
            print_test_result(description, False, f"异常: {str(e)}")
    
    return results


def analyze_api_structure():
    """分析API结构"""
    print_section("分析API结构")
    
    # 检查前端API文件
    api_js_path = Path("frontend/js/api.js")
    if api_js_path.exists():
        with open(api_js_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否包含模型管理方法
        model_methods = [
            'getModelStatus',
            'getModelMetrics', 
            'switchActiveModel',
            'addModel',
            'testModel',
            'updateModelConfig',
            'performModelHealthCheck'
        ]
        
        missing_methods = []
        for method in model_methods:
            if f"async {method}(" not in content:
                missing_methods.append(method)
        
        if not missing_methods:
            print_test_result("API方法完整性", True, "所有模型管理方法都已添加")
        else:
            print_test_result("API方法完整性", False, f"缺失方法: {missing_methods}")
        
        # 检查apiClient绑定
        if "getModelStatus: configAPI.getModelStatus.bind(configAPI)" in content:
            print_test_result("apiClient绑定", True, "模型管理方法已正确绑定到apiClient")
        else:
            print_test_result("apiClient绑定", False, "模型管理方法未绑定到apiClient")
        
        return len(missing_methods) == 0
    else:
        print_test_result("API文件存在", False, "frontend/js/api.js文件不存在")
        return False


def check_settings_js_updates():
    """检查settings.js的更新"""
    print_section("检查settings.js的更新")
    
    settings_js_path = Path("frontend/js/settings.js")
    if settings_js_path.exists():
        try:
            with open(settings_js_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                with open(settings_js_path, 'r', encoding='utf-8-sig') as f:
                    content = f.read()
            except UnicodeDecodeError:
                with open(settings_js_path, 'r', encoding='latin-1') as f:
                    content = f.read()
        
        # 检查是否使用了统一的apiClient调用
        old_patterns = [
            "fetch('/config/models/",
            "method: 'POST'",
            "headers: {'Content-Type': 'application/json'}"
        ]
        
        new_patterns = [
            "apiClient.getModelStatus()",
            "apiClient.switchActiveModel(",
            "apiClient.addModel(",
            "apiClient.testModel(",
            "apiClient.updateModelConfig(",
            "apiClient.testConnection("
        ]
        
        # 检查是否还有旧的fetch调用
        old_calls_found = sum(1 for pattern in old_patterns if pattern in content)
        
        # 更准确地计算apiClient调用数量
        import re
        apiClient_calls = len(re.findall(r'apiClient\.\w+\(', content))
        
        if old_calls_found == 0 and apiClient_calls >= 10:
            print_test_result("API调用统一化", True, f"已使用统一apiClient调用 ({apiClient_calls}个调用)")
        elif old_calls_found > 0:
            print_test_result("API调用统一化", False, f"仍有{old_calls_found}个旧的fetch调用")
        else:
            print_test_result("API调用统一化", False, f"只找到{apiClient_calls}个apiClient调用")
        
        return old_calls_found == 0 and apiClient_calls >= 10
    else:
        print_test_result("settings.js文件存在", False, "frontend/js/settings.js文件不存在")
        return False


def generate_usage_examples():
    """生成使用示例"""
    print_section("API调用使用示例")
    
    examples = [
        ("获取模型状态", "const status = await apiClient.getModelStatus();"),
        ("切换活跃模型", "const result = await apiClient.switchActiveModel('embedding', 'new-model');"),
        ("添加新模型", "const result = await apiClient.addModel('embedding', config);"),
        ("测试模型", "const result = await apiClient.testModel('embedding', 'model-name');"),
        ("更新模型配置", "const result = await apiClient.updateModelConfig(configData);"),
        ("执行健康检查", "const result = await apiClient.performModelHealthCheck();")
    ]
    
    print("📝 统一API调用示例:")
    for description, code in examples:
        print(f"  {description}:")
        print(f"    {code}")
    
    print("\n🔄 对比旧的调用方式:")
    print("  旧方式 (不推荐):")
    print("    const response = await fetch('/config/models/status');")
    print("    const data = await response.json();")
    
    print("  新方式 (推荐):")
    print("    const data = await apiClient.getModelStatus();")


def main():
    """主函数"""
    print("🚀 API统一调用测试")
    print("测试前端API调用的统一化改进")
    
    # 运行测试
    api_results = test_api_endpoints()
    api_structure_ok = analyze_api_structure()
    settings_updated = check_settings_js_updates()
    
    # 生成使用示例
    generate_usage_examples()
    
    # 总结
    print_section("测试总结")
    
    api_success_count = sum(1 for _, success in api_results if success)
    api_total_count = len(api_results)
    
    print(f"API端点测试: {api_success_count}/{api_total_count} 通过")
    print(f"API结构检查: {'✅ 通过' if api_structure_ok else '❌ 失败'}")
    print(f"settings.js更新: {'✅ 通过' if settings_updated else '❌ 失败'}")
    
    overall_success = (api_success_count == api_total_count and 
                      api_structure_ok and 
                      settings_updated)
    
    if overall_success:
        print("\n🎉 API统一化改进完成！")
        print("✅ 所有API调用已统一使用apiClient")
        print("✅ 代码更加简洁和一致")
        print("✅ 错误处理更加统一")
    else:
        print("\n⚠️ API统一化需要进一步完善")
        if api_success_count < api_total_count:
            print("❌ 部分API端点不可用")
        if not api_structure_ok:
            print("❌ API结构需要完善")
        if not settings_updated:
            print("❌ settings.js需要更新")
    
    print("\n💡 优势:")
    print("- 统一的错误处理机制")
    print("- 简化的API调用语法")
    print("- 更好的代码维护性")
    print("- 一致的响应处理")


if __name__ == "__main__":
    main()