#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import MySQLdb
import time
from multiprocessing import Queue
from threading import Thread


class market_data(object):
    def __init__(self,data_file):
        # 分两线程
        # 1线程处理数据,组成list 推到消息队列
        # 2线程查询消息队列 分批处理 配合拼接SQL语句 插入
        self.data_file = data_file
        self.file_end_flag = True
        self.mysql = MySQLdb.connect(host="192.168.1.138",
                                     user="root",
                                     password="a*963.-+",
                                     port=3306,  # 端口
                                     database="sz_20200522",
                                     charset='utf8')
        self.cursor = self.mysql.cursor()
        self.queue = Queue()

    def data_cut(self):
        secid = 0
        total_vol = -4
        total_price = -3
        last_price = 7
        AskVol = 9
        BidPrice = 11
        level2_data_line = 0
        level2_total_vol = []
        level2_total_price = []
        level2_market_vwap = []
        all_market_vmap_para = []
        with open(self.data_file, 'r') as total_level2_data:
            print('start read time:', time.time())
            while True:
                if level2_data_line > 0 and level2_data_line % 100001 == 0:
                    print('cut 100001 time:',time.time())
                    print(level2_data_line)
                    break
                level2_data = total_level2_data.readline()
                if not level2_data:
                    self.file_end_flag = False
                    break
                level2_data_line += 1

                # 得到股票代码和行情数据
                level2_data_split = level2_data.split('|')
                self.level2_secid = level2_data_split[secid]

                # 数据处理
                # 取分钟和整分钟判断逻辑
                level2_time = level2_data_split[2][8:]     #
                time_s = level2_data_split[2][12:]
                # 最新总价和总量 ， 分时量价 在 和算法那块一起算
                total_vol_n = int(level2_data_split[total_vol])  #
                total_price_n = int(level2_data_split[total_price])  #
                last_price_n = float(level2_data_split[last_price]) / 1000000  #
                AskVol_10 = level2_data_split[AskVol]
                BidPrice_10 = level2_data_split[BidPrice]
                total_order_qty = sum([eval(_) for _ in AskVol_10.split(',')]) + sum([eval(_) for _ in BidPrice_10.split(',')])   #
                level2_total_vol.append(level2_data_split[total_vol])
                level2_total_price.append(level2_data_split[total_price])
                # print('cut done time:', time.time())
                # 开盘时间后算市场Vmap
                if 93000000 <= int(level2_time) <= 113000000 or 130000000 <= int(level2_time) <= 150100000:
                    # print('start vmap time:', time.time())
                    try:
                        market_vmap = (float(total_price_n) / 10000) / (float(total_vol_n) / 100)   #
                    except ZeroDivisionError:
                        market_vmap = 0.00001
                    # print('vmap done time:', time.time())
                    if time_s == '00000' or int(level2_time) >= 150000000:
                        all_market_vmap_para.append(self.level2_secid)
                        all_market_vmap_para.append('id')
                        all_market_vmap_para.append(level2_time)
                        all_market_vmap_para.append(last_price_n)
                        all_market_vmap_para.append(total_vol_n)
                        all_market_vmap_para.append(total_price_n)
                        all_market_vmap_para.append(total_order_qty)
                        all_market_vmap_para.append(market_vmap)
                        self.queue.put(all_market_vmap_para)
                        # print('start write mysql time:', time.time())
                        # 摘整分钟数据 写数据库
                        # 写数据库

                        # print('write mysql done time:', time.time())
                else:
                    market_vmap = 0
                level2_market_vwap.append(market_vmap)

    def mysql_commit(self):
        while self.file_end_flag:
            sql_str = tuple(self.queue.get())
            self.mysql_insert_data = "INSERT INTO `sz_20200522`.`000038` (`id`,`time`,`last_price`,`total_vol`,`total_price`,`total_order_qty`,`market_vmap`) VALUES "
            try:
                self.cursor.execute(self.mysql_insert_data)
                self.mysql.commit()
            except Exception as mysql_error:
                self.mysql_create_table = "CREATE TABLE `sz_20200522`.`{0}` (`id` INT, `time` CHAR(9), `last_price` FLOAT, `total_vol` BIGINT, `total_price` BIGINT, `total_order_qty` BIGINT, `market_vmap` FLOAT);".format(
                    sql_str[0])
                self.cursor.execute(self.mysql_create_table)
                self.mysql.commit()
                self.cursor.execute(self.mysql_insert_data)
                self.mysql.commit()
        pass


if __name__ == '__main__':
    mysql_data = market_data(r'D:\软件柜台\sz_20200522 LEVEL2数据\SZSE_LEVEL2_BIN_0414\SZSE_LEVEL2_BIN_0414')
    mysql_data.data_cut()

