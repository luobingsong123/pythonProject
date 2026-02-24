/**
 * 基于时间回测面板
 */

let tbProfitChart = null;
let currentTbPeriod = null;
let tbSummaryData = [];
let currentBenchmark = 'sh000001';

// 基准指数配置
const benchmarkConfig = {
    'sh000001': { name: '上证指数', market: 'sh', code: '000001' },
    'sz399001': { name: '深证成指', market: 'sz', code: '399001' },
    'sh000300': { name: '沪深300', market: 'sh', code: '000300' },
    'sh000852': { name: '中证1000', market: 'sh', code: '000852' }
};

/**
 * 初始化面板
 */
function initTimeBasedPanel() {
    loadTbStrategies();
    initTbProfitChart();
    initBenchmarkButtons();

    document.getElementById('tb-search-btn').addEventListener('click', searchTimeBased);
}

/**
 * 初始化收益图表
 */
function initTbProfitChart() {
    const chartDom = document.getElementById('tb-profit-chart');
    if (!chartDom) return;
    
    tbProfitChart = echarts.init(chartDom);
    tbProfitChart.setOption({
        title: { text: '选择回测区间后显示收益曲线', left: 'center', top: 'center', textStyle: { color: '#999', fontSize: 14 } }
    });

    window.addEventListener('resize', function() {
        if (tbProfitChart) {
            tbProfitChart.resize();
        }
    });
}

/**
 * 初始化基准按钮
 */
function initBenchmarkButtons() {
    document.querySelectorAll('.benchmark-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.benchmark-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            currentBenchmark = this.dataset.index;

            // 如果已选择回测区间，重新加载图表
            if (currentTbPeriod) {
                loadTbProfitChartData(currentTbPeriod.strategy_name, currentTbPeriod.backtest_start_date, currentTbPeriod.backtest_end_date);
            }
        });
    });
}

/**
 * 加载策略列表
 */
async function loadTbStrategies() {
    try {
        const response = await fetch('/api/strategies?backtest_framework=time_based');
        const result = await response.json();

        if (result.success) {
            const select = document.getElementById('tb-strategy-select');
            select.innerHTML = '<option value="">请选择策略</option>';
            result.data.forEach(strategy => {
                const option = document.createElement('option');
                option.value = strategy;
                option.textContent = strategy;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('加载策略列表失败:', error);
    }
}

/**
 * 搜索回测记录
 */
async function searchTimeBased() {
    const strategy = document.getElementById('tb-strategy-select').value;
    const periodsContainer = document.getElementById('tb-periods-container');

    if (!strategy) {
        Utils.showError(periodsContainer, '请先选择策略');
        return;
    }

    Utils.showLoading(periodsContainer, '加载中...');

    // 重置其他面板
    document.getElementById('tb-params-container').innerHTML = `<div class="empty-state"><span class="material-icons empty-state-icon">tune</span><div>选择回测区间后显示策略参数</div></div>`;
    document.getElementById('tb-daily-body').innerHTML = `<tr><td colspan="8"><div class="empty-state"><span class="material-icons empty-state-icon">inbox</span><div>选择回测区间后显示每日持仓记录</div></div></td></tr>`;
    tbProfitChart.setOption({
        title: { text: '选择回测区间后显示收益曲线', left: 'center', top: 'center', textStyle: { color: '#999', fontSize: 14 } }
    });
    document.getElementById('tb-chart-period').textContent = '';
    document.getElementById('tb-daily-count').textContent = '';
    document.getElementById('tb-stats-period').textContent = '';

    try {
        const url = `/api/summary_list?backtest_framework=time_based&strategy=${encodeURIComponent(strategy)}`;
        const response = await fetch(url);
        const result = await response.json();

        if (result.success) {
            tbSummaryData = result.data;
            if (result.data.length === 0) {
                Utils.showEmpty(periodsContainer, 'event_note', '该策略暂无回测记录');
                updateTbStats([]);
            } else {
                updateTbStats(result.data);
                renderTbPeriods(result.data);
            }
        } else {
            Utils.showError(periodsContainer, result.error);
        }
    } catch (error) {
        Utils.showError(periodsContainer, '网络错误: ' + error.message);
    }
}

/**
 * 更新汇总统计
 */
function updateTbStats(data) {
    const count = data.length;
    
    if (count === 0) {
        document.getElementById('tb-stat-return').textContent = '-';
        document.getElementById('tb-stat-winrate').textContent = '-';
        document.getElementById('tb-stat-drawdown').textContent = '-';
        document.getElementById('tb-stat-sharpe').textContent = '-';
        document.getElementById('tb-stat-trades').textContent = '-';
        document.getElementById('tb-stat-days').textContent = '-';
        document.getElementById('tb-stat-profit-loss').textContent = '-';
        document.getElementById('tb-stat-commission').textContent = '-';
        document.getElementById('tb-stats-period').textContent = '';
        return;
    }

    // 计算各指标平均值
    const avgReturn = data.reduce((sum, d) => sum + (d.summary?.total_return || 0), 0) / count;
    const avgWinRate = data.reduce((sum, d) => sum + (d.summary?.win_rate || 0), 0) / count;
    const avgDrawdown = data.reduce((sum, d) => sum + (d.summary?.max_drawdown || 0), 0) / count;
    const avgSharpe = data.reduce((sum, d) => sum + (d.summary?.sharpe_ratio || 0), 0) / count;
    const totalTrades = data.reduce((sum, d) => sum + (d.summary?.total_trades || 0), 0);
    const totalDays = data.reduce((sum, d) => sum + (d.summary?.trading_days_count || 0), 0);
    const totalProfitTrades = data.reduce((sum, d) => sum + (d.summary?.profit_trade_count || 0), 0);
    const totalLossTrades = data.reduce((sum, d) => sum + (d.summary?.loss_trade_count || 0), 0);
    const totalCommission = data.reduce((sum, d) => sum + (d.summary?.total_commission || 0), 0);

    document.getElementById('tb-stat-return').textContent = avgReturn.toFixed(2) + '%';
    document.getElementById('tb-stat-return').className = 'tb-stat-value ' + (avgReturn >= 0 ? 'negative' : 'positive');
    document.getElementById('tb-stat-winrate').textContent = avgWinRate.toFixed(1) + '%';
    document.getElementById('tb-stat-drawdown').textContent = avgDrawdown.toFixed(2) + '%';
    document.getElementById('tb-stat-drawdown').className = 'tb-stat-value positive';
    document.getElementById('tb-stat-sharpe').textContent = avgSharpe.toFixed(2);
    document.getElementById('tb-stat-trades').textContent = totalTrades.toLocaleString();
    document.getElementById('tb-stat-days').textContent = totalDays.toLocaleString();
    document.getElementById('tb-stat-profit-loss').textContent = `${totalProfitTrades}/${totalLossTrades}`;
    document.getElementById('tb-stat-commission').textContent = '¥' + totalCommission.toLocaleString(undefined, {maximumFractionDigits: 0});
    document.getElementById('tb-stats-period').textContent = `（共 ${count} 个区间平均）`;
}

/**
 * 更新单个区间统计
 */
function updateTbStatsForPeriod(summary) {
    if (!summary) {
        document.getElementById('tb-stat-return').textContent = '-';
        document.getElementById('tb-stat-winrate').textContent = '-';
        document.getElementById('tb-stat-drawdown').textContent = '-';
        document.getElementById('tb-stat-sharpe').textContent = '-';
        document.getElementById('tb-stat-trades').textContent = '-';
        document.getElementById('tb-stat-days').textContent = '-';
        document.getElementById('tb-stat-profit-loss').textContent = '-';
        document.getElementById('tb-stat-commission').textContent = '-';
        return;
    }

    const totalReturn = summary.total_return || 0;
    const winRate = summary.win_rate || 0;
    const maxDrawdown = summary.max_drawdown || 0;
    const sharpe = summary.sharpe_ratio || 0;
    const trades = summary.total_trades || 0;
    const days = summary.trading_days_count || 0;
    const profitTrades = summary.profit_trade_count || 0;
    const lossTrades = summary.loss_trade_count || 0;
    const commission = summary.total_commission || 0;

    document.getElementById('tb-stat-return').textContent = totalReturn.toFixed(2) + '%';
    document.getElementById('tb-stat-return').className = 'tb-stat-value ' + (totalReturn >= 0 ? 'negative' : 'positive');
    document.getElementById('tb-stat-winrate').textContent = winRate.toFixed(1) + '%';
    document.getElementById('tb-stat-drawdown').textContent = maxDrawdown.toFixed(2) + '%';
    document.getElementById('tb-stat-drawdown').className = 'tb-stat-value positive';
    document.getElementById('tb-stat-sharpe').textContent = sharpe.toFixed(2);
    document.getElementById('tb-stat-trades').textContent = trades.toLocaleString();
    document.getElementById('tb-stat-days').textContent = days.toLocaleString();
    document.getElementById('tb-stat-profit-loss').textContent = `${profitTrades}/${lossTrades}`;
    document.getElementById('tb-stat-commission').textContent = '¥' + commission.toLocaleString(undefined, {maximumFractionDigits: 0});
}

/**
 * 渲染回测区间列表
 */
function renderTbPeriods(data) {
    const container = document.getElementById('tb-periods-container');
    container.className = 'tb-periods-container';
    container.innerHTML = '';

    document.getElementById('tb-periods-count').textContent = `共 ${data.length} 个回测区间`;

    data.forEach(item => {
        const btn = document.createElement('div');
        btn.className = 'tb-period-btn';
        btn.dataset.startDate = item.backtest_start_date;
        btn.dataset.endDate = item.backtest_end_date;

        const summary = item.summary || {};
        const statsText = `交易: ${summary.total_trades || 0}次 | 收益: ${(summary.total_return || 0).toFixed(1)}%`;

        btn.innerHTML = `
            <div class="tb-period-date">${item.backtest_start_date} 至 ${item.backtest_end_date}</div>
            <div class="tb-period-stats">${statsText}</div>
        `;

        btn.addEventListener('click', function() {
            document.querySelectorAll('.tb-period-btn').forEach(el => el.classList.remove('active'));
            this.classList.add('active');
            loadTbPeriodDetail(item);
        });

        container.appendChild(btn);
    });
}

/**
 * 加载区间详情
 */
async function loadTbPeriodDetail(item) {
    currentTbPeriod = item;
    const startDate = item.backtest_start_date;
    const endDate = item.backtest_end_date;
    const strategy = item.strategy_name;

    // 更新区间信息
    document.getElementById('tb-chart-period').textContent = `（${startDate} 至 ${endDate}）`;
    document.getElementById('tb-stats-period').textContent = `（${startDate} 至 ${endDate}）`;

    // 更新统计
    updateTbStatsForPeriod(item.summary);

    // 加载策略参数
    await loadTbStrategyParams(strategy, startDate, endDate);

    // 加载收益图表
    await loadTbProfitChartData(strategy, startDate, endDate);

    // 加载每日记录
    await loadTbDailyRecords(strategy, startDate, endDate);
}

/**
 * 加载策略参数
 */
async function loadTbStrategyParams(strategy, startDate, endDate) {
    const container = document.getElementById('tb-params-container');

    try {
        const url = `/api/strategy_params?strategy=${encodeURIComponent(strategy)}&start_date=${startDate}&end_date=${endDate}`;
        const response = await fetch(url);
        const result = await response.json();

        if (result.success && result.data) {
            const data = result.data;
            const strategyParams = data.strategy_params || {};
            const backtestConfig = data.backtest_config || {};
            
            if (Object.keys(strategyParams).length === 0 && Object.keys(backtestConfig).length === 0) {
                Utils.showEmpty(container, 'tune', '该回测区间暂无策略参数');
            } else {
                container.innerHTML = renderTbParams(strategyParams, backtestConfig);
            }
        } else {
            Utils.showEmpty(container, 'tune', '暂无策略参数信息');
        }
    } catch (error) {
        Utils.showError(container, '加载策略参数失败: ' + error.message);
    }
}

/**
 * 渲染策略参数
 */
function renderTbParams(strategyParams, backtestConfig) {
    // 参数名称映射
    const paramNameMap = {
        'ma_period': '均线周期',
        'max_pe_ttm': '最大PE(TTM)',
        'max_pb_mrq': '最大PB(MRQ)',
        'buy_threshold': '买入阈值',
        'sell_threshold_up': '卖出阈值',
        'max_hold_days': '最大持仓天数',
        'take_profit': '止盈点',
        'stop_loss': '止损点',
        'trailing_stop_trigger': '移动止损触发',
        'trailing_stop_pct': '移动止损回撤',
        'trailing_stop_min_profit': '保底盈利',
        'printlog': '日志开关',
        'initial_cash': '初始资金',
        'commission': '手续费率',
        'slippage_perc': '滑点率',
        'max_positions': '最大持仓数',
        'position_size_pct': '仓位比例'
    };
    
    // 格式化参数值
    function formatValue(key, value) {
        if (value === null || value === undefined) return '-';
        if (typeof value === 'boolean') return value ? '开启' : '关闭';
        if (key === 'initial_cash') return value.toLocaleString() + ' 元';
        if (key === 'commission' || key === 'slippage_perc' || key === 'position_size_pct') {
            return (value * 100).toFixed(2) + '%';
        }
        if (key === 'buy_threshold' || key === 'sell_threshold_up' || 
            key === 'take_profit' || key === 'stop_loss' ||
            key === 'trailing_stop_trigger' || key === 'trailing_stop_pct' ||
            key === 'trailing_stop_min_profit') {
            return (value * 100).toFixed(1) + '%';
        }
        return value;
    }
    
    // 参数分组定义
    const paramGroups = {
        '基础参数': ['ma_period', 'max_pe_ttm', 'max_pb_mrq', 'buy_threshold', 'sell_threshold_up', 'max_hold_days'],
        '止盈止损': ['take_profit', 'stop_loss', 'trailing_stop_trigger', 'trailing_stop_pct', 'trailing_stop_min_profit'],
        '回测配置': ['initial_cash', 'commission', 'slippage_perc', 'max_positions', 'position_size_pct']
    };
    
    let html = '';
    
    // 渲染参数分组
    for (const [groupName, groupKeys] of Object.entries(paramGroups)) {
        const allParams = { ...strategyParams, ...backtestConfig };
        const groupParams = groupKeys.filter(key => allParams.hasOwnProperty(key) && key !== 'printlog');
        
        if (groupParams.length > 0) {
            html += `<div class="tb-params-group">
                <div class="tb-params-group-title">${groupName}</div>
                <div class="tb-params-grid">`;
            
            for (const key of groupParams) {
                const value = allParams[key];
                const displayName = paramNameMap[key] || key;
                const displayValue = formatValue(key, value);
                html += `
                    <div class="tb-param-item">
                        <span class="tb-param-label">${displayName}</span>
                        <span class="tb-param-value">${displayValue}</span>
                    </div>
                `;
            }
            
            html += `</div></div>`;
        }
    }
    
    return html || `<div class="empty-state"><span class="material-icons empty-state-icon">tune</span><div>该回测区间暂无策略参数</div></div>`;
}

/**
 * 加载收益图表数据
 */
async function loadTbProfitChartData(strategy, startDate, endDate) {
    if (!tbProfitChart) return;
    
    tbProfitChart.showLoading();

    try {
        const benchmarkInfo = benchmarkConfig[currentBenchmark];
        const url = `/api/profit_chart?strategy=${encodeURIComponent(strategy)}&start_date=${startDate}&end_date=${endDate}&benchmark=${currentBenchmark}`;
        const response = await fetch(url);
        const result = await response.json();

        tbProfitChart.hideLoading();

        if (result.success && result.data) {
            const data = result.data;
            const dates = data.dates || [];
            const strategyValues = data.strategy_values || [];
            const benchmarkValues = data.benchmark_values || [];
            const totalAssets = data.total_assets || [];
            const benchmarkPrices = data.benchmark_prices || [];

            const option = {
                tooltip: {
                    trigger: 'axis',
                    appendToBody: true,
                    formatter: function(params) {
                        let html = `<div style="font-weight:bold;margin-bottom:5px;">${params[0].axisValue}</div>`;
                        const dataIndex = params[0].dataIndex;
                        
                        params.forEach((p, idx) => {
                            if (p.seriesName === '策略收益') {
                                const assetVal = totalAssets[dataIndex] || 0;
                                html += `<div>${p.marker} 策略收益: ${p.value.toFixed(2)}%</div>`;
                                html += `<div style="padding-left:18px;color:#666;font-size:11px;">总资产: ¥${assetVal.toLocaleString()}</div>`;
                            } else {
                                const priceVal = benchmarkPrices[dataIndex] || 0;
                                html += `<div>${p.marker} ${p.seriesName}: ${p.value.toFixed(2)}%</div>`;
                                html += `<div style="padding-left:18px;color:#666;font-size:11px;">指数: ${priceVal.toFixed(2)}</div>`;
                            }
                        });
                        return html;
                    }
                },
                legend: {
                    data: ['策略收益', benchmarkInfo.name],
                    top: 5,
                    textStyle: { fontSize: 11 }
                },
                grid: {
                    left: '3%',
                    right: '4%',
                    bottom: '3%',
                    top: 35,
                    containLabel: true
                },
                xAxis: {
                    type: 'category',
                    data: dates,
                    boundaryGap: false,
                    axisLabel: { fontSize: 10 }
                },
                yAxis: {
                    type: 'value',
                    axisLabel: {
                        formatter: function(value) {
                            return value.toFixed(1) + '%';
                        },
                        fontSize: 10
                    }
                },
                series: [
                    {
                        name: '策略收益',
                        type: 'line',
                        data: strategyValues,
                        smooth: true,
                        lineStyle: { width: 2, color: '#1976d2' },
                        areaStyle: { color: 'rgba(25, 118, 210, 0.1)' }
                    },
                    {
                        name: benchmarkInfo.name,
                        type: 'line',
                        data: benchmarkValues,
                        smooth: true,
                        lineStyle: { width: 2, color: '#ff9800', type: 'dashed' }
                    }
                ]
            };

            tbProfitChart.setOption(option, true);
        } else {
            tbProfitChart.setOption({
                title: { text: '暂无收益数据', left: 'center', top: 'center', textStyle: { color: '#999', fontSize: 14 } }
            });
        }
    } catch (error) {
        tbProfitChart.hideLoading();
        tbProfitChart.setOption({
            title: { text: `错误: ${error.message}`, left: 'center', top: 'center', textStyle: { color: '#d32f2f', fontSize: 14 } }
        });
    }
}

/**
 * 加载每日记录
 */
async function loadTbDailyRecords(strategy, startDate, endDate) {
    const tbody = document.getElementById('tb-daily-body');
    tbody.innerHTML = `<tr><td colspan="8"><div class="loading"><span class="material-icons" style="animation: spin 1s linear infinite; font-size: 32px;">refresh</span><div style="margin-top: 8px;">加载中...</div></div></td></tr>`;

    try {
        const url = `/api/daily_records?strategy=${encodeURIComponent(strategy)}&start_date=${startDate}&end_date=${endDate}`;
        const response = await fetch(url);
        const result = await response.json();

        if (result.success && result.data && result.data.length > 0) {
            document.getElementById('tb-daily-count').textContent = `（共 ${result.data.length} 条记录）`;
            renderTbDailyTable(result.data);
        } else {
            tbody.innerHTML = `<tr><td colspan="8"><div class="empty-state"><span class="material-icons empty-state-icon">inbox</span><div>该回测区间暂无每日记录</div></div></td></tr>`;
            document.getElementById('tb-daily-count').textContent = '';
        }
    } catch (error) {
        tbody.innerHTML = `<tr><td colspan="8"><div class="error-message">网络错误: ${error.message}</div></td></tr>`;
    }
}

/**
 * 渲染每日记录表格
 */
function renderTbDailyTable(data) {
    const tbody = document.getElementById('tb-daily-body');
    tbody.innerHTML = '';

    data.forEach(item => {
        const row = document.createElement('tr');
        const profitRate = parseFloat(item.profit_rate || 0);
        const profitClass = profitRate > 0 ? 'positive' : profitRate < 0 ? 'negative' : '';

        // 解析持仓详情
        let positionHtml = '-';
        if (item.position_detail) {
            try {
                const positions = JSON.parse(item.position_detail);
                if (Array.isArray(positions) && positions.length > 0) {
                    positionHtml = positions.map(p => {
                        const profitRateVal = parseFloat(p.profit_rate || 0);
                        let cls = '';
                        if (profitRateVal > 0) cls = 'profit';
                        else if (profitRateVal < 0) cls = 'loss';
                        return `<span class="position-item ${cls}">${p.code || ''} (${profitRateVal >= 0 ? '+' : ''}${profitRateVal.toFixed(1)}%)</span>`;
                    }).join('');
                }
            } catch (e) {
                positionHtml = item.position_detail;
            }
        }

        row.innerHTML = `
            <td>${item.trade_date}</td>
            <td>${item.buy_count || 0}</td>
            <td>${item.sell_count || 0}</td>
            <td>¥${(item.total_asset || 0).toLocaleString()}</td>
            <td class="${profitClass}">${profitRate >= 0 ? '+' : ''}${profitRate.toFixed(2)}%</td>
            <td>¥${(item.cash || 0).toLocaleString()}</td>
            <td>${item.position_count || 0} / ${item.max_positions || 5}</td>
            <td class="position-detail-cell">${positionHtml}</td>
        `;
        tbody.appendChild(row);
    });
}

/**
 * 导出模块
 */
window.TimeBasedPanel = {
    init: initTimeBasedPanel,
    getCurrentPeriod: () => currentTbPeriod,
    getProfitChart: () => tbProfitChart,
    refresh: () => loadTbStrategies()
};
