/**
 * Document Manager
 * Handles document upload, listing, and management functionality
 * Version: 2025-08-04-17:58 (统计功能修复版本)
 */

class DocumentManager {
    constructor() {
        this.documents = [];
        this.currentPage = 1;
        this.pageSize = 10;
        this.totalPages = 1;
        this.currentFilter = 'all';
        this.searchQuery = '';
        this.init();
    }

    // 本地统计API调用方法，作为备用方案
    async getDocumentStatsLocal() {
        try {
            const response = await fetch('http://localhost:8000/documents/stats/summary');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error('本地统计API调用失败:', error);
            throw error;
        }
    }

    init() {
        this.setupEventListeners();
        this.loadDocuments();
    }

    setupEventListeners() {
        // File input and upload
        const fileInput = document.getElementById('fileInput');
        const uploadBtn = document.getElementById('uploadBtn');
        const uploadArea = document.getElementById('uploadArea');

        if (fileInput && uploadBtn) {
            uploadBtn.addEventListener('click', () => fileInput.click());
            fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        }

        if (uploadArea) {
            // Drag and drop functionality
            uploadArea.addEventListener('dragover', (e) => this.handleDragOver(e));
            uploadArea.addEventListener('dragleave', (e) => this.handleDragLeave(e));
            uploadArea.addEventListener('drop', (e) => this.handleDrop(e));
        }

        // Search and filter
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('input', debounce(() => {
                this.searchQuery = searchInput.value.trim();
                this.currentPage = 1;
                this.loadDocuments();
            }, 300));
        }

        // Filter dropdown
        const filterBtn = document.getElementById('filterBtn');
        const filterMenu = document.getElementById('filterMenu');
        if (filterBtn && filterMenu) {
            filterBtn.addEventListener('click', () => {
                filterMenu.classList.toggle('active');
            });

            filterMenu.addEventListener('change', (e) => {
                if (e.target.name === 'status') {
                    this.currentFilter = e.target.value;
                    this.currentPage = 1;
                    this.loadDocuments();
                    filterMenu.classList.remove('active');
                }
            });
        }

        // Refresh button
        const refreshBtn = document.getElementById('refreshBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadDocuments());
        }

        // Pagination
        const prevPage = document.getElementById('prevPage');
        const nextPage = document.getElementById('nextPage');
        if (prevPage) {
            prevPage.addEventListener('click', () => this.goToPage(this.currentPage - 1));
        }
        if (nextPage) {
            nextPage.addEventListener('click', () => this.goToPage(this.currentPage + 1));
        }

        // Close modal
        const modalClose = document.getElementById('modalClose');
        if (modalClose) {
            modalClose.addEventListener('click', () => this.closeModal());
        }

        // Click outside modal to close
        const modal = document.getElementById('documentModal');
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeModal();
                }
            });
        }
    }

    handleDragOver(e) {
        e.preventDefault();
        e.currentTarget.classList.add('drag-over');
    }

    handleDragLeave(e) {
        e.preventDefault();
        e.currentTarget.classList.remove('drag-over');
    }

    handleDrop(e) {
        e.preventDefault();
        e.currentTarget.classList.remove('drag-over');

        const files = Array.from(e.dataTransfer.files);
        this.uploadFiles(files);
    }

    handleFileSelect(e) {
        const files = Array.from(e.target.files);
        this.uploadFiles(files);
        e.target.value = ''; // Reset file input
    }

    async uploadFiles(files) {
        if (!files || files.length === 0) return;

        // Validate files
        const validFiles = files.filter(file => this.validateFile(file));
        if (validFiles.length === 0) {
            notificationManager.show('没有有效的文件可上传', 'warning');
            return;
        }

        // Show upload progress
        this.showUploadProgress();

        for (let i = 0; i < validFiles.length; i++) {
            const file = validFiles[i];
            try {
                await this.uploadSingleFile(file, i + 1, validFiles.length);
            } catch (error) {
                console.error('Upload failed:', error);
                notificationManager.show(`文件 ${file.name} 上传失败`, 'error');
            }
        }

        this.hideUploadProgress();
        this.loadDocuments();
    }

    validateFile(file) {
        const allowedTypes = ['.pdf', '.docx', '.txt', '.md'];
        const maxSize = 50 * 1024 * 1024; // 50MB

        const extension = '.' + file.name.split('.').pop().toLowerCase();

        if (!allowedTypes.includes(extension)) {
            notificationManager.show(`不支持的文件格式: ${file.name}`, 'error');
            return false;
        }

        if (file.size > maxSize) {
            notificationManager.show(`文件过大: ${file.name} (最大50MB)`, 'error');
            return false;
        }

        return true;
    }

    async uploadSingleFile(file, current, total) {
        const progressText = document.getElementById('progressText');
        const progressPercent = document.getElementById('progressPercent');
        const progressFill = document.getElementById('progressFill');

        if (progressText) {
            progressText.textContent = `上传中 (${current}/${total}): ${file.name}`;
        }

        try {
            // 使用apiClient的uploadDocument方法，并传入进度回调
            const result = await apiClient.uploadDocument(file, (percent) => {
                if (progressPercent && progressFill) {
                    const roundedPercent = Math.round((current - 1 + percent / 100) / total * 100);
                    progressPercent.textContent = `${roundedPercent}%`;
                    progressFill.style.width = `${roundedPercent}%`;
                }
            });

            // 最终进度更新
            if (progressPercent && progressFill) {
                const finalPercent = Math.round((current / total) * 100);
                progressPercent.textContent = `${finalPercent}%`;
                progressFill.style.width = `${finalPercent}%`;
            }

            notificationManager.show(`文件 ${file.name} 上传成功`, 'success');
            return result;

        } catch (error) {
            throw error;
        }
    }

    showUploadProgress() {
        const uploadProgress = document.getElementById('uploadProgress');
        if (uploadProgress) {
            uploadProgress.style.display = 'block';
        }
    }

    hideUploadProgress() {
        const uploadProgress = document.getElementById('uploadProgress');
        if (uploadProgress) {
            uploadProgress.style.display = 'none';
        }

        // Reset progress
        const progressFill = document.getElementById('progressFill');
        const progressPercent = document.getElementById('progressPercent');
        const progressText = document.getElementById('progressText');

        if (progressFill) progressFill.style.width = '0%';
        if (progressPercent) progressPercent.textContent = '0%';
        if (progressText) progressText.textContent = '上传中...';
    }

    async loadDocuments() {
        const loadingState = document.getElementById('loadingState');
        const documentsList = document.getElementById('documentsList');

        if (loadingState) loadingState.style.display = 'block';
        if (documentsList) documentsList.innerHTML = '';

        try {
            console.log('🔄 开始加载文档和统计信息...');
            console.log('apiClient类型:', typeof apiClient);
            console.log('apiClient.getDocumentStats存在:', !!apiClient.getDocumentStats);
            console.log('documentAPI.getDocumentStats存在:', !!documentAPI.getDocumentStats);

            // 并行加载文档列表和统计信息
            const statusFilter = this.currentFilter !== 'all' ? this.currentFilter : null;
            console.log('状态过滤器:', statusFilter);

            const [documentsResponse, statsResponse] = await Promise.all([
                apiClient.getDocuments(statusFilter),
                apiClient.getDocumentStats()
                // 使用本地方法作为可靠的备用方案
                //this.getDocumentStatsLocal()
            ]);

            console.log('文档列表响应:', documentsResponse);
            console.log('统计信息响应:', statsResponse);

            this.documents = documentsResponse.documents || [];
            this.totalPages = documentsResponse.total_pages || 1;

            this.renderDocuments();
            this.updateStats(statsResponse);
            this.updatePagination();

        } catch (error) {
            console.error('Failed to load documents:', error);
            notificationManager.show('加载文档列表失败', 'error');
        } finally {
            if (loadingState) loadingState.style.display = 'none';
        }
    }

    renderDocuments() {
        const documentsList = document.getElementById('documentsList');
        if (!documentsList) return;

        if (this.documents.length === 0) {
            documentsList.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-folder-open"></i>
                    <h3>暂无文档</h3>
                    <p>请上传文档开始构建您的知识库</p>
                </div>
            `;
            return;
        }

        const documentsHtml = this.documents.map(doc => this.renderDocumentItem(doc)).join('');
        documentsList.innerHTML = documentsHtml;

        // Add event listeners for document actions
        this.attachDocumentEventListeners();
    }

    renderDocumentItem(doc) {
        const statusClass = this.getStatusClass(doc.status);
        const statusIcon = this.getStatusIcon(doc.status);
        const statusText = this.getStatusText(doc.status);

        return `
            <div class="document-item" data-doc-id="${doc.id}">
                <div class="document-icon">
                    <i class="fas ${this.getFileIcon(doc.file_type)}"></i>
                </div>
                <div class="document-info">
                    <div class="document-name" title="${escapeHtml(doc.filename)}">
                        ${escapeHtml(doc.filename)}
                    </div>
                    <div class="document-meta">
                        <span class="file-size">${formatFileSize(doc.file_size)}</span>
                        <span class="upload-time">${formatDate(new Date(doc.upload_time))}</span>
                        ${doc.chunk_count ? `<span class="chunk-count">${doc.chunk_count} 块</span>` : ''}
                    </div>
                </div>
                <div class="document-status">
                    <span class="status-badge ${statusClass}">
                        <i class="fas ${statusIcon}"></i>
                        ${statusText}
                    </span>
                </div>
                <div class="document-actions">
                    <button class="action-btn view-btn" onclick="documentManager.viewDocument('${doc.id}')" title="查看详情">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="action-btn delete-btn" onclick="documentManager.deleteDocument('${doc.id}')" title="删除文档">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `;
    }

    getFileIcon(fileType) {
        const icons = {
            'pdf': 'fa-file-pdf',
            'docx': 'fa-file-word',
            'txt': 'fa-file-alt',
            'md': 'fa-file-code'
        };
        return icons[fileType] || 'fa-file';
    }

    getStatusClass(status) {
        const classes = {
            'ready': 'status-ready',
            'processing': 'status-processing',
            'error': 'status-error'
        };
        return classes[status] || 'status-unknown';
    }

    getStatusIcon(status) {
        const icons = {
            'ready': 'fa-check-circle',
            'processing': 'fa-spinner fa-spin',
            'error': 'fa-exclamation-triangle'
        };
        return icons[status] || 'fa-question-circle';
    }

    getStatusText(status) {
        const texts = {
            'ready': '已就绪',
            'processing': '处理中',
            'error': '处理失败'
        };
        return texts[status] || '未知状态';
    }

    attachDocumentEventListeners() {
        // Event delegation is handled by onclick attributes in the HTML
        // This method can be used for additional event listeners if needed
    }

    async viewDocument(docId) {
        try {
            const doc = await apiClient.getDocument(docId);
            this.showDocumentModal(doc);
        } catch (error) {
            console.error('Failed to load document details:', error);
            notificationManager.show('加载文档详情失败', 'error');
        }
    }

    showDocumentModal(doc) {
        const modal = document.getElementById('documentModal');
        const modalTitle = document.getElementById('modalTitle');
        const modalBody = document.getElementById('modalBody');
        console.log('显示文档模态框:', doc);
        console.log('模态框元素:', { modal: !!modal, modalTitle: !!modalTitle, modalBody: !!modalBody });

        if (!modal || !modalTitle || !modalBody) {
            console.error('模态框元素未找到');
            return;
        }

        modalTitle.textContent = doc.filename || '未知文档';
        console.log('设置标题:', doc.filename);
        modalBody.innerHTML = `
            <div class="document-details">
                <div class="detail-row">
                    <label>文件名:</label>
                    <span>${escapeHtml(doc.filename)}</span>
                </div>
                <div class="detail-row">
                    <label>文件类型:</label>
                    <span>${doc.file_type.toUpperCase()}</span>
                </div>
                <div class="detail-row">
                    <label>文件大小:</label>
                    <span>${formatFileSize(doc.file_size)}</span>
                </div>
                <div class="detail-row">
                    <label>上传时间:</label>
                    <span>${formatDateTime(new Date(doc.upload_time))}</span>
                </div>
                <div class="detail-row">
                    <label>处理状态:</label>
                    <span class="status-badge ${this.getStatusClass(doc.status)}">
                        <i class="fas ${this.getStatusIcon(doc.status)}"></i>
                        ${this.getStatusText(doc.status)}
                    </span>
                </div>
                ${doc.chunk_count ? `
                <div class="detail-row">
                    <label>文本块数:</label>
                    <span>${doc.chunk_count}</span>
                </div>
                ` : ''}
                ${doc.error_message ? `
                <div class="detail-row">
                    <label>错误信息:</label>
                    <span class="error-message">${escapeHtml(doc.error_message)}</span>
                </div>
                ` : ''}
            </div>
        `;

        modal.classList.add('active');
    }

    closeModal() {
        const modal = document.getElementById('documentModal');
        if (modal) {
            modal.classList.remove('active');
        }
    }

    async deleteDocument(docId) {
        const confirmed = confirm('确定要删除这个文档吗？此操作不可撤销。');
        if (!confirmed) return;

        try {
            await apiClient.deleteDocument(docId);
            notificationManager.show('文档删除成功', 'success');
            this.loadDocuments();
        } catch (error) {
            console.error('Failed to delete document:', error);
            notificationManager.show('删除文档失败', 'error');
        }
    }

    updateStats(stats) {
        console.log('updateStats 被调用，参数:', stats);

        if (!stats) {
            console.warn('统计数据为空，跳过更新');
            return;
        }

        const totalDocs = document.getElementById('totalDocs');
        const readyDocs = document.getElementById('readyDocs');
        const processingDocs = document.getElementById('processingDocs');
        const errorDocs = document.getElementById('errorDocs');

        console.log('找到的DOM元素:', {
            totalDocs: !!totalDocs,
            readyDocs: !!readyDocs,
            processingDocs: !!processingDocs,
            errorDocs: !!errorDocs
        });

        // 使用API返回的正确字段名
        if (totalDocs) {
            totalDocs.textContent = stats.total_documents || 0;
            console.log('更新总文档数:', stats.total_documents);
        }
        if (readyDocs) {
            readyDocs.textContent = stats.ready_documents || 0;
            console.log('更新已就绪:', stats.ready_documents);
        }
        if (processingDocs) {
            processingDocs.textContent = stats.processing_documents || 0;
            console.log('更新处理中:', stats.processing_documents);
        }
        if (errorDocs) {
            errorDocs.textContent = stats.error_documents || 0;
            console.log('更新处理失败:', stats.error_documents);
        }

        console.log('✅ 统计信息更新完成');
    }

    updatePagination() {
        const pagination = document.getElementById('pagination');
        const prevPage = document.getElementById('prevPage');
        const nextPage = document.getElementById('nextPage');
        const pageInfo = document.getElementById('pageInfo');

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
        this.loadDocuments();
    }
}

// Initialize document manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('documents')) {
        window.documentManager = new DocumentManager();
    }
});