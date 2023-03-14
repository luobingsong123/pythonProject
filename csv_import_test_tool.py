# coding=utf-8
import csv

# def reader(file):
#     with open(file,'r') as test_case:
#         reader = csv.reader(test_case)
#         next(reader)    # 表头
#         while True:
#             try:
#                 k = next(reader)    # 读文件，输出CSV
#                 print(k)
#                 d = ','
#                 s = '|'
#                 out_csv = open('d:/algo_csv/' + 'case_' + k[0] + '_' + k[1] + '.csv', 'w', encoding='utf-8')
#                 out_csv.write(k[2]+d+k[3]+s+k[4]+d+k[5]+'.'+k[6]+d+k[7]+s+k[8]+d+k[9]+s+k[10]+d+k[11]+d+k[12]+s+k[13]+d+k[14]+d+k[15]+d+k[16]+d+k[17]+d+k[18]+d+k[19]+d+k[20])
#                 out_csv.close()
#             except StopIteration:
#                 print('csv read end.')
#                 break


def reader(file):
    with open(file,'r') as test_case:
        reader = csv.reader(test_case)
        next(reader)    # 表头
        k = next(reader)  # 读文件，输出CSV
        print(k)
        d = ','
        s = '|'
        out_csv = open('d:/algo_csv/' + 'case_' + k[0] + '_' + k[1] + '.csv', 'w', encoding='utf-8')
        out_csv.write(
            k[2] + d + k[3] + s + k[4] + d + k[5] + '.' + k[6] + d + k[7] + s + k[8] + d + k[9] + s + k[10] + d + k[
                11] + d + k[12] + s + k[13] + d + k[14] + d + k[15] + d + k[16] + d + k[17] + d + k[18] + d + k[
                19] + d + k[20]+'\n')
        while True:
            try:
                k = next(reader)    # 读文件，输出CSV
                print(k)
                d = ','
                s = '|'
                out_csv.write(k[2]+d+k[3]+s+k[4]+d+k[5]+'.'+k[6]+d+k[7]+s+k[8]+d+k[9]+s+k[10]+d+k[11]+d+k[12]+s+k[13]+d+k[14]+d+k[15]+d+k[16]+d+k[17]+d+k[18]+d+k[19]+d+k[20]+'\n')
            except StopIteration:
                print('csv read end.')
                break
        out_csv.close()


if __name__ == '__main__':
    # file = r'C:\Users\DELL\Desktop\CSV_test_case.csv'
    file = r'C:\Users\DELL\Desktop\piliang.csv'
    reader(file)
