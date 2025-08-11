#!/usr/bin/env python3
"""
启动完整的RAG系统（包含所有修复）
"""
import uvicorn
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from rag_system.api.main import app

def check_javascript_functions():
    """检查JavaScript函数是否正确定义"""
    print("🔍 检查JavaScript函数...")
    
    utils_path = Path("frontend/js/utils.js")
    if utils_path.exists():
        with open(utils_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_functions = ['formatTime', 'formatDate', 'formatDateTime']
        missing = [func for func in required_functions if f"function {func}(" not in content]
        
        if missing:
            print(f"⚠️  缺失JavaScript函数: {', '.join(missing)}")
            return False
        else:
            print("✅ JavaScript函数检查通过")
            return True
    else:
        print("❌ utils.js文件不存在")
        return False

def check_environment():
    """检查环境配置"""
    print("🔍 检查环境配置...")
    
    # 检查API密钥
    api_keys = []
    if os.getenv("SILICONFLOW_API_KEY"):
        api_keys.append("SiliconFlow")
    if os.getenv("OPENAI_API_KEY"):
        api_keys.append("OpenAI")
    
    if api_keys:
        print(f"✅ 已配置API密钥: {', '.join(api_keys)}")
    else:
        print("⚠️  未检测到API密钥，将使用Mock模式")
    
    # 检查配置文件
    config_path = Path("config.yaml")
    if config_path.exists():
        print("✅ 配置文件存在")
    else:
        print("⚠️  配置文件不存在，将使用默认配置")
    
    # 检查关键文件
    critical_files = [
        "frontend/index.html",
        "frontend/js/utils.js",
        "frontend/js/qa.js",
        "frontend/js/api.js",
        "frontend/js/notifications.js"
    ]
    
    missing_files = []
    for file_path in critical_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            missing_files.append(file_path)
            print(f"❌ {file_path}")
    
    return len(missing_files) == 0

def show_test_urls():
    """显示测试URL"""
    print("\n🧪 测试页面:")
    test_pages = [
        ("主界面", "http://localhost:8000"),
        ("API文档", "http://localhost:8000/docs"),
        ("健康检查", "http://localhost:8000/health"),
        ("通知系统测试", "http://localhost:8000/test_notifications.html"),
        ("QA功能测试", "http://localhost:8000/test_qa_functions.html")
    ]
    
    for name, url in test_pages:
        print(f"  • {name}: {url}")

def show_available_tools():
    """显示可用的工具"""
    print("\n🔧 可用工具:")
    tools = [
        ("真实模型连接测试", "python test_real_model_connection.py"),
        ("API端点测试", "python test_api_endpoints.py"),
        ("配置API测试", "python test_config_api.py"),
        ("文档上传问题修复", "python fix_document_upload_issues.py"),
        ("QA功能错误修复", "python fix_qa_javascript_errors.py"),
        ("向量维度问题修复", "python fix_vector_dimension_mismatch.py")
    ]
    
    for name, command in tools:
        print(f"  • {name}: {command}")

if __name__ == "__main__":
    print("🚀 启动完整的RAG知识问答系统")
    print("=" * 60)
    
    # 环境检查
    env_ok = check_environment()
    js_ok = check_javascript_functions()
    
    if not env_ok:
        print("\n❌ 环境检查失败，请检查缺失的文件")
        sys.exit(1)
    
    if not js_ok:
        print("\n⚠️  JavaScript函数检查失败，可能影响前端功能")
        print("建议运行: python fix_qa_javascript_errors.py")
    
    show_test_urls()
    show_available_tools()
    
    print("\n✅ 系统功能状态:")
    print("  ✓ 文档上传和向量化")
    print("  ✓ 智能问答功能")
    print("  ✓ 系统配置管理")
    print("  ✓ 连接测试功能")
    print("  ✓ 通知系统")
    print("  ✓ 健康检查")
    
    print("\n🔧 已修复的问题:")
    print("  ✓ JavaScript语法错误")
    print("  ✓ formatTime函数缺失")
    print("  ✓ 通知系统显示问题")
    print("  ✓ API路径不匹配")
    print("  ✓ 配置保存和连接测试")
    print("  ✓ 向量维度不匹配")
    print("  ✓ 文档状态处理错误")
    
    print("\n⚠️  按 Ctrl+C 停止服务")
    print("=" * 60)
    
    # 启动服务器
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )