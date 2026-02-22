-- 批量回测汇总结果表设计
-- 用于存储每轮批量回测的汇总结果，汇总结果以JSON格式存放
-- 以策略名称、回测开始日期、回测结束日期作为唯一索引

CREATE TABLE IF NOT EXISTS `backtest_batch_summary` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `strategy_name` varchar(100) NOT NULL COMMENT '策略名称',
  `backtest_start_date` date NOT NULL COMMENT '回测开始日期',
  `backtest_end_date` date NOT NULL COMMENT '回测结束日期',
  `backtest_framework` varchar(50) NOT NULL DEFAULT 'backtrader' COMMENT '回测框架：backtrader, time_based',
  `summary_json` json NOT NULL COMMENT '汇总结果JSON数据',
  `strategy_params_json` json DEFAULT NULL COMMENT '策略参数JSON数据',
  `stock_count` int unsigned DEFAULT 0 COMMENT '回测股票数量',
  `execution_time` decimal(12,4) DEFAULT 0.00 COMMENT '执行时间（秒）',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_strategy_period_framework` (`strategy_name`, `backtest_start_date`, `backtest_end_date`, `backtest_framework`),
  KEY `idx_strategy_name` (`strategy_name`),
  KEY `idx_backtest_period` (`backtest_start_date`, `backtest_end_date`),
  KEY `idx_backtest_framework` (`backtest_framework`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='批量回测汇总结果表';

-- 如果表已存在，添加新字段（可选执行）
-- ALTER TABLE `backtest_batch_summary` ADD COLUMN `strategy_params_json` json DEFAULT NULL COMMENT '策略参数JSON数据' AFTER `summary_json`;
-- ALTER TABLE `backtest_batch_summary` ADD COLUMN `backtest_framework` varchar(50) NOT NULL DEFAULT 'backtrader' COMMENT '回测框架：backtrader, time_based' AFTER `backtest_end_date`;
-- ALTER TABLE `backtest_batch_summary` DROP INDEX `uk_strategy_period`;
-- ALTER TABLE `backtest_batch_summary` ADD UNIQUE KEY `uk_strategy_period_framework` (`strategy_name`, `backtest_start_date`, `backtest_end_date`, `backtest_framework`);


-- 示例数据插入

-- 示例JSON数据结构
-- summary_json 字段包含以下内容：
-- {
--   "trading_days_count": 1200,              // 交易日历天数
--   "initial_cash": 100000,                   // 初始资金
--   "commission": 0.001,                      // 手续费率
--   "slippage_perc": 0.001,                  // 滑点率
--   "avg_return_rate": 5.23,                 // 平均收益率（%）
--   "avg_max_drawdown": 8.45,                // 平均最大回撤（%）
--   "profit_stock_count": 650,               // 盈利股票数
--   "loss_stock_count": 350,                 // 亏损股票数
--   "profit_ratio": 65.0,                    // 盈利占比（%）
--   "total_trade_count": 15000,              // 总交易次数
--   "total_profit_trade_count": 8500,        // 盈利交易次数
--   "total_loss_trade_count": 6500,          // 亏损交易次数
--   "win_rate": 56.67,                       // 胜率（%）
--   "total_commission": 2500000.00,          // 总手续费
--   "total_buy_commission": 1250000.00,      // 买入手续费
--   "total_sell_commission": 1250000.00,     // 卖出手续费
--   "commission_ratio": 2.50,                // 手续费占比（%）
--   "max_return_rate": 35.50,                // 最高收益率（%）
--   "min_return_rate": -15.20,               // 最低收益率（%）
--   "max_sharpe_ratio": 1.85,                // 最高夏普比率
--   "avg_sharpe_ratio": 0.85,                // 平均夏普比率
--   "csv_file_path": "csv/backtest_summary_20200101_to_20251220.csv",  // CSV文件路径
--   "execution_time": 3600.5,               // 执行时间（秒）
--   "avg_time_per_stock": 3.6005,            // 平均每只股票回测时间（秒）
--   "created_at": "2024-01-22 10:30:00",     // 创建时间
--   "created_by": "batch_backtest"           // 创建方式
-- }

INSERT INTO `backtest_batch_summary`
(`strategy_name`, `backtest_start_date`, `backtest_end_date`, `summary_json`, `stock_count`, `execution_time`)
VALUES
(
  'CodeBuddyStrategyDFX',
  '2020-01-01',
  '2025-12-20',
  '{
    "trading_days_count": 1200,
    "initial_cash": 100000,
    "commission": 0.001,
    "slippage_perc": 0.001,
    "avg_return_rate": 5.23,
    "avg_max_drawdown": 8.45,
    "profit_stock_count": 650,
    "loss_stock_count": 350,
    "profit_ratio": 65.0,
    "total_trade_count": 15000,
    "total_profit_trade_count": 8500,
    "total_loss_trade_count": 6500,
    "win_rate": 56.67,
    "total_commission": 2500000.00,
    "total_buy_commission": 1250000.00,
    "total_sell_commission": 1250000.00,
    "commission_ratio": 2.50,
    "max_return_rate": 35.50,
    "min_return_rate": -15.20,
    "max_sharpe_ratio": 1.85,
    "avg_sharpe_ratio": 0.85,
    "csv_file_path": "csv/backtest_summary_20200101_to_20251220.csv",
    "execution_time": 3600.5,
    "avg_time_per_stock": 3.6005,
    "created_at": "2024-01-22 10:30:00",
    "created_by": "batch_backtest"
  }',
  1000,
  3600.5
);

INSERT INTO `backtest_batch_summary`
(`strategy_name`, `backtest_start_date`, `backtest_end_date`, `summary_json`, `stock_count`, `execution_time`)
VALUES
(
  'CodeBuddyStrategy',
  '2024-01-01',
  '2024-06-20',
  '{
    "trading_days_count": 120,
    "initial_cash": 100000,
    "commission": 0.001,
    "slippage_perc": 0.001,
    "avg_return_rate": 3.45,
    "avg_max_drawdown": 6.20,
    "profit_stock_count": 420,
    "loss_stock_count": 180,
    "profit_ratio": 70.0,
    "total_trade_count": 8500,
    "total_profit_trade_count": 5000,
    "total_loss_trade_count": 3500,
    "win_rate": 58.82,
    "total_commission": 1450000.00,
    "total_buy_commission": 720000.00,
    "total_sell_commission": 730000.00,
    "commission_ratio": 1.93,
    "max_return_rate": 28.30,
    "min_return_rate": -12.50,
    "max_sharpe_ratio": 1.65,
    "avg_sharpe_ratio": 0.72,
    "csv_file_path": "csv/backtest_summary_20240101_to_20240620.csv",
    "execution_time": 2150.3,
    "avg_time_per_stock": 3.5838,
    "created_at": "2024-01-22 14:20:00",
    "created_by": "batch_backtest"
  }',
  600,
  2150.3
);


-- 常用查询示例

-- 1. 查询所有批量回测汇总结果
-- SELECT * FROM backtest_batch_summary ORDER BY created_at DESC;

-- 2. 查询指定策略的回测汇总
-- SELECT 
--   strategy_name,
--   backtest_start_date,
--   backtest_end_date,
--   stock_count,
--   execution_time,
--   JSON_EXTRACT(summary_json, '$.avg_return_rate') as avg_return_rate,
--   JSON_EXTRACT(summary_json, '$.profit_ratio') as profit_ratio,
--   JSON_EXTRACT(summary_json, '$.win_rate') as win_rate
-- FROM backtest_batch_summary
-- WHERE strategy_name = 'CodeBuddyStrategyDFX'
-- ORDER BY created_at DESC;

-- 3. 查询指定时间段的回测汇总
-- SELECT 
--   strategy_name,
--   backtest_start_date,
--   backtest_end_date,
--   JSON_EXTRACT(summary_json, '$.avg_return_rate') as avg_return_rate,
--   JSON_EXTRACT(summary_json, '$.profit_stock_count') as profit_stock_count,
--   JSON_EXTRACT(summary_json, '$.loss_stock_count') as loss_stock_count,
--   created_at
-- FROM backtest_batch_summary
-- WHERE backtest_start_date >= '2020-01-01' AND backtest_end_date <= '2025-12-31'
-- ORDER BY created_at DESC;

-- 4. 统计各策略的回测表现对比
-- SELECT 
--   strategy_name,
--   COUNT(*) as batch_count,
--   AVG(JSON_EXTRACT(summary_json, '$.avg_return_rate')) as avg_return_rate,
--   AVG(JSON_EXTRACT(summary_json, '$.profit_ratio')) as avg_profit_ratio,
--   AVG(JSON_EXTRACT(summary_json, '$.win_rate')) as avg_win_rate,
--   AVG(execution_time) as avg_execution_time
-- FROM backtest_batch_summary
-- GROUP BY strategy_name
-- ORDER BY avg_return_rate DESC;

-- 5. 查询表现最好的回测批次（按平均收益率）
-- SELECT 
--   strategy_name,
--   backtest_start_date,
--   backtest_end_date,
--   stock_count,
--   JSON_EXTRACT(summary_json, '$.avg_return_rate') as avg_return_rate,
--   JSON_EXTRACT(summary_json, '$.max_return_rate') as max_return_rate,
--   JSON_EXTRACT(summary_json, '$.profit_ratio') as profit_ratio,
--   execution_time,
--   created_at
-- FROM backtest_batch_summary
-- ORDER BY JSON_EXTRACT(summary_json, '$.avg_return_rate') DESC
-- LIMIT 10;

-- 6. 查看完整JSON数据（MySQL 5.7+）
-- SELECT 
--   strategy_name,
--   backtest_start_date,
--   backtest_end_date,
--   JSON_PRETTY(summary_json) as summary_data
-- FROM backtest_batch_summary
-- WHERE strategy_name = 'CodeBuddyStrategyDFX'
-- LIMIT 1;

-- 7. 获取JSON中的特定嵌套字段
-- SELECT 
--   strategy_name,
--   JSON_EXTRACT(summary_json, '$.csv_file_path') as csv_file,
--   JSON_EXTRACT(summary_json, '$.trading_days_count') as trading_days,
--   JSON_EXTRACT(summary_json, '$.commission') as commission_rate
-- FROM backtest_batch_summary;

-- 8. 检查是否存在某策略某时间段的回测结果
-- SELECT EXISTS(
--   SELECT 1 FROM backtest_batch_summary
--   WHERE strategy_name = 'CodeBuddyStrategyDFX'
--     AND backtest_start_date = '2020-01-01'
--     AND backtest_end_date = '2025-12-20'
-- ) as exists;

-- 9. 更新回测汇总结果
-- UPDATE backtest_batch_summary
-- SET 
--   summary_json = JSON_SET(summary_json, '$.avg_return_rate', 6.50),
--   summary_json = JSON_SET(summary_json, '$.profit_ratio', 70.0),
--   updated_at = CURRENT_TIMESTAMP
-- WHERE strategy_name = 'CodeBuddyStrategyDFX'
--   AND backtest_start_date = '2020-01-01'
--   AND backtest_end_date = '2025-12-20';

-- 10. 删除指定策略的回测汇总
-- DELETE FROM backtest_batch_summary
-- WHERE strategy_name = 'CodeBuddyStrategyDFX';
