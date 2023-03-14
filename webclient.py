from selenium import webdriver
from time import sleep
import re
import xlrd

test_case = []

def get_all_msg(file):
    datas = xlrd.open_workbook(file)
    sheet = datas.sheet_by_name('Sheet1')
    cols = int(sheet.nrows)
    rows = int(sheet.ncols)
    j = 1
    row = 1
    while j < cols:
        data = []
        for i in range(rows):
            ctype = sheet.cell(row,i).ctype
            a = sheet.cell_value(row, i)  # 行，列
            if ctype == 2 and a % 1 == 0.0:
                a = int(a)
            data.append(str(a))
        # print(data)
        test_case.append(data)
        j += 1
        row += 1

def webclient():
    driver = webdriver.Chrome()
    driver.get("http://192.168.1.78/")
    sleep(1)
    driver.maximize_window()
    # 点击登录
    driver.find_element_by_xpath('//*[@id="root"]/div/form/div[3]/div/div/span/button').click()
    sleep(1)
    # 登录后获取窗口title进行判断是否登录成功,进入主页
    if driver.title == '主页':
        # 成功后截图
        driver.get_screenshot_as_file("D:\\webclient_login_success_img.png")
        print('登录成功')
    else:
        # 失败后截图
        driver.get_screenshot_as_file("D:\\webclient_login_fail_img.png")
        print('登录失败')
    sleep(1)

    # 定位某一组元素
    # 需要窗口能完全显示所有元素情况下才能正确抓取
    # texts = driver.find_elements_by_xpath('//tbody/tr/th')
    # datas = driver.find_elements_by_xpath('//tbody/tr/td')
    # th = []
    # td = []
    #
    # # 循环遍历出每一条搜索结果的标题并保存到列表内
    # for t in texts:
    #     # print(t.text)
    #     th.append(t.text)
    # for k in datas:
    #     # print(k.text)
    #     td.append(k.text)
    # # print(th)
    # print(td)
    # # find_element_by_xpath方法获取的元素需要用.text方法进行处理
    # msg = driver.find_element_by_xpath('/html/body/div[1]/section/section/div/div[2]/section/main/div/div/div[3]/div[1]/div[2]/div/div/div[1]/div[2]/table/tbody/tr[3]/td/div')
    # print("msg", msg.text)
    # print(len(td))
    # search 匹配不到内容则返回 None
    # 考虑使用表格管理

    # # 板卡类型
    # if re.search('HQM_\w{2}\d{4}', td[0]) != None:
    #     print(th[0],'数据正常')
    # else:
    #     print(th[0],'数据异常')
    # # FPGA版本
    # if re.search('HQM_\w{2}\d{4}', td[1]) != None:
    #     print(th[1],'数据正常')
    # else:
    #     print(th[1],'数据异常')
    # # 行情类型
    # if re.search('sz|sh', td[2]) != None:
    #     print(th[2],'数据正常')
    # else:
    #     print(th[2],'数据异常')
    # # 接入类型
    # if re.search('HQM_\w{2}\d{4}', td[3]) != None:
    #     print(th[3],'数据正常')
    # else:
    #     print(th[3],'数据异常')
    # # 编译日期,可以考虑对月份1-12，日期1-31进行限制
    # if re.search('202\d{5}', td[4]) != None:
    #     print(th[4],'数据正常')
    # else:
    #     print(th[4],'数据异常')
    # # SGDMA版本
    # if re.search('HQM_\w{2}\d{4}', td[5]) != None:
    #     print(th[5],'数据正常')
    # else:
    #     print(th[5],'数据异常')
    # # SGDMA日期
    # if re.search('HQM_\w{2}\d{4}', td[6]) != None:
    #     print(th[6],'数据正常')
    # else:
    #     print(th[6],'数据异常')
    # # PCIe速率
    # if re.search('gen\d{1}', td[7]) != None:
    #     print(th[7],'数据正常')
    # else:
    #     print(th[7],'数据异常')
    # # PCIe带宽
    # if re.search('x\d+', td[8]) != None:
    #     print(th[8],'数据正常')
    # else:
    #     print(th[8],'数据异常')
    # # DMA模式
    # if re.search('HQM_\w{2}\d{4}', td[9]) != None:
    #     print(th[9],'数据正常')
    # else:
    #     print(th[9],'数据异常')
    # # 开启状态
    # if re.search('HQM_\w{2}\d{4}', td[10]) != None:
    #     print(th[10],'数据正常')
    # else:
    #     print(th[10],'数据异常')
    #
    # if re.search('HQM_\w{2}\d{4}', td[11]) != None:
    #     print(th[11],'数据正常')
    # else:
    #     print(th[11],'数据异常')
    #
    # if re.search('HQM_\w{2}\d{4}', td[12]) != None:
    #     print(th[12],'数据正常')
    # else:
    #     print(th[12],'数据异常')
    #
    # if re.search('HQM_\w{2}\d{4}', td[13]) != None:
    #     print(th[13],'数据正常')
    # else:
    #     print(th[13],'数据异常')
    #
    # if re.search('HQM_\w{2}\d{4}', td[14]) != None:
    #     print(th[14],'数据正常')
    # else:
    #     print(th[14],'数据异常')
    #
    # if re.search('\w{2}:\w{2}:\w{2}:\w{2}:\w{2}:\w{2}', td[15]) != None:
    #     print(th[15],'数据正常')
    # else:
    #     print(th[15],'数据异常')
    #
    # if re.search('\d+\.\d+\.\d+\.\d+', td[16]) != None:
    #     print(th[16],'数据正常')
    # else:
    #     print(th[16],'数据异常')
    #
    # if re.search('HQM_\w{2}\d{4}', td[17]) != None:
    #     print(th[17],'数据正常')
    # else:
    #     print(th[17],'数据异常')
    #
    # if re.search('HQM_\w{2}\d{4}', td[18]) != None:
    #     print(th[18],'数据正常')
    # else:
    #     print(th[18],'数据异常')
    #
    # if re.search('HQM_\w{2}\d{4}', td[19]) != None:
    #     print(th[19],'数据正常')
    # else:
    #     print(th[19],'数据异常')
    #
    # if re.search('HQM_\w{2}\d{4}', td[20]) != None:
    #     print(th[20],'数据正常')
    # else:
    #     print(th[20],'数据异常')
    #
    # if re.search('HQM_\w{2}\d{4}', td[21]) != None:
    #     print(th[21],'数据正常')
    # else:
    #     print(th[21],'数据异常')
    #
    # if re.search('HQM_\w{2}\d{4}', td[22]) != None:
    #     print(th[22],'数据正常')
    # else:
    #     print(th[22],'数据异常')
    #
    # if re.search('HQM_\w{2}\d{4}', td[23]) != None:
    #     print(th[23],'数据正常')
    # else:
    #     print(th[23],'数据异常')


    # # 点击切换系统运行指数
    # driver.find_element_by_xpath('//*[@id="/main/parameter$Menu"]/li[2]').click()
    # sleep(1)
    # driver.find_element_by_xpath('//*[@id="/main/parameter$Menu"]/li[3]').click()
    # sleep(1)
    # # 选择展开行情实时信息
    # driver.find_element_by_xpath('//*[@id="root"]/section/section/div/div[1]/aside/div/ul/li[2]/div/span/i').click()
    # sleep(1)
    # driver.find_element_by_xpath('//*[@id="/main/market$Menu"]/li[1]').click()
    # sleep(1)
    # driver.find_element_by_xpath('//*[@id="/main/market$Menu"]/li[2]').click()
    # sleep(1)
    # driver.find_element_by_xpath('//*[@id="/main/market$Menu"]/li[3]').click()
    # sleep(1)
    #登出
    driver.find_element_by_xpath('//*[@id="root"]/section/header/div/div[1]').click()
    sleep(1)
    # 登出后获取窗口title进行判断是否登出成功,进入主页
    if driver.title == '登录':
        driver.get_screenshot_as_file("D:\\webclient_logout_success_img.png")
        print('登出成功')
    else:
        driver.get_screenshot_as_file("D:\\webclient_logout_success_img.png")
        print('登出失败')
    sleep(1)
    # 关闭浏览器
    driver.quit()

# 参数考虑直接传入表格路径和webdriver？
# def element_check(sheet_name,element_name,element_xpath,sample_data,regular):
#
#     if sheet_name == sheeta:
#         driver.find_element_by_xpath().click()
#         if re.search(regular, td[0]) != None:
#             print(element_name,'数据正常')
#         else:
#             print(element_name,'数据异常')
#     elif sheet_name == sheetb:
#     elif sheet_name == sheetc:
#     elif sheet_name == sheetd:
#     elif sheet_name == sheete:
#     elif sheet_name == sheetf:
#     elif sheet_name == sheetg:


if __name__ == '__main__':
    webclient()
    # get_all_msg('D:\webclient自动化测试用例管理示例.xlsx')
    # print(test_case)
