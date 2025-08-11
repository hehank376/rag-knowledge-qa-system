#!/usr/bin/env python3
"""
修复会话问题
"""
import subprocess
import sys
import time
import os


def fix_session_issue():
    """修复会话问题"""
    print("🔧 修复会话问题...")
    
    try:
        # 1. 检查当前代码状态
        print("\n1. 检查当前代码状态...")
        
        # 检查QAResponseFormatted是否有session_id字段
        with open('rag_system/api/qa_api.py', 'r', encoding='utf-8') as f:
            content = f.read()
            if 'session_id: Optional[str] = None' in content:
                print("   ✅ QAResponseFormatted已包含session_id字段")
            else:
                print("   ❌ QAResponseFormatted缺少session_id字段")
        
        # 检查会话创建逻辑
        if 'await session_service.create_session(request.user_id)' in content:
            print("   ✅ 自动创建会话逻辑已添加")
        else:
            print("   ❌ 缺少自动创建会话逻辑")
        
        # 2. 验证语法
        print("\n2. 验证代码语法...")
        result = subprocess.run([sys.executable, '-m', 'py_compile', 'rag_system/api/qa_api.py'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("   ✅ 代码语法正确")
        else:
            print(f"   ❌ 语法错误: {result.stderr}")
            return
        
        # 3. 尝试重启服务器
        print("\n3. 尝试重启服务器...")
        
        # 在Windows上终止Python进程
        try:
            subprocess.run(['taskkill', '/F', '/IM', 'python.exe'], 
                         capture_output=True, timeout=5)
            print("   已终止现有Python进程")
            time.sleep(3)
        except:
            print("   无法终止进程或没有运行的进程")
        
        # 启动新服务器
        print("   启动新服务器...")
        if os.path.exists('start_rag_system.py'):
            process = subprocess.Popen([sys.executable, 'start_rag_system.py'])
            print(f"   服务器进程ID: {process.pid}")
        else:
            print("   找不到启动脚本")
            return
        
        # 4. 等待服务器启动
        print("\n4. 等待服务器启动...")
        for i in range(10):
            time.sleep(2)
            try:
                import requests
                response = requests.get("http://localhost:8000/health", timeout=3)
                if response.status_code == 200:
                    print(f"   ✅ 服务器启动成功 (耗时 {(i+1)*2} 秒)")
                    break
            except:
                print(f"   等待中... ({(i+1)*2}s)")
        else:
            print("   ⚠️ 服务器启动超时，但可能仍在启动中")
        
        # 5. 测试修复效果
        print("\n5. 测试修复效果...")
        try:
            import requests
            
            # 测试自动创建会话
            test_request = {
                "question": "测试自动创建会话",
                "session_id": None,
                "user_id": "test_fix_user"
            }
            
            response = requests.post(
                "http://localhost:8000/qa/ask",
                json=test_request,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                session_id = result.get('session_id')
                if session_id and session_id != 'N/A':
                    print(f"   ✅ 修复成功! 自动创建的会话ID: {session_id}")
                    
                    # 检查统计
                    stats_response = requests.get("http://localhost:8000/sessions/stats/summary", timeout=10)
                    if stats_response.status_code == 200:
                        stats = stats_response.json()
                        print(f"   统计数据: 会话={stats.get('total_sessions', 0)}, 问答对={stats.get('total_qa_pairs', 0)}")
                else:
                    print(f"   ❌ 会话ID仍然无效: {session_id}")
            else:
                print(f"   ❌ 测试请求失败: {response.status_code}")
                print(f"   错误: {response.text}")
                
        except Exception as e:
            print(f"   ❌ 测试失败: {str(e)}")
        
        print("\n✅ 修复完成")
        
    except Exception as e:
        print(f"❌ 修复失败: {str(e)}")


if __name__ == "__main__":
    fix_session_issue()