#!/usr/bin/env python3
"""
RAG Knowledge QA System - Main API Application
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 初始化日志配置
def setup_logging():
    """设置日志配置"""
    try:
        from rag_system.utils.logging_config import setup_logging as setup_rag_logging
        setup_rag_logging(
            log_level="DEBUG",
            log_dir="logs",
            enable_file_logging=True,
            enable_console_logging=True
        )
        print("✓ API日志配置初始化成功")
    except Exception as e:
        print(f"⚠ API日志配置失败: {e}")
        logging.basicConfig(level=logging.DEBUG)

# 初始化日志
setup_logging()
logger = logging.getLogger(__name__)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import uvicorn

# Import API routers
from fastapi import APIRouter

# Initialize routers
document_router = APIRouter(prefix="/documents", tags=["documents"])
qa_router = APIRouter(prefix="/qa", tags=["qa"])
config_router = APIRouter(prefix="/config", tags=["config"])
monitoring_router = APIRouter(prefix="/monitoring", tags=["monitoring"])
session_router = APIRouter(prefix="/sessions", tags=["sessions"])

# Try to import actual router implementations
try:
    from .document_api import router as doc_router
    document_router = doc_router
    print("✓ Document API router loaded")
except ImportError as e:
    print(f"⚠ Document API router not available: {e}")

try:
    from .qa_api import router as qa_api_router
    qa_router = qa_api_router
    print("✓ QA API router loaded")
except ImportError as e:
    print(f"⚠ QA API router not available: {e}")

try:
    from .config_api import router as config_api_router
    config_router = config_api_router
    print("✓ Config API router loaded")
except ImportError as e:
    print(f"⚠ Config API router not available: {e}")

try:
    from .monitoring_api import router as monitoring_api_router
    monitoring_router = monitoring_api_router
    print("✓ Monitoring API router loaded")
except ImportError as e:
    print(f"⚠ Monitoring API router not available: {e}")

try:
    from .session_api import router as session_api_router
    session_router = session_api_router
    print("✓ Session API router loaded")
except ImportError as e:
    print(f"⚠ Session API router not available: {e}")

try:
    from .model_manager_api import router as model_manager_router
    print("✓ Model Manager API router loaded")
except ImportError as e:
    print(f"⚠ Model Manager API router not available: {e}")
    # Create placeholder router
    model_manager_router = APIRouter(prefix="/models", tags=["models"])
    
    @model_manager_router.post("/add")
    async def add_model_placeholder(request: dict):
        return {"success": False, "message": "Model Manager API not available"}
    
    @model_manager_router.post("/test")
    async def test_model_placeholder(request: dict):
        return {"success": False, "message": "Model Manager API not available"}
    
    @model_manager_router.get("/configs")
    async def get_model_configs_placeholder():
        return {"success": False, "model_configs": {}, "message": "Model Manager API not available"}
    
    @model_manager_router.post("/switch")
    async def switch_model_placeholder(request: dict):
        return {"success": False, "message": "Model Manager API not available"}

# Add basic endpoints to placeholder routers if real ones aren't available
if not hasattr(document_router, '_routes') or len(document_router.routes) == 0:
    @document_router.get("/")
    async def list_documents():
        return {"message": "Document API placeholder", "documents": []}
    
    @document_router.get("/stats")
    async def document_stats():
        return {"total": 0, "ready": 0, "processing": 0, "error": 0}

if not hasattr(qa_router, '_routes') or len(qa_router.routes) == 0:
    @qa_router.post("/ask")
    async def ask_question(question: dict):
        return {
            "answer": "This is a mock response. The QA system is not fully configured yet.",
            "confidence": 0.5,
            "sources": []
        }

if not hasattr(config_router, '_routes') or len(config_router.routes) == 0:
    @config_router.get("/")
    async def get_config():
        return {
            "app": {"name": "RAG Knowledge QA System", "version": "1.0.0"},
            "status": "mock_config"
        }

if not hasattr(monitoring_router, '_routes') or len(monitoring_router.routes) == 0:
    @monitoring_router.get("/health")
    async def monitoring_health():
        return {
            "status": "healthy",
            "components": {
                "api": "up",
                "database": "unknown",
                "vector_store": "unknown"
            }
        }

if not hasattr(session_router, '_routes') or len(session_router.routes) == 0:
    from pydantic import BaseModel
    from typing import Optional
    
    class SessionCreateRequest(BaseModel):
        title: Optional[str] = None
        user_id: Optional[str] = None
    
    @session_router.post("/")
    async def create_session(request: SessionCreateRequest = SessionCreateRequest()):
        import uuid
        from datetime import datetime
        return {
            "session_id": str(uuid.uuid4()),
            "title": request.title,
            "user_id": request.user_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "qa_count": 0
        }
    
    @session_router.get("/recent")
    async def get_recent_sessions():
        return {"sessions": []}
    
    @session_router.get("/{session_id}/history")
    async def get_session_history(session_id: str):
        return []

# Initialize FastAPI app
app = FastAPI(
    title="RAG Knowledge QA System",
    description="A comprehensive knowledge question-answering system using RAG (Retrieval-Augmented Generation)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost,http://localhost:3000,http://localhost:8080").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(document_router)
app.include_router(qa_router)
app.include_router(config_router)
app.include_router(monitoring_router)
app.include_router(session_router)
app.include_router(model_manager_router)

# 挂载静态文件服务
try:
    # 挂载前端文件
    app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")
    # 挂载根目录文件（用于测试页面）
    app.mount("/static", StaticFiles(directory="."), name="static")
    logger.info("✅ 静态文件服务已配置")
except Exception as e:
    logger.warning(f"⚠️ 静态文件服务配置失败: {e}")

# 应用启动和关闭事件
@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("🚀 RAG Knowledge QA System API 启动中...")
    

    
    logger.info("📚 文档API路由已加载")
    logger.info("🤖 问答API路由已加载")
    logger.info("⚙️ 配置API路由已加载")
    logger.info("📊 监控API路由已加载")
    logger.info("💬 会话API路由已加载")
    logger.info("🔧 模型管理API路由已加载")
    logger.info("✅ RAG Knowledge QA System API 启动完成")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("🛑 RAG Knowledge QA System API 正在关闭...")
    

    logger.info("✅ RAG Knowledge QA System API 已关闭")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and load balancers"""
    logger.info("健康检查请求")
    return {
        "status": "healthy",
        "service": "RAG Knowledge QA System",
        "version": "1.0.0",
        "timestamp": "2024-01-01T00:00:00Z"
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with system information"""
    logger.info("根路径访问请求")
    return {
        "message": "RAG Knowledge QA System API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "documents": "/documents",
            "qa": "/qa",
            "config": "/config",
            "monitoring": "/monitoring",
            "sessions": "/sessions"
        }
    }

# Serve static files (frontend)
if os.path.exists("frontend"):
    app.mount("/static", StaticFiles(directory="frontend"), name="static")
    
    # Serve frontend index.html at root
    from fastapi.responses import FileResponse
    
    @app.get("/app")
    async def serve_frontend():
        return FileResponse("frontend/index.html")
    
    # Serve frontend files
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "type": type(exc).__name__
        }
    )

# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    print("🚀 RAG Knowledge QA System starting up...")
    print(f"📍 Environment: {os.getenv('ENVIRONMENT', 'development')}")
    print(f"🔧 Debug mode: {os.getenv('DEBUG', 'true')}")
    print(f"📊 Log level: {os.getenv('LOG_LEVEL', 'INFO')}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    print("🛑 RAG Knowledge QA System shutting down...")

if __name__ == "__main__":
    # Configuration from environment variables
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload = os.getenv("RELOAD", "false").lower() == "true"
    workers = int(os.getenv("API_WORKERS", "1"))
    
    print(f"🌐 Starting server on {host}:{port}")
    print(f"🔄 Reload: {reload}")
    print(f"👥 Workers: {workers}")
    
    if reload:
        # Development mode with auto-reload
        uvicorn.run(
            "rag_system.api.main:app",
            host=host,
            port=port,
            reload=reload,
            log_level=os.getenv("LOG_LEVEL", "info").lower()
        )
    else:
        # Production mode
        uvicorn.run(
            app,
            host=host,
            port=port,
            workers=workers,
            log_level=os.getenv("LOG_LEVEL", "info").lower()
        )