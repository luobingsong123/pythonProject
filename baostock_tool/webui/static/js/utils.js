/**
 * 通用工具函数
 */

/**
 * 根据证券代码判断市场
 * @param {string} code - 证券代码
 * @returns {string} 市场代码 (sh/sz/bj)
 */
function determineMarket(code) {
    const codeInt = parseInt(code);
    if (codeInt >= 600000 && codeInt <= 689999) return 'sh';
    if (codeInt >= 300001 && codeInt <= 301999) return 'sz';
    if (codeInt >= 430001 && codeInt <= 839999) return 'bj';
    if (codeInt >= 0 && codeInt <= 2999) return 'sz';
    if (codeInt >= 200001 && codeInt <= 299999) return 'sz';
    return 'sh';
}

/**
 * 格式化数值
 * @param {number} value - 数值
 * @param {number} decimals - 小数位数
 * @returns {string} 格式化后的字符串
 */
function formatNumber(value, decimals = 2) {
    if (value === null || value === undefined) return '-';
    return Number(value).toLocaleString(undefined, {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    });
}

/**
 * 格式化日期
 * @param {Date|string} date - 日期对象或字符串
 * @returns {string} 格式化后的日期字符串
 */
function formatDate(date) {
    if (!date) return '';
    return new Date(date).toLocaleDateString('zh-CN');
}

/**
 * 格式化货币
 * @param {number} value - 数值
 * @returns {string} 格式化后的货币字符串
 */
function formatCurrency(value) {
    if (value === null || value === undefined) return '-';
    return '¥' + Number(value).toLocaleString(undefined, {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2
    });
}

/**
 * 格式化百分比
 * @param {number} value - 数值
 * @param {number} decimals - 小数位数
 * @returns {string} 格式化后的百分比字符串
 */
function formatPercent(value, decimals = 2) {
    if (value === null || value === undefined) return '-';
    const sign = value >= 0 ? '+' : '';
    return sign + value.toFixed(decimals) + '%';
}

/**
 * 显示错误消息
 * @param {HTMLElement} container - 容器元素
 * @param {string} message - 错误消息
 */
function showError(container, message) {
    container.innerHTML = `<div class="error-message">${message}</div>`;
}

/**
 * 显示加载状态
 * @param {HTMLElement} container - 容器元素
 * @param {string} message - 加载消息
 */
function showLoading(container, message = '加载中...') {
    container.innerHTML = `<div class="loading"><span class="material-icons" style="animation: spin 1s linear infinite; font-size: 32px;">refresh</span><div style="margin-top: 8px;">${message}</div></div>`;
}

/**
 * 显示空状态
 * @param {HTMLElement} container - 容器元素
 * @param {string} icon - Material Icons 图标名
 * @param {string} message - 提示消息
 */
function showEmpty(container, icon = 'inbox', message = '暂无数据') {
    container.innerHTML = `<div class="empty-state"><span class="material-icons empty-state-icon">${icon}</span><div>${message}</div></div>`;
}

/**
 * 导出模块
 */
window.Utils = {
    determineMarket,
    formatNumber,
    formatDate,
    formatCurrency,
    formatPercent,
    showError,
    showLoading,
    showEmpty
};
