# import requests
# import json
#
# url = "http://192.168.2.87:4523/mock/800178/user/api/heartbeat/3d3778ae-9594-44ad-8772-525e4a750964"
#
# payload = json.dumps({
#    "account": "pcf_test2",
#    "password": "123456",
#    "addressIp": "1.1.1.1"
# })
# headers = {
#    'User-Agent': 'apifox/1.0.0 (https://www.apifox.cn)',
#    'Content-Type': 'application/json'
# }
#
# response = requests.request("POST", url, headers=headers, data=payload)
#
# print(response.text)
import requests
import json

url = "http://192.168.2.87:4523/mock/800178/user/api/heartbeat/3d3778ae-9594-44ad-8772-525e4a750964"

payload = json.dumps({
   "heartId": "3d3778ae-9594-44ad-8772-525e4a750964"
})


headers = {
   'User-Agent': 'apifox/1.0.0 (https://www.apifox.cn)',
   'Content-Type': 'application/json'
}

response = requests.request("PUT", url, headers=headers, data=payload)

print(response.text)