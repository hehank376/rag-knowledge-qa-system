#!/usr/bin/env python3
"""
修复QA功能JavaScript错误
"""
import os
from pathlib import Path

def check_utils_functions():
    """检查utils.js中的函数定义"""
    print("🔍 检查utils.js中的函数定义...")
    
    utils_path = Path("frontend/js/utils.js")
    if not utils_path.exists():
        print("❌ utils.js文件不存在")
        return False
    
    try:
        with open(utils_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查必需的函数
        required_functions = [
            'formatTime',
            'formatDate', 
            'formatDateTime'
        ]
        
        missing_functions = []
        for func in required_functions:
            if f"function {func}(" in content:
                print(f"✓ {func} 函数已定义")
            else:
                missing_functions.append(func)
                print(f"❌ {func} 函数缺失")
        
        if missing_functions:
            print(f"\n⚠️  缺失的函数: {', '.join(missing_functions)}")
            return False
        else:
            print("\n✅ 所有必需的函数都已定义")
            return True
            
    except Exception as e:
        print(f"❌ 读取utils.js失败: {e}")
        return False

def check_qa_js_usage():
    """检查qa.js中的函数使用"""
    print("\n🔍 检查qa.js中的函数使用...")
    
    qa_path = Path("frontend/js/qa.js")
    if not qa_path.exists():
        print("❌ qa.js文件不存在")
        return False
    
    try:
        with open(qa_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查函数调用
        function_calls = [
            'formatTime(',
            'formatDate(',
            'formatDateTime('
        ]
        
        for func_call in function_calls:
            if func_call in content:
                print(f"✓ 发现函数调用: {func_call}")
            else:
                print(f"ℹ️  未发现函数调用: {func_call}")
        
        # 检查可能的问题
        if 'formatTime(' in content:
            print("✓ qa.js中使用了formatTime函数")
        
        return True
        
    except Exception as e:
        print(f"❌ 读取qa.js失败: {e}")
        return False

def check_html_script_order():
    """检查HTML中脚本加载顺序"""
    print("\n🔍 检查HTML中脚本加载顺序...")
    
    html_path = Path("frontend/index.html")
    if not html_path.exists():
        print("❌ index.html文件不存在")
        return False
    
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找脚本标签
        script_order = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            if '<script src="js/' in line:
                script_name = line.split('src="js/')[1].split('"')[0]
                script_order.append((i, script_name))
        
        print("📄 脚本加载顺序:")
        for line_num, script in script_order:
            print(f"  {line_num}: {script}")
        
        # 检查utils.js是否在qa.js之前加载
        utils_line = None
        qa_line = None
        
        for line_num, script in script_order:
            if script == 'utils.js':
                utils_line = line_num
            elif script == 'qa.js':
                qa_line = line_num
        
        if utils_line and qa_line:
            if utils_line < qa_line:
                print("✅ utils.js在qa.js之前加载，顺序正确")
                return True
            else:
                print("❌ utils.js在qa.js之后加载，顺序错误")
                return False
        else:
            print("⚠️  未找到utils.js或qa.js的引用")
            return False
        
    except Exception as e:
        print(f"❌ 读取index.html失败: {e}")
        return False

def create_test_page():
    """创建测试页面"""
    print("\n🔧 创建QA功能测试页面...")
    
    test_page_path = Path("test_qa_functions.html")
    if test_page_path.exists():
        print("✅ 测试页面已存在: test_qa_functions.html")
    else:
        print("❌ 测试页面不存在")
    
    return test_page_path.exists()

def show_fix_suggestions():
    """显示修复建议"""
    print("\n💡 修复建议:")
    print("1. 确保utils.js中定义了formatTime函数")
    print("2. 确保HTML中utils.js在qa.js之前加载")
    print("3. 检查浏览器控制台是否还有其他错误")
    print("4. 使用test_qa_functions.html测试函数是否正常工作")
    
    print("\n🧪 测试步骤:")
    print("1. 启动服务器: python start_production_ready_server.py")
    print("2. 访问测试页面: http://localhost:8000/test_qa_functions.html")
    print("3. 点击各个测试按钮验证函数功能")
    print("4. 访问主页面: http://localhost:8000")
    print("5. 测试问答功能是否正常")

def main():
    print("🛠️  QA功能JavaScript错误修复工具")
    print("=" * 50)
    
    # 检查各个组件
    utils_ok = check_utils_functions()
    qa_ok = check_qa_js_usage()
    html_ok = check_html_script_order()
    test_ok = create_test_page()
    
    print("\n" + "=" * 50)
    print("📋 检查结果:")
    print(f"  • utils.js函数定义: {'✅' if utils_ok else '❌'}")
    print(f"  • qa.js函数使用: {'✅' if qa_ok else '❌'}")
    print(f"  • HTML脚本顺序: {'✅' if html_ok else '❌'}")
    print(f"  • 测试页面: {'✅' if test_ok else '❌'}")
    
    if all([utils_ok, qa_ok, html_ok]):
        print("\n🎉 所有检查通过！QA功能应该可以正常工作。")
        print("\n🚀 下一步:")
        print("1. 重新启动服务器")
        print("2. 清除浏览器缓存")
        print("3. 测试问答功能")
    else:
        print("\n⚠️  发现问题，请根据上述检查结果进行修复。")
    
    show_fix_suggestions()

if __name__ == "__main__":
    main()