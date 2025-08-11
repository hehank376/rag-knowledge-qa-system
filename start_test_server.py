#!/usr/bin/env python3
"""
启动测试服务器
"""
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

def start_api_server():
    """启动API服务器"""
    print("🚀 启动API服务器...")
    try:
        # 启动FastAPI服务器
        process = subprocess.Popen([
            sys.executable, "-m", "rag_system.api.main"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # 等待服务器启动
        time.sleep(3)
        
        # 检查服务器是否启动成功
        import requests
        try:
            response = requests.get('http://localhost:8000/health', timeout=5)
            if response.status_code == 200:
                print("✅ API服务器启动成功！")
                print("📍 API地址: http://localhost:8000")
                print("📚 API文档: http://localhost:8000/docs")
                return process
            else:
                print(f"❌ API服务器启动失败，状态码: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"❌ API服务器连接失败: {str(e)}")
            return None
            
    except Exception as e:
        print(f"❌ 启动API服务器失败: {str(e)}")
        return None

def start_frontend_server():
    """启动前端测试服务器"""
    print("🌐 启动前端测试服务器...")
    try:
        # 使用Python内置的HTTP服务器
        process = subprocess.Popen([
            sys.executable, "-m", "http.server", "3000"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # 等待服务器启动
        time.sleep(2)
        
        print("✅ 前端测试服务器启动成功！")
        print("📍 测试页面: http://localhost:3000/test_upload_frontend.html")
        
        return process
        
    except Exception as e:
        print(f"❌ 启动前端服务器失败: {str(e)}")
        return None

def main():
    """主函数"""
    print("=== RAG系统文件上传测试环境启动 ===\n")
    
    # 启动API服务器
    api_process = start_api_server()
    if not api_process:
        print("❌ API服务器启动失败，退出")
        return
    
    print()
    
    # 启动前端服务器
    frontend_process = start_frontend_server()
    if not frontend_process:
        print("❌ 前端服务器启动失败，但API服务器仍在运行")
        print("📍 你可以直接访问: http://localhost:8000/docs 测试API")
    
    print("\n=== 服务器启动完成 ===")
    print("📝 测试说明:")
    print("1. 访问 http://localhost:3000/test_upload_frontend.html 进行文件上传测试")
    print("2. 访问 http://localhost:8000/docs 查看API文档")
    print("3. 按 Ctrl+C 停止所有服务器")
    
    # 自动打开浏览器
    try:
        time.sleep(1)
        webbrowser.open('http://localhost:3000/test_upload_frontend.html')
    except:
        pass
    
    try:
        # 等待用户中断
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 正在停止服务器...")
        
        if api_process:
            api_process.terminate()
            print("✅ API服务器已停止")
        
        if frontend_process:
            frontend_process.terminate()
            print("✅ 前端服务器已停止")
        
        print("👋 再见！")

if __name__ == "__main__":
    main()