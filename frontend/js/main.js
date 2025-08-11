/**
 * Main Application Controller
 * Handles tab switching, navigation, and overall app initialization
 */

class App {
    constructor() {
        this.currentTab = 'documents';
        this.init();
    }

    init() {
        this.setupNavigation();
        this.setupSystemStatus();
        this.initializeCurrentTab();
    }

    setupNavigation() {
        const navLinks = document.querySelectorAll('.nav-link');
        
        navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const tabId = link.getAttribute('data-tab');
                this.switchTab(tabId);
            });
        });
    }

    switchTab(tabId) {
        if (tabId === this.currentTab) return;

        // Update navigation
        const navLinks = document.querySelectorAll('.nav-link');
        navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('data-tab') === tabId) {
                link.classList.add('active');
            }
        });

        // Update content
        const tabContents = document.querySelectorAll('.tab-content');
        tabContents.forEach(content => {
            content.classList.remove('active');
            if (content.id === tabId) {
                content.classList.add('active');
            }
        });

        this.currentTab = tabId;
        
        // Initialize tab-specific functionality
        this.initializeTab(tabId);
        
        // Update URL hash
        window.location.hash = tabId;
    }

    initializeTab(tabId) {
        switch (tabId) {
            case 'documents':
                if (window.documentManager) {
                    window.documentManager.loadDocuments();
                }
                break;
            case 'qa':
                if (window.qaManager) {
                    // Q&A manager is already initialized
                    // Could add specific initialization here if needed
                }
                break;
            case 'history':
                this.initializeHistoryTab();
                break;
            case 'settings':
                this.initializeSettingsTab();
                break;
        }
    }

    initializeCurrentTab() {
        // Check URL hash for initial tab
        const hash = window.location.hash.substring(1);
        const validTabs = ['documents', 'qa', 'history', 'settings'];
        
        if (hash && validTabs.includes(hash)) {
            this.switchTab(hash);
        } else {
            this.switchTab('documents');
        }
    }

    initializeHistoryTab() {
        if (window.historyManager) {
            window.historyManager.loadSessions();
        }
    }

    initializeSettingsTab() {
        if (window.settingsManager) {
            window.settingsManager.loadSettings();
        }
    }

    setupSystemStatus() {
        this.updateSystemStatus();
        
        // Update system status periodically
        setInterval(() => {
            this.updateSystemStatus();
        }, 30000); // Every 30 seconds
    }

    async updateSystemStatus() {
        const statusIndicator = document.querySelector('.status-indicator');
        const statusText = document.querySelector('.status-text');
        
        if (!statusIndicator || !statusText) return;

        try {
            // Check system health
            const response = await fetch('http://localhost:8000/health');
            
            if (response.ok) {
                statusIndicator.className = 'fas fa-circle status-indicator status-online';
                statusText.textContent = '系统正常';
            } else {
                throw new Error('Health check failed');
            }
        } catch (error) {
            statusIndicator.className = 'fas fa-circle status-indicator status-offline';
            statusText.textContent = '系统异常';
            console.error('System health check failed:', error);
        }
    }
}

// Global error handler
window.addEventListener('error', (event) => {
    console.error('Global error:', event.error);
    if (window.notificationManager) {
        notificationManager.show('发生了未预期的错误', 'error');
    }
});

// Global unhandled promise rejection handler
window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
    if (window.notificationManager) {
        notificationManager.show('网络请求失败', 'error');
    }
});

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
    
    // Initialize global managers
    if (typeof ThemeManager !== 'undefined') {
        window.themeManager = new ThemeManager();
    }
    
    if (typeof NotificationManager !== 'undefined') {
        window.notificationManager = new NotificationManager();
    }
    
    console.log('RAG Knowledge QA System initialized');
});

// Handle browser back/forward buttons
window.addEventListener('popstate', () => {
    if (window.app) {
        window.app.initializeCurrentTab();
    }
});

// Utility function to show loading state
function showLoading(element, text = '加载中...') {
    if (!element) return;
    
    element.innerHTML = `
        <div class="loading-state">
            <div class="loading-spinner"></div>
            <p>${text}</p>
        </div>
    `;
}

// Utility function to show empty state
function showEmptyState(element, icon = 'fa-folder-open', title = '暂无数据', description = '') {
    if (!element) return;
    
    element.innerHTML = `
        <div class="empty-state">
            <i class="fas ${icon}"></i>
            <h3>${title}</h3>
            ${description ? `<p>${description}</p>` : ''}
        </div>
    `;
}

// Utility function to show error state
function showErrorState(element, message = '加载失败，请重试') {
    if (!element) return;
    
    element.innerHTML = `
        <div class="error-state">
            <i class="fas fa-exclamation-triangle"></i>
            <h3>出错了</h3>
            <p>${message}</p>
            <button class="btn btn-primary" onclick="location.reload()">重新加载</button>
        </div>
    `;
}