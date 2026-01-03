import matplotlib
matplotlib.use('TkAgg')  # 或者 'Qt5Agg', 'Agg'
import baostock as bs
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error
import matplotlib.pyplot as plt
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.optimizers import Adam
import warnings

warnings.filterwarnings('ignore')

# 设置matplotlib中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False


def fetch_stock_data():
    """获取股票数据"""
    print("正在获取股票数据...")

    #### 登陆系统 ####
    lg = bs.login()
    # 显示登陆返回信息
    print('login respond error_code:' + lg.error_code)
    print('login respond  error_msg:' + lg.error_msg)

    #### 获取历史K线数据 ####
    # 详细指标参数，参见"历史行情指标参数"章节
    rs = bs.query_history_k_data_plus("sh.600580",
                                      "date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,peTTM,pbMRQ,psTTM,pcfNcfTTM,isST",
                                      start_date='2025-04-01', end_date='2025-12-11',
                                      frequency="d", adjustflag="3")  # frequency="d"取日k线，adjustflag="3"默认不复权

    print('query_history_k_data_plus respond error_code:' + rs.error_code)
    print('query_history_k_data_plus respond  error_msg:' + rs.error_msg)

    # 将数据转换为DataFrame
    data_list = []
    while (rs.error_code == '0') & rs.next():
        # 获取一条记录，将记录合并在一起
        data_list.append(rs.get_row_data())

    result = pd.DataFrame(data_list, columns=rs.fields)

    #### 登出系统 ####
    bs.logout()

    # 数据预处理
    # 转换数据类型
    numeric_columns = ['open', 'high', 'low', 'close', 'preclose', 'volume', 'amount', 'turn', 'pctChg', 'peTTM', 'pbMRQ', 'psTTM', 'pcfNcfTTM']
    for col in numeric_columns:
        result[col] = pd.to_numeric(result[col], errors='coerce')

    # 按日期排序
    result['date'] = pd.to_datetime(result['date'])
    result = result.sort_values('date').reset_index(drop=True)

    print(f"成功获取 {len(result)} 条数据")
    print(f"数据时间范围: {result['date'].min()} 到 {result['date'].max()}")

    return result


def prepare_data(data, time_step=60):
    """准备训练数据"""
    # 使用收盘价作为主要特征
    price_data = data['close'].values.reshape(-1, 1)

    # 数据标准化
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(price_data)

    # 创建训练数据集
    X, y = [], []
    for i in range(time_step, len(scaled_data)):
        X.append(scaled_data[i - time_step:i, 0])
        y.append(scaled_data[i, 0])

    X, y = np.array(X), np.array(y)

    # 重塑数据为LSTM输入格式 [样本数, 时间步长, 特征数]
    X = X.reshape(X.shape[0], X.shape[1], 1)

    return X, y, scaler


def create_lstm_model(time_step):
    """创建LSTM模型"""
    model = Sequential()

    model.add(LSTM(units=50, return_sequences=True, input_shape=(time_step, 1)))
    model.add(Dropout(0.2))

    model.add(LSTM(units=50, return_sequences=True))
    model.add(Dropout(0.2))

    model.add(LSTM(units=50))
    model.add(Dropout(0.2))

    model.add(Dense(units=1))

    model.compile(optimizer=Adam(learning_rate=0.001),
                  loss='mean_squared_error')

    return model


def main():
    # 获取数据
    stock_data = fetch_stock_data()

    # 设置参数
    time_step = 60
    test_size = 0.2

    # 准备数据
    X, y, scaler = prepare_data(stock_data, time_step)

    # 划分训练集和测试集
    split_index = int(len(X) * (1 - test_size))
    X_train, X_test = X[:split_index], X[split_index:]
    y_train, y_test = y[:split_index], y[split_index:]

    print(f"训练集大小: {X_train.shape[0]}")
    print(f"测试集大小: {X_test.shape[0]}")

    # 创建和训练模型
    model = create_lstm_model(time_step)

    print("开始训练模型...")
    history = model.fit(X_train, y_train,
                        epochs=100,
                        batch_size=32,
                        validation_split=0.1,
                        verbose=1,
                        shuffle=False)

    # 预测
    train_predict = model.predict(X_train)
    test_predict = model.predict(X_test)

    # 反标准化
    train_predict = scaler.inverse_transform(train_predict)
    y_train_actual = scaler.inverse_transform(y_train.reshape(-1, 1))
    test_predict = scaler.inverse_transform(test_predict)
    y_test_actual = scaler.inverse_transform(y_test.reshape(-1, 1))

    # 计算评估指标
    train_rmse = np.sqrt(mean_squared_error(y_train_actual, train_predict))
    test_rmse = np.sqrt(mean_squared_error(y_test_actual, test_predict))
    train_mae = mean_absolute_error(y_train_actual, train_predict)
    test_mae = mean_absolute_error(y_test_actual, test_predict)

    print(f"\n模型评估结果:")
    print(f"训练集 RMSE: {train_rmse:.4f}")
    print(f"测试集 RMSE: {test_rmse:.4f}")
    print(f"训练集 MAE: {train_mae:.4f}")
    print(f"测试集 MAE: {test_mae:.4f}")

    # 可视化结果
    plt.figure(figsize=(15, 10))

    # 训练集结果
    plt.subplot(2, 1, 1)
    plt.plot(y_train_actual, label='实际价格', color='blue', alpha=0.7)
    plt.plot(train_predict, label='预测价格', color='red', alpha=0.7)
    plt.title('训练集: 实际价格 vs 预测价格')
    plt.xlabel('时间')
    plt.ylabel('价格')
    plt.legend()
    plt.grid(True)

    # 测试集结果
    plt.subplot(2, 1, 2)
    plt.plot(y_test_actual, label='实际价格', color='blue', alpha=0.7)
    plt.plot(test_predict, label='预测价格', color='red', alpha=0.7)
    plt.title('测试集: 实际价格 vs 预测价格')
    plt.xlabel('时间')
    plt.ylabel('价格')
    plt.legend()
    plt.grid(True)

    plt.tight_layout()
    # plt.show()
    plt.savefig('kline_chart.png', dpi=300, bbox_inches='tight')
    # 显示损失曲线
    plt.figure(figsize=(10, 6))
    plt.plot(history.history['loss'], label='训练损失')
    plt.plot(history.history['val_loss'], label='验证损失')
    plt.title('模型损失曲线')
    plt.xlabel('训练轮次')
    plt.ylabel('损失')
    plt.legend()
    plt.grid(True)
    # plt.show()
    plt.savefig('kline_chart.png', dpi=300, bbox_inches='tight')
    # 显示最后几天的预测结果
    print("\n最后5天的预测结果对比:")
    recent_results = pd.DataFrame({
        '实际价格': y_test_actual[-5:].flatten(),
        '预测价格': test_predict[-5:].flatten(),
        '误差': (y_test_actual[-5:].flatten() - test_predict[-5:].flatten())
    })
    print(recent_results.round(4))


if __name__ == "__main__":
    main()