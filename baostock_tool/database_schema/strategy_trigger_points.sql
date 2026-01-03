-- 策略触发点位表设计
-- 用于存储各策略的触发点位JSON数据

CREATE TABLE IF NOT EXISTS `strategy_trigger_points` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `strategy_name` varchar(100) NOT NULL COMMENT '策略名称',
  `stock_code` varchar(10) NOT NULL COMMENT '证券代码',
  `market` enum('sh','sz','bj') NOT NULL DEFAULT 'sh' COMMENT '市场：sh=上海，sz=深圳，bj=北京',
  `trigger_points_json` json NOT NULL COMMENT '策略触发的对应日期JSON数据',
  `backtest_start_date` date NOT NULL COMMENT '策略回测开始日期',
  `backtest_end_date` date NOT NULL COMMENT '策略回测结束日期',
  `trigger_count` int unsigned DEFAULT 0 COMMENT '触发点位数量',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_strategy_stock_backtest` (`strategy_name`, `stock_code`, `market`, `backtest_start_date`, `backtest_end_date`),
  KEY `idx_strategy_name` (`strategy_name`),
  KEY `idx_stock_code` (`stock_code`),
  KEY `idx_market` (`market`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='策略触发点位表';

-- 示例数据插入
INSERT INTO `strategy_trigger_points` 
(`strategy_name`, `stock_code`, `market`, `trigger_points_json`, `backtest_start_date`, `backtest_end_date`, `trigger_count`)
VALUES 
(
  'CodeBuddyStrategy',
  '601288',
  'sh',
  '[
    {
      "date": "2024-01-05",
      "trigger_type": "buy",
      "price": 3.52,
      "volume": 1250000,
      "volume_rank": "20日最低"
    },
    {
      "date": "2024-01-08",
      "trigger_type": "sell",
      "price": 3.58,
      "hold_days": 2,
      "profit": 0.06,
      "profit_rate": 1.70
    },
    {
      "date": "2024-03-15",
      "trigger_type": "buy",
      "price": 3.65,
      "volume": 980000,
      "volume_rank": "20日最低"
    },
    {
      "date": "2024-03-18",
      "trigger_type": "sell",
      "price": 3.62,
      "hold_days": 2,
      "profit": -0.03,
      "profit_rate": -0.82
    }
  ]',
  '2024-01-01',
  '2024-12-31',
  4
);

-- 常用查询示例

-- 1. 查询指定策略的所有触发点位
-- SELECT * FROM strategy_trigger_points WHERE strategy_name = 'CodeBuddyStrategy';

-- 2. 查询指定股票的策略触发数据
-- SELECT * FROM strategy_trigger_points WHERE stock_code = '601288' AND market = 'sh';

-- 3. 查询指定时间范围内的回测数据
-- SELECT * FROM strategy_trigger_points 
-- WHERE backtest_start_date >= '2024-01-01' AND backtest_end_date <= '2024-12-31';

-- 4. 统计各策略的触发次数
-- SELECT strategy_name, COUNT(*) as stock_count, SUM(trigger_count) as total_triggers
-- FROM strategy_trigger_points
-- GROUP BY strategy_name;

-- 5. 查询JSON数据中的特定字段（MySQL 5.7+）
-- SELECT 
--   strategy_name,
--   stock_code,
--   market,
--   JSON_LENGTH(trigger_points_json) as trigger_count,
--   JSON_EXTRACT(trigger_points_json, '$[0].date') as first_trigger_date
-- FROM strategy_trigger_points
-- WHERE stock_code = '601288';
