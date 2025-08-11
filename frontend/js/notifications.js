// 通知系统

class NotificationManager {
    constructor() {
        this.container = null;
        this.notifications = new Map();
        this.defaultDuration = 5000; // 5秒
        this.maxNotifications = 5;
        this.init();
    }

    /**
     * 初始化通知管理器
     */
    init() {
        this.createContainer();
    }

    /**
     * 创建通知容器
     */
    createContainer() {
        this.container = document.getElementById('notifications');
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = 'notifications';
            this.container.className = 'notifications';
            document.body.appendChild(this.container);
        }
    }

    /**
     * 显示通知
     * @param {Object|string} options - 通知选项或消息文本
     * @param {string} type - 通知类型（当第一个参数是字符串时使用）
     * @returns {string} 通知ID
     */
    show(options = {}, type = 'info') {
        console.log('显示通知:', options, type);

        // 兼容旧的调用方式：show(message, type)
        if (typeof options === 'string') {
            options = {
                message: options,
                type: type
            };
        }

        const {
            type: notificationType = 'info',
            title = '',
            message = '',
            duration = this.defaultDuration,
            persistent = false,
            actions = []
        } = options;

        console.log('处理后的通知参数:', {
            type: notificationType,
            title,
            message,
            duration,
            persistent,
            actions
        });

        // 生成唯一ID
        const id = this.generateId();

        // 创建通知元素
        const notification = this.createNotificationElement({
            id,
            type: notificationType,
            title,
            message,
            persistent,
            actions
        });

        // 添加到容器
        console.log('添加通知到容器:', this.container, notification);
        this.container.appendChild(notification);
        this.notifications.set(id, {
            element: notification,
            timer: null,
            persistent
        });

        // 触发入场动画
        requestAnimationFrame(() => {
            notification.classList.add('show');
            console.log('通知动画触发:', notification);
        });

        // 设置自动关闭
        if (!persistent && duration > 0) {
            this.setAutoClose(id, duration);
        }

        // 限制通知数量
        this.limitNotifications();

        return id;
    }

    /**
     * 创建通知元素
     * @param {Object} options - 通知选项
     * @returns {Element} 通知元素
     */
    createNotificationElement(options) {
        const { id, type, title, message, persistent, actions } = options;

        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.dataset.id = id;

        // 图标
        const icon = document.createElement('div');
        icon.className = 'notification-icon';
        icon.innerHTML = `<i class="${this.getTypeIcon(type)}"></i>`;

        // 内容
        const content = document.createElement('div');
        content.className = 'notification-content';

        if (title) {
            const titleElement = document.createElement('div');
            titleElement.className = 'notification-title';
            titleElement.textContent = title;
            content.appendChild(titleElement);
        }

        if (message) {
            const messageElement = document.createElement('div');
            messageElement.className = 'notification-message';
            messageElement.textContent = message;
            content.appendChild(messageElement);
        }

        // 操作按钮
        if (actions && actions.length > 0) {
            const actionsContainer = document.createElement('div');
            actionsContainer.className = 'notification-actions';

            actions.forEach(action => {
                const button = document.createElement('button');
                button.className = `btn btn-sm ${action.style || 'btn-secondary'}`;
                button.textContent = action.text;
                button.addEventListener('click', () => {
                    if (action.handler) {
                        action.handler();
                    }
                    if (action.dismiss !== false) {
                        this.dismiss(id);
                    }
                });
                actionsContainer.appendChild(button);
            });

            content.appendChild(actionsContainer);
        }

        // 关闭按钮
        const closeButton = document.createElement('button');
        closeButton.className = 'notification-close';
        closeButton.innerHTML = '<i class="fas fa-times"></i>';
        closeButton.addEventListener('click', () => {
            this.dismiss(id);
        });

        // 组装通知
        notification.appendChild(icon);
        notification.appendChild(content);
        if (!persistent || actions.length === 0) {
            notification.appendChild(closeButton);
        }

        return notification;
    }

    /**
     * 获取类型图标
     * @param {string} type - 通知类型
     * @returns {string} 图标类名
     */
    getTypeIcon(type) {
        const icons = {
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle',
            warning: 'fas fa-exclamation-triangle',
            info: 'fas fa-info-circle'
        };

        return icons[type] || icons.info;
    }

    /**
     * 设置自动关闭
     * @param {string} id - 通知ID
     * @param {number} duration - 持续时间
     */
    setAutoClose(id, duration) {
        const notification = this.notifications.get(id);
        if (!notification) return;

        notification.timer = setTimeout(() => {
            this.dismiss(id);
        }, duration);
    }

    /**
     * 关闭通知
     * @param {string} id - 通知ID
     */
    dismiss(id) {
        const notification = this.notifications.get(id);
        if (!notification) return;

        // 清除定时器
        if (notification.timer) {
            clearTimeout(notification.timer);
        }

        // 添加退出动画
        notification.element.classList.add('dismissing');

        // 移除元素
        setTimeout(() => {
            if (notification.element.parentNode) {
                notification.element.parentNode.removeChild(notification.element);
            }
            this.notifications.delete(id);
        }, 300);
    }

    /**
     * 关闭所有通知
     */
    dismissAll() {
        const ids = Array.from(this.notifications.keys());
        ids.forEach(id => this.dismiss(id));
    }

    /**
     * 限制通知数量
     */
    limitNotifications() {
        const notifications = Array.from(this.notifications.entries());
        if (notifications.length > this.maxNotifications) {
            const oldestId = notifications[0][0];
            this.dismiss(oldestId);
        }
    }

    /**
     * 生成唯一ID
     * @returns {string} 唯一ID
     */
    generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }

    /**
     * 显示成功通知
     * @param {string} message - 消息内容
     * @param {string} title - 标题
     * @param {Object} options - 其他选项
     * @returns {string} 通知ID
     */
    success(message, title = '成功', options = {}) {
        return this.show({
            type: 'success',
            title,
            message,
            ...options
        });
    }

    /**
     * 显示错误通知
     * @param {string} message - 消息内容
     * @param {string} title - 标题
     * @param {Object} options - 其他选项
     * @returns {string} 通知ID
     */
    error(message, title = '错误', options = {}) {
        return this.show({
            type: 'error',
            title,
            message,
            duration: 8000, // 错误通知显示更长时间
            ...options
        });
    }

    /**
     * 显示警告通知
     * @param {string} message - 消息内容
     * @param {string} title - 标题
     * @param {Object} options - 其他选项
     * @returns {string} 通知ID
     */
    warning(message, title = '警告', options = {}) {
        return this.show({
            type: 'warning',
            title,
            message,
            duration: 6000,
            ...options
        });
    }

    /**
     * 显示信息通知
     * @param {string} message - 消息内容
     * @param {string} title - 标题
     * @param {Object} options - 其他选项
     * @returns {string} 通知ID
     */
    info(message, title = '提示', options = {}) {
        return this.show({
            type: 'info',
            title,
            message,
            ...options
        });
    }

    /**
     * 显示加载通知
     * @param {string} message - 消息内容
     * @param {string} title - 标题
     * @returns {string} 通知ID
     */
    loading(message = '处理中...', title = '') {
        return this.show({
            type: 'info',
            title,
            message,
            persistent: true,
            actions: []
        });
    }

    /**
     * 显示确认通知
     * @param {string} message - 消息内容
     * @param {Function} onConfirm - 确认回调
     * @param {Function} onCancel - 取消回调
     * @param {string} title - 标题
     * @returns {string} 通知ID
     */
    confirm(message, onConfirm, onCancel = null, title = '确认') {
        return this.show({
            type: 'warning',
            title,
            message,
            persistent: true,
            actions: [
                {
                    text: '确认',
                    style: 'btn-primary',
                    handler: onConfirm
                },
                {
                    text: '取消',
                    style: 'btn-secondary',
                    handler: onCancel
                }
            ]
        });
    }

    /**
     * 更新通知内容
     * @param {string} id - 通知ID
     * @param {Object} options - 更新选项
     */
    update(id, options = {}) {
        const notification = this.notifications.get(id);
        if (!notification) return;

        const element = notification.element;
        const { title, message, type } = options;

        if (type) {
            // 更新类型样式
            element.className = element.className.replace(/notification-\w+/, `notification-${type}`);

            // 更新图标
            const icon = element.querySelector('.notification-icon i');
            if (icon) {
                icon.className = this.getTypeIcon(type);
            }
        }

        if (title !== undefined) {
            const titleElement = element.querySelector('.notification-title');
            if (titleElement) {
                titleElement.textContent = title;
            }
        }

        if (message !== undefined) {
            const messageElement = element.querySelector('.notification-message');
            if (messageElement) {
                messageElement.textContent = message;
            }
        }
    }

    /**
     * 获取通知数量
     * @returns {number} 通知数量
     */
    getCount() {
        return this.notifications.size;
    }

    /**
     * 检查是否有指定类型的通知
     * @param {string} type - 通知类型
     * @returns {boolean} 是否存在
     */
    hasType(type) {
        return Array.from(this.notifications.values()).some(
            notification => notification.element.classList.contains(`notification-${type}`)
        );
    }
}

// 创建全局通知管理器实例
let notifications;
let notificationManager;

// DOM加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    console.log('初始化通知系统...');
    notifications = new NotificationManager();
    notificationManager = notifications; // 设置全局变量
    window.notificationManager = notifications; // 确保全局可访问
    console.log('通知系统初始化完成:', window.notificationManager);

    // 测试通知系统
    setTimeout(() => {
        if (window.notificationManager) {
            console.log('测试通知系统...');
            window.notificationManager.info('通知系统已加载', '系统提示');
        }
    }, 1000);
});

// 添加CSS样式（如果还没有）
if (!document.querySelector('#notification-styles')) {
    const style = document.createElement('style');
    style.id = 'notification-styles';
    style.textContent = `
        .notification {
            transform: translateX(100%);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        .notification.show {
            transform: translateX(0);
        }
        
        .notification.dismissing {
            transform: translateX(100%);
            opacity: 0;
        }
        
        .notification-actions {
            display: flex;
            gap: var(--spacing-sm);
            margin-top: var(--spacing-sm);
        }
        
        .notification-actions .btn {
            font-size: 0.75rem;
            padding: var(--spacing-xs) var(--spacing-sm);
        }
    `;
    document.head.appendChild(style);
}

// 导出通知管理器
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        NotificationManager
    };
}