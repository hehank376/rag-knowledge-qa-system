/**
 * 数据库配置管理器
 * 与现有设置系统集成的数据库配置管理
 */

class DatabaseConfigManager {
    constructor() {
        this.supportedDatabases = {
            'sqlite': {
                name: 'SQLite',
                urlTemplate: 'sqlite:///./database/{dbname}.db',
                description: '轻量级文件数据库，适合开发和小型应用',
                configFields: ['timeout', 'echo'],
                defaultConfig: {
                    timeout: 30.0,
                    echo: false
                }
            },
            'postgresql': {
                name: 'PostgreSQL',
                urlTemplate: 'postgresql://{user}:{password}@{host}:{port}/{database}',
                description: '企业级关系数据库，适合生产环境',
                configFields: ['pool_size', 'max_overflow', 'pool_timeout', 'echo'],
                defaultConfig: {
                    pool_size: 5,
                    max_overflow: 10,
                    pool_timeout: 30,
                    echo: false
                }
            },
            'mysql': {
                name: 'MySQL',
                urlTemplate: 'mysql://{user}:{password}@{host}:{port}/{database}',
                description: '流行的关系数据库，适合Web应用',
                configFields: ['pool_size', 'max_overflow', 'pool_timeout', 'charset', 'echo'],
                defaultConfig: {
                    pool_size: 5,
                    max_overflow: 10,
                    pool_timeout: 30,
                    charset: 'utf8mb4',
                    echo: false
                }
            }
        };
        
        this.currentDatabaseType = 'sqlite';
        this.connectionTestResult = null;
    }

    /**
     * 初始化数据库配置管理器
     */
    init() {
        this.setupEventListeners();
        this.loadDatabaseInfo();
    }

    /**
     * 设置事件监听器
     */
    setupEventListeners() {
        // 数据库类型选择变化
        const databaseTypeSelect = document.getElementById('databaseType');
        if (databaseTypeSelect) {
            databaseTypeSelect.addEventListener('change', (e) => {
                this.onDatabaseTypeChange(e.target.value);
            });
        }

        // 数据库连接测试按钮
        const testDatabaseBtn = document.getElementById('testDatabaseConnection');
        if (testDatabaseBtn) {
            testDatabaseBtn.addEventListener('click', () => {
                this.testDatabaseConnection();
            });
        }

        // 数据库配置重新加载按钮
        const reloadDatabaseBtn = document.getElementById('reloadDatabaseConfig');
        if (reloadDatabaseBtn) {
            reloadDatabaseBtn.addEventListener('click', () => {
                this.reloadDatabaseConfig();
            });
        }

        // 数据库URL输入框变化
        const databaseUrlInput = document.getElementById('databaseUrl');
        if (databaseUrlInput) {
            databaseUrlInput.addEventListener('input', () => {
                this.onDatabaseUrlChange();
            });
        }
    }

    /**
     * 加载数据库信息
     */
    async loadDatabaseInfo() {
        try {
            const response = await apiClient.getDatabaseInfo();
            
            if (response.success) {
                this.updateDatabaseInfo(response.data);
            } else {
                console.error('加载数据库信息失败:', response.error);
            }
        } catch (error) {
            console.error('加载数据库信息异常:', error);
        }
    }

    /**
     * 更新数据库信息显示
     */
    updateDatabaseInfo(data) {
        // 更新当前数据库类型
        if (data.current_config && data.current_config.type) {
            this.currentDatabaseType = data.current_config.type;
            this.updateDatabaseTypeSelect(this.currentDatabaseType);
        }

        // 更新连接状态显示
        this.updateConnectionStatus(data.connection_info);

        // 更新支持的数据库类型选项
        this.updateSupportedDatabasesUI(data.supported_databases);
    }

    /**
     * 数据库类型变化处理
     */
    onDatabaseTypeChange(selectedType) {
        this.currentDatabaseType = selectedType;
        
        // 更新URL模板提示
        this.updateUrlTemplate(selectedType);
        
        // 更新配置字段显示
        this.updateConfigFields(selectedType);
        
        // 更新描述信息
        this.updateDescription(selectedType);
        
        // 清除之前的测试结果
        this.clearTestResult();
    }

    /**
     * 更新URL模板提示
     */
    updateUrlTemplate(dbType) {
        const urlInput = document.getElementById('databaseUrl');
        const urlHint = document.getElementById('databaseUrlHint');
        
        if (urlInput && this.supportedDatabases[dbType]) {
            const template = this.supportedDatabases[dbType].urlTemplate;
            urlInput.placeholder = template;
            
            if (urlHint) {
                urlHint.textContent = `格式: ${template}`;
            }
        }
    }

    /**
     * 更新配置字段显示
     */
    updateConfigFields(dbType) {
        const allFields = ['timeout', 'echo', 'pool_size', 'max_overflow', 'pool_timeout', 'charset'];
        const relevantFields = this.supportedDatabases[dbType]?.configFields || [];
        
        allFields.forEach(field => {
            const fieldElement = document.getElementById(`db_${field}`);
            if (fieldElement) {
                const container = fieldElement.closest('.form-group');
                if (container) {
                    container.style.display = relevantFields.includes(field) ? 'block' : 'none';
                }
            }
        });
    }

    /**
     * 更新描述信息
     */
    updateDescription(dbType) {
        const descriptionElement = document.getElementById('databaseDescription');
        if (descriptionElement && this.supportedDatabases[dbType]) {
            descriptionElement.textContent = this.supportedDatabases[dbType].description;
        }
    }

    /**
     * 数据库URL变化处理
     */
    onDatabaseUrlChange() {
        const urlInput = document.getElementById('databaseUrl');
        if (urlInput && urlInput.value) {
            // 从URL自动检测数据库类型
            const detectedType = this.detectDatabaseType(urlInput.value);
            if (detectedType && detectedType !== this.currentDatabaseType) {
                this.updateDatabaseTypeSelect(detectedType);
                this.onDatabaseTypeChange(detectedType);
            }
        }
        
        // 清除之前的测试结果
        this.clearTestResult();
    }

    /**
     * 从URL检测数据库类型
     */
    detectDatabaseType(url) {
        if (url.startsWith('sqlite:')) {
            return 'sqlite';
        } else if (url.startsWith('postgresql:') || url.startsWith('postgres:')) {
            return 'postgresql';
        } else if (url.startsWith('mysql:')) {
            return 'mysql';
        }
        return null;
    }

    /**
     * 更新数据库类型选择器
     */
    updateDatabaseTypeSelect(dbType) {
        const select = document.getElementById('databaseType');
        if (select) {
            select.value = dbType;
        }
    }

    /**
     * 测试数据库连接
     */
    async testDatabaseConnection() {
        const testBtn = document.getElementById('testDatabaseConnection');
        
        // 更新按钮状态
        if (testBtn) {
            testBtn.disabled = true;
            testBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 测试中...';
        }

        try {
            // 收集数据库配置
            const config = this.collectDatabaseConfig();
            
            // 执行连接测试
            const response = await apiClient.testDatabaseConnection(config);
            
            // 显示测试结果
            this.showTestResult(response);
            
        } catch (error) {
            console.error('数据库连接测试失败:', error);
            this.showTestResult({
                success: false,
                message: `连接测试失败: ${error.message}`
            });
        } finally {
            // 恢复按钮状态
            if (testBtn) {
                testBtn.disabled = false;
                testBtn.innerHTML = '<i class="fas fa-plug"></i> 测试连接';
            }
        }
    }

    /**
     * 收集数据库配置
     */
    collectDatabaseConfig() {
        const url = document.getElementById('databaseUrl')?.value || '';
        
        const config = {
            url: url,
            config: {}
        };

        // 收集相关配置字段
        const relevantFields = this.supportedDatabases[this.currentDatabaseType]?.configFields || [];
        
        relevantFields.forEach(field => {
            const element = document.getElementById(`db_${field}`);
            if (element) {
                if (element.type === 'checkbox') {
                    config.config[field] = element.checked;
                } else if (element.type === 'number' || element.type === 'range') {
                    config.config[field] = parseFloat(element.value) || 0;
                } else {
                    config.config[field] = element.value;
                }
            }
        });

        return config;
    }

    /**
     * 显示测试结果
     */
    showTestResult(result) {
        this.connectionTestResult = result;
        
        const resultContainer = document.getElementById('databaseTestResult');
        if (resultContainer) {
            const isSuccess = result.success;
            const message = result.message || (isSuccess ? '连接测试成功' : '连接测试失败');
            
            resultContainer.className = `test-result ${isSuccess ? 'success' : 'error'}`;
            resultContainer.innerHTML = `
                <div class="result-header">
                    <i class="fas ${isSuccess ? 'fa-check-circle' : 'fa-times-circle'}"></i>
                    <span class="result-title">${isSuccess ? '连接成功' : '连接失败'}</span>
                </div>
                <div class="result-message">${message}</div>
                ${result.data && result.data.database_type ? 
                    `<div class="result-details">数据库类型: ${result.data.database_type}</div>` : 
                    ''
                }
            `;
            resultContainer.style.display = 'block';
        }

        // 显示通知
        if (window.notificationManager) {
            window.notificationManager.show(
                result.message || (result.success ? '数据库连接测试成功' : '数据库连接测试失败'),
                result.success ? 'success' : 'error'
            );
        }
    }

    /**
     * 清除测试结果
     */
    clearTestResult() {
        const resultContainer = document.getElementById('databaseTestResult');
        if (resultContainer) {
            resultContainer.style.display = 'none';
        }
        this.connectionTestResult = null;
    }

    /**
     * 重新加载数据库配置
     */
    async reloadDatabaseConfig() {
        const reloadBtn = document.getElementById('reloadDatabaseConfig');
        
        // 更新按钮状态
        if (reloadBtn) {
            reloadBtn.disabled = true;
            reloadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 重新加载中...';
        }

        try {
            const response = await apiClient.reloadDatabaseConfig();
            
            if (response.success) {
                // 重新加载数据库信息
                await this.loadDatabaseInfo();
                
                if (window.notificationManager) {
                    window.notificationManager.show('数据库配置重新加载成功', 'success');
                }
            } else {
                throw new Error(response.message || '重新加载失败');
            }
            
        } catch (error) {
            console.error('重新加载数据库配置失败:', error);
            if (window.notificationManager) {
                window.notificationManager.show(`重新加载失败: ${error.message}`, 'error');
            }
        } finally {
            // 恢复按钮状态
            if (reloadBtn) {
                reloadBtn.disabled = false;
                reloadBtn.innerHTML = '<i class="fas fa-sync-alt"></i> 重新加载配置';
            }
        }
    }

    /**
     * 更新连接状态显示
     */
    updateConnectionStatus(connectionInfo) {
        const statusElement = document.getElementById('databaseConnectionStatus');
        if (statusElement && connectionInfo) {
            const isConnected = connectionInfo.service_initialized;
            const dbType = connectionInfo.database_type || 'unknown';
            
            statusElement.className = `connection-status ${isConnected ? 'connected' : 'disconnected'}`;
            statusElement.innerHTML = `
                <i class="fas ${isConnected ? 'fa-check-circle' : 'fa-times-circle'}"></i>
                <span>${isConnected ? '已连接' : '未连接'} (${dbType})</span>
            `;
        }
    }

    /**
     * 更新支持的数据库类型UI
     */
    updateSupportedDatabasesUI(supportedDatabases) {
        if (supportedDatabases) {
            // 更新本地支持的数据库信息
            Object.assign(this.supportedDatabases, supportedDatabases);
        }
    }

    /**
     * 获取当前数据库配置
     */
    getCurrentConfig() {
        return this.collectDatabaseConfig();
    }

    /**
     * 获取测试结果
     */
    getTestResult() {
        return this.connectionTestResult;
    }

    /**
     * 检查配置是否有效
     */
    validateConfig() {
        const config = this.collectDatabaseConfig();
        
        if (!config.url || !config.url.trim()) {
            return {
                valid: false,
                error: '数据库连接URL不能为空'
            };
        }

        const dbType = this.detectDatabaseType(config.url);
        if (!dbType || !this.supportedDatabases[dbType]) {
            return {
                valid: false,
                error: '不支持的数据库类型'
            };
        }

        return {
            valid: true,
            type: dbType
        };
    }
}

// 导出数据库配置管理器
window.DatabaseConfigManager = DatabaseConfigManager;