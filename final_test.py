#!/usr/bin/env python3
"""
最终测试脚本 - 验证文档统计功能
"""
import requests
import json
import time

def test_api_endpoints():
    """测试API端点"""
    print("🧪 测试API端点...")
    
    endpoints = [
        ("健康检查", "http://localhost:8000/health"),
        ("文档统计", "http://localhost:8000/documents/stats/summary"),
        ("文档列表", "http://localhost:8000/documents/"),
        ("前端页面", "http://localhost:8000/frontend/index.html"),
        ("测试页面", "http://localhost:8000/static/simple_test.html")
    ]
    
    results = {}
    
    for name, url in endpoints:
        try:
            response = requests.get(url, timeout=10)
            results[name] = {
                "status": response.status_code,
                "success": response.status_code == 200,
                "content_type": response.headers.get('content-type', ''),
                "size": len(response.content)
            }
            
            if name == "文档统计" and response.status_code == 200:
                stats = response.json()
                results[name]["data"] = stats
                
        except Exception as e:
            results[name] = {
                "status": "ERROR",
                "success": False,
                "error": str(e)
            }
    
    return results

def print_results(results):
    """打印测试结果"""
    print("\\n📊 测试结果:")
    print("=" * 60)
    
    for name, result in results.items():
        status = "✅" if result["success"] else "❌"
        print(f"{status} {name}")
        
        if result["success"]:
            print(f"   状态码: {result['status']}")
            print(f"   内容类型: {result['content_type']}")
            print(f"   大小: {result['size']} bytes")
            
            if "data" in result:
                data = result["data"]
                print(f"   统计数据:")
                print(f"     - 总文档数: {data.get('total_documents', 0)}")
                print(f"     - 已就绪: {data.get('ready_documents', 0)}")
                print(f"     - 处理中: {data.get('processing_documents', 0)}")
                print(f"     - 处理失败: {data.get('error_documents', 0)}")
        else:
            if "error" in result:
                print(f"   错误: {result['error']}")
            else:
                print(f"   状态码: {result['status']}")
        
        print()

def main():
    """主函数"""
    print("🚀 开始最终测试")
    print("=" * 60)
    
    # 测试API端点
    results = test_api_endpoints()
    
    # 打印结果
    print_results(results)
    
    # 总结
    success_count = sum(1 for r in results.values() if r["success"])
    total_count = len(results)
    
    print("=" * 60)
    print(f"📈 测试总结: {success_count}/{total_count} 个端点正常工作")
    
    if success_count == total_count:
        print("🎉 所有测试通过！")
        print("\\n💡 使用说明:")
        print("1. 访问 http://localhost:8000/frontend/index.html 查看主页面")
        print("2. 访问 http://localhost:8000/static/simple_test.html 查看简单测试页面")
        print("3. 打开浏览器开发者工具查看控制台日志")
        print("4. 如果主页面统计仍显示0，请:")
        print("   - 按 Ctrl+F5 强制刷新页面")
        print("   - 清除浏览器缓存")
        print("   - 检查浏览器控制台是否有JavaScript错误")
    else:
        print("⚠️ 部分测试失败，请检查相关服务")

if __name__ == "__main__":
    main()