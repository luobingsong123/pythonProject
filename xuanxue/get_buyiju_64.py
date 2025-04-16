import requests
from bs4 import BeautifulSoup
import json
import time
import os

# 伪装浏览器头
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': 'https://www.buyiju.com/'
}


def fetch_gua_content(gua_id):
    """抓取单个卦象内容"""
    url = f"https://www.buyiju.com/zhouyi/yijing/64gua-{gua_id}.html"

    try:
        # 带延迟的请求（防止反爬）
        time.sleep(1.5)
        response = requests.get(url, headers=HEADERS)
        response.encoding = 'utf-8'  # 目标网站编码

        if response.status_code != 200:
            print(f"请求失败，卦ID：{gua_id}，状态码：{response.status_code}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        main_content = soup.find('div', class_='content')
        print(main_content.prettify())  # 打印HTML结构，便于调试
        # 数据提取
        data = {
            "卦ID": gua_id,
            "卦名": main_content.find('h1').get_text(strip=True),
            "卦象": main_content.find('p', class_='gua-xiang').get_text(strip=True).split('：')[-1],
            "卦辞": main_content.find('div', class_='gua-ci').find('p').get_text(strip=True),
            "象辞": main_content.find('div', class_='xiang-ci').find('p').get_text(strip=True),
            "爻辞": [li.get_text(strip=True) for li in main_content.find('div', class_='yao-ci').find_all('li')],
            "解析": {
                "事业": main_content.find('div', id='career').find('p').get_text(strip=True),
                "经商": main_content.find('div', id='business').find('p').get_text(strip=True),
                "婚恋": main_content.find('div', id='marriage').find('p').get_text(strip=True),
                "决策": main_content.find('div', id='decision').find('p').get_text(strip=True)
            }
        }
        return data

    except Exception as e:
        print(f"抓取异常，卦ID：{gua_id}，错误：{str(e)}")
        return None


def save_to_json(data, filename):
    """保存数据到JSON文件"""
    os.makedirs('data', exist_ok=True)
    with open(f'data/{filename}', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def batch_fetch(start=1, end=64):
    """批量抓取卦象"""
    all_data = []

    for gua_id in range(start, end + 1):
        print(f"正在抓取第 {gua_id} 卦...")
        data = fetch_gua_content(gua_id)

        if data:
            # 保存单个卦象文件
            save_to_json(data, f'gua_{gua_id}.json')
            all_data.append(data)
        time.sleep(1.5)  # 延迟请求

    # 保存全集数据
    save_to_json(all_data, 'all_hexagrams.json')
    print("全部卦象抓取完成！")


if __name__ == '__main__':
    # 示例：抓取渐卦（ID=53）和全部64卦
    # 单卦测试
    # data = fetch_gua_content(53)
    # if data:
    #     save_to_json(data, 'gua_53.json')

    # 批量抓取
    batch_fetch(1, 64)  # 正式运行请解除注释