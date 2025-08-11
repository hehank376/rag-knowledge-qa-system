"""
通用工具函数
"""
import uuid
import hashlib
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path


def generate_id() -> str:
    """生成唯一ID"""
    return str(uuid.uuid4())


def generate_hash(content: str) -> str:
    """生成内容哈希"""
    return hashlib.md5(content.encode()).hexdigest()


def get_file_extension(filename: str) -> str:
    """获取文件扩展名"""
    return Path(filename).suffix.lower()


def get_current_timestamp() -> datetime:
    """获取当前时间戳"""
    return datetime.now()


def validate_file_type(filename: str, allowed_types: list) -> bool:
    """验证文件类型"""
    ext = get_file_extension(filename)
    return ext in allowed_types


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f}{size_names[i]}"


def safe_get(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    """安全获取字典值"""
    return data.get(key, default)


def create_metadata(doc_id: str, chunk_index: int, **kwargs) -> Dict[str, Any]:
    """创建元数据"""
    metadata = {
        "document_id": doc_id,
        "chunk_index": chunk_index,
        "created_at": get_current_timestamp().isoformat()
    }
    metadata.update(kwargs)
    return metadata