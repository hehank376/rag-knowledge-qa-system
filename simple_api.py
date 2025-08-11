#!/usr/bin/env python3
"""
RAG Knowledge QA System - Simple API for Testing
简化版API用于测试前端连接
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import os

# Initialize FastAPI app
app = FastAPI(
    title="RAG Knowledge QA System",
    description="A comprehensive knowledge question-answering system using RAG",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源用于测试
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class QuestionRequest(BaseModel):
    question: str
    session_id: Optional[str] = None

class SessionRequest(BaseModel):
    title: Optional[str] = None

class DocumentStats(BaseModel):
    total: int = 0
    ready: int = 0
    processing: int = 0
    error: int = 0

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with system information"""
    return {
        "message": "RAG Knowledge QA System API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "documents": "/api/documents",
            "qa": "/api/qa",
            "config": "/api/config",
            "monitoring": "/api/monitoring"
        }
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "RAG Knowledge QA System",
        "version": "1.0.0",
        "timestamp": "2024-01-01T00:00:00Z"
    }

# Document API endpoints
@app.get("/api/documents/")
async def list_documents():
    """获取文档列表"""
    return {
        "documents": [
            {
                "id": "doc1",
                "filename": "sample.pdf",
                "status": "ready",
                "upload_time": "2024-01-01T10:00:00Z",
                "file_size": 1024000
            },
            {
                "id": "doc2", 
                "filename": "example.txt",
                "status": "processing",
                "upload_time": "2024-01-01T11:00:00Z",
                "file_size": 2048
            }
        ],
        "total_count": 2,
        "ready_count": 1,
        "processing_count": 1,
        "error_count": 0
    }

@app.get("/api/documents/stats")
async def document_stats():
    """获取文档统计"""
    return DocumentStats(
        total=2,
        ready=1,
        processing=1,
        error=0
    )

@app.post("/api/documents/upload")
async def upload_document():
    """上传文档（演示版本）"""
    return {
        "message": "文档上传成功（演示模式）",
        "document": {
            "id": "demo_doc_123",
            "filename": "demo_document.pdf",
            "status": "processing",
            "upload_time": "2024-01-01T12:00:00Z",
            "file_size": 1024000
        }
    }

@app.delete("/api/documents/{document_id}")
async def delete_document(document_id: str):
    """删除文档"""
    return {"message": f"Document {document_id} deleted successfully"}

# Session API endpoints
@app.get("/api/sessions/")
async def list_sessions():
    """获取会话列表"""
    return {
        "sessions": [
            {
                "id": "session1",
                "title": "测试会话1",
                "created_at": "2024-01-01T10:00:00Z",
                "question_count": 5
            },
            {
                "id": "session2",
                "title": "测试会话2", 
                "created_at": "2024-01-01T11:00:00Z",
                "question_count": 3
            }
        ],
        "total_count": 2
    }

@app.get("/api/sessions/paginated")
async def list_sessions_paginated():
    """获取分页会话列表"""
    return {
        "sessions": [
            {
                "id": "session1",
                "title": "测试会话1",
                "created_at": "2024-01-01T10:00:00Z",
                "question_count": 5
            },
            {
                "id": "session2",
                "title": "测试会话2", 
                "created_at": "2024-01-01T11:00:00Z",
                "question_count": 3
            }
        ],
        "total_count": 2,
        "page": 1,
        "per_page": 10,
        "total_pages": 1
    }

@app.post("/api/sessions/")
async def create_session(request: SessionRequest):
    """创建新会话"""
    return {
        "id": "new_session_123",
        "title": request.title or "新会话",
        "created_at": "2024-01-01T12:00:00Z",
        "question_count": 0
    }

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    return {"message": f"Session {session_id} deleted successfully"}

@app.get("/api/sessions/stats")
async def session_stats():
    """获取会话统计"""
    return {
        "total_sessions": 2,
        "total_questions": 8,
        "today_sessions": 1,
        "avg_response_time": "1.2s"
    }

@app.get("/api/sessions/all")
async def get_all_sessions():
    """获取所有会话（用于导出）"""
    return {
        "sessions": [
            {
                "id": "session1",
                "title": "测试会话1",
                "created_at": "2024-01-01T10:00:00Z",
                "question_count": 5,
                "history": [
                    {"question": "什么是RAG？", "answer": "RAG是检索增强生成技术..."},
                    {"question": "如何使用？", "answer": "您可以通过上传文档..."}
                ]
            },
            {
                "id": "session2",
                "title": "测试会话2", 
                "created_at": "2024-01-01T11:00:00Z",
                "question_count": 3,
                "history": [
                    {"question": "系统功能？", "answer": "系统提供智能问答功能..."}
                ]
            }
        ]
    }

@app.delete("/api/sessions/clear")
async def clear_all_sessions():
    """清空所有会话"""
    return {"message": "所有会话已清空", "cleared_count": 2}

@app.get("/api/sessions/{session_id}/history")
async def get_session_history(session_id: str):
    """获取会话历史记录"""
    return {
        "session_id": session_id,
        "history": [
            {
                "id": "qa1",
                "question": "什么是RAG技术？",
                "answer": "RAG（检索增强生成）是一种结合了信息检索和文本生成的AI技术...",
                "confidence": 0.9,
                "sources": [{"document": "rag_intro.pdf", "page": 1}],
                "timestamp": "2024-01-01T10:30:00Z"
            },
            {
                "id": "qa2", 
                "question": "如何实现RAG系统？",
                "answer": "实现RAG系统需要以下步骤：1. 文档预处理 2. 向量化 3. 检索 4. 生成...",
                "confidence": 0.85,
                "sources": [{"document": "rag_implementation.pdf", "page": 3}],
                "timestamp": "2024-01-01T10:35:00Z"
            }
        ]
    }

# QA API endpoints
@app.post("/api/qa/ask")
async def ask_question(request: QuestionRequest):
    """问答接口"""
    return {
        "answer": f"这是对问题「{request.question}」的模拟回答。在实际系统中，这里会基于上传的文档内容生成智能回答。",
        "confidence": 0.85,
        "sources": [
            {
                "document_id": "doc1",
                "document_name": "sample.pdf",
                "chunk_text": "相关文档片段内容...",
                "similarity": 0.92
            }
        ],
        "session_id": request.session_id or "default_session",
        "response_time": 1.2
    }

# Config API endpoints
@app.get("/api/config/")
async def get_config():
    """获取系统配置"""
    return {
        "app": {
            "name": "RAG Knowledge QA System",
            "version": "1.0.0",
            "environment": "development"
        },
        "llm": {
            "provider": "mock",
            "model": "mock-model",
            "temperature": 0.7
        },
        "embedding": {
            "provider": "mock",
            "model": "mock-embedding",
            "dimension": 384
        },
        "retrieval": {
            "top_k": 5,
            "similarity_threshold": 0.7
        }
    }

@app.put("/api/config/{section}")
async def update_config(section: str, config: dict):
    """更新配置"""
    return {
        "message": f"Configuration section '{section}' updated successfully",
        "section": section,
        "config": config
    }

# Monitoring API endpoints
@app.get("/api/monitoring/health")
async def monitoring_health():
    """监控健康状态"""
    return {
        "status": "healthy",
        "components": {
            "api": "up",
            "database": "up",
            "vector_store": "up",
            "llm_service": "up"
        },
        "uptime": "2h 30m",
        "memory_usage": "45%",
        "cpu_usage": "12%"
    }

@app.get("/api/monitoring/metrics")
async def get_metrics():
    """获取系统指标"""
    return {
        "requests_per_minute": 25,
        "average_response_time": 1.2,
        "error_rate": 0.02,
        "active_sessions": 3,
        "documents_processed": 15
    }

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "type": type(exc).__name__
        }
    )

if __name__ == "__main__":
    print("🚀 启动RAG知识问答系统简化API服务器...")
    print("🌐 服务地址: http://localhost:8000")
    print("📚 API文档: http://localhost:8000/docs")
    print("🧪 这是一个用于测试的简化版本")
    print("=" * 50)
    
    uvicorn.run(
        "simple_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )