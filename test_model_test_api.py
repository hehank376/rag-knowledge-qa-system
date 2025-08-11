#!/usr/bin/env python3
"""
测试模型测试API
检查测试嵌入模型和重排序模型的API是否正常工作
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

async def test_embedding_model():
    """测试嵌入模型"""
    print_section("测试嵌入模型API")
    
    base_url = "http://localhost:8000"
    
    # 构造测试数据
    test_data = {
        "model_type": "embedding",
        "model_name": "BAAI/bge-large-zh-v1.5"
    }
    
    print(f"1. 准备测试嵌入模型")
    print(f"   📤 模型类型: {test_data['model_type']}")
    print(f"   📤 模型名称: {test_data['model_name']}")
    
    # 发送测试请求
    try:
        async with aiohttp.ClientSession() as session:
            print(f"\n2. 发送POST请求到 {base_url}/models/test")
            async with session.post(
                f"{base_url}/models/test",
                json=test_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                print(f"   📋 响应状态码: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    print(f"   ✅ 测试嵌入模型成功")
                    print(f"   📋 响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
                    return True
                else:
                    error_text = await response.text()
                    print(f"   ❌ 测试嵌入模型失败 (状态码: {response.status})")
                    print(f"   📋 错误响应: {error_text}")
                    return False
                    
    except Exception as e:
        print(f"   ❌ 请求失败: {str(e)}")
        print(f"   📋 错误类型: {type(e).__name__}")
        return False

async def test_reranking_model():
    """测试重排序模型"""
    print_section("测试重排序模型API")
    
    base_url = "http://localhost:8000"
    
    # 构造测试数据
    test_data = {
        "model_type": "reranking",
        "model_name": "BAAI/bge-reranker-v2-m3"
    }
    
    print(f"1. 准备测试重排序模型")
    print(f"   📤 模型类型: {test_data['model_type']}")
    print(f"   📤 模型名称: {test_data['model_name']}")
    
    # 发送测试请求
    try:
        async with aiohttp.ClientSession() as session:
            print(f"\n2. 发送POST请求到 {base_url}/models/test")
            async with session.post(
                f"{base_url}/models/test",
                json=test_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                print(f"   📋 响应状态码: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    print(f"   ✅ 测试重排序模型成功")
                    print(f"   📋 响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
                    return True
                else:
                    error_text = await response.text()
                    print(f"   ❌ 测试重排序模型失败 (状态码: {response.status})")
                    print(f"   📋 错误响应: {error_text}")
                    return False
                    
    except Exception as e:
        print(f"   ❌ 请求失败: {str(e)}")
        print(f"   📋 错误类型: {type(e).__name__}")
        return False

async def test_invalid_model_type():
    """测试无效模型类型"""
    print_section("测试无效模型类型")
    
    base_url = "http://localhost:8000"
    
    # 构造测试数据
    test_data = {
        "model_type": "invalid_type",
        "model_name": "test-model"
    }
    
    print(f"1. 准备测试无效模型类型")
    print(f"   📤 模型类型: {test_data['model_type']}")
    print(f"   📤 模型名称: {test_data['model_name']}")
    
    # 发送测试请求
    try:
        async with aiohttp.ClientSession() as session:
            print(f"\n2. 发送POST请求到 {base_url}/models/test")
            async with session.post(
                f"{base_url}/models/test",
                json=test_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                print(f"   📋 响应状态码: {response.status}")
                
                if response.status == 422 or response.status == 400:
                    error_text = await response.text()
                    print(f"   ✅ 正确返回错误 (状态码: {response.status})")
                    print(f"   📋 错误响应: {error_text}")
                    return True
                else:
                    result_text = await response.text()
                    print(f"   ❌ 未正确处理无效类型 (状态码: {response.status})")
                    print(f"   📋 响应: {result_text}")
                    return False
                    
    except Exception as e:
        print(f"   ❌ 请求失败: {str(e)}")
        print(f"   📋 错误类型: {type(e).__name__}")
        return False

async def main():
    """主函数"""
    print("🚀 模型测试API测试")
    print("检查测试嵌入模型和重排序模型的API是否正常工作")
    
    results = []
    
    try:
        # 1. 测试嵌入模型
        results.append(await test_embedding_model())
        
        # 2. 测试重排序模型
        results.append(await test_reranking_model())
        
        # 3. 测试无效模型类型
        results.append(await test_invalid_model_type())
        
        print_section("测试总结")
        test_names = ["测试嵌入模型", "测试重排序模型", "测试无效模型类型"]
        
        print("📊 测试结果:")
        for i, (name, result) in enumerate(zip(test_names, results), 1):
            status = "✅ 通过" if result else "❌ 失败"
            print(f"   {i}. {name}: {status}")
        
        if all(results):
            print("\n🎉 所有测试通过！")
            print("🎯 模型测试API功能正常工作:")
            print("   ✅ 嵌入模型测试API正常工作")
            print("   ✅ 重排序模型测试API正常工作")
            print("   ✅ 错误处理正确")
            
            print("\n💡 前端应该能够:")
            print("   1. 成功测试嵌入模型")
            print("   2. 成功测试重排序模型")
            print("   3. 接收到正确的测试结果")
            print("   4. 显示适当的成功或错误消息")
        else:
            failed_tests = [name for name, result in zip(test_names, results) if not result]
            print(f"\n❌ 部分测试失败: {', '.join(failed_tests)}")
            print("\n🔧 可能的问题:")
            if not results[0]:
                print("   - 嵌入模型测试API有问题")
                print("   - 模型管理器初始化失败")
            if len(results) > 1 and not results[1]:
                print("   - 重排序模型测试API有问题")
                print("   - 重排序模型配置不正确")
            if len(results) > 2 and not results[2]:
                print("   - 错误处理逻辑有问题")
                print("   - 输入验证不正确")
        
        return all(results)
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)