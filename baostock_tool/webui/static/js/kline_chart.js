/**
 * K线图模块
 */

let klineChart = null;

/**
 * 初始化 K 线图
 */
function initKlineChart() {
    const chartDom = document.getElementById('bt-kline-chart');
    if (!chartDom) return;
    
    klineChart = echarts.init(chartDom);
    klineChart.setOption({
        title: { text: '暂无数据', left: 'center', top: 'center', textStyle: { color: '#999', fontSize: 16 } }
    });

    // 监听窗口大小变化
    window.addEventListener('resize', function() {
        if (klineChart) {
            klineChart.resize();
        }
    });
}

/**
 * 加载 K 线数据
 */
async function loadKlineData(stockCode, buyDate, sellDate = null, buyPrice = 0, sellPrice = 0) {
    if (!klineChart) return;
    
    klineChart.showLoading();

    try {
        let url = `/api/kline_data?stock_code=${encodeURIComponent(stockCode)}&start_date=${encodeURIComponent(buyDate)}`;
        if (sellDate) {
            url += `&sell_date=${encodeURIComponent(sellDate)}`;
        }

        const response = await fetch(url);
        const result = await response.json();

        klineChart.hideLoading();

        if (result.success && result.data && result.data.length > 0) {
            let infoText = `买入: ${buyDate}`;
            if (buyPrice > 0) infoText += ` (¥${buyPrice.toFixed(2)})`;
            if (sellDate) {
                infoText += ` | 卖出: ${sellDate}`;
                if (sellPrice > 0) infoText += ` (¥${sellPrice.toFixed(2)})`;
            }
            infoText += ` | 数据: ${result.data[0].date} 至 ${result.data[result.data.length - 1].date}`;
            document.getElementById('bt-chart-info').textContent = infoText;

            renderKlineChart(result.data, buyDate, sellDate, buyPrice, sellPrice);
        } else {
            klineChart.setOption({
                title: { text: '暂无K线数据', left: 'center', top: 'center', textStyle: { color: '#999' } }
            });
        }
    } catch (error) {
        klineChart.hideLoading();
        klineChart.setOption({
            title: { text: `错误: ${error.message}`, left: 'center', top: 'center', textStyle: { color: '#d32f2f' } }
        });
    }
}

/**
 * 渲染 K 线图
 */
function renderKlineChart(data, buyDate, sellDate, buyPrice, sellPrice) {
    if (!klineChart) return;
    
    const dates = data.map(item => item.date);
    const values = data.map(item => [item.open, item.close, item.low, item.high]);
    
    // 成交量数据：包含值和颜色配置
    const volumes = data.map((item, index) => ({
        value: item.volume,
        itemStyle: {
            color: values[index][1] >= values[index][0] ? '#d32f2f' : '#2e7d32'
        }
    }));

    const buyIndex = dates.indexOf(buyDate);
    const sellIndex = sellDate ? dates.indexOf(sellDate) : -1;

    const markPointData = [];
    if (buyIndex !== -1) {
        const buyLow = values[buyIndex][2];
        const buyLabel = buyPrice > 0 ? `¥${buyPrice.toFixed(2)}` : '买入';
        markPointData.push({
            name: '买入', coord: [buyDate, buyLow], value: buyLabel,
            symbol: 'triangle', symbolSize: 20, symbolOffset: [0, 15],
            itemStyle: { color: '#d32f2f' },
            label: { show: true, position: 'bottom', color: '#d32f2f', fontSize: 12, fontWeight: 'bold' }
        });
    }

    if (sellDate && sellIndex !== -1) {
        const sellHigh = values[sellIndex][3];
        const sellLabel = sellPrice > 0 ? `¥${sellPrice.toFixed(2)}` : '卖出';
        markPointData.push({
            name: '卖出', coord: [sellDate, sellHigh], value: sellLabel,
            symbol: 'triangle', symbolSize: 20, symbolOffset: [0, -15], symbolRotate: 180,
            itemStyle: { color: '#2e7d32' },
            label: { show: true, position: 'top', color: '#2e7d32', fontSize: 12, fontWeight: 'bold' }
        });
    }

    const option = {
        tooltip: {
            trigger: 'axis', axisPointer: { type: 'cross' },
            formatter: function(params) {
                const item = data[params[0].dataIndex];
                const change = ((item.close - item.open) / item.open * 100).toFixed(2);
                const color = change >= 0 ? '#d32f2f' : '#2e7d32';
                return `<div style="font-weight:bold;margin-bottom:5px;">${item.date}</div>
                    <div>开盘: ${item.open}</div><div>收盘: ${item.close}</div>
                    <div>最高: ${item.high}</div><div>最低: ${item.low}</div>
                    <div>涨跌: <span style="color:${color};font-weight:bold;">${change}%</span></div>
                    <div>成交量: ${(item.volume / 10000).toFixed(2)}万手</div>`;
            }
        },
        grid: [
            { left: '10%', right: '8%', top: '10%', height: '55%' },
            { left: '10%', right: '8%', top: '72%', height: '18%' }
        ],
        xAxis: [
            { type: 'category', data: dates, scale: true, boundaryGap: false, axisLine: { onZero: false }, splitLine: { show: false } },
            { type: 'category', gridIndex: 1, data: dates, scale: true, boundaryGap: false, axisLine: { onZero: false }, axisTick: { show: false }, splitLine: { show: false }, axisLabel: { show: false } }
        ],
        yAxis: [
            { scale: true, splitArea: { show: true } },
            { scale: true, gridIndex: 1, splitNumber: 2, axisLabel: { show: false }, axisLine: { show: false }, axisTick: { show: false }, splitLine: { show: false } }
        ],
        dataZoom: [
            { type: 'inside', xAxisIndex: [0, 1], start: 0, end: 100 },
            { show: true, xAxisIndex: [0, 1], type: 'slider', top: '92%', start: 0, end: 100 }
        ],
        series: [
            { name: 'K线', type: 'candlestick', data: values, markPoint: { data: markPointData },
              itemStyle: { color: '#d32f2f', color0: '#2e7d32', borderColor: '#d32f2f', borderColor0: '#2e7d32' } },
            { name: '成交量', type: 'bar', xAxisIndex: 1, yAxisIndex: 1, data: volumes }
        ]
    };

    klineChart.setOption(option, true);
    
    // 确保 K 线图正确渲染（解决隐藏容器初始化问题）
    setTimeout(() => {
        klineChart.resize();
    }, 50);
}

/**
 * 调整图表大小
 */
function resizeKlineChart() {
    if (klineChart) {
        klineChart.resize();
    }
}

/**
 * 导出模块
 */
window.KlineChart = {
    init: initKlineChart,
    load: loadKlineData,
    resize: resizeKlineChart,
    getChart: () => klineChart
};
