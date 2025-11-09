import time
import random
import datetime
import zhdate


log_file = open('xiaoliuren_log.txt', 'a')

# xlr_dict = {
#     '空': {'空':"跳过0这个数"},
#     '大安': {'释义': '身不动时，五行属木，颜色青色，方位东方。\n临青龙，谋事主一、五、七。\n有静止、心安。\n吉祥之含义。',
#              '诀曰': '大安事事昌，求谋在东方，失物去不远，宅舍保安康。\n行人身未动，病者主无妨。\n将军回田野，仔细好推详。',
#              },
#     '留连': {'释义': '人未归时，五行属水，颜色黑色，方位北方，临玄武，凡谋事主二、八、十。\n有喑味不明，延迟。\n纠缠．拖延、漫长之含义。',
#              '诀曰': '留连事难成，求谋日未明。\n官事只宜缓，去者来回程，失物南方去，急寻方心明。\n更需防口舌，人事且平平。',
#              },
#     '速喜': {'释义': '人即至时，五行属火，颜色红色方位南方，临朱雀，谋事主三，六，九。\n有快速、喜庆，吉利之含义。\n指时机已到。',
#              '诀曰': '速喜喜来临，求财向南行。\n失物申未午，逢人要打听。\n官事有福德，病者无须恐。\n田宅六畜吉，行人音信明。',
#              },
#     '赤口': {'释义': '官事凶时，五行属金，颜色白色，方位西方，临白虎，谋事主四、七，十。\n有不吉、惊恐，凶险、口舌是非之含义。',
#              '诀曰': '赤口主口舌，官非切要防。\n失物急去寻，行人有惊慌。\n鸡犬多作怪，病者出西方。\n更须防咀咒，恐怕染瘟殃。',
#              },
#     '小吉': {'释义': '人来喜时，五行属木，临六合，凡谋事主一、五、七有和合、吉利之含义。',
#              '诀曰': '小吉最吉昌，路上好商量。\n阴人来报喜，失物在坤方。\n行人立便至，交易甚是强，凡事皆和合，病者祈上苍。',
#              },
#     '空亡': {'释义': '音信稀时，五行属土，颜色黄色，方位中央；临勾陈。\n谋事主三、六、九。\n有不吉、无结果、忧虑之含义。',
#              '诀曰': '空亡事不祥，阴人多乖张。\n求财无利益，行人有灾殃。\n失物寻不见，官事有刑伤。\n病人逢暗鬼，析解可安康。\n《神白经》云：“空亡空亡几多般，十干不到作空看。”\n古歌云：“胎里生逢怕遇空，遇空时节自昏蒙；饶君十步有九计，不免飘飘西复东。”',
#              },
# }

xlr_dict = {
    '空': {'空':"跳过0这个数"},
    '大安': {'释义': '',
             '诀曰': '',
             },
    '留连': {'释义': '',
             '诀曰': '',
             },
    '速喜': {'释义': '',
             '诀曰': '',
             },
    '赤口': {'释义': '',
             '诀曰': '',
             },
    '小吉': {'释义': '',
             '诀曰': '',
             },
    '空亡': {'释义': '',
             '诀曰': '',
             },
}


# 获取农历年月日时
def date_to_zhdate():
    times = datetime.datetime.now()
    log_file.write('问询时间：' + str(times) + '\n')
    try:
        zd = zhdate.ZhDate(2000, 1, 1, False)
        zd = zd.from_datetime(datetime.datetime(times.year, times.month, times.day))
        # print(zd.lunar_year, zd.lunar_month, zd.lunar_day, zd.leap_month)
        zd_hour = (times.hour + 1) // 2 % 12
        shi = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
        print('农历年月日时：', zd.lunar_year, '年', zd.lunar_month, '月 初', zd.lunar_day, '，   ', shi[zd_hour], '时')
        log_file.write('农历年月日时：' + str(zd.lunar_year) + '年' + str(zd.lunar_month) + '月' + str(zd.lunar_day) + '日' + str(zd_hour) + '时\n')
        return zd.lunar_year + zd.lunar_month + zd.lunar_day + zd_hour
    except Exception as e:
        # print('获取农历年月日时失败', e)
        print('今日不宜算卦。')

def zby():
    total_flag = []
    for i in range(3):
        input('按下回车键开始掷杯筊。')
        print('第', i + 1, '次掷杯筊...')
        print('掷杯筊中...')
        time.sleep(1)
        flag = [random.randint(0, 1), random.randint(0, 1)]
        t = sum(flag)
        if t == 0:
            print('杯筊结果：阴杯')
            total_flag.append(t)
        elif t == 1:
            print('杯筊结果：圣杯')
            total_flag.append(t)
        elif t == 2:
            print('杯筊结果：笑杯')
            total_flag.append(t)
        time.sleep(1)
    if total_flag == [1, 1, 1]:
        # if total_flag:
        print('掷出三圣杯，则本次测算之结果为可信之论。')
        log_file.write('掷出三圣杯，本次测算之结果为可信之论。')
        time.sleep(1)
    else:
        print('未掷出三圣杯，本次测算之结果为不可信之论。')
        log_file.write('未掷出三圣杯，本次测算之结果为不可信之论。')
        time.sleep(1)
    return total_flag


def xlr():
    # print(list(xlr_dict.keys()))
    while True:
        print('东风卷钱袋，金库破闸开；财路拦不住，洪流涌进来。')
        log_file.write('\n' + str(input('今日所卜：'))+'\n')
        keys_times = date_to_zhdate() % 6
        keys_t = list(xlr_dict.keys())[keys_times + 1]
        print('是时 ', keys_t)
        for ks in xlr_dict[keys_t]:
            print(ks, xlr_dict[keys_t][ks])
        print('*' * 64)
        print('仅依小六壬之法，结合时辰信息，预测吉凶祸福。')
        print('*' * 64)
        time.sleep(3)
        zby()
        input('请按下任意键继续...')
        time.sleep(1)
        while True:
            inputs = input('请输入任意数字(若不输入，则为随机数字测算):')
            try:
                inputs = int(inputs)
            except Exception as e:
                print('输入者非数字。以随机数者起卦')
                inputs = random.randint(0, 999999)
            log_file.write('输入数字：' + str(inputs) + '\n')
            if not inputs:
                inputs = random.randint(0, 999999)
            print('起卦数字：', inputs, '\n')
            log_file.write('起卦数字：' + str(inputs) + '\n')
            keys = list(xlr_dict.keys())[((int(inputs)+keys_times) % 6)+1]
            # keys = list(xlr_dict.keys())[(int(inputs)) % 6]
            time.sleep(1)
            print('是事 ', keys)
            log_file.write('是事 ' + keys + '\n')
            time.sleep(1)
            for ks in xlr_dict[keys]:
                print(ks, xlr_dict[keys][ks])
                log_file.write(ks + xlr_dict[keys][ks] + '\n')
            # print('祝您好运！')
            input('继续询问请输入询问事项后按回车键：')
            time.sleep(2)


if __name__ == '__main__':
    xlr()

