// MyHelper JavaScript 功能

// 全局配置
const MyHelper = {
    config: {
        apiBase: '/api/v1',
        refreshInterval: 30000, // 30秒
        toastDuration: 5000 // 5秒
    },
    
    // 工具函数
    utils: {
        // 格式化日期时间
        formatDateTime: function(dateString) {
            if (!dateString) return '-';
            const date = new Date(dateString);
            return date.toLocaleString('zh-CN', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        },
        
        // 计算时间差
        timeDiff: function(startTime, endTime) {
            if (!startTime || !endTime) return null;
            const start = new Date(startTime);
            const end = new Date(endTime);
            const diff = end - start;
            
            if (diff < 1000) return `${diff}ms`;
            if (diff < 60000) return `${Math.round(diff / 1000)}s`;
            if (diff < 3600000) return `${Math.round(diff / 60000)}m`;
            return `${Math.round(diff / 3600000)}h`;
        },
        
        // 复制到剪贴板
        copyToClipboard: function(text) {
            if (navigator.clipboard) {
                navigator.clipboard.writeText(text).then(() => {
                    MyHelper.ui.showToast('已复制到剪贴板', 'success');
                });
            } else {
                // 降级方案
                const textArea = document.createElement('textarea');
                textArea.value = text;
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);
                MyHelper.ui.showToast('已复制到剪贴板', 'success');
            }
        },
        
        // 防抖函数
        debounce: function(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        },
        
        // 节流函数
        throttle: function(func, limit) {
            let inThrottle;
            return function() {
                const args = arguments;
                const context = this;
                if (!inThrottle) {
                    func.apply(context, args);
                    inThrottle = true;
                    setTimeout(() => inThrottle = false, limit);
                }
            }
        }
    },
    
    // UI 相关功能
    ui: {
        // 显示加载状态
        showLoading: function(element) {
            if (typeof element === 'string') {
                element = document.querySelector(element);
            }
            if (element) {
                element.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 加载中...';
                element.disabled = true;
            }
        },
        
        // 隐藏加载状态
        hideLoading: function(element, originalText) {
            if (typeof element === 'string') {
                element = document.querySelector(element);
            }
            if (element) {
                element.innerHTML = originalText || element.getAttribute('data-original-text') || '完成';
                element.disabled = false;
            }
        },
        
        // 显示消息提示
        showToast: function(message, type = 'info') {
            const toastContainer = this.getOrCreateToastContainer();
            const toast = document.createElement('div');
            toast.className = `alert alert-${type} alert-dismissible fade show`;
            toast.innerHTML = `
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            
            toastContainer.appendChild(toast);
            
            // 自动消失
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.remove();
                }
            }, MyHelper.config.toastDuration);
        },
        
        // 获取或创建消息容器
        getOrCreateToastContainer: function() {
            let container = document.getElementById('toast-container');
            if (!container) {
                container = document.createElement('div');
                container.id = 'toast-container';
                container.style.position = 'fixed';
                container.style.top = '20px';
                container.style.right = '20px';
                container.style.zIndex = '9999';
                container.style.maxWidth = '400px';
                document.body.appendChild(container);
            }
            return container;
        },
        
        // 确认对话框
        confirm: function(message, callback) {
            const result = window.confirm(message);
            if (result && callback) {
                callback();
            }
            return result;
        },
        
        // 创建模态框
        createModal: function(title, content, actions = []) {
            const modalId = 'dynamic-modal-' + Date.now();
            const modal = document.createElement('div');
            modal.className = 'modal fade';
            modal.id = modalId;
            modal.tabIndex = -1;
            
            let actionsHtml = '';
            actions.forEach(action => {
                actionsHtml += `<button type="button" class="btn btn-${action.type || 'secondary'}" ${action.dismiss ? 'data-bs-dismiss="modal"' : ''} onclick="${action.onclick || ''}">${action.text}</button>`;
            });
            
            modal.innerHTML = `
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">${title}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">${content}</div>
                        <div class="modal-footer">${actionsHtml}</div>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
            const bsModal = new bootstrap.Modal(modal);
            
            // 模态框关闭时移除元素
            modal.addEventListener('hidden.bs.modal', () => {
                modal.remove();
            });
            
            return bsModal;
        }
    },
    
    // API 相关功能
    api: {
        // 发送请求
        request: function(url, options = {}) {
            const defaultOptions = {
                headers: {
                    'Content-Type': 'application/json'
                }
            };
            
            const finalOptions = Object.assign(defaultOptions, options);
            
            return fetch(MyHelper.config.apiBase + url, finalOptions)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return response.json();
                })
                .catch(error => {
                    console.error('API request failed:', error);
                    MyHelper.ui.showToast('请求失败: ' + error.message, 'danger');
                    throw error;
                });
        },
        
        // 获取任务列表
        getTasks: function() {
            return this.request('/hooks');
        },
        
        // 触发任务
        triggerTask: function(taskId, context = {}) {
            return this.request(`/hooks/${taskId}`, {
                method: 'POST',
                body: JSON.stringify({
                    trigger_context: context
                })
            });
        },
        
        // 验证任务
        validateTask: function(taskId, context = {}) {
            return this.request(`/hooks/${taskId}/validate`, {
                method: 'POST',
                body: JSON.stringify({
                    trigger_context: context
                })
            });
        },
        
        // 获取报告列表
        getReports: function(params = {}) {
            const queryString = new URLSearchParams(params).toString();
            const url = '/reports' + (queryString ? '?' + queryString : '');
            return this.request(url);
        },
        
        // 获取报告详情
        getReport: function(reportId) {
            return this.request(`/reports/${reportId}`);
        },
        
        // 获取报告状态
        getReportStatus: function(reportId) {
            return this.request(`/reports/${reportId}/status`);
        }
    },
    
    // 页面特定功能
    pages: {
        // 任务页面功能
        tasks: {
            init: function() {
                // 初始化任务页面
                this.bindEvents();
                this.startAutoRefresh();
            },
            
            bindEvents: function() {
                // 绑定事件处理器
                document.addEventListener('click', (e) => {
                    if (e.target.matches('[data-action="trigger-task"]')) {
                        const taskId = e.target.getAttribute('data-task-id');
                        this.triggerTask(taskId);
                    }
                    
                    if (e.target.matches('[data-action="validate-task"]')) {
                        const taskId = e.target.getAttribute('data-task-id');
                        this.validateTask(taskId);
                    }
                });
            },
            
            triggerTask: function(taskId) {
                MyHelper.api.triggerTask(taskId, {
                    source: 'web_interface',
                    timestamp: new Date().toISOString()
                }).then(data => {
                    if (data.status === 'queued') {
                        MyHelper.ui.showToast(`任务已提交执行，报告ID: ${data.report_id}`, 'success');
                    }
                }).catch(error => {
                    MyHelper.ui.showToast('任务执行失败', 'danger');
                });
            },
            
            validateTask: function(taskId) {
                MyHelper.api.validateTask(taskId).then(data => {
                    if (data.valid) {
                        MyHelper.ui.showToast('任务验证通过', 'success');
                    } else {
                        MyHelper.ui.showToast('任务验证失败: ' + data.message, 'warning');
                    }
                });
            },
            
            startAutoRefresh: function() {
                // 如果页面有运行中的任务，启动自动刷新
                const runningTasks = document.querySelectorAll('.badge.bg-primary');
                if (runningTasks.length > 0) {
                    setTimeout(() => {
                        location.reload();
                    }, MyHelper.config.refreshInterval);
                }
            }
        },
        
        // 报告页面功能
        reports: {
            init: function() {
                this.bindEvents();
                this.startAutoRefresh();
            },
            
            bindEvents: function() {
                // 绑定事件处理器
            },
            
            startAutoRefresh: function() {
                // 如果有运行中的报告，启动自动刷新
                const runningReports = document.querySelectorAll('.badge.bg-primary');
                if (runningReports.length > 0) {
                    setTimeout(() => {
                        location.reload();
                    }, MyHelper.config.refreshInterval);
                }
            }
        }
    }
};

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 根据当前页面初始化相应功能
    const currentPage = document.body.getAttribute('data-page');
    
    switch (currentPage) {
        case 'tasks':
            MyHelper.pages.tasks.init();
            break;
        case 'reports':
            MyHelper.pages.reports.init();
            break;
    }
    
    // 全局功能初始化
    initGlobalFeatures();
});

// 初始化全局功能
function initGlobalFeatures() {
    // 初始化所有提示工具
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // 初始化所有弹出框
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // 添加复制按钮功能
    document.querySelectorAll('code').forEach(function(codeBlock) {
        if (codeBlock.textContent.length > 20) {
            const copyBtn = document.createElement('button');
            copyBtn.className = 'btn btn-sm btn-outline-secondary copy-btn';
            copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
            copyBtn.title = '复制代码';
            copyBtn.style.position = 'absolute';
            copyBtn.style.top = '5px';
            copyBtn.style.right = '5px';
            copyBtn.style.fontSize = '12px';
            copyBtn.style.padding = '2px 6px';
            
            const container = codeBlock.parentElement;
            if (container.tagName === 'PRE') {
                container.style.position = 'relative';
                container.appendChild(copyBtn);
                
                copyBtn.addEventListener('click', function() {
                    MyHelper.utils.copyToClipboard(codeBlock.textContent);
                });
            }
        }
    });
    
    // 添加返回顶部按钮
    const backToTop = document.createElement('button');
    backToTop.className = 'btn btn-primary fab';
    backToTop.innerHTML = '<i class="fas fa-arrow-up"></i>';
    backToTop.title = '返回顶部';
    backToTop.style.display = 'none';
    document.body.appendChild(backToTop);
    
    // 滚动事件处理
    window.addEventListener('scroll', MyHelper.utils.throttle(function() {
        if (window.pageYOffset > 300) {
            backToTop.style.display = 'flex';
        } else {
            backToTop.style.display = 'none';
        }
    }, 100));
    
    // 返回顶部点击事件
    backToTop.addEventListener('click', function() {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });
}

// 导出到全局
window.MyHelper = MyHelper;