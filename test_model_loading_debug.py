#!/usr/bin/env python3
"""
模型加载调试测试
深入调试模型加载失败的原因
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

async def test_model_loading_details():
    """测试模型加载的详细信息"""
    print_section("测试模型加载详细信息")
    
    base_url = "http://localhost:8000"
    
    # 1. 添加一个简单的嵌入模型
    print("1. 添加嵌入模型")
    embedding_data = {
        "model_type": "embedding",
        "name": "debug_embedding",
        "provider": "mock",  # 使用mock提供商，应该更容易成功
        "model_name": "mock-embedding-model",
        "config": {
            "provider": "mock",
            "dimensions": 768,
            "batch_size": 10
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
                    
                    if result.get('loaded'):
                        print(f"   ✅ 模型加载成功")
                    else:
                        print(f"   ❌ 模型加载失败")
                else:
                    error_text = await response.text()
                    print(f"   ❌ 添加嵌入模型失败: {error_text}")
                    return False
    except Exception as e:
        print(f"   ❌ 请求失败: {str(e)}")
        return False
    
    # 2. 获取详细的模型状态
    print("\n2. 获取模型状态详情")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base_url}/models/configs") as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"   ✅ 获取模型状态成功")
                    
                    model_statuses = result.get('model_statuses', {})
                    for name, status in model_statuses.items():
                        print(f"   📋 模型 {name}:")
                        print(f"      状态: {status.get('status', 'unknown')}")
                        print(f"      健康: {status.get('health', 'unknown')}")
                        if status.get('error_message'):
                            print(f"      错误: {status.get('error_message')}")
                        if status.get('load_time'):
                            print(f"      加载时间: {status.get('load_time')}秒")
                else:
                    error_text = await response.text()
                    print(f"   ❌ 获取模型状态失败: {error_text}")
    except Exception as e:
        print(f"   ❌ 请求失败: {str(e)}")
    
    # 3. 测试模型（使用注册名称）
    print("\n3. 测试模型（使用注册名称）")
    test_data = {
        "model_type": "embedding",
        "model_name": "debug_embedding"
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
                    print(f"   📋 测试结果: {result}")
                    if result.get('success'):
                        print(f"   ✅ 模型测试成功")
                        return True
                    else:
                        print(f"   ❌ 模型测试失败: {result.get('error')}")
                        return False
                else:
                    error_text = await response.text()
                    print(f"   ❌ 测试请求失败: {error_text}")
                    return False
    except Exception as e:
        print(f"   ❌ 请求异常: {str(e)}")
        return False

async def test_reranking_loading_details():
    """测试重排序模型加载详情"""
    print_section("测试重排序模型加载详情")
    
    base_url = "http://localhost:8000"
    
    # 1. 添加一个简单的重排序模型
    print("1. 添加重排序模型")
    reranking_data = {
        "model_type": "reranking",
        "name": "debug_reranking",
        "provider": "mock",  # 使用mock提供商
        "model_name": "mock-reranking-model",
        "config": {
            "provider": "mock",
            "batch_size": 8,
            "max_length": 256
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
                    
                    if result.get('loaded'):
                        print(f"   ✅ 模型加载成功")
                    else:
                        print(f"   ❌ 模型加载失败")
                else:
                    error_text = await response.text()
                    print(f"   ❌ 添加重排序模型失败: {error_text}")
                    return False
    except Exception as e:
        print(f"   ❌ 请求失败: {str(e)}")
        return False
    
    # 2. 测试重排序模型
    print("\n2. 测试重排序模型（使用注册名称）")
    test_data = {
        "model_type": "reranking",
        "model_name": "debug_reranking"
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
                    print(f"   📋 测试结果: {result}")
                    if result.get('success'):
                        print(f"   ✅ 重排序模型测试成功")
                        return True
                    else:
                        print(f"   ❌ 重排序模型测试失败: {result.get('error')}")
                        return False
                else:
                    error_text = await response.text()
                    print(f"   ❌ 测试请求失败: {error_text}")
                    return False
    except Exception as e:
        print(f"   ❌ 请求异常: {str(e)}")
        return False

async def test_current_config_models():
    """测试当前配置文件中的模型"""
    print_section("测试当前配置文件中的模型")
    
    base_url = "http://localhost:8000"
    
    # 1. 获取当前配置
    print("1. 获取当前配置")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base_url}/config/") as response:
                if response.status == 200:
                    result = await response.json()
                    config = result.get('config', {})
                    
                    # 检查嵌入模型配置
                    embeddings = config.get('embeddings', {})
                    if embeddings:
                        print(f"   📋 当前嵌入模型配置:")
                        print(f"      提供商: {embeddings.get('provider')}")
                        print(f"      模型: {embeddings.get('model')}")
                        print(f"      维度: {embeddings.get('dimensions')}")
                        
                        # 测试当前配置的嵌入模型
                        print(f"\n   测试当前配置的嵌入模型:")
                        test_data = {
                            "model_type": "embedding",
                            "model_name": embeddings.get('model')
                        }
                        
                        async with session.post(
                            f"{base_url}/models/test",
                            json=test_data,
                            headers={"Content-Type": "application/json"}
                        ) as test_response:
                            if test_response.status == 200:
                                test_result = await test_response.json()
                                if test_result.get('success'):
                                    print(f"      ✅ 当前嵌入模型测试成功")
                                else:
                                    print(f"      ❌ 当前嵌入模型测试失败: {test_result.get('error')}")
                    
                    # 检查重排序模型配置
                    reranking = config.get('reranking', {})
                    if reranking:
                        print(f"\n   📋 当前重排序模型配置:")
                        print(f"      提供商: {reranking.get('provider')}")
                        print(f"      模型: {reranking.get('model')}")
                        print(f"      批处理大小: {reranking.get('batch_size')}")
                        
                        # 测试当前配置的重排序模型
                        print(f"\n   测试当前配置的重排序模型:")
                        test_data = {
                            "model_type": "reranking",
                            "model_name": reranking.get('model')
                        }
                        
                        async with session.post(
                            f"{base_url}/models/test",
                            json=test_data,
                            headers={"Content-Type": "application/json"}
                        ) as test_response:
                            if test_response.status == 200:
                                test_result = await test_response.json()
                                if test_result.get('success'):
                                    print(f"      ✅ 当前重排序模型测试成功")
                                    return True
                                else:
                                    print(f"      ❌ 当前重排序模型测试失败: {test_result.get('error')}")
                                    return False
                else:
                    error_text = await response.text()
                    print(f"   ❌ 获取配置失败: {error_text}")
                    return False
    except Exception as e:
        print(f"   ❌ 请求失败: {str(e)}")
        return False

async def main():
    """主函数"""
    print("🚀 模型加载调试测试")
    print("深入调试模型加载失败的原因")
    
    results = []
    
    try:
        # 1. 测试mock模型加载
        results.append(await test_model_loading_details())
        
        # 2. 测试重排序模型加载
        results.append(await test_reranking_loading_details())
        
        # 3. 测试当前配置文件中的模型
        results.append(await test_current_config_models())
        
        print_section("调试总结")
        test_names = ["Mock嵌入模型", "Mock重排序模型", "配置文件模型"]
        
        print("📊 测试结果:")
        for i, (name, result) in enumerate(zip(test_names, results), 1):
            status = "✅ 通过" if result else "❌ 失败"
            print(f"   {i}. {name}: {status}")
        
        if any(results):
            print("\n🎯 发现的问题:")
            if results[0]:
                print("   ✅ Mock嵌入模型可以正常工作")
            else:
                print("   ❌ 连Mock嵌入模型都无法工作，可能是基础架构问题")
            
            if results[1]:
                print("   ✅ Mock重排序模型可以正常工作")
            else:
                print("   ❌ Mock重排序模型无法工作")
            
            if results[2]:
                print("   ✅ 配置文件中的模型可以工作")
            else:
                print("   ❌ 配置文件中的模型无法工作")
        else:
            print("\n❌ 所有测试都失败了")
            print("🔧 可能的问题:")
            print("   - 模型管理器初始化有问题")
            print("   - 服务创建逻辑有问题")
            print("   - 依赖注入有问题")
        
        return any(results)
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)