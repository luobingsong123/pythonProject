/**
 * 主入口文件
 */

/**
 * 页面加载完成后初始化
 */
document.addEventListener('DOMContentLoaded', function() {
    // 初始化 Tab 导航
    Tabs.init();
    
    // 初始化各面板
    TimeBasedPanel.init();
    BacktraderPanel.init();
    DataUpdatePanel.init();
    KronosPanel.init();
    
    // 初始化 K 线图
    KlineChart.init();
    
    // 监听 Tab 切换事件，调整图表大小
    document.addEventListener('tabChanged', function(e) {
        const tab = e.detail.tab;
        setTimeout(() => {
            if (tab === 'backtrader') {
                KlineChart.resize();
            }
            if (tab === 'time-based') {
                const profitChart = TimeBasedPanel.getProfitChart();
                if (profitChart) {
                    profitChart.resize();
                }
            }
            if (tab === 'kronos-predict') {
                // 切换到Kronos面板时确保图表已初始化
                if (!window.KronosPanel.getChart()) {
                    window.KronosPanel.reinitChart();
                }
                KronosPanel.resize();
            }
        }, 100);
    });
    
    // 监听 K 线图加载事件
    document.addEventListener('loadKline', function(e) {
        const { stockCode, buyDate, sellDate, buyPrice, sellPrice } = e.detail;
        KlineChart.load(stockCode, buyDate, sellDate, buyPrice, sellPrice);
    });
    
    // 监听窗口大小变化
    window.addEventListener('resize', function() {
        KlineChart.resize();
        const profitChart = TimeBasedPanel.getProfitChart();
        if (profitChart) {
            profitChart.resize();
        }
        KronosPanel.resize();
    });
});
