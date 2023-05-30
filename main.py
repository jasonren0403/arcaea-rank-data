# -*- coding: utf8 -*-
import json
import pathlib
import datetime
import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.35"
url_dict = {
    'free': 'https://webapi.lowiro.com/webapi/song/rank/free',
    'paid': 'https://webapi.lowiro.com/webapi/song/rank/paid'
}

def get_proxy():
    # https://github.com/TheSpeedX/PROXY-List
    ip_net = "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt"
    try:
        res = requests.get(ip_net, timeout=5)
        ips = res.text.split('\n')[:30]
        for each in ips:
            try:
                print(f'testing {each}')
                res2 = requests.get('https://arcaea.lowiro.com/', proxies={
                    'http': each
                }, timeout=5)
                if res2.status_code == 200:
                    return {
                        'http': each
                    }
            except Exception:
                pass
    except Exception:
        return {}

def process_bg(datalist, source):
    proxy = get_proxy()
    if proxy:
        print(f"Using proxy {proxy}")
    for each in datalist:
        url = f"https://webassets.lowiro.com/{each['bg']}.jpg?v=323"
        print(f"downloading {each['song_id']} from url {url}")
        local_path = pathlib.Path('./img') / f'{each["bg"]}.jpg'
        if not local_path.exists():
            req = requests.get(url=url, headers={
                'User-Agent': UA,
                'Referer': f'https://arcaea.lowiro.com/song_ranking/{source}'
            }, proxies = proxy,timeout=5)
            if req.status_code==200:
                with open(local_path, 'wb') as file:
                    file.write(req.content)
            else:
                print(f"warning: failed to get {each['song_id']}")


def get_song_rank(choose):
    if choose not in ('free', 'paid'):
        raise ValueError('song_rank should be free or paid!')
    print(f"getting {choose} data")
    url = url_dict.get(choose)
    try:
        proxy = get_proxy()
        if proxy:
            print(f"Using proxy {proxy}")
        req = requests.get(url=url, headers={
            'User-Agent': UA,
            'origin': 'https://arcaea.lowiro.com',
            'referer': 'https://arcaea.lowiro.com/'
        }, proxies = proxy, timeout=5)
        data = req.json()
        if 'success' in data and data['success']:
            process_bg(data['value'], choose)
            return True, data['value']
        return False, data
    except Exception as e:
        return False, {
            'error': e,
            'text': req.text if req is not None else ''
        }

def main():
    res, free = get_song_rank('free')
    res2, paid = get_song_rank('paid')
    d = datetime.datetime.now()
    p = pathlib.Path(f'./{d.year}/{d.month}/{d.day}')
    if not p.exists():
        p.mkdir(parents=True)
    if res:
        with open(p / 'free.json', 'w', encoding='utf-8') as file:
            json.dump(free, file, ensure_ascii=False, indent=2)
    else:
        print(f"get free data error! {free}")
    if res2:
        with open(p / 'paid.json', 'w', encoding='utf-8') as file:
            json.dump(paid, file, ensure_ascii=False, indent=2)
    else:
        print(f"get paid data error! {paid}")
    # print(free)
    # print("------")
    # print(paid)

main()
