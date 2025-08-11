#!/usr/bin/env python3
"""
测试设置页面修复效果
"""

import requests
import json
import sys
from pathlib import Path

def test_config_get():
    """测试配置获取"""
    print("🔍 测试配置获取...")
    
    try:
        response = requests.get("http://localhost:8000/config/")
        if response.status_code == 200:
            config_data = response.json()
            print("✅ 配置获取成功")
            
            # 检查关键配置项
            config = config_data.get('config', {})
            
            print(f"📋 配置内容:")
            print(f"  应用名称: {config.get('app', {}).get('name')}")
            print(f"  LLM提供商: {config.get('llm', {}).get('provider')}")
            print(f"  LLM模型: {config.get('llm', {}).get('model')}")
            print(f"  LLM温度: {config.get('llm', {}).get('temperature')}")
            print(f"  嵌入提供商: {config.get('embeddings', {}).get('provider')}")
            print(f"  嵌入模型: {config.get('embeddings', {}).get('model')}")
            print(f"  块大小: {config.get('embeddings', {}).get('chunk_size')}")
            
            return config_data
        else:
            print(f"❌ 配置获取失败: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return None

def test_config_update():
    """测试配置更新"""
    print("\n🔍 测试配置更新...")
    
    # 测试更新LLM配置
    llm_config = {
        "provider": "siliconflow",
        "model": "Qwen/Qwen2-7B-Instruct",
        "temperature": 0.7,
        "max_tokens": 2000,
        "api_key": "test-api-key"
    }
    
    try:
        response = requests.put(
            "http://localhost:8000/config/llm",
            json=llm_config,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ LLM配置更新成功")
            print(f"  消息: {result.get('message')}")
            return True
        else:
            print(f"❌ LLM配置更新失败: {response.status_code}")
            print(f"  错误: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 更新请求异常: {e}")
        return False

def test_config_validation():
    """测试配置验证"""
    print("\n🔍 测试配置验证...")
    
    # 测试有效配置
    valid_config = {
        "provider": "siliconflow",
        "model": "Qwen/Qwen2-7B-Instruct",
        "temperature": 0.7,
        "max_tokens": 2000
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/config/validate",
            json={"section": "llm", "config": valid_config},
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 配置验证成功")
            print(f"  有效: {result.get('valid')}")
            if result.get('errors'):
                print(f"  错误: {result.get('errors')}")
            if result.get('warnings'):
                print(f"  警告: {result.get('warnings')}")
            return True
        else:
            print(f"❌ 配置验证失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 验证请求异常: {e}")
        return False

def check_config_file():
    """检查配置文件内容"""
    print("\n🔍 检查配置文件...")
    
    config_file = Path("config/development.yaml")
    if config_file.exists():
        print(f"✅ 配置文件存在: {config_file}")
        
        try:
            import yaml
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            print("📋 配置文件内容:")
            if 'llm' in config_data:
                llm_config = config_data['llm']
                print(f"  LLM提供商: {llm_config.get('provider')}")
                print(f"  LLM模型: {llm_config.get('model')}")
                print(f"  LLM温度: {llm_config.get('temperature')}")
            
            if 'embeddings' in config_data:
                emb_config = config_data['embeddings']
                print(f"  嵌入提供商: {emb_config.get('provider')}")
                print(f"  嵌入模型: {emb_config.get('model')}")
                print(f"  块大小: {emb_config.get('chunk_size')}")
            
            return True
            
        except Exception as e:
            print(f"❌ 读取配置文件失败: {e}")
            return False
    else:
        print(f"❌ 配置文件不存在: {config_file}")
        return False

if __name__ == "__main__":
    print("🚀 开始测试设置页面修复效果...")
    
    # 检查配置文件
    check_config_file()
    
    # 测试配置获取
    config_data = test_config_get()
    
    # 测试配置验证
    test_config_validation()
    
    # 测试配置更新
    test_config_update()
    
    # 再次检查配置文件
    print("\n" + "="*50)
    print("更新后的配置文件:")
    check_config_file()
    
    print("\n🏁 测试完成!")
    print("\n💡 现在可以打开浏览器访问系统设置页面测试界面功能")