import pandas as pd


file = 'D:\\优选寄存器上海.xlsx'
outfile = 'D:\\优选寄存器上海.csv'


def xlsx_to_csv_pd():
    data_xls = pd.read_excel(file, index_col=0)
    data_xls.to_csv(outfile, encoding='utf-8')


if __name__ == '__main__':
    xlsx_to_csv_pd()
    print("\n转化完成！！！\nCSV文件所处位置：" + str(outfile))