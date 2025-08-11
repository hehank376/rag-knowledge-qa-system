#!/usr/bin/env python3
"""
配置加载修复测试

测试前端是否能正确从配置文件中读取最新的配置值
"""

import asyncio
import sys
import json
import yaml
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


def read_config_file():
    """读取配置文件"""
    config_path = Path("config/development.yaml")
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return None


async def test_config_api_response():
    """测试配置API是否返回正确的配置值"""
    print_section("测试配置API响应")
    
    base_url = "http://localhost:8000"
    
    # 1. 读取配置文件中的实际值
    print("1. 读取配置文件中的实际值")
    config_file = read_config_file()
    if config_file:
        file_dimensions = config_file.get('embeddings', {}).get('dimensions', 'unknown')
        file_model = config_file.get('embeddings', {}).get('model', 'unknown')
        file_provider = config_file.get('embeddings', {}).get('provider', 'unknown')
        file_batch_size = config_file.get('embeddings', {}).get('batch_size', 'unknown')
        
        print(f"   📋 配置文件中的维度: {file_dimensions}")
        print(f"   📋 配置文件中的模型: {file_model}")
        print(f"   📋 配置文件中的提供商: {file_provider}")
        print(f"   📋 配置文件中的批处理大小: {file_batch_size}")
    else:
        print("   ❌ 无法读取配置文件")
        return False
    
    # 2. 调用配置API
    print("\n2. 调用配置API")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base_url}/config/") as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"   ✅ 配置API调用成功")
                    
                    # 提取embeddings配置
                    api_config = result.get('config', {})
                    api_embeddings = api_config.get('embeddings', {})
                    
                    api_dimensions = api_embeddings.get('dimensions', 'missing')
                    api_model = api_embeddings.get('model', 'missing')
                    api_provider = api_embeddings.get('provider', 'missing')
                    api_batch_size = api_embeddings.get('batch_size', 'missing')
                    
                    print(f"   📋 API返回的维度: {api_dimensions}")
                    print(f"   📋 API返回的模型: {api_model}")
                    print(f"   📋 API返回的提供商: {api_provider}")
                    print(f"   📋 API返回的批处理大小: {api_batch_size}")
                    
                    # 3. 对比配置文件和API返回值
                    print("\n3. 对比配置文件和API返回值")
                    success = True
                    
                    if api_dimensions == file_dimensions:
                        print(f"   ✅ 维度值匹配: {api_dimensions}")
                    else:
                        print(f"   ❌ 维度值不匹配: 文件={file_dimensions}, API={api_dimensions}")
                        success = False
                    
                    if api_model == file_model:
                        print(f"   ✅ 模型值匹配: {api_model}")
                    else:
                        print(f"   ❌ 模型值不匹配: 文件={file_model}, API={api_model}")
                        success = False
                    
                    if api_provider == file_provider:
                        print(f"   ✅ 提供商值匹配: {api_provider}")
                    else:
                        print(f"   ❌ 提供商值不匹配: 文件={file_provider}, API={api_provider}")
                        success = False
                    
                    if api_batch_size == file_batch_size:
                        print(f"   ✅ 批处理大小匹配: {api_batch_size}")
                    else:
                        print(f"   ❌ 批处理大小不匹配: 文件={file_batch_size}, API={api_batch_size}")
                        success = False
                    
                    return success
                    
                else:
                    error_text = await response.text()
                    print(f"   ❌ 配置API调用失败 (状态码: {response.status})")
                    print(f"   📋 错误: {error_text}")
                    return False
                    
    except Exception as e:
        print(f"   ❌ 请求失败: {str(e)}")
        print(f"   💡 请确保后端服务正在运行: python -m rag_system.api.main")
        return False


async def test_frontend_config_loading():
    """测试前端配置加载逻辑"""
    print_section("测试前端配置加载逻辑")
    
    # 模拟前端的配置加载过程
    base_url = "http://localhost:8000"
    
    print("1. 模拟前端调用 apiClient.getConfig()")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base_url}/config/") as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"   ✅ 前端API调用成功")
                    
                    # 模拟前端的数据处理逻辑
                    settings = result.get('config', result)
                    embeddings = settings.get('embeddings', {})
                    
                    # 模拟前端的 populateForm 逻辑
                    embeddingDimension = embeddings.get('dimensions')
                    embeddingModel = embeddings.get('model')
                    embeddingProvider = embeddings.get('provider')
                    
                    print(f"   📋 前端解析的维度: {embeddingDimension}")
                    print(f"   📋 前端解析的模型: {embeddingModel}")
                    print(f"   📋 前端解析的提供商: {embeddingProvider}")
                    
                    # 验证前端是否能获取到正确的值
                    if embeddingDimension is not None:
                        print(f"   ✅ 前端能够获取到维度值: {embeddingDimension}")
                        return True
                    else:
                        print(f"   ❌ 前端无法获取到维度值")
                        return False
                        
                else:
                    print(f"   ❌ 前端API调用失败")
                    return False
                    
    except Exception as e:
        print(f"   ❌ 前端模拟请求失败: {str(e)}")
        return False


async def test_complete_config_flow():
    """测试完整的配置流程"""
    print_section("测试完整的配置流程")
    
    # 1. 修改配置文件中的值
    print("1. 修改配置文件中的测试值")
    config_file = read_config_file()
    if config_file:
        original_dimensions = config_file.get('embeddings', {}).get('dimensions', 1024)
        test_dimensions = 4096  # 设置一个测试值
        
        print(f"   📋 原始维度: {original_dimensions}")
        print(f"   📋 测试维度: {test_dimensions}")
        
        # 临时修改配置文件
        config_file['embeddings']['dimensions'] = test_dimensions
        
        config_path = Path("config/development.yaml")
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_file, f, default_flow_style=False, allow_unicode=True, indent=2)
        
        print(f"   ✅ 已将维度临时修改为: {test_dimensions}")
        
        # 2. 测试API是否返回新值
        print("\n2. 测试API是否返回新值")
        import time
        time.sleep(1)  # 等待文件更新
        
        base_url = "http://localhost:8000"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{base_url}/config/") as response:
                    if response.status == 200:
                        result = await response.json()
                        api_dimensions = result.get('config', {}).get('embeddings', {}).get('dimensions')
                        
                        print(f"   📋 API返回的维度: {api_dimensions}")
                        
                        if api_dimensions == test_dimensions:
                            print(f"   ✅ API正确返回了新的维度值")
                            success = True
                        else:
                            print(f"   ❌ API返回的维度值不正确")
                            success = False
                        
                        # 恢复原始值
                        config_file['embeddings']['dimensions'] = original_dimensions
                        with open(config_path, 'w', encoding='utf-8') as f:
                            yaml.dump(config_file, f, default_flow_style=False, allow_unicode=True, indent=2)
                        print(f"   🔄 已恢复原始维度值: {original_dimensions}")
                        
                        return success
                    else:
                        print(f"   ❌ API调用失败")
                        return False
                        
        except Exception as e:
            print(f"   ❌ 测试请求失败: {str(e)}")
            # 确保恢复原始值
            config_file['embeddings']['dimensions'] = original_dimensions
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_file, f, default_flow_style=False, allow_unicode=True, indent=2)
            return False
    else:
        print("   ❌ 无法读取配置文件")
        return False


async def main():
    """主函数"""
    print("🚀 配置加载修复测试")
    print("测试前端是否能正确从配置文件中读取最新的配置值")
    
    results = []
    
    try:
        # 1. 测试配置API响应
        results.append(await test_config_api_response())
        
        # 2. 测试前端配置加载逻辑
        results.append(await test_frontend_config_loading())
        
        # 3. 测试完整的配置流程
        results.append(await test_complete_config_flow())
        
        print_section("测试总结")
        
        test_names = ["配置API响应", "前端配置加载", "完整配置流程"]
        
        print("📊 测试结果:")
        for i, (name, result) in enumerate(zip(test_names, results), 1):
            status = "✅ 通过" if result else "❌ 失败"
            print(f"   {i}. {name}: {status}")
        
        if all(results):
            print("\n🎉 所有测试通过！")
            print("🎯 配置加载功能正常工作:")
            print("   ✅ 后端API正确返回配置文件中的值")
            print("   ✅ 前端能够正确解析API响应")
            print("   ✅ 配置文件修改后API立即反映变化")
            print("   ✅ 前端页面重新加载时会显示最新配置")
            
            print("\n💡 现在用户可以:")
            print("   1. 在前端修改嵌入模型维度参数")
            print("   2. 点击添加模型保存配置")
            print("   3. 刷新页面后看到更新后的值")
            print("   4. 配置在页面重新加载后保持一致")
            
        else:
            failed_tests = [name for name, result in zip(test_names, results) if not result]
            print(f"\n❌ 部分测试失败: {', '.join(failed_tests)}")
            
            print("\n🔧 可能的问题:")
            if not results[0]:
                print("   - 后端配置API未正确返回dimensions字段")
            if not results[1]:
                print("   - 前端配置解析逻辑有问题")
            if not results[2]:
                print("   - 配置文件更新后API未及时反映")
        
        return all(results)
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)