# -*- coding: utf8 -*-
# pylint: disable=C0116
import json
import os
import pathlib
import datetime
import time
import random
import logging
import telnetlib # todo: replace with un-deprecated package
import telebot

import requests
import coloredlogs
from requests.adapters import HTTPAdapter

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.35"
url_dict = {
    'free': 'https://webapi.lowiro.com/webapi/song/rank/free',
    'paid': 'https://webapi.lowiro.com/webapi/song/rank/paid'
}

BOT_CHAT_ID = "1355571156"
LOCAL_TEST = os.getenv('CI') is None
TEST_PROXY = {
    'http': '<TEST_IP>',
    'https': '<TEST_IP>'
}

logger = logging.getLogger("rank-data-crawler")
coloredlogs.install(level="INFO", logger=logger,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def get_proxy():
    # https://github.com/TheSpeedX/PROXY-List
    ip_net = "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt"
    try:
        res = requests.get(ip_net, timeout=5)
        ips = random.sample(res.text.split('\n'), k=int(
            os.getenv('IP_CHECK_COUNT', "5")))
        count = 0
        for each in ips:
            try:
                time.sleep(2)
                count += 1
                logger.info('[%s/%s]testing %s', count, len(ips), each)
                ip, port = each.split(":")
                telnetlib.Telnet(ip, port=port, timeout=10)
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
                logger.warning("%s errored with %s", each, res2.status_code)
            except (requests.exceptions.ProxyError,
                    requests.exceptions.ConnectTimeout,
                    requests.exceptions.ReadTimeout) as ex:
                logger.error("Proxy %s have problems (%s), try next one", each, ex)
                continue
            except TimeoutError as ex:
                logger.error("Proxy %s connect timeout, next one", each)
                continue
            except Exception as e:
                logger.exception(
                    f"{each} processed with exception", exc_info=e)
                continue
    except Exception:
        return {}


def process_bg(datalist, source, proxy_ip=None):
    s = requests.Session()
    s.mount('http://', HTTPAdapter(max_retries=3))
    s.mount('https://', HTTPAdapter(max_retries=3))
    proxy = proxy_ip
    dl_list = []
    for each in datalist:
        url = f"https://webassets.lowiro.com/{each['bg']}.jpg?v=323"
        local_path = pathlib.Path('./img') / f'{each["bg"]}.jpg'
        logger.info("checking local path %s", local_path.as_posix())
        if not local_path.exists():
            dl_list.append({
                "url": url,
                "song_id": each['song_id']
            })
    for item in dl_list:
        time.sleep(random.uniform(2, 4))
        req = s.get(url=item['url'], headers={
            'User-Agent': UA,
            'Referer': f'https://arcaea.lowiro.com/song_ranking/{source}'
        }, proxies=proxy, timeout=5)
        if req.status_code == 200:
            logger.info("downloading %s from url %s", item['song_id'], item['url'])
            with open(local_path, 'wb') as file:
                file.write(req.content)
        else:
            logger.warning("failed to get %s", item['song_id'])


def get_song_rank(choose, proxy_ip=None):
    if choose not in ('free', 'paid'):
        raise ValueError('song_rank should be free or paid!')
    logger.info("songInfo: getting %s data, using proxy %s", choose, proxy_ip)
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
            logger.info(
                "getting %s data success, processing background", choose)
            process_bg(data['value'], choose, proxy_ip)
            return True, data['value']
        logger.warning("error: %s", data)
        return False, data
    except Exception as ex:
        if data is not None and 'success' in data and data['success']:
            return True, data['value']
        logger.warning("error: %s", ex)
        return False, {
            'error': ex,
            'text': req.text if req is not None else ''
        }


def format_to_string(obj, title, link_url):
    from telebot.formatting import mbold, mlink
    return f"{mbold(mlink(content=title, url=link_url))}"


def main(get_free=True, get_paid=True):
    if not LOCAL_TEST:
        API_TOKEN = os.getenv('TG_BOT_TOKEN')
        if os.getenv('CI', 'false') == 'true' and API_TOKEN is None:
            logger.warning("No bot token set, will not send anything to telegram group")
            tb = None
        else:
            tb = telebot.TeleBot(API_TOKEN)
    else:
        tb = telebot.TeleBot("YOUR_TOKEN")
    d = datetime.datetime.now()
    p = pathlib.Path(f'./{d.year}/{d.month}/{d.day}')
    if not p.exists():
        p.mkdir(parents=True)
    if get_free:
        res, free = get_song_rank('free')
        if res and 'error' not in free:
            logger.info("free data saved")
            with open(p / 'free.json', 'w', encoding='utf-8') as file:
                json.dump(free, file, ensure_ascii=False, indent=2)
            if tb is not None:
                logger.info("send free data to telegram group")
                tb.send_message(chat_id=BOT_CHAT_ID, text=format_to_string(res, "Free Song Ranking", "https://arcaea.lowiro.com/song_ranking/free"))
        else:
            failed = True
            proxy = TEST_PROXY if LOCAL_TEST else get_proxy()
            if proxy:
                logger.info("Using proxy %s for further fetch", proxy)
                res, free = get_song_rank('free', proxy_ip=proxy)
                if res and 'error' not in free:
                    logger.info("free data saved")
                    with open(p / 'free.json', 'w', encoding='utf-8') as file:
                        json.dump(free, file, ensure_ascii=False, indent=2)
                    failed = False
                    if tb is not None:
                        logger.info("send free data to telegram group")
                        tb.send_message(chat_id=BOT_CHAT_ID, text=format_to_string(res, "Free Song Ranking", "https://arcaea.lowiro.com/song_ranking/free"))
                else:
                    logger.fatal(
                        "get free data error! %s(using proxy but get error data)", free)
            else:
                logger.fatal("get free data error! %s(cannot get proxy)", free)
            if failed and os.getenv('CI', 'false') == 'true':
                os.system('echo "FREE_DATA_ERRORED=true" >> "$GITHUB_ENV"')
    if get_paid:
        res2, paid = get_song_rank('paid')
        if res2 and 'error' not in paid:
            logger.info("paid data saved")
            with open(p / 'paid.json', 'w', encoding='utf-8') as file:
                json.dump(paid, file, ensure_ascii=False, indent=2)
            if tb is not None:
                logger.info("send paid data to telegram group")
                tb.send_message(chat_id=BOT_CHAT_ID, text=format_to_string(res, "Paid Song Ranking", "https://arcaea.lowiro.com/en/song_ranking/paid"))
        else:
            failed = True
            proxy = TEST_PROXY if LOCAL_TEST else get_proxy()
            if proxy:
                logger.info("Using proxy %s for further fetch", proxy)
                res, paid = get_song_rank('paid', proxy_ip=proxy)
                if res and 'error' not in free:
                    logger.info("paid data saved")
                    with open(p / 'paid.json', 'w', encoding='utf-8') as file:
                        json.dump(free, file, ensure_ascii=False, indent=2)
                    failed = False
                    if tb is not None:
                        logger.info("send paid data to telegram group")
                        tb.send_message(chat_id=BOT_CHAT_ID, text=format_to_string(res, "Paid Song Ranking", "https://arcaea.lowiro.com/en/song_ranking/paid"))
                else:
                    logger.fatal(
                        "get paid data error! %s(using proxy but get error data)", paid)
            else:
                logger.fatal("get paid data error! %s(cannot get proxy)", paid)
            if failed and os.getenv('CI', 'false') == 'true':
                os.system('echo "PAID_DATA_ERRORED=true" >> "$GITHUB_ENV"')


if __name__ == "__main__":    
    main()
    if os.getenv('CI', 'false') == 'true':
        logger.info('FREE_DATA_ERRORED=%s, PAID_DATA_ERRORED=%s', 
        os.getenv('FREE_DATA_ERRORED'), os.getenv('PAID_DATA_ERRORED'))
