# K线图与指标展示系统

一个基于Flask的Web应用，用于展示K线图、技术指标和量化策略管理。该应用提供了一个直观的三区域界面，左侧显示策略列表，中间展示K线图和成交量，右侧提供技术指标选择功能。

!https://via.placeholder.com/800x450/1a2332/ffffff?text=K线图与指标展示系统

## 功能特性

### 1. 策略管理
- 策略列表展示，包含名称、描述、状态和创建时间
- 策略搜索功能
- 按状态分类显示（运行中/已暂停）

### 2. K线图展示
- 完整的K线图（蜡烛图）展示
- 成交量柱状图
- 时间周期选择（30/60/100/200天）
- 图表缩放和拖拽功能
- 鼠标悬停显示详细数据

### 3. 技术指标叠加
- 支持8种常用技术指标：
  - 移动平均线（MA）
  - 指数移动平均线（EMA）
  - 移动平均收敛/发散指标（MACD）
  - 布林带（BOLL）
  - 随机指标（KDJ）
  - 相对强弱指数（RSI）
  - 成交量指标
  - 平均真实波幅（ATR）
- 多指标同时叠加显示
- 一键清空所有指标

### 4. 用户界面
- 现代化响应式设计
- 三区域布局（左侧列表、中间图表、右侧指标）
- 暗色主题界面
- 全屏模式支持
- 实时时间显示

## 技术栈

### 后端
- **Flask** - Python Web框架
- **ECharts** - 数据可视化库
- **JSON** - 数据交换格式

### 前端
- **HTML5/CSS3** - 页面结构和样式
- **JavaScript (ES6+)** - 交互逻辑
- **ECharts.js** - 图表渲染
- **Fetch API** - 异步数据请求

## 快速开始

### 环境要求
- Python 3.7+
- pip（Python包管理器）

### 安装步骤

1. 克隆或下载项目文件
```bash
git clone <项目地址>
cd flask-kline-app
```

2. 创建项目目录结构
```bash
mkdir -p templates static/css static/js
```

3. 将代码文件放入对应目录
- 将`app.py`放在项目根目录
- 将`index.html`放在`templates`目录
- 将`style.css`放在`static/css`目录
- 将`script.js`放在`static/js`目录

4. 安装Flask
```bash
pip install flask
```

5. 运行应用
```bash
python app.py
```

6. 访问应用
在浏览器中打开：`http://localhost:5000`

## 项目结构

```
flask-kline-app/
├── app.py                 # Flask主应用
├── requirements.txt       # Python依赖包
├── templates/
│   └── index.html        # 主页面模板
├── static/
│   ├── css/
│   │   └── style.css     # 样式文件
│   └── js/
│       └── script.js     # 前端交互脚本
├── data/                  # 数据目录（可选）
└── README.md             # 项目说明文档
```

## API接口说明

### 1. 获取策略列表
- **端点**: `GET /api/strategies`
- **参数**: 
  - `search` (可选): 搜索关键词
- **响应**: 
  ```json
  {
    "success": true,
    "data": [
      {
        "id": 1,
        "name": "策略名称",
        "description": "策略描述",
        "status": "active",
        "created_at": "2024-01-15"
      }
    ],
    "total": 8
  }
  ```

### 2. 获取K线数据
- **端点**: `GET /api/kline-data`
- **参数**: 
  - `days` (可选): 数据天数，默认100
- **响应**: 
  ```json
  {
    "success": true,
    "data": [
      {
        "time": "2024-01-01",
        "open": 100.00,
        "high": 105.00,
        "low": 99.50,
        "close": 102.50,
        "volume": 25000
      }
    ]
  }
  ```

### 3. 获取技术指标列表
- **端点**: `GET /api/indicators`
- **响应**: 
  ```json
  {
    "success": true,
    "data": [
      {
        "id": "ma",
        "name": "移动平均线(MA)",
        "description": "简单移动平均线"
      }
    ]
  }
  ```

### 4. 获取指标数据
- **端点**: `GET /api/indicator-data/<indicator_id>`
- **参数**: 
  - `days` (可选): 数据天数，默认100
- **响应**: 
  ```json
  {
    "success": true,
    "indicator_id": "ma",
    "data": [
      {
        "time": "2024-01-01",
        "value": 101.25
      }
    ]
  }
  ```

## 配置说明

### 模拟数据
应用默认使用模拟数据生成K线图。要使用真实数据，可以：

1. 修改`app.py`中的`generate_kline_data`函数
2. 连接真实数据源（数据库、API等）
3. 更新相关API端点以返回真实数据

### 策略数据
默认策略数据存储在`STRATEGIES`列表中。要使用真实策略数据，可以：

1. 连接数据库获取策略信息
2. 修改`/api/strategies`端点逻辑
3. 添加策略创建、编辑、删除功能

## 部署指南

### 开发环境
```bash
python app.py
```

### 生产环境
1. 使用Gunicorn或uWSGI作为WSGI服务器
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

2. 配置Nginx作为反向代理
```nginx
server {
    listen 80;
    server_name your_domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

3. 设置系统服务（使用systemd）
```bash
sudo nano /etc/systemd/system/kline-app.service
```

```ini
[Unit]
Description=K线图应用
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/flask-kline-app
ExecStart=/usr/local/bin/gunicorn -w 4 -b 127.0.0.1:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

## 使用说明

### 1. 查看策略
- 左侧面板显示所有可用策略
- 点击策略可选中查看
- 使用搜索框按名称过滤策略

### 2. 查看K线图
- 主区域显示K线图和成交量
- 使用鼠标滚轮缩放图表
- 拖拽图表区域查看历史数据
- 选择时间周期切换数据范围

### 3. 添加技术指标
- 右侧面板显示可用技术指标
- 点击指标名称或复选框添加指标
- 指标会实时叠加到K线图上
- 点击"清空"按钮移除所有指标

### 4. 交互功能
- **鼠标悬停**: 查看K线详细信息
- **图表缩放**: 鼠标滚轮或拖拽选择区域
- **全屏模式**: 点击右上角全屏按钮
- **时间周期**: 下拉菜单切换数据天数

## 自定义和扩展

### 添加新的技术指标
1. 在`app.py`的`TECHNICAL_INDICATORS`列表中添加新指标
```python
TECHNICAL_INDICATORS.append({
    "id": "new_indicator",
    "name": "新指标",
    "description": "指标描述"
})
```

2. 在`get_indicator_data`函数中添加数据处理逻辑
3. 在`addIndicatorToChart`函数（script.js）中添加图表渲染逻辑

### 修改样式
- 主样式文件: `static/css/style.css`
- 主要颜色变量在文件顶部定义
- 响应式断点：1200px, 992px

### 添加新功能
- 策略详情页面
- 数据导出功能
- 多图表对比
- 用户登录和权限管理
- 实时数据更新

## 故障排除

### 常见问题

1. **应用无法启动**
   - 检查Python版本（需要3.7+）
   - 确保Flask已正确安装
   - 检查端口5000是否被占用

2. **图表不显示**
   - 检查浏览器控制台错误
   - 确保ECharts库正确加载
   - 验证API端点返回正确数据格式

3. **样式错乱**
   - 清除浏览器缓存
   - 检查CSS文件路径
   - 验证HTML结构完整性

4. **数据加载失败**
   - 检查网络连接
   - 查看Flask控制台输出
   - 验证API端点URL

### 调试模式
启动应用时启用调试模式查看详细错误：
```bash
export FLASK_ENV=development
python app.py
```

## 性能优化建议

1. **数据缓存**: 对频繁请求的数据添加缓存
2. **分页加载**: 大量数据时分页加载
3. **图表优化**: 减少初始渲染数据点数量
4. **CDN加速**: 使用CDN加载ECharts等静态资源
5. **数据库连接池**: 使用连接池管理数据库连接

## 安全注意事项

1. **生产环境配置**
   - 禁用调试模式
   - 设置强密钥
   - 使用HTTPS

2. **API安全**
   - 添加API请求频率限制
   - 实现用户认证和授权
   - 验证输入参数

3. **数据安全**
   - 不要暴露敏感数据
   - 对用户输入进行过滤
   - 使用参数化查询防止SQL注入

## 浏览器兼容性

- Chrome 60+
- Firefox 55+
- Safari 11+
- Edge 79+

## 许可证

本项目采用MIT许可证。有关详细信息，请参阅LICENSE文件。

## 贡献指南

1. Fork本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 开启Pull Request

## 联系方式

如有问题或建议，请通过以下方式联系：

- 创建GitHub Issue
- 发送邮件至 [your-email@example.com]

## 更新日志

### v1.0.0 (2024-01-01)
- 初始版本发布
- 基础K线图展示
- 8种技术指标支持
- 策略列表管理
- 响应式设计

---

## 免责声明

本应用提供的所有数据均为模拟数据，仅用于演示和学习目的。不构成任何投资建议。在实际使用中，请确保遵守相关法律法规，并连接真实、合法的数据源。