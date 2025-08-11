#!/usr/bin/env python3
"""
重启服务器
"""
import subprocess
import sys
import time
import os


def restart_server():
    """重启服务器"""
    print("🔄 重启服务器...")
    
    try:
        # 1. 尝试停止现有服务器
        print("\n1. 停止现有服务器...")
        try:
            # 在Windows上查找并终止Python进程
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'],
                capture_output=True,
                text=True
            )
            
            if 'python.exe' in result.stdout:
                print("   发现运行中的Python进程，尝试终止...")
                subprocess.run(['taskkill', '/F', '/IM', 'python.exe'], capture_output=True)
                time.sleep(2)
            
        except Exception as e:
            print(f"   停止服务器时出错: {str(e)}")
        
        # 2. 启动新服务器
        print("\n2. 启动新服务器...")
        
        # 检查启动脚本是否存在
        if os.path.exists('start_rag_system.py'):
            print("   使用 start_rag_system.py 启动...")
            subprocess.Popen([sys.executable, 'start_rag_system.py'])
        else:
            print("   直接启动API服务器...")
            subprocess.Popen([sys.executable, '-m', 'rag_system.api.main'])
        
        print("   等待服务器启动...")
        time.sleep(5)
        
        # 3. 测试服务器是否启动成功
        print("\n3. 测试服务器状态...")
        try:
            import requests
            response = requests.get("http://localhost:8000/health", timeout=5)
            if response.status_code == 200:
                print("   ✅ 服务器启动成功!")
            else:
                print(f"   ⚠️ 服务器响应异常: {response.status_code}")
        except Exception as e:
            print(f"   ⚠️ 无法连接到服务器: {str(e)}")
        
        print("\n✅ 重启完成")
        
    except Exception as e:
        print(f"❌ 重启失败: {str(e)}")


if __name__ == "__main__":
    restart_server()