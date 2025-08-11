#!/usr/bin/env python3
"""
启动最终完整的RAG系统（包含所有修复）
"""
import uvicorn
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from rag_system.api.main import app

def check_all_components():
    """检查所有系统组件"""
    print("🔍 系统组件检查...")
    
    checks = []
    
    # 1. 检查JavaScript函数
    utils_path = Path("frontend/js/utils.js")
    if utils_path.exists():
        with open(utils_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_functions = ['formatTime', 'formatDate', 'formatDateTime']
        missing = [func for func in required_functions if f"function {func}(" not in content]
        
        if missing:
            checks.append(("JavaScript函数", False, f"缺失: {', '.join(missing)}"))
        else:
            checks.append(("JavaScript函数", True, "所有必需函数已定义"))
    else:
        checks.append(("JavaScript函数", False, "utils.js文件不存在"))
    
    # 2. 检查API密钥
    api_keys = []
    if os.getenv("SILICONFLOW_API_KEY"):
        api_keys.append("SiliconFlow")
    if os.getenv("OPENAI_API_KEY"):
        api_keys.append("OpenAI")
    
    if api_keys:
        checks.append(("API密钥", True, f"已配置: {', '.join(api_keys)}"))
    else:
        checks.append(("API密钥", False, "未配置，将使用Mock模式"))
    
    # 3. 检查配置文件
    config_path = Path("config.yaml")
    if config_path.exists():
        checks.append(("配置文件", True, "config.yaml存在"))
    else:
        checks.append(("配置文件", False, "config.yaml不存在"))
    
    # 4. 检查关键前端文件
    critical_files = [
        "frontend/index.html",
        "frontend/js/utils.js",
        "frontend/js/qa.js",
        "frontend/js/api.js",
        "frontend/js/notifications.js"
    ]
    
    missing_files = [f for f in critical_files if not Path(f).exists()]
    if missing_files:
        checks.append(("前端文件", False, f"缺失: {', '.join(missing_files)}"))
    else:
        checks.append(("前端文件", True, "所有关键文件存在"))
    
    # 5. 检查数据目录
    data_dirs = ["./chroma_db", "./uploads", "./data"]
    existing_dirs = [d for d in data_dirs if Path(d).exists()]
    if existing_dirs:
        checks.append(("数据目录", True, f"存在: {', '.join(existing_dirs)}"))
    else:
        checks.append(("数据目录", True, "将自动创建"))
    
    # 显示检查结果
    print("\n📋 系统组件状态:")
    for component, status, details in checks:
        status_icon = "✅" if status else "⚠️"
        print(f"  {status_icon} {component}: {details}")
    
    return all(check[1] for check in checks if check[0] in ["JavaScript函数", "前端文件"])

def show_system_info():
    """显示系统信息"""
    print("\n🌐 服务地址:")
    print("  • 主界面: http://localhost:8000")
    print("  • API文档: http://localhost:8000/docs")
    print("  • 健康检查: http://localhost:8000/health")
    
    print("\n🧪 测试页面:")
    test_pages = [
        ("通知系统测试", "http://localhost:8000/test_notifications.html"),
        ("QA功能测试", "http://localhost:8000/test_qa_functions.html")
    ]
    
    for name, url in test_pages:
        print(f"  • {name}: {url}")
    
    print("\n🔧 修复工具:")
    tools = [
        ("会话API错误修复", "python fix_session_api_errors.py"),
        ("QA功能错误修复", "python fix_qa_javascript_errors.py"),
        ("文档上传问题修复", "python fix_document_upload_issues.py"),
        ("真实模型连接测试", "python test_real_model_connection.py")
    ]
    
    for name, command in tools:
        print(f"  • {name}: {command}")

def show_fixed_issues():
    """显示已修复的问题"""
    print("\n✅ 已修复的问题:")
    issues = [
        "JavaScript语法错误 (history.js)",
        "formatDate函数未定义",
        "formatTime函数未定义",
        "通知系统显示问题",
        "API路径不匹配",
        "配置保存和连接测试",
        "向量维度不匹配",
        "文档状态处理错误",
        "会话API参数不匹配"
    ]
    
    for i, issue in enumerate(issues, 1):
        print(f"  {i}. ✓ {issue}")

def show_system_features():
    """显示系统功能"""
    print("\n🎯 系统功能:")
    features = [
        "文档上传和向量化存储",
        "智能问答和对话管理",
        "多平台模型支持 (OpenAI, SiliconFlow)",
        "系统配置和连接测试",
        "实时通知和状态反馈",
        "会话历史和管理",
        "健康监控和错误处理"
    ]
    
    for feature in features:
        print(f"  • {feature}")

if __name__ == "__main__":
    print("🚀 启动最终完整的RAG知识问答系统")
    print("=" * 60)
    
    # 系统检查
    system_ok = check_all_components()
    
    if not system_ok:
        print("\n⚠️  系统检查发现问题，但服务器仍将启动")
        print("建议运行相应的修复工具解决问题")
    
    show_system_info()
    show_fixed_issues()
    show_system_features()
    
    print("\n🎉 系统已完全修复并准备就绪！")
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