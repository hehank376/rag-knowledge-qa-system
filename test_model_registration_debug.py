#!/usr/bin/env python3
"""
模型注册调试测试
检查模型注册和加载的完整流程
"""
import asyncio
import sys
import json
from pathlib import Path
import aiohttp

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def print_section(title: str):
    """打印格式化的章节"""
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print(f"{'='*60}")

async def test_model_registration_flow():
    """测试完整的模型注册流程"""
    print_section("测试模型注册和测试流程")
    
    base_url = "http://localhost:8000"
    
    # 1. 添加嵌入模型
    print("1. 添加嵌入模型")
    embedding_data = {
        "model_type": "embedding",
        "name": "test_embedding_debug",  # 注意：这是注册名称
        "provider": "siliconflow",
        "model_name": "BAAI/bge-large-zh-v1.5",  # 注意：这是实际模型名称
        "config": {
            "provider": "siliconflow",
            "dimensions": 1024,
            "batch_size": 50,
            "api_key": "sk-test-debug",
            "base_url": "https://api.siliconflow.cn/v1"
        }
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{base_url}/models/add",
                json=embedding_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"   ✅ 添加嵌入模型成功")
                    print(f"   📋 响应: {result}")
                    print(f"   📋 模型是否加载成功: {result.get('loaded', 'unknown')}")
                else:
                    error_text = await response.text()
                    print(f"   ❌ 添加嵌入模型失败: {error_text}")
                    return False
    except Exception as e:
        print(f"   ❌ 请求失败: {str(e)}")
        return False
    
    # 2. 获取模型配置列表
    print("\n2. 获取模型配置列表")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base_url}/models/configs") as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"   ✅ 获取模型配置成功")
                    
                    model_configs = result.get('model_configs', {})
                    active_models = result.get('active_models', {})
                    model_statuses = result.get('model_statuses', {})
                    
                    print(f"   📋 注册的模型配置:")
                    for name, config in model_configs.items():
                        print(f"      - {name}: {config.get('model_type', 'unknown')} / {config.get('model_name', 'unknown')}")
                    
                    print(f"   📋 活跃的模型:")
                    for model_type, model_name in active_models.items():
                        print(f"      - {model_type}: {model_name}")
                    
                    print(f"   📋 模型状态:")
                    for name, status in model_statuses.items():
                        print(f"      - {name}: {status.get('status', 'unknown')} / {status.get('health', 'unknown')}")
                        if status.get('error_message'):
                            print(f"        错误: {status.get('error_message')}")
                else:
                    error_text = await response.text()
                    print(f"   ❌ 获取模型配置失败: {error_text}")
    except Exception as e:
        print(f"   ❌ 请求失败: {str(e)}")
    
    # 3. 测试不同的模型名称
    print("\n3. 测试不同的模型名称")
    
    test_cases = [
        ("使用注册名称", "test_embedding_debug"),
        ("使用实际模型名称", "BAAI/bge-large-zh-v1.5"),
        ("使用配置文件中的模型名称", "BAAI/bge-large-zh-v1.5")  # 从配置文件读取
    ]
    
    for test_name, model_name in test_cases:
        print(f"\n   测试 {test_name}: {model_name}")
        test_data = {
            "model_type": "embedding",
            "model_name": model_name
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{base_url}/models/test",
                    json=test_data,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get('success'):
                            print(f"      ✅ 测试成功: {result}")
                        else:
                            print(f"      ❌ 测试失败: {result.get('error', 'unknown error')}")
                    else:
                        error_text = await response.text()
                        print(f"      ❌ 请求失败: {error_text}")
        except Exception as e:
            print(f"      ❌ 请求异常: {str(e)}")
    
    return True

async def test_reranking_model_flow():
    """测试重排序模型流程"""
    print_section("测试重排序模型注册和测试流程")
    
    base_url = "http://localhost:8000"
    
    # 1. 添加重排序模型
    print("1. 添加重排序模型")
    reranking_data = {
        "model_type": "reranking",
        "name": "test_reranking_debug",  # 注意：这是注册名称
        "provider": "siliconflow",
        "model_name": "BAAI/bge-reranker-v2-m3",  # 注意：这是实际模型名称
        "config": {
            "provider": "siliconflow",
            "batch_size": 32,
            "max_length": 512,
            "api_key": "sk-test-debug",
            "base_url": "https://api.siliconflow.cn/v1"
        }
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{base_url}/models/add",
                json=reranking_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"   ✅ 添加重排序模型成功")
                    print(f"   📋 响应: {result}")
                    print(f"   📋 模型是否加载成功: {result.get('loaded', 'unknown')}")
                else:
                    error_text = await response.text()
                    print(f"   ❌ 添加重排序模型失败: {error_text}")
                    return False
    except Exception as e:
        print(f"   ❌ 请求失败: {str(e)}")
        return False
    
    # 2. 测试不同的模型名称
    print("\n2. 测试不同的模型名称")
    
    test_cases = [
        ("使用注册名称", "test_reranking_debug"),
        ("使用实际模型名称", "BAAI/bge-reranker-v2-m3"),
    ]
    
    for test_name, model_name in test_cases:
        print(f"\n   测试 {test_name}: {model_name}")
        test_data = {
            "model_type": "reranking",
            "model_name": model_name
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{base_url}/models/test",
                    json=test_data,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get('success'):
                            print(f"      ✅ 测试成功: {result}")
                        else:
                            print(f"      ❌ 测试失败: {result.get('error', 'unknown error')}")
                    else:
                        error_text = await response.text()
                        print(f"      ❌ 请求失败: {error_text}")
        except Exception as e:
            print(f"      ❌ 请求异常: {str(e)}")
    
    return True

async def main():
    """主函数"""
    print("🚀 模型注册调试测试")
    print("检查模型注册、加载和测试的完整流程")
    
    results = []
    
    try:
        # 1. 测试嵌入模型流程
        results.append(await test_model_registration_flow())
        
        # 2. 测试重排序模型流程
        results.append(await test_reranking_model_flow())
        
        print_section("测试总结")
        test_names = ["嵌入模型流程", "重排序模型流程"]
        
        print("📊 测试结果:")
        for i, (name, result) in enumerate(zip(test_names, results), 1):
            status = "✅ 通过" if result else "❌ 失败"
            print(f"   {i}. {name}: {status}")
        
        if all(results):
            print("\n🎉 所有测试通过！")
            print("🎯 模型注册和测试流程正常工作")
        else:
            failed_tests = [name for name, result in zip(test_names, results) if not result]
            print(f"\n❌ 部分测试失败: {', '.join(failed_tests)}")
            print("\n🔧 可能的问题:")
            print("   - 模型名称不匹配（注册名称 vs 实际模型名称）")
            print("   - 模型加载失败")
            print("   - 服务字典中没有对应的服务实例")
        
        return all(results)
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)