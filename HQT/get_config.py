import configparser
import os.path

def getConfig(section,key=None):
    config = configparser.ConfigParser()  #初始化一个configparser类对象
    # dir = os.path.dirname(os.path.dirname(__file__)) #获取当前文件的文件夹位置
    # print(dir)
    # file_path = dir+'\config.ini'  #完整的config.ini文件路径
    # print(file_path)
    config.read('config.ini',encoding='utf-8') #读取config.ini文件内容
    if key!=None:
        return config.get(section,key)  #获取某个section下面的某个key的值
    else:
        return config.items(section)  #或者某个section下面的所有值



if __name__=="__main__":
    print(getConfig('API_DEMO_DATABASE','host'))
    print(getConfig('API_DEMO_DATABASE'))
    print(getConfig('HQT_DATABASE'))

    self.own_data[ 'tb_order_info_cal' ][ 'margin' ] = self.own_data[ 'tb_cli_insert_req' ][ 'limit_price' ] * \
                                                       self.own_data[ 'tb_instrument_info' ][ 'volume_multiple' ] * \
                                                       self.own_data[ 'tb_fee_ratio_info' ][
                                                           self.own_data[ 'tb_cli_insert_req' ][ 'instrument_i_d' ] ][
                                                           'long_margin_ratio_by_money' ] * \
                                                       self.own_data[ 'tb_cli_insert_req' ][ 'volume_total_original' ]