/**
 * Tab 导航管理
 */

let currentTab = 'time-based';

/**
 * 初始化 Tab 导航
 */
function initTabs() {
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            // 切换 Tab 样式
            tabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            
            // 切换面板显示
            currentTab = this.dataset.tab;
            document.querySelectorAll('.tab-panel').forEach(panel => {
                panel.classList.remove('active');
            });
            document.getElementById(`${currentTab}-panel`).classList.add('active');
            
            // 触发 Tab 切换事件
            document.dispatchEvent(new CustomEvent('tabChanged', { 
                detail: { tab: currentTab } 
            }));
        });
    });
}

/**
 * 获取当前 Tab
 * @returns {string} 当前 Tab 名称
 */
function getCurrentTab() {
    return currentTab;
}

/**
 * 导出模块
 */
window.Tabs = {
    init: initTabs,
    getCurrent: getCurrentTab
};
