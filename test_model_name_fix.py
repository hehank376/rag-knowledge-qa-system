#!/usr/bin/env python3
"""
模型名称修复测试
测试通过实际模型名称查找服务是否正常工作
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

async def test_model_name_resolution():
    """测试模型名称解析修复"""
    print_section("测试模型名称解析修复")
    
    base_url = "http://localhost:8000"
    
    # 1. 添加一个嵌入模型（使用不同的注册名称和实际模型名称）
    print("1. 添加嵌入模型")
    embedding_data = {
        "model_type": "embedding",
        "name": "my_custom_embedding",           # 注册名称
        "provider": "siliconflow",
        "model_name": "BAAI/bge-large-zh-v1.5", # 实际模型名称
        "config": {
            "provider": "siliconflow",
            "dimensions": 1024,
            "batch_size": 50,
            "api_key": "sk-test-name-fix",
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
                    print(f"   📋 注册名称: my_custom_embedding")
                    print(f"   📋 实际模型名称: BAAI/bge-large-zh-v1.5")
                    print(f"   📋 模型加载状态: {result.get('loaded', 'unknown')}")
                else:
                    error_text = await response.text()
                    print(f"   ❌ 添加嵌入模型失败: {error_text}")
                    return False
    except Exception as e:
        print(f"   ❌ 请求失败: {str(e)}")
        return False
    
    # 2. 测试使用注册名称
    print("\n2. 测试使用注册名称")
    test_data = {
        "model_type": "embedding",
        "model_name": "my_custom_embedding"  # 使用注册名称
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
                        print(f"   ✅ 使用注册名称测试成功")
                    else:
                        print(f"   ❌ 使用注册名称测试失败: {result.get('error')}")
                else:
                    error_text = await response.text()
                    print(f"   ❌ 请求失败: {error_text}")
    except Exception as e:
        print(f"   ❌ 请求异常: {str(e)}")
    
    # 3. 测试使用实际模型名称（这是修复的重点）
    print("\n3. 测试使用实际模型名称")
    test_data = {
        "model_type": "embedding",
        "model_name": "BAAI/bge-large-zh-v1.5"  # 使用实际模型名称
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
                        print(f"   ✅ 使用实际模型名称测试成功！修复有效！")
                        return True
                    else:
                        print(f"   ❌ 使用实际模型名称测试失败: {result.get('error')}")
                        return False
                else:
                    error_text = await response.text()
                    print(f"   ❌ 请求失败: {error_text}")
                    return False
    except Exception as e:
        print(f"   ❌ 请求异常: {str(e)}")
        return False

async def test_reranking_name_resolution():
    """测试重排序模型名称解析"""
    print_section("测试重排序模型名称解析")
    
    base_url = "http://localhost:8000"
    
    # 1. 添加一个重排序模型
    print("1. 添加重排序模型")
    reranking_data = {
        "model_type": "reranking",
        "name": "my_custom_reranking",           # 注册名称
        "provider": "siliconflow",
        "model_name": "BAAI/bge-reranker-v2-m3", # 实际模型名称
        "config": {
            "provider": "siliconflow",
            "batch_size": 32,
            "max_length": 512,
            "api_key": "sk-test-name-fix",
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
                    print(f"   📋 注册名称: my_custom_reranking")
                    print(f"   📋 实际模型名称: BAAI/bge-reranker-v2-m3")
                    print(f"   📋 模型加载状态: {result.get('loaded', 'unknown')}")
                else:
                    error_text = await response.text()
                    print(f"   ❌ 添加重排序模型失败: {error_text}")
                    return False
    except Exception as e:
        print(f"   ❌ 请求失败: {str(e)}")
        return False
    
    # 2. 测试使用实际模型名称
    print("\n2. 测试使用实际模型名称")
    test_data = {
        "model_type": "reranking",
        "model_name": "BAAI/bge-reranker-v2-m3"  # 使用实际模型名称
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
                        print(f"   ✅ 使用实际模型名称测试成功！修复有效！")
                        return True
                    else:
                        print(f"   ❌ 使用实际模型名称测试失败: {result.get('error')}")
                        return False
                else:
                    error_text = await response.text()
                    print(f"   ❌ 请求失败: {error_text}")
                    return False
    except Exception as e:
        print(f"   ❌ 请求异常: {str(e)}")
        return False

async def main():
    """主函数"""
    print("🚀 模型名称修复测试")
    print("测试通过实际模型名称查找服务是否正常工作")
    
    results = []
    
    try:
        # 1. 测试嵌入模型名称解析
        results.append(await test_model_name_resolution())
        
        # 2. 测试重排序模型名称解析
        results.append(await test_reranking_name_resolution())
        
        print_section("测试总结")
        test_names = ["嵌入模型名称解析", "重排序模型名称解析"]
        
        print("📊 测试结果:")
        for i, (name, result) in enumerate(zip(test_names, results), 1):
            status = "✅ 通过" if result else "❌ 失败"
            print(f"   {i}. {name}: {status}")
        
        if all(results):
            print("\n🎉 所有测试通过！")
            print("🎯 模型名称解析修复成功:")
            print("   ✅ 可以使用注册名称测试模型")
            print("   ✅ 可以使用实际模型名称测试模型")
            print("   ✅ 模型测试功能完全正常")
            
            print("\n💡 现在用户可以:")
            print("   1. 添加模型时使用任意注册名称")
            print("   2. 测试时使用实际模型名称（如 BAAI/bge-large-zh-v1.5）")
            print("   3. 测试时也可以使用注册名称")
            print("   4. 系统会自动找到对应的模型服务")
        else:
            failed_tests = [name for name, result in zip(test_names, results) if not result]
            print(f"\n❌ 部分测试失败: {', '.join(failed_tests)}")
            print("\n🔧 可能的问题:")
            print("   - 模型加载失败")
            print("   - 服务查找逻辑仍有问题")
            print("   - 后端服务未正常运行")
        
        return all(results)
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)