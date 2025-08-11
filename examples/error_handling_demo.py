#!/usr/bin/env python3
"""
错误处理机制演示脚本
演示任务9.1：统一错误处理机制的使用
"""
import asyncio
import logging
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from rag_system.utils.exceptions import (
    DocumentNotFoundError, QATimeoutError, ConfigurationError,
    VectorStoreConnectionError, ValidationError, ErrorCode
)
from rag_system.utils.error_handler import (
    ErrorHandler, ErrorHandlerMiddleware, create_error_response,
    handle_api_error, global_error_handler
)
from rag_system.utils.logging_config import setup_logging, get_logger


def demo_exception_classes():
    """演示异常类的使用"""
    print("=" * 60)
    print("异常类演示")
    print("=" * 60)
    
    # 1. 基础异常
    print("\n1. 基础RAG系统异常")
    print("-" * 30)
    try:
        from rag_system.utils.exceptions import RAGSystemError
        error = RAGSystemError(
            "这是一个测试错误",
            error_code=ErrorCode.VALIDATION_ERROR,
            details={"field": "email", "value": "invalid"}
        )
        print(f"异常字符串: {error}")
        print(f"错误代码: {error.error_code.value}")
        print(f"错误详情: {error.details}")
        print(f"异常字典: {error.to_dict()}")
    except Exception as e:
        print(f"创建异常时出错: {e}")
    
    # 2. 文档相关异常
    print("\n2. 文档相关异常")
    print("-" * 30)
    
    # 文档未找到
    doc_not_found = DocumentNotFoundError("doc_123")
    print(f"文档未找到: {doc_not_found}")
    print(f"错误代码: {doc_not_found.error_code.value}")
    
    # 文档格式错误
    from rag_system.utils.exceptions import DocumentFormatError
    format_error = DocumentFormatError("test.xyz", "PDF")
    print(f"格式错误: {format_error}")
    print(f"详情: {format_error.details}")
    
    # 3. 问答相关异常
    print("\n3. 问答相关异常")
    print("-" * 30)
    
    # 问答超时
    qa_timeout = QATimeoutError("什么是人工智能？", 30)
    print(f"问答超时: {qa_timeout}")
    print(f"详情: {qa_timeout.details}")
    
    # 无相关内容
    from rag_system.utils.exceptions import QANoRelevantContentError
    no_content = QANoRelevantContentError("这是一个无关问题")
    print(f"无相关内容: {no_content}")
    
    # 4. 配置相关异常
    print("\n4. 配置相关异常")
    print("-" * 30)
    
    config_error = ConfigurationError(
        "数据库配置无效",
        config_key="database.url"
    )
    print(f"配置错误: {config_error}")
    
    # 5. 向量存储异常
    print("\n5. 向量存储异常")
    print("-" * 30)
    
    vector_error = VectorStoreConnectionError("chroma")
    print(f"向量存储连接错误: {vector_error}")
    print(f"详情: {vector_error.details}")


def demo_error_handler():
    """演示错误处理器的使用"""
    print("\n" + "=" * 60)
    print("错误处理器演示")
    print("=" * 60)
    
    # 设置日志
    setup_logging(log_level="INFO", enable_file_logging=False)
    logger = get_logger("demo")
    
    error_handler = ErrorHandler(logger)
    
    # 测试不同类型的异常处理
    test_errors = [
        DocumentNotFoundError("doc_456"),
        QATimeoutError("复杂问题", 60),
        ConfigurationError("配置加载失败"),
        HTTPException(status_code=400, detail="请求参数错误"),
        ValueError("数据验证失败"),
        FileNotFoundError("文件不存在"),
        RuntimeError("未知运行时错误")
    ]
    
    for i, error in enumerate(test_errors, 1):
        print(f"\n{i}. 处理 {error.__class__.__name__}")
        print("-" * 40)
        
        try:
            result = error_handler.handle_exception(error)
            print(f"状态码: {result['status_code']}")
            print(f"错误类型: {result['response']['error']['type']}")
            print(f"错误代码: {result['response']['error']['code']}")
            print(f"错误消息: {result['response']['error']['message']}")
            
            if result['response']['error'].get('details'):
                print(f"错误详情: {result['response']['error']['details']}")
        except Exception as e:
            print(f"处理异常时出错: {e}")


def demo_error_middleware():
    """演示错误处理中间件的使用"""
    print("\n" + "=" * 60)
    print("错误处理中间件演示")
    print("=" * 60)
    
    # 创建FastAPI应用
    app = FastAPI(title="错误处理演示")
    
    # 添加错误处理中间件
    logger = get_logger("demo.api")
    app.add_middleware(ErrorHandlerMiddleware, logger=logger)
    
    # 定义测试端点
    @app.get("/success")
    async def success_endpoint():
        return {"message": "成功响应", "status": "ok"}
    
    @app.get("/document-not-found")
    async def document_not_found_endpoint():
        raise DocumentNotFoundError("test_doc_789")
    
    @app.get("/qa-timeout")
    async def qa_timeout_endpoint():
        raise QATimeoutError("这是一个复杂的问题", 45)
    
    @app.get("/validation-error")
    async def validation_error_endpoint():
        raise ValidationError("邮箱格式不正确", field="email", value="invalid-email")
    
    @app.get("/http-error")
    async def http_error_endpoint():
        raise HTTPException(status_code=403, detail="权限不足")
    
    @app.get("/unknown-error")
    async def unknown_error_endpoint():
        raise RuntimeError("这是一个未知错误")
    
    # 使用装饰器的端点
    @app.get("/decorated-endpoint")
    @handle_api_error
    async def decorated_endpoint():
        raise ConfigurationError("配置文件损坏")
    
    # 创建测试客户端
    client = TestClient(app)
    
    # 测试各个端点
    test_endpoints = [
        ("/success", "成功请求"),
        ("/document-not-found", "文档未找到异常"),
        ("/qa-timeout", "问答超时异常"),
        ("/validation-error", "验证错误异常"),
        ("/http-error", "HTTP异常"),
        ("/unknown-error", "未知异常"),
        ("/decorated-endpoint", "装饰器处理异常")
    ]
    
    for endpoint, description in test_endpoints:
        print(f"\n测试: {description}")
        print("-" * 40)
        
        try:
            response = client.get(endpoint)
            print(f"状态码: {response.status_code}")
            
            data = response.json()
            if response.status_code == 200:
                print(f"响应: {data}")
            else:
                print(f"错误类型: {data.get('error', {}).get('type', 'Unknown')}")
                print(f"错误代码: {data.get('error', {}).get('code', 'Unknown')}")
                print(f"错误消息: {data.get('error', {}).get('message', 'Unknown')}")
                
                if data.get('error', {}).get('details'):
                    print(f"错误详情: {data['error']['details']}")
        except Exception as e:
            print(f"测试端点时出错: {e}")


def demo_error_response_creation():
    """演示错误响应创建"""
    print("\n" + "=" * 60)
    print("错误响应创建演示")
    print("=" * 60)
    
    # 1. 基础错误响应
    print("\n1. 基础错误响应")
    print("-" * 30)
    
    response = create_error_response(
        ErrorCode.VALIDATION_ERROR,
        "数据验证失败"
    )
    print(f"状态码: {response.status_code}")
    print(f"响应体: {response.body.decode()}")
    
    # 2. 带详情的错误响应
    print("\n2. 带详情的错误响应")
    print("-" * 30)
    
    response = create_error_response(
        ErrorCode.DOCUMENT_UPLOAD_ERROR,
        "文件上传失败",
        details={
            "filename": "large_file.pdf",
            "size": "50MB",
            "max_size": "10MB"
        }
    )
    print(f"状态码: {response.status_code}")
    print(f"响应体: {response.body.decode()}")
    
    # 3. 自定义状态码
    print("\n3. 自定义状态码")
    print("-" * 30)
    
    response = create_error_response(
        ErrorCode.QA_PROCESSING_ERROR,
        "问答服务暂时不可用",
        status_code=503
    )
    print(f"状态码: {response.status_code}")
    print(f"响应体: {response.body.decode()}")


def demo_global_error_handler():
    """演示全局错误处理器"""
    print("\n" + "=" * 60)
    print("全局错误处理器演示")
    print("=" * 60)
    
    # 使用全局错误处理器
    test_errors = [
        ValidationError("输入数据无效", field="age", value="-5"),
        DocumentNotFoundError("global_test_doc"),
        QATimeoutError("全局测试问题", 120)
    ]
    
    for i, error in enumerate(test_errors, 1):
        print(f"\n{i}. 全局处理 {error.__class__.__name__}")
        print("-" * 40)
        
        result = global_error_handler.handle_exception(error)
        print(f"状态码: {result['status_code']}")
        print(f"错误代码: {result['response']['error']['code']}")
        print(f"错误消息: {result['response']['error']['message']}")


async def demo_async_error_handling():
    """演示异步错误处理"""
    print("\n" + "=" * 60)
    print("异步错误处理演示")
    print("=" * 60)
    
    @handle_api_error
    async def async_function_with_error():
        await asyncio.sleep(0.1)  # 模拟异步操作
        raise QATimeoutError("异步问答超时", 30)
    
    @handle_api_error
    async def async_function_success():
        await asyncio.sleep(0.1)
        return {"result": "异步操作成功"}
    
    # 测试成功的异步函数
    print("\n1. 异步成功操作")
    print("-" * 30)
    result = await async_function_success()
    print(f"结果: {result}")
    
    # 测试异常的异步函数
    print("\n2. 异步异常操作")
    print("-" * 30)
    result = await async_function_with_error()
    print(f"结果类型: {type(result)}")
    if hasattr(result, 'status_code'):
        print(f"状态码: {result.status_code}")


def main():
    """主演示函数"""
    print("RAG系统统一错误处理机制演示")
    print("=" * 80)
    
    try:
        # 1. 异常类演示
        demo_exception_classes()
        
        # 2. 错误处理器演示
        demo_error_handler()
        
        # 3. 错误中间件演示
        demo_error_middleware()
        
        # 4. 错误响应创建演示
        demo_error_response_creation()
        
        # 5. 全局错误处理器演示
        demo_global_error_handler()
        
        # 6. 异步错误处理演示
        print("\n开始异步错误处理演示...")
        asyncio.run(demo_async_error_handling())
        
        print("\n" + "=" * 80)
        print("错误处理机制演示完成")
        print("=" * 80)
        
    except Exception as e:
        print(f"演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()