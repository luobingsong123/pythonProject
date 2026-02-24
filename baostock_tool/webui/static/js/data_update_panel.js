/**
 * 数据更新面板
 */

/**
 * 初始化面板
 */
function initDataUpdatePanel() {
    document.getElementById('update-data-btn').addEventListener('click', startDataUpdate);
}

/**
 * 开始数据更新
 */
async function startDataUpdate() {
    const btn = document.getElementById('update-data-btn');
    const statusDiv = document.getElementById('update-status');
    const statusText = document.getElementById('update-status-text');
    const resultDiv = document.getElementById('update-result');
    const logDiv = document.getElementById('update-log');

    // 禁用按钮，显示状态
    btn.disabled = true;
    statusDiv.style.display = 'flex';
    resultDiv.style.display = 'none';
    statusText.textContent = '正在连接服务器...';

    try {
        const response = await fetch('/api/update_market_data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let result = '';

        statusText.textContent = '正在更新数据...';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            result += chunk;

            // 更新日志显示
            resultDiv.style.display = 'block';
            logDiv.textContent = result;
            logDiv.scrollTop = logDiv.scrollHeight;
        }

        statusDiv.style.display = 'none';
        btn.disabled = false;

        // 显示完成状态
        resultDiv.style.display = 'block';
        if (result.includes('成功') || result.includes('完成')) {
            logDiv.innerHTML = result + '\n\n<span style="color: #2e7d32; font-weight: bold;">✓ 数据更新完成</span>';
        } else {
            logDiv.innerHTML = result + '\n\n<span style="color: #d32f2f; font-weight: bold;">✗ 数据更新可能存在问题，请检查日志</span>';
        }

    } catch (error) {
        statusDiv.style.display = 'none';
        btn.disabled = false;
        resultDiv.style.display = 'block';
        logDiv.innerHTML = `<span style="color: #d32f2f; font-weight: bold;">网络错误: ${error.message}</span>`;
    }
}

/**
 * 导出模块
 */
window.DataUpdatePanel = {
    init: initDataUpdatePanel
};
