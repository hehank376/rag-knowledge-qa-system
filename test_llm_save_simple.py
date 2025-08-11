#!/usr/bin/env python3
"""
简化的LLM配置保存测试
"""

import sys
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from fastapi.testclient import TestClient
from rag_system.api.main import app


def test_llm_only():
    """只测试LLM配置保存"""
    print("🧪 测试LLM配置保存")
    
    client = TestClient(app)
    
    # 读取保存前的配置
    config_file = Path("config/development.yaml")
    config_before = config_file.read_text(encoding='utf-8') if config_file.exists() else ""
    
    # 准备测试数据 - 只更新LLM配置
    timestamp = str(int(time.time()))
    test_config = {
        "llm": {
            "provider": "siliconflow",
            "model": "Qwen/Qwen2.5-7B-Instruct",
            "api_key": f"test-llm-save-{timestamp}",
            "base_url": "https://api.siliconflow.cn/v1",
            "temperature": 0.95,
            "max_tokens": 2500,
            "timeout": 180,
            "retry_attempts": 3
        }
    }
    
    print(f"测试数据: {test_config}")
    
    try:
        # 发送更新请求
        response = client.put("/config/llm", json=test_config["llm"])
        
        print(f"响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"响应数据: {data}")
            
            if data.get('success'):
                print("✅ API调用成功")
                
                # 等待文件写入完成
                time.sleep(2)
                
                # 读取保存后的配置
                config_after = config_file.read_text(encoding='utf-8') if config_file.exists() else ""
                
                if config_after != config_before:
                    print("✅ 配置文件已更新")
                    
                    # 检查具体的LLM配置是否保存
                    if test_config["llm"]["api_key"] in config_after:
                        print(f"✅ API密钥已保存: {test_config['llm']['api_key']}")
                    else:
                        print(f"❌ API密钥未保存: {test_config['llm']['api_key']}")
                    
                    if str(test_config["llm"]["temperature"]) in config_after:
                        print(f"✅ 温度参数已保存: {test_config['llm']['temperature']}")
                    else:
                        print(f"❌ 温度参数未保存: {test_config['llm']['temperature']}")
                    
                    if str(test_config["llm"]["max_tokens"]) in config_after:
                        print(f"✅ 最大令牌数已保存: {test_config['llm']['max_tokens']}")
                    else:
                        print(f"❌ 最大令牌数未保存: {test_config['llm']['max_tokens']}")
                    
                    # 显示LLM配置部分
                    print("\n📄 更新后的LLM配置:")
                    lines = config_after.split('\n')
                    in_llm = False
                    for line in lines:
                        if line.startswith('llm:'):
                            in_llm = True
                            print(line)
                        elif in_llm:
                            if line.startswith('  ') or line.strip() == '':
                                print(line)
                            else:
                                break
                    
                    return True
                else:
                    print("❌ 配置文件未更新")
                    return False
            else:
                print(f"❌ API调用失败: {data}")
                return False
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            print(f"响应内容: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 异常: {str(e)}")
        return False


if __name__ == "__main__":
    success = test_llm_only()
    if success:
        print("\n🎉 LLM配置保存测试通过！")
    else:
        print("\n⚠️ LLM配置保存测试失败！")