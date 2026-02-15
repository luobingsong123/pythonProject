-- ============================================
-- 优化的日线数据表结构
-- 适用于5000只股票十余年数据
-- ============================================

-- 方案1：带分区的日线表（推荐）
-- 优势：按年分区，便于历史数据管理和删除，提升查询性能
-- 注意：主键必须包含分区键（date）

CREATE TABLE `stock_daily_data_partitioned` (
  `date` date NOT NULL COMMENT '交易所行情日期',
  `market` varchar(2) NOT NULL COMMENT '市场代码：sh=上海, sz=深圳',
  `code_int` int(10) unsigned NOT NULL COMMENT '6位数字股票代码',
  `frequency` char(1) NOT NULL DEFAULT 'd' COMMENT '频率：d=日, w=周, m=月',

  -- 价格数据：使用decimal(10,4)支持股价到小数点后4位（足够覆盖股价）
  `open` decimal(10,4) NOT NULL COMMENT '开盘价',
  `high` decimal(10,4) NOT NULL COMMENT '最高价',
  `low` decimal(10,4) NOT NULL COMMENT '最低价',
  `close` decimal(10,4) NOT NULL COMMENT '收盘价',
  `preclose` decimal(10,6) DEFAULT NULL COMMENT '昨收价',

  -- 成交数据
  `volume` bigint(20) DEFAULT NULL COMMENT '成交量(股)',
  `amount` decimal(15,4) DEFAULT NULL COMMENT '成交额(元)',

  -- 技术指标
  `adjustflag` tinyint(4) NOT NULL DEFAULT 3 COMMENT '复权状态：1=后复权, 2=前复权, 3=不复权',
  `turn` decimal(10,6) DEFAULT NULL COMMENT '换手率',
  `tradestatus` tinyint(4) DEFAULT 1 COMMENT '交易状态：1=正常交易, 0=停牌',
  `pctChg` decimal(10,6) DEFAULT NULL COMMENT '涨跌幅(%)',

  -- 估值指标
  `peTTM` decimal(10,6) DEFAULT NULL COMMENT '滚动市盈率',
  `psTTM` decimal(10,6) DEFAULT NULL COMMENT '滚动市销率',
  `pcfNcfTTM` decimal(10,6) DEFAULT NULL COMMENT '滚动市现率',
  `pbMRQ` decimal(10,6) DEFAULT NULL COMMENT '市净率',

  -- 标志位
  `isST` tinyint(4) DEFAULT 0 COMMENT '是否ST股：1=是, 0=否',

  -- 时间戳
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),

  -- 主键：必须包含分区键date，保证唯一性
  PRIMARY KEY (`date`,`market`,`code_int`,`frequency`),

  -- 索引优化：根据查询模式设计
  -- 查询1: WHERE market='sh' AND code_int=601288 AND frequency='d' AND date>='2019-01-01'
  KEY `idx_market_code_date` (`market`,`code_int`,`date`),

  -- 查询2: 按代码日期范围查询
  KEY `idx_code_date` (`code_int`,`date`),

  -- 查询3: 按频率和日期查询
  KEY `idx_frequency_date` (`frequency`,`date`),

  -- 查询4: 按日期范围查询所有股票（用于批量回测）
  KEY `idx_date` (`date`)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 
COMMENT='A股日线/周线/月线数据（按年分区优化版）'
ROW_FORMAT=COMPRESSED KEY_BLOCK_SIZE=8  -- 使用压缩减少存储空间
PARTITION BY RANGE (TO_DAYS(`date`)) (
  PARTITION p2015 VALUES LESS THAN (TO_DAYS('2016-01-01')),
  PARTITION p2016 VALUES LESS THAN (TO_DAYS('2017-01-01')),
  PARTITION p2017 VALUES LESS THAN (TO_DAYS('2018-01-01')),
  PARTITION p2018 VALUES LESS THAN (TO_DAYS('2019-01-01')),
  PARTITION p2019 VALUES LESS THAN (TO_DAYS('2020-01-01')),
  PARTITION p2020 VALUES LESS THAN (TO_DAYS('2021-01-01')),
  PARTITION p2021 VALUES LESS THAN (TO_DAYS('2022-01-01')),
  PARTITION p2022 VALUES LESS THAN (TO_DAYS('2023-01-01')),
  PARTITION p2023 VALUES LESS THAN (TO_DAYS('2024-01-01')),
  PARTITION p2024 VALUES LESS THAN (TO_DAYS('2025-01-01')),
  PARTITION p2025 VALUES LESS THAN (TO_DAYS('2026-01-01')),
  PARTITION p_future VALUES LESS THAN MAXVALUE
);


-- 方案2：不分区但优化索引的版本
-- 如果不需要分区功能，使用这个版本更简单

CREATE TABLE `stock_daily_data_simple` (
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
  KEY `idx_market_code_date` (`market`,`code_int`,`date`),
  KEY `idx_code_date` (`code_int`,`date`),
  KEY `idx_frequency_date` (`frequency`,`date`),
  KEY `idx_date` (`date`)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 
ROW_FORMAT=COMPRESSED KEY_BLOCK_SIZE=8
COMMENT='A股日线/周线/月线数据（优化索引版）';


-- ============================================
-- 数据迁移脚本：从原表迁移到新表
-- ============================================

-- 迁移到分区表
INSERT INTO `stock_daily_data_partitioned`
SELECT * FROM `stock_daily_data`
ORDER BY `date`, `market`, `code_int`, `frequency`;

-- 验证数据一致性
SELECT
  (SELECT COUNT(*) FROM `stock_daily_data`) AS original_count,
  (SELECT COUNT(*) FROM `stock_daily_data_partitioned`) AS new_count;


-- ============================================
-- 表维护和优化建议
-- ============================================

-- 1. 定期分析表以更新统计信息
ANALYZE TABLE `stock_daily_data_partitioned`;

-- 2. 优化表以整理碎片
OPTIMIZE TABLE `stock_daily_data_partitioned`;

-- 3. 检查表状态
SHOW TABLE STATUS LIKE 'stock_daily_data_partitioned';

-- 4. 查看分区信息
SELECT
  PARTITION_NAME,
  PARTITION_EXPRESSION,
  PARTITION_DESCRIPTION,
  TABLE_ROWS
FROM information_schema.PARTITIONS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'stock_daily_data_partitioned'
ORDER BY PARTITION_ORDINAL_POSITION;


-- ============================================
-- 查询性能分析
-- ============================================

-- 查看查询执行计划（使用你的典型查询）
EXPLAIN SELECT date, open, high, low, close, volume, amount, pctChg
FROM `stock_daily_data_partitioned`
WHERE market = 'sh'
  AND code_int = 601288
  AND frequency = 'd'
  AND date >= '2019-01-01'
ORDER BY date;


-- ============================================
-- 分区管理操作
-- ============================================

-- 添加新分区（每年年初执行一次）
ALTER TABLE `stock_daily_data_partitioned`
ADD PARTITION (
    PARTITION p2026 VALUES LESS THAN (TO_DAYS('2027-01-01'))
);

-- 删除旧分区（谨慎使用，会删除数据）
ALTER TABLE `stock_daily_data_partitioned` DROP PARTITION p2015;


-- ============================================
-- 回退方案：如果分区表不满足需求
-- ============================================

-- 重命名原表
RENAME TABLE `stock_daily_data` TO `stock_daily_data_backup`;

-- 重命名新表
RENAME TABLE `stock_daily_data_partitioned` TO `stock_daily_data`;
