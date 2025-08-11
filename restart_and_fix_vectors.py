#!/usr/bin/env python3
"""
重启服务器并修复向量维度问题
"""

import os
import sys
import time
import shutil
import requests
import subprocess
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_server_status():
    """检查服务器状态"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=3)
        return response.status_code == 200
    except:
        return False

def wait_for_server_start(max_wait=30):
    """等待服务器启动"""
    print("⏳ 等待服务器启动...")
    
    for i in range(max_wait):
        if check_server_status():
            print(f"✓ 服务器启动成功 ({i+1}秒)")
            return True
        time.sleep(1)
    
    print(f"✗ 服务器启动超时 ({max_wait}秒)")
    return False

def clear_vector_store():
    """清空向量存储"""
    print("🗑️ 清空向量存储...")
    
    chroma_dir = Path("./chroma_db")
    if chroma_dir.exists():
        try:
            shutil.rmtree(chroma_dir)
            print("✓ 向量存储已清空")
            return True
        except Exception as e:
            print(f"✗ 清空向量存储失败: {str(e)}")
            return False
    else:
        print("✓ 向量存储目录不存在，无需清空")
        return True

def main():
    """主函数"""
    print("🔄 重启服务器并修复向量维度问题")
    print("=" * 50)
    
    # 1. 检查服务器状态
    if check_server_status():
        print("⚠ 服务器正在运行，需要重启以清空向量存储")
        print("\n请按以下步骤操作:")
        print("1. 停止当前运行的服务器 (Ctrl+C)")
        print("2. 运行此脚本的第二部分:")
        print("   python restart_and_fix_vectors.py --fix-only")
        print("3. 重新启动服务器")
        return
    
    # 2. 清空向量存储
    if not clear_vector_store():
        print("❌ 清空向量存储失败")
        return
    
    print("\n✅ 向量存储已清空")
    print("\n🚀 下一步操作:")
    print("1. 启动服务器:")
    print("   python start_rag_system.py")
    print("2. 等待服务器启动完成")
    print("3. 运行文档重新处理:")
    print("   python fix_vector_dimension_issue.py")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--fix-only":
        # 只执行修复，不检查服务器
        clear_vector_store()
        print("\n✅ 向量存储已清空，现在可以重启服务器了")
    else:
        main()