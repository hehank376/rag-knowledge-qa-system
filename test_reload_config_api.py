#!/usr/bin/env python3
"""
测试配置重新加载API
"""

import asyncio
import aiohttp
import yaml
from pathlib import Path


async def test_reload_api():
    """测试配置重新加载API"""
    base_url = "http://localhost:8000"
    
    # 1. 读取当前配置
    config_path = Path("config/development.yaml")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    original_dimensions = config['embeddings']['dimensions']
    test_dimensions = 9999
    
    print(f"原始维度: {original_dimensions}")
    print(f"测试维度: {test_dimensions}")
    
    # 2. 修改配置文件
    config['embeddings']['dimensions'] = test_dimensions
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, indent=2)
    
    print(f"已修改配置文件维度为: {test_dimensions}")
    
    try:
        async with aiohttp.ClientSession() as session:
            # 3. 测试配置API（修改前）
            async with session.get(f"{base_url}/config/") as response:
                if response.status == 200:
                    result = await response.json()
                    api_dimensions_before = result.get('config', {}).get('embeddings', {}).get('dimensions')
                    print(f"重新加载前API返回维度: {api_dimensions_before}")
                
            # 4. 调用重新加载API
            async with session.post(f"{base_url}/config/reload") as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"重新加载API调用成功: {result.get('message', 'No message')}")
                else:
                    print(f"重新加载API调用失败: {response.status}")
            
            # 5. 测试配置API（修改后）
            async with session.get(f"{base_url}/config/") as response:
                if response.status == 200:
                    result = await response.json()
                    api_dimensions_after = result.get('config', {}).get('embeddings', {}).get('dimensions')
                    print(f"重新加载后API返回维度: {api_dimensions_after}")
                    
                    if api_dimensions_after == test_dimensions:
                        print("✅ 配置重新加载成功！")
                    else:
                        print("❌ 配置重新加载失败")
    
    finally:
        # 恢复原始配置
        config['embeddings']['dimensions'] = original_dimensions
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, indent=2)
        print(f"已恢复原始维度: {original_dimensions}")


if __name__ == "__main__":
    asyncio.run(test_reload_api())