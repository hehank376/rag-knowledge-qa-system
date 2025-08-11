#!/usr/bin/env python3
"""
修复缓存和重排序配置问题的脚本
"""

import yaml
from pathlib import Path

def fix_config_issues():
    """修复配置文件中的问题"""
    config_path = Path("config/development.yaml")
    
    # 读取当前配置
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    print("🔧 修复配置问题...")
    
    # 1. 修复缓存配置
    print("1. 修复缓存配置")
    if 'cache' in config:
        # 启用缓存
        config['cache']['enabled'] = True
        print("   ✅ 启用缓存服务")
        
        # 修复Redis端口（如果需要）
        if 'redis' in config:
            # 检查Redis端口配置
            redis_url = config['redis'].get('url', '')
            if ':6380/' in redis_url:
                print(f"   ⚠️  当前Redis端口: 6380")
                print(f"   💡 如果Redis运行在默认端口6379，请修改配置")
                # 可以选择自动修复
                # config['redis']['url'] = redis_url.replace(':6380/', ':6379/')
    
    # 2. 修复重排序配置键名
    print("2. 修复重排序配置")
    if 'reranking' in config:
        reranking_config = config['reranking']
        
        # 检查配置键名
        if 'model' in reranking_config and 'model_name' not in reranking_config:
            # 添加model_name键，保持向后兼容
            reranking_config['model_name'] = reranking_config['model']
            print(f"   ✅ 添加model_name配置: {reranking_config['model']}")
        
        # 确保有正确的配置
        expected_model = "BAAI/bge-reranker-v2-m3"
        if reranking_config.get('model') != expected_model:
            reranking_config['model'] = expected_model
            reranking_config['model_name'] = expected_model
            print(f"   ✅ 设置重排序模型: {expected_model}")
    
    # 3. 保存修复后的配置
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    print("✅ 配置文件修复完成")
    return config

def check_redis_connection():
    """检查Redis连接"""
    print("\n🔍 检查Redis连接...")
    
    try:
        import redis
        
        # 尝试连接默认端口
        try:
            r = redis.Redis(host='localhost', port=6379, db=0, socket_connect_timeout=2)
            r.ping()
            print("   ✅ Redis (端口6379) 连接成功")
            return True, 6379
        except:
            pass
        
        # 尝试连接配置的端口
        try:
            r = redis.Redis(host='localhost', port=6380, db=0, socket_connect_timeout=2)
            r.ping()
            print("   ✅ Redis (端口6380) 连接成功")
            return True, 6380
        except:
            pass
        
        print("   ❌ Redis连接失败 - 请确保Redis服务正在运行")
        print("   💡 启动Redis: redis-server 或 docker run -d -p 6379:6379 redis")
        return False, None
        
    except ImportError:
        print("   ❌ Redis库未安装")
        print("   💡 安装Redis: pip install redis")
        return False, None

def create_reranking_service_fix():
    """创建重排序服务修复补丁"""
    print("\n🔧 创建重排序服务修复...")
    
    fix_content = '''
# 重排序服务配置修复

## 问题
重排序服务没有正确读取配置文件中的模型配置，而是使用了硬编码的默认模型。

## 修复方案
修改 `rag_system/services/reranking_service.py` 中的模型配置读取逻辑：

```python
# 原代码 (第23行左右)
self.model_name = self.config.get('model_name', 'cross-encoder/ms-marco-MiniLM-L-6-v2')

# 修复后的代码
self.model_name = self.config.get('model_name') or self.config.get('model', 'cross-encoder/ms-marco-MiniLM-L-6-v2')
```

## 配置文件确认
确保 config/development.yaml 中有正确的重排序配置：

```yaml
reranking:
  provider: siliconflow
  model: BAAI/bge-reranker-v2-m3
  model_name: BAAI/bge-reranker-v2-m3  # 添加这行以确保兼容性
  api_key: sk-test-update-123456789
  base_url: https://api.siliconflow.cn/v1
  batch_size: 32
  max_length: 512
  timeout: 30
```
'''
    
    with open('reranking_service_fix.md', 'w', encoding='utf-8') as f:
        f.write(fix_content)
    
    print("   ✅ 修复说明已保存到 reranking_service_fix.md")

def main():
    """主函数"""
    print("🚀 修复缓存和重排序配置问题")
    print("=" * 50)
    
    # 1. 修复配置文件
    config = fix_config_issues()
    
    # 2. 检查Redis连接
    redis_ok, redis_port = check_redis_connection()
    
    # 3. 创建重排序服务修复说明
    create_reranking_service_fix()
    
    # 4. 总结和建议
    print("\n" + "=" * 50)
    print("📋 修复总结:")
    print(f"   ✅ 配置文件已修复")
    print(f"   {'✅' if redis_ok else '❌'} Redis连接: {'正常' if redis_ok else '需要启动Redis服务'}")
    print(f"   ✅ 重排序修复说明已生成")
    
    print("\n💡 下一步操作:")
    if not redis_ok:
        print("   1. 启动Redis服务:")
        print("      - 本地安装: redis-server")
        print("      - Docker: docker run -d -p 6379:6379 redis")
    
    print("   2. 应用重排序服务修复 (见 reranking_service_fix.md)")
    print("   3. 重启应用服务")
    
    print("\n🎯 预期效果:")
    print("   - 缓存服务正常工作")
    print("   - 重排序使用配置的SiliconFlow模型")
    print("   - 不再出现HuggingFace连接错误")

if __name__ == "__main__":
    main()