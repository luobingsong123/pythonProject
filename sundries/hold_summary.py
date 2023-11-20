import MySQLdb


# mysql = MySQLdb.connect(host="192.168.1.80",
mysql = MySQLdb.connect(host="192.168.1.138",
                             user="root",
                             # password="a*963.-+",
                             password="Root_123",
                             port=3306,  # 端口
                             database="algo_access",
                             charset='utf8')
cursor = mysql.cursor()

key1_userid = 111
key2_securtyid = 0
key2_securty = ['000001','000002','000004','000005','000006','000007','000008','000009','000010','000011']
t = open('chicang.log','w')

ID = 0
USERID = 'User0000'
ACCOUNTID = '06400000'
SECURITYID = 0
QUANTITY = 22402670000
ORIGIN_QTY = 22402670000
ASSETACCOUNT = 0
insert_time = 0
while key1_userid < 200:
    while key2_securtyid < 10:
        mysql_str = 'INSERT INTO `algo_access`.`tb_hold_summary`(`ID`, `USERID`, `ACCOUNTID`, `SECURITYID`, `QUANTITY`, `ORIGIN_Q' \
                    'TY`, `ORIGIN_OPEN_PRICE`, `FREE_QTY`, `FROZEN_QTY`, `PRICE`, `PROFIT_AND_LOSS`, `RATE_OF_RETURN`, `CREATETIME`, ' \
                    '`UPDATETIME`, `LASTEXECID`, `VERSION`, `CUMBUYQTY`) VALUES ({0}, \'{1}\', \'{2}\', \'{3}  \', {4}, {5}, 45.7014, 22402670000, ' \
                    '44554600, 45.7014, 0, 0, 1654592222, 1654592222, \'\', 1, 0);'.format(key1_userid*8192+key2_securtyid+1,USERID+(str(key1_userid)),ACCOUNTID+(str(key1_userid)),key2_securty[key2_securtyid],QUANTITY,ORIGIN_QTY)
        try:
            cursor.execute(mysql_str)
            insert_time += 1
            t.write(mysql_str + '\n')
        except Exception:
            pass
        key2_securtyid += 1

    # mysql_str_money = "INSERT INTO `algo_access`.`tb_assetinfo`(`ID`, `USERID`, `ASSETACCOUNT`, `BALANCE`, `FROZEN`, `CREATETIME`, `UPDATETIME`, `VERSION`) VALUES ({0}, '{1}', '{2}', 999999999999, 0, 1654592222, 1655288290528, 2016);".format(key1_userid,USERID+(str(key1_userid)),ASSETACCOUNT)
    # t.write(mysql_str_money + '\n')
    key2_securtyid = 0
    key1_userid += 2
    mysql.commit()

print(insert_time)


