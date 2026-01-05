"""
API测试脚本
用于测试WebUI的各项API接口
"""

import requests
import json
from utils.logger_utils import setup_logger
import config

log_config = config.get_log_config()
logger = setup_logger(logger_name=__name__,
                      log_level=log_config["log_level"],
                      log_dir=log_config["log_dir"])

# API基础URL
web_config = config.get_web_config()
BASE_URL = f"http://{web_config['host']}:{web_config['port']}/api"


def print_response(response):
    """打印响应结果"""
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print("-" * 60)


def test_get_strategies():
    """测试获取策略列表"""
    print("\n测试1: 获取所有策略")
    print("-" * 60)
    try:
        response = requests.get(f"{BASE_URL}/strategies")
        print_response(response)
        return response.json()
    except Exception as e:
        print(f"请求失败: {str(e)}")
        return None


def test_get_stocks(strategy_name):
    """测试获取股票列表"""
    print(f"\n测试2: 获取策略 '{strategy_name}' 的股票列表")
    print("-" * 60)
    try:
        response = requests.get(f"{BASE_URL}/stocks", params={'strategy_name': strategy_name})
        print_response(response)
        return response.json()
    except Exception as e:
        print(f"请求失败: {str(e)}")
        return None


def test_get_trigger_points(strategy_name, stock_code, market):
    """测试获取触发点位"""
    print(f"\n测试3: 获取触发点位 - 策略: {strategy_name}, 股票: {stock_code}")
    print("-" * 60)
    try:
        params = {
            'strategy_name': strategy_name,
            'stock_code': stock_code,
            'market': market
        }
        response = requests.get(f"{BASE_URL}/trigger_points", params=params)
        print_response(response)
        return response.json()
    except Exception as e:
        print(f"请求失败: {str(e)}")
        return None


def test_get_kline_data(strategy_name, stock_code, market, trigger_index=0):
    """测试获取K线数据"""
    print(f"\n测试4: 获取K线数据 - 策略: {strategy_name}, 股票: {stock_code}, 触发点: {trigger_index}")
    print("-" * 60)
    try:
        params = {
            'strategy_name': strategy_name,
            'stock_code': stock_code,
            'market': market,
            'trigger_index': trigger_index,
            'bars_before': 30,
            'bars_after': 30
        }
        response = requests.get(f"{BASE_URL}/kline_data", params=params)
        print_response(response)
        return response.json()
    except Exception as e:
        print(f"请求失败: {str(e)}")
        return None


def test_get_statistics():
    """测试获取统计信息"""
    print("\n测试5: 获取统计信息")
    print("-" * 60)
    try:
        response = requests.get(f"{BASE_URL}/statistics")
        print_response(response)
        return response.json()
    except Exception as e:
        print(f"请求失败: {str(e)}")
        return None


def main():
    """主测试函数"""
    print("=" * 60)
    print("WebUI API 测试")
    print("=" * 60)

    # 测试1: 获取策略列表
    strategies_result = test_get_strategies()

    if not strategies_result or not strategies_result.get('success'):
        print("\n未找到策略数据，测试终止")
        return

    strategies = strategies_result['data']
    if not strategies:
        print("\n策略列表为空，请先运行回测并保存触发点位")
        return

    # 使用第一个策略进行后续测试
    first_strategy = strategies[0]['strategy_name']
    print(f"\n使用策略 '{first_strategy}' 进行后续测试")

    # 测试2: 获取股票列表
    stocks_result = test_get_stocks(first_strategy)

    if not stocks_result or not stocks_result.get('success'):
        print("\n未找到股票数据，测试终止")
        return

    stocks = stocks_result['data']
    if not stocks:
        print(f"\n策略 '{first_strategy}' 没有股票数据，请先运行回测")
        return

    # 使用第一只股票进行后续测试
    first_stock = stocks[0]
    stock_code = first_stock['stock_code']
    market = first_stock['market']
    print(f"\n使用股票 {stock_code} ({market}) 进行后续测试")

    # 测试3: 获取触发点位
    trigger_points_result = test_get_trigger_points(first_strategy, stock_code, market)

    if not trigger_points_result or not trigger_points_result.get('success'):
        print("\n未找到触发点位数据，测试终止")
        return

    trigger_count = trigger_points_result['data']['trigger_count']
    if trigger_count == 0:
        print(f"\n股票 {stock_code} 没有触发点位数据")
        return

    print(f"\n触发点位数量: {trigger_count}")

    # 测试4: 获取K线数据（第一个触发点）
    test_get_kline_data(first_strategy, stock_code, market, trigger_index=0)

    # 测试5: 获取统计信息
    test_get_statistics()

    print("\n" + "=" * 60)
    print("所有测试完成")
    print("=" * 60)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
