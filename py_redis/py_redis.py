import redis

# tb_algo_order_detail 这个表是子单信息
# tb_algo_order 这个表是母单信息

r = redis.Redis(host='192.168.1.80', port=6379,db=0,decode_responses=True)


total_keys = r.hkeys('sz:000038:20220522')
total_keys.sort()
total_price_sum = 0
total_trade_vol_sum = 0
total_pt_sum = 0
market_vmap = 0
all_price = []
all_trade_vol = []
all_macket_vmap = []
orig_time = []
data = ''
for key in total_keys:
    data = eval(r.hget('sz:000038:20220522', key))
    total_price_sum += data['last_price']
    total_trade_vol_sum += data['total_trade_vol']
    total_pt_sum += (data['last_price']/100 * data['total_trade_vol'])
    all_trade_vol.append(data['total_trade_vol'])
    all_price.append(data['last_price']/100)
    market_vmap = total_pt_sum/total_trade_vol_sum
    all_macket_vmap.append(market_vmap)
print(data)
print(all_price)
print(all_trade_vol)
print(all_macket_vmap)

import matplotlib as mpl
# mpl.use("TkAgg") # Use TKAgg to show figures
import matplotlib.pyplot as plt

fig2 = plt.figure(figsize=(7, 5))
# plt.plot(total_keys, all_trade_vol, c='g')  # 1.过点画线

# plt.plot(x_data1,y_data1)
# 一个图中要画出多条线的时候，只需要再使用plt.plot画出另一条线即可

plt.plot(total_keys, all_price)  # 2.画点
plt.plot(total_keys, all_macket_vmap)  # 2.画点

plt.title('X-Y Test')  # 3. 图标题
plt.xlabel("X")  # 4. X轴名字
plt.ylabel("Y")  # 5. Y轴名字

# plt.savefig("test.png")
plt.show()
# data = r.hget('sz:000038:20220522', '202205220932')
# print(type(data))
# data_eval = eval(data)
# print(data_eval)
# print(type(data_eval))
# data_key = r.hkeys('sz:000038:20220522')
# print(data_key)
# print(type(data_key))
