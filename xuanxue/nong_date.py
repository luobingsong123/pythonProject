# -*- coding: utf-8 -*-
import zhdate
import datetime


# ------------------------------------------------------------------------------

def zhdate_to_date(year, month, day, leap_month):
    try:
        zd = zhdate.ZhDate(year, month, day, leap_month)
        zd = zd.to_datetime()
        return True, zd.year, zd.month, zd.day
    except:
        return False, None, None, None


x = zhdate_to_date(1938, 10, 29, 0)
print(x)


def date_to_zhdate(year, month, day):
    try:
        zd = zhdate.ZhDate(2000, 1, 1, False)
        zd = zd.from_datetime(datetime.datetime(year, month, day))
        return True, zd.lunar_year, zd.lunar_month, zd.lunar_day, zd.leap_month
    except:
        return False, None, None, None, None


# x = date_to_zhdate(1979, 2, 10)
# print(x)

# ------------------------------------------------------------------------------

def calc_days_between_dates(year_from, month_from, day_from, year_to, month_to, day_to):
    try:
        d1 = datetime.datetime(year_from, month_from, day_from)
        d2 = datetime.datetime(year_to, month_to, day_to)
        return True, (d2 - d1).days
    except:
        return False, None


# x = calc_days_between_dates(1938, 10, 29, 2023, 12, 26)
# print(x)

def calc_days_between_zhdates(year_from, month_from, day_from, leap_from, year_to, month_to, day_to, leap_to):
    try:
        d1 = zhdate.ZhDate(year_from, month_from, day_from, leap_from)
        d2 = zhdate.ZhDate(year_to, month_to, day_to, leap_to)
        d1 = d1.to_datetime()
        d2 = d2.to_datetime()
        return True, (d2 - d1).days
    except:
        return False, None


# x = calc_days_between_zhdates(1938, 10, 29, False, 2023, 12, 26, False)
# print(x)


def calc_days_between_date_and_zhdate(year_from, month_from, day_from, year_to, month_to, day_to, leap_to):
    try:
        d1 = datetime.datetime(year_from, month_from, day_from)
        d2 = zhdate.ZhDate(year_to, month_to, day_to, leap_to).to_datetime()
        return True, (d2 - d1).days
    except:
        return False, None


# x = calc_days_between_date_and_zhdate(1938, 12, 20, 2023, 12, 26, False)
# print(x)


def calc_days_between_zhdate_and_date(year_from, month_from, day_from, leap_from, year_to, month_to, day_to):
    try:
        d1 = zhdate.ZhDate(year_from, month_from, day_from, leap_from).to_datetime()
        d2 = datetime.datetime(year_to, month_to, day_to)
        return True, (d2 - d1).days
    except:
        return False, None


# x = calc_days_between_zhdate_and_date(1938, 10, 29, False, 2024, 2, 5)
# print(x)

# ------------------------------------------------------------------------------

def date_offset_to_date(year, month, day, offset_days):
    try:
        d = datetime.datetime(year, month, day) + datetime.timedelta(offset_days)
        return True, d.year, d.month, d.day
    except:
        return False, None, None, None


# x = date_offset_to_date(2024, 4, 30, 1)
# print(x)

def date_offset_to_zhdate(year, month, day, offset_days):
    try:
        d = datetime.datetime(year, month, day) + datetime.timedelta(offset_days)
        m = zhdate.ZhDate(2000, 1, 1, False)
        m = m.from_datetime(d)
        return True, m.lunar_year, m.lunar_month, m.lunar_day, m.leap_month
    except:
        return False, None, None, None, None


# x = date_offset_to_zhdate(1938, 10, 29, 1)
# print(x)


def zhdate_offset_to_zhdate(year_from, month_from, day_from, leap_from, offset_days):
    try:
        d1 = zhdate.ZhDate(year_from, month_from, day_from, leap_from)
        d2 = d1.to_datetime()
        d2 = d2 + datetime.timedelta(offset_days)
        d1 = d1.from_datetime(d2)
        return True, d1.lunar_year, d1.lunar_month, d1.lunar_day, d1.leap_month
    except:
        return False, None, None, None, None


# x = zhdate_offset_to_zhdate(1938, 10, 29, False, 31093)
# print(x)

def zhdate_offset_to_date(year_from, month_from, day_from, leap_from, offset_days):
    try:
        d1 = zhdate.ZhDate(year_from, month_from, day_from, leap_from)
        d2 = d1.to_datetime()
        d2 = d2 + datetime.timedelta(offset_days)
        return True, d2.year, d2.month, d2.day
    except:
        return False, None, None, None


# x = zhdate_offset_to_date(1938, 10, 29, False, 31093)
# print(x)

# ------------------------------------------------------------------------------

def fix_line(line):
    line = line.strip()
    length = 0

    while True:
        length = len(line)
        line = line.replace('  ', ' ')

        if length == len(line):
            break

    return line


# print(fix_line(' 1  2   3    4'))


def line_to_num_array(line):
    line = fix_line(line)
    cells = line.split(' ')
    cells = [int(c.lstrip('0') if len(c) > 1 else c) for c in cells]
    return cells


# print(line_to_num_array(' 1  2   3    4'))


def date_ui():
    print("")
    print("      要计算的内容")
    print("========================")
    print("  1 公历 -> 公历 : 天数")
    print("  2 公历 -> 农历 : 天数")
    print("  3 农历 -> 公历 : 天数")
    print("  4 农历 -> 农历 : 天数")
    print("")
    print("  5 公历 + 天数 -> 公历")
    print("  6 公历 + 天数 -> 农历")
    print("  7 农历 + 天数 -> 公历")
    print("  8 农历 + 天数 -> 农历")
    print("")
    print("  9 公历 -> 农历")
    print(" 10 农历 -> 公历")
    print("========================")

    ans = input("请输入要计算的内容 : ")

    if ans == '1':
        print("请依次输入起始年、月、日和结束年、月、日，以空格分割不同的数据：")
        ans = input("")
        cells = line_to_num_array(ans)

        if len(cells) != 6:
            print("输入参数应该是 6 个。")
        else:
            flag, days = calc_days_between_dates(cells[0], cells[1], cells[2], cells[3], cells[4], cells[5])

            if not flag:
                print("计算失败，请检查参数是否合理。")
            else:
                print("天数：", days)

    elif ans == '2':
        print("请依次输入起始公历年、月、日和结束农历年、月、日、闰月标记，以空格分割不同的数据：")
        print("是闰月则闰月标记写 1, 否则写 0.")
        ans = input("")

        cells = line_to_num_array(ans)

        if len(cells) != 7:
            print("输入参数应该是 7 个。")
        else:
            flag, days = calc_days_between_date_and_zhdate(cells[0], cells[1], cells[2], cells[3], cells[4], cells[5], cells[6])

            if not flag:
                print("计算失败，请检查参数是否合理。")
            else:
                print("天数：", days)

    elif ans == '3':
        print("请依次输入起始农历年、月、日、闰月标记和结束公历年、月、日，以空格分割不同的数据：")
        print("是闰月则闰月标记写 1, 否则写 0.")
        ans = input("")

        cells = line_to_num_array(ans)

        if len(cells) != 7:
            print("输入参数应该是 7 个。")
        else:
            flag, days = calc_days_between_zhdate_and_date(cells[0], cells[1], cells[2], cells[3], cells[4], cells[5], cells[6])

            if not flag:
                print("计算失败，请检查参数是否合理。")
            else:
                print("天数：", days)

    elif ans == '4':
        print("请依次输入起始农历年、月、日、闰月标记和结束农历年、月、日、闰月标记，以空格分割不同的数据：")
        print("是闰月则闰月标记写 1, 否则写 0.")
        ans = input("")

        cells = line_to_num_array(ans)

        if len(cells) != 8:
            print("输入参数应该是 8 个。")
        else:
            flag, days = calc_days_between_zhdates(cells[0], cells[1], cells[2], cells[3], cells[4], cells[5], cells[6], cells[7])

            if not flag:
                print("计算失败，请检查参数是否合理。")
            else:
                print("天数：", days)

    elif ans == '5':
        print("请依次输入起始年、月、日和天数，以空格分割不同的数据：")
        ans = input("")

        cells = line_to_num_array(ans)

        if len(cells) != 4:
            print("输入参数应该是 4 个。")
        else:
            flag, *date = date_offset_to_date(cells[0], cells[1], cells[2], cells[3])

            if not flag:
                print("计算失败，请检查参数是否合理。")
            else:
                print("公历：%4d 年 %02d 月 %02d 日" % (date[0], date[1], date[2]))

    elif ans == '6':
        print("请依次输入起始年、月、日和天数，以空格分割不同的数据：")
        ans = input("")

        cells = line_to_num_array(ans)

        if len(cells) != 4:
            print("输入参数应该是 4 个。")
        else:
            flag, *date = date_offset_to_zhdate(cells[0], cells[1], cells[2], cells[3])

            if not flag:
                print("计算失败，请检查参数是否合理。")
            else:
                print("农历：%4d 年 %s %02d 月 %02d 日" % (date[0], '闰' if date[3] else '', date[1], date[2]))

    elif ans == '7':
        print("请依次输入起始农历年、月、日、闰月标记和天数，以空格分割不同的数据：")
        print("是闰月则闰月标记写 1, 否则写 0.")
        ans = input("")

        cells = line_to_num_array(ans)

        if len(cells) != 5:
            print("输入参数应该是 5 个。")
        else:
            flag, *date = zhdate_offset_to_date(cells[0], cells[1], cells[2], cells[3], cells[4])

            if not flag:
                print("计算失败，请检查参数是否合理。")
            else:
                print("公历：%4d 年 %02d 月 %02d 日" % (date[0], date[1], date[2]))

    elif ans == '8':
        print("请依次输入起始农历年、月、日、闰月标记和天数，以空格分割不同的数据：")
        print("是闰月则闰月标记写 1, 否则写 0.")
        ans = input("")

        cells = line_to_num_array(ans)

        if len(cells) != 5:
            print("输入参数应该是 5 个。")
        else:
            flag, *date = zhdate_offset_to_zhdate(cells[0], cells[1], cells[2], cells[3], cells[4])

            if not flag:
                print("计算失败，请检查参数是否合理。")
            else:
                print("农历：%4d 年 %s %02d 月 %02d 日" % (date[0], '闰' if date[3] else '', date[1], date[2]))
    elif ans == '9':
        print("请依次输入公历年、月、日，以空格分割不同的数据：")
        ans = input("")

        cells = line_to_num_array(ans)

        if len(cells) != 3:
            print("输入参数应该是 3 个。")
        else:
            flag, *date = date_to_zhdate(cells[0], cells[1], cells[2])

            if not flag:
                print("计算失败，请检查参数是否合理。")
            else:
                print("农历：%4d 年 %s %02d 月 %02d 日" % (date[0], '闰' if date[3] else '', date[1], date[2]))

    elif ans == '10':
        print("请依次输入起始农历年、月、日、闰月标记，以空格分割不同的数据：")
        ans = input("")

        cells = line_to_num_array(ans)

        if len(cells) != 4:
            print("输入参数应该是 4 个。")
        else:
            flag, *date = zhdate_to_date(cells[0], cells[1], cells[2], cells[3])

            if not flag:
                print("计算失败，请检查参数是否合理。")
            else:
                print("公历：%4d 年 %02d 月 %02d 日" % (date[0], date[1], date[2]))

    else:
        print("未定义的输入 ：[%s]" % ans)

    return


# ------------------------------------------------------------------------------

def ui_loop():
    print("")
    print("日期计算工具")
    print("Farman@2024")

    while True:
        date_ui()

        ans = input("继续？(Y/n): ")

        if ans == 'n':
            break

    return


# ------------------------------------------------------------------------------

if __name__ == "__main__":
    ui_loop()