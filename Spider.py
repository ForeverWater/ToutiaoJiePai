import requests
import re
from urllib.parse import urlencode
from  requests.exceptions import RequestException
import json
from bs4 import BeautifulSoup
import lxml
from config import *
import pymongo
from json import JSONDecodeError
from multiprocessing import Pool

client = pymongo.MongoClient(MONGO_URL,connect=False)
db = client[MONGO_DB]

def get_page_index(offset, keyword):
    data = {
        'offset': offset,
        'format': 'json',
        'keyword': keyword,
        'autoload': 'true',
        'count': 20,
        'cur_tab': 1
    }
    url = 'https://www.toutiao.com/search_content/?' + urlencode(data)
    try:
        responce = requests.get(url)
        if responce.status_code == 200:
            return responce.text
        return None
    except RequestException:
        print('请求索引页出错')
        return None

def parse_page_index(html):
    try:
        data = json.loads(html)
        if data and 'data' in data.keys():
            for item in data.get('data'):
                yield item.get('article_url')
    except JSONDecodeError:
        print('解析json出错')
        return None

def get_page_detail(url):
    try:
        responce = requests.get(url)
        if responce.status_code == 200:
            return responce.text
        return None
    except RequestException:
        print('请求详情页出错',url)
        return None

def parse_page_detail(html,url):
    soup = BeautifulSoup(html,'lxml')
    title = soup.select('title')[0].get_text()
    print(title)
    pattern = re.compile('JSON.parse\("(.*?)"\),',re.S)
    results = re.search(pattern,html)
    if results:
        str = results.group(1)#需要去除json字符串中的转义符
        data = json.loads(str.replace('\\',''))
        if data and 'sub_images' in data.keys():
            sub_images = data.get('sub_images')
            images = [item.get('url') for item in sub_images]
            return {
                'title':title,
                'url':url,
                'images':images
            }
    else:
        pattern = re.compile('content: \'(.*?)\',', re.S)
        other_result = re.search(pattern, html)
        if other_result:
           soup = BeautifulSoup(other_result.group(1),'lxml')
           pattern = re.compile('img src="(.*?)" ', re.S)
           images = re.findall(pattern,soup.text)
           return {
               'title': title,
               'url': url,
               'images': images
           }

def save_to_mongo(result):
    if db[MONGO_TABLE].insert(result):
        print('MONGO数据库存储成功')
        return True
    return False

def main(offset):
    html = get_page_index(offset,'街拍')
    for detail_url in parse_page_index(html):
        html = get_page_detail(detail_url)
        if html:
          result = parse_page_detail(html,detail_url)
          print(result)
          #保存到数据库
          # if result:
          #    save_to_mongo(result)
          # else:
          #     print("数据为空")


if __name__ == '__main__':
    groups = [x * 20 for x in range(GROUP_START,GROUP_END + 1)]
    pool = Pool()
    pool.map(main,groups)
