/**
 * History Manager
 * Handles session history viewing, searching, and management
 */

class HistoryManager {
    constructor() {
        this.sessions = [];
        this.currentPage = 1;
        this.pageSize = 10;
        this.totalPages = 1;
        this.currentSort = 'newest';
        this.searchQuery = '';
        this.startDate = '';
        this.endDate = '';
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadSessions();
    }

    setupEventListeners() {
        // Search input
        const searchInput = document.getElementById('historySearchInput');
        if (searchInput) {
            searchInput.addEventListener('input', debounce(() => {
                this.searchQuery = searchInput.value.trim();
                this.currentPage = 1;
                this.loadSessions();
            }, 300));
        }

        // Date filters
        const startDate = document.getElementById('startDate');
        const endDate = document.getElementById('endDate');
        if (startDate) {
            startDate.addEventListener('change', () => {
                this.startDate = startDate.value;
                this.currentPage = 1;
                this.loadSessions();
            });
        }
        if (endDate) {
            endDate.addEventListener('change', () => {
                this.endDate = endDate.value;
                this.currentPage = 1;
                this.loadSessions();
            });
        }

        // Sort dropdown
        const sortBtn = document.getElementById('sortBtn');
        const sortMenu = document.getElementById('sortMenu');
        if (sortBtn && sortMenu) {
            sortBtn.addEventListener('click', () => {
                sortMenu.classList.toggle('active');
            });

            sortMenu.addEventListener('change', (e) => {
                if (e.target.name === 'sort') {
                    this.currentSort = e.target.value;
                    this.currentPage = 1;
                    this.loadSessions();
                    sortMenu.classList.remove('active');
                }
            });
        }

        // Control buttons
        const clearHistoryBtn = document.getElementById('clearHistoryBtn');
        const exportHistoryBtn = document.getElementById('exportHistoryBtn');
        const refreshHistoryBtn = document.getElementById('refreshHistoryBtn');

        if (clearHistoryBtn) {
            clearHistoryBtn.addEventListener('click', () => this.clearAllHistory());
        }
        if (exportHistoryBtn) {
            exportHistoryBtn.addEventListener('click', () => this.exportHistory());
        }
        if (refreshHistoryBtn) {
            refreshHistoryBtn.addEventListener('click', () => this.loadSessions());
        }

        // Pagination
        const prevPage = document.getElementById('historyPrevPage');
        const nextPage = document.getElementById('historyNextPage');
        if (prevPage) {
            prevPage.addEventListener('click', () => this.goToPage(this.currentPage - 1));
        }
        if (nextPage) {
            nextPage.addEventListener('click', () => this.goToPage(this.currentPage + 1));
        }
    }

    async loadSessions() {
        const loadingState = document.getElementById('historyLoadingState');
        const sessionsList = document.getElementById('sessionsList');
        
        if (loadingState) loadingState.style.display = 'block';
        if (sessionsList) sessionsList.innerHTML = '';

        try {
            const params = new URLSearchParams({
                page: this.currentPage,
                size: this.pageSize,
                sort: this.currentSort,
                search: this.searchQuery,
                start_date: this.startDate,
                end_date: this.endDate
            });

            const response = await apiClient.getSessions(params.toString());
            console.log('Sessions API response:', response);
            this.sessions = response.sessions || [];
            // 处理不同的分页字段名：后端返回 total_count，前端期望 total_pages
            this.totalPages = response.total_pages || Math.ceil((response.total_count || 0) / this.pageSize) || 1;

            this.renderSessions();
            this.updateStats(response.stats); // 如果API返回了stats就使用，否则会自动加载
            this.updatePagination();

        } catch (error) {
            console.error('Failed to load sessions:', error);
            if (window.notificationManager) {
                notificationManager.show('加载历史记录失败', 'error');
            }
        } finally {
            if (loadingState) loadingState.style.display = 'none';
        }
    }

    renderSessions() {
        const sessionsList = document.getElementById('sessionsList');
        if (!sessionsList) return;

        if (this.sessions.length === 0) {
            sessionsList.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-history"></i>
                    <h3>暂无历史记录</h3>
                    <p>开始与AI对话，您的历史记录将显示在这里</p>
                </div>
            `;
            return;
        }

        const sessionsHtml = this.sessions.map(session => this.renderSessionItem(session)).join('');
        sessionsList.innerHTML = sessionsHtml;
    }

    renderSessionItem(session) {
        const duration = this.calculateDuration(session.created_at, session.updated_at || session.last_activity);
        // 后端返回的是 qa_count，不是 qa_pairs，所以需要处理
        const firstQuestion = session.title || (session.qa_count > 0 ? '会话记录' : '无问题记录');

        return `
            <div class="session-item" data-session-id="${session.session_id}">
                <div class="session-header">
                    <div class="session-info">
                        <div class="session-title">
                            <i class="fas fa-comments"></i>
                            <span class="session-preview">${firstQuestion.substring(0, 50)}${firstQuestion.length > 50 ? '...' : ''}</span>
                        </div>
                        <div class="session-meta">
                            <span class="session-time">
                                <i class="fas fa-clock"></i>
                                ${formatDate(session.created_at)}
                            </span>
                            <span class="session-duration">
                                <i class="fas fa-hourglass-half"></i>
                                ${duration}
                            </span>
                            <span class="session-count">
                                <i class="fas fa-question-circle"></i>
                                ${session.qa_count || 0} 个问题
                            </span>
                        </div>
                    </div>
                    <div class="session-actions">
                        <button class="action-btn view-btn" onclick="historyManager.viewSession('${session.session_id}')" title="查看详情">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="action-btn continue-btn" onclick="historyManager.continueSession('${session.session_id}')" title="继续对话">
                            <i class="fas fa-play"></i>
                        </button>
                        <button class="action-btn export-btn" onclick="historyManager.exportSession('${session.session_id}')" title="导出会话">
                            <i class="fas fa-download"></i>
                        </button>
                        <button class="action-btn delete-btn" onclick="historyManager.deleteSession('${session.session_id}')" title="删除会话">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
                <div class="session-content" id="session-content-${session.session_id}" style="display: none;">
                </div>
            </div>
        `;
    }

    calculateDuration(startTime, endTime) {
        const start = new Date(startTime);
        const end = new Date(endTime);
        const diffMs = end - start;
        const diffMins = Math.floor(diffMs / 60000);
        
        if (diffMins < 1) return '< 1分钟';
        if (diffMins < 60) return `${diffMins}分钟`;
        
        const diffHours = Math.floor(diffMins / 60);
        const remainingMins = diffMins % 60;
        
        if (diffHours < 24) {
            return remainingMins > 0 ? `${diffHours}小时${remainingMins}分钟` : `${diffHours}小时`;
        }
        
        const diffDays = Math.floor(diffHours / 24);
        return `${diffDays}天`;
    }

    async viewSession(sessionId) {
        //alert('seesionID = '+sessionId)
        const sessionItem = document.querySelector(`[data-session-id="${sessionId}"]`);
        const contentDiv = document.getElementById(`session-content-${sessionId}`);
        
        //console.log('seesionID = '+sessionId)
        if (!sessionItem || !contentDiv) return;

        //console.log('sessionItem = '+sessionItem)
        //console.log('contentDiv = '+contentDiv)
        // Toggle visibility
        const isVisible = contentDiv.style.display !== 'none';
        
        if (isVisible) {
            contentDiv.style.display = 'none';
            return;
        }

        // Load session details if not already loaded
        if (contentDiv.innerHTML.trim() === '') {
            try {
                //alert(' 获取历史回话详情 '+sessionId)

                const session = await apiClient.getSessionHistory(sessionId);
                
                this.renderSessionDetails(contentDiv, session);
            } catch (error) {
                console.error('Failed to load session details:', error);
                contentDiv.innerHTML = `
                    <div class="error-state">
                        <i class="fas fa-exclamation-triangle"></i>
                        <p>加载会话详情失败</p>
                    </div>
                `;
            }
        }

        contentDiv.style.display = 'block';
    }

    renderSessionDetails(container, historyData) {
        // 处理不同的数据格式
        let qaPairs = [];
        if (Array.isArray(historyData)) {
            qaPairs = historyData;
        } else if (historyData && historyData.history) {
            qaPairs = historyData.history;
        } else {
            console.warn('Invalid history data format:', historyData);
        }

        if (!qaPairs || qaPairs.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-comment-slash"></i>
                    <p>此会话暂无对话记录</p>
                </div>
            `;
            return;
        }

        const qaHtml = qaPairs.map((qa, index) => `
            <div class="qa-pair">
                <div class="qa-question">
                    <div class="qa-header">
                        <i class="fas fa-user"></i>
                        <span class="qa-label">问题 ${index + 1}</span>
                        <span class="qa-time">${formatDate(qa.timestamp)}</span>
                    </div>
                    <div class="qa-content">${qa.question}</div>
                </div>
                <div class="qa-answer">
                    <div class="qa-header">
                        <i class="fas fa-robot"></i>
                        <span class="qa-label">回答</span>
                    </div>
                    <div class="qa-content">${this.formatAnswer(qa.answer)}</div>
                    ${qa.sources && qa.sources.length > 0 ? this.renderSources(qa.sources) : ''}
                </div>
            </div>
        `).join('');

        container.innerHTML = `
            <div class="session-details">
                ${qaHtml}
            </div>
        `;
    }

    formatAnswer(text) {
        return this.escapeHtml(text)
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    renderSources(sources) {
        const sourcesHtml = sources.map(source => `
            <div class="source-item">
                <div class="source-header">
                    <i class="fas fa-file"></i>
                    <span class="source-name">${source.document_name}</span>
                    <span class="source-score">${Math.round(source.score * 100)}%</span>
                </div>
                <div class="source-content">${source.content}</div>
            </div>
        `).join('');

        return `
            <div class="qa-sources">
                <div class="sources-header">
                    <i class="fas fa-book"></i>
                    <span>参考来源</span>
                </div>
                <div class="sources-list">
                    ${sourcesHtml}
                </div>
            </div>
        `;
    }

    async continueSession(sessionId) {
        try {
            // Switch to QA tab and set the session
            if (window.app) {
                window.app.switchTab('qa');
            }
            
            // Set the current session in QA manager
            if (window.qaManager) {
                window.qaManager.currentSessionId = sessionId;
                await window.qaManager.loadSessionHistory();
            }
            
            if (window.notificationManager) {
                notificationManager.show('已切换到该会话', 'success');
            }
        } catch (error) {
            console.error('Failed to continue session:', error);
            if (window.notificationManager) {
                notificationManager.show('切换会话失败', 'error');
            }
        }
    }

    async exportSession(sessionId) {
        try {
            const historyData = await apiClient.getSessionHistory(sessionId);
            
            // 处理不同的数据格式
            let session = [];
            if (Array.isArray(historyData)) {
                session = historyData;
            } else if (historyData && historyData.history) {
                session = historyData.history;
            }
            
            if (!session || session.length === 0) {
                if (window.notificationManager) {
                    notificationManager.show('该会话无内容可导出', 'warning');
                }
                return;
            }

            const sessionText = session.map((qa, index) => {
                let text = `问题 ${index + 1}: ${qa.question}\n`;
                text += `回答: ${qa.answer}\n`;
                if (qa.sources && qa.sources.length > 0) {
                    text += `来源: ${qa.sources.map(s => s.document_name).join(', ')}\n`;
                }
                text += `时间: ${formatDate(qa.timestamp)}\n`;
                return text;
            }).join('\n---\n\n');

            const blob = new Blob([sessionText], { type: 'text/plain;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `session-${sessionId}.txt`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            if (window.notificationManager) {
                notificationManager.show('会话已导出', 'success');
            }
        } catch (error) {
            console.error('Failed to export session:', error);
            if (window.notificationManager) {
                notificationManager.show('导出会话失败', 'error');
            }
        }
    }

    async deleteSession(sessionId) {
        const confirmed = confirm('确定要删除这个会话吗？此操作不可撤销。');
        if (!confirmed) return;

        try {
            await apiClient.deleteSession(sessionId);
            if (window.notificationManager) {
                notificationManager.show('会话删除成功', 'success');
            }
            this.loadSessions();
        } catch (error) {
            console.error('Failed to delete session:', error);
            if (window.notificationManager) {
                notificationManager.show('删除会话失败', 'error');
            }
        }
    }

    async clearAllHistory() {
        const confirmed = confirm('确定要清空所有历史记录吗？此操作不可撤销。');
        if (!confirmed) return;

        try {
            await apiClient.clearAllSessions();
            if (window.notificationManager) {
                notificationManager.show('历史记录已清空', 'success');
            }
            this.loadSessions();
        } catch (error) {
            console.error('Failed to clear history:', error);
            if (window.notificationManager) {
                notificationManager.show('清空历史记录失败', 'error');
            }
        }
    }

    async exportHistory() {
        try {
            const allSessions = await apiClient.getAllSessions();
            if (!allSessions || allSessions.length === 0) {
                if (window.notificationManager) {
                    notificationManager.show('暂无历史记录可导出', 'warning');
                }
                return;
            }

            const historyText = allSessions.map(session => {
                let text = `会话ID: ${session.session_id}\n`;
                text += `创建时间: ${formatDate(session.created_at)}\n`;
                text += `问题数量: ${session.qa_pairs ? session.qa_pairs.length : 0}\n\n`;
                
                if (session.qa_pairs) {
                    session.qa_pairs.forEach((qa, index) => {
                        text += `问题 ${index + 1}: ${qa.question}\n`;
                        text += `回答: ${qa.answer}\n`;
                        if (qa.sources && qa.sources.length > 0) {
                            text += `来源: ${qa.sources.map(s => s.document_name).join(', ')}\n`;
                        }
                        text += `时间: ${formatDate(qa.timestamp)}\n\n`;
                    });
                }
                
                return text;
            }).join('\n===================\n\n');

            const blob = new Blob([historyText], { type: 'text/plain;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `history-export-${new Date().toISOString().split('T')[0]}.txt`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            if (window.notificationManager) {
                notificationManager.show('历史记录已导出', 'success');
            }
        } catch (error) {
            console.error('Failed to export history:', error);
            if (window.notificationManager) {
                notificationManager.show('导出历史记录失败', 'error');
            }
        }
    }

    updateStats(stats) {
        if (!stats) {
            // 如果没有传入stats，尝试从API获取
            this.loadStats();
            return;
        }

        const totalSessions = document.getElementById('totalSessions');
        const totalQuestions = document.getElementById('totalQuestions');
        const todaySessions = document.getElementById('todaySessions');
        const avgResponseTime = document.getElementById('avgResponseTime');

        if (totalSessions) totalSessions.textContent = stats.total_sessions || 0;
        if (totalQuestions) totalQuestions.textContent = stats.total_qa_pairs || stats.total_questions || 0;
        if (todaySessions) todaySessions.textContent = stats.today_sessions || stats.active_sessions || 0;
        if (avgResponseTime) {
            const avgTime = stats.avg_response_time || 0;
            avgResponseTime.textContent = avgTime > 0 ? `${avgTime.toFixed(1)}s` : '0s';
        }
    }

    async loadStats() {
        try {
            const stats = await apiClient.getSessionStats();
            this.updateStats(stats);
        } catch (error) {
            console.error('Failed to load stats:', error);
        }
    }

    updatePagination() {
        const pagination = document.getElementById('historyPagination');
        const prevPage = document.getElementById('historyPrevPage');
        const nextPage = document.getElementById('historyNextPage');
        const pageInfo = document.getElementById('historyPageInfo');

        if (!pagination) return;

        if (this.totalPages <= 1) {
            pagination.style.display = 'none';
            return;
        }

        pagination.style.display = 'flex';

        if (prevPage) {
            prevPage.disabled = this.currentPage <= 1;
        }

        if (nextPage) {
            nextPage.disabled = this.currentPage >= this.totalPages;
        }

        if (pageInfo) {
            pageInfo.textContent = `第 ${this.currentPage} 页，共 ${this.totalPages} 页`;
        }
    }

    goToPage(page) {
        if (page < 1 || page > this.totalPages) return;
        this.currentPage = page;
        this.loadSessions();
    }
}

// Initialize history manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('history')) {
        window.historyManager = new HistoryManager();
    }
});