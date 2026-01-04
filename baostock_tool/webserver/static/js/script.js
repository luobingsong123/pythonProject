/**
 * K线图与指标展示系统 - 前端交互脚本
 * 主要功能：
 * 1. 加载和展示策略列表
 * 2. 渲染K线图和成交量
 * 3. 处理技术指标的选择和展示
 */

// 全局变量
let klineChart = null;
let currentStrategies = [];
let currentIndicators = [];
let selectedIndicators = new Set();
let currentKlineData = [];

// DOM加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

// 初始化应用
function initializeApp() {
    // 初始化当前时间显示
    updateCurrentTime();
    setInterval(updateCurrentTime, 1000);

    // 加载策略列表
    loadStrategies();

    // 加载K线数据
    loadKlineData();

    // 加载技术指标
    loadIndicators();

    // 绑定事件监听器
    bindEvents();

    // 初始化ECharts图表
    initChart();
}

// 更新当前时间显示
function updateCurrentTime() {
    const now = new Date();
    const timeString = now.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    });
    document.getElementById('current-time').textContent = timeString;
}

// 加载策略列表
function loadStrategies(searchQuery = '') {
    const url = searchQuery ?
        `/api/strategies?search=${encodeURIComponent(searchQuery)}` :
        '/api/strategies';

    fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                currentStrategies = data.data;
                renderStrategiesList(currentStrategies);
            } else {
                console.error('加载策略失败');
            }
        })
        .catch(error => {
            console.error('加载策略时出错:', error);
            showError('无法加载策略列表，请检查网络连接');
        });
}

// 渲染策略列表
function renderStrategiesList(strategies) {
    const strategiesList = document.getElementById('strategies-list');
    const strategyCount = document.getElementById('strategy-count');

    if (strategies.length === 0) {
        strategiesList.innerHTML = '<div class="loading">未找到匹配的策略</div>';
        strategyCount.textContent = '0';
        return;
    }

    let html = '';

    strategies.forEach(strategy => {
        const statusClass = strategy.status === 'active' ? 'status-active' : 'status-paused';
        const statusText = strategy.status === 'active' ? '运行中' : '已暂停';

        html += `
            <div class="strategy-item" data-id="${strategy.id}">
                <div class="strategy-name">${strategy.name}</div>
                <div class="strategy-description">${strategy.description}</div>
                <div class="strategy-meta">
                    <span class="strategy-status ${statusClass}">${statusText}</span>
                    <span class="strategy-date">创建: ${strategy.created_at}</span>
                </div>
            </div>
        `;
    });

    strategiesList.innerHTML = html;
    strategyCount.textContent = strategies.length;

    // 为每个策略项添加点击事件
    document.querySelectorAll('.strategy-item').forEach(item => {
        item.addEventListener('click', function() {
            // 移除其他项的active类
            document.querySelectorAll('.strategy-item').forEach(el => {
                el.classList.remove('active');
            });

            // 为当前项添加active类
            this.classList.add('active');

            // 这里可以添加策略选择的逻辑
            const strategyId = this.getAttribute('data-id');
            console.log('选择了策略:', strategyId);
        });
    });
}

// 加载K线数据
function loadKlineData() {
    const timeframeSelect = document.getElementById('timeframe-select');
    const days = timeframeSelect.value;

    fetch(`/api/kline-data?days=${days}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                currentKlineData = data.data;
                renderKlineChart(currentKlineData);
                updateDataInfo(currentKlineData);
            } else {
                console.error('加载K线数据失败');
            }
        })
        .catch(error => {
            console.error('加载K线数据时出错:', error);
            showError('无法加载K线数据，请检查网络连接');
        });
}

// 初始化ECharts图表
function initChart() {
    const chartDom = document.getElementById('kline-chart');
    klineChart = echarts.init(chartDom);

    // 窗口大小变化时重绘图表
    window.addEventListener('resize', function() {
        klineChart.resize();
    });
}

// 渲染K线图表
function renderKlineChart(klineData) {
    if (!klineChart || klineData.length === 0) return;

    // 准备K线数据
    const dates = klineData.map(item => item.time);
    const values = klineData.map(item => [item.open, item.close, item.low, item.high]);
    const volumes = klineData.map(item => item.volume);

    // 计算数据范围
    const prices = klineData.map(item => [item.low, item.high]).flat();
    const minPrice = Math.min(...prices) * 0.99;
    const maxPrice = Math.max(...prices) * 1.01;

    // 配置选项
    const option = {
        backgroundColor: '#fff',
        animation: true,
        legend: {
            top: 10,
            left: 'center',
            data: ['K线', '成交量', ...Array.from(selectedIndicators)]
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: {
                type: 'cross'
            },
            backgroundColor: 'rgba(255, 255, 255, 0.9)',
            borderWidth: 1,
            borderColor: '#ccc',
            textStyle: {
                color: '#333'
            },
            formatter: function(params) {
                let result = `<div style="font-weight: bold; margin-bottom: 5px;">${params[0].axisValue}</div>`;

                params.forEach(param => {
                    if (param.seriesType === 'candlestick') {
                        result += `
                            <div>开盘: ${param.data[1]}</div>
                            <div>收盘: ${param.data[2]}</div>
                            <div>最低: ${param.data[3]}</div>
                            <div>最高: ${param.data[4]}</div>
                        `;
                    } else if (param.seriesType === 'bar' && param.seriesName === '成交量') {
                        result += `<div>成交量: ${param.data}</div>`;
                    } else if (param.seriesType === 'line') {
                        result += `<div>${param.seriesName}: ${param.data}</div>`;
                    }
                });

                return result;
            }
        },
        axisPointer: {
            link: { xAxisIndex: 'all' },
            label: {
                backgroundColor: '#777'
            }
        },
        grid: [
            {
                left: '3%',
                right: '3%',
                top: '15%',
                height: '60%',
                containLabel: true
            },
            {
                left: '3%',
                right: '3%',
                top: '80%',
                height: '15%',
                containLabel: true
            }
        ],
        xAxis: [
            {
                type: 'category',
                data: dates,
                boundaryGap: false,
                axisLine: { onZero: false },
                splitLine: { show: true },
                splitNumber: 20,
                min: 'dataMin',
                max: 'dataMax',
                axisLabel: {
                    formatter: function(value) {
                        return echarts.format.formatTime('MM-dd', new Date(value));
                    }
                }
            },
            {
                type: 'category',
                gridIndex: 1,
                data: dates,
                axisLine: { onZero: false },
                axisTick: { show: false },
                splitLine: { show: false },
                axisLabel: { show: false },
                splitNumber: 20,
                min: 'dataMin',
                max: 'dataMax'
            }
        ],
        yAxis: [
            {
                scale: true,
                splitNumber: 5,
                axisLine: { show: true },
                splitLine: { show: true },
                axisLabel: {
                    formatter: '{value}'
                },
                min: minPrice,
                max: maxPrice
            },
            {
                scale: true,
                gridIndex: 1,
                splitNumber: 2,
                axisLabel: { show: false },
                axisLine: { show: false },
                axisTick: { show: false },
                splitLine: { show: false }
            }
        ],
        dataZoom: [
            {
                type: 'inside',
                xAxisIndex: [0, 1],
                start: 50,
                end: 100
            }
        ],
        series: [
            {
                name: 'K线',
                type: 'candlestick',
                data: values,
                itemStyle: {
                    color: '#ef232a',
                    color0: '#14b143',
                    borderColor: '#ef232a',
                    borderColor0: '#14b143'
                }
            },
            {
                name: '成交量',
                type: 'bar',
                xAxisIndex: 1,
                yAxisIndex: 1,
                data: volumes,
                itemStyle: {
                    color: function(params) {
                        const klineItem = klineData[params.dataIndex];
                        return klineItem.close >= klineItem.open ? '#14b143' : '#ef232a';
                    }
                }
            }
        ]
    };

    // 应用配置
    klineChart.setOption(option, true);
}

// 更新数据信息
function updateDataInfo(klineData) {
    if (klineData.length === 0) return;

    const firstDate = klineData[0].time;
    const lastDate = klineData[klineData.length - 1].time;
    const dataPoints = klineData.length;

    document.getElementById('data-range').textContent = `${firstDate} 至 ${lastDate}`;
    document.getElementById('data-points').textContent = dataPoints;
}

// 加载技术指标
function loadIndicators() {
    fetch('/api/indicators')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                currentIndicators = data.data;
                renderIndicatorsList(currentIndicators);
            } else {
                console.error('加载指标失败');
            }
        })
        .catch(error => {
            console.error('加载指标时出错:', error);
            showError('无法加载技术指标列表');
        });
}

// 渲染技术指标列表
function renderIndicatorsList(indicators) {
    const indicatorsList = document.getElementById('indicators-list');

    if (indicators.length === 0) {
        indicatorsList.innerHTML = '<div class="loading">暂无指标</div>';
        return;
    }

    let html = '';

    indicators.forEach(indicator => {
        const isActive = selectedIndicators.has(indicator.id);
        const activeClass = isActive ? 'active' : '';

        html += `
            <div class="indicator-item ${activeClass}" data-id="${indicator.id}">
                <input 
                    type="checkbox" 
                    class="indicator-checkbox" 
                    id="indicator-${indicator.id}"
                    ${isActive ? 'checked' : ''}
                >
                <div class="indicator-content">
                    <div class="indicator-name">${indicator.name}</div>
                    <div class="indicator-description">${indicator.description}</div>
                </div>
            </div>
        `;
    });

    indicatorsList.innerHTML = html;

    // 为每个指标项添加事件监听
    document.querySelectorAll('.indicator-item').forEach(item => {
        const checkbox = item.querySelector('.indicator-checkbox');
        const indicatorId = item.getAttribute('data-id');

        // 复选框点击事件
        checkbox.addEventListener('change', function() {
            toggleIndicator(indicatorId, this.checked);
        });

        // 整个项点击事件
        item.addEventListener('click', function(e) {
            if (e.target !== checkbox) {
                checkbox.checked = !checkbox.checked;
                toggleIndicator(indicatorId, checkbox.checked);
            }

            // 显示指标详情
            const indicator = currentIndicators.find(ind => ind.id === indicatorId);
            if (indicator) {
                document.getElementById('indicator-info').textContent =
                    `${indicator.name}: ${indicator.description}`;
            }
        });
    });

    // 更新激活的指标显示
    updateActiveIndicatorsDisplay();
}

// 切换指标显示
function toggleIndicator(indicatorId, isChecked) {
    if (isChecked) {
        selectedIndicators.add(indicatorId);
        loadIndicatorData(indicatorId);
    } else {
        selectedIndicators.delete(indicatorId);
        removeIndicatorFromChart(indicatorId);
    }

    // 更新指标项样式
    const indicatorItem = document.querySelector(`.indicator-item[data-id="${indicatorId}"]`);
    if (indicatorItem) {
        indicatorItem.classList.toggle('active', isChecked);
    }

    // 更新激活的指标显示
    updateActiveIndicatorsDisplay();
}

// 加载指标数据
function loadIndicatorData(indicatorId) {
    const timeframeSelect = document.getElementById('timeframe-select');
    const days = timeframeSelect.value;

    fetch(`/api/indicator-data/${indicatorId}?days=${days}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                addIndicatorToChart(indicatorId, data.data);
            } else {
                console.error(`加载指标 ${indicatorId} 数据失败`);
            }
        })
        .catch(error => {
            console.error(`加载指标 ${indicatorId} 数据时出错:`, error);
            showError(`无法加载指标 ${indicatorId} 的数据`);
        });
}

// 添加指标到图表
function addIndicatorToChart(indicatorId, indicatorData) {
    if (!klineChart || indicatorData.length === 0) return;

    const option = klineChart.getOption();
    const indicator = currentIndicators.find(ind => ind.id === indicatorId);

    if (!indicator) return;

    // 根据指标类型添加相应的系列
    if (indicatorId === 'boll') {
        // 布林带 - 三条线
        const dates = indicatorData.map(item => item.time);
        const upper = indicatorData.map(item => item.upper);
        const middle = indicatorData.map(item => item.middle);
        const lower = indicatorData.map(item => item.lower);

        option.series.push({
            name: '布林带上轨',
            type: 'line',
            data: upper.map((value, index) => [dates[index], value]),
            smooth: true,
            lineStyle: {
                width: 1,
                color: '#ff9800'
            },
            showSymbol: false
        }, {
            name: '布林带中轨',
            type: 'line',
            data: middle.map((value, index) => [dates[index], value]),
            smooth: true,
            lineStyle: {
                width: 1,
                color: '#2196f3'
            },
            showSymbol: false
        }, {
            name: '布林带下轨',
            type: 'line',
            data: lower.map((value, index) => [dates[index], value]),
            smooth: true,
            lineStyle: {
                width: 1,
                color: '#ff9800'
            },
            showSymbol: false
        });
    } else {
        // 其他指标 - 单条线
        const values = indicatorData.map(item => [item.time, item.value]);

        option.series.push({
            name: indicator.name,
            type: 'line',
            data: values,
            smooth: true,
            lineStyle: {
                width: 2
            },
            showSymbol: false
        });
    }

    // 更新图例
    option.legend.data = ['K线', '成交量', ...Array.from(selectedIndicators).map(id => {
        const ind = currentIndicators.find(i => i.id === id);
        return ind ? ind.name : id;
    })];

    klineChart.setOption(option);
}

// 从图表中移除指标
function removeIndicatorFromChart(indicatorId) {
    if (!klineChart) return;

    const option = klineChart.getOption();
    const indicator = currentIndicators.find(ind => ind.id === indicatorId);

    if (!indicator) return;

    // 移除对应的系列
    if (indicatorId === 'boll') {
        // 布林带有三个系列
        option.series = option.series.filter(series =>
            series.name !== '布林带上轨' &&
            series.name !== '布林带中轨' &&
            series.name !== '布林带下轨'
        );
    } else {
        // 其他指标只有一个系列
        option.series = option.series.filter(series => series.name !== indicator.name);
    }

    // 更新图例
    option.legend.data = ['K线', '成交量', ...Array.from(selectedIndicators).map(id => {
        const ind = currentIndicators.find(i => i.id === id);
        return ind ? ind.name : id;
    })];

    klineChart.setOption(option);
}

// 更新激活的指标显示
function updateActiveIndicatorsDisplay() {
    const activeIndicatorsEl = document.getElementById('active-indicators');

    if (selectedIndicators.size === 0) {
        activeIndicatorsEl.textContent = '无';
        return;
    }

    const indicatorNames = Array.from(selectedIndicators).map(id => {
        const indicator = currentIndicators.find(ind => ind.id === id);
        return indicator ? indicator.name : id;
    });

    activeIndicatorsEl.textContent = indicatorNames.join(', ');
}

// 绑定事件监听器
function bindEvents() {
    // 搜索功能
    const searchInput = document.getElementById('search-input');
    const searchButton = document.getElementById('search-button');

    // 搜索按钮点击事件
    searchButton.addEventListener('click', function() {
        loadStrategies(searchInput.value.trim());
    });

    // 搜索框回车事件
    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            loadStrategies(searchInput.value.trim());
        }
    });

    // 刷新策略列表按钮
    document.getElementById('refresh-strategies').addEventListener('click', function() {
        searchInput.value = '';
        loadStrategies();
    });

    // 时间周期选择
    document.getElementById('timeframe-select').addEventListener('change', function() {
        loadKlineData();

        // 重新加载已选择的指标
        selectedIndicators.forEach(indicatorId => {
            loadIndicatorData(indicatorId);
        });
    });

    // 清空指标按钮
    document.getElementById('clear-indicators').addEventListener('click', function() {
        // 清空所有选择的指标
        selectedIndicators.forEach(indicatorId => {
            const checkbox = document.getElementById(`indicator-${indicatorId}`);
            if (checkbox) {
                checkbox.checked = false;
            }

            const indicatorItem = document.querySelector(`.indicator-item[data-id="${indicatorId}"]`);
            if (indicatorItem) {
                indicatorItem.classList.remove('active');
            }

            removeIndicatorFromChart(indicatorId);
        });

        selectedIndicators.clear();
        updateActiveIndicatorsDisplay();
        document.getElementById('indicator-info').textContent = '已清空所有指标';
    });

    // 全屏按钮
    document.getElementById('fullscreen-btn').addEventListener('click', function() {
        const chartContainer = document.querySelector('.chart-container');

        if (!document.fullscreenElement) {
            if (chartContainer.requestFullscreen) {
                chartContainer.requestFullscreen();
            } else if (chartContainer.webkitRequestFullscreen) {
                chartContainer.webkitRequestFullscreen();
            } else if (chartContainer.msRequestFullscreen) {
                chartContainer.msRequestFullscreen();
            }
        } else {
            if (document.exitFullscreen) {
                document.exitFullscreen();
            } else if (document.webkitExitFullscreen) {
                document.webkitExitFullscreen();
            } else if (document.msExitFullscreen) {
                document.msExitFullscreen();
            }
        }
    });
}

// 显示错误信息
function showError(message) {
    // 这里可以添加更友好的错误提示
    console.error(message);
    alert(message);
}