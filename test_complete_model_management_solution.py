#!/usr/bin/env python3
"""
完整模型管理解决方案测试

验证从前端到后端的完整模型管理流程
"""

import asyncio
import sys
import json
import yaml
from pathlib import Path
import aiohttp
import time

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def print_section(title: str):
    """打印格式化的章节"""
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print(f"{'='*60}")


async def test_api_startup_and_model_manager():
    """测试API启动和模型管理器初始化"""
    print_section("测试API启动和模型管理器初始化")
    
    base_url = "http://localhost:8000"
    
    # 1. 测试健康检查
    print("1. 测试API健康检查")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base_url}/health") as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"   ✅ API服务正常运行")
                    print(f"   📋 服务: {result.get('service', 'unknown')}")
                    print(f"   📋 状态: {result.get('status', 'unknown')}")
                    return True
                else:
                    print(f"   ❌ API服务异常 (状态码: {response.status})")
                    return False
    except Exception as e:
        print(f"   ❌ 无法连接到API服务: {str(e)}")
        print(f"   💡 请确保后端服务正在运行: python -m rag_system.api.main")
        return False


async def test_model_management_apis():
    """测试模型管理API"""
    print_section("测试模型管理API")
    
    base_url = "http://localhost:8000"
    
    # 1. 测试获取模型配置
    print("1. 测试获取模型配置API")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base_url}/models/configs") as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"   ✅ 获取模型配置成功")
                    print(f"   📋 成功状态: {result.get('success', False)}")
                    print(f"   📋 模型配置数量: {len(result.get('model_configs', {}))}")
                    return True
                else:
                    error_text = await response.text()
                    print(f"   ❌ 获取模型配置失败 (状态码: {response.status})")
                    print(f"   📋 错误信息: {error_text}")
                    return False
    except Exception as e:
        print(f"   ❌ 请求失败: {str(e)}")
        return False


async def test_add_embedding_model():
    """测试添加嵌入模型"""
    print_section("测试添加嵌入模型")
    
    base_url = "http://localhost:8000"
    
    # 构造测试数据（模拟前端发送的数据）
    model_data = {
        "model_type": "embedding",
        "name": "test_embedding_model_2048",
        "provider": "siliconflow",
        "model_name": "BAAI/bge-large-zh-v1.5",
        "config": {
            "dimensions": 2048,  # 关键：用户设置的维度
            "batch_size": 50,
            "chunk_size": 1000,
            "chunk_overlap": 50,
            "timeout": 120,
            "api_key": "sk-test-embedding-key",
            "base_url": "https://api.siliconflow.cn/v1"
        }
    }
    
    print("1. 发送添加嵌入模型请求")
    print(f"   📤 模型名称: {model_data['name']}")
    print(f"   📤 提供商: {model_data['provider']}")
    print(f"   📤 维度: {model_data['config']['dimensions']}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{base_url}/models/add",
                json=model_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"   ✅ 添加嵌入模型成功")
                    print(f"   📋 响应: {result}")
                    return True
                else:
                    error_text = await response.text()
                    print(f"   ❌ 添加嵌入模型失败 (状态码: {response.status})")
                    print(f"   📋 错误信息: {error_text}")
                    return False
    except Exception as e:
        print(f"   ❌ 请求失败: {str(e)}")
        return False


async def test_model_test_api():
    """测试模型测试API"""
    print_section("测试模型测试API")
    
    base_url = "http://localhost:8000"
    
    test_data = {
        "model_type": "embedding",
        "model_name": "test_embedding_model_2048"
    }
    
    print("1. 发送模型测试请求")
    print(f"   📤 模型类型: {test_data['model_type']}")
    print(f"   📤 模型名称: {test_data['model_name']}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{base_url}/models/test",
                json=test_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"   ✅ 模型测试成功")
                    print(f"   📋 响应: {result}")
                    return True
                else:
                    error_text = await response.text()
                    print(f"   ❌ 模型测试失败 (状态码: {response.status})")
                    print(f"   📋 错误信息: {error_text}")
                    return False
    except Exception as e:
        print(f"   ❌ 请求失败: {str(e)}")
        return False


def test_frontend_integration():
    """测试前端集成"""
    print_section("测试前端集成")
    
    print("1. 验证前端API客户端")
    api_js_path = Path("frontend/js/api.js")
    if api_js_path.exists():
        with open(api_js_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_methods = ['addModel', 'testModel', 'getModelConfigs', 'switchActiveModel']
        all_methods_exist = True
        
        for method in required_methods:
            if f"async {method}(" in content:
                print(f"   ✅ API方法 {method} 存在")
            else:
                print(f"   ❌ API方法 {method} 缺失")
                all_methods_exist = False
        
        if all_methods_exist:
            print("   ✅ 前端API客户端完整")
        else:
            print("   ❌ 前端API客户端不完整")
            return False
    else:
        print("   ❌ 前端API客户端文件不存在")
        return False
    
    print("\n2. 验证前端设置管理")
    settings_js_path = Path("frontend/js/settings.js")
    if settings_js_path.exists():
        with open(settings_js_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if "async function addEmbeddingModel" in content:
            print("   ✅ addEmbeddingModel 函数存在")
        else:
            print("   ❌ addEmbeddingModel 函数缺失")
            return False
        
        if "embeddingDimension" in content:
            print("   ✅ 维度参数处理存在")
        else:
            print("   ❌ 维度参数处理缺失")
            return False
    else:
        print("   ❌ 前端设置文件不存在")
        return False
    
    return True


async def main():
    """主函数"""
    print("🚀 完整模型管理解决方案测试")
    print("验证从前端到后端的完整模型管理流程")
    
    results = []
    
    try:
        # 1. 测试前端集成
        print("📋 第一阶段：前端集成测试")
        results.append(test_frontend_integration())
        
        # 2. 测试API启动和模型管理器
        print("\n📋 第二阶段：后端服务测试")
        results.append(await test_api_startup_and_model_manager())
        
        if results[-1]:  # 如果API服务正常
            # 3. 测试模型管理API
            print("\n📋 第三阶段：模型管理API测试")
            results.append(await test_model_management_apis())
            
            # 4. 测试添加嵌入模型
            print("\n📋 第四阶段：添加嵌入模型测试")
            results.append(await test_add_embedding_model())
            
            # 5. 测试模型测试API
            print("\n📋 第五阶段：模型测试API测试")
            results.append(await test_model_test_api())
        else:
            print("\n⚠️ 跳过后续测试，因为API服务不可用")
            results.extend([False, False, False])  # 添加失败结果
        
        print_section("测试总结")
        
        test_names = [
            "前端集成",
            "API服务启动",
            "模型管理API",
            "添加嵌入模型",
            "模型测试API"
        ]
        
        print("📊 测试结果:")
        for i, (name, result) in enumerate(zip(test_names, results), 1):
            status = "✅ 通过" if result else "❌ 失败"
            print(f"   {i}. {name}: {status}")
        
        if all(results):
            print("\n🎉 所有测试通过！")
            print("🎯 完整模型管理解决方案正常工作:")
            print("   ✅ 前端界面完整")
            print("   ✅ API客户端正确")
            print("   ✅ 后端服务正常")
            print("   ✅ 模型管理器已初始化")
            print("   ✅ 添加模型功能正常")
            print("   ✅ 模型测试功能正常")
            
            print("\n💡 用户现在可以:")
            print("   1. 在前端设置页面配置嵌入模型")
            print("   2. 修改维度参数（如设置为2048）")
            print("   3. 点击添加模型按钮")
            print("   4. 系统会正确保存所有配置")
            print("   5. 可以测试模型连接")
            
        else:
            failed_tests = [name for name, result in zip(test_names, results) if not result]
            print(f"\n❌ 部分测试失败: {', '.join(failed_tests)}")
            
            print("\n🔧 修复建议:")
            if not results[0]:
                print("   - 检查前端文件完整性")
            if not results[1]:
                print("   - 启动后端服务: python -m rag_system.api.main")
            if len(results) > 2 and not results[2]:
                print("   - 检查模型管理器初始化")
            if len(results) > 3 and not results[3]:
                print("   - 检查模型添加API实现")
            if len(results) > 4 and not results[4]:
                print("   - 检查模型测试API实现")
        
        return all(results)
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)