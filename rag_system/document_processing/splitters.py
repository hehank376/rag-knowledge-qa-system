"""
文档文本分割器
"""
import logging
import re
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from ..models.document import TextChunk
from ..utils.exceptions import ProcessingError

logger = logging.getLogger(__name__)


@dataclass
class SplitConfig:
    """分割配置"""
    chunk_size: int = 1000
    chunk_overlap: int = 200
    min_chunk_size: int = 100
    max_chunk_size: int = 2000
    preserve_structure: bool = True
    generate_summary: bool = False
    generate_questions: bool = False
    semantic_split: bool = False


class BaseSplitter(ABC):
    """文本分割器基类"""
    
    def __init__(self, config: Optional[SplitConfig] = None):
        self.config = config or SplitConfig()
    
    @abstractmethod
    def split(self, text: str, document_id: str) -> List[TextChunk]:
        """分割文本"""
        pass
    
    def _create_chunk(self, content: str, document_id: str, chunk_index: int, 
                     metadata: Optional[Dict[str, Any]] = None) -> TextChunk:
        """创建文本块"""
        if not content.strip():
            raise ProcessingError("文本块内容不能为空")
        
        chunk_metadata = {
            "length": len(content),
            "created_at": datetime.now().isoformat(),
            "splitter_type": self.__class__.__name__
        }
        
        if metadata:
            chunk_metadata.update(metadata)
        
        return TextChunk(
            id=str(uuid.uuid4()),
            document_id=document_id,
            content=content.strip(),
            chunk_index=chunk_index,
            metadata=chunk_metadata
        )
    
    def _clean_text(self, text: str) -> str:
        """清理文本"""
        if not text:
            return ""
        
        # 先移除多余的换行符
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # 将连续的空格和制表符统一为单个空格，但保留换行符
        text = re.sub(r'[ \t]+', ' ', text)
        
        # 移除行首行尾空白，但保留换行符结构
        lines = text.split('\n')
        lines = [line.strip() for line in lines]
        text = '\n'.join(lines)
        
        return text
    
    def _generate_summary(self, content: str) -> str:
        """生成内容摘要（简单实现）"""
        if len(content) <= 100:
            return content
        
        # 简单的摘要生成：取前两句话
        sentences = re.split(r'[.!?。！？]', content)
        summary_sentences = []
        
        for sentence in sentences[:2]:
            sentence = sentence.strip()
            if sentence:
                summary_sentences.append(sentence)
        
        summary = '. '.join(summary_sentences)
        if summary and not summary.endswith(('.', '!', '?', '。', '！', '？')):
            summary += '...'
        
        return summary or content[:100] + "..."
    
    def _generate_questions(self, content: str) -> List[str]:
        """生成内置问题（简单实现）"""
        questions = []
        
        # 基于内容长度和关键词生成问题
        if "什么" in content or "什么是" in content:
            questions.append("这段内容主要讲述了什么？")
        
        if "如何" in content or "怎么" in content:
            questions.append("如何理解这段内容的要点？")
        
        if "为什么" in content or "原因" in content:
            questions.append("这段内容提到的原因是什么？")
        
        # 默认问题
        if not questions:
            questions.append("这段内容的主要信息是什么？")
        
        return questions[:3]  # 最多3个问题


class FixedSizeSplitter(BaseSplitter):
    """固定大小分割器"""
    
    def split(self, text: str, document_id: str) -> List[TextChunk]:
        """按固定大小分割文本"""
        try:
            logger.info(f"开始固定大小分割: 文档ID={document_id}, 文本长度={len(text)}")
            
            if not text or not text.strip():
                raise ProcessingError("文本内容为空")
            
            text = self._clean_text(text)
            chunks = []
            chunk_index = 0
            
            start = 0
            while start < len(text):
                # 计算当前块的结束位置
                end = start + self.config.chunk_size
                
                # 如果不是最后一块，尝试在合适的位置断开
                if end < len(text):
                    # 寻找最近的句号、换行符或空格
                    break_points = ['.', '。', '\n', ' ']
                    best_break = end
                    
                    for i in range(min(50, len(text) - end)):  # 向后查找50个字符
                        if text[end + i] in break_points:
                            best_break = end + i + 1
                            break
                    
                    end = best_break
                
                chunk_content = text[start:end]
                
                if chunk_content.strip():
                    metadata = {
                        "start_pos": start,
                        "end_pos": end,
                        "split_method": "fixed_size"
                    }
                    
                    if self.config.generate_summary:
                        metadata["summary"] = self._generate_summary(chunk_content)
                    
                    if self.config.generate_questions:
                        metadata["questions"] = self._generate_questions(chunk_content)
                    
                    chunk = self._create_chunk(chunk_content, document_id, chunk_index, metadata)
                    chunks.append(chunk)
                    chunk_index += 1
                
                # 计算下一块的开始位置（考虑重叠）
                start = max(start + 1, end - self.config.chunk_overlap)
            
            logger.info(f"固定大小分割完成: 生成块数={len(chunks)}")
            return chunks
            
        except Exception as e:
            logger.error(f"固定大小分割失败: {str(e)}")
            raise ProcessingError(f"固定大小分割失败: {str(e)}")


class StructureSplitter(BaseSplitter):
    """结构化分割器（按文档结构分割）"""
    
    def split(self, text: str, document_id: str) -> List[TextChunk]:
        """按文档结构分割文本"""
        try:
            logger.info(f"开始结构化分割: 文档ID={document_id}")
            
            if not text or not text.strip():
                raise ProcessingError("文本内容为空")
            
            text = self._clean_text(text)
            chunks = []
            chunk_index = 0
            
            # 按段落分割
            paragraphs = self._split_by_paragraphs(text)
            
            current_chunk = ""
            current_metadata = {"split_method": "structure", "paragraphs": []}
            
            for para_idx, paragraph in enumerate(paragraphs):
                # 检查是否是标题
                is_header = self._is_header(paragraph)
                
                # 如果是标题且当前块不为空，保存当前块
                if is_header and current_chunk.strip():
                    chunk = self._create_chunk_with_metadata(
                        current_chunk, document_id, chunk_index, current_metadata
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                    current_chunk = ""
                    current_metadata = {"split_method": "structure", "paragraphs": []}
                
                # 检查添加当前段落后是否超过大小限制
                if current_chunk and len(current_chunk) + len(paragraph) > self.config.chunk_size:
                    # 保存当前块
                    chunk = self._create_chunk_with_metadata(
                        current_chunk, document_id, chunk_index, current_metadata
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                    
                    # 开始新块，考虑重叠
                    if self.config.chunk_overlap > 0:
                        overlap_text = current_chunk[-self.config.chunk_overlap:]
                        current_chunk = overlap_text + "\n\n" + paragraph
                    else:
                        current_chunk = paragraph
                    
                    current_metadata = {
                        "split_method": "structure", 
                        "paragraphs": [para_idx]
                    }
                else:
                    # 添加到当前块
                    if current_chunk:
                        current_chunk += "\n\n" + paragraph
                        current_metadata["paragraphs"].append(para_idx)
                    else:
                        current_chunk = paragraph
                        current_metadata["paragraphs"] = [para_idx]
                
                # 标记标题
                if is_header:
                    current_metadata["has_header"] = True
                    current_metadata["header_level"] = self._get_header_level(paragraph)
            
            # 保存最后一个块
            if current_chunk.strip():
                chunk = self._create_chunk_with_metadata(
                    current_chunk, document_id, chunk_index, current_metadata
                )
                chunks.append(chunk)
            
            logger.info(f"结构化分割完成: 生成块数={len(chunks)}")
            return chunks
            
        except Exception as e:
            logger.error(f"结构化分割失败: {str(e)}")
            raise ProcessingError(f"结构化分割失败: {str(e)}")
    
    def _split_by_paragraphs(self, text: str) -> List[str]:
        """按段落分割"""
        # 按双换行符分割段落
        paragraphs = re.split(r'\n\s*\n', text)
        return [p.strip() for p in paragraphs if p.strip()]
    
    def _is_header(self, paragraph: str) -> bool:
        """判断是否是标题"""
        # 简单的标题检测规则
        paragraph = paragraph.strip()
        
        # Markdown标题
        if re.match(r'^#{1,6}\s+', paragraph):
            return True
        
        # 短段落且以数字或字母开头
        if len(paragraph) < 100 and re.match(r'^[0-9一二三四五六七八九十]+[.、]\s*', paragraph):
            return True
        
        # 全大写或包含"第...章"等
        if re.search(r'第[0-9一二三四五六七八九十]+[章节部分]', paragraph):
            return True
        
        return False
    
    def _get_header_level(self, paragraph: str) -> int:
        """获取标题级别"""
        # Markdown标题级别
        match = re.match(r'^(#{1,6})\s+', paragraph)
        if match:
            return len(match.group(1))
        
        # 其他标题默认为1级
        return 1
    
    def _create_chunk_with_metadata(self, content: str, document_id: str, 
                                   chunk_index: int, base_metadata: Dict[str, Any]) -> TextChunk:
        """创建带有额外元数据的文本块"""
        if self.config.generate_summary:
            base_metadata["summary"] = self._generate_summary(content)
        
        if self.config.generate_questions:
            base_metadata["questions"] = self._generate_questions(content)
        
        return self._create_chunk(content, document_id, chunk_index, base_metadata)


class HierarchicalSplitter(BaseSplitter):
    """层次化分割器（多级索引）"""
    
    def split(self, text: str, document_id: str) -> List[TextChunk]:
        """按层次结构分割文本"""
        try:
            logger.info(f"开始层次化分割: 文档ID={document_id}")
            
            if not text or not text.strip():
                raise ProcessingError("文本内容为空")
            
            text = self._clean_text(text)
            
            # 构建文档层次结构
            hierarchy = self._build_hierarchy(text)
            
            # 根据层次结构生成块
            chunks = self._generate_hierarchical_chunks(hierarchy, document_id)
            
            logger.info(f"层次化分割完成: 生成块数={len(chunks)}")
            return chunks
            
        except Exception as e:
            logger.error(f"层次化分割失败: {str(e)}")
            raise ProcessingError(f"层次化分割失败: {str(e)}")
    
    def _build_hierarchy(self, text: str) -> Dict[str, Any]:
        """构建文档层次结构"""
        print(f"DEBUG: _build_hierarchy 接收到的文本长度: {len(text)}")
        print(f"DEBUG: _build_hierarchy 文本前300字符: {repr(text[:300])}")
        paragraphs = re.split(r'\n\s*\n', text)
        print(f"DEBUG: 使用 r'\\n\\s*\\n' 分割成 {len(paragraphs)} 个段落")
        
        # 尝试不同的分割模式
        paragraphs2 = re.split(r'\n\n+', text)
        print(f"DEBUG: 使用 r'\\n\\n+' 分割成 {len(paragraphs2)} 个段落")
        
        # 使用更好的分割模式
        paragraphs = paragraphs2 if len(paragraphs2) > len(paragraphs) else paragraphs
        
        for i, para in enumerate(paragraphs[:3]):  # 只显示前3个段落
            print(f"DEBUG: 段落 {i+1}: {repr(para[:100])}")
        
        hierarchy = {
            "type": "document",
            "content": "",
            "children": [],
            "level": 0
        }
        
        current_section = hierarchy
        section_stack = [hierarchy]
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            # 检测标题级别
            header_level = self._detect_header_level(paragraph)
            
            if header_level > 0:
                # 分离标题和内容
                lines = paragraph.split('\n')
                title = lines[0].strip()
                content = '\n'.join(lines[1:]).strip() if len(lines) > 1 else ""
                
                # 创建新的章节
                section = {
                    "type": "section",
                    "title": title,
                    "content": content,
                    "children": [],
                    "level": header_level
                }
                
                # 找到合适的父级
                while len(section_stack) > 1 and section_stack[-1]["level"] >= header_level:
                    section_stack.pop()
                
                section_stack[-1]["children"].append(section)
                section_stack.append(section)
                current_section = section
            else:
                # 添加到当前章节的内容
                if current_section["content"]:
                    current_section["content"] += "\n\n" + paragraph
                else:
                    current_section["content"] = paragraph
        
        return hierarchy
    
    def _detect_header_level(self, paragraph: str) -> int:
        """检测标题级别"""
        # 只检测第一行是否为标题
        first_line = paragraph.split('\n')[0].strip()
        
        # Markdown标题
        match = re.match(r'^(#{1,6})\s+', first_line)
        if match:
            return len(match.group(1))
        
        # 数字标题（只有标题行，长度不超过100字符）
        if re.match(r'^[0-9]+\.\s+', first_line) and len(first_line) < 100:
            return 1
        
        # 中文章节标题
        if re.search(r'^第[0-9一二三四五六七八九十]+[章节]', first_line):
            return 1
        
        # 子标题
        if re.match(r'^[0-9]+\.[0-9]+\s+', first_line) and len(first_line) < 100:
            return 2
        
        return 0
    
    def _generate_hierarchical_chunks(self, hierarchy: Dict[str, Any], document_id: str) -> List[TextChunk]:
        """根据层次结构生成文本块"""
        chunks = []
        chunk_index = 0
        
        def process_node(node: Dict[str, Any], path: List[str] = None):
            nonlocal chunk_index
            
            if path is None:
                path = []
            
            # 处理当前节点的内容
            if node.get("content") and node["content"].strip():
                content = node["content"].strip()
                
                # 检查内容长度是否满足最小要求
                if len(content) >= self.config.min_chunk_size:
                    # 如果内容太长，进一步分割
                    if len(content) > self.config.chunk_size:
                        sub_chunks = self._split_long_content(content)
                        for i, sub_content in enumerate(sub_chunks):
                            if sub_content.strip() and len(sub_content.strip()) >= self.config.min_chunk_size:
                                metadata = {
                                    "split_method": "hierarchical",
                                    "hierarchy_path": path.copy(),
                                    "level": node.get("level", 0),
                                    "sub_chunk_index": i,
                                    "total_sub_chunks": len(sub_chunks)
                                }
                                
                                if node.get("title"):
                                    metadata["section_title"] = node["title"]
                                
                                if self.config.generate_summary:
                                    metadata["summary"] = self._generate_summary(sub_content)
                                
                                if self.config.generate_questions:
                                    metadata["questions"] = self._generate_questions(sub_content)
                                
                                chunk = self._create_chunk(sub_content.strip(), document_id, chunk_index, metadata)
                                chunks.append(chunk)
                                chunk_index += 1
                    else:
                        metadata = {
                            "split_method": "hierarchical",
                            "hierarchy_path": path.copy(),
                            "level": node.get("level", 0)
                        }
                        
                        if node.get("title"):
                            metadata["section_title"] = node["title"]
                        
                        if self.config.generate_summary:
                            metadata["summary"] = self._generate_summary(content)
                        
                        if self.config.generate_questions:
                            metadata["questions"] = self._generate_questions(content)
                        
                        chunk = self._create_chunk(content, document_id, chunk_index, metadata)
                        chunks.append(chunk)
                        chunk_index += 1
            
            # 递归处理子节点
            for child in node.get("children", []):
                child_path = path + [child.get("title", f"Section_{len(path)}")]
                process_node(child, child_path)
        
        process_node(hierarchy)
        return chunks
    
    def _split_long_content(self, content: str) -> List[str]:
        """分割过长的内容"""
        if len(content) <= self.config.chunk_size:
            return [content]
        
        chunks = []
        start = 0
        
        while start < len(content):
            end = start + self.config.chunk_size
            
            if end < len(content):
                # 寻找合适的断点
                for i in range(min(100, len(content) - end)):
                    if content[end + i] in '.。\n':
                        end = end + i + 1
                        break
            
            chunk_content = content[start:end].strip()
            if chunk_content:
                chunks.append(chunk_content)
            
            start = max(start + 1, end - self.config.chunk_overlap)
        
        return chunks


class SemanticSplitter(BaseSplitter):
    """语义分割器（基于语义相似性）"""
    
    def split(self, text: str, document_id: str) -> List[TextChunk]:
        """按语义相似性分割文本"""
        try:
            logger.info(f"开始语义分割: 文档ID={document_id}")
            
            if not text or not text.strip():
                raise ProcessingError("文本内容为空")
            
            text = self._clean_text(text)
            
            # 先按句子分割
            sentences = self._split_sentences(text)
            
            if len(sentences) <= 1:
                # 如果只有一个句子，直接返回
                metadata = {
                    "split_method": "semantic",
                    "sentence_count": len(sentences)
                }
                chunk = self._create_chunk(text, document_id, 0, metadata)
                return [chunk]
            
            # 基于简单规则进行语义分组
            chunks = self._group_sentences_semantically(sentences, document_id)
            
            logger.info(f"语义分割完成: 生成块数={len(chunks)}")
            return chunks
            
        except Exception as e:
            logger.error(f"语义分割失败: {str(e)}")
            raise ProcessingError(f"语义分割失败: {str(e)}")
    
    def _split_sentences(self, text: str) -> List[str]:
        """分割句子"""
        # 使用正则表达式分割句子
        sentence_endings = r'[.!?。！？]+'
        sentences = re.split(sentence_endings, text)
        
        # 清理和过滤空句子
        cleaned_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(sentence) > 10:  # 过滤太短的句子
                cleaned_sentences.append(sentence)
        
        return cleaned_sentences
    
    def _group_sentences_semantically(self, sentences: List[str], document_id: str) -> List[TextChunk]:
        """基于语义相似性分组句子"""
        chunks = []
        chunk_index = 0
        
        current_group = []
        current_length = 0
        
        for sentence in sentences:
            # 简单的语义分组规则
            should_start_new_group = (
                current_length + len(sentence) > self.config.chunk_size or
                self._should_break_semantic_group(current_group, sentence)
            )
            
            if should_start_new_group and current_group:
                # 创建当前组的块
                chunk_content = '. '.join(current_group) + '.'
                metadata = {
                    "split_method": "semantic",
                    "sentence_count": len(current_group),
                    "semantic_group": chunk_index
                }
                
                if self.config.generate_summary:
                    metadata["summary"] = self._generate_summary(chunk_content)
                
                if self.config.generate_questions:
                    metadata["questions"] = self._generate_questions(chunk_content)
                
                chunk = self._create_chunk(chunk_content, document_id, chunk_index, metadata)
                chunks.append(chunk)
                chunk_index += 1
                
                # 开始新组，考虑重叠
                if self.config.chunk_overlap > 0 and current_group:
                    overlap_sentences = current_group[-1:]  # 保留最后一句作为重叠
                    current_group = overlap_sentences + [sentence]
                    current_length = sum(len(s) for s in current_group)
                else:
                    current_group = [sentence]
                    current_length = len(sentence)
            else:
                current_group.append(sentence)
                current_length += len(sentence)
        
        # 处理最后一组
        if current_group:
            chunk_content = '. '.join(current_group) + '.'
            metadata = {
                "split_method": "semantic",
                "sentence_count": len(current_group),
                "semantic_group": chunk_index
            }
            
            if self.config.generate_summary:
                metadata["summary"] = self._generate_summary(chunk_content)
            
            if self.config.generate_questions:
                metadata["questions"] = self._generate_questions(chunk_content)
            
            chunk = self._create_chunk(chunk_content, document_id, chunk_index, metadata)
            chunks.append(chunk)
        
        return chunks
    
    def _should_break_semantic_group(self, current_group: List[str], new_sentence: str) -> bool:
        """判断是否应该开始新的语义组"""
        if not current_group:
            return False
        
        # 简单的语义断点检测规则
        last_sentence = current_group[-1].lower()
        new_sentence_lower = new_sentence.lower()
        
        # 话题转换指示词
        topic_change_indicators = [
            '然而', '但是', '不过', '另外', '此外', '另一方面', 
            '相反', '与此同时', '接下来', '首先', '其次', '最后',
            'however', 'but', 'on the other hand', 'meanwhile', 'next'
        ]
        
        for indicator in topic_change_indicators:
            if new_sentence_lower.startswith(indicator):
                return True
        
        # 时间转换
        time_indicators = ['后来', '然后', '接着', '随后', 'later', 'then', 'afterwards']
        for indicator in time_indicators:
            if indicator in new_sentence_lower:
                return True
        
        return False


class RecursiveTextSplitter(BaseSplitter):
    """递归文本分割器（综合多种分割策略）"""
    
    def __init__(self, config: Optional[SplitConfig] = None):
        super().__init__(config)
        self.splitters = {
            "structure": StructureSplitter(config),
            "hierarchical": HierarchicalSplitter(config),
            "semantic": SemanticSplitter(config),
            "fixed": FixedSizeSplitter(config)
        }
    
    def split(self, text: str, document_id: str) -> List[TextChunk]:
        """递归分割文本，自动选择最佳策略"""
        try:
            logger.info(f"开始递归分割: 文档ID={document_id}, 文本长度={len(text)}")
            
            if not text or not text.strip():
                raise ProcessingError("文本内容为空")
            
            # 选择最佳分割策略
            strategy = self._select_best_strategy(text)
            logger.info(f"选择分割策略: {strategy}")
            
            # 执行分割
            chunks = self.splitters[strategy].split(text, document_id)
            
            # 后处理：检查块大小并进一步分割过大的块
            final_chunks = self._post_process_chunks(chunks, document_id)
            
            logger.info(f"递归分割完成: 生成块数={len(final_chunks)}")
            return final_chunks
            
        except Exception as e:
            logger.error(f"递归分割失败: {str(e)}")
            raise ProcessingError(f"递归分割失败: {str(e)}")
    
    def _select_best_strategy(self, text: str) -> str:
        """选择最佳分割策略"""
        text_length = len(text)
        
        # 检测文档结构特征
        has_headers = bool(re.search(r'^#{1,6}\s+|^[0-9]+\.\s+', text, re.MULTILINE))
        has_hierarchy = bool(re.search(r'第[0-9一二三四五六七八九十]+[章节]', text))
        paragraph_count = len(re.split(r'\n\s*\n', text))
        
        # 策略选择逻辑
        if has_hierarchy and text_length > 2000:
            return "hierarchical"
        elif has_headers and paragraph_count > 5:
            return "structure"
        elif self.config.semantic_split and text_length > 1000:
            return "semantic"
        else:
            return "fixed"
    
    def _post_process_chunks(self, chunks: List[TextChunk], document_id: str) -> List[TextChunk]:
        """后处理文本块"""
        final_chunks = []
        chunk_index = 0
        
        for chunk in chunks:
            if len(chunk.content) > self.config.max_chunk_size:
                # 进一步分割过大的块
                sub_chunks = self._split_large_chunk(chunk, document_id, chunk_index)
                final_chunks.extend(sub_chunks)
                chunk_index += len(sub_chunks)
            elif len(chunk.content) >= self.config.min_chunk_size:
                # 重新编号
                chunk.chunk_index = chunk_index
                final_chunks.append(chunk)
                chunk_index += 1
            # 过小的块被丢弃或合并到前一个块
            elif final_chunks and len(final_chunks[-1].content) + len(chunk.content) <= self.config.max_chunk_size:
                # 合并到前一个块
                final_chunks[-1].content += "\n\n" + chunk.content
                final_chunks[-1].metadata["merged_chunks"] = final_chunks[-1].metadata.get("merged_chunks", 0) + 1
        
        return final_chunks
    
    def _split_large_chunk(self, chunk: TextChunk, document_id: str, start_index: int) -> List[TextChunk]:
        """分割过大的文本块"""
        # 使用固定大小分割器处理过大的块
        fixed_splitter = FixedSizeSplitter(self.config)
        sub_chunks = fixed_splitter.split(chunk.content, document_id)
        
        # 更新元数据和索引
        for i, sub_chunk in enumerate(sub_chunks):
            sub_chunk.chunk_index = start_index + i
            sub_chunk.metadata.update({
                "parent_chunk_id": chunk.id,
                "is_sub_chunk": True,
                "original_split_method": chunk.metadata.get("split_method", "unknown")
            })
        
        return sub_chunks


# 主要的文本分割器类（向后兼容）
class TextSplitter(RecursiveTextSplitter):
    """文本分割器（主要接口）"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200, **kwargs):
        config = SplitConfig(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            **kwargs
        )
        super().__init__(config)