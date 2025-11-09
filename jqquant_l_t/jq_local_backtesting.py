# from backtesting.test import GOOG

# print(GOOG.head())

from jqdatasdk import *

auth('13877907589', 'aA*963.-+')

print(get_account_info())

print(get_query_count())

print(get_price("601607.XSHG", start_date='2025-06-01', end_date='2025-06-10', frequency='1m'))

print(get_query_count())