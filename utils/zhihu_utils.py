import execjs

from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
js = execjs.compile((_ROOT / 'static' / 'zhihu.js').read_text(encoding='utf-8'), cwd=str(_ROOT))

def get_comment_headers():
    return {
        "accept": "*/*",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "origin": "https://zhuanlan.zhihu.com",
        "referer": "https://zhuanlan.zhihu.com/p/542800387",
        "sec-ch-ua": "\"Microsoft Edge\";v=\"123\", \"Not:A-Brand\";v=\"8\", \"Chromium\";v=\"123\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
        "x-requested-with": "fetch",
        "x-zse-93": "101_3_3.0",
        "x-zse-96": ""
    }

def trans_cookies(cookies):
    return {i.split('=')[0]: '='.join(i.split('=')[1:]) for i in cookies.split('; ')}

def get_x_zse_96(url, params, d_c0):
    er = url +  "?" + "&".join([f"{k}={v}" for k, v in params.items()])
    eo = ""
    ei = {
        "zse93": "101_3_3.0",
        "dc0": d_c0,
        "xZst81": None
    }
    ec = ""
    res = js.call('tv', er, eo, ei, ec)
    x_zse_96 = '2.0_' + res['signature']
    return x_zse_96
