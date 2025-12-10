CREATE DATABASE IF NOT EXISTS `baostock_api_market_data`
DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE `baostock_api_market_data`;


-- baostock_api_market_data.stock_basic_info definition

CREATE TABLE `stock_basic_info` (
  `market` varchar(2) NOT NULL COMMENT '市场代码',
  `code_int` int(10) unsigned NOT NULL COMMENT '6位数字股票代码',
  `name` varchar(100) DEFAULT NULL COMMENT '证券名称',
  `industry` varchar(100) DEFAULT NULL COMMENT '所属行业',
  `area` varchar(50) DEFAULT NULL COMMENT '地区',
  `list_date` date DEFAULT NULL COMMENT '上市日期',
  `is_hs` tinyint(4) DEFAULT 0 COMMENT '是否沪深港通标的：1=是, 0=否',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`market`,`code_int`),
  KEY `idx_market` (`market`),
  KEY `idx_code` (`code_int`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票基本信息';


-- baostock_api_market_data.stock_daily_data definition

CREATE TABLE `stock_daily_data` (
  `date` date NOT NULL COMMENT '交易所行情日期',
  `market` varchar(2) NOT NULL COMMENT '市场代码：sh=上海, sz=深圳',
  `code_int` int(10) unsigned NOT NULL COMMENT '6位数字股票代码',
  `frequency` char(1) NOT NULL DEFAULT 'd' COMMENT '频率：d=日, w=周, m=月',
  `open` decimal(10,4) NOT NULL COMMENT '开盘价',
  `high` decimal(10,4) NOT NULL COMMENT '最高价',
  `low` decimal(10,4) NOT NULL COMMENT '最低价',
  `close` decimal(10,4) NOT NULL COMMENT '收盘价',
  `preclose` decimal(10,6) DEFAULT NULL,
  `volume` bigint(20) DEFAULT NULL COMMENT '成交量(股)',
  `amount` decimal(15,4) DEFAULT NULL COMMENT '成交额(元)',
  `adjustflag` tinyint(4) NOT NULL DEFAULT 3 COMMENT '复权状态：1=后复权, 2=前复权, 3=不复权',
  `turn` decimal(10,6) DEFAULT NULL,
  `tradestatus` tinyint(4) DEFAULT 1 COMMENT '交易状态：1=正常交易, 0=停牌',
  `pctChg` decimal(10,6) DEFAULT NULL,
  `peTTM` decimal(10,6) DEFAULT NULL COMMENT '滚动市盈率',
  `psTTM` decimal(10,6) DEFAULT NULL COMMENT '滚动市销率',
  `pcfNcfTTM` decimal(10,6) DEFAULT NULL COMMENT '滚动市现率',
  `pbMRQ` decimal(10,6) DEFAULT NULL COMMENT '市净率',
  `isST` tinyint(4) DEFAULT 0 COMMENT '是否ST股：1=是, 0=否',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`date`,`market`,`code_int`,`frequency`),
  KEY `idx_market_code` (`market`,`code_int`),
  KEY `idx_code` (`code_int`),
  KEY `idx_date` (`date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='A股日线/周线/月线数据';


-- baostock_api_market_data.stock_minute_data definition

CREATE TABLE `stock_minute_data` (
  `date` date NOT NULL COMMENT '交易所行情日期',
  `time` varchar(17) NOT NULL COMMENT '交易所行情时间，格式YYYYMMDDHHMMSSsss',
  `market` varchar(2) NOT NULL COMMENT '市场代码：sh=上海, sz=深圳',
  `code_int` int(10) unsigned NOT NULL COMMENT '6位数字股票代码',
  `frequency` tinyint(4) NOT NULL COMMENT '频率：5=5分钟, 15=15分钟, 30=30分钟, 60=60分钟',
  `open` decimal(12,6) NOT NULL COMMENT '开盘价',
  `high` decimal(12,6) NOT NULL COMMENT '最高价',
  `low` decimal(12,6) NOT NULL COMMENT '最低价',
  `close` decimal(12,6) NOT NULL COMMENT '收盘价',
  `volume` bigint(20) NOT NULL COMMENT '成交量(股)',
  `amount` decimal(17,4) NOT NULL COMMENT '成交额(元)',
  `adjustflag` tinyint(4) NOT NULL DEFAULT 3 COMMENT '复权状态：1=后复权, 2=前复权, 3=不复权',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`market`,`code_int`,`date`,`time`,`frequency`),
  KEY `idx_date_market` (`date`,`market`),
  KEY `idx_date_frequency` (`date`,`frequency`),
  KEY `idx_market_code_date` (`market`,`code_int`,`date`),
  KEY `idx_code_date` (`code_int`,`date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='A股分钟线数据（不包含指数）'
 PARTITION BY RANGE (year(`date`) * 100 + month(`date`))
(PARTITION `p202001` VALUES LESS THAN (202002) ENGINE = InnoDB,
 PARTITION `p202002` VALUES LESS THAN (202003) ENGINE = InnoDB,
 PARTITION `p202003` VALUES LESS THAN (202004) ENGINE = InnoDB,
 PARTITION `p202004` VALUES LESS THAN (202005) ENGINE = InnoDB,
 PARTITION `p202005` VALUES LESS THAN (202006) ENGINE = InnoDB,
 PARTITION `p202006` VALUES LESS THAN (202007) ENGINE = InnoDB,
 PARTITION `p202007` VALUES LESS THAN (202008) ENGINE = InnoDB,
 PARTITION `p202008` VALUES LESS THAN (202009) ENGINE = InnoDB,
 PARTITION `p202009` VALUES LESS THAN (202010) ENGINE = InnoDB,
 PARTITION `p202010` VALUES LESS THAN (202011) ENGINE = InnoDB,
 PARTITION `p202011` VALUES LESS THAN (202012) ENGINE = InnoDB,
 PARTITION `p202012` VALUES LESS THAN (202101) ENGINE = InnoDB,
 PARTITION `p202101` VALUES LESS THAN (202102) ENGINE = InnoDB,
 PARTITION `p202102` VALUES LESS THAN (202103) ENGINE = InnoDB,
 PARTITION `p202103` VALUES LESS THAN (202104) ENGINE = InnoDB,
 PARTITION `p202104` VALUES LESS THAN (202105) ENGINE = InnoDB,
 PARTITION `p202105` VALUES LESS THAN (202106) ENGINE = InnoDB,
 PARTITION `p202106` VALUES LESS THAN (202107) ENGINE = InnoDB,
 PARTITION `p202107` VALUES LESS THAN (202108) ENGINE = InnoDB,
 PARTITION `p202108` VALUES LESS THAN (202109) ENGINE = InnoDB,
 PARTITION `p202109` VALUES LESS THAN (202110) ENGINE = InnoDB,
 PARTITION `p202110` VALUES LESS THAN (202111) ENGINE = InnoDB,
 PARTITION `p202111` VALUES LESS THAN (202112) ENGINE = InnoDB,
 PARTITION `p202112` VALUES LESS THAN (202201) ENGINE = InnoDB,
 PARTITION `p202201` VALUES LESS THAN (202202) ENGINE = InnoDB,
 PARTITION `p202202` VALUES LESS THAN (202203) ENGINE = InnoDB,
 PARTITION `p202203` VALUES LESS THAN (202204) ENGINE = InnoDB,
 PARTITION `p202204` VALUES LESS THAN (202205) ENGINE = InnoDB,
 PARTITION `p202205` VALUES LESS THAN (202206) ENGINE = InnoDB,
 PARTITION `p202206` VALUES LESS THAN (202207) ENGINE = InnoDB,
 PARTITION `p202207` VALUES LESS THAN (202208) ENGINE = InnoDB,
 PARTITION `p202208` VALUES LESS THAN (202209) ENGINE = InnoDB,
 PARTITION `p202209` VALUES LESS THAN (202210) ENGINE = InnoDB,
 PARTITION `p202210` VALUES LESS THAN (202211) ENGINE = InnoDB,
 PARTITION `p202211` VALUES LESS THAN (202212) ENGINE = InnoDB,
 PARTITION `p202212` VALUES LESS THAN (202301) ENGINE = InnoDB,
 PARTITION `p202301` VALUES LESS THAN (202302) ENGINE = InnoDB,
 PARTITION `p202302` VALUES LESS THAN (202303) ENGINE = InnoDB,
 PARTITION `p202303` VALUES LESS THAN (202304) ENGINE = InnoDB,
 PARTITION `p202304` VALUES LESS THAN (202305) ENGINE = InnoDB,
 PARTITION `p202305` VALUES LESS THAN (202306) ENGINE = InnoDB,
 PARTITION `p202306` VALUES LESS THAN (202307) ENGINE = InnoDB,
 PARTITION `p202307` VALUES LESS THAN (202308) ENGINE = InnoDB,
 PARTITION `p202308` VALUES LESS THAN (202309) ENGINE = InnoDB,
 PARTITION `p202309` VALUES LESS THAN (202310) ENGINE = InnoDB,
 PARTITION `p202310` VALUES LESS THAN (202311) ENGINE = InnoDB,
 PARTITION `p202311` VALUES LESS THAN (202312) ENGINE = InnoDB,
 PARTITION `p202312` VALUES LESS THAN (202401) ENGINE = InnoDB,
 PARTITION `p202401` VALUES LESS THAN (202402) ENGINE = InnoDB,
 PARTITION `p202402` VALUES LESS THAN (202403) ENGINE = InnoDB,
 PARTITION `p202403` VALUES LESS THAN (202404) ENGINE = InnoDB,
 PARTITION `p202404` VALUES LESS THAN (202405) ENGINE = InnoDB,
 PARTITION `p202405` VALUES LESS THAN (202406) ENGINE = InnoDB,
 PARTITION `p202406` VALUES LESS THAN (202407) ENGINE = InnoDB,
 PARTITION `p202407` VALUES LESS THAN (202408) ENGINE = InnoDB,
 PARTITION `p202408` VALUES LESS THAN (202409) ENGINE = InnoDB,
 PARTITION `p202409` VALUES LESS THAN (202410) ENGINE = InnoDB,
 PARTITION `p202410` VALUES LESS THAN (202411) ENGINE = InnoDB,
 PARTITION `p202411` VALUES LESS THAN (202412) ENGINE = InnoDB,
 PARTITION `p202412` VALUES LESS THAN (202501) ENGINE = InnoDB,
 PARTITION `p202501` VALUES LESS THAN (202502) ENGINE = InnoDB,
 PARTITION `p202502` VALUES LESS THAN (202503) ENGINE = InnoDB,
 PARTITION `p202503` VALUES LESS THAN (202504) ENGINE = InnoDB,
 PARTITION `p202504` VALUES LESS THAN (202505) ENGINE = InnoDB,
 PARTITION `p202505` VALUES LESS THAN (202506) ENGINE = InnoDB,
 PARTITION `p202506` VALUES LESS THAN (202507) ENGINE = InnoDB,
 PARTITION `p202507` VALUES LESS THAN (202508) ENGINE = InnoDB,
 PARTITION `p202508` VALUES LESS THAN (202509) ENGINE = InnoDB,
 PARTITION `p202509` VALUES LESS THAN (202510) ENGINE = InnoDB,
 PARTITION `p202510` VALUES LESS THAN (202511) ENGINE = InnoDB,
 PARTITION `p202511` VALUES LESS THAN (202512) ENGINE = InnoDB,
 PARTITION `p_future` VALUES LESS THAN MAXVALUE ENGINE = InnoDB);

-- 创建交易日数据表
CREATE TABLE IF NOT EXISTS trade_calendar (
    id INT AUTO_INCREMENT PRIMARY KEY,
    calendar_date DATE NOT NULL UNIQUE COMMENT '日历日期',
    is_trading_day TINYINT(1) NOT NULL COMMENT '是否交易日：0-否，1-是',
    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_date (calendar_date),
    INDEX idx_trading (is_trading_day)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='交易日历数据表';


-- 创建回测配置表
CREATE TABLE backtest_config (
    backtest_id VARCHAR(36) PRIMARY KEY COMMENT '回测唯一标识(UUID)',
    strategy_name VARCHAR(100) NOT NULL COMMENT '策略名称',
    stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
    market VARCHAR(10) NOT NULL COMMENT '市场代码',
    start_date DATE NOT NULL COMMENT '回测开始日期',
    end_date DATE NOT NULL COMMENT '回测结束日期',
    initial_cash DECIMAL(15,2) NOT NULL DEFAULT 100000.00 COMMENT '初始资金',
    commission_rate DECIMAL(8,6) NOT NULL DEFAULT 0.001 COMMENT '手续费率',
    slippage_rate DECIMAL(8,6) NOT NULL DEFAULT 0.001 COMMENT '滑点率',
    parameters JSON COMMENT '策略参数(JSON格式)',
    description TEXT COMMENT '回测描述',
    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    status ENUM('running', 'completed', 'error') DEFAULT 'running' COMMENT '回测状态',

    INDEX idx_strategy_name (strategy_name),
    INDEX idx_stock_market (stock_code, market),
    INDEX idx_date_range (start_date, end_date),
    INDEX idx_created_time (created_time),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='回测配置表';

-- 创建回测绩效表
CREATE TABLE backtest_performance (
    performance_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '绩效记录ID',
    backtest_id VARCHAR(36) NOT NULL COMMENT '回测唯一标识',
    final_value DECIMAL(15,2) NOT NULL COMMENT '最终资金',
    total_return DECIMAL(10,4) NOT NULL COMMENT '总收益率(%)',
    annual_return DECIMAL(10,4) COMMENT '年化收益率(%)',
    sharpe_ratio DECIMAL(10,4) COMMENT '夏普比率',
    max_drawdown DECIMAL(10,4) COMMENT '最大回撤(%)',
    total_trades INT NOT NULL DEFAULT 0 COMMENT '总交易次数',
    win_rate DECIMAL(8,4) COMMENT '胜率(%)',
    profit_factor DECIMAL(10,4) COMMENT '盈亏比',
    total_commission DECIMAL(15,2) NOT NULL DEFAULT 0 COMMENT '总手续费',
    avg_trade_return DECIMAL(10,4) COMMENT '平均每笔交易收益',
    calmar_ratio DECIMAL(10,4) COMMENT '卡尔玛比率',
    sortino_ratio DECIMAL(10,4) COMMENT '索提诺比率',
    trade_days INT NOT NULL COMMENT '回测交易日数',
    benchmark_return DECIMAL(10,4) COMMENT '基准收益率(%)',
    alpha DECIMAL(10,4) COMMENT '阿尔法',
    beta DECIMAL(10,4) COMMENT '贝塔',
    information_ratio DECIMAL(10,4) COMMENT '信息比率',
    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    UNIQUE KEY uk_backtest_id (backtest_id),
    INDEX idx_total_return (total_return),
    INDEX idx_sharpe_ratio (sharpe_ratio),
    INDEX idx_max_drawdown (max_drawdown),
    INDEX idx_win_rate (win_rate),
    FOREIGN KEY (backtest_id) REFERENCES backtest_config(backtest_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='回测绩效表';

-- 创建交易明细表
CREATE TABLE backtest_trades (
    trade_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '交易记录ID',
    backtest_id VARCHAR(36) NOT NULL COMMENT '回测唯一标识',
    trade_date DATE NOT NULL COMMENT '交易日期',
    trade_type ENUM('buy', 'sell') NOT NULL COMMENT '交易类型',
    price DECIMAL(10,4) NOT NULL COMMENT '成交价格',
    size INT NOT NULL COMMENT '交易数量',
    value DECIMAL(15,2) NOT NULL COMMENT '交易金额',
    commission DECIMAL(10,4) NOT NULL DEFAULT 0 COMMENT '手续费',
    slippage DECIMAL(10,4) NOT NULL DEFAULT 0 COMMENT '滑点成本',
    pnl DECIMAL(12,4) COMMENT '盈亏金额(卖出时计算)',
    position_after INT NOT NULL COMMENT '交易后持仓',
    cash_after DECIMAL(15,2) NOT NULL COMMENT '交易后现金',
    trade_symbol VARCHAR(50) COMMENT '交易标的',
    trade_comment VARCHAR(200) COMMENT '交易备注',
    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    INDEX idx_backtest_id (backtest_id),
    INDEX idx_trade_date (trade_date),
    INDEX idx_trade_type (trade_type),
    INDEX idx_trade_symbol (trade_symbol),
    INDEX idx_date_type (trade_date, trade_type),
    FOREIGN KEY (backtest_id) REFERENCES backtest_config(backtest_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='交易明细表';