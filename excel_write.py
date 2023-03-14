import pandas as pd
from pandas import DataFrame

dic1 = {'标题列1': ['张三','李四'],
        '标题列2': [80, 90]
       }
df = pd.DataFrame(dic1)
df.to_excel('1.xlsx', index=False)