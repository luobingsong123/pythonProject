a = 'int et'
b = 'source ap'
c = 'destination ap'
e = 'exit'

with open('aristaconfig.txt','w') as f:
    for i in range(5, 37):
        f.write(a+str(i+4)+'\n')
        f.write(b+str(i)+'\n')
        f.write(c+str(i)+'\n')
        f.write(e+'\n')