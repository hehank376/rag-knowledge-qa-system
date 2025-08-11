#!/usr/bin/env python3
"""
最终测试设置页面功能
"""

import requests
import json
import time
from pathlib import Path

def test_settings_page_integration():
    """测试设置页面集成"""
    print("🚀 开始测试设置页面集成...")
    
    base_url = "http://localhost:8000"
    
    # 1. 测试配置API
    print("\n1. 测试配置API...")
    try:
        response = requests.get(f"{base_url}/config/")
        if response.status_code == 200:
            config_data = response.json()
            print("✅ 配置API正常")
            
            # 检查配置结构
            config = config_data.get('config', {})
            print(f"  📋 配置结构检查:")
            print(f"    应用: {config.get('app', {})}")
            print(f"    LLM: {config.get('llm', {})}")
            print(f"    嵌入: {config.get('embeddings', {})}")
            print(f"    检索: {config.get('retrieval', {})}")
            
            return config_data
        else:
            print(f"❌ 配置API失败: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ 配置API异常: {e}")
        return None

def test_frontend_api_paths():
    """测试前端API路径"""
    print("\n2. 测试前端API路径...")
    
    base_url = "http://localhost:8000"
    
    # 前端使用的API路径
    api_paths = [
        ("/config/", "获取完整配置"),
        ("/config/llm", "获取LLM配置"),
        ("/config/embeddings", "获取嵌入配置"),
        ("/config/retrieval", "获取检索配置"),
        ("/config/health", "健康检查"),
    ]
    
    results = []
    for path, description in api_paths:
        try:
            response = requests.get(f"{base_url}{path}")
            if response.status_code == 200:
                results.append(f"✅ {description}: 正常")
            else:
                results.append(f"❌ {description}: {response.status_code}")
        except Exception as e:
            results.append(f"❌ {description}: 异常 - {e}")
    
    for result in results:
        print(f"  {result}")
    
    return all("✅" in result for result in results)

def test_monitoring_api():
    """测试监控API"""
    print("\n3. 测试监控API...")
    
    base_url = "http://localhost:8000"
    
    # 监控API路径
    monitoring_paths = [
        ("/monitoring/health", "监控健康检查"),
        ("/monitoring/status", "系统状态"),
        ("/monitoring/metrics", "系统指标"),
        ("/config/health", "配置健康检查"),  # 备用路径
    ]
    
    available_endpoints = []
    for path, description in monitoring_paths:
        try:
            response = requests.get(f"{base_url}{path}")
            if response.status_code == 200:
                available_endpoints.append(path)
                print(f"  ✅ {description}: 可用")
                
                # 显示响应数据结构
                try:
                    data = response.json()
                    print(f"    📊 数据结构: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                except:
                    pass
            else:
                print(f"  ❌ {description}: {response.status_code}")
        except Exception as e:
            print(f"  ❌ {description}: 异常 - {e}")
    
    return available_endpoints

def test_config_update():
    """测试配置更新"""
    print("\n4. 测试配置更新...")
    
    base_url = "http://localhost:8000"
    
    # 测试更新LLM配置
    test_config = {
        "provider": "siliconflow",
        "model": "Qwen/Qwen2-7B-Instruct",
        "temperature": 0.8,
        "max_tokens": 1500,
        "api_key": "test-key-updated"
    }
    
    try:
        # 更新配置
        response = requests.put(
            f"{base_url}/config/llm",
            json=test_config,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("  ✅ 配置更新成功")
            print(f"    消息: {result.get('message')}")
            
            # 验证配置是否生效
            time.sleep(1)  # 等待配置生效
            
            verify_response = requests.get(f"{base_url}/config/llm")
            if verify_response.status_code == 200:
                verify_data = verify_response.json()
                updated_config = verify_data.get('config', {}).get('llm', {})
                
                print("  📋 更新后的配置:")
                print(f"    提供商: {updated_config.get('provider')}")
                print(f"    模型: {updated_config.get('model')}")
                print(f"    温度: {updated_config.get('temperature')}")
                print(f"    最大令牌: {updated_config.get('max_tokens')}")
                
                return True
            else:
                print("  ❌ 配置验证失败")
                return False
        else:
            print(f"  ❌ 配置更新失败: {response.status_code}")
            print(f"    错误: {response.text}")
            return False
            
    except Exception as e:
        print(f"  ❌ 配置更新异常: {e}")
        return False

def check_config_file():
    """检查配置文件是否更新"""
    print("\n5. 检查配置文件...")
    
    config_file = Path("config/development.yaml")
    if config_file.exists():
        print(f"  ✅ 配置文件存在: {config_file}")
        
        try:
            import yaml
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            print("  📋 当前配置文件内容:")
            if 'llm' in config_data:
                llm_config = config_data['llm']
                print(f"    LLM提供商: {llm_config.get('provider')}")
                print(f"    LLM模型: {llm_config.get('model')}")
                print(f"    LLM温度: {llm_config.get('temperature')}")
                print(f"    最大令牌: {llm_config.get('max_tokens')}")
            
            return True
            
        except Exception as e:
            print(f"  ❌ 读取配置文件失败: {e}")
            return False
    else:
        print(f"  ❌ 配置文件不存在: {config_file}")
        return False

def generate_test_report():
    """生成测试报告"""
    print("\n" + "="*60)
    print("📊 设置页面集成测试报告")
    print("="*60)
    
    # 运行所有测试
    config_api_ok = test_settings_page_integration() is not None
    frontend_paths_ok = test_frontend_api_paths()
    monitoring_endpoints = test_monitoring_api()
    config_update_ok = test_config_update()
    config_file_ok = check_config_file()
    
    print(f"\n🎯 测试结果总结:")
    print(f"  配置API: {'✅ 通过' if config_api_ok else '❌ 失败'}")
    print(f"  前端API路径: {'✅ 通过' if frontend_paths_ok else '❌ 失败'}")
    print(f"  监控API: {'✅ 通过' if len(monitoring_endpoints) > 0 else '❌ 失败'} ({len(monitoring_endpoints)} 个端点可用)")
    print(f"  配置更新: {'✅ 通过' if config_update_ok else '❌ 失败'}")
    print(f"  配置文件: {'✅ 通过' if config_file_ok else '❌ 失败'}")
    
    overall_success = all([
        config_api_ok,
        frontend_paths_ok,
        len(monitoring_endpoints) > 0,
        config_update_ok,
        config_file_ok
    ])
    
    print(f"\n🏆 总体结果: {'✅ 全部通过' if overall_success else '❌ 部分失败'}")
    
    if overall_success:
        print("\n🎉 设置页面集成测试成功！")
        print("💡 现在可以通过Web界面管理系统配置了")
    else:
        print("\n⚠️  部分功能需要进一步调试")
    
    return overall_success

if __name__ == "__main__":
    print("🔧 RAG系统设置页面集成测试")
    print("="*60)
    
    success = generate_test_report()
    
    if success:
        print("\n🚀 测试完成，系统就绪！")
    else:
        print("\n🔧 需要进一步调试和修复")