/**
 * Kronos预测面板模块
 * 清华大模型股票预测功能
 */

let kronosChart = null;
let searchTimeout = null;

/**
 * 初始化Kronos预测面板
 */
function initKronosPanel() {
    initStockCodeAutocomplete();
    initPredictButton();
    initKronosChart();
}

/**
 * 初始化股票代码自动补全
 */
function initStockCodeAutocomplete() {
    const input = document.getElementById('kronos-stock-code');
    const suggestionsDiv = document.getElementById('kronos-suggestions');
    
    if (!input || !suggestionsDiv) return;
    
    // 输入事件处理
    input.addEventListener('input', function() {
        const keyword = this.value.trim();
        
        // 清除之前的定时器
        if (searchTimeout) {
            clearTimeout(searchTimeout);
        }
        
        // 隐藏建议列表
        if (!keyword) {
            suggestionsDiv.style.display = 'none';
            return;
        }
        
        // 延迟搜索（防抖）
        searchTimeout = setTimeout(() => {
            fetchSuggestions(keyword);
        }, 300);
    });
    
    // 失焦隐藏建议
    input.addEventListener('blur', function() {
        setTimeout(() => {
            suggestionsDiv.style.display = 'none';
        }, 200);
    });
    
    // 聚焦显示建议
    input.addEventListener('focus', function() {
        if (this.value.trim() && suggestionsDiv.children.length > 0) {
            suggestionsDiv.style.display = 'block';
        }
    });
}

/**
 * 获取联想建议
 */
async function fetchSuggestions(keyword) {
    const suggestionsDiv = document.getElementById('kronos-suggestions');
    
    try {
        const response = await fetch(`/api/stock_search?keyword=${encodeURIComponent(keyword)}`);
        const result = await response.json();
        
        if (result.success && result.data && result.data.length > 0) {
            renderSuggestions(result.data);
        } else {
            suggestionsDiv.style.display = 'none';
        }
    } catch (error) {
        console.error('搜索股票代码失败:', error);
        suggestionsDiv.style.display = 'none';
    }
}

/**
 * 渲染联想建议列表
 */
function renderSuggestions(suggestions) {
    const suggestionsDiv = document.getElementById('kronos-suggestions');
    suggestionsDiv.innerHTML = '';
    
    suggestions.forEach(item => {
        const div = document.createElement('div');
        div.className = 'autocomplete-item';
        div.textContent = item.display;
        div.addEventListener('click', () => {
            document.getElementById('kronos-stock-code').value = item.code;
            suggestionsDiv.style.display = 'none';
        });
        suggestionsDiv.appendChild(div);
    });
    
    suggestionsDiv.style.display = 'block';
}

/**
 * 初始化预测按钮
 */
function initPredictButton() {
    const btn = document.getElementById('kronos-predict-btn');
    if (!btn) return;
    
    btn.addEventListener('click', executePrediction);
}

/**
 * 执行预测
 */
async function executePrediction() {
    // 安全获取各参数值
    const stockCodeEl = document.getElementById('kronos-stock-code');
    const lookbackEl = document.getElementById('kronos-lookback');
    const predDaysEl = document.getElementById('kronos-pred-days');
    const temperatureEl = document.getElementById('kronos-temperature');
    const topPEl = document.getElementById('kronos-top-p');
    const sampleCountEl = document.getElementById('kronos-sample-count');
    
    // 检查元素是否存在
    if (!stockCodeEl || !lookbackEl || !predDaysEl || !temperatureEl || !topPEl || !sampleCountEl) {
        console.error('部分表单元素未找到');
        alert('页面初始化异常，请刷新页面重试');
        return;
    }
    
    const stockCode = stockCodeEl.value.trim();
    const lookbackDays = parseInt(lookbackEl.value) || 60;
    const predDays = parseInt(predDaysEl.value) || 5;
    const temperature = parseFloat(temperatureEl.value) || 0.5;
    const topP = parseFloat(topPEl.value) || 5;
    const sampleCount = parseInt(sampleCountEl.value) || 5;
    
    // 参数验证
    if (!stockCode) {
        alert('请输入证券代码');
        return;
    }
    
    // 显示加载状态
    const btn = document.getElementById('kronos-predict-btn');
    const status = document.getElementById('kronos-status');
    const statusText = document.getElementById('kronos-status-text');
    
    if (!btn || !status || !statusText) {
        console.error('状态元素未找到');
        return;
    }
    
    btn.disabled = true;
    status.style.display = 'flex';
    statusText.textContent = '正在预测...';
    
    try {
        const response = await fetch('/api/kronos_predict', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                stock_code: stockCode,
                lookback_days: lookbackDays,
                pred_days: predDays,
                temperature: temperature,
                top_p: topP,
                sample_count: sampleCount
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            console.log('📊 开始渲染图表...');
            renderKronosChart(result.data);
            console.log('📊 图表渲染完成，开始更新摘要...');
            updateSummary(result.data);
            console.log('📊 摘要更新完成');
        } else {
            alert('预测失败: ' + result.error);
        }
    } catch (error) {
        console.error('预测请求失败:', error);
        alert('预测请求失败: ' + error.message);
    } finally {
        btn.disabled = false;
        status.style.display = 'none';
    }
}

/**
 * 初始化K线图表
 */
function initKronosChart() {
    const chartDom = document.getElementById('kronos-kline-chart');
    if (!chartDom) {
        console.warn('K线图表容器未找到');
        return;
    }
    
    // 如果图表已存在，先销毁
    if (kronosChart) {
        kronosChart.dispose();
    }
    
    kronosChart = echarts.init(chartDom);
    kronosChart.setOption({
        title: { 
            text: '请输入证券代码并点击预测', 
            left: 'center', 
            top: 'center',
            textStyle: { color: '#999', fontSize: 16 }
        }
    });
    
    // 监听窗口大小变化
    window.addEventListener('resize', function() {
        if (kronosChart) {
            kronosChart.resize();
        }
    });
}

/**
 * 渲染K线预测图表
 */
function renderKronosChart(data) {
    // 调试：打印接收到的数据
    console.log('📊 接收到的数据:', data);
    console.log('📊 historical:', data.historical);
    console.log('📊 prediction:', data.prediction);
    
    // 确保图表已初始化
    if (!kronosChart) {
        const chartDom = document.getElementById('kronos-kline-chart');
        if (chartDom) {
            kronosChart = echarts.init(chartDom);
        } else {
            console.error('K线图表容器未找到');
            return;
        }
    }
    
    const historical = data.historical || [];
    const prediction = data.prediction || [];
    const predDays = data.pred_days || 5;
    
    console.log('📊 historical length:', historical.length);
    console.log('📊 prediction length:', prediction.length);
    
    // 合并历史和预测数据
    const allData = [...historical, ...prediction];
    console.log('📊 allData length:', allData.length);
    console.log('📊 allData sample:', allData.slice(0, 3));
    
    // 检查是否有 null 数据
    const nullItems = allData.filter(item => item === null || item === undefined);
    if (nullItems.length > 0) {
        console.error('❌ 发现 null 数据:', nullItems);
    }
    
    // 生成日期数组
    const dates = allData.map(item => item.date);
    
    // K线数据 [open, close, low, high]
    const values = allData.map(item => {
        if (!item) return [0, 0, 0, 0];
        return [item.open || 0, item.close || 0, item.low || 0, item.high || 0];
    });
    console.log('📊 values sample:', values.slice(0, 3));
    
    // 成交量数据
    const volumes = allData.map((item, index) => {
        if (!item) return { value: 0, itemStyle: { color: '#2e7d32' } };
        return {
            value: item.volume || 0,
            itemStyle: {
                color: values[index][1] >= values[index][0] ? '#d32f2f' : '#2e7d32'
            }
        };
    });
    console.log('📊 volumes sample:', volumes.slice(0, 3));
    
    // 预测分界线索引
    const boundaryIndex = historical.length - 1;
    console.log('📊 boundaryIndex:', boundaryIndex);
    console.log('📊 dates[boundaryIndex]:', dates[boundaryIndex]);
    
    // 构建图表配置
    console.log('📊 开始构建 ECharts 配置...');
    
    const option = {
        title: {
            text: `${data.stock_code} ${data.stock_name}`,
            left: 'center',
            top: 10,
            textStyle: { fontSize: 14, color: '#333' }
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'cross' },
            formatter: function(params) {
                const dataIndex = params[0].dataIndex;
                const item = allData[dataIndex];
                const isPred = item.isPrediction;
                const change = ((item.close - item.open) / item.open * 100).toFixed(2);
                const color = change >= 0 ? '#d32f2f' : '#2e7d32';
                
                return `<div style="font-weight:bold;margin-bottom:5px;">${item.date} ${isPred ? '<span style="color:#ff9800;">(预测)</span>' : ''}</div>
                    <div>开盘: ${item.open}</div><div>收盘: ${item.close}</div>
                    <div>最高: ${item.high}</div><div>最低: ${item.low}</div>
                    <div>涨跌: <span style="color:${color};font-weight:bold;">${change}%</span></div>
                    <div>成交量: ${(item.volume / 10000).toFixed(2)}万手</div>`;
            }
        },
        legend: {
            data: ['历史K线', '预测K线'],
            top: 35
        },
        grid: [
            { left: '10%', right: '8%', top: '15%', height: '50%' },
            { left: '10%', right: '8%', top: '72%', height: '18%' }
        ],
        xAxis: [
            { 
                type: 'category', 
                data: dates, 
                scale: true, 
                boundaryGap: false, 
                axisLine: { onZero: false }, 
                splitLine: { show: false },
                axisLabel: {
                    formatter: function(value, index) {
                        // 只显示部分日期标签
                        const total = dates.length;
                        if (index === 0 || index === total - 1 || index % Math.ceil(total / 10) === 0) {
                            return value;
                        }
                        return '';
                    }
                }
            },
            { 
                type: 'category', 
                gridIndex: 1, 
                data: dates, 
                scale: true, 
                boundaryGap: false, 
                axisLine: { onZero: false }, 
                axisTick: { show: false }, 
                splitLine: { show: false }, 
                axisLabel: { show: false } 
            }
        ],
        yAxis: [
            { scale: true, splitArea: { show: true } },
            { scale: true, gridIndex: 1, splitNumber: 2, axisLabel: { show: false }, axisLine: { show: false }, axisTick: { show: false }, splitLine: { show: false } }
        ],
        dataZoom: [
            { type: 'inside', xAxisIndex: [0, 1], start: Math.max(0, (1 - predDays * 3 / dates.length) * 100), end: 100 },
            { show: true, xAxisIndex: [0, 1], type: 'slider', top: '92%', start: Math.max(0, (1 - predDays * 3 / dates.length) * 100), end: 100 }
        ],
        series: [
            {
                name: '历史K线',
                type: 'candlestick',
                data: values.slice(0, historical.length),
                itemStyle: { 
                    color: '#d32f2f', 
                    color0: '#2e7d32', 
                    borderColor: '#d32f2f', 
                    borderColor0: '#2e7d32' 
                },
                markLine: {
                    silent: true,
                    symbol: 'none',
                    data: [{
                        xAxis: dates[boundaryIndex],
                        label: { position: 'end', formatter: '预测分界' },
                        lineStyle: { color: '#ff9800', type: 'dashed', width: 2 }
                    }]
                }
            },
            {
                name: '预测K线',
                type: 'candlestick',
                data: new Array(historical.length - 1).fill(null).concat(values.slice(boundaryIndex)),
                itemStyle: { 
                    color: '#ff9800', 
                    color0: '#ffa726', 
                    borderColor: '#ff9800', 
                    borderColor0: '#ffa726' 
                }
            },
            { 
                name: '成交量', 
                type: 'bar', 
                xAxisIndex: 1, 
                yAxisIndex: 1, 
                data: volumes 
            }
        ]
    };
    
    console.log('📊 ECharts 配置构建完成，准备渲染...');
    kronosChart.setOption(option, true);
    console.log('📊 ECharts 渲染完成');
    
    // 确保图表正确渲染
    setTimeout(() => {
        if (kronosChart) {
            kronosChart.resize();
        }
    }, 50);
    
    // 更新标题
    const chartTitleEl = document.getElementById('kronos-chart-title');
    if (chartTitleEl) {
        chartTitleEl.textContent = `${data.market}.${data.stock_code} ${data.stock_name}`;
    }
}

/**
 * 更新预测摘要
 */
function updateSummary(data) {
    console.log('📊 updateSummary 接收到的数据:', data);
    const summaryDiv = document.getElementById('kronos-summary');
    if (summaryDiv) {
        summaryDiv.style.display = 'block';
    }
    
    const lastCloseEl = document.getElementById('kronos-last-close');
    if (lastCloseEl) {
        lastCloseEl.textContent = '¥' + (data.last_close || 0).toFixed(2);
    }
    
    const changePctEl = document.getElementById('kronos-change-pct');
    if (changePctEl) {
        const changePct = data.pred_change_pct || 0;
        changePctEl.textContent = (changePct >= 0 ? '+' : '') + changePct.toFixed(2) + '%';
        changePctEl.className = 'kronos-stat-value ' + (changePct >= 0 ? 'positive' : 'negative');
    }
    
    const predDaysDisplayEl = document.getElementById('kronos-pred-days-display');
    if (predDaysDisplayEl) {
        predDaysDisplayEl.textContent = (data.pred_days || 0) + '天';
    }
    
    const histDaysEl = document.getElementById('kronos-hist-days');
    if (histDaysEl) {
        histDaysEl.textContent = (data.historical ? data.historical.length : 0) + '天';
    }
}

/**
 * 调整图表大小
 */
function resizeKronosChart() {
    if (kronosChart) {
        kronosChart.resize();
    }
}

/**
 * 重新初始化图表（用于Tab切换时）
 */
function reinitChart() {
    const chartDom = document.getElementById('kronos-kline-chart');
    if (chartDom) {
        if (kronosChart) {
            kronosChart.dispose();
        }
        kronosChart = echarts.init(chartDom);
        kronosChart.setOption({
            title: { 
                text: '请输入证券代码并点击预测', 
                left: 'center', 
                top: 'center',
                textStyle: { color: '#999', fontSize: 16 }
            }
        });
    }
}

/**
 * 导出模块
 */
window.KronosPanel = {
    init: initKronosPanel,
    resize: resizeKronosChart,
    reinitChart: reinitChart,
    getChart: () => kronosChart
};
