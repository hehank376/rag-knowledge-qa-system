"""
文本预处理器
"""
import logging
import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PreprocessConfig:
    """预处理配置"""
    remove_extra_whitespace: bool = True
    remove_special_chars: bool = False
    normalize_unicode: bool = True
    remove_urls: bool = True
    remove_emails: bool = True
    remove_phone_numbers: bool = False
    convert_to_lowercase: bool = False
    remove_stopwords: bool = False
    language: str = "zh"  # 语言设置
    custom_patterns: List[str] = None  # 自定义清理模式


class BasePreprocessor(ABC):
    """文本预处理器基类"""
    
    def __init__(self, config: Optional[PreprocessConfig] = None):
        self.config = config or PreprocessConfig()
    
    @abstractmethod
    def process(self, text: str) -> str:
        """处理文本"""
        pass


class WhitespaceNormalizer(BasePreprocessor):
    """空白字符标准化器"""
    
    def process(self, text: str) -> str:
        """标准化空白字符"""
        if not text:
            return text
        
        # 先标准化段落分隔符
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # 将连续的空格和制表符统一为单个空格，但保留换行符
        text = re.sub(r'[ \t]+', ' ', text)
        
        # 移除行首行尾空白，但保留换行符结构
        lines = text.split('\n')
        lines = [line.strip() for line in lines]
        text = '\n'.join(lines)
        
        return text


class SpecialCharCleaner(BasePreprocessor):
    """特殊字符清理器"""
    
    def process(self, text: str) -> str:
        """清理特殊字符"""
        if not text:
            return text
        
        # 移除控制字符（保留换行符和制表符）
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # 移除零宽字符
        text = re.sub(r'[\u200B-\u200D\uFEFF]', '', text)
        
        # 可选：移除其他特殊字符
        if self.config.remove_special_chars:
            # 保留基本标点符号，移除其他特殊字符
            text = re.sub(r'[^\w\s\u4e00-\u9fff.,!?;:()[\]{}"\'`~@#$%^&*+=|\\/<>-]', '', text)
        
        return text


class UnicodeNormalizer(BasePreprocessor):
    """Unicode标准化器"""
    
    def process(self, text: str) -> str:
        """标准化Unicode字符"""
        if not text:
            return text
        
        import unicodedata
        
        # 标准化Unicode（NFC形式）
        text = unicodedata.normalize('NFC', text)
        
        # 转换全角字符为半角
        text = self._convert_fullwidth_to_halfwidth(text)
        
        return text
    
    def _convert_fullwidth_to_halfwidth(self, text: str) -> str:
        """转换全角字符为半角字符"""
        result = []
        for char in text:
            code = ord(char)
            # 全角字符范围
            if 0xFF01 <= code <= 0xFF5E:
                # 转换为对应的半角字符
                result.append(chr(code - 0xFEE0))
            elif code == 0x3000:  # 全角空格
                result.append(' ')
            else:
                result.append(char)
        return ''.join(result)


class URLEmailCleaner(BasePreprocessor):
    """URL和邮箱清理器"""
    
    def process(self, text: str) -> str:
        """清理URL和邮箱地址"""
        if not text:
            return text
        
        if self.config.remove_urls:
            # 移除URL
            url_pattern = r'https?://[^\s<>"{}|\\^`[\]]+|www\.[^\s<>"{}|\\^`[\]]+'
            text = re.sub(url_pattern, '', text, flags=re.IGNORECASE)
        
        if self.config.remove_emails:
            # 移除邮箱地址
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            text = re.sub(email_pattern, '', text)
        
        if self.config.remove_phone_numbers:
            # 移除电话号码（简单模式）
            phone_patterns = [
                r'\b\d{3}-\d{3}-\d{4}\b',  # 123-456-7890
                r'\b\d{3}\.\d{3}\.\d{4}\b',  # 123.456.7890
                r'\b\d{10}\b',  # 1234567890
                r'\b\d{3}\s\d{3}\s\d{4}\b',  # 123 456 7890
                r'\+\d{1,3}\s?\d{3,4}\s?\d{3,4}\s?\d{3,4}',  # 国际格式
            ]
            
            for pattern in phone_patterns:
                text = re.sub(pattern, '', text)
        
        return text


class CustomPatternCleaner(BasePreprocessor):
    """自定义模式清理器"""
    
    def process(self, text: str) -> str:
        """使用自定义模式清理文本"""
        if not text or not self.config.custom_patterns:
            return text
        
        for pattern in self.config.custom_patterns:
            try:
                text = re.sub(pattern, '', text, flags=re.IGNORECASE)
            except re.error as e:
                logger.warning(f"无效的正则表达式模式: {pattern}, 错误: {str(e)}")
                continue
        
        return text


class StopwordRemover(BasePreprocessor):
    """停用词移除器"""
    
    def __init__(self, config: Optional[PreprocessConfig] = None):
        super().__init__(config)
        self.stopwords = self._load_stopwords()
    
    def process(self, text: str) -> str:
        """移除停用词"""
        if not text or not self.config.remove_stopwords:
            return text
        
        # 简单的词分割（可以根据需要改进）
        words = re.findall(r'\b\w+\b', text.lower())
        filtered_words = [word for word in words if word not in self.stopwords]
        
        # 重建文本（简化处理）
        return ' '.join(filtered_words)
    
    def _load_stopwords(self) -> Set[str]:
        """加载停用词列表"""
        # 中文停用词
        chinese_stopwords = {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
            '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
            '自己', '这', '那', '里', '就是', '还', '把', '比', '或者', '因为', '所以',
            '但是', '如果', '这样', '那样', '什么', '怎么', '为什么', '哪里', '哪个'
        }
        
        # 英文停用词
        english_stopwords = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from', 'has',
            'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the', 'to', 'was',
            'will', 'with', 'the', 'this', 'but', 'they', 'have', 'had', 'what',
            'said', 'each', 'which', 'she', 'do', 'how', 'their', 'if', 'up', 'out',
            'many', 'then', 'them', 'these', 'so', 'some', 'her', 'would', 'make',
            'like', 'into', 'him', 'time', 'two', 'more', 'go', 'no', 'way', 'could'
        }
        
        if self.config.language == "zh":
            return chinese_stopwords
        elif self.config.language == "en":
            return english_stopwords
        else:
            return chinese_stopwords.union(english_stopwords)


class TextPreprocessor:
    """文本预处理器主类"""
    
    def __init__(self, config: Optional[PreprocessConfig] = None):
        self.config = config or PreprocessConfig()
        self.processors = self._initialize_processors()
    
    def _initialize_processors(self) -> List[BasePreprocessor]:
        """初始化预处理器列表"""
        processors = []
        
        # 按顺序添加预处理器
        if self.config.normalize_unicode:
            processors.append(UnicodeNormalizer(self.config))
        
        processors.append(SpecialCharCleaner(self.config))
        
        if self.config.remove_urls or self.config.remove_emails or self.config.remove_phone_numbers:
            processors.append(URLEmailCleaner(self.config))
        
        if self.config.custom_patterns:
            processors.append(CustomPatternCleaner(self.config))
        
        if self.config.remove_extra_whitespace:
            processors.append(WhitespaceNormalizer(self.config))
        
        if self.config.remove_stopwords:
            processors.append(StopwordRemover(self.config))
        
        return processors
    
    def process(self, text: str) -> str:
        """处理文本"""
        if not text:
            return text
        
        logger.debug(f"开始预处理文本，长度: {len(text)}")
        
        processed_text = text
        
        # 依次应用所有预处理器
        for processor in self.processors:
            try:
                processed_text = processor.process(processed_text)
            except Exception as e:
                logger.warning(f"预处理器 {processor.__class__.__name__} 处理失败: {str(e)}")
                continue
        
        # 可选：转换为小写
        if self.config.convert_to_lowercase:
            processed_text = processed_text.lower()
        
        # 最终清理
        processed_text = self._final_cleanup(processed_text)
        
        logger.debug(f"预处理完成，处理后长度: {len(processed_text)}")
        
        return processed_text
    
    def _final_cleanup(self, text: str) -> str:
        """最终清理"""
        if not text:
            return text
        
        # 移除多余的空行
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # 移除首尾空白
        text = text.strip()
        
        return text
    
    def process_batch(self, texts: List[str]) -> List[str]:
        """批量处理文本"""
        return [self.process(text) for text in texts]
    
    def add_custom_processor(self, processor: BasePreprocessor):
        """添加自定义预处理器"""
        self.processors.append(processor)
    
    def get_processing_stats(self, original_text: str, processed_text: str) -> Dict[str, Any]:
        """获取处理统计信息"""
        return {
            "original_length": len(original_text),
            "processed_length": len(processed_text),
            "reduction_ratio": 1 - (len(processed_text) / len(original_text)) if original_text else 0,
            "original_word_count": len(re.findall(r'\b\w+\b', original_text)),
            "processed_word_count": len(re.findall(r'\b\w+\b', processed_text)),
            "processors_used": [p.__class__.__name__ for p in self.processors]
        }