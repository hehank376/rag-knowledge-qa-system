// 主题管理

class ThemeManager {
    constructor() {
        this.currentTheme = 'light';
        this.themeKey = 'rag-system-theme';
        this.init();
    }

    /**
     * 初始化主题管理器
     */
    init() {
        // 从本地存储加载主题设置
        this.loadTheme();
        
        // 监听系统主题变化
        this.watchSystemTheme();
        
        // 绑定主题切换按钮
        this.bindThemeToggle();
        
        // 应用主题
        this.applyTheme(this.currentTheme);
    }

    /**
     * 从本地存储加载主题设置
     */
    loadTheme() {
        const savedTheme = localStorage.getItem(this.themeKey);
        
        if (savedTheme) {
            this.currentTheme = savedTheme;
        } else {
            // 如果没有保存的主题，检查系统偏好
            this.currentTheme = this.getSystemTheme();
        }
    }

    /**
     * 获取系统主题偏好
     * @returns {string} 主题名称
     */
    getSystemTheme() {
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return 'dark';
        }
        return 'light';
    }

    /**
     * 监听系统主题变化
     */
    watchSystemTheme() {
        if (window.matchMedia) {
            const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
            
            mediaQuery.addEventListener('change', (e) => {
                // 只有在用户没有手动设置主题时才跟随系统
                if (!localStorage.getItem(this.themeKey)) {
                    const newTheme = e.matches ? 'dark' : 'light';
                    this.setTheme(newTheme, false); // 不保存到本地存储
                }
            });
        }
    }

    /**
     * 绑定主题切换按钮
     */
    bindThemeToggle() {
        const themeToggle = document.getElementById('themeToggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => {
                this.toggleTheme();
            });
        }
    }

    /**
     * 切换主题
     */
    toggleTheme() {
        const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';
        this.setTheme(newTheme, true);
    }

    /**
     * 设置主题
     * @param {string} theme - 主题名称
     * @param {boolean} save - 是否保存到本地存储
     */
    setTheme(theme, save = true) {
        this.currentTheme = theme;
        this.applyTheme(theme);
        
        if (save) {
            localStorage.setItem(this.themeKey, theme);
        }
        
        // 触发主题变化事件
        this.dispatchThemeChange(theme);
    }

    /**
     * 应用主题
     * @param {string} theme - 主题名称
     */
    applyTheme(theme) {
        const body = document.body;
        const themeToggle = document.getElementById('themeToggle');
        
        // 移除所有主题类
        body.classList.remove('light-theme', 'dark-theme');
        
        // 添加新主题类
        body.classList.add(`${theme}-theme`);
        
        // 更新主题切换按钮图标
        if (themeToggle) {
            const icon = themeToggle.querySelector('i');
            if (icon) {
                icon.className = theme === 'light' ? 'fas fa-moon' : 'fas fa-sun';
            }
        }
        
        // 更新meta标签（用于移动端状态栏）
        this.updateMetaThemeColor(theme);
        
        // 添加过渡效果类
        body.classList.add('theme-transition');
        
        // 移除过渡效果类（避免影响其他动画）
        setTimeout(() => {
            body.classList.remove('theme-transition');
        }, 300);
    }

    /**
     * 更新meta主题颜色
     * @param {string} theme - 主题名称
     */
    updateMetaThemeColor(theme) {
        let metaThemeColor = document.querySelector('meta[name="theme-color"]');
        
        if (!metaThemeColor) {
            metaThemeColor = document.createElement('meta');
            metaThemeColor.name = 'theme-color';
            document.head.appendChild(metaThemeColor);
        }
        
        // 设置主题颜色
        const colors = {
            light: '#ffffff',
            dark: '#0f172a'
        };
        
        metaThemeColor.content = colors[theme] || colors.light;
    }

    /**
     * 触发主题变化事件
     * @param {string} theme - 主题名称
     */
    dispatchThemeChange(theme) {
        const event = new CustomEvent('themechange', {
            detail: { theme }
        });
        
        document.dispatchEvent(event);
    }

    /**
     * 获取当前主题
     * @returns {string} 当前主题名称
     */
    getCurrentTheme() {
        return this.currentTheme;
    }

    /**
     * 检查是否为深色主题
     * @returns {boolean} 是否为深色主题
     */
    isDarkTheme() {
        return this.currentTheme === 'dark';
    }

    /**
     * 重置主题为系统默认
     */
    resetToSystemTheme() {
        localStorage.removeItem(this.themeKey);
        const systemTheme = this.getSystemTheme();
        this.setTheme(systemTheme, false);
    }

    /**
     * 获取主题CSS变量值
     * @param {string} variableName - CSS变量名
     * @returns {string} CSS变量值
     */
    getThemeVariable(variableName) {
        return getComputedStyle(document.documentElement)
            .getPropertyValue(variableName)
            .trim();
    }

    /**
     * 设置主题CSS变量
     * @param {string} variableName - CSS变量名
     * @param {string} value - CSS变量值
     */
    setThemeVariable(variableName, value) {
        document.documentElement.style.setProperty(variableName, value);
    }

    /**
     * 预加载主题资源
     * @param {string} theme - 主题名称
     */
    preloadTheme(theme) {
        // 预加载主题相关的图片或资源
        const themeImages = {
            light: [],
            dark: []
        };
        
        const images = themeImages[theme] || [];
        images.forEach(src => {
            const img = new Image();
            img.src = src;
        });
    }

    /**
     * 获取主题配置
     * @returns {Object} 主题配置对象
     */
    getThemeConfig() {
        return {
            current: this.currentTheme,
            available: ['light', 'dark'],
            system: this.getSystemTheme(),
            saved: localStorage.getItem(this.themeKey)
        };
    }
}

// 主题动画效果
class ThemeAnimations {
    /**
     * 主题切换动画
     * @param {string} fromTheme - 原主题
     * @param {string} toTheme - 目标主题
     */
    static async transitionTheme(fromTheme, toTheme) {
        const body = document.body;
        
        // 添加过渡类
        body.classList.add('theme-transitioning');
        
        // 创建遮罩层
        const overlay = document.createElement('div');
        overlay.className = 'theme-transition-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: ${toTheme === 'dark' ? '#0f172a' : '#ffffff'};
            opacity: 0;
            z-index: 9999;
            pointer-events: none;
            transition: opacity 0.3s ease;
        `;
        
        document.body.appendChild(overlay);
        
        // 淡入遮罩
        requestAnimationFrame(() => {
            overlay.style.opacity = '0.8';
        });
        
        // 等待动画完成
        await new Promise(resolve => setTimeout(resolve, 150));
        
        // 切换主题
        body.classList.remove(`${fromTheme}-theme`);
        body.classList.add(`${toTheme}-theme`);
        
        // 淡出遮罩
        overlay.style.opacity = '0';
        
        // 清理
        setTimeout(() => {
            body.classList.remove('theme-transitioning');
            if (overlay.parentNode) {
                overlay.parentNode.removeChild(overlay);
            }
        }, 300);
    }

    /**
     * 主题切换按钮动画
     * @param {Element} button - 按钮元素
     * @param {string} theme - 目标主题
     */
    static animateThemeButton(button, theme) {
        const icon = button.querySelector('i');
        if (!icon) return;
        
        // 旋转动画
        icon.style.transform = 'rotate(180deg)';
        
        setTimeout(() => {
            icon.className = theme === 'light' ? 'fas fa-moon' : 'fas fa-sun';
            icon.style.transform = 'rotate(0deg)';
        }, 150);
    }
}

// 创建全局主题管理器实例
let themeManager;

// DOM加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    themeManager = new ThemeManager();
    
    // 监听主题变化事件
    document.addEventListener('themechange', (event) => {
        console.log('主题已切换到:', event.detail.theme);
        
        // 可以在这里添加主题切换后的额外处理
        // 例如：更新图表颜色、重新渲染某些组件等
    });
});

// 导出主题管理器
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        ThemeManager,
        ThemeAnimations
    };
}