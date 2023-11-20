import os,time

def run_silently(cmd: str) -> str:
    """返回系统命令的执行结果"""
    with os.popen(cmd) as fp:
        bf = fp._stream.buffer.read()
    try:
        return bf.decode().strip()
    except UnicodeDecodeError:
        return bf.decode('gbk').strip()
name=time.strftime('%m%d%H%M%S')

#启动exe
# for i in range(1,19):
#     st = time.strftime('%m%d%H%M%S')
#     r=run_silently(f'start ""/d "./" /wait "test{i}.exe"')
#     with open(f'test{name}.log','a+',encoding='utf-8') as t:
#          t.write(f'---------------------测试指标{i}用例已开始运行,开始时间为：{st}---------------------')
#          t.write('\r\n')
#          t.write(r)
#          t.write('\r\n')
#          et = time.strftime('%m%d%H%M%S')
#          t.write(f'---------------------测试指标{i}用例已运行结束,结束时间为：{et}---------------------')
#          t.write('\r\n')


#启动py
for i in range(1,10):
    st = time.strftime('%m%d%H%M%S')
    r=run_silently(f"python  ./test{i}.py")
    with open(f'test{name}.log','a+',encoding='utf-8') as t:
         t.write(f'---------------------测试指标{i}用例已开始运行,开始时间为：{st}---------------------')
         t.write('\r\n')
         t.write(r)
         t.write('\r\n')
         et = time.strftime('%m%d%H%M%S')
         t.write(f'---------------------测试指标{i}用例已运行结束,结束时间为：{et}---------------------')
         t.write('\r\n')








