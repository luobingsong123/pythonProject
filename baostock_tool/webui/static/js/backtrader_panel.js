/**
 * 遍历回测面板（Backtrader）
 */

let btCurrentPage = 1;
let btTotalPages = 1;
let btSearchStrategy = '';
let btSearchStockCode = '';
let currentStock = '';

/**
 * 初始化面板
 */
function initBacktraderPanel() {
    loadBtStrategies();

    document.getElementById('bt-search-btn').addEventListener('click', function() {
        btCurrentPage = 1;
        searchBtStocks();
    });

    document.getElementById('bt-stock-search').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            btCurrentPage = 1;
            searchBtStocks();
        }
    });

    // 分页按钮事件
    document.getElementById('bt-prev-page').addEventListener('click', function() {
        if (btCurrentPage > 1) {
            btCurrentPage--;
            loadBtStocksPage();
        }
    });

    document.getElementById('bt-next-page').addEventListener('click', function() {
        if (btCurrentPage < btTotalPages) {
            btCurrentPage++;
            loadBtStocksPage();
        }
    });
}

/**
 * 加载策略列表
 */
async function loadBtStrategies() {
    try {
        const response = await fetch('/api/strategies?backtest_framework=backtrader');
        const result = await response.json();

        if (result.success) {
            const select = document.getElementById('bt-strategy-select');
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
 * 搜索股票
 */
async function searchBtStocks() {
    const strategy = document.getElementById('bt-strategy-select').value;
    const stockCode = document.getElementById('bt-stock-search').value.trim();
    const container = document.getElementById('bt-stocks-list');

    if (!strategy) {
        Utils.showError(container, '请先选择策略');
        document.getElementById('bt-pagination').style.display = 'none';
        return;
    }

    // 保存搜索参数
    btSearchStrategy = strategy;
    btSearchStockCode = stockCode;

    Utils.showLoading(container, '加载中...');

    await loadBtStocksPage();
}

/**
 * 加载股票分页
 */
async function loadBtStocksPage() {
    const container = document.getElementById('bt-stocks-list');
    const pagination = document.getElementById('bt-pagination');

    Utils.showLoading(container, '加载中...');

    try {
        let url = `/api/stocks?strategy=${encodeURIComponent(btSearchStrategy)}&page=${btCurrentPage}&page_size=13`;
        if (btSearchStockCode) {
            url += `&stock_code=${encodeURIComponent(btSearchStockCode)}`;
        }

        const response = await fetch(url);
        const result = await response.json();

        if (result.success) {
            const paginationData = result.pagination;
            btTotalPages = paginationData.total_pages;

            if (result.data.length === 0) {
                Utils.showEmpty(container, 'search_off', '未找到相关股票');
                pagination.style.display = 'none';
            } else {
                renderBtStocksList(result.data);
                
                // 更新分页控件
                if (btTotalPages > 1) {
                    pagination.style.display = 'flex';
                    document.getElementById('bt-page-info').textContent = `${btCurrentPage}/${btTotalPages} (${paginationData.total}条)`;
                    document.getElementById('bt-prev-page').disabled = !paginationData.has_prev;
                    document.getElementById('bt-next-page').disabled = !paginationData.has_next;
                } else {
                    pagination.style.display = 'none';
                }
            }
        } else {
            Utils.showError(container, result.error);
            pagination.style.display = 'none';
        }
    } catch (error) {
        Utils.showError(container, '网络错误: ' + error.message);
        pagination.style.display = 'none';
    }
}

/**
 * 渲染股票列表
 */
function renderBtStocksList(stocks) {
    const container = document.getElementById('bt-stocks-list');
    container.innerHTML = '';

    stocks.forEach(stock => {
        const item = document.createElement('div');
        item.className = 'list-item';
        item.textContent = stock;
        item.addEventListener('click', function() {
            document.querySelectorAll('#bt-stocks-list .list-item').forEach(el => el.classList.remove('active'));
            this.classList.add('active');
            loadBtPeriods(stock);
        });
        container.appendChild(item);
    });
}

/**
 * 加载回测时段
 */
async function loadBtPeriods(stockCode) {
    currentStock = stockCode;
    const container = document.getElementById('bt-periods-list');
    const infoDiv = document.getElementById('bt-selected-stock');
    
    infoDiv.textContent = `当前: ${stockCode}`;
    Utils.showLoading(container, '加载中...');

    try {
        const strategy = document.getElementById('bt-strategy-select').value;
        const url = `/api/backtest_periods?strategy=${encodeURIComponent(strategy)}&stock_code=${encodeURIComponent(stockCode)}`;

        const response = await fetch(url);
        const result = await response.json();

        if (result.success) {
            if (result.data.length === 0) {
                Utils.showEmpty(container, 'event_busy', '该股票暂无回测记录');
            } else {
                await renderBtPeriodsList(result.data);
            }
        } else {
            Utils.showError(container, result.error);
        }
    } catch (error) {
        Utils.showError(container, '网络错误: ' + error.message);
    }
}

/**
 * 渲染回测时段列表
 */
async function renderBtPeriodsList(periods) {
    const container = document.getElementById('bt-periods-list');
    container.innerHTML = '';

    const strategy = document.getElementById('bt-strategy-select').value;

    for (const period of periods) {
        const triggerList = document.createElement('div');
        triggerList.className = 'trigger-list';
        triggerList.id = `triggers-${period.replace(/[^a-zA-Z0-9]/g, '-')}`;

        const stats = await loadBtPeriodStats(period, triggerList);

        const periodItem = document.createElement('div');
        periodItem.className = 'period-item';

        const statsHtml = stats.total > 0
            ? `<div class="period-stats">盈:${stats.profit} 亏:${stats.loss} 平:${stats.flat} | 盈利率: ${stats.winRate}%</div>`
            : '';

        periodItem.innerHTML = `
            <div>${period}</div>
            ${statsHtml}
        `;

        periodItem.addEventListener('click', function() {
            const isExpanded = triggerList.classList.contains('show');
            
            container.querySelectorAll('.trigger-list').forEach(el => el.classList.remove('show'));
            container.querySelectorAll('.period-item').forEach(el => el.classList.remove('expanded'));

            if (!isExpanded) {
                periodItem.classList.add('expanded');
                triggerList.classList.add('show');
            }
        });

        container.appendChild(periodItem);
        container.appendChild(triggerList);
    }
}

/**
 * 加载时段统计
 */
async function loadBtPeriodStats(period, triggerContainer) {
    try {
        const strategy = document.getElementById('bt-strategy-select').value;
        const url = `/api/trigger_points?strategy=${encodeURIComponent(strategy)}&stock_code=${encodeURIComponent(currentStock)}&backtest_period=${encodeURIComponent(period)}`;

        const response = await fetch(url);
        const result = await response.json();

        if (result.success && result.data.length > 0) {
            renderBtTriggerPoints(result.data, triggerContainer);

            let profit = 0, loss = 0, flat = 0;
            result.data.forEach(point => {
                if (point.profit_flag === 1) profit++;
                else if (point.profit_flag === -1) loss++;
                else flat++;
            });

            const total = profit + loss + flat;
            const winRate = total > 0 ? ((profit / total) * 100).toFixed(1) : 0;

            return { total, profit, loss, flat, winRate };
        } else {
            Utils.showEmpty(triggerContainer, '', '暂无触发点位');
            return { total: 0, profit: 0, loss: 0, flat: 0, winRate: 0 };
        }
    } catch (error) {
        Utils.showError(triggerContainer, error.message);
        return { total: 0, profit: 0, loss: 0, flat: 0, winRate: 0 };
    }
}

/**
 * 渲染触发点位
 */
function renderBtTriggerPoints(points, container) {
    container.innerHTML = '';

    points.forEach(point => {
        const item = document.createElement('div');
        item.className = 'trigger-item';

        let badgeClass = 'badge-flat', badgeText = '平';
        if (point.profit_flag === 1) { badgeClass = 'badge-profit'; badgeText = '盈'; }
        else if (point.profit_flag === -1) { badgeClass = 'badge-loss'; badgeText = '亏'; }

        const buyPriceText = point.buy_price ? `¥${point.buy_price.toFixed(2)}` : '';
        const sellPriceText = point.sell_price ? `→ ¥${point.sell_price.toFixed(2)}` : '';
        let percentText = '';
        if (point.buy_price && point.sell_price) {
            const percent = ((point.sell_price - point.buy_price) / point.buy_price * 100).toFixed(2);
            percentText = ` (${percent >= 0 ? '+' : ''}${percent}%)`;
        }

        item.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span class="trigger-date">买入: ${point.buy_date}</span>
                <span class="badge ${badgeClass}">${badgeText}</span>
            </div>
            ${buyPriceText ? `<div class="trigger-price">${buyPriceText} ${sellPriceText}${percentText}</div>` : ''}
        `;

        item.addEventListener('click', function() {
            container.querySelectorAll('.trigger-item').forEach(el => el.classList.remove('active'));
            this.classList.add('active');
            
            // 触发 K 线图加载事件
            document.dispatchEvent(new CustomEvent('loadKline', { 
                detail: {
                    stockCode: currentStock,
                    buyDate: point.buy_date,
                    sellDate: point.sell_date,
                    buyPrice: point.buy_price,
                    sellPrice: point.sell_price
                }
            }));
        });

        container.appendChild(item);
    });
}

/**
 * 导出模块
 */
window.BacktraderPanel = {
    init: initBacktraderPanel,
    getCurrentStock: () => currentStock,
    refresh: () => loadBtStrategies()
};
