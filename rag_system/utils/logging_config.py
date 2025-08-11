"""
日志配置模块
实现任务9.1：统一错误处理机制
"""
import os
import logging
import logging.config
from pathlib import Path
from typing import Dict, Any


def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    enable_file_logging: bool = True,
    enable_console_logging: bool = True
) -> None:
    """
    设置系统日志配置
    
    Args:
        log_level: 日志级别
        log_dir: 日志文件目录
        enable_file_logging: 是否启用文件日志
        enable_console_logging: 是否启用控制台日志
    """
    # 创建日志目录
    if enable_file_logging:
        Path(log_dir).mkdir(exist_ok=True)
    
    # 日志配置字典
    config = get_logging_config(
        log_level=log_level,
        log_dir=log_dir,
        enable_file_logging=enable_file_logging,
        enable_console_logging=enable_console_logging
    )
    
    # 应用配置
    logging.config.dictConfig(config)


def get_logging_config(
    log_level: str = "INFO",
    log_dir: str = "logs",
    enable_file_logging: bool = True,
    enable_console_logging: bool = True
) -> Dict[str, Any]:
    """
    获取日志配置字典
    
    Args:
        log_level: 日志级别
        log_dir: 日志文件目录
        enable_file_logging: 是否启用文件日志
        enable_console_logging: 是否启用控制台日志
        
    Returns:
        日志配置字典
    """
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "json": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(filename)s:%(lineno)d",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {},
        "loggers": {
            "rag_system": {
                "level": log_level,
                "handlers": [],
                "propagate": False
            },
            "rag_system.errors": {
                "level": "WARNING",
                "handlers": [],
                "propagate": False
            },
            "rag_system.api": {
                "level": log_level,
                "handlers": [],
                "propagate": False
            },
            "rag_system.services": {
                "level": log_level,
                "handlers": [],
                "propagate": False
            }
        },
        "root": {
            "level": log_level,
            "handlers": []
        }
    }
    
    handlers = []
    
    # 控制台处理器
    if enable_console_logging:
        config["handlers"]["console"] = {
            "class": "logging.StreamHandler",
            "level": log_level,
            "formatter": "standard",
            "stream": "ext://sys.stdout"
        }
        handlers.append("console")
    
    # 文件处理器
    if enable_file_logging:
        # 应用日志文件
        config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": log_level,
            "formatter": "detailed",
            "filename": os.path.join(log_dir, "rag_system.log"),
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "encoding": "utf-8"
        }
        
        # 错误日志文件
        config["handlers"]["error_file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "detailed",
            "filename": os.path.join(log_dir, "errors.log"),
            "maxBytes": 10485760,  # 10MB
            "backupCount": 10,
            "encoding": "utf-8"
        }
        
        # API访问日志文件
        config["handlers"]["api_file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "json",
            "filename": os.path.join(log_dir, "api_access.log"),
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "encoding": "utf-8"
        }
        
        handlers.extend(["file", "error_file"])
        
        # 为特定日志器添加处理器
        config["loggers"]["rag_system.errors"]["handlers"] = ["error_file", "console"] if enable_console_logging else ["error_file"]
        config["loggers"]["rag_system.api"]["handlers"] = ["api_file", "console"] if enable_console_logging else ["api_file"]
    
    # 为所有日志器添加处理器
    for logger_name in config["loggers"]:
        if not config["loggers"][logger_name]["handlers"]:
            config["loggers"][logger_name]["handlers"] = handlers
    
    config["root"]["handlers"] = handlers
    
    return config


def get_logger(name: str) -> logging.Logger:
    """
    获取日志记录器（企业级配置）
    需要预先调用setup_logging()进行配置
    
    Args:
        name: 日志记录器名称
        
    Returns:
        日志记录器实例
    """
    return logging.getLogger(name)


def get_simple_logger(name: str = __name__) -> logging.Logger:
    """
    获取简单配置的日志记录器
    自动初始化基本配置，适用于测试和开发环境
    
    Args:
        name: 日志记录器名称
        
    Returns:
        logging.Logger: 日志记录器实例
    """
    logger = logging.getLogger(name)
    
    # 检查是否已经配置过全局日志系统
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        # 使用简化配置进行初始化
        setup_logging(
            log_level="INFO",
            enable_file_logging=False,  # 测试环境不需要文件日志
            enable_console_logging=True
        )
    
    return logging.getLogger(name)


def log_api_access(
    method: str,
    url: str,
    status_code: int,
    response_time: float,
    client_ip: str = None,
    user_agent: str = None,
    request_id: str = None
) -> None:
    """
    记录API访问日志
    
    Args:
        method: HTTP方法
        url: 请求URL
        status_code: 响应状态码
        response_time: 响应时间（秒）
        client_ip: 客户端IP
        user_agent: 用户代理
        request_id: 请求ID
    """
    logger = get_logger("rag_system.api")
    
    log_data = {
        "method": method,
        "url": url,
        "status_code": status_code,
        "response_time": response_time,
        "client_ip": client_ip,
        "user_agent": user_agent,
        "request_id": request_id
    }
    
    # 过滤None值
    log_data = {k: v for k, v in log_data.items() if v is not None}
    
    logger.info("API访问", extra=log_data)


def log_error_with_context(
    logger: logging.Logger,
    error: Exception,
    context: Dict[str, Any] = None,
    level: str = "error"
) -> None:
    """
    记录带上下文的错误日志
    
    Args:
        logger: 日志记录器
        error: 异常对象
        context: 上下文信息
        level: 日志级别
    """
    import traceback
    from .exceptions import RAGSystemError
    
    log_data = {
        "error_type": error.__class__.__name__,
        "error_message": str(error),
        "traceback": traceback.format_exc()
    }
    
    if isinstance(error, RAGSystemError):
        log_data.update({
            "error_code": error.error_code.value,
            "details": error.details
        })
    
    if context:
        log_data.update(context)
    
    log_method = getattr(logger, level.lower(), logger.error)
    log_method(f"错误记录: {error}", extra=log_data)


class ContextFilter(logging.Filter):
    """上下文过滤器，为日志记录添加上下文信息"""
    
    def __init__(self, context: Dict[str, Any] = None):
        super().__init__()
        self.context = context or {}
    
    def filter(self, record):
        """为日志记录添加上下文信息"""
        for key, value in self.context.items():
            setattr(record, key, value)
        return True


class RequestContextFilter(logging.Filter):
    """请求上下文过滤器，为API请求添加上下文信息"""
    
    def filter(self, record):
        """为日志记录添加请求上下文信息"""
        # 这里可以从请求上下文中获取信息
        # 例如：request_id, user_id, session_id等
        # 实际实现需要根据具体的请求上下文管理方式
        
        # 示例：添加默认的请求ID
        if not hasattr(record, 'request_id'):
            import uuid
            record.request_id = str(uuid.uuid4())[:8]
        
        return True


def configure_uvicorn_logging():
    """配置Uvicorn日志"""
    # 禁用Uvicorn的默认访问日志，使用我们自己的
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.disabled = True
    
    # 配置Uvicorn错误日志
    uvicorn_error = logging.getLogger("uvicorn.error")
    uvicorn_error.setLevel(logging.WARNING)


# 预定义的日志配置
DEVELOPMENT_CONFIG = {
    "log_level": "DEBUG",
    "enable_file_logging": True,
    "enable_console_logging": True
}

PRODUCTION_CONFIG = {
    "log_level": "INFO",
    "enable_file_logging": True,
    "enable_console_logging": False
}

TESTING_CONFIG = {
    "log_level": "WARNING",
    "enable_file_logging": False,
    "enable_console_logging": True
}