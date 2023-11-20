import requests

url = "http://192.168.2.87:4523/mock/800178/user/api/auth?username=huayun&password=123456&addressIP=192.168.1.111"

payload={}
headers = {
   'User-Agent': 'apifox/1.0.0 (https://www.apifox.cn)'
}

response = requests.request("POST", url, headers=headers, data=payload)

print(response.text)
