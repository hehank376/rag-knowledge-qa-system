#!/usr/bin/env python3
"""
完整配置同步测试

测试从添加模型到前端显示的完整流程
"""

import asyncio
import aiohttp
import yaml
from pathlib import Path


async def test_complete_config_sync():
    """测试完整的配置同步流程"""
    base_url = "http://localhost:8000"
    
    print("🚀 完整配置同步测试")
    print("测试从添加模型到前端显示的完整流程")
    
    # 1. 读取当前配置文件
    print("\n1. 读取当前配置文件")
    config_path = Path("config/development.yaml")
    with open(config_path, 'r', encoding='utf-8') as f:
        original_config = yaml.safe_load(f)
    
    original_dimensions = original_config.get('embeddings', {}).get('dimensions', 1024)
    print(f"   📋 当前配置文件维度: {original_dimensions}")
    
    # 2. 调用添加模型API
    print("\n2. 调用添加模型API")
    test_dimensions = 3072  # 新的测试维度
    
    model_data = {
        "model_type": "embedding",
        "name": "test_sync_model",
        "provider": "siliconflow",
        "model_name": "BAAI/bge-large-zh-v1.5",
        "config": {
            "provider": "siliconflow",
            "dimensions": test_dimensions,  # 关键：新的维度值
            "batch_size": 64,
            "chunk_size": 2000,
            "chunk_overlap": 100,
            "timeout": 180,
            "api_key": "sk-test-sync-key",
            "base_url": "https://api.siliconflow.cn/v1"
        }
    }
    
    print(f"   📤 准备添加模型，维度: {test_dimensions}")
    
    try:
        async with aiohttp.ClientSession() as session:
            # 调用添加模型API
            async with session.post(
                f"{base_url}/models/add",
                json=model_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"   ✅ 添加模型成功: {result.get('message', 'No message')}")
                else:
                    error_text = await response.text()
                    print(f"   ❌ 添加模型失败: {error_text}")
                    return False
            
            # 3. 验证配置文件是否更新
            print("\n3. 验证配置文件是否更新")
            import time
            time.sleep(1)  # 等待文件写入
            
            with open(config_path, 'r', encoding='utf-8') as f:
                updated_config = yaml.safe_load(f)
            
            file_dimensions = updated_config.get('embeddings', {}).get('dimensions', 'unknown')
            print(f"   📋 配置文件中的维度: {file_dimensions}")
            
            if file_dimensions == test_dimensions:
                print(f"   ✅ 配置文件已正确更新")
            else:
                print(f"   ❌ 配置文件未正确更新")
                return False
            
            # 4. 验证配置API是否返回新值
            print("\n4. 验证配置API是否返回新值")
            async with session.get(f"{base_url}/config/") as response:
                if response.status == 200:
                    result = await response.json()
                    api_dimensions = result.get('config', {}).get('embeddings', {}).get('dimensions')
                    print(f"   📋 配置API返回的维度: {api_dimensions}")
                    
                    if api_dimensions == test_dimensions:
                        print(f"   ✅ 配置API返回正确的新值")
                    else:
                        print(f"   ❌ 配置API返回的值不正确")
                        print(f"   📋 期望: {test_dimensions}, 实际: {api_dimensions}")
                        return False
                else:
                    print(f"   ❌ 配置API调用失败")
                    return False
            
            # 5. 模拟前端页面重新加载
            print("\n5. 模拟前端页面重新加载")
            async with session.get(f"{base_url}/config/") as response:
                if response.status == 200:
                    result = await response.json()
                    settings = result.get('config', result)
                    
                    # 模拟前端的数据解析
                    frontend_dimensions = settings.get('embeddings', {}).get('dimensions')
                    frontend_model = settings.get('embeddings', {}).get('model')
                    frontend_provider = settings.get('embeddings', {}).get('provider')
                    frontend_batch_size = settings.get('embeddings', {}).get('batch_size')
                    
                    print(f"   📋 前端解析的维度: {frontend_dimensions}")
                    print(f"   📋 前端解析的模型: {frontend_model}")
                    print(f"   📋 前端解析的提供商: {frontend_provider}")
                    print(f"   📋 前端解析的批处理大小: {frontend_batch_size}")
                    
                    # 验证前端是否能获取到正确的值
                    success = True
                    if frontend_dimensions == test_dimensions:
                        print(f"   ✅ 前端能获取到正确的维度值")
                    else:
                        print(f"   ❌ 前端获取的维度值不正确")
                        success = False
                    
                    if frontend_model == model_data['model_name']:
                        print(f"   ✅ 前端能获取到正确的模型名称")
                    else:
                        print(f"   ❌ 前端获取的模型名称不正确")
                        success = False
                    
                    if frontend_batch_size == model_data['config']['batch_size']:
                        print(f"   ✅ 前端能获取到正确的批处理大小")
                    else:
                        print(f"   ❌ 前端获取的批处理大小不正确")
                        success = False
                    
                    return success
                else:
                    print(f"   ❌ 前端配置加载失败")
                    return False
                    
    except Exception as e:
        print(f"   ❌ 测试过程中出现错误: {str(e)}")
        return False


async def main():
    """主函数"""
    try:
        success = await test_complete_config_sync()
        
        print("\n" + "="*60)
        print("🔍 测试总结")
        print("="*60)
        
        if success:
            print("🎉 完整配置同步测试通过！")
            print("🎯 配置同步流程正常工作:")
            print("   ✅ 添加模型API正确保存配置到文件")
            print("   ✅ 配置缓存正确重新加载")
            print("   ✅ 配置API返回最新值")
            print("   ✅ 前端页面重新加载时显示正确值")
            
            print("\n💡 用户现在可以:")
            print("   1. 在前端修改嵌入模型参数")
            print("   2. 点击添加模型保存配置")
            print("   3. 刷新页面后看到更新后的值")
            print("   4. 所有参数都与配置文件保持同步")
            
        else:
            print("❌ 完整配置同步测试失败")
            print("🔧 需要进一步检查:")
            print("   - 模型添加API的配置保存逻辑")
            print("   - 配置缓存的重新加载机制")
            print("   - 前端配置解析逻辑")
        
        return success
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)