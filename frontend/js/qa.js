/**
 * Q&A Interface Management
 * Handles question input, answer display, and source information
 */

class QAManager {
    constructor() {
        this.currentSessionId = null;
        this.isProcessing = false;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.createSession();
        this.loadSessionHistory();
    }

    setupEventListeners() {
        // Question form submission
        const qaForm = document.getElementById('qa-form');
        if (qaForm) {
            qaForm.addEventListener('submit', (e) => this.handleQuestionSubmit(e));
        }

        // Question input handling
        const questionInput = document.getElementById('question-input');
        if (questionInput) {
            questionInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.handleQuestionSubmit(e);
                }
            });
            
            questionInput.addEventListener('input', () => {
                this.adjustTextareaHeight(questionInput);
                this.updateCharCount(questionInput);
            });
        }

        // Clear conversation button
        const clearBtn = document.getElementById('clear-conversation');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearConversation());
        }

        // Export conversation button
        const exportBtn = document.getElementById('export-conversation');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => this.exportConversation());
        }
    }

    adjustTextareaHeight(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }

    updateCharCount(input) {
        const charCount = document.querySelector('.char-count');
        if (!charCount) return;

        const length = input.value.length;
        const maxLength = input.getAttribute('maxlength') || 1000;
        
        charCount.textContent = `${length}/${maxLength}`;
        
        // Update styling based on character count
        charCount.classList.remove('warning', 'error');
        if (length > maxLength * 0.9) {
            charCount.classList.add('error');
        } else if (length > maxLength * 0.8) {
            charCount.classList.add('warning');
        }
    }

    async createSession() {
        try {
            const response = await apiClient.createSession();
            this.currentSessionId = response.session_id;
            console.log('Session created:', this.currentSessionId);
        } catch (error) {
            console.error('Failed to create session:', error);
            notificationManager.show('创建会话失败', 'error');
        }
    }

    async handleQuestionSubmit(e) {
        e.preventDefault();
        
        if (this.isProcessing) return;

        const questionInput = document.getElementById('question-input');
        const question = questionInput.value.trim();
        
        if (!question) {
            notificationManager.show('请输入问题', 'warning');
            return;
        }

        this.isProcessing = true;
        this.updateSubmitButton(true);
        
        // Add user question to conversation
        this.addMessageToConversation(question, 'user');
        
        // Clear input
        questionInput.value = '';
        this.adjustTextareaHeight(questionInput);
        
        // Add loading message
        const loadingId = this.addLoadingMessage();
        
        try {
            const response = await apiClient.askQuestion(question, this.currentSessionId);
            
            // Remove loading message
            this.removeLoadingMessage(loadingId);
            
            // Add assistant response
            this.addAnswerToConversation(response);
            
        } catch (error) {
            console.error('Question failed:', error);
            this.removeLoadingMessage(loadingId);
            this.addErrorMessage('抱歉，处理您的问题时出现了错误。请稍后重试。');
            notificationManager.show('问答失败', 'error');
        } finally {
            this.isProcessing = false;
            this.updateSubmitButton(false);
        }
    }

    addMessageToConversation(message, type) {
        const conversationArea = document.getElementById('conversation-area');
        if (!conversationArea) return;

        const messageElement = document.createElement('div');
        messageElement.className = `message message-${type}`;
        messageElement.innerHTML = `
            <div class="message-content">
                <div class="message-text">${this.formatMessage(message)}</div>
                <div class="message-time">${formatTime(new Date())}</div>
            </div>
        `;

        conversationArea.appendChild(messageElement);
        this.scrollToBottom();
    }

    addAnswerToConversation(response) {
        const conversationArea = document.getElementById('conversation-area');
        if (!conversationArea) return;

        const messageElement = document.createElement('div');
        messageElement.className = 'message message-assistant';
        
        const sourcesHtml = response.sources && response.sources.length > 0 
            ? this.generateSourcesHtml(response.sources)
            : '';

        messageElement.innerHTML = `
            <div class="message-content">
                <div class="message-text">${this.formatMessage(response.answer)}</div>
                ${sourcesHtml}
                <div class="message-meta">
                    <span class="message-time">${formatTime(new Date())}</span>
                    ${response.confidence_score ? `<span class="confidence-score">置信度: ${(response.confidence_score * 100).toFixed(1)}%</span>` : ''}
                    ${response.processing_time ? `<span class="processing-time">处理时间: ${response.processing_time.toFixed(2)}s</span>` : ''}
                </div>
            </div>
        `;

        conversationArea.appendChild(messageElement);
        this.scrollToBottom();
    }

    generateSourcesHtml(sources) {
        if (!sources || sources.length === 0) return '';

        const sourcesHtml = sources.map((source, index) => `
            <div class="source-item" data-source-index="${index}">
                <div class="source-header">
                    <span class="source-icon">📄</span>
                    <span class="source-name">${escapeHtml(source.document_name)}</span>
                    <span class="source-score">${(source.similarity_score * 100).toFixed(1)}%</span>
                </div>
                <div class="source-content">
                    ${escapeHtml(source.chunk_content)}
                </div>
            </div>
        `).join('');

        return `
            <div class="message-sources">
                <div class="sources-header">
                    <span class="sources-title">参考来源</span>
                    <button class="sources-toggle" onclick="this.parentElement.parentElement.classList.toggle('expanded')">
                        <span class="toggle-icon">▼</span>
                    </button>
                </div>
                <div class="sources-content">
                    ${sourcesHtml}
                </div>
            </div>
        `;
    }

    addLoadingMessage() {
        const conversationArea = document.getElementById('conversation-area');
        if (!conversationArea) return null;

        const loadingId = 'loading-' + Date.now();
        const loadingElement = document.createElement('div');
        loadingElement.id = loadingId;
        loadingElement.className = 'message message-assistant message-loading';
        loadingElement.innerHTML = `
            <div class="message-content">
                <div class="loading-indicator">
                    <div class="loading-dots">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                    <span class="loading-text">正在思考中...</span>
                </div>
            </div>
        `;

        conversationArea.appendChild(loadingElement);
        this.scrollToBottom();
        return loadingId;
    }

    removeLoadingMessage(loadingId) {
        if (loadingId) {
            const loadingElement = document.getElementById(loadingId);
            if (loadingElement) {
                loadingElement.remove();
            }
        }
    }

    addErrorMessage(message) {
        const conversationArea = document.getElementById('conversation-area');
        if (!conversationArea) return;

        const errorElement = document.createElement('div');
        errorElement.className = 'message message-error';
        errorElement.innerHTML = `
            <div class="message-content">
                <div class="message-text">
                    <span class="error-icon">⚠️</span>
                    ${escapeHtml(message)}
                </div>
                <div class="message-time">${formatTime(new Date())}</div>
            </div>
        `;

        conversationArea.appendChild(errorElement);
        this.scrollToBottom();
    }

    updateSubmitButton(isLoading) {
        const submitBtn = document.getElementById('submit-question');
        if (!submitBtn) return;

        if (isLoading) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="loading-spinner"></span>发送中...';
        } else {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '发送';
        }
    }

    scrollToBottom() {
        const conversationArea = document.getElementById('conversation-area');
        if (conversationArea) {
            conversationArea.scrollTop = conversationArea.scrollHeight;
        }
    }

    formatMessage(text) {
        // Convert markdown-like formatting to HTML
        return escapeHtml(text)
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
    }

    async clearConversation() {
        const confirmed = await this.showConfirmDialog('确定要清空当前对话吗？');
        if (!confirmed) return;

        const conversationArea = document.getElementById('conversation-area');
        if (conversationArea) {
            conversationArea.innerHTML = '';
        }

        // Create new session
        await this.createSession();
        notificationManager.show('对话已清空', 'success');
    }

    async exportConversation() {
        const conversationArea = document.getElementById('conversation-area');
        if (!conversationArea) return;

        const messages = Array.from(conversationArea.querySelectorAll('.message:not(.message-loading)'));
        if (messages.length === 0) {
            notificationManager.show('没有对话内容可导出', 'warning');
            return;
        }

        const conversationText = messages.map(msg => {
            const isUser = msg.classList.contains('message-user');
            const text = msg.querySelector('.message-text').textContent;
            const time = msg.querySelector('.message-time').textContent;
            return `${isUser ? '用户' : '助手'} [${time}]: ${text}`;
        }).join('\n\n');

        const blob = new Blob([conversationText], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `conversation-${formatDate(new Date())}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        notificationManager.show('对话已导出', 'success');
    }

    async loadSessionHistory() {
        if (!this.currentSessionId) return;

        try {
            const history = await apiClient.getSessionHistory(this.currentSessionId);
            this.displaySessionHistory(history);
        } catch (error) {
            console.error('Failed to load session history:', error);
        }
    }

    displaySessionHistory(historyData) {
        const conversationArea = document.getElementById('conversation-area');
        if (!conversationArea) return;

        // 处理不同的数据格式
        let history = [];
        if (Array.isArray(historyData)) {
            history = historyData;
        } else if (historyData && historyData.history) {
            history = historyData.history;
        } else {
            console.warn('Invalid history data format:', historyData);
            return;
        }

        if (history.length === 0) return;

        conversationArea.innerHTML = '';

        history.forEach(qa => {
            // Add question
            this.addMessageToConversation(qa.question, 'user');
            
            // Add answer with sources
            const response = {
                answer: qa.answer,
                sources: qa.sources || [],
                confidence_score: qa.confidence_score,
                processing_time: qa.processing_time
            };
            this.addAnswerToConversation(response);
        });
    }

    showConfirmDialog(message) {
        return new Promise((resolve) => {
            const modal = document.createElement('div');
            modal.className = 'modal modal-active';
            modal.innerHTML = `
                <div class="modal-content">
                    <div class="modal-header">
                        <h3>确认操作</h3>
                    </div>
                    <div class="modal-body">
                        <p>${escapeHtml(message)}</p>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" onclick="this.closest('.modal').remove(); window.tempResolve(false)">取消</button>
                        <button class="btn btn-primary" onclick="this.closest('.modal').remove(); window.tempResolve(true)">确定</button>
                    </div>
                </div>
            `;

            window.tempResolve = resolve;
            document.body.appendChild(modal);
        });
    }
}

// Initialize Q&A manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('qa-interface')) {
        window.qaManager = new QAManager();
    }
});