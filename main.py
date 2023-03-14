import sys
import struct
import time
import socket

# linux能绑定网卡这里绑定组播IP地址不会服错，windows没法绑定网卡这里不能绑定组播IP地址只能绑定本网卡IP地址
if "linux" in sys.platform:
    # 绑定到的网卡名，如果自己的不是eth0则注意修改
    nic_name = "eth0"
    # 监听的组播地址
    mcast_group_ip = "239.255.255.252"
else:
    mcast_group_ip = socket.gethostbyname(socket.gethostname())
mcast_group_port = 23456

def receiver():
    # 建立接收socket，和正常UDP数据包没区别
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    # 25是linux上的socket.SO_BINDTODEVICE的宏定义，但由于windows没实现SO_BINDTODEVICE，所以python索性也就没有实现SO_BINDTODEVICE，我们直接使用25
    # windows没有实现SO_BINDTODEVICE，所以不能通过这种方式绑定网卡，windows怎么实现绑定网卡暂不清楚
    if "linux" in sys.platform:
        sock.setsockopt(socket.SOL_SOCKET, 25, nic_name)
    # linux能绑定网卡这里绑定组播IP地址不会服错，windows没法绑定网卡这里不能绑定组播IP地址只能绑定本网卡IP地址
    sock.bind((mcast_group_ip, mcast_group_port))
    # 加入组播组
    mreq = struct.pack("=4sl", socket.inet_aton(mcast_group_ip), socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP,socket.IP_ADD_MEMBERSHIP,mreq)

    # 允许端口复用，看到很多教程都有没想清楚意义是什么，我这里直接注释掉
    # sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # 设置非阻塞，看到很多教程都有也没想清楚有什么用，我这里直接注释掉
    # sock.setblocking(0)
    while True:
        try:
            message, addr = sock.recvfrom(1024)
            print(f'{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}: Receive data from {addr}: {message.decode()}')
        except :
            print("while receive message error occur")


if __name__ == "__main__":
    receiver()