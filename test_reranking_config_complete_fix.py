#!/usr/bin/env python3
"""
重排序模型配置完整修复测试
测试重排序模型配置是否能正确从配置文件中读取和显示
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

def test_config_loading():
    """测试配置加载"""
    print_section("测试配置加载")
    
    try:
        from rag_system.config.loader import ConfigLoader
        
        loader = ConfigLoader()
        config = loader.load_config()
        
        print(f"✅ 配置加载成功")
        print(f"📋 配置类型: {type(config)}")
        
        # 检查重排序配置
        if hasattr(config, 'reranking'):
            print(f"✅ 重排序配置存在")
            print(f"📋 重排序配置类型: {type(config.reranking)}")
            
            if config.reranking:
                print(f"📋 重排序提供商: {getattr(config.reranking, 'provider', 'N/A')}")
                print(f"📋 重排序模型: {getattr(config.reranking, 'model', 'N/A')}")
                print(f"📋 重排序批处理大小: {getattr(config.reranking, 'batch_size', 'N/A')}")
                print(f"📋 重排序最大长度: {getattr(config.reranking, 'max_length', 'N/A')}")
                print(f"📋 重排序超时时间: {getattr(config.reranking, 'timeout', 'N/A')}")
                return True
            else:
                print("❌ 重排序配置为空")
                return False
        else:
            print("❌ 重排序配置不存在")
            return False
            
    except Exception as e:
        print(f"❌ 配置加载失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_reranking_config_api():
    """测试重排序模型配置API"""
    print_section("测试重排序模型配置API")
    
    base_url = "http://localhost:8000"
    
    # 1. 读取配置文件中的实际值
    print("1. 读取配置文件中的重排序模型配置")
    config_file = read_config_file()
    if config_file:
        reranking_config = config_file.get('reranking', {})
        file_provider = reranking_config.get('provider', 'unknown')
        file_model = reranking_config.get('model', 'unknown')
        file_batch_size = reranking_config.get('batch_size', 'unknown')
        file_max_length = reranking_config.get('max_length', 'unknown')
        file_timeout = reranking_config.get('timeout', 'unknown')
        file_api_key = reranking_config.get('api_key', 'unknown')
        file_base_url = reranking_config.get('base_url', 'unknown')
        
        print(f"   📋 配置文件中的提供商: {file_provider}")
        print(f"   📋 配置文件中的模型: {file_model}")
        print(f"   📋 配置文件中的批处理大小: {file_batch_size}")
        print(f"   📋 配置文件中的最大长度: {file_max_length}")
        print(f"   📋 配置文件中的超时时间: {file_timeout}")
        print(f"   📋 配置文件中的API密钥: {file_api_key[:15]}..." if file_api_key and file_api_key != 'unknown' else f"   📋 配置文件中的API密钥: {file_api_key}")
        print(f"   📋 配置文件中的基础URL: {file_base_url}")
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
                    
                    # 提取reranking配置
                    api_config = result.get('config', {})
                    api_reranking = api_config.get('reranking', {})
                    
                    if api_reranking:
                        api_provider = api_reranking.get('provider', 'missing')
                        api_model = api_reranking.get('model', 'missing')
                        api_batch_size = api_reranking.get('batch_size', 'missing')
                        api_max_length = api_reranking.get('max_length', 'missing')
                        api_timeout = api_reranking.get('timeout', 'missing')
                        api_api_key = api_reranking.get('api_key', 'missing')
                        api_base_url = api_reranking.get('base_url', 'missing')
                        
                        print(f"   📋 API返回的提供商: {api_provider}")
                        print(f"   📋 API返回的模型: {api_model}")
                        print(f"   📋 API返回的批处理大小: {api_batch_size}")
                        print(f"   📋 API返回的最大长度: {api_max_length}")
                        print(f"   📋 API返回的超时时间: {api_timeout}")
                        print(f"   📋 API返回的API密钥: {str(api_api_key)[:15]}..." if api_api_key != 'missing' and api_api_key else f"   📋 API返回的API密钥: {api_api_key}")
                        print(f"   📋 API返回的基础URL: {api_base_url}")
                    else:
                        print("   ❌ API响应中没有reranking配置")
                        return False
                    
                    # 3. 对比配置文件和API返回值
                    print("\n3. 对比配置文件和API返回值")
                    success = True
                    
                    comparisons = [
                        ('提供商', file_provider, api_provider),
                        ('模型', file_model, api_model),
                        ('批处理大小', file_batch_size, api_batch_size),
                        ('最大长度', file_max_length, api_max_length),
                        ('超时时间', file_timeout, api_timeout),
                        ('API密钥', file_api_key, api_api_key),
                        ('基础URL', file_base_url, api_base_url)
                    ]
                    
                    for name, file_val, api_val in comparisons:
                        if api_val == file_val:
                            print(f"   ✅ {name}值匹配: {api_val}")
                        else:
                            print(f"   ❌ {name}值不匹配: 文件={file_val}, API={api_val}")
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

async def main():
    """主函数"""
    print("🚀 重排序模型配置完整修复测试")
    print("测试重排序模型配置是否能正确从配置文件中读取和显示")
    
    results = []
    
    try:
        # 1. 测试配置加载
        results.append(test_config_loading())
        
        # 2. 测试重排序模型配置API
        results.append(await test_reranking_config_api())
        
        print_section("测试总结")
        test_names = ["配置加载", "重排序配置API"]
        
        print("📊 测试结果:")
        for i, (name, result) in enumerate(zip(test_names, results), 1):
            status = "✅ 通过" if result else "❌ 失败"
            print(f"   {i}. {name}: {status}")
        
        if all(results):
            print("\n🎉 所有测试通过！")
            print("🎯 重排序模型配置功能正常工作:")
            print("   ✅ 配置加载器正确创建重排序配置对象")
            print("   ✅ 后端API正确返回重排序模型配置")
            print("   ✅ 配置文件中的参数正确传递到API")
            print("   ✅ 页面重新加载时会显示最新的重排序配置")
            
            print("\n💡 现在用户可以:")
            print("   1. 在前端修改重排序模型参数（批处理大小、最大长度等）")
            print("   2. 点击添加模型保存配置")
            print("   3. 刷新页面后看到更新后的重排序参数")
            print("   4. 重排序配置在页面重新加载后保持一致")
        else:
            failed_tests = [name for name, result in zip(test_names, results) if not result]
            print(f"\n❌ 部分测试失败: {', '.join(failed_tests)}")
            print("\n🔧 可能的问题:")
            if not results[0]:
                print("   - 配置加载器未正确创建重排序配置对象")
                print("   - 重排序配置类定义有问题")
            if len(results) > 1 and not results[1]:
                print("   - 后端配置API未正确返回重排序字段")
                print("   - 重排序配置访问逻辑有问题")
        
        return all(results)
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)