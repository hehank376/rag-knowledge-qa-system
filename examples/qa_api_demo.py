"""
问答API演示脚本
展示问答API的各种功能
"""
import asyncio
import json
from fastapi.testclient import TestClient
from fastapi import FastAPI
from rag_system.api.qa_api import router


def create_test_app():
    """创建测试应用"""
    app = FastAPI(title="RAG问答系统API", version="1.0.0")
    app.include_router(router)
    return app


def demo_basic_qa(client):
    """演示基础问答功能"""
    print("=" * 50)
    print("基础问答功能演示")
    print("=" * 50)
    
    questions = [
        "什么是人工智能？",
        "机器学习的主要类型有哪些？",
        "深度学习和传统机器学习的区别是什么？"
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n{i}. 问题: {question}")
        
        try:
            response = client.post(
                "/qa/ask",
                json={
                    "question": question,
                    "top_k": 5,
                    "temperature": 0.7
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"   答案: {data['answer']}")
                print(f"   置信度: {data.get('confidence_score', 'N/A')}")
                print(f"   处理时间: {data.get('processing_time', 'N/A')}秒")
                print(f"   源文档数量: {data['source_count']}")
            else:
                print(f"   错误: {response.text}")
                
        except Exception as e:
            print(f"   异常: {str(e)}")


def demo_session_qa(client):
    """演示会话问答功能"""
    print("\n" + "=" * 50)
    print("会话问答功能演示")
    print("=" * 50)
    
    user_id = "demo_user_001"
    session_id = None
    
    questions = [
        "什么是神经网络？",
        "请详细解释一下反向传播算法",
        "神经网络有哪些常见的激活函数？"
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n{i}. 问题: {question}")
        
        try:
            # 第一次调用时创建会话，后续使用相同会话
            request_data = {"question": question}
            if session_id:
                request_data["session_id"] = session_id
            
            response = client.post(
                "/qa/ask-with-session",
                json=request_data,
                params={"user_id": user_id}
            )
            
            if response.status_code == 200:
                data = response.json()
                qa_response = data["qa_response"]
                session_info = data["session_info"]
                
                # 保存会话ID
                if not session_id:
                    session_id = session_info["session_id"]
                    print(f"   创建新会话: {session_id}")
                
                print(f"   答案: {qa_response['answer']}")
                print(f"   置信度: {qa_response.get('confidence_score', 'N/A')}")
                print(f"   会话ID: {session_info['session_id']}")
            else:
                print(f"   错误: {response.text}")
                
        except Exception as e:
            print(f"   异常: {str(e)}")
    
    # 获取会话历史
    if session_id:
        print(f"\n获取会话历史 (会话ID: {session_id})")
        try:
            response = client.get(f"/qa/session/{session_id}/history")
            if response.status_code == 200:
                data = response.json()
                print(f"   历史记录数量: {data['total_count']}")
                for j, qa in enumerate(data['history'], 1):
                    print(f"   {j}. Q: {qa['question'][:50]}...")
                    print(f"      A: {qa['answer'][:50]}...")
            else:
                print(f"   获取历史失败: {response.text}")
        except Exception as e:
            print(f"   异常: {str(e)}")


def demo_streaming_qa(client):
    """演示流式问答功能"""
    print("\n" + "=" * 50)
    print("流式问答功能演示")
    print("=" * 50)
    
    question = "请详细介绍一下卷积神经网络的工作原理"
    print(f"问题: {question}")
    print("流式响应:")
    
    try:
        response = client.post(
            "/qa/ask-stream",
            json={
                "question": question,
                "timeout": 10
            }
        )
        
        if response.status_code == 200:
            content = response.text
            lines = content.split('\n')
            
            for line in lines:
                if line.startswith('data: '):
                    try:
                        data = json.loads(line[6:])  # 去掉 'data: ' 前缀
                        event_type = data.get('type', 'unknown')
                        
                        if event_type == 'start':
                            print(f"   [开始] {data.get('message', '')}")
                        elif event_type == 'retrieval':
                            print(f"   [检索] {data.get('message', '')}")
                        elif event_type == 'processing':
                            print(f"   [处理] {data.get('message', '')}")
                        elif event_type == 'answer_chunk':
                            print(data.get('content', ''), end='', flush=True)
                        elif event_type == 'complete':
                            print(f"\n   [完成] 响应生成完毕")
                        elif event_type == 'error':
                            print(f"   [错误] {data.get('error', '')}")
                    except json.JSONDecodeError:
                        continue
        else:
            print(f"错误: {response.text}")
            
    except Exception as e:
        print(f"异常: {str(e)}")


def demo_search_and_stats(client):
    """演示搜索和统计功能"""
    print("\n" + "=" * 50)
    print("搜索和统计功能演示")
    print("=" * 50)
    
    # 搜索问答对
    print("1. 搜索问答对")
    try:
        response = client.get(
            "/qa/search",
            params={
                "query": "神经网络",
                "limit": 5
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   搜索查询: {data['query']}")
            print(f"   结果数量: {data['total_count']}")
            
            for i, result in enumerate(data['results'], 1):
                print(f"   {i}. Q: {result['question'][:50]}...")
                print(f"      A: {result['answer'][:50]}...")
                print(f"      置信度: {result['confidence_score']}")
        else:
            print(f"   搜索失败: {response.text}")
    except Exception as e:
        print(f"   异常: {str(e)}")
    
    # 获取最近问答对
    print("\n2. 获取最近问答对")
    try:
        response = client.get(
            "/qa/sessions/recent",
            params={"limit": 5}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   最近问答对数量: {data['total_count']}")
            
            for i, qa in enumerate(data['recent_qa_pairs'], 1):
                print(f"   {i}. Q: {qa['question'][:50]}...")
                print(f"      A: {qa['answer'][:50]}...")
                print(f"      会话ID: {qa['session_id']}")
        else:
            print(f"   获取失败: {response.text}")
    except Exception as e:
        print(f"   异常: {str(e)}")
    
    # 获取系统统计
    print("\n3. 获取系统统计")
    try:
        response = client.get("/qa/stats")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   QA服务统计: {data.get('qa_service_stats', {})}")
            print(f"   结果处理器统计: {data.get('result_processor_stats', {})}")
            print(f"   总处理问题数: {data.get('total_questions_processed', 0)}")
        else:
            print(f"   获取统计失败: {response.text}")
    except Exception as e:
        print(f"   异常: {str(e)}")


def demo_error_handling(client):
    """演示错误处理功能"""
    print("\n" + "=" * 50)
    print("错误处理功能演示")
    print("=" * 50)
    
    # 测试空问题
    print("1. 测试空问题")
    try:
        response = client.post(
            "/qa/ask",
            json={"question": ""}
        )
        print(f"   状态码: {response.status_code}")
        if response.status_code != 200:
            print(f"   错误信息: {response.json().get('detail', 'N/A')}")
    except Exception as e:
        print(f"   异常: {str(e)}")
    
    # 测试空搜索查询
    print("\n2. 测试空搜索查询")
    try:
        response = client.get(
            "/qa/search",
            params={"query": ""}
        )
        print(f"   状态码: {response.status_code}")
        if response.status_code != 200:
            print(f"   错误信息: {response.json().get('detail', 'N/A')}")
    except Exception as e:
        print(f"   异常: {str(e)}")
    
    # 测试无答案帮助
    print("\n3. 测试无答案帮助")
    try:
        response = client.post(
            "/qa/no-answer-help",
            params={
                "question": "这是一个测试问题",
                "reason": "no_relevant_content"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   有答案: {data['has_answer']}")
            print(f"   原因: {data['reason']}")
            print(f"   建议数量: {len(data['suggestions'])}")
            print(f"   建议: {data['suggestions']}")
        else:
            print(f"   错误: {response.text}")
    except Exception as e:
        print(f"   异常: {str(e)}")


def main():
    """主函数"""
    print("RAG知识问答系统 - 问答API功能演示")
    print("=" * 60)
    
    # 创建测试应用和客户端
    app = create_test_app()
    client = TestClient(app)
    
    # 健康检查
    print("系统健康检查...")
    try:
        response = client.get("/qa/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ 服务状态: {data['status']}")
            print(f"✓ 服务名称: {data['service']}")
            print(f"✓ 版本: {data['version']}")
        else:
            print("✗ 健康检查失败")
            return
    except Exception as e:
        print(f"✗ 健康检查异常: {str(e)}")
        return
    
    # 运行各种演示
    try:
        demo_basic_qa(client)
        demo_session_qa(client)
        demo_streaming_qa(client)
        demo_search_and_stats(client)
        demo_error_handling(client)
        
        print("\n" + "=" * 60)
        print("问答API功能演示完成！")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n演示被用户中断")
    except Exception as e:
        print(f"\n演示过程中发生错误: {str(e)}")


if __name__ == "__main__":
    main()