# -*- coding: UTF-8 -*-

import json
from os import path

import sys

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
import sqlite3
from threading import Thread
import requests
import time
import os
import random
import logging

threads = []

logging.basicConfig(
    level=logging.DEBUG,  # 定义输出到文件的log级别，
    format='%(asctime)s  %(filename)s : %(levelname)s  %(message)s',  # 定义输出log的格式
    datefmt='%Y-%m-%d %A %H:%M:%S',  # 时间
    filename="./x1x.log",  # log文件名
    filemode='w')  # 写入模式“w”或“a”
# Define a Handler and set a format which output to console
console = logging.StreamHandler()  # 定义console handler
console.setLevel(logging.INFO)  # 定义该handler级别
formatter = logging.Formatter('%(asctime)s  %(filename)s : %(levelname)s  %(message)s')  # 定义该handler格式
console.setFormatter(formatter)
# Create an instance
logging.getLogger().addHandler(console)  # 实例化添加handler


def log(tag, text):
    if (tag == 'i'):
        logging.info(text)
    elif (tag == 'e'):
        logging.error(text)
    elif (tag == 's'):
        logging.warning(text)


def get_proxy(proxy_list):
    '''
    (list) -> dict
    Given a proxy list <proxy_list>, a proxy is selected and returned.
    '''
    # Choose a random proxy
    proxy = random.choice(proxy_list)

    # Set up the proxy to be used
    proxies = {
        "http": str(proxy),
        "https": str(proxy)
    }

    # Return the proxy
    return proxies


def get(url, headers, proxies, timeout):
    try:
        if len(proxies) > 0:
            proxies = get_proxy(proxies)
            r = requests.get(url, timeout=timeout, verify=False, headers=headers, proxies=proxies)
            return r
        else:
            r = requests.get(url, timeout=timeout, verify=False, headers=headers)
            return r
    except BaseException as e:
        log("e", str(e))


def consle(alert_type, product_info):
    log("i", "名称：{0}，图片：{1}，更新时间：{2}".format(product_info[6] + product_info[0], product_info[4], product_info[3]))


def end():
    log("i", "token 过期！！请更换token！！")
    log("i", "。。。。自动退出。。。。")


def monitor(link, token, proxy_list):
    while (True):
        log('i', "Monitoring site <" + link + ">.")
        # Get the products on the site
        headers = {
            'accept': "*/*",
            'content-type': "application/json",
            'token': token,
            'accept-language': "zh-cn",
            'version': "1.4.0",
            'referer': "https://servicewechat.com/wxf8e9886ac9480eba/55/page-frame.html",
            'accept-encoding': "br, gzip, deflate",
            'cache-control': "no-cache",
            'User-Agent': "Mozilla/5.0 (Linux; Android 4.0.4; Galaxy Nexus Build/IMM76B) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.133 Mobile Safari/535.19"
        }
        try:
            r = get(link, timeout=10, headers=headers, proxies=proxy_list)
        except:
            try:
                r = get(link, timeout=20, headers=headers, proxies=proxy_list)
            except:
                log('e', "Connection to URL <" + link + "> failed.")
                # continue
        try:
            data = r.json()
            # print(data)
            if "code" in data.keys() and data['code'] == 1003:
                end()
                os._exit(0)

            data = data["data"]
            shopList = data['data']
            get_datas(shopList)
        except:
            log('e', "Connection to URL <" + link + "> failed." + r.text)
        time.sleep(delay)


def get_datas(datas):
    for product in datas:
        stock = True
        if product["stock"] <= 0:
            stock = False
        time_local = time.localtime(int(product["ctime"]) / 1000)
        dt = time.strftime("%Y-%m-%d %H:%M:%S", time_local)
        product_info = (
            product["title"],
            product['contentId'],
            stock,
            dt,
            product["picOptimizeBigUrl"],
            "未知",
            product["shopName"])
        alert = add_to_db(product_info)
        if (alert):
            consle("", product_info)


def add_to_db(product):
    # Initialize variables
    title = product[0]
    link = product[1]
    stock = str(product[2])
    skus = product[3]
    alert = False

    # Create database
    conn = sqlite3.connect('xex.db')
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS products(title TEXT, link TEXT UNIQUE, stock TEXT, skus TEXT)""")

    # Add product to database if it's unique
    try:
        c.execute("""INSERT INTO products (title, link, stock, skus) VALUES (?, ?, ?, ?)""",
                  (title, link, stock, skus))
        log('s', "Found new product with title " + title + ". Link = " + link)
        alert = product[2]
    except:
        try:
            # this is messy as fuck and I'm sorry.. :(
            d = (link,)
            c.execute('SELECT (stock) FROM products WHERE link=?', d)
            old_skus = c.fetchone()
            old_skus = old_skus[0]
            if old_skus != stock:
                # update table for that product with new stock
                log('s', "Product at URL: " + link + " update.")
                c.execute("""UPDATE products SET stock = ? WHERE link= ?""", (stock, link))
                if product[2]:
                    alert = True
                else:
                    alert = False
            else:
                log('w', "Product at URL: " + link + " already exists in the database.")
                pass
        except sqlite3.Error as e:
            log('e', "database error: " + str(e))
    # Close database
    conn.commit()
    c.close()
    conn.close()

    # Return whether or not it's a new product
    return alert


''' --------------------------------- RUN --------------------------------- '''

if (__name__ == "__main__"):
    # Ignore insecure messages
    requests.packages.urllib3.disable_warnings()
    log("i", "SNEAKER探针营出品，仅供学习交流 🚫禁止倒卖")

    with open(os.path.dirname(os.path.realpath(sys.argv[0])) + '/config.json') as config:
        j = json.load(config)
    proxies = []
    keywords = []
    # Load sites from file
    sites = j['sites']
    delay = j['delay']
    token = j['token']

    # Start monitoring sites
    for site in sites:
        t = Thread(target=monitor, args=(site, token, proxies))
        threads.append(t)
        t.start()
