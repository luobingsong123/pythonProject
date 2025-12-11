import matplotlib
matplotlib.use('TkAgg')  # 或者 'Qt5Agg', 'Agg'
import baostock as bs
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.pylab import rcParams
import warnings
from datetime import datetime, timedelta
import math


warnings.filterwarnings('ignore')

# 设置中文字体和图表样式
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False
plt.style.use('seaborn-v0_8')
rcParams['figure.figsize'] = 15, 10


def fetch_stock_data(code, start_date, end_date):
    """获取指定股票数据"""
    print("正在登录baostock系统...")

    # 登陆系统
    lg = bs.login()
    print(f'登录状态: {lg.error_code} - {lg.error_msg}')

    # 获取历史K线数据
    rs = bs.query_history_k_data_plus(code,
                                      "date,open,high,low,close,volume,amount,turn,pctChg",
                                      start_date=start_date,
                                      end_date=end_date,
                                      frequency="d",
                                      adjustflag="3")

    print(f'数据查询状态: {rs.error_code} - {rs.error_msg}')

    # 转换为DataFrame
    data_list = []
    while (rs.error_code == '0') & rs.next():
        data_list.append(rs.get_row_data())

    df = pd.DataFrame(data_list, columns=rs.fields)

    # 登出系统
    bs.logout()

    # 数据预处理
    numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'amount', 'turn', 'pctChg']
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)

    print(f"成功获取 {len(df)} 个交易日的数据")
    print(f"数据时间范围: {df['date'].min().strftime('%Y-%m-%d')} 到 {df['date'].max().strftime('%Y-%m-%d')}")

    return df


def create_kline_chart(df, code, save_fig=False):
    """创建K线图和成交量分析"""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(20, 12), gridspec_kw={'height_ratios': [3, 1]})

    # K线图（使用蜡烛图）
    for i in range(len(df)):
        date = df['date'].iloc[i]
        open_price = df['open'].iloc[i]
        high = df['high'].iloc[i]
        low = df['low'].iloc[i]
        close = df['close'].iloc[i]

        # 确定颜色：涨为红色，跌为绿色
        color = 'red' if close >= open_price else 'green'

        # 绘制影线
        ax1.plot([date, date], [low, high], color='black', linewidth=1)

        # 绘制实体
        body_width = 0.6
        ax1.fill_between([date - pd.Timedelta(days=body_width / 2),
                          date + pd.Timedelta(days=body_width / 2)],
                         open_price, close, color=color, alpha=0.7)

    # 添加移动平均线
    df['MA5'] = df['close'].rolling(window=5).mean()
    df['MA10'] = df['close'].rolling(window=10).mean()
    df['MA20'] = df['close'].rolling(window=20).mean()

    ax1.plot(df['date'], df['MA5'], label='5日均线', color='blue', linewidth=1.5)
    ax1.plot(df['date'], df['MA10'], label='10日均线', color='orange', linewidth=1.5)
    ax1.plot(df['date'], df['MA20'], label='20日均线', color='purple', linewidth=1.5)

    ax1.set_title(f'{code} K线图与移动平均线', fontsize=16, fontweight='bold', pad=20)
    ax1.set_ylabel('价格(元)', fontsize=12)
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 成交量图
    colors = ['red' if df['close'].iloc[i] >= df['open'].iloc[i] else 'green' for i in range(len(df))]
    ax2.bar(df['date'], df['volume'] / 10000, color=colors, alpha=0.7)
    ax2.set_title('成交量(万手)', fontsize=14)
    ax2.set_ylabel('成交量', fontsize=12)
    ax2.set_xlabel('日期', fontsize=12)
    ax2.grid(True, alpha=0.3)

    # 格式化x轴
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax1.xaxis.set_major_locator(mdates.MonthLocator())
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax2.xaxis.set_major_locator(mdates.MonthLocator())

    if save_fig:
        plt.tight_layout()
        plt.savefig(f'{code}_kline_chart.png', dpi=300, bbox_inches='tight')
    plt.close()


def calculate_technical_indicators(df):
    """计算各类技术指标"""
    # MACD指标
    exp12 = df['close'].ewm(span=12, adjust=False).mean()
    exp26 = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp12 - exp26
    df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_hist'] = df['MACD'] - df['MACD_signal']

    # RSI指标
    def calculate_rsi(prices, window=14):
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    df['RSI'] = calculate_rsi(df['close'])

    # 布林带
    df['BB_middle'] = df['close'].rolling(window=20).mean()
    df['BB_std'] = df['close'].rolling(window=20).std()
    df['BB_upper'] = df['BB_middle'] + 2 * df['BB_std']
    df['BB_lower'] = df['BB_middle'] - 2 * df['BB_std']

    # KDJ指标
    low_14 = df['low'].rolling(window=14).min()
    high_14 = df['high'].rolling(window=14).max()
    df['%K'] = (df['close'] - low_14) / (high_14 - low_14) * 100
    df['%D'] = df['%K'].rolling(window=3).mean()
    df['%J'] = 3 * df['%K'] - 2 * df['%D']

    # OBV能量潮
    df['OBV'] = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()

    print("技术指标计算完成")
    return df


def create_technical_chart(df, code,save_fig=False):
    """创建技术指标图表"""
    fig, axes = plt.subplots(4, 1, figsize=(20, 16))

    # 1. 价格与布林带
    axes[0].plot(df['date'], df['close'], label='收盘价', linewidth=2, color='black')
    axes[0].plot(df['date'], df['BB_upper'], label='布林带上轨', color='red', alpha=0.7, linestyle='--')
    axes[0].plot(df['date'], df['BB_middle'], label='布林带中轨', color='blue', alpha=0.7)
    axes[0].plot(df['date'], df['BB_lower'], label='布林带下轨', color='green', alpha=0.7, linestyle='--')
    axes[0].fill_between(df['date'], df['BB_upper'], df['BB_lower'], alpha=0.1, color='gray')
    axes[0].set_title('价格走势与布林带', fontsize=14, fontweight='bold')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # 2. MACD
    axes[1].plot(df['date'], df['MACD'], label='MACD', color='blue', linewidth=1.5)
    axes[1].plot(df['date'], df['MACD_signal'], label='信号线', color='red', linewidth=1.5)
    axes[1].bar(df['date'], df['MACD_hist'], label='柱状图', alpha=0.3, color='gray')
    axes[1].axhline(y=0, color='black', linestyle='-', alpha=0.3)
    axes[1].set_title('MACD指标', fontsize=14, fontweight='bold')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    # 3. RSI
    axes[2].plot(df['date'], df['RSI'], label='RSI', color='purple', linewidth=2)
    axes[2].axhline(y=70, color='red', linestyle='--', alpha=0.7, label='超买线(70)')
    axes[2].axhline(y=30, color='green', linestyle='--', alpha=0.7, label='超卖线(30)')
    axes[2].axhline(y=50, color='black', linestyle='-', alpha=0.3)
    axes[2].set_title('RSI相对强弱指标', fontsize=14, fontweight='bold')
    axes[2].set_ylim(0, 100)
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)

    # 4. KDJ
    axes[3].plot(df['date'], df['%K'], label='K线', color='blue', alpha=0.7)
    axes[3].plot(df['date'], df['%D'], label='D线', color='red', alpha=0.7)
    axes[3].plot(df['date'], df['%J'], label='J线', color='green', alpha=0.7)
    axes[3].axhline(y=80, color='red', linestyle='--', alpha=0.5, label='超买区')
    axes[3].axhline(y=20, color='green', linestyle='--', alpha=0.5, label='超卖区')
    axes[3].set_title('KDJ随机指标', fontsize=14, fontweight='bold')
    axes[3].set_ylim(0, 100)
    axes[3].legend()
    axes[3].grid(True, alpha=0.3)

    # 设置x轴格式
    for ax in axes:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.MonthLocator())
    if save_fig:
        plt.tight_layout()
        plt.savefig(f'{code}_technical_indicators.png', dpi=300, bbox_inches='tight')
    plt.close()


def fibonacci_analysis(df, code):
    """进行黄金分割分析"""
    recent_high = df['high'].max()
    recent_low = df['low'].min()
    price_range = recent_high - recent_low
    current_price = df['close'].iloc[-1]

    # 黄金分割关键位
    fib_levels = {
        '0.0%': recent_low,
        '23.6%': recent_low + price_range * 0.236,
        '38.2%': recent_low + price_range * 0.382,
        '50.0%': recent_low + price_range * 0.5,
        '61.8%': recent_low + price_range * 0.618,
        '78.6%': recent_low + price_range * 0.786,
        '100.0%': recent_high
    }

    print("=== 黄金分割分析 ===")
    print(f"近期高点: {recent_high:.2f}")
    print(f"近期低点: {recent_low:.2f}")
    print(f"价格区间: {price_range:.2f}")
    print(f"当前价格: {current_price:.2f}")
    print("\n关键支撑阻力位:")

    for level, price in fib_levels.items():
        position = "上方" if current_price < price else "下方"
        distance_pct = ((current_price - price) / price) * 100
        print(f"{level}: {price:.2f} (当前价格{position} {abs(distance_pct):.2f}%)")

    return fib_levels


def gann_analysis(df):
    """基于江恩理论的动态价格水平分析"""

    # 风险提示
    print("本代码仅用于回测研究，实盘使用风险自担")

    current_price = df['close'].iloc[-1]
    current_date = df['date'].iloc[-1] if 'date' in df.columns else df.index[-1]

    print("\n=== 江恩理论动态分析 ===")

    # 1. 计算关键价格水平（基于历史波动）
    high_price = df['high'].tail(len(df)).max()
    low_price = df['low'].tail(len(df)).min()
    price_range = high_price - low_price

    # 江恩关键回调比例：50%、63%、75%、100% [7,8](@ref)
    gann_ratios = [0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 1.0]
    key_price_levels = []

    for ratio in gann_ratios:
        level = low_price + price_range * ratio
        key_price_levels.append(level)

    print("动态关键价格水平分析:")
    for level in sorted(key_price_levels):
        position = "支撑位" if current_price > level else "阻力位"
        distance = abs(current_price - level)
        print(f"{position}: {level:.2f}元 (距离: {distance:.2f}元)")

    # 2. 江恩角度线分析 [1,5](@ref)
    def calculate_gann_angle(price_start, price_end, days):
        """计算江恩角度"""
        if days == 0:
            return 0
        price_diff = price_end - price_start
        # 江恩角度 = arctan(价格差/时间差) * 180/π [5](@ref)
        angle = 180 * math.atan(price_diff / days) / math.pi
        return angle

    # 计算不同周期的角度
    periods = [30, 60, 90, 180]
    print(f"\n江恩角度分析:")
    for period in periods:
        if len(df) > period:
            start_price = df['close'].iloc[-period]
            end_price = current_price
            angle = calculate_gann_angle(start_price, end_price, period)
            trend = "上升" if angle > 0 else "下降"
            print(f"{period}日周期: {trend}趋势, 角度: {abs(angle):.1f}°")

    # 3. 时间周期分析 [6](@ref)
    total_days = len(df)
    price_change_pct = (current_price - df['close'].iloc[0]) / df['close'].iloc[0] * 100

    print(f"\n时间周期分析:")
    print(f"分析周期: {total_days}个交易日")
    print(f"总涨跌幅: {price_change_pct:+.2f}%")

    # 江恩重要时间窗口 [6](@ref)
    gann_time_windows = [30, 45, 60, 90, 120, 180]
    print(f"\n江恩时间窗口预测:")
    for days in gann_time_windows:
        if isinstance(current_date, pd.Timestamp):
            future_date = current_date + timedelta(days=days)
            date_str = future_date.strftime('%Y-%m-%d')
        else:
            date_str = f"当前日期后{days}天"
        print(f"{days}天后: {date_str}")

    # 4. 回调带分析 [7,8](@ref)
    print(f"\n江恩回调带分析:")
    important_retracements = [0.5, 0.63, 0.75, 1.0]
    for retracement in important_retracements:
        level = low_price + price_range * retracement
        status = "强支撑" if current_price > level else "强阻力"
        print(f"{retracement * 100:.0f}%回调位: {level:.2f}元 ({status})")

    return {
        'key_price_levels': key_price_levels,
        'price_range': price_range,
        'current_trend': '上升' if current_price > df['close'].iloc[-10] else '下降'
    }

def trend_analysis(df, gann_levels):
    """进行趋势分析和预测"""
    current_price = df['close'].iloc[-1]
    latest_rsi = df['RSI'].iloc[-1]
    latest_macd = df['MACD'].iloc[-1]
    latest_macd_signal = df['MACD_signal'].iloc[-1]

    print("=== 趋势分析与预测 ===")

    # 趋势信号分析
    trend_signals = []

    # RSI分析
    if latest_rsi > 70:
        rsi_signal = "RSI显示超买状态，需警惕回调风险"
    elif latest_rsi < 30:
        rsi_signal = "RSI显示超卖状态，可能存在反弹机会"
    else:
        rsi_signal = "RSI处于正常区间"
    trend_signals.append(rsi_signal)

    # MACD分析
    if latest_macd > latest_macd_signal:
        macd_signal = "MACD金叉，短期看涨信号"
    else:
        macd_signal = "MACD死叉，短期看跌信号"
    trend_signals.append(macd_signal)

    # 布林带位置分析
    bb_position = (current_price - df['BB_lower'].iloc[-1]) / (df['BB_upper'].iloc[-1] - df['BB_lower'].iloc[-1]) * 100

    if bb_position > 80:
        bb_signal = "价格接近布林带上轨，存在回调压力"
    elif bb_position < 20:
        bb_signal = "价格接近布林带下轨，存在反弹机会"
    else:
        bb_signal = "价格在布林带中轨附近运行"
    trend_signals.append(bb_signal)

    # 移动平均线趋势
    if df['MA5'].iloc[-1] > df['MA10'].iloc[-1] > df['MA20'].iloc[-1]:
        ma_signal = "均线呈多头排列，趋势向上"
    elif df['MA5'].iloc[-1] < df['MA10'].iloc[-1] < df['MA20'].iloc[-1]:
        ma_signal = "均线呈空头排列，趋势向下"
    else:
        ma_signal = "均线交织，趋势不明朗"
    trend_signals.append(ma_signal)

    print("当前技术信号:")
    for i, signal in enumerate(trend_signals, 1):
        print(f"{i}. {signal}")

    print(f"\n布林带位置: {bb_position:.1f}%")
    print(f"RSI当前值: {latest_rsi:.1f}")
    print(f"MACD差值: {latest_macd - latest_macd_signal:.3f}")

    # # 支撑阻力位分析
    # support_levels = [level for level in gann_levels if level < current_price]
    # resistance_levels = [level for level in gann_levels if level > current_price]
    #
    # print(f"\n关键支撑位: {sorted(support_levels, reverse=True)[:3]}")
    # print(f"关键阻力位: {sorted(resistance_levels)[:3]}")

    return trend_signals


def fibonacci_time_analysis(df):
    """进行斐波那契时间周期分析"""
    current_date = df['date'].iloc[-1]
    fib_periods = [5, 8, 13, 21, 34, 55, 89, 144]

    print("\n=== 斐波那契时间周期分析 ===")
    print("未来关键时间窗口:")

    for days in fib_periods:
        future_date = current_date + pd.Timedelta(days=days)
        days_to_weekend = (future_date.weekday() - 4) % 7
        if days_to_weekend == 0:
            future_date += pd.Timedelta(days=2)  # 如果是周五，移到下周
        elif days_to_weekend == 1:
            future_date += pd.Timedelta(days=1)  # 如果是周六，移到周一

        print(f"斐波那契 {days:3d} 天: {future_date.strftime('%Y-%m-%d')} (周{future_date.strftime('%a')})")

    # 历史斐波那契时间点验证
    print(f"\n历史重要时间点验证:")
    important_dates = df[df['pctChg'].abs() > 5]['date']  # 涨跌幅超过5%的日期
    if not important_dates.empty:
        for date in important_dates[-3:]:  # 最近3个重要日期
            days_passed = (current_date - date).days
            print(f"{date.strftime('%Y-%m-%d')} (重大波动) - 距今{days_passed}天")


def get_comprehensive_rating(df):
    """生成综合评级"""
    score = 0
    total_indicators = 5

    # RSI评分
    rsi = df['RSI'].iloc[-1]
    if 30 <= rsi <= 70:
        score += 1
    elif 40 <= rsi <= 60:
        score += 2

    # MACD评分
    macd_diff = df['MACD'].iloc[-1] - df['MACD_signal'].iloc[-1]
    if macd_diff > 0:
        score += 1

    # 均线评分
    if df['MA5'].iloc[-1] > df['MA10'].iloc[-1] > df['MA20'].iloc[-1]:
        score += 2
    elif df['MA5'].iloc[-1] > df['MA20'].iloc[-1]:
        score += 1

    # 布林带评分
    bb_position = (df['close'].iloc[-1] - df['BB_lower'].iloc[-1]) / (df['BB_upper'].iloc[-1] - df['BB_lower'].iloc[-1])
    if 0.3 <= bb_position <= 0.7:
        score += 1

    # 成交量评分
    volume_ma = df['volume'].rolling(5).mean().iloc[-1]
    if df['volume'].iloc[-1] > volume_ma:
        score += 1

    rating = score / total_indicators * 100

    if rating >= 80:
        return "强烈看好", rating
    elif rating >= 60:
        return "看好", rating
    elif rating >= 40:
        return "中性", rating
    elif rating >= 20:
        return "谨慎", rating
    else:
        return "看空", rating


def generate_report(df, code):
    """生成综合分析报告"""
    current_data = df.iloc[-1]
    rating, score = get_comprehensive_rating(df)

    print("\n" + "=" * 60)
    print(f"{code} 技术分析综合报告")
    print("=" * 60)

    print(f"分析日期: {current_data['date'].strftime('%Y-%m-%d')}")
    print(f"当前价格: {current_data['close']:.2f}元")
    print(f"当日涨跌幅: {current_data['pctChg']:+.2f}%")
    print(f"成交量: {current_data['volume'] / 10000:.0f}万手")
    print(f"换手率: {current_data['turn']:.2f}%")
    print(f"\n综合评级: {rating} (得分: {score:.1f}/100)")

    print("\n操作建议:")
    if score >= 70:
        print("✅ 技术面整体向好，可考虑逢低布局")
    elif score >= 50:
        print("🔄 技术面中性，建议观望等待明确方向")
    else:
        print("⚠️ 技术面偏弱，注意风险控制")

    print("\n风险提示: 本分析基于历史数据，仅供参考，不构成投资建议。")
    print("实际投资需结合基本面、市场环境等因素综合判断。")


if __name__ == '__main__':
    # 用户输入参数
    # code = input("请输入证券代码（如：sh.600000）: ").strip()
    # start_date = input("请输入开始日期（格式：YYYY-MM-DD）: ").strip()
    # end_date = input("请输入结束日期（格式：YYYY-MM-DD）: ").strip()
    code = "sz.300462"
    # start_date = "2025-05-06"
    end_date = "2025-09-11"
    days = 60  # 分析天数
    image_save = False

    end_date = datetime.strptime(end_date, "%Y-%m-%d")
    # 计算起始日期（end_date - days）
    start_date = end_date - timedelta(days=days)
    # 将结果转换回字符串格式（可选）
    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")
    # print(start_date_str,end_date_str)
    print(f"\n开始分析 {code}，时间范围：{start_date_str} 至 {end_date_str}")

    # 获取数据
    df = fetch_stock_data(code, start_date_str, end_date_str)

    if len(df) == 0:
        print("未获取到数据，请检查输入参数是否正确")
        exit()

    # 创建K线图
    create_kline_chart(df, code, image_save)

    # 计算技术指标
    df = calculate_technical_indicators(df)

    # 创建技术指标图表
    create_technical_chart(df, code, image_save)

    # 各种分析
    fib_levels = fibonacci_analysis(df, code)
    gann_levels = gann_analysis(df)
    trend_signals = trend_analysis(df, gann_levels)
    # fibonacci_time_analysis(df)

    # 生成最终报告
    generate_report(df, code)

    if image_save:
        print(f"\n分析完成！图表已保存为：{code}_kline_chart.png 和 {code}_technical_indicators.png")