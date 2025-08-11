"""
文本预处理器测试
"""
import pytest

from rag_system.document_processing.preprocessors import (
    TextPreprocessor, PreprocessConfig, WhitespaceNormalizer,
    SpecialCharCleaner, UnicodeNormalizer, URLEmailCleaner,
    CustomPatternCleaner, StopwordRemover
)


class TestPreprocessConfig:
    """预处理配置测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = PreprocessConfig()
        
        assert config.remove_extra_whitespace is True
        assert config.remove_special_chars is False
        assert config.normalize_unicode is True
        assert config.remove_urls is True
        assert config.remove_emails is True
        assert config.remove_phone_numbers is False
        assert config.convert_to_lowercase is False
        assert config.remove_stopwords is False
        assert config.language == "zh"
        assert config.custom_patterns is None
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = PreprocessConfig(
            remove_special_chars=True,
            convert_to_lowercase=True,
            remove_stopwords=True,
            language="en",
            custom_patterns=[r'\d+']
        )
        
        assert config.remove_special_chars is True
        assert config.convert_to_lowercase is True
        assert config.remove_stopwords is True
        assert config.language == "en"
        assert config.custom_patterns == [r'\d+']


class TestWhitespaceNormalizer:
    """空白字符标准化器测试"""
    
    def test_normalize_whitespace(self):
        """测试空白字符标准化"""
        normalizer = WhitespaceNormalizer()
        
        text = "这是    一个\t\t测试\n\n\n文本。"
        result = normalizer.process(text)
        
        assert result == "这是 一个 测试\n\n文本。"
    
    def test_remove_leading_trailing_whitespace(self):
        """测试移除首尾空白"""
        normalizer = WhitespaceNormalizer()
        
        text = "   这是测试文本   "
        result = normalizer.process(text)
        
        assert result == "这是测试文本"
    
    def test_normalize_paragraph_separators(self):
        """测试标准化段落分隔符"""
        normalizer = WhitespaceNormalizer()
        
        text = "第一段\n\n\n\n第二段\n\n\n\n\n第三段"
        result = normalizer.process(text)
        
        assert result == "第一段\n\n第二段\n\n第三段"
    
    def test_empty_text(self):
        """测试空文本处理"""
        normalizer = WhitespaceNormalizer()
        
        assert normalizer.process("") == ""
        assert normalizer.process(None) is None


class TestSpecialCharCleaner:
    """特殊字符清理器测试"""
    
    def test_remove_control_characters(self):
        """测试移除控制字符"""
        cleaner = SpecialCharCleaner()
        
        text = "正常文本\x00控制字符\x1F测试"
        result = cleaner.process(text)
        
        assert result == "正常文本控制字符测试"
    
    def test_remove_zero_width_characters(self):
        """测试移除零宽字符"""
        cleaner = SpecialCharCleaner()
        
        text = "文本\u200B零宽\u200C字符\uFEFF测试"
        result = cleaner.process(text)
        
        assert result == "文本零宽字符测试"
    
    def test_remove_special_chars_option(self):
        """测试移除特殊字符选项"""
        config = PreprocessConfig(remove_special_chars=True)
        cleaner = SpecialCharCleaner(config)
        
        text = "正常文本★特殊符号※测试"
        result = cleaner.process(text)
        
        # 应该保留基本标点，移除特殊符号
        assert "★" not in result
        assert "※" not in result
        assert "正常文本" in result
        assert "测试" in result


class TestUnicodeNormalizer:
    """Unicode标准化器测试"""
    
    def test_unicode_normalization(self):
        """测试Unicode标准化"""
        normalizer = UnicodeNormalizer()
        
        # 使用组合字符
        text = "café"  # 可能包含组合字符
        result = normalizer.process(text)
        
        # 结果应该是标准化的
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_fullwidth_to_halfwidth_conversion(self):
        """测试全角到半角转换"""
        normalizer = UnicodeNormalizer()
        
        text = "ＡＢＣ１２３！？"  # 全角字符
        result = normalizer.process(text)
        
        assert result == "ABC123!?"  # 应该转换为半角
    
    def test_fullwidth_space_conversion(self):
        """测试全角空格转换"""
        normalizer = UnicodeNormalizer()
        
        text = "文本　空格　测试"  # 包含全角空格
        result = normalizer.process(text)
        
        assert result == "文本 空格 测试"  # 全角空格应该转换为半角空格


class TestURLEmailCleaner:
    """URL和邮箱清理器测试"""
    
    def test_remove_urls(self):
        """测试移除URL"""
        config = PreprocessConfig(remove_urls=True)
        cleaner = URLEmailCleaner(config)
        
        text = "访问 https://example.com 或 www.test.com 获取更多信息"
        result = cleaner.process(text)
        
        assert "https://example.com" not in result
        assert "www.test.com" not in result
        assert "访问" in result
        assert "获取更多信息" in result
    
    def test_remove_emails(self):
        """测试移除邮箱"""
        config = PreprocessConfig(remove_emails=True)
        cleaner = URLEmailCleaner(config)
        
        text = "联系我们：test@example.com 或 support@company.org"
        result = cleaner.process(text)
        
        assert "test@example.com" not in result
        assert "support@company.org" not in result
        assert "联系我们" in result
    
    def test_remove_phone_numbers(self):
        """测试移除电话号码"""
        config = PreprocessConfig(remove_phone_numbers=True)
        cleaner = URLEmailCleaner(config)
        
        text = "电话：123-456-7890 或 123.456.7890 或 1234567890"
        result = cleaner.process(text)
        
        assert "123-456-7890" not in result
        assert "123.456.7890" not in result
        assert "1234567890" not in result
        assert "电话" in result
    
    def test_keep_content_when_disabled(self):
        """测试禁用时保留内容"""
        config = PreprocessConfig(
            remove_urls=False,
            remove_emails=False,
            remove_phone_numbers=False
        )
        cleaner = URLEmailCleaner(config)
        
        text = "访问 https://example.com 联系 test@example.com 电话 123-456-7890"
        result = cleaner.process(text)
        
        assert result == text  # 应该保持不变


class TestCustomPatternCleaner:
    """自定义模式清理器测试"""
    
    def test_custom_patterns(self):
        """测试自定义模式清理"""
        config = PreprocessConfig(custom_patterns=[r'\d+', r'[A-Z]+'])
        cleaner = CustomPatternCleaner(config)
        
        text = "文本123包含ABC数字和大写字母"
        result = cleaner.process(text)
        
        assert "123" not in result
        assert "ABC" not in result
        assert "文本" in result
        assert "包含" in result
        assert "数字和大写字母" in result
    
    def test_invalid_pattern(self):
        """测试无效正则表达式模式"""
        config = PreprocessConfig(custom_patterns=[r'[invalid'])  # 无效的正则表达式
        cleaner = CustomPatternCleaner(config)
        
        text = "测试文本"
        result = cleaner.process(text)
        
        # 应该忽略无效模式，返回原文本
        assert result == text
    
    def test_no_custom_patterns(self):
        """测试没有自定义模式"""
        config = PreprocessConfig(custom_patterns=None)
        cleaner = CustomPatternCleaner(config)
        
        text = "测试文本"
        result = cleaner.process(text)
        
        assert result == text


class TestStopwordRemover:
    """停用词移除器测试"""
    
    def test_remove_chinese_stopwords(self):
        """测试移除中文停用词"""
        config = PreprocessConfig(remove_stopwords=True, language="zh")
        remover = StopwordRemover(config)
        
        text = "这是一个测试文档的内容"
        result = remover.process(text)
        
        # 停用词应该被移除
        assert "这" not in result
        assert "是" not in result
        assert "一个" not in result
        assert "的" not in result
        # 实际内容应该保留
        assert "测试" in result
        assert "文档" in result
        assert "内容" in result
    
    def test_remove_english_stopwords(self):
        """测试移除英文停用词"""
        config = PreprocessConfig(remove_stopwords=True, language="en")
        remover = StopwordRemover(config)
        
        text = "This is a test document with some content"
        result = remover.process(text)
        
        # 停用词应该被移除
        assert "this" not in result.lower()
        assert "is" not in result.lower()
        assert "a" not in result.lower()
        assert "with" not in result.lower()
        # 实际内容应该保留
        assert "test" in result
        assert "document" in result
        assert "content" in result
    
    def test_disabled_stopword_removal(self):
        """测试禁用停用词移除"""
        config = PreprocessConfig(remove_stopwords=False)
        remover = StopwordRemover(config)
        
        text = "这是一个测试文档"
        result = remover.process(text)
        
        assert result == text  # 应该保持不变


class TestTextPreprocessor:
    """文本预处理器主类测试"""
    
    def test_default_preprocessing(self):
        """测试默认预处理"""
        preprocessor = TextPreprocessor()
        
        text = "  这是    一个\t\t测试\n\n\n文本。  "
        result = preprocessor.process(text)
        
        # 应该标准化空白字符
        assert "这是 一个 测试" in result
        assert "文本。" in result
        # 验证多余的空白被清理
        assert "    " not in result
        assert "\t\t" not in result
    
    def test_comprehensive_preprocessing(self):
        """测试综合预处理"""
        config = PreprocessConfig(
            remove_extra_whitespace=True,
            normalize_unicode=True,
            remove_urls=True,
            remove_emails=True,
            convert_to_lowercase=True
        )
        preprocessor = TextPreprocessor(config)
        
        text = "访问 HTTPS://EXAMPLE.COM 联系 TEST@EXAMPLE.COM 获取信息"
        result = preprocessor.process(text)
        
        # URL和邮箱应该被移除，文本应该转换为小写
        assert "https://example.com" not in result
        assert "test@example.com" not in result
        assert result.islower()
        assert "访问" in result
        assert "获取信息" in result
    
    def test_batch_processing(self):
        """测试批量处理"""
        preprocessor = TextPreprocessor()
        
        texts = [
            "第一个  文本",
            "第二个\t\t文本",
            "第三个\n\n\n文本"
        ]
        
        results = preprocessor.process_batch(texts)
        
        assert len(results) == len(texts)
        assert results[0] == "第一个 文本"
        assert results[1] == "第二个 文本"
        assert results[2] == "第三个\n\n文本"
    
    def test_processing_stats(self):
        """测试处理统计信息"""
        preprocessor = TextPreprocessor()
        
        original_text = "  这是    一个\t\t测试   文本。  "
        processed_text = preprocessor.process(original_text)
        
        stats = preprocessor.get_processing_stats(original_text, processed_text)
        
        assert "original_length" in stats
        assert "processed_length" in stats
        assert "reduction_ratio" in stats
        assert "original_word_count" in stats
        assert "processed_word_count" in stats
        assert "processors_used" in stats
        
        assert stats["original_length"] == len(original_text)
        assert stats["processed_length"] == len(processed_text)
        assert isinstance(stats["processors_used"], list)
    
    def test_empty_text_handling(self):
        """测试空文本处理"""
        preprocessor = TextPreprocessor()
        
        assert preprocessor.process("") == ""
        assert preprocessor.process("   ") == ""
        assert preprocessor.process(None) == ""
    
    def test_add_custom_processor(self):
        """测试添加自定义预处理器"""
        preprocessor = TextPreprocessor()
        
        # 创建自定义预处理器
        class CustomProcessor:
            def process(self, text):
                return text.replace("测试", "TEST")
        
        custom_processor = CustomProcessor()
        preprocessor.add_custom_processor(custom_processor)
        
        text = "这是测试文本"
        result = preprocessor.process(text)
        
        assert "TEST" in result
        assert "测试" not in result
    
    def test_processor_error_handling(self):
        """测试预处理器错误处理"""
        preprocessor = TextPreprocessor()
        
        # 添加一个会出错的预处理器
        class ErrorProcessor:
            def process(self, text):
                raise Exception("测试错误")
        
        error_processor = ErrorProcessor()
        preprocessor.add_custom_processor(error_processor)
        
        text = "测试文本"
        result = preprocessor.process(text)
        
        # 应该跳过出错的预处理器，继续处理
        assert result is not None
        assert len(result) > 0


class TestPreprocessorIntegration:
    """预处理器集成测试"""
    
    def test_full_pipeline(self):
        """测试完整预处理流水线"""
        config = PreprocessConfig(
            remove_extra_whitespace=True,
            remove_special_chars=False,
            normalize_unicode=True,
            remove_urls=True,
            remove_emails=True,
            remove_phone_numbers=True,
            convert_to_lowercase=False,
            remove_stopwords=False,
            language="zh",
            custom_patterns=[r'\d{4}-\d{2}-\d{2}']  # 移除日期格式
        )
        
        preprocessor = TextPreprocessor(config)
        
        text = """
        联系信息：
        网站：https://example.com
        邮箱：contact@example.com  
        电话：123-456-7890
        日期：2023-12-25
        
        这是    一个包含多种    格式的测试文档。
        """
        
        result = preprocessor.process(text)
        
        # 验证各种清理都生效了
        assert "https://example.com" not in result
        assert "contact@example.com" not in result
        assert "123-456-7890" not in result
        assert "2023-12-25" not in result
        
        # 验证空白字符被标准化
        assert "这是 一个包含多种 格式的测试文档" in result
        
        # 验证基本内容保留
        assert "联系信息" in result
        assert "测试文档" in result