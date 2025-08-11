#!/usr/bin/env python3
"""
错误信息本地化支持
实现任务6.1：错误信息的标准化和本地化
"""
from typing import Dict, Any, Optional
from enum import Enum


class Language(str, Enum):
    """支持的语言"""
    ZH_CN = "zh_CN"  # 简体中文
    EN_US = "en_US"  # 英语
    ZH_TW = "zh_TW"  # 繁体中文


class ErrorMessageLocalizer:
    """错误信息本地化器"""
    
    def __init__(self, default_language: Language = Language.ZH_CN):
        self.default_language = default_language
        self.messages = self._load_messages()
    
    def _load_messages(self) -> Dict[str, Dict[str, str]]:
        """加载错误信息"""
        return {
            # 系统错误
            "SYSTEM_ERROR": {
                Language.ZH_CN: "系统内部错误",
                Language.EN_US: "Internal system error",
                Language.ZH_TW: "系統內部錯誤"
            },
            "SERVICE_UNAVAILABLE": {
                Language.ZH_CN: "服务暂时不可用",
                Language.EN_US: "Service temporarily unavailable",
                Language.ZH_TW: "服務暫時不可用"
            },
            
            # 检索错误
            "RETRIEVAL_ERROR": {
                Language.ZH_CN: "检索操作失败",
                Language.EN_US: "Retrieval operation failed",
                Language.ZH_TW: "檢索操作失敗"
            },
            "SEARCH_MODE_ERROR": {
                Language.ZH_CN: "搜索模式执行失败",
                Language.EN_US: "Search mode execution failed",
                Language.ZH_TW: "搜索模式執行失敗"
            },
            "SEARCH_FALLBACK_ERROR": {
                Language.ZH_CN: "搜索降级失败",
                Language.EN_US: "Search fallback failed",
                Language.ZH_TW: "搜索降級失敗"
            },
            
            # 重排序错误
            "RERANKING_ERROR": {
                Language.ZH_CN: "重排序操作失败",
                Language.EN_US: "Reranking operation failed",
                Language.ZH_TW: "重排序操作失敗"
            },
            "RERANKING_MODEL_ERROR": {
                Language.ZH_CN: "重排序模型加载失败",
                Language.EN_US: "Reranking model loading failed",
                Language.ZH_TW: "重排序模型載入失敗"
            },
            "RERANKING_COMPUTE_ERROR": {
                Language.ZH_CN: "重排序计算失败",
                Language.EN_US: "Reranking computation failed",
                Language.ZH_TW: "重排序計算失敗"
            },
            
            # 缓存错误
            "CACHE_ERROR": {
                Language.ZH_CN: "缓存操作失败",
                Language.EN_US: "Cache operation failed",
                Language.ZH_TW: "快取操作失敗"
            },
            "CACHE_CONNECTION_ERROR": {
                Language.ZH_CN: "缓存服务连接失败",
                Language.EN_US: "Cache service connection failed",
                Language.ZH_TW: "快取服務連接失敗"
            },
            "CACHE_OPERATION_ERROR": {
                Language.ZH_CN: "缓存操作执行失败",
                Language.EN_US: "Cache operation execution failed",
                Language.ZH_TW: "快取操作執行失敗"
            },
            
            # 配置错误
            "CONFIG_ERROR": {
                Language.ZH_CN: "配置错误",
                Language.EN_US: "Configuration error",
                Language.ZH_TW: "配置錯誤"
            },
            "CONFIG_LOAD_ERROR": {
                Language.ZH_CN: "配置加载失败",
                Language.EN_US: "Configuration loading failed",
                Language.ZH_TW: "配置載入失敗"
            },
            "CONFIG_VALIDATION_ERROR": {
                Language.ZH_CN: "配置验证失败",
                Language.EN_US: "Configuration validation failed",
                Language.ZH_TW: "配置驗證失敗"
            },
            
            # 认证授权错误
            "AUTH_ERROR": {
                Language.ZH_CN: "认证失败",
                Language.EN_US: "Authentication failed",
                Language.ZH_TW: "認證失敗"
            },
            "AUTHZ_ERROR": {
                Language.ZH_CN: "权限不足",
                Language.EN_US: "Insufficient permissions",
                Language.ZH_TW: "權限不足"
            },
            
            # 数据错误
            "VALIDATION_ERROR": {
                Language.ZH_CN: "数据验证失败",
                Language.EN_US: "Data validation failed",
                Language.ZH_TW: "數據驗證失敗"
            },
            "NOT_FOUND": {
                Language.ZH_CN: "资源不存在",
                Language.EN_US: "Resource not found",
                Language.ZH_TW: "資源不存在"
            },
            "CONFLICT": {
                Language.ZH_CN: "资源冲突",
                Language.EN_US: "Resource conflict",
                Language.ZH_TW: "資源衝突"
            },
            
            # 数据库错误
            "DATABASE_ERROR": {
                Language.ZH_CN: "数据库操作失败",
                Language.EN_US: "Database operation failed",
                Language.ZH_TW: "數據庫操作失敗"
            },
            
            # 文档处理错误
            "DOCUMENT_ERROR": {
                Language.ZH_CN: "文档处理失败",
                Language.EN_US: "Document processing failed",
                Language.ZH_TW: "文檔處理失敗"
            },
            
            # 向量存储错误
            "VECTOR_STORE_ERROR": {
                Language.ZH_CN: "向量存储操作失败",
                Language.EN_US: "Vector store operation failed",
                Language.ZH_TW: "向量存儲操作失敗"
            },
            
            # 嵌入向量错误
            "EMBEDDING_ERROR": {
                Language.ZH_CN: "嵌入向量处理失败",
                Language.EN_US: "Embedding processing failed",
                Language.ZH_TW: "嵌入向量處理失敗"
            },
            
            # 问答错误
            "QA_ERROR": {
                Language.ZH_CN: "问答处理失败",
                Language.EN_US: "Q&A processing failed",
                Language.ZH_TW: "問答處理失敗"
            },
            
            # 会话错误
            "SESSION_ERROR": {
                Language.ZH_CN: "会话处理失败",
                Language.EN_US: "Session processing failed",
                Language.ZH_TW: "會話處理失敗"
            },
            
            # 处理错误
            "PROCESSING_ERROR": {
                Language.ZH_CN: "处理操作失败",
                Language.EN_US: "Processing operation failed",
                Language.ZH_TW: "處理操作失敗"
            },
            
            # 频率限制错误
            "RATE_LIMIT": {
                Language.ZH_CN: "请求频率过高",
                Language.EN_US: "Request rate too high",
                Language.ZH_TW: "請求頻率過高"
            }
        }
    
    def get_message(self, error_code: str, language: Optional[Language] = None, **kwargs) -> str:
        """获取本地化错误信息"""
        if language is None:
            language = self.default_language
        
        # 获取错误信息模板
        error_messages = self.messages.get(error_code, {})
        message_template = error_messages.get(language)
        
        # 如果没有找到指定语言的消息，使用默认语言
        if message_template is None:
            message_template = error_messages.get(self.default_language)
        
        # 如果还是没有找到，使用错误代码作为消息
        if message_template is None:
            message_template = error_code
        
        # 格式化消息（支持参数替换）
        try:
            return message_template.format(**kwargs)
        except (KeyError, ValueError):
            return message_template
    
    def get_suggestion(self, error_code: str, language: Optional[Language] = None) -> str:
        """获取错误处理建议"""
        if language is None:
            language = self.default_language
        
        suggestions = {
            "SEARCH_MODE_ERROR": {
                Language.ZH_CN: "请检查搜索模式配置，或尝试使用语义搜索模式",
                Language.EN_US: "Please check search mode configuration or try semantic search mode",
                Language.ZH_TW: "請檢查搜索模式配置，或嘗試使用語義搜索模式"
            },
            "RERANKING_MODEL_ERROR": {
                Language.ZH_CN: "请检查重排序模型安装，或考虑禁用重排序功能",
                Language.EN_US: "Please check reranking model installation or consider disabling reranking",
                Language.ZH_TW: "請檢查重排序模型安裝，或考慮禁用重排序功能"
            },
            "CACHE_CONNECTION_ERROR": {
                Language.ZH_CN: "请检查Redis服务状态，或考虑禁用缓存功能",
                Language.EN_US: "Please check Redis service status or consider disabling cache",
                Language.ZH_TW: "請檢查Redis服務狀態，或考慮禁用快取功能"
            },
            "CONFIG_LOAD_ERROR": {
                Language.ZH_CN: "请检查配置文件是否存在且格式正确",
                Language.EN_US: "Please check if configuration file exists and is properly formatted",
                Language.ZH_TW: "請檢查配置文件是否存在且格式正確"
            }
        }
        
        error_suggestions = suggestions.get(error_code, {})
        return error_suggestions.get(language, error_suggestions.get(self.default_language, ""))
    
    def set_default_language(self, language: Language) -> None:
        """设置默认语言"""
        self.default_language = language
    
    def add_custom_message(self, error_code: str, messages: Dict[Language, str]) -> None:
        """添加自定义错误信息"""
        if error_code not in self.messages:
            self.messages[error_code] = {}
        
        self.messages[error_code].update(messages)


# 全局本地化器实例
global_localizer = ErrorMessageLocalizer()


# 便捷函数
def get_localized_message(error_code: str, language: Optional[Language] = None, **kwargs) -> str:
    """获取本地化错误信息的便捷函数"""
    return global_localizer.get_message(error_code, language, **kwargs)


def get_localized_suggestion(error_code: str, language: Optional[Language] = None) -> str:
    """获取本地化建议的便捷函数"""
    return global_localizer.get_suggestion(error_code, language)


def set_default_language(language: Language) -> None:
    """设置默认语言的便捷函数"""
    global_localizer.set_default_language(language)


def add_custom_message(error_code: str, messages: Dict[Language, str]) -> None:
    """添加自定义错误信息的便捷函数"""
    global_localizer.add_custom_message(error_code, messages)


# 错误信息格式化工具
class ErrorMessageFormatter:
    """错误信息格式化工具"""
    
    @staticmethod
    def format_user_friendly_message(error_code: str, original_message: str, language: Optional[Language] = None) -> str:
        """格式化用户友好的错误信息"""
        localized_message = get_localized_message(error_code, language)
        suggestion = get_localized_suggestion(error_code, language)
        
        if suggestion:
            return f"{localized_message}。{suggestion}"
        else:
            return localized_message
    
    @staticmethod
    def format_technical_message(error_code: str, original_message: str, context: Dict[str, Any]) -> str:
        """格式化技术性错误信息"""
        parts = [f"错误代码: {error_code}"]
        
        if original_message:
            parts.append(f"错误信息: {original_message}")
        
        if context:
            context_str = ", ".join([f"{k}={v}" for k, v in context.items() if v is not None])
            if context_str:
                parts.append(f"上下文: {context_str}")
        
        return " | ".join(parts)
    
    @staticmethod
    def format_api_error_response(error_code: str, message: str, language: Optional[Language] = None) -> Dict[str, Any]:
        """格式化API错误响应"""
        return {
            "error": {
                "code": error_code,
                "message": get_localized_message(error_code, language) if error_code in global_localizer.messages else message,
                "original_message": message,
                "suggestion": get_localized_suggestion(error_code, language)
            }
        }