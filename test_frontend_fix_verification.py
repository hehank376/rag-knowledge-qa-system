#!/usr/bin/env python3
"""
前端修复验证测试

验证前端模型管理修复是否完成
"""

import sys
from pathlib import Path

def print_section(title: str):
    """打印格式化的章节"""
    print(f"\n{'='*50}")
    print(f"🔍 {title}")
    print(f"{'='*50}")


def test_api_client_methods():
    """测试API客户端方法"""
    print_section("测试前端API客户端方法")
    
    api_js_path = Path("frontend/js/api.js")
    if not api_js_path.exists():
        print("   ❌ API客户端文件不存在")
        return False
    
    try:
        with open(api_js_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查必要的方法
        required_methods = {
            'addModel': 'async addModel(',
            'testModel': 'async testModel(',
            'getModelConfigs': 'async getModelConfigs(',
            'switchActiveModel': 'async switchActiveModel('
        }
        
        all_methods_exist = True
        for method_name, method_signature in required_methods.items():
            if method_signature in content:
                print(f"   ✅ 方法 {method_name} 存在")
            else:
                print(f"   ❌ 方法 {method_name} 缺失")
                all_methods_exist = False
        
        # 检查API路径
        required_paths = [
            "'/models/add'",
            "'/models/test'", 
            "'/models/configs'",
            "'/models/switch'"
        ]
        
        print("\n   检查API路径:")
        all_paths_exist = True
        for path in required_paths:
            if path in content:
                print(f"   ✅ 路径 {path} 存在")
            else:
                print(f"   ❌ 路径 {path} 缺失")
                all_paths_exist = False
        
        return all_methods_exist and all_paths_exist
        
    except Exception as e:
        print(f"   ❌ 读取API客户端文件失败: {str(e)}")
        return False


def test_backend_api_routes():
    """测试后端API路由"""
    print_section("测试后端API路由")
    
    api_file_path = Path("rag_system/api/model_manager_api.py")
    if not api_file_path.exists():
        print("   ❌ 后端API文件不存在")
        return False
    
    try:
        with open(api_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查必要的路由
        required_routes = {
            'add': '@router.post("/add")',
            'test': '@router.post("/test")',
            'configs': '@router.get("/configs")',
            'switch': '@router.post("/switch")'
        }
        
        all_routes_exist = True
        for route_name, route_decorator in required_routes.items():
            if route_decorator in content:
                print(f"   ✅ 路由 {route_name} 存在")
            else:
                print(f"   ❌ 路由 {route_name} 缺失")
                all_routes_exist = False
        
        return all_routes_exist
        
    except Exception as e:
        print(f"   ❌ 读取后端API文件失败: {str(e)}")
        return False


def test_api_registration():
    """测试API注册"""
    print_section("测试API注册")
    
    main_api_path = Path("rag_system/api/main.py")
    if not main_api_path.exists():
        print("   ❌ 主API文件不存在")
        return False
    
    try:
        with open(main_api_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查模型管理API是否被导入和注册
        if "from .model_manager_api import router as model_manager_router" in content:
            print("   ✅ 模型管理API已导入")
        else:
            print("   ❌ 模型管理API未导入")
            return False
        
        if "app.include_router(model_manager_router)" in content:
            print("   ✅ 模型管理API已注册")
        else:
            print("   ❌ 模型管理API未注册")
            return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ 读取主API文件失败: {str(e)}")
        return False


def test_import_fix():
    """测试导入修复"""
    print_section("测试导入修复")
    
    model_manager_path = Path("rag_system/services/model_manager.py")
    if not model_manager_path.exists():
        print("   ❌ 模型管理器文件不存在")
        return False
    
    try:
        with open(model_manager_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否还有错误的导入
        if "RerankingServiceManager" in content:
            print("   ❌ 仍然存在错误的 RerankingServiceManager 导入")
            return False
        else:
            print("   ✅ 错误的导入已修复")
        
        # 检查正确的导入
        if "from .reranking_service import RerankingService" in content:
            print("   ✅ 正确的 RerankingService 导入存在")
        else:
            print("   ❌ 缺少正确的 RerankingService 导入")
            return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ 读取模型管理器文件失败: {str(e)}")
        return False


def main():
    """主函数"""
    print("🚀 前端修复验证测试")
    print("验证前端模型管理修复是否完成")
    
    results = []
    
    # 1. 测试API客户端方法
    results.append(test_api_client_methods())
    
    # 2. 测试后端API路由
    results.append(test_backend_api_routes())
    
    # 3. 测试API注册
    results.append(test_api_registration())
    
    # 4. 测试导入修复
    results.append(test_import_fix())
    
    print_section("修复验证总结")
    
    if all(results):
        print("✅ 所有修复验证通过！")
        print("🎯 修复完成项目:")
        print("   - 前端API客户端: 添加了缺失的模型管理方法")
        print("   - 后端API路由: 提供完整的模型管理接口")
        print("   - API路由注册: 模型管理API已正确注册")
        print("   - 导入错误修复: 移除了不存在的类导入")
        
        print("\n💡 现在可以:")
        print("   1. 启动后端服务: python -m rag_system.api.main")
        print("   2. 打开前端页面进行模型配置")
        print("   3. 使用添加模型和测试连接功能")
        print("   4. 运行完整的端到端测试")
        
        print("\n🧪 建议的测试步骤:")
        print("   1. 运行: python test_simple_reranking_fix.py")
        print("   2. 启动API服务并测试端点")
        print("   3. 在前端界面中测试模型管理功能")
        
    else:
        print("❌ 部分修复验证失败")
        print("请检查上述失败的项目并进行修复")
    
    return all(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)