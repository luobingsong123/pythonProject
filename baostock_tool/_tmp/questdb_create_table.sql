-- QuestDB 表创建脚本
-- 表名: stock_daily_data
-- 说明: A股日线/周线/月线数据

-- 删除已存在的表（可选）
-- DROP TABLE IF EXISTS stock_daily_data;

CREATE TABLE IF NOT EXISTS stock_daily_data (
    -- 时间戳列（QuestDB要求必须有TIMESTAMP类型作为主键）
    date TIMESTAMP NOT NULL,
    
    -- 市场代码：sh=上海, sz=深圳 (使用SYMBOL优化重复值)
    market SYMBOL,
    
    -- 6位数字股票代码
    code_int INT,
    
    -- 频率：d=日, w=周, m=月
    frequency SYMBOL,
    
    -- 开盘价
    open DOUBLE,
    
    -- 最高价
    high DOUBLE,
    
    -- 最低价
    low DOUBLE,
    
    -- 收盘价
    close DOUBLE,
    
    -- 前收盘价(元)
    preclose DOUBLE,
    
    -- 成交量(股)
    volume LONG,
    
    -- 成交额(元)
    amount DOUBLE,
    
    -- 复权状态：1=后复权, 2=前复权, 3=不复权
    adjustflag INT,
    
    -- 换手率(%)
    turn DOUBLE,
    
    -- 交易状态：1=正常交易, 0=停牌
    tradestatus INT,
    
    -- 涨跌幅(%)
    pctChg DOUBLE,
    
    -- 滚动市盈率
    peTTM DOUBLE,
    
    -- 滚动市销率
    psTTM DOUBLE,
    
    -- 滚动市现率
    pcfNcfTTM DOUBLE,
    
    -- 市净率
    pbMRQ DOUBLE,
    
    -- 是否ST股：1=是, 0=否
    isST INT,
    
    -- 创建时间
    created_at TIMESTAMP,
    
    -- 更新时间
    updated_at TIMESTAMP,
    
    -- 主键：使用date作为时间戳主键
    PRIMARY KEY(date, market, code_int, frequency) NOT NULL
)
-- 按年份分区
PARTITION BY YEAR;

-- 创建索引以加速查询
-- 市场+代码+日期 索引
-- INDEX已弃用，QuestDB自动为SYMBOL列创建索引
-- 这里使用物化视图或滚动窗口查询替代

-- 注释说明
-- 1. QuestDB必须有TIMESTAMP类型的列作为主键，这里使用date
-- 2. market和frequency使用SYMBOL类型，自动创建索引
-- 3. 按YEAR自动分区，支持高效的时间范围查询
-- 4. DOUBLE类型兼容MySQL的DECIMAL
-- 5. LONG类型对应MySQL的BIGINT

-- 示例查询
-- SELECT * FROM stock_daily_data WHERE date >= '2024-01-01' AND date <= '2024-12-31';
-- SELECT * FROM stock_daily_data WHERE market = 'sh' AND code_int = 600054;
