#!/usr/bin/env python3
"""
RAG Knowledge QA System Frontend Server
启动前端静态文件服务器
"""

import http.server
import socketserver
import os
import webbrowser
from pathlib import Path

def start_frontend_server():
    """启动前端服务器"""
    # 设置前端目录
    frontend_dir = Path("frontend")
    
    if not frontend_dir.exists():
        print("❌ 前端目录不存在: frontend/")
        return
    
    # 切换到前端目录
    os.chdir(frontend_dir)
    
    # 配置服务器
    PORT = 3000
    Handler = http.server.SimpleHTTPRequestHandler
    
    print("🚀 启动RAG知识问答系统前端服务器...")
    print(f"📁 前端目录: {frontend_dir.absolute()}")
    print(f"🌐 前端地址: http://localhost:{PORT}")
    print(f"🔗 后端API: http://localhost:8000")
    print("=" * 50)
    
    try:
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print(f"✅ 前端服务器已启动在端口 {PORT}")
            print("📱 正在自动打开浏览器...")
            
            # 自动打开浏览器
            try:
                webbrowser.open(f"http://localhost:{PORT}")
            except Exception as e:
                print(f"⚠️ 无法自动打开浏览器: {e}")
                print(f"请手动访问: http://localhost:{PORT}")
            
            print("\n🎯 演示指南:")
            print("1. 📄 文档管理 - 查看模拟文档列表")
            print("2. 💬 智能问答 - 测试问答功能")
            print("3. 📊 历史记录 - 查看会话历史")
            print("4. ⚙️ 系统设置 - 配置系统参数")
            print("5. 🌙 主题切换 - 切换深色/浅色主题")
            print("\n按 Ctrl+C 停止服务器")
            print("=" * 50)
            
            # 启动服务器
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n⏹️ 前端服务器已停止")
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ 端口 {PORT} 已被占用")
            print("💡 请检查是否已有服务在运行，或尝试其他端口")
        else:
            print(f"❌ 启动失败: {e}")
    except Exception as e:
        print(f"💥 未知错误: {e}")

if __name__ == "__main__":
    start_frontend_server()