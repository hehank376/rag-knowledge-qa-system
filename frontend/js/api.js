// API接口管理
// Version: 2025-08-04-18:15 (修复getDocumentStats绑定)

class APIClient {
    constructor(baseURL = 'http://localhost:8000') {
        this.baseURL = baseURL;
        this.defaultHeaders = {
            'Content-Type': 'application/json',
        };
    }

    /**
     * 发送HTTP请求
     * @param {string} url - 请求URL
     * @param {Object} options - 请求选项
     * @returns {Promise} 响应Promise
     */
    async request(url, options = {}) {
        const config = {
            headers: { ...this.defaultHeaders, ...options.headers },
            ...options
        };

        try {
            const response = await fetch(`${this.baseURL}${url}`, config);

            // 检查响应状态
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
            }

            // 尝试解析JSON响应
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            }

            return await response.text();
        } catch (error) {
            console.error('API请求失败:', error);
            // 确保错误消息是字符串格式
            const errorMessage = error.message || error.toString() || '未知错误';
            throw new Error(errorMessage);
        }
    }

    /**
     * GET请求
     * @param {string} url - 请求URL
     * @param {Object} params - 查询参数
     * @returns {Promise} 响应Promise
     */
    async get(url, params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const fullUrl = queryString ? `${url}?${queryString}` : url;

        return this.request(fullUrl, {
            method: 'GET'
        });
    }

    /**
     * POST请求
     * @param {string} url - 请求URL
     * @param {Object} data - 请求数据
     * @returns {Promise} 响应Promise
     */
    async post(url, data = {}) {
        return this.request(url, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    /**
     * PUT请求
     * @param {string} url - 请求URL
     * @param {Object} data - 请求数据
     * @returns {Promise} 响应Promise
     */
    async put(url, data = {}) {
        return this.request(url, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    /**
     * DELETE请求
     * @param {string} url - 请求URL
     * @returns {Promise} 响应Promise
     */
    async delete(url) {
        return this.request(url, {
            method: 'DELETE'
        });
    }

    /**
     * 上传文件
     * @param {string} url - 上传URL
     * @param {FormData} formData - 表单数据
     * @param {Function} onProgress - 进度回调
     * @returns {Promise} 响应Promise
     */
    async upload(url, formData, onProgress = null) {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();

            // 设置进度监听
            if (onProgress) {
                xhr.upload.addEventListener('progress', (event) => {
                    if (event.lengthComputable) {
                        const percentComplete = (event.loaded / event.total) * 100;
                        onProgress(percentComplete);
                    }
                });
            }

            // 设置完成监听
            xhr.addEventListener('load', () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        resolve(response);
                    } catch (error) {
                        resolve(xhr.responseText);
                    }
                } else {
                    try {
                        const errorData = JSON.parse(xhr.responseText);
                        reject(new Error(errorData.detail || `HTTP ${xhr.status}: ${xhr.statusText}`));
                    } catch (error) {
                        reject(new Error(`HTTP ${xhr.status}: ${xhr.statusText}`));
                    }
                }
            });

            // 设置错误监听
            xhr.addEventListener('error', () => {
                reject(new Error('网络错误'));
            });

            // 发送请求
            xhr.open('POST', `${this.baseURL}${url}`);
            xhr.send(formData);
        });
    }
}

// 创建API客户端实例
const api = new APIClient();

// 文档管理API
const documentAPI = {
    /**
     * 获取文档列表
     * @param {string} statusFilter - 状态筛选
     * @returns {Promise} 文档列表
     */
    async getDocuments(statusFilter = null) {
        const params = statusFilter ? { status_filter: statusFilter } : {};
        return api.get('/documents/', params);
    },

    /**
     * 获取单个文档信息
     * @param {string} documentId - 文档ID
     * @returns {Promise} 文档信息
     */
    async getDocument(documentId) {
        return api.get(`/documents/${documentId}`);
    },

    /**
     * 上传文档
     * @param {File} file - 文件对象
     * @param {Function} onProgress - 进度回调
     * @returns {Promise} 上传结果
     */
    async uploadDocument(file, onProgress = null) {
        const formData = new FormData();
        formData.append('file', file);

        return api.upload('/documents/upload', formData, onProgress);
    },

    /**
     * 批量上传文档
     * @param {FileList} files - 文件列表
     * @param {Function} onProgress - 进度回调
     * @returns {Promise} 上传结果
     */
    async batchUploadDocuments(files, onProgress = null) {
        const formData = new FormData();
        Array.from(files).forEach(file => {
            formData.append('files', file);
        });

        return api.upload('/documents/batch-upload', formData, onProgress);
    },

    /**
     * 删除文档
     * @param {string} documentId - 文档ID
     * @returns {Promise} 删除结果
     */
    async deleteDocument(documentId) {
        return api.delete(`/documents/${documentId}`);
    },

    /**
     * 重新处理文档
     * @param {string} documentId - 文档ID
     * @returns {Promise} 处理结果
     */
    async reprocessDocument(documentId) {
        return api.post(`/documents/${documentId}/reprocess`);
    },

    /**
     * 获取文档统计信息
     * @returns {Promise} 统计信息
     */
    async getDocumentStats() {
        return api.get('/documents/stats/summary');
    },

    /**
     * 获取支持的文件格式
     * @returns {Promise} 支持的格式
     */
    async getSupportedFormats() {
        return api.get('/documents/supported-formats');
    }
};

// 问答API
const qaAPI = {
    /**
     * 发送问答请求
     * @param {string} question - 问题
     * @param {string} sessionId - 会话ID
     * @returns {Promise} 问答结果
     */
    async askQuestion(question, sessionId = null) {
        const data = { question };
        if (sessionId) {
            data.session_id = sessionId;
        }
        return api.post('/qa/ask', data);
    },

    /**
     * 获取问答历史
     * @param {string} sessionId - 会话ID
     * @returns {Promise} 历史记录
     */
    async getQAHistory(sessionId) {
        return api.get(`/qa/session/${sessionId}/history`);
    }
};

// 会话管理API
const sessionAPI = {
    /**
     * 创建新会话
     * @param {string} title - 会话标题
     * @returns {Promise} 会话信息
     */
    async createSession(title = null) {
        try {
            const data = title ? { title } : {};
            return api.post('/sessions/', data);
        } catch (error) {
            console.warn('Session API not available, using temporary session:', error);
            // 如果会话API不可用，返回一个临时会话ID
            return {
                session_id: 'temp_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9),
                title: title
            };
        }
    },

    /**
     * 获取会话列表
     * @returns {Promise} 会话列表
     */
    async getSessions() {
        try {
            return api.get('/sessions/recent');
        } catch (error) {
            console.warn('Session API not available:', error);
            return { sessions: [] };
        }
    },

    /**
     * 获取单个会话
     * @param {string} sessionId - 会话ID
     * @returns {Promise} 会话信息
     */
    async getSession(sessionId) {
        return api.get(`/sessions/${sessionId}`);
    },

    /**
     * 删除会话
     * @param {string} sessionId - 会话ID
     * @returns {Promise} 删除结果
     */
    async deleteSession(sessionId) {
        return api.delete(`/sessions/${sessionId}`);
    },

    /**
     * 获取会话历史记录
     * @param {string} sessionId - 会话ID
     * @returns {Promise} 会话历史记录
     */
    async getSessionHistory(sessionId) {
        try {
            return api.get(`/sessions/${sessionId}/history`);
        } catch (error) {
            console.warn('Session history API not available:', error);
            return [];
        }
    },

    /**
     * 获取分页会话列表
     * @param {string} params - 查询参数
     * @returns {Promise} 分页会话列表
     */
    async getSessionsWithPagination(params = '') {
        try {
            const url = params ? `/sessions/recent?${params}` : '/sessions/recent';
            return api.get(url);
        } catch (error) {
            console.warn('Session pagination API not available:', error);
            return { sessions: [], total_pages: 1 };
        }
    },

    /**
     * 获取所有会话（用于导出）
     * @returns {Promise} 所有会话
     */
    async getAllSessions() {
        return api.get('/sessions/');
    },

    /**
     * 清空所有会话
     * @returns {Promise} 清空结果
     */
    async clearAllSessions() {
        return api.delete('/sessions/?confirm=true');
    },

    /**
     * 获取会话统计信息
     * @returns {Promise} 统计信息
     */
    async getSessionStats() {
        return api.get('/sessions/stats/summary');
    }
};

// 配置管理API
const configAPI = {
    /**
     * 获取系统配置
     * @returns {Promise} 系统配置
     */
    async getConfig() {
        try {
            return api.get('/config/');
        } catch (error) {
            console.warn('Config API not available, using default settings:', error);
            // 返回默认设置
            return {
                llm_provider: 'mock',
                llm_model: 'test-model',
                embedding_provider: 'mock',
                embedding_model: 'test-embedding',
                max_tokens: 1000,
                temperature: 0.7
            };
        }
    },

    /**
     * 获取配置节
     * @param {string} section - 配置节名称
     * @returns {Promise} 配置节信息
     */
    async getConfigSection(section) {
        return api.get(`/config/${section}`);
    },

    /**
     * 更新配置节
     * @param {string} section - 配置节名称
     * @param {Object} config - 配置数据
     * @returns {Promise} 更新结果
     */
    async updateConfigSection(section, config) {
        try {
            return api.put(`/config/${section}`, config);
        } catch (error) {
            console.warn('Config update API not available:', error);
            // 模拟成功响应
            return { message: '设置已保存（模拟）' };
        }
    },

    /**
     * 验证配置
     * @param {string} section - 配置节名称
     * @param {Object} config - 配置数据
     * @returns {Promise} 验证结果
     */
    async validateConfig(section, config) {
        return api.post('/config/validate', { section, config });
    },

    /**
     * 重新加载配置
     * @returns {Promise} 重新加载结果
     */
    async reloadConfig() {
        return api.post('/config/reload');
    },

    /**
     * 获取模型状态
     * @returns {Promise} 模型状态信息
     */
    async getModelStatus() {
        return api.get('/config/models/status');
    },

    /**
     * 获取模型性能指标
     * @returns {Promise} 模型性能指标
     */
    async getModelMetrics() {
        return api.get('/config/models/metrics');
    },

    /**
     * 切换活跃模型
     * @param {string} modelType - 模型类型 (embedding/reranking)
     * @param {string} modelName - 模型名称
     * @returns {Promise} 切换结果
     */
    async switchActiveModel(switchData) {
        return api.post('/models/switch', switchData);
    },

    /**
     * 添加新模型
     * @param {string} modelType - 模型类型
     * @param {Object} config - 模型配置
     * @returns {Promise} 添加结果
     */
    async addModel(modelData) {
        return api.post('/models/add', modelData);
    },

    /**
     * 测试模型
     * @param {string} modelType - 模型类型
     * @param {string} modelName - 模型名称
     * @returns {Promise} 测试结果
     */
    async testModel(testData) {
        return api.post('/models/test', testData);
    },

    /**
     * 获取模型配置列表
     * @returns {Promise} 模型配置列表
     */
    async getModelConfigs() {
        return api.get('/models/configs');
    },

    /**
     * 更新模型配置
     * @param {Object} configData - 配置数据
     * @returns {Promise} 更新结果
     */
    async updateModelConfig(configData) {
        return api.post('/config/models/update-config', configData);
    },

    /**
     * 执行模型健康检查
     * @returns {Promise} 健康检查结果
     */
    async performModelHealthCheck() {
        return api.post('/config/models/health-check');
    },

    /**
     * 测试连接
     * @param {string} type - 连接类型 (llm/embedding/storage/all)
     * @param {Object} config - 配置数据
     * @returns {Promise} 测试结果
     */
    async testConnection(type, config) {
        return api.post(`/config/test/${type}`, config);
    },

    // 数据库相关API
    /**
     * 获取数据库信息
     * @returns {Promise} 数据库信息
     */
    async getDatabaseInfo() {
        return api.get('/config/database/info');
    },

    /**
     * 测试数据库连接
     * @param {Object} config - 数据库配置
     * @returns {Promise} 测试结果
     */
    async testDatabaseConnection(config) {
        return api.post('/config/database/test', config);
    },

    /**
     * 重新加载数据库配置
     * @returns {Promise} 重新加载结果
     */
    async reloadDatabaseConfig() {
        return api.post('/config/database/reload');
    },

    /**
     * 检查数据库健康状态
     * @returns {Promise} 健康检查结果
     */
    async checkDatabaseHealth() {
        return api.get('/config/database/health');
    }
};

// 监控API
const monitoringAPI = {
    /**
     * 获取系统健康状态
     * @returns {Promise} 健康状态
     */
    async getHealth() {
        try {
            // 尝试多个可能的健康检查端点
            const endpoints = ['/monitoring/health', '/config/health', '/health'];
            for (const endpoint of endpoints) {
                try {
                    return await api.get(endpoint);
                } catch (error) {
                    console.warn(`Health check endpoint ${endpoint} failed:`, error);
                    continue;
                }
            }
            throw new Error('All health check endpoints failed');
        } catch (error) {
            console.warn('Health check not available:', error);
            return { status: 'unknown', message: 'Health check not available' };
        }
    },

    /**
     * 获取系统指标
     * @returns {Promise} 系统指标
     */
    async getMetrics() {
        try {
            return await api.get('/monitoring/metrics');
        } catch (error) {
            console.warn('Metrics API not available:', error);
            return { metrics: [], message: 'Metrics not available' };
        }
    },

    /**
     * 获取系统状态概览
     * @returns {Promise} 状态概览
     */
    async getSystemStatus() {
        try {
            return await api.get('/monitoring/status');
        } catch (error) {
            console.warn('System status API not available:', error);
            return { status: 'unknown', message: 'System status not available' };
        }
    },

    /**
     * 获取告警信息
     * @param {number} minutes - 时间范围（分钟）
     * @returns {Promise} 告警信息
     */
    async getAlerts(minutes = 60) {
        return api.get('/api/monitoring/alerts', { minutes });
    }
};

// 错误处理辅助函数
function handleAPIError(error, defaultMessage = '操作失败') {
    console.error('API错误:', error);

    if (error.message) {
        return error.message;
    }

    return defaultMessage;
}

// 统一的API客户端
const apiClient = {
    // 文档管理
    uploadDocument: documentAPI.uploadDocument.bind(documentAPI),
    getDocuments: documentAPI.getDocuments.bind(documentAPI),
    getDocument: documentAPI.getDocument.bind(documentAPI),
    deleteDocument: documentAPI.deleteDocument.bind(documentAPI),
    getDocumentStats: documentAPI.getDocumentStats.bind(documentAPI),

    // 问答
    askQuestion: qaAPI.askQuestion.bind(qaAPI),

    // 会话管理
    createSession: sessionAPI.createSession.bind(sessionAPI),
    getSessions: sessionAPI.getSessionsWithPagination.bind(sessionAPI),
    getSession: sessionAPI.getSession.bind(sessionAPI),
    getSessionHistory: sessionAPI.getSessionHistory.bind(sessionAPI),
    getAllSessions: sessionAPI.getAllSessions.bind(sessionAPI),
    deleteSession: sessionAPI.deleteSession.bind(sessionAPI),
    clearAllSessions: sessionAPI.clearAllSessions.bind(sessionAPI),
    getSessionStats: sessionAPI.getSessionStats.bind(sessionAPI),

    // 配置管理
    getConfig: configAPI.getConfig.bind(configAPI),
    getConfigSection: configAPI.getConfigSection.bind(configAPI),
    updateConfigSection: configAPI.updateConfigSection.bind(configAPI),
    validateConfig: configAPI.validateConfig.bind(configAPI),
    reloadConfig: configAPI.reloadConfig.bind(configAPI),

    // 模型管理
    getModelStatus: configAPI.getModelStatus.bind(configAPI),
    getModelMetrics: configAPI.getModelMetrics.bind(configAPI),
    switchActiveModel: configAPI.switchActiveModel.bind(configAPI),
    addModel: configAPI.addModel.bind(configAPI),
    testModel: configAPI.testModel.bind(configAPI),
    updateModelConfig: configAPI.updateModelConfig.bind(configAPI),
    performModelHealthCheck: configAPI.performModelHealthCheck.bind(configAPI),
    testConnection: configAPI.testConnection.bind(configAPI),

    // 监控
    getHealth: monitoringAPI.getHealth.bind(monitoringAPI),
    getMetrics: monitoringAPI.getMetrics.bind(monitoringAPI),
    getSystemStatus: monitoringAPI.getSystemStatus.bind(monitoringAPI),
    getAlerts: monitoringAPI.getAlerts.bind(monitoringAPI)
};

// 导出API对象
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        api,
        documentAPI,
        qaAPI,
        sessionAPI,
        configAPI,
        monitoringAPI,
        apiClient,
        handleAPIError
    };
}