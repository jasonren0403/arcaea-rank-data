# -*- coding: utf8 -*-
import json
import pathlib
import datetime
import time
import random
import logging

import requests
from requests.adapters import HTTPAdapter

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.35"
url_dict = {
    'free': 'https://webapi.lowiro.com/webapi/song/rank/free',
    'paid': 'https://webapi.lowiro.com/webapi/song/rank/paid'
}

logging.basicConfig(level = logging.INFO,format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("rank-data-crawler")

def get_proxy():
    # https://github.com/TheSpeedX/PROXY-List
    ip_net = "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt"
    try:
        res = requests.get(ip_net, timeout=5)
        ips = random.sample(res.text.split('\n'), 30)
        for each in ips:
            try:
                time.sleep(3)
                logger.info('testing %s', each)
                requests.get('https://github.com/', headers={
                    'User-Agent': UA
                }, proxies={
                    'http': each,
                    'https': each
                }, timeout=5)
                res2 = requests.get('https://webapi.lowiro.com/webapi/song/rank/free', headers={
                    'accept': 'application/json',
                    'User-Agent': UA,
                    'origin': 'https://arcaea.lowiro.com',
                    'referer': 'https://arcaea.lowiro.com/'
                }, proxies={
                    'http': each,
                    'https': each
                }, timeout=10)
                if res2.status_code == 200:
                    # print(res2.content)
                    logger.info("%s is ok", each)
                    return {
                        'http': each,
                        'https': each
                    }
                # print(res2.text)
                logger.warning(f"{each} errored with {res2.status_code}, headers: {res2.headers}")
            except (requests.exceptions.ProxyError, 
                    requests.exceptions.ConnectTimeout, 
                    requests.exceptions.ReadTimeout) as ex:
                logger.error(f"Proxy {each} have problems ({ex}), try next one")
                continue
            except Exception as e:
                logger.exception(f"{each} processed with exception", exc_info=e)
                continue
    except Exception:
        return {}

def process_bg(datalist, source, proxy_ip=None):
    s = requests.Session()
    s.mount('http://', HTTPAdapter(max_retries=3))
    s.mount('https://', HTTPAdapter(max_retries=3))
    proxy = proxy_ip
    for each in datalist:
        time.sleep(random.uniform(2,5))
        url = f"https://webassets.lowiro.com/{each['bg']}.jpg?v=323"
        local_path = pathlib.Path('./img') / f'{each["bg"]}.jpg'
        logger.info("checking local path %s", local_path.as_posix())
        if not local_path.exists():
            req = s.get(url=url, headers={
                'User-Agent': UA,
                'Referer': f'https://arcaea.lowiro.com/song_ranking/{source}'
            }, proxies=proxy,timeout=5)
            if req.status_code==200:
                logger.info(f"downloading {each['song_id']} from url {url}")
                with open(local_path, 'wb') as file:
                    file.write(req.content)
            else:
                logger.warning("failed to get %s", each['song_id'])


def get_song_rank(choose, proxy_ip=None):
    if choose not in ('free', 'paid'):
        raise ValueError('song_rank should be free or paid!')
    logger.info("songInfo: getting %s data", choose)
    url = url_dict.get(choose)
    s = requests.Session()
    s.mount('http://', HTTPAdapter(max_retries=3))
    s.mount('https://', HTTPAdapter(max_retries=3))
    req = None
    data = {}
    try:
        proxy = proxy_ip
        req = s.get(url=url, headers={
            'User-Agent': UA,
            'origin': 'https://arcaea.lowiro.com',
            'Referer': 'https://arcaea.lowiro.com/'
        }, proxies=proxy, timeout=15)
        data = req.json()
        if 'success' in data and data['success']:
            logger.info("getting %s data success, processing background", choose)
            process_bg(data['value'], choose, proxy_ip)
            return True, data['value']
        return False, data
    except Exception as ex:
        if data is not None and 'success' in data and data['success']:
            return True, data['value']
        return False, {
            'error': ex,
            'text': req.text if req is not None else ''
        }

def main():
    proxy = get_proxy()
    if proxy:
        logger.info("Using proxy %s for further fetch", proxy)
    res, free = get_song_rank('free', proxy_ip=proxy)
    res2, paid = get_song_rank('paid', proxy_ip=proxy)
    d = datetime.datetime.now()
    p = pathlib.Path(f'./{d.year}/{d.month}/{d.day}')
    if not p.exists():
        p.mkdir(parents=True)
    if res or 'error' not in free:
        logger.info("free data saved")
        with open(p / 'free.json', 'w', encoding='utf-8') as file:
            json.dump(free, file, ensure_ascii=False, indent=2)
    else:
        logger.fatal("get free data error! %s", free)
    if res2 or 'error' not in paid:
        logger.info("paid data saved")
        with open(p / 'paid.json', 'w', encoding='utf-8') as file:
            json.dump(paid, file, ensure_ascii=False, indent=2)
    else:
        logger.fatal("get paid data error! %s", paid)
    # print(free)
    # print("------")
    # print(paid)

main()
