
import socket
import time
#创建socket对象
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
#发送数据 字节
str1 = {"name":"tom"}
while True:
    s.sendto(str(str1).encode(), ('229.0.0.15', 10000))
    print(str(str1).encode())
    time.sleep(1)
