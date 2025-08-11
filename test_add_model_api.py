#!/usr/bin/env python3
"""
测试添加模型API
检查添加重排序模型的API是否正常工作
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

async def test_add_reranking_model():
    """测试添加重排序模型"""
    print_section("测试添加重排序模型API")
    
    base_url = "http://localhost:8000"
    
    # 构造测试数据
    model_data = {
        "model_type": "reranking",
        "name": "test_reranking_api",
        "provider": "siliconflow",
        "model_name": "BAAI/bge-reranker-v2-m3",
        "config": {
            "provider": "siliconflow",
            "batch_size": 16,
            "max_length": 256,
            "timeout": 60,
            "api_key": "sk-test-api-key",
            "base_url": "https://api.siliconflow.cn/v1"
        }
    }
    
    print(f"1. 准备添加重排序模型")
    print(f"   📤 模型类型: {model_data['model_type']}")
    print(f"   📤 模型名称: {model_data['name']}")
    print(f"   📤 提供商: {model_data['provider']}")
    print(f"   📤 批处理大小: {model_data['config']['batch_size']}")
    print(f"   📤 最大长度: {model_data['config']['max_length']}")
    
    # 发送添加模型请求
    try:
        async with aiohttp.ClientSession() as session:
            print(f"\n2. 发送POST请求到 {base_url}/models/add")
            async with session.post(
                f"{base_url}/models/add",
                json=model_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                print(f"   📋 响应状态码: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    print(f"   ✅ 添加重排序模型成功")
                    print(f"   📋 响应: {result.get('message', 'No message')}")
                    return True
                else:
                    error_text = await response.text()
                    print(f"   ❌ 添加重排序模型失败 (状态码: {response.status})")
                    print(f"   📋 错误响应: {error_text}")
                    return False
                    
    except aiohttp.ClientConnectorError as e:
        print(f"   ❌ 连接失败: {str(e)}")
        print(f"   💡 请确保后端服务正在运行: python -m rag_system.api.main")
        return False
    except Exception as e:
        print(f"   ❌ 请求失败: {str(e)}")
        print(f"   📋 错误类型: {type(e).__name__}")
        return False

async def test_api_endpoints():
    """测试API端点是否可访问"""
    print_section("测试API端点可访问性")
    
    base_url = "http://localhost:8000"
    endpoints = [
        "/",
        "/config/",
        "/models/add"
    ]
    
    results = []
    
    try:
        async with aiohttp.ClientSession() as session:
            for endpoint in endpoints:
                url = f"{base_url}{endpoint}"
                print(f"\n测试端点: {url}")
                
                try:
                    if endpoint == "/models/add":
                        # POST请求需要数据
                        async with session.post(url, json={}) as response:
                            print(f"   📋 状态码: {response.status}")
                            if response.status in [200, 400, 422]:  # 400/422是预期的，因为数据不完整
                                print(f"   ✅ 端点可访问")
                                results.append(True)
                            else:
                                print(f"   ❌ 端点不可访问")
                                results.append(False)
                    else:
                        # GET请求
                        async with session.get(url) as response:
                            print(f"   📋 状态码: {response.status}")
                            if response.status == 200:
                                print(f"   ✅ 端点可访问")
                                results.append(True)
                            else:
                                print(f"   ❌ 端点不可访问")
                                results.append(False)
                                
                except Exception as e:
                    print(f"   ❌ 请求失败: {str(e)}")
                    results.append(False)
                    
    except Exception as e:
        print(f"❌ 会话创建失败: {str(e)}")
        return False
    
    return all(results)

async def test_cors_headers():
    """测试CORS头部"""
    print_section("测试CORS配置")
    
    base_url = "http://localhost:8000"
    
    try:
        async with aiohttp.ClientSession() as session:
            # 发送OPTIONS请求测试CORS
            async with session.options(
                f"{base_url}/models/add",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Content-Type"
                }
            ) as response:
                print(f"   📋 OPTIONS响应状态码: {response.status}")
                
                cors_headers = {
                    "Access-Control-Allow-Origin": response.headers.get("Access-Control-Allow-Origin"),
                    "Access-Control-Allow-Methods": response.headers.get("Access-Control-Allow-Methods"),
                    "Access-Control-Allow-Headers": response.headers.get("Access-Control-Allow-Headers")
                }
                
                print(f"   📋 CORS头部:")
                for header, value in cors_headers.items():
                    print(f"      {header}: {value}")
                
                return response.status in [200, 204]
                
    except Exception as e:
        print(f"   ❌ CORS测试失败: {str(e)}")
        return False

async def main():
    """主函数"""
    print("🚀 添加模型API测试")
    print("检查添加重排序模型的API是否正常工作")
    
    results = []
    
    try:
        # 1. 测试API端点可访问性
        results.append(await test_api_endpoints())
        
        # 2. 测试CORS配置
        results.append(await test_cors_headers())
        
        # 3. 测试添加重排序模型
        results.append(await test_add_reranking_model())
        
        print_section("测试总结")
        test_names = ["API端点可访问性", "CORS配置", "添加重排序模型"]
        
        print("📊 测试结果:")
        for i, (name, result) in enumerate(zip(test_names, results), 1):
            status = "✅ 通过" if result else "❌ 失败"
            print(f"   {i}. {name}: {status}")
        
        if all(results):
            print("\n🎉 所有测试通过！")
            print("🎯 添加模型API功能正常工作:")
            print("   ✅ API端点可以正常访问")
            print("   ✅ CORS配置正确")
            print("   ✅ 添加重排序模型API正常工作")
            
            print("\n💡 前端应该能够:")
            print("   1. 成功发送添加模型请求")
            print("   2. 接收到正确的响应")
            print("   3. 显示成功或错误消息")
        else:
            failed_tests = [name for name, result in zip(test_names, results) if not result]
            print(f"\n❌ 部分测试失败: {', '.join(failed_tests)}")
            print("\n🔧 可能的问题:")
            if not results[0]:
                print("   - 后端服务未正常运行")
                print("   - API路由配置有问题")
            if len(results) > 1 and not results[1]:
                print("   - CORS配置不正确")
                print("   - 前端跨域请求被阻止")
            if len(results) > 2 and not results[2]:
                print("   - 添加模型API逻辑有问题")
                print("   - 请求数据格式不正确")
        
        return all(results)
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)