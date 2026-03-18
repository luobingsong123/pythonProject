-- ========================================================
-- 选股结果数据表设计
-- ========================================================

-- --------------------------------------------------------
-- 表: stock_selection_result
-- 用途: 存储每日选股结果的主表
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS `stock_selection_result` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '自增主键ID',
    `batch_id` VARCHAR(64) NOT NULL COMMENT '选股批次ID，格式: SELECT_YYYYMMDD_NNN',
    `strategy_id` VARCHAR(64) NOT NULL COMMENT '选股策略ID',
    `strategy_name` VARCHAR(128) DEFAULT NULL COMMENT '策略名称',
    `version` VARCHAR(10) NOT NULL DEFAULT '1.0' COMMENT '数据版本',
    `trade_date` DATE NOT NULL COMMENT '交易日期',
    `total_count` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '本次选股总数',
    `market_filter` VARCHAR(10) DEFAULT NULL COMMENT '市场过滤条件(sh/sz/null)',
    `strategy_params` JSON DEFAULT NULL COMMENT '策略参数JSON',
    `selection_time` DATETIME(3) DEFAULT NULL COMMENT '选股时间',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_batch_id` (`batch_id`),
    KEY `idx_trade_date` (`trade_date`),
    KEY `idx_strategy_id` (`strategy_id`),
    KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='选股结果主表';


-- --------------------------------------------------------
-- 表: stock_selection_detail
-- 用途: 存储选股结果中每只个股的详细信息
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS `stock_selection_detail` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '自增主键ID',
    `batch_id` VARCHAR(64) NOT NULL COMMENT '选股批次ID',
    `trade_date` DATE NOT NULL COMMENT '交易日期',
    `symbol` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `exchange` VARCHAR(10) NOT NULL COMMENT '交易所代码(SSE/SZSE)',
    `market` VARCHAR(2) NOT NULL COMMENT '市场代码(sh/sz)',
    `code_int` INT UNSIGNED NOT NULL COMMENT '数字股票代码',
    `name` VARCHAR(100) NOT NULL COMMENT '股票名称',
    `sort_order` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '排序序号',
    
    -- 基本信息
    `prev_close` DECIMAL(12,4) DEFAULT NULL COMMENT '昨收价',
    `ma5` DECIMAL(12,4) DEFAULT NULL COMMENT '5日均线',
    `ma10` DECIMAL(12,4) DEFAULT NULL COMMENT '10日均线',
    `ma20` DECIMAL(12,4) DEFAULT NULL COMMENT '20日均线',
    `ma60` DECIMAL(12,4) DEFAULT NULL COMMENT '60日均线',
    `ma5_high` DECIMAL(12,4) DEFAULT NULL COMMENT '近5日最高价',
    `volume_ratio` DECIMAL(8,4) DEFAULT NULL COMMENT '量比',
    `turnover_rate` DECIMAL(8,4) DEFAULT NULL COMMENT '换手率(%)',
    
    -- 技术指标
    `vol_ma5` BIGINT DEFAULT NULL COMMENT '5日均量',
    `vol_ma10` BIGINT DEFAULT NULL COMMENT '10日均量',
    `vol_ma20` BIGINT DEFAULT NULL COMMENT '20日均量',
    
    -- 基本面数据
    `pe` DECIMAL(8,2) DEFAULT NULL COMMENT '市盈率',
    `pb` DECIMAL(8,2) DEFAULT NULL COMMENT '市净率',
    `market_cap` DECIMAL(15,2) DEFAULT NULL COMMENT '市值（百万）',
    
    -- 策略信号
    `strategy_score` DECIMAL(10,4) DEFAULT NULL COMMENT '策略得分',
    `strategy_signals` JSON DEFAULT NULL COMMENT '策略信号JSON',
    
    -- 分钟成交量数据（5天）
    `minute_volume_5d_01` JSON DEFAULT NULL COMMENT '第1天每5分钟成交量',
    `minute_volume_5d_02` JSON DEFAULT NULL COMMENT '第2天每5分钟成交量',
    `minute_volume_5d_03` JSON DEFAULT NULL COMMENT '第3天每5分钟成交量',
    `minute_volume_5d_04` JSON DEFAULT NULL COMMENT '第4天每5分钟成交量',
    `minute_volume_5d_05` JSON DEFAULT NULL COMMENT '第5天每5分钟成交量',
    
    -- 当日行情数据
    `open_price` DECIMAL(12,4) DEFAULT NULL COMMENT '开盘价',
    `high_price` DECIMAL(12,4) DEFAULT NULL COMMENT '最高价',
    `low_price` DECIMAL(12,4) DEFAULT NULL COMMENT '最低价',
    `close_price` DECIMAL(12,4) DEFAULT NULL COMMENT '收盘价',
    `volume` BIGINT DEFAULT NULL COMMENT '成交量',
    `amount` DECIMAL(17,2) DEFAULT NULL COMMENT '成交额',
    `pct_chg` DECIMAL(8,4) DEFAULT NULL COMMENT '涨跌幅(%)',
    
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_batch_symbol` (`batch_id`, `symbol`),
    KEY `idx_batch_id` (`batch_id`),
    KEY `idx_trade_date` (`trade_date`),
    KEY `idx_symbol` (`symbol`),
    KEY `idx_exchange_symbol` (`exchange`, `symbol`),
    KEY `idx_market_code` (`market`, `code_int`),
    KEY `idx_sort_order` (`batch_id`, `sort_order`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='选股结果明细表';


-- --------------------------------------------------------
-- 表: stock_selection_stats
-- 用途: 存储选股结果的统计信息
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS `stock_selection_stats` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '自增主键ID',
    `batch_id` VARCHAR(64) NOT NULL COMMENT '选股批次ID',
    `trade_date` DATE NOT NULL COMMENT '交易日期',
    
    -- 市值统计
    `avg_market_cap` DECIMAL(15,2) DEFAULT NULL COMMENT '平均市值',
    `min_market_cap` DECIMAL(15,2) DEFAULT NULL COMMENT '最小市值',
    `max_market_cap` DECIMAL(15,2) DEFAULT NULL COMMENT '最大市值',
    
    -- 涨跌幅统计
    `avg_pct_chg` DECIMAL(8,4) DEFAULT NULL COMMENT '平均涨跌幅',
    `min_pct_chg` DECIMAL(8,4) DEFAULT NULL COMMENT '最小涨跌幅',
    `max_pct_chg` DECIMAL(8,4) DEFAULT NULL COMMENT '最大涨跌幅',
    
    -- 成交量统计
    `avg_volume` BIGINT DEFAULT NULL COMMENT '平均成交量',
    `total_volume` BIGINT DEFAULT NULL COMMENT '总成交量',
    `total_amount` DECIMAL(17,2) DEFAULT NULL COMMENT '总成交额',
    
    -- 行业分布（JSON格式）
    `industry_distribution` JSON DEFAULT NULL COMMENT '行业分布统计',
    
    -- 市场分布
    `sse_count` INT UNSIGNED DEFAULT 0 COMMENT '上交所股票数量',
    `szse_count` INT UNSIGNED DEFAULT 0 COMMENT '深交所股票数量',
    
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_batch_id` (`batch_id`),
    KEY `idx_trade_date` (`trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='选股结果统计表';


-- --------------------------------------------------------
-- 视图: v_stock_selection_latest
-- 用途: 查看最新选股结果
-- --------------------------------------------------------
CREATE OR REPLACE VIEW `v_stock_selection_latest` AS
SELECT 
    r.*,
    d.symbol,
    d.exchange,
    d.name,
    d.prev_close,
    d.ma10,
    d.market_cap,
    d.strategy_score
FROM stock_selection_result r
JOIN stock_selection_detail d ON r.batch_id = d.batch_id
WHERE r.trade_date = (
    SELECT MAX(trade_date) FROM stock_selection_result
)
ORDER BY r.batch_id, d.sort_order;


-- --------------------------------------------------------
-- 示例查询
-- --------------------------------------------------------

-- 1. 查询某日的选股结果
-- SELECT * FROM stock_selection_result WHERE trade_date = '2026-03-17';

-- 2. 查询某批次的所有选股明细
-- SELECT * FROM stock_selection_detail WHERE batch_id = 'SELECT_20260317_001' ORDER BY sort_order;

-- 3. 查询某策略的历史选股表现
-- SELECT 
--     r.trade_date,
--     r.batch_id,
--     AVG(d.pct_chg) as avg_return,
--     COUNT(*) as stock_count
-- FROM stock_selection_result r
-- JOIN stock_selection_detail d ON r.batch_id = d.batch_id
-- WHERE r.strategy_id = 'MA_VOLUME_FILTER'
-- GROUP BY r.trade_date, r.batch_id
-- ORDER BY r.trade_date DESC;

-- 4. 查询市值小于100亿的选股
-- SELECT * FROM stock_selection_detail 
-- WHERE batch_id = 'SELECT_20260317_001' AND market_cap < 100000
-- ORDER BY market_cap ASC;
