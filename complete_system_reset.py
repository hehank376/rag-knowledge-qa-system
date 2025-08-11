#!/usr/bin/env python3
"""
完整的系统重置和修复脚本
1. 停止服务器
2. 清理所有数据
3. 重新启动系统
4. 上传测试文档
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

def clean_all_data():
    """清理所有数据文件"""
    print("🧹 清理所有数据文件...")
    
    files_to_clean = [
        "./chroma_db",
        "./database/rag_system.db",
        "./database/documents.db", 
        "./database/qa_sessions.db",
        "./sessions.db",
        "./demo_sessions.db"
    ]
    
    cleaned_count = 0
    for file_path in files_to_clean:
        path = Path(file_path)
        try:
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path)
                    print(f"  ✓ 删除目录: {file_path}")
                else:
                    path.unlink()
                    print(f"  ✓ 删除文件: {file_path}")
                cleaned_count += 1
            else:
                print(f"  - 不存在: {file_path}")
        except Exception as e:
            print(f"  ✗ 删除失败 {file_path}: {str(e)}")
    
    print(f"✓ 清理完成，处理了 {cleaned_count} 个文件/目录")
    return True

def create_test_documents():
    """创建测试文档"""
    print("📝 创建测试文档...")
    
    # 确保documents目录存在
    docs_dir = Path("documents")
    docs_dir.mkdir(exist_ok=True)
    
    test_docs = {
        "ai_introduction.txt": """人工智能简介

人工智能（Artificial Intelligence，AI）是计算机科学的一个分支，它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。

人工智能的主要应用领域包括：
1. 机器学习 - 让计算机能够自动学习和改进
2. 自然语言处理 - 让计算机理解和生成人类语言
3. 计算机视觉 - 让计算机能够"看"和理解图像
4. 专家系统 - 模拟人类专家的决策过程
5. 机器人技术 - 创造能够执行任务的智能机器

机器学习是人工智能的核心技术之一，它包括：
- 监督学习：使用标记数据训练模型
- 无监督学习：从未标记数据中发现模式
- 强化学习：通过试错来学习最优策略

深度学习是机器学习的一个子领域，使用神经网络来模拟人脑的工作方式。它在图像识别、语音识别和自然语言处理等领域取得了突破性进展。

RAG（Retrieval-Augmented Generation）是一种结合了信息检索和文本生成的技术，它能够从大量文档中检索相关信息，然后生成准确的答案。
""",
        
        "company_policy.txt": """公司管理制度

一、考勤制度
1. 工作时间：周一至周五 9:00-18:00，中午休息1小时
2. 迟到早退：迟到或早退超过30分钟按半天假处理
3. 请假制度：
   - 事假：需提前1天申请，扣除相应工资
   - 病假：需提供医院证明，按基本工资80%发放
   - 年假：工作满1年享受5天年假，满3年享受10天年假

二、薪酬制度
1. 基本工资：按岗位等级确定
2. 绩效奖金：根据月度考核结果发放
3. 年终奖：根据公司业绩和个人表现发放
4. 工资发放时间：每月15日发放上月工资

三、培训制度
1. 新员工培训：入职后进行为期1周的岗前培训
2. 技能培训：定期组织专业技能培训
3. 管理培训：为管理岗位提供领导力培训

四、福利制度
1. 社会保险：公司为员工缴纳五险一金
2. 商业保险：为员工购买意外险和医疗险
3. 节日福利：春节、中秋节等传统节日发放福利
4. 生日福利：员工生日当天享受生日假和生日礼品
""",

        "study_guide.txt": """学习指南

高考志愿填报建议

一、了解自己
1. 兴趣爱好：选择自己感兴趣的专业领域
2. 能力特长：发挥自己的优势和特长
3. 性格特点：选择适合自己性格的专业
4. 职业规划：考虑未来的职业发展方向

二、了解专业
1. 专业内容：深入了解专业的学习内容和课程设置
2. 就业前景：关注专业的就业率和发展前景
3. 薪资水平：了解该专业毕业生的平均薪资
4. 行业发展：关注相关行业的发展趋势

三、了解院校
1. 学校排名：参考各种大学排名，但不要盲目追求
2. 地理位置：考虑学校所在城市的发展机会
3. 师资力量：了解学校的师资配置和教学质量
4. 校园文化：选择适合自己的校园氛围

四、填报策略
1. 冲稳保：合理搭配不同层次的院校
2. 专业优先还是学校优先：根据个人情况选择
3. 服从调剂：增加录取机会，但要慎重考虑
4. 多方咨询：听取老师、家长和学长学姐的建议

五、注意事项
1. 仔细阅读招生简章和专业要求
2. 注意填报时间和截止日期
3. 保存好相关材料和密码
4. 及时关注录取结果和征集志愿信息
"""
    }
    
    created_count = 0
    for filename, content in test_docs.items():
        file_path = docs_dir / filename
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  ✓ 创建文档: {filename}")
            created_count += 1
        except Exception as e:
            print(f"  ✗ 创建失败 {filename}: {str(e)}")
    
    print(f"✓ 创建了 {created_count} 个测试文档")
    return created_count > 0

def upload_test_documents():
    """上传测试文档"""
    print("📤 上传测试文档...")
    
    docs_dir = Path("documents")
    test_files = ["ai_introduction.txt", "company_policy.txt", "study_guide.txt"]
    
    uploaded_count = 0
    for filename in test_files:
        file_path = docs_dir / filename
        if not file_path.exists():
            print(f"  ✗ 文件不存在: {filename}")
            continue
        
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (filename, f, 'text/plain')}
                response = requests.post(
                    "http://localhost:8000/documents/upload",
                    files=files,
                    timeout=30
                )
            
            if response.status_code == 200:
                result = response.json()
                print(f"  ✓ 上传成功: {filename}")
                print(f"    文档ID: {result.get('document_id', 'N/A')}")
                uploaded_count += 1
            else:
                error_detail = response.json().get('detail', '未知错误') if response.headers.get('content-type', '').startswith('application/json') else response.text
                print(f"  ✗ 上传失败 {filename}: {error_detail}")
                
        except Exception as e:
            print(f"  ✗ 上传异常 {filename}: {str(e)}")
    
    print(f"✓ 上传了 {uploaded_count} 个文档")
    return uploaded_count

def wait_for_processing():
    """等待文档处理完成"""
    print("⏳ 等待文档处理完成...")
    
    max_wait = 120  # 最多等待2分钟
    for i in range(max_wait):
        try:
            response = requests.get("http://localhost:8000/documents/", timeout=5)
            if response.status_code == 200:
                data = response.json()
                total = data.get('total_count', 0)
                ready = data.get('ready_count', 0)
                processing = data.get('processing_count', 0)
                error = data.get('error_count', 0)
                
                if total > 0:
                    if processing == 0:
                        print(f"  ✓ 处理完成: 总数={total}, 就绪={ready}, 错误={error}")
                        return ready > 0
                    else:
                        if i % 10 == 0:  # 每10秒打印一次状态
                            print(f"  ⏳ 处理中: 总数={total}, 就绪={ready}, 处理中={processing}, 错误={error}")
                
            time.sleep(1)
        except Exception as e:
            if i % 30 == 0:  # 每30秒打印一次错误
                print(f"  ⚠ 检查状态失败: {str(e)}")
            time.sleep(1)
    
    print(f"  ⚠ 等待超时")
    return False

def test_qa_functionality():
    """测试问答功能"""
    print("🧪 测试问答功能...")
    
    test_questions = [
        "什么是人工智能？",
        "公司的考勤制度是什么？", 
        "高考志愿填报有什么建议？",
        "什么是RAG技术？"
    ]
    
    success_count = 0
    for i, question in enumerate(test_questions, 1):
        print(f"\n{i}. 问题: {question}")
        
        try:
            response = requests.post(
                "http://localhost:8000/qa/ask",
                json={"question": question},
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get('answer', '')
                sources = result.get('sources', [])
                confidence = result.get('confidence_score', 0)
                
                print(f"   答案: {answer[:150]}...")
                print(f"   源文档数量: {len(sources)}")
                print(f"   置信度: {confidence}")
                
                if len(sources) > 0 and confidence > 0:
                    print(f"   ✓ 找到相关内容")
                    success_count += 1
                else:
                    print(f"   ⚠ 没有找到相关内容")
                    
            else:
                print(f"   ✗ 请求失败: {response.status_code}")
                
        except Exception as e:
            print(f"   ✗ 请求异常: {str(e)}")
    
    print(f"\n📊 测试结果: {success_count}/{len(test_questions)} 个问题找到了相关内容")
    return success_count > 0

def main():
    """主函数"""
    print("🔄 完整系统重置和修复")
    print("=" * 50)
    
    # 检查服务器状态
    if check_server_status():
        print("⚠ 服务器正在运行")
        print("\n请先停止服务器，然后运行:")
        print("python complete_system_reset.py --reset-only")
        print("\n然后重新启动服务器:")
        print("python start_rag_system.py")
        print("\n最后运行完整测试:")
        print("python complete_system_reset.py --test-only")
        return
    
    # 执行重置
    if len(sys.argv) > 1 and sys.argv[1] == "--reset-only":
        print("🧹 执行系统重置...")
        clean_all_data()
        create_test_documents()
        print("\n✅ 系统重置完成")
        print("现在可以重新启动服务器了:")
        print("python start_rag_system.py")
        return
    
    # 执行测试
    if len(sys.argv) > 1 and sys.argv[1] == "--test-only":
        print("🧪 执行完整测试...")
        
        if not check_server_status():
            print("❌ 服务器未运行，请先启动服务器")
            return
        
        # 创建测试文档（如果不存在）
        create_test_documents()
        
        # 上传文档
        if upload_test_documents() > 0:
            # 等待处理
            if wait_for_processing():
                # 测试问答
                if test_qa_functionality():
                    print("\n🎉 系统测试成功！")
                    print("现在可以在前端测试问答功能了")
                else:
                    print("\n⚠ 问答功能测试部分成功")
            else:
                print("\n⚠ 文档处理超时")
        else:
            print("\n❌ 文档上传失败")
        return
    
    # 默认提示
    print("请按以下步骤操作:")
    print("1. 停止当前服务器 (Ctrl+C)")
    print("2. 运行重置: python complete_system_reset.py --reset-only")
    print("3. 启动服务器: python start_rag_system.py")
    print("4. 运行测试: python complete_system_reset.py --test-only")

if __name__ == "__main__":
    main()