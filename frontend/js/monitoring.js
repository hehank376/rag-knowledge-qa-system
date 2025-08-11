/**
 * Monitoring Manager
 * 处理系统监控数据的展示和管理
 */

class MonitoringManager {
    constructor() {
        this.updateInterval = null;
        this.refreshRate = 30000; // 30秒更新一次
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.startAutoUpdate();
    }

    setupEventListeners() {
        // 监听页面可见性变化
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.stopAutoUpdate();
            } else {
                this.startAutoUpdate();
            }
        });
    }

    startAutoUpdate() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        
        // 立即更新一次
        this.updateSystemStatus();
        
        // 设置定时更新
        this.updateInterval = setInterval(() => {
            this.updateSystemStatus();
        }, this.refreshRate);
    }

    stopAutoUpdate() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }

    async updateSystemStatus() {
        try {
            // 更新导航栏的系统状态指示器
            await this.updateNavbarStatus();
            
            // 如果在监控页面，更新详细信息
            if (this.isOnMonitoringPage()) {
                await this.updateMonitoringDashboard();
            }
        } catch (error) {
            console.warn('Failed to update system status:', error);
        }
    }

    async updateNavbarStatus() {
        const statusIndicator = document.getElementById('systemStatus');
        if (!statusIndicator) return;

        const statusIcon = statusIndicator.querySelector('.status-indicator');
        const statusText = statusIndicator.querySelector('.status-text');

        try {
            const health = await apiClient.getHealth();
            
            if (health && health.status === 'healthy') {
                statusIcon.className = 'fas fa-circle status-indicator status-online';
                statusText.textContent = '系统正常';
            } else {
                statusIcon.className = 'fas fa-circle status-indicator status-warning';
                statusText.textContent = '系统异常';
            }
        } catch (error) {
            statusIcon.className = 'fas fa-circle status-indicator status-offline';
            statusText.textContent = '连接失败';
        }
    }

    isOnMonitoringPage() {
        // 检查是否在监控相关页面
        const activeTab = document.querySelector('.nav-link.active');
        return activeTab && activeTab.getAttribute('data-tab') === 'monitoring';
    }

    async updateMonitoringDashboard() {
        try {
            const [health, metrics, status] = await Promise.all([
                apiClient.getHealth(),
                apiClient.getMetrics(),
                apiClient.getSystemStatus()
            ]);

            this.renderHealthStatus(health);
            this.renderMetrics(metrics);
            this.renderSystemStatus(status);
        } catch (error) {
            console.error('Failed to update monitoring dashboard:', error);
        }
    }

    renderHealthStatus(health) {
        const healthContainer = document.getElementById('healthStatus');
        if (!healthContainer) return;

        const status = health?.status || 'unknown';
        const statusClass = this.getStatusClass(status);
        
        healthContainer.innerHTML = `
            <div class="health-card ${statusClass}">
                <div class="health-header">
                    <i class="fas fa-heartbeat"></i>
                    <h3>系统健康状态</h3>
                </div>
                <div class="health-status">
                    <span class="status-badge ${statusClass}">${this.getStatusText(status)}</span>
                </div>
                <div class="health-details">
                    <p>最后检查: ${new Date().toLocaleString()}</p>
                    ${health?.message ? `<p>消息: ${health.message}</p>` : ''}
                </div>
            </div>
        `;
    }

    renderMetrics(metrics) {
        const metricsContainer = document.getElementById('systemMetrics');
        if (!metricsContainer) return;

        const metricsData = metrics?.metrics || [];
        
        let metricsHtml = '<div class="metrics-grid">';
        
        if (metricsData.length === 0) {
            metricsHtml += '<p class="no-data">暂无指标数据</p>';
        } else {
            metricsData.forEach(metric => {
                metricsHtml += `
                    <div class="metric-card">
                        <div class="metric-name">${metric.name}</div>
                        <div class="metric-value">${metric.value}</div>
                        <div class="metric-unit">${metric.unit || ''}</div>
                    </div>
                `;
            });
        }
        
        metricsHtml += '</div>';
        metricsContainer.innerHTML = metricsHtml;
    }

    renderSystemStatus(status) {
        const statusContainer = document.getElementById('systemStatusDetails');
        if (!statusContainer) return;

        const components = status?.components || {};
        
        let statusHtml = '<div class="status-components">';
        
        if (Object.keys(components).length === 0) {
            statusHtml += '<p class="no-data">暂无状态数据</p>';
        } else {
            Object.entries(components).forEach(([name, info]) => {
                const statusClass = this.getStatusClass(info.status);
                statusHtml += `
                    <div class="component-status ${statusClass}">
                        <div class="component-header">
                            <span class="component-name">${name}</span>
                            <span class="status-badge ${statusClass}">${this.getStatusText(info.status)}</span>
                        </div>
                        ${info.message ? `<div class="component-message">${info.message}</div>` : ''}
                        ${info.last_check ? `<div class="component-time">最后检查: ${new Date(info.last_check).toLocaleString()}</div>` : ''}
                    </div>
                `;
            });
        }
        
        statusHtml += '</div>';
        statusContainer.innerHTML = statusHtml;
    }

    getStatusClass(status) {
        switch (status?.toLowerCase()) {
            case 'healthy':
            case 'ok':
            case 'online':
                return 'status-healthy';
            case 'warning':
            case 'degraded':
                return 'status-warning';
            case 'error':
            case 'critical':
            case 'offline':
                return 'status-error';
            default:
                return 'status-unknown';
        }
    }

    getStatusText(status) {
        switch (status?.toLowerCase()) {
            case 'healthy':
                return '健康';
            case 'ok':
                return '正常';
            case 'online':
                return '在线';
            case 'warning':
                return '警告';
            case 'degraded':
                return '降级';
            case 'error':
                return '错误';
            case 'critical':
                return '严重';
            case 'offline':
                return '离线';
            default:
                return '未知';
        }
    }

    // 手动刷新监控数据
    async refresh() {
        await this.updateSystemStatus();
        
        // 显示刷新成功提示
        if (window.notificationManager) {
            notificationManager.show('监控数据已刷新', 'success');
        }
    }

    // 导出监控数据
    exportData() {
        // 实现数据导出功能
        console.log('导出监控数据功能待实现');
    }
}

// 初始化监控管理器
document.addEventListener('DOMContentLoaded', () => {
    window.monitoringManager = new MonitoringManager();
});

// 导出给其他模块使用
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MonitoringManager;
}