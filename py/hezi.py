# -*- coding: utf-8 -*-
"""
魔法盒子 (l98.cn) Python Spider — 兼容 FongMi/TV (T3) 与 WebHomeTV / PeekPro (T4)
站点: http://l98.cn
本版改动:
  - 移除一级分类「剧迷影视」「歪比影视」「速影TV」
  - 新增内置分支「奇优影院」「趣看看短剧」「麒麟视频」
  - 修复趣看看播放：playerContent 按 "albumId:seq" 格式识别
"""
import sys
import json
import re
import time
import base64
import uuid
import hashlib
import hmac

try:
    import threading
except Exception:
    threading = None

try:
    from urllib.parse import quote
except Exception:
    def quote(s, safe=""):
        return s

sys.path.append('..')

try:
    from base.spider import Spider
except ImportError:
    import requests as _rq
    try:
        import urllib3
        urllib3.disable_warnings()
    except Exception:
        pass

    class Spider(object):
        def fetch(self, url, headers=None, data=None, **kw):
            timeout = kw.pop('timeout', 15)
            if data:
                r = _rq.post(url, headers=headers, data=data, timeout=timeout, verify=False)
            else:
                r = _rq.get(url, headers=headers, timeout=timeout, verify=False)
            r.encoding = 'utf-8'
            return r

        def postJson(self, url, json=None, headers=None, **kw):
            timeout = kw.pop('timeout', 15)
            r = _rq.post(url, headers=headers, json=json, timeout=timeout, verify=False, **kw)
            r.encoding = 'utf-8'
            return r


# ============================================================
# 常量
# ============================================================
HOST = "http://l98.cn"
API_SOURCES = HOST + "/api/tvbox/sources"
API_HOME = HOST + "/api/tvbox/home"
API_CATEGORY = HOST + "/api/tvbox/category"
API_SEARCH = HOST + "/api/search"
API_DETAIL = HOST + "/api/detail"

UA = ("Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36")

SEARCH_ALL = False

SEARCH_ONLY = [
    "source-37dc8f3871",
    "wencai",
    "tv",
    "j4k",
    "source-0ad659640c",
    "hema",
]

DIRECT_PLAY = True
CAT_MIN_ITEMS = 40
CAT_PAGES = 3
CAT_MAX = 120
CAT_TIMEOUT = 10
REC_TIMEOUT = 8
REC_WAIT = 3.0
SEARCH_WORKERS = 12
SEARCH_TIMEOUT = 5
SEARCH_PER_SRC = 20
SEARCH_MAX = 200
SEARCH_LIMIT = 20
SEARCH_STRICT = "auto"
DETAIL_FALLBACK = True
FALLBACK_TRY = 4
CACHE_TTL = 300

SOURCES = [
    {"key": "hema", "name": "河马短剧", "type": "py"},
    {"key": "yunyun", "name": "芸芸音乐", "type": "js"},
    {"key": "source-37dc8f3871", "name": "独播库", "type": "py"},
    {"key": "source-8ee56df12f", "name": "歪比影视", "type": "py"},
    {"key": "source-b5552441f5", "name": "云端影视", "type": "py"},
    {"key": "source-681f32793f", "name": "金牌影视", "type": "py"},
    {"key": "tv", "name": "爱瓜TV", "type": "py"},
    {"key": "wencai", "name": "文才影视T3", "type": "py"},
    {"key": "jumi", "name": "剧迷影视", "type": "py"},
    {"key": "j4k", "name": "极影4K", "type": "js"},
    {"key": "source-4eb17c91b4", "name": "三秋影视", "type": "py"},
    {"key": "source-0ad659640c", "name": "泥巴影视", "type": "py"},
    {"key": "source-e2baa3717e", "name": "网易影像", "type": "py"},
    {"key": "source-05849e86e9", "name": "飞流视频", "type": "py"},
    {"key": "jd4k", "name": "JD4K", "type": "js"},
    {"key": "source-90e25e2716", "name": "布布影视", "type": "py"},
    {"key": "source-aa4f0ed30b", "name": "奇优动漫", "type": "py"},
    {"key": "source-d1867dcc71", "name": "悟圣短剧", "type": "py"},
    {"key": "source-cd6cd838d1", "name": "喜福短剧", "type": "py"},
    {"key": "source-c6eef9d264", "name": "星芽短剧", "type": "py"},
    {"key": "source-984a66ab13", "name": "央视卫视", "type": "py"},
    {"key": "source-b3e87ad824", "name": "西饭短剧", "type": "py"},
    {"key": "source-616fbcbf9e", "name": "瓜子APP", "type": "py"},
    {"key": "source-d6c318599c", "name": "蛋蛋奇", "type": "py"},
    {"key": "source-cb4888cc81", "name": "剧OK影视", "type": "py"},
]

SUB_CLASS = {
    "hema": [
        {"n": "甜宠", "v": "462"}, {"n": "古装仙侠", "v": "1102"},
        {"n": "现代言情", "v": "1145"}, {"n": "青春", "v": "1170"},
        {"n": "豪门恩怨", "v": "585"}, {"n": "逆袭", "v": "417-464"},
        {"n": "重生", "v": "439-465"}, {"n": "系统", "v": "1159"},
        {"n": "总裁", "v": "1147"}, {"n": "职场商战", "v": "943"},
    ],
    "yunyun": [
        {"n": "推荐歌单", "v": "recommend"}, {"n": "排行榜", "v": "toplist"},
        {"n": "热门歌单", "v": "hot"}, {"n": "热门歌手", "v": "artist"},
    ],
    "source-37dc8f3871": [
        {"n": "连续剧", "v": "2"}, {"n": "综艺", "v": "3"},
        {"n": "电影", "v": "1"}, {"n": "动漫", "v": "4"},
    ],
    "source-b5552441f5": [],
    "source-681f32793f": [
        {"n": "电影", "v": "1"}, {"n": "电视剧", "v": "2"},
        {"n": "综艺", "v": "3"}, {"n": "动漫", "v": "4"},
    ],
    "tv": [
        {"n": "电视剧", "v": "2"}, {"n": "电影", "v": "1"},
        {"n": "综艺", "v": "3"}, {"n": "动漫", "v": "4"},
        {"n": "纪录片", "v": "32"},
    ],
    "wencai": [
        {"n": "电影", "v": "1"}, {"n": "电视剧", "v": "2"},
        {"n": "综艺", "v": "3"}, {"n": "动漫", "v": "4"}, {"n": "短剧", "v": "88"},
    ],
    "j4k": [
        {"n": "电影", "v": "1"}, {"n": "剧集", "v": "2"}, {"n": "综艺", "v": "3"},
        {"n": "动漫", "v": "4"}, {"n": "短剧", "v": "29"}, {"n": "少儿", "v": "25"},
        {"n": "记录", "v": "31"}, {"n": "学习", "v": "32"},
    ],
    "source-4eb17c91b4": [
        {"n": "电影", "v": "电影"}, {"n": "剧集", "v": "剧集"},
        {"n": "动漫", "v": "动漫"}, {"n": "综艺", "v": "综艺"},
    ],
    "source-0ad659640c": [
        {"n": "电影", "v": "1"}, {"n": "电视剧", "v": "2"},
        {"n": "综艺", "v": "3"}, {"n": "动漫", "v": "4"},
    ],
    "source-e2baa3717e": [
        {"n": "电影", "v": "movie"}, {"n": "纪录片", "v": "doc"},
        {"n": "动画片", "v": "ani"}, {"n": "珍贵史料", "v": "his"},
    ],
    "source-05849e86e9": [
        {"n": "电影", "v": "151438147786375168"},
        {"n": "电视剧", "v": "151438147794763777"},
        {"n": "综艺", "v": "151438147807346691"},
        {"n": "动漫", "v": "151438147807346690"},
        {"n": "体育", "v": "151438147807346693"},
        {"n": "电影解说", "v": "204814944317734918"},
        {"n": "短剧", "v": "331153971999670710"},
    ],
    "jd4k": [
        {"n": "电影", "v": "1"}, {"n": "剧集", "v": "2"}, {"n": "综艺", "v": "3"},
        {"n": "动漫", "v": "4"}, {"n": "短剧", "v": "29"}, {"n": "少儿", "v": "25"},
        {"n": "记录", "v": "31"}, {"n": "学习", "v": "32"},
    ],
    "source-90e25e2716": [
        {"n": "电影", "v": "电影"}, {"n": "剧集", "v": "剧集"},
        {"n": "动漫", "v": "动漫"}, {"n": "综艺", "v": "综艺"},
    ],
    "source-aa4f0ed30b": [
        {"n": "电影", "v": "1"}, {"n": "电视剧", "v": "2"},
        {"n": "动漫", "v": "3"}, {"n": "综艺", "v": "4"}, {"n": "午夜", "v": "6"},
    ],
    "source-d1867dcc71": [
        {"n": "甜宠", "v": "1287"}, {"n": "逆袭", "v": "1288"},
        {"n": "热血", "v": "1289"}, {"n": "现代", "v": "1290"}, {"n": "古代", "v": "1291"},
    ],
    "source-cd6cd838d1": [
        {"n": "爽剧", "v": "3"}, {"n": "甜宠", "v": "6"}, {"n": "逆袭", "v": "5"},
        {"n": "现代言情", "v": "1"}, {"n": "都市", "v": "4"}, {"n": "玄幻", "v": "23"},
        {"n": "古代言情", "v": "16"},
    ],
    "source-c6eef9d264": [
        {"n": "剧场", "v": "1"}, {"n": "新剧", "v": "3"}, {"n": "热播", "v": "2"},
        {"n": "星选", "v": "7"}, {"n": "阳光", "v": "5"},
    ],
    "source-984a66ab13": [{"n": "直播", "v": "25"}],
    "source-b3e87ad824": [
        {"n": "都市", "v": "都市"}, {"n": "甜宠", "v": "甜宠"}, {"n": "逆袭", "v": "逆袭"},
        {"n": "战神", "v": "战神"}, {"n": "古装", "v": "古装"}, {"n": "穿越", "v": "穿越"},
        {"n": "萌宝", "v": "萌宝"},
    ],
    "source-616fbcbf9e": [
        {"n": "热门", "v": "hot"}, {"n": "动漫", "v": "4"}, {"n": "漫剧", "v": "74"},
        {"n": "电影", "v": "1"}, {"n": "国产剧", "v": "2"}, {"n": "短剧", "v": "64"},
        {"n": "综艺", "v": "3"}, {"n": "海外剧", "v": "overseas"},
        {"n": "儿童", "v": "children"},
    ],
    "source-d6c318599c": [
        {"n": "首页", "v": "home"}, {"n": "电影", "v": "dianying"},
        {"n": "剧集", "v": "juji"}, {"n": "综艺", "v": "zongyi"},
        {"n": "动漫", "v": "dongman"}, {"n": "今日更新", "v": "new"}, {"n": "热榜", "v": "hot"},
    ],
    "source-cb4888cc81": [
        {"n": "首页", "v": "home"}, {"n": "电影", "v": "movie"},
        {"n": "电视剧", "v": "tv"}, {"n": "综艺", "v": "variety"},
        {"n": "动漫", "v": "anime"}, {"n": "热榜", "v": "ranking"},
        {"n": "短剧", "v": "short"}, {"n": "听歌", "v": "music"},
    ],
}

SOURCE_API = {}
for _s in SOURCES:
    SOURCE_API[_s["key"]] = "tvbox-%s://%s" % (_s["type"], _s["key"])
SOURCE_NAME = dict((_s["key"], _s["name"]) for _s in SOURCES)

# 一级分类（已删除 速影TV，新增 麒麟视频）
CLASSES = [
    {"type_name": "影视推荐", "type_id": "s_rec"},
    {"type_name": "芸芸音乐", "type_id": "s_yunyun"},
    {"type_name": "独播库", "type_id": "s_source-37dc8f3871"},
    {"type_name": "麒麟视频", "type_id": "s_qilin"},
    {"type_name": "奇优影院", "type_id": "s_qiyou"},
    {"type_name": "趣看看短剧", "type_id": "s_qukkan"},
]

REC_KEY = "rec"
REC_TID = "s_rec"

RECOMMEND_SOURCES = [
    "hema", "wencai", "tv", "j4k",
    "source-37dc8f3871", "source-0ad659640c",
]

REC_PER_SRC = 10
REC_LIMIT = 20

# 内置分支 key（已移除 suying）
EXTRA_KEYS = ("qiyou", "qukkan", "qilin")

# 麒麟视频 分类（参考 麒麟视频.py 的 24 个分类）
QILIN_CATS = [
    {"n": "电影", "v": "1"}, {"n": "电视剧", "v": "2"}, {"n": "短剧", "v": "3"},
    {"n": "动漫", "v": "4"}, {"n": "综艺", "v": "5"}, {"n": "内地剧", "v": "6"},
    {"n": "港台剧", "v": "7"}, {"n": "日韩剧", "v": "8"}, {"n": "欧美剧", "v": "9"},
    {"n": "动作片", "v": "10"}, {"n": "恐怖片", "v": "11"}, {"n": "科幻片", "v": "12"},
    {"n": "战争片", "v": "13"}, {"n": "爱情片", "v": "14"}, {"n": "喜剧片", "v": "15"},
    {"n": "剧情片", "v": "16"}, {"n": "记录片", "v": "17"}, {"n": "内地番", "v": "18"},
    {"n": "日韩番", "v": "19"}, {"n": "港台番", "v": "20"}, {"n": "欧美番", "v": "21"},
    {"n": "泰剧", "v": "22"}, {"n": "漫剧", "v": "23"}, {"n": "有声漫剧", "v": "24"},
]

_QILIN_YEARS = [{"n": "全部", "v": ""}]
for _y in range(2026, 1999, -1):
    _QILIN_YEARS.append({"n": str(_y), "v": str(_y)})

_QILIN_AREAS = [{"n": "全部", "v": ""}] + [
    {"n": a, "v": a} for a in
    ["大陆", "香港", "台湾", "美国", "日本", "韩国", "英国", "法国", "德国",
     "泰国", "印度", "俄罗斯", "加拿大", "澳大利亚", "新加坡"]
]

FILTERS = {}
for _c in CLASSES:
    _tid = _c["type_id"]
    if _tid == REC_TID:
        FILTERS[_tid] = [{"key": "src", "name": "来源", "value": [{"n": "全部", "v": ""}] + [{"n": SOURCE_NAME.get(k, k), "v": k} for k in RECOMMEND_SOURCES]}]
        continue
    _k = _tid[2:]
    if _k == "qiyou":
        FILTERS[_tid] = [{"key": "tid", "name": "分类", "value": [
            {"n": "电影", "v": "1"}, {"n": "电视剧", "v": "2"},
            {"n": "动漫", "v": "3"}, {"n": "综艺", "v": "4"},
        ]}]
    elif _k == "qukkan":
        FILTERS[_tid] = [
            {"key": "tid", "name": "分类", "value": [
                {"n": "全部短剧", "v": "all"},
                {"n": "现代言情", "v": "1"}, {"n": "爽剧", "v": "3"}, {"n": "都市", "v": "4"},
                {"n": "逆袭", "v": "5"}, {"n": "甜宠", "v": "6"}, {"n": "女强", "v": "7"},
                {"n": "虐恋", "v": "13"}, {"n": "古代言情", "v": "16"}, {"n": "玄幻", "v": "23"},
            ]},
            {"key": "by", "name": "排序", "value": [
                {"n": "综合", "v": ""}, {"n": "最新", "v": "time"}, {"n": "最热", "v": "hot"},
            ]},
        ]
    elif _k == "qilin":
        _qv = []
        for _qc in QILIN_CATS:
            _qv.append(_qc)
        FILTERS[_tid] = [
            {"key": "tid", "name": "分类", "value": _qv},
            {"key": "year", "name": "年份", "value": _QILIN_YEARS},
            {"key": "area", "name": "地区", "value": _QILIN_AREAS},
        ]
    else:
        _vals = [{"n": "推荐", "v": ""}] + list(SUB_CLASS.get(_k, []))
        FILTERS[_tid] = [{"key": "tid", "name": "分类", "value": _vals}]

    if not isinstance(FILTERS[_tid][0].get("value"), list):
        FILTERS[_tid] = [{"key": "tid", "name": "分类", "value": [{"n": "推荐", "v": ""}]}]


# ============================================================
# 内置分支：奇优影院 (qiyou05.com)
# ============================================================
class _QiYou(object):
    def __init__(self):
        self.site_url = "http://www.qiyou05.com"
        self.headers = {
            "User-Agent": UA,
            "Referer": self.site_url,
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        self._cache = {}

    def _get(self, url, method="GET", data=None, timeout=10):
        import requests
        try:
            if method.upper() == "POST":
                r = requests.post(url, headers=self.headers, data=data, timeout=timeout, verify=False)
            else:
                r = requests.get(url, headers=self.headers, timeout=timeout, verify=False)
            r.encoding = "utf-8"
            return r
        except Exception:
            return None

    def _card(self, item_html):
        vod_id = re.search(r'href="(/view/\d+\.html)"', item_html)
        vod_name = re.search(r'title="([^"]+)"', item_html)
        vod_pic = re.search(r'data-original="([^"]+)"', item_html)
        vod_remarks = re.search(r'<span class="pic-text text-right">([^<]*)</span>', item_html)
        if not (vod_id and vod_name and vod_pic):
            return None
        pic = vod_pic.group(1)
        if pic.startswith("//"):
            pic = "https:" + pic
        elif not pic.startswith(("http://", "https://")):
            pic = self.site_url + pic
        return {
            "vod_id": "qiyou@" + self.site_url + vod_id.group(1),
            "vod_name": vod_name.group(1).strip(),
            "vod_pic": pic,
            "vod_remarks": vod_remarks.group(1).strip() if vod_remarks else "",
        }

    def _list_from_html(self, html):
        out = []
        for m in re.finditer(r'<li class="col-md-\d+ col-sm-4 col-xs-3">(.*?)</li>', html, re.S):
            c = self._card(m.group(1))
            if c:
                out.append(c)
        if not out:
            for m in re.finditer(r'<li class="active[^"]*clearfix">(.*?)</li>', html, re.S):
                c = self._card(m.group(1))
                if c:
                    out.append(c)
        return out

    def category(self, tid, pg):
        tid = tid or "1"
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        if pg <= 1:
            url = "%s/list/%s.html" % (self.site_url, tid)
        else:
            url = "%s/list/%s_%d.html" % (self.site_url, tid, pg)
        ck = ("cat", tid, pg)
        cached = self._cache.get(ck)
        if cached and time.time() - cached[0] < CACHE_TTL:
            items = cached[1]
        else:
            res = self._get(url)
            items = self._list_from_html(res.text) if res and res.ok else []
            self._cache[ck] = (time.time(), items)
        return {
            "list": items, "page": pg,
            "pagecount": pg + 1 if len(items) >= 24 else pg,
            "limit": 24, "total": 9999,
        }

    def detail(self, vod_id):
        res = self._get(vod_id)
        if not res or not res.ok:
            return {"list": []}
        html = res.text
        t = re.search(r'<h1 class="line1">([^<]+)</h1>', html)
        pic = re.search(r'<img class="lazyload" data-original="([^"]+)"', html)
        rm = re.search(r'<span class="pic-text text-right">([^<]*)</span>', html)
        dm = re.search(r'<p class="desc[^"]*"><span class="left text-muted">简介：</span>(.*?)<a href="#desc">', html, re.S)
        content = re.sub(r'<[^>]+>', '', dm.group(1)).strip() if dm else ""
        pf, pu = [], []
        for sid, sname in re.findall(r'<a data-toggle="tab" href="#(down\d+)">([^<]+)</a>', html):
            sm = re.search(r'id="' + sid + r'"[^>]*>.*?<ul class="stui-content__playlist clearfix">(.*?)</ul>', html, re.S)
            if not sm:
                continue
            eps = ["%s$%s" % (n.strip(), (self.site_url + u) if u.startswith("/") else u)
                   for u, n in re.findall(r'<a href="(/play/[^"]+)" title="([^"]+)">', sm.group(1))]
            if eps:
                pf.append(sname.strip())
                pu.append("#".join(eps))
        if not pf:
            eps = ["%s$%s" % (n.strip(), (self.site_url + u) if u.startswith("/") else u)
                   for u, n in re.findall(r'<a href="(/play/[^"]+)" title="([^"]+)">', html)]
            if eps:
                pf.append("奇优线路")
                pu.append("#".join(eps))
        if not pf:
            return {"list": []}
        p = pic.group(1) if pic else ""
        if p.startswith("//"):
            p = "https:" + p
        return {"list": [{
            "vod_id": "qiyou@" + vod_id,
            "vod_name": t.group(1).strip() if t else "未知名称",
            "vod_pic": p,
            "vod_remarks": rm.group(1).strip() if rm else "",
            "vod_content": content,
            "vod_play_from": "$$$".join(pf),
            "vod_play_url": "$$$".join(pu),
        }]}

    def search(self, key, pg=1):
        res = self._get(self.site_url + "/search.php", method="POST", data={"searchword": key})
        items = self._list_from_html(res.text) if res and res.ok else []
        return {"list": items, "page": 1, "pagecount": 1, "limit": len(items) or 20, "total": len(items)}

    def player(self, play_url):
        from urllib.parse import urlparse
        res = self._get(play_url)
        if not res or not res.ok:
            return {"parse": 1, "url": play_url, "header": self.headers}
        html = res.text
        im = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.S)
        if im:
            iu = im.group(1)
            if iu.startswith("//"):
                iu = "https:" + iu
            elif not iu.startswith(("http://", "https://")):
                iu = self.site_url + iu
            ires = self._get(iu)
            if ires and ires.ok:
                ihtml = ires.text
                uv = re.search(r'const\s+Url\s*=\s*["\']([^"\']+)["\']', ihtml)
                sv = re.search(r'const\s+Sign\s*=\s*["\']([^"\']+)["\']', ihtml)
                fv = re.search(r'const\s+From\s*=\s*["\']([^"\']+)["\']', ihtml)
                if uv and sv and fv:
                    pu = urlparse(iu)
                    api = "%s://%s/player/api.php?url=%s&sign=%s&t=%s" % (
                        pu.scheme, pu.netloc, uv.group(1), sv.group(1), fv.group(1))
                    ah = {"User-Agent": self.headers["User-Agent"], "Referer": iu}
                    try:
                        import requests
                        ar = requests.get(api, headers=ah, timeout=10, verify=False)
                        if ar.ok and ar.json().get("code") == 200 and ar.json().get("url"):
                            return {"parse": 0, "url": ar.json()["url"], "header": self.headers}
                    except Exception:
                        pass
                for pat in (r'(https?://[^"\']+\.m3u8[^"\']*)', r'(https?://[^"\']+\.mp4[^"\']*)'):
                    m = re.search(pat, ihtml)
                    if m:
                        return {"parse": 0, "url": m.group(1), "header": self.headers}
            return {"parse": 1, "url": iu, "header": self.headers}
        for pat in (r"(https?://[^\"\']+\.m3u8)", r"(https?://[^\"\']+\.mp4)"):
            m = re.search(pat, html)
            if m:
                return {"parse": 0, "url": m.group(1), "header": self.headers}
        return {"parse": 1, "url": play_url, "header": self.headers}


# ============================================================
# 内置分支：趣看看短剧 (阿里云 VOD)
# ============================================================
def _aliyun_encode(v):
    from urllib.parse import quote as _q
    v = _q(str(v), safe="!~*'()")
    return v.replace("+", "%2B").replace("*", "%2A").replace("%7E", "~")


def _aliyun_sign(params, secret):
    canon = "&".join("%s=%s" % (_aliyun_encode(k), _aliyun_encode(v))
                     for k, v in sorted(params.items()))
    sts = "GET&" + _aliyun_encode("/") + "&" + _aliyun_encode(canon)
    d = hmac.new((secret + "&").encode(), sts.encode(), hashlib.sha1).digest()
    return base64.b64encode(d).decode()


def _decode_playauth(auth):
    try:
        raw = base64.b64decode(auth + "=" * (-len(auth) % 4))
        data = json.loads(raw)
        return {
            "AccessKeyId": data["AccessKeyId"],
            "AccessKeySecret": data["AccessKeySecret"],
            "SecurityToken": data["SecurityToken"],
            "AuthInfo": data["AuthInfo"],
            "Region": data["Region"],
            "VideoId": data["VideoMeta"]["VideoId"],
        }
    except Exception:
        return None


class _QuKanKan(object):
    API = "https://minidrama-api.contentchina.com"
    HOST = "https://minidrama.contentchina.com"
    UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
          "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")

    def __init__(self):
        import requests
        self.s = requests.Session()
        self.s.headers.update({
            "User-Agent": self.UA,
            "Accept": "application/json, text/plain, */*",
            "Referer": self.HOST + "/",
        })
        self.s.verify = False
        self._play_cache = {}
        self._detail_cache = {}

    def _gj(self, url, params=None, timeout=5):
        try:
            r = self.s.get(url, params=params, timeout=timeout)
            if r.status_code == 200:
                d = r.json()
                if d.get("code") == 200:
                    return d.get("data")
        except Exception:
            pass
        return None

    def _card(self, it):
        total = it.get("total") or 0
        return {
            "vod_id": "qukkan@" + str(it.get("albumId") or ""),
            "vod_name": it.get("title") or "",
            "vod_pic": it.get("coverUrl") or "",
            "vod_remarks": ("全%s集" % total) if total else "",
        }

    def category(self, tid, pg, by=""):
        try:
            pg = max(1, int(pg or 1))
        except Exception:
            pg = 1
        params = {"pageSize": 100, "currentPage": pg}
        if tid and tid != "all":
            params["filterCategories"] = tid
        data = self._gj(self.API + "/web/v1/drama/list", params=params)
        if not data:
            return {"list": [], "page": pg, "pagecount": 1, "limit": 36, "total": 0}
        items = data.get("data") or []
        if by == "hot":
            items.sort(key=lambda x: int(x.get("hot") or 0), reverse=True)
        elif by == "time":
            items.sort(key=lambda x: int(x.get("updateTime") or 0), reverse=True)
        pag = data.get("pagination") or {}
        return {
            "list": [self._card(i) for i in items],
            "page": pg,
            "pagecount": max(1, pag.get("totalPages") or 1),
            "limit": 36,
            "total": pag.get("total") or len(items),
        }

    def detail(self, album_id):
        cached = self._detail_cache.get(album_id)
        if cached and time.time() - cached[0] < 600:
            return cached[1]
        data = self._gj(self.API + "/web/v1/drama/detail", params={"albumId": album_id})
        if not data:
            return {"list": []}
        serial = data.get("serialData") or {}
        eps = ["第%s集$%s:%s" % (ep.get("sequence"), album_id, ep.get("sequence"))
               for ep in (data.get("episodeList") or []) if ep.get("sequence")]
        result = {"list": [{
            "vod_id": "qukkan@" + album_id,
            "vod_name": serial.get("title") or "剧集%s" % album_id,
            "vod_pic": serial.get("coverUrl") or "",
            "type_name": ",".join(serial.get("categories") or []),
            "vod_remarks": ("全%s集" % serial.get("total")) if serial.get("total") else "",
            "vod_actor": ",".join(serial.get("leadActor") or []),
            "vod_content": (serial.get("introduction") or "").strip(),
            "vod_play_from": "趣看看短剧",
            "vod_play_url": "#".join(eps),
        }]}
        self._detail_cache[album_id] = (time.time(), result)
        return result

    def search(self, key, pg=1):
        try:
            pg = max(1, int(pg or 1))
        except Exception:
            pg = 1
        data = self._gj(self.API + "/web/v1/drama/list",
                        params={"pageSize": 100, "currentPage": pg})
        if not data:
            return {"list": [], "page": pg, "pagecount": 1, "limit": 36, "total": 0}
        hits = [self._card(i) for i in (data.get("data") or []) if key in (i.get("title") or "")]
        pag = data.get("pagination") or {}
        return {
            "list": hits, "page": pg,
            "pagecount": max(1, pag.get("totalPages") or 1),
            "limit": 36, "total": pag.get("total") or 0,
        }

    def player(self, play_id):
        album_id, seq = None, None
        parts = str(play_id).split(":")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            album_id, seq = parts
        if not album_id:
            return {"parse": 0, "playUrl": "", "url": ""}
        ck = "%s:%s" % (album_id, seq)
        c = self._play_cache.get(ck)
        if c and time.time() - c[0] < 1800:
            url = c[1]
        else:
            url = self._resolve(album_id, seq)
            if url:
                self._play_cache[ck] = (time.time(), url)
        if not url:
            return {"parse": 1, "playUrl": "", "url": ""}
        return {
            "parse": 0, "playUrl": "", "url": url,
            "header": {"User-Agent": self.UA, "Referer": self.HOST + "/", "Origin": self.HOST},
        }

    def _resolve(self, album_id, seq):
        try:
            auth = self._gj(self.API + "/web/v1/drama/play_auth",
                            params={"albumId": album_id, "seq": seq})
            if not auth or not auth.get("playAuth"):
                return ""
            info = _decode_playauth(auth["playAuth"])
            if not info:
                return ""
            params = {
                "AccessKeyId": info["AccessKeyId"],
                "Action": "GetPlayInfo",
                "VideoId": info["VideoId"],
                "Formats": "mp4",
                "AuthTimeout": 3600,
                "SecurityToken": info["SecurityToken"],
                "Format": "JSON",
                "Version": "2017-03-21",
                "SignatureMethod": "HMAC-SHA1",
                "SignatureVersion": "1.0",
                "SignatureNonce": str(uuid.uuid4()),
                "Channel": "HTML5",
                "AuthInfo": info["AuthInfo"],
            }
            params["Signature"] = _aliyun_sign(params, info["AccessKeySecret"])
            query = "&".join("%s=%s" % (_aliyun_encode(k), _aliyun_encode(v))
                             for k, v in params.items())
            r = self.s.get("https://vod.%s.aliyuncs.com/?%s" % (info["Region"], query), timeout=4)
            plays = r.json().get("PlayInfoList", {}).get("PlayInfo") or []
            if plays:
                plays.sort(key=lambda p: int(p.get("Height") or 0), reverse=True)
                return plays[0].get("PlayURL") or ""
        except Exception:
            pass
        return ""


# ============================================================
# 内置分支：麒麟视频 (qlys.cc，苹果CMS：网页列表 + API详情/搜索)
# ============================================================
class _QiLin(object):
    SITE = "https://www.qlys.cc"
    API = "https://www.qlys.cc/api.php/provide/vod/"
    UA = ("Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/118.0.0.0 Mobile Safari/537.36")

    def __init__(self):
        import requests
        self.s = requests.Session()
        self.s.headers.update({
            "User-Agent": self.UA,
            "Referer": self.SITE + "/",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        self.s.verify = False
        self._cache = {}

    def _get(self, url, timeout=10):
        try:
            r = self.s.get(url, timeout=timeout, verify=False)
            r.encoding = "utf-8"
            return r
        except Exception:
            return None

    def _gj(self, url, timeout=8):
        try:
            r = self._get(url, timeout)
            if r and r.ok:
                return r.json()
        except Exception:
            pass
        return None

    def _cache_get(self, key, ttl):
        c = self._cache.get(key)
        if c and time.time() - c[0] < ttl:
            return c[1]
        return None

    def _cache_put(self, key, val):
        if threading:
            try:
                with threading.Lock():
                    self._cache[key] = (time.time(), val)
            except Exception:
                self._cache[key] = (time.time(), val)
        else:
            self._cache[key] = (time.time(), val)

    # ---- 分类列表：网页解析 ----
    def category(self, tid, pg, year="", area=""):
        tid = tid or "1"
        try:
            pg = max(1, int(pg or 1))
        except Exception:
            pg = 1
        ck = ("cat", tid, pg, year, area)
        cached = self._cache_get(ck, CACHE_TTL)
        if cached is not None:
            return cached
        fp = ""
        if year:
            fp += "/year/%s" % year
        if area:
            fp += "/area/%s" % quote(str(area))
        url = "%s/index.php/vod/type/id/%s%s/page/%d.html" % (self.SITE, tid, fp, pg)
        res = self._get(url)
        items = []
        pagecount = pg
        if res and res.ok:
            html = res.text
            for m in re.finditer(r'<div class="vod-item">(.*?)</a>\s*</div>', html, re.S):
                blk = m.group(1)
                vid = re.search(r'href="/index\.php/vod/detail/id/(\d+)\.html"', blk)
                name = re.search(r'title="([^"]+)"', blk)
                pic = re.search(r'<img[^>]+src="([^"]+)"', blk)
                rmk = re.search(r'<span class="remarks">([^<]+)</span>', blk)
                if not (vid and name):
                    continue
                p = pic.group(1) if pic else ""
                if p.startswith("//"):
                    p = "https:" + p
                elif p and not p.startswith(("http://", "https://")):
                    p = self.SITE + (p if p.startswith("/") else "/" + p)
                items.append({
                    "vod_id": "qilin@" + vid.group(1),
                    "vod_name": name.group(1).strip(),
                    "vod_pic": p,
                    "vod_remarks": rmk.group(1).strip() if rmk else "",
                })
            tail = re.search(r'title="尾页"', html)
            if tail:
                nums = [int(x) for x in re.findall(r'/page/(\d+)\.html', html)]
                if nums:
                    pagecount = max(nums)
        result = {"list": items, "page": pg, "pagecount": max(1, pagecount),
                  "limit": 30, "total": 9999}
        if items:
            self._cache_put(ck, result)
        return result

    # ---- 详情：走 API ----
    def detail(self, vid):
        vid = str(vid)
        ck = ("detail", vid)
        cached = self._cache_get(ck, CACHE_TTL)
        if cached is not None:
            return cached
        data = self._gj("%s?ac=detail&ids=%s" % (self.API, vid))
        if not data or not data.get("list"):
            return {"list": []}
        it = data["list"][0]
        play_from = it.get("vod_play_from", "") or "麒麟线路"
        play_url = it.get("vod_play_url", "") or ""
        # 对齐线路、剔除空线路
        if play_url:
            fs = play_from.split("$$$")
            us = play_url.split("$$$")
            if len(fs) != len(us):
                n = min(len(fs), len(us))
                fs, us = fs[:n], us[:n]
            kf, ku = [], []
            for f, u in zip(fs, us):
                if u and "$" in u:
                    kf.append(f)
                    ku.append(u)
            play_from = "$$$".join(kf) if kf else "麒麟线路"
            play_url = "$$$".join(ku)
        if not play_url:
            return {"list": []}
        content = re.sub(r'<[^>]+>', '', it.get("vod_content", "") or "").strip()
        result = {"list": [{
            "vod_id": "qilin@" + vid,
            "vod_name": it.get("vod_name", "") or "未知名称",
            "vod_pic": it.get("vod_pic", "") or "",
            "vod_remarks": it.get("vod_remarks", "") or "",
            "type_name": it.get("type_name", "") or "麒麟视频",
            "vod_year": str(it.get("vod_year", "") or ""),
            "vod_area": it.get("vod_area", "") or "",
            "vod_actor": it.get("vod_actor", "") or "",
            "vod_director": it.get("vod_director", "") or "",
            "vod_content": content[:500],
            "vod_play_from": play_from,
            "vod_play_url": play_url,
        }]}
        self._cache_put(ck, result)
        return result

    # ---- 搜索：走 API ----
    def search(self, key, pg=1):
        try:
            pg = max(1, int(pg or 1))
        except Exception:
            pg = 1
        data = self._gj("%s?ac=detail&wd=%s&pg=%d" % (self.API, quote(key or ""), pg))
        items = []
        pagecount = pg
        if data and data.get("list"):
            for it in data["list"]:
                pic = it.get("vod_pic", "") or ""
                if pic.startswith("//"):
                    pic = "https:" + pic
                items.append({
                    "vod_id": "qilin@" + str(it.get("vod_id", "")),
                    "vod_name": it.get("vod_name", "") or "",
                    "vod_pic": pic,
                    "vod_remarks": it.get("vod_remarks", "") or "",
                })
            pagecount = int(data.get("pagecount") or pg)
        return {"list": items, "page": pg, "pagecount": max(1, pagecount),
                "limit": 30, "total": int(data.get("total") or 0) if data else 0}

    # ---- 播放：m3u8 直链 ----
    def player(self, play_url):
        u = str(play_url).split("$")[-1].strip()
        if not u:
            return {"parse": 0, "playUrl": "", "url": ""}
        is_m3u8 = ".m3u8" in u.lower()
        return {
            "parse": 0, "playUrl": "", "url": u,
            "header": {"User-Agent": self.UA, "Referer": self.SITE + "/"},
            "format": "application/x-mpegURL" if is_m3u8 else "",
            "contentType": "application/x-mpegURL" if is_m3u8 else "",
        }


# ============================================================
# Spider 主类
# ============================================================
class Spider(Spider):
    def getName(self):
        return "魔法盒子"

    def init(self, extend=""):
        self.extend = "" if isinstance(extend, list) else (extend or "")
        self.header = self._default_header()
        if threading:
            self._lock = threading.Lock()
        self._multi_source = False
        self._home_cache = {}
        self._cat_cache = {}
        self._src_cache = {}
        self._search_cache = {}
        self._page_size = {}
        self._page_steps = {}
        self._seen = {}
        self._qiyou = _QiYou()
        self._qukkan = _QuKanKan()
        self._qilin = _QiLin()

    # ===== 网络工具 =====
    def _default_header(self):
        return {
            "User-Agent": UA,
            "Referer": HOST + "/",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": HOST,
        }

    def _rsp_text(self, rsp):
        try:
            t = rsp.text
            if t:
                return t
        except Exception:
            pass
        try:
            raw = rsp.read() if hasattr(rsp, "read") else rsp.content
            if isinstance(raw, bytes):
                return raw.decode("utf-8", "ignore")
            return str(raw or "")
        except Exception:
            pass
        try:
            return str(rsp)
        except Exception:
            return ""

    def _parse_json_rsp(self, rsp):
        text = self._rsp_text(rsp)
        if not text:
            return None
        try:
            return json.loads(text)
        except Exception:
            return None

    def _urllib_post(self, url, body, headers, timeout):
        import urllib.request
        req = urllib.request.Request(url, data=body, method="POST")
        for k, v in (headers or {}).items():
            try:
                req.add_header(str(k), str(v))
            except Exception:
                pass
        return urllib.request.urlopen(req, timeout=timeout)

    def _is_guard(self, data):
        try:
            d = (data or {}).get("data")
            if isinstance(d, dict):
                for c in (d.get("class") or []):
                    if isinstance(c, dict) and str(c.get("type_id")) == "guard":
                        return True
                if d.get("vod_name") == "资源维护中":
                    return True
            elif isinstance(d, list):
                for x in d:
                    if isinstance(x, dict) and x.get("vod_name") == "资源维护中":
                        return True
        except Exception:
            pass
        return False

    def _post_once(self, url, payload, timeout, deadline=None):
        try:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        except Exception:
            return None
        headers = dict(getattr(self, "header", None) or self._default_header())
        attempts = []
        if hasattr(self, "postJson"):
            attempts.append(lambda t: self.postJson(url, json=payload, headers=headers, timeout=t))
        if hasattr(self, "post"):
            attempts.append(lambda t: self.post(url, json=payload, headers=headers, timeout=t))
            attempts.append(lambda t: self.post(url, data=body, headers=headers, timeout=t))
        attempts.append(lambda t: self._urllib_post(url, body, headers, t))
        if hasattr(self, "fetch"):
            attempts.append(lambda t: self.fetch(url, headers=headers, data=body, timeout=t))
            attempts.append(lambda t: self.fetch(url, headers=headers, data=body))
        fallback = None
        for fn in attempts:
            if deadline:
                left = deadline - time.time()
                if left < 0.5:
                    break
                t = max(1.0, min(timeout, left))
            else:
                t = timeout
            try:
                rsp = fn(t)
            except Exception:
                continue
            data = self._parse_json_rsp(rsp)
            if data is None:
                continue
            if not self._is_guard(data):
                return data
            if fallback is None:
                fallback = data
        return fallback

    def _post_json(self, url, payload, timeout=12):
        deadline = time.time() + timeout + 2
        data = self._post_once(url, payload, timeout, deadline)
        if self._is_guard(data):
            left = deadline - time.time()
            if left > 1.5:
                time.sleep(0.5)
                retry = self._post_once(url, payload, max(1.5, min(timeout, left)), deadline)
                if retry is not None:
                    data = retry
        return data

    def _get_json(self, url, timeout=12):
        try:
            rsp = self.fetch(url, headers=self.header, timeout=timeout)
            return self._parse_json_rsp(rsp)
        except Exception:
            return None

    def _cache_get(self, store, key):
        try:
            ts, val = store.get(key, (0, None))
            if val is not None and int(time.time()) - ts < CACHE_TTL:
                return val
        except Exception:
            pass
        return None

    def _cache_put(self, store, key, val):
        try:
            if self._lock:
                with self._lock:
                    store[key] = (int(time.time()), val)
            else:
                store[key] = (int(time.time()), val)
        except Exception:
            pass

    # ===== URL 补全 =====
    def _abs_url(self, u):
        u = (u or "").strip().replace("\\/", "/")
        if u.startswith("//"):
            return "http:" + u
        if u.startswith("/"):
            return HOST + u
        return u

    def _fix_play_url(self, s):
        if not s:
            return ""
        groups = []
        for grp in s.split("$$$"):
            eps = []
            for ep in grp.split("#"):
                if not ep.strip():
                    continue
                if "$" in ep:
                    n, u = ep.split("$", 1)
                    eps.append("%s$%s" % (n, self._abs_url(u)))
                else:
                    eps.append(self._abs_url(ep))
            groups.append("#".join(eps))
        return "$$$".join(groups)

    def _decode_ep_token(self, url):
        try:
            token = url.rsplit("/", 1)[-1].split("?")[0]
            if not token.startswith("tvbox_ep_"):
                return ""
            token = token[len("tvbox_ep_"):]
            token += "=" * (-len(token) % 4)
            obj = json.loads(base64.b64decode(token).decode("utf-8", "ignore"))
            real = obj.get("i") or ""
            if isinstance(real, str) and real.startswith("http"):
                return real
        except Exception:
            pass
        return ""

    def _resolve_play(self, url):
        if DIRECT_PLAY and "/api/tvbox/play/" in url:
            real = self._decode_ep_token(url)
            if real:
                return real
        return url

    # ===== id 编解码 =====
    def _enc_id(self, src_key, vod_id):
        return "%s@%s" % (src_key, vod_id)

    def _dec_id(self, s):
        s = str(s or "")
        m = re.match(r"^(qiyou|qukkan|qilin)@(.+)$", s)
        if m:
            return m.group(1), m.group(2)
        m = re.match(r"^([A-Za-z0-9\-_]+)@(.+)$", s)
        if m and m.group(1) in SOURCE_API:
            return m.group(1), m.group(2)
        if "@" in s:
            k, v = s.split("@", 1)
            if k in SOURCE_API:
                return k, v
        return "", s

    def _src_of_tid(self, tid):
        tid = str(tid or "")
        if tid.startswith("s_"):
            return tid[2:]
        return tid

    def _card(self, src_key, v):
        vid = v.get("vod_id", "")
        pic = v.get("vod_pic", "") or ""
        if pic.startswith("//"):
            pic = "http:" + pic
        remark = (v.get("vod_remarks", "") or "").strip()
        if len(remark) > 20:
            remark = remark[:20]
        if self._multi_source and remark:
            remark = "%s · %s" % (SOURCE_NAME.get(src_key, src_key), remark)
        elif self._multi_source:
            remark = SOURCE_NAME.get(src_key, src_key)
        return {
            "vod_id": self._enc_id(src_key, vid),
            "vod_name": v.get("vod_name", ""),
            "vod_pic": pic,
            "vod_remarks": remark,
        }

    # ===== 首页 =====
    def homeContent(self, filter):
        result = {"class": CLASSES, "filters": FILTERS}
        try:
            self._multi_source = False
            key = SOURCES[0]["key"]
            home = self._home_of(key)
            vods = [self._card(key, v) for v in (home.get("list") or [])]
            if vods:
                result["list"] = vods
        except Exception:
            pass
        return result

    def homeVideoContent(self):
        self._multi_source = True
        rec = self._recommend_list()
        return {"list": rec[:REC_LIMIT]}

    def _recommend_list(self):
        cached = self._cache_get(self._rec_cache_store(), "rec")
        if cached is not None:
            return cached
        out = []
        lock = threading.Lock() if threading else None

        def _one(k):
            home = self._home_of(k, REC_TIMEOUT)
            cards = [self._card(k, v) for v in (home.get("list") or [])[:REC_PER_SRC]]
            if cards:
                if lock:
                    with lock:
                        out.append((k, cards))
                else:
                    out.append((k, cards))

        complete = True
        if threading:
            workers = []
            for k in RECOMMEND_SOURCES:
                t = threading.Thread(target=_one, args=(k,))
                t.daemon = True
                t.start()
                workers.append(t)
            waited = 0.0
            while waited < REC_WAIT:
                time.sleep(0.2)
                waited += 0.2
                if lock:
                    with lock:
                        n = sum(len(c) for _, c in out)
                else:
                    n = sum(len(c) for _, c in out)
                if n >= REC_LIMIT:
                    break
            if any(w.is_alive() for w in workers):
                complete = False
        else:
            for k in RECOMMEND_SOURCES:
                _one(k)
        merged = self._merge_by_source(out, RECOMMEND_SOURCES)
        if complete:
            self._cache_put(self._rec_cache_store(), "rec", merged)
        return merged

    def _merge_by_source(self, out, order_list):
        order = dict((k, i) for i, k in enumerate(order_list))
        out.sort(key=lambda kv: order.get(kv[0], 99))
        merged = []
        idx = 0
        total = sum(len(c) for _, c in out)
        while len(merged) < total:
            added = False
            for _, cards in out:
                if idx < len(cards):
                    merged.append(cards[idx])
                    added = True
            if not added:
                break
            idx += 1
        return merged

    def _rec_cache_store(self):
        if not hasattr(self, "_rec_store"):
            self._rec_store = {}
        return self._rec_store

    def _home_of(self, src_key, timeout=12):
        cached = self._cache_get(self._home_cache, src_key)
        if cached is not None:
            return cached
        data = self._post_json(API_HOME, {"api": SOURCE_API.get(src_key, ""), "filter": True}, timeout=timeout)
        home = (data or {}).get("data") or {}
        home["list"] = home.get("list") or []
        home["class"] = home.get("class") or []
        if home["list"]:
            self._cache_put(self._home_cache, src_key, home)
        if home["class"] and not SUB_CLASS.get(src_key):
            SUB_CLASS[src_key] = [{"n": c.get("type_name", ""), "v": str(c.get("type_id", ""))} for c in home["class"]]
        return home

    # ===== 分类 =====
    def categoryContent(self, tid, pg, filter, extend):
        self._multi_source = False
        try:
            page = int(pg or 1)
            if page < 1:
                page = 1
            ext = {}
            if extend:
                if isinstance(extend, dict):
                    ext = extend
                elif isinstance(extend, str):
                    try:
                        ext = json.loads(extend)
                    except Exception:
                        ext = {}
            src_key = self._src_of_tid(tid)

            if src_key == "qiyou":
                sub = str(ext.get("tid", "") or "") or "1"
                return self._qiyou.category(sub, page)

            if src_key == "qukkan":
                sub = str(ext.get("tid", "") or "") or "all"
                by = str(ext.get("by", "") or "")
                return self._qukkan.category(sub, page, by)

            # ---- 内置分支：麒麟视频 ----
            if src_key == "qilin":
                sub = str(ext.get("tid", "") or "") or "1"
                year = str(ext.get("year", "") or "")
                area = str(ext.get("area", "") or "")
                return self._qilin.category(sub, page, year, area)

            if src_key == REC_KEY:
                rec = self._recommend_list()
                src_filter = str(ext.get("src", "") or "")
                if src_filter:
                    rec = [v for v in rec if v["vod_id"].split("@", 1)[0] == src_filter]
                start = (page - 1) * REC_LIMIT
                items = rec[start:start + REC_LIMIT]
                pagecount = max(1, (len(rec) + REC_LIMIT - 1) // REC_LIMIT)
                return {"list": items, "page": page, "pagecount": pagecount,
                        "limit": REC_LIMIT, "total": len(rec)}

            if src_key not in SOURCE_API:
                return {"page": page, "pagecount": page, "limit": 10, "total": 0, "list": []}

            sub_tid = str(ext.get("tid", "") or "")
            if not sub_tid:
                home = self._home_of(src_key)
                vods = [self._card(src_key, v) for v in (home.get("list") or [])]
                return {"list": vods, "page": 1, "pagecount": 1,
                        "limit": len(vods) or 10, "total": len(vods)}

            ck = (src_key, sub_tid, page)
            cached = self._cache_get(self._cat_cache, ck)
            if cached is None:
                cached = self._cat_fetch(src_key, sub_tid, page)
                if cached:
                    self._cache_put(self._cat_cache, ck, cached)
            vods = [self._card(src_key, v) for v in cached]
            pagecount = page + 1 if vods else page
            return {"list": vods, "page": page, "pagecount": pagecount,
                    "limit": len(vods) or 10,
                    "total": len(vods) * page if vods else 0}
        except Exception:
            return {"page": 1, "pagecount": 1, "limit": 10, "total": 0, "list": []}

    def _cat_page(self, src_key, tid, page):
        ck = ("p", src_key, tid, page)
        cached = self._cache_get(self._cat_cache, ck)
        if cached is not None:
            return cached
        payload = {"api": SOURCE_API[src_key], "tid": tid, "page": page, "filter": True, "extend": {}}
        data = self._post_json(API_CATEGORY, payload, timeout=CAT_TIMEOUT)
        lst = (data or {}).get("data", {}).get("list") or []
        if lst:
            self._cache_put(self._cat_cache, ck, lst)
        return lst

    def _cat_fetch(self, src_key, tid, pg):
        items = []
        steps = self._page_steps.get(src_key)
        if steps is None:
            steps = CAT_PAGES
            self._page_steps[src_key] = steps
        first = self._cat_page(src_key, tid, 1)
        if first:
            self._page_size[src_key] = len(first)
            if len(first) >= CAT_MIN_ITEMS and pg <= 1:
                self._page_steps[src_key] = 1
                return first[:CAT_MAX]
            items = list(first)
        start = (pg - 1) * steps + 1
        pages = [start + i for i in range(steps)]
        got = []
        lock = threading.Lock() if threading else None

        def _one(p):
            r = self._cat_page(src_key, tid, p)
            if r:
                if lock:
                    with lock:
                        got.append((p, r))
                else:
                    got.append((p, r))

        if threading:
            workers = []
            for p in pages:
                t = threading.Thread(target=_one, args=(p,))
                t.daemon = True
                t.start()
                workers.append(t)
            for w in workers:
                w.join()
        else:
            for p in pages:
                _one(p)
        seen = set(str(v.get("vod_id", "")) for v in items)
        for _, r in sorted(got, key=lambda x: x[0]):
            for v in r:
                vid = str(v.get("vod_id", ""))
                if vid and vid in seen:
                    continue
                seen.add(vid)
                items.append(v)
        return items[:CAT_MAX]

    # ===== 详情 =====
    def detailContent(self, ids):
        self._multi_source = False
        if isinstance(ids, str):
            ids = [ids]
        src_key, real_id = self._dec_id(ids[0])
        if not src_key or not real_id:
            return {"list": []}

        if src_key == "qiyou":
            return self._qiyou.detail(real_id)
        if src_key == "qukkan":
            return self._qukkan.detail(real_id)
        if src_key == "qilin":
            return self._qilin.detail(real_id)

        data = None
        for _ in range(2):
            data = self._post_json(API_DETAIL, {"api": SOURCE_API[src_key], "ids": [real_id]}, timeout=12)
            if data and data.get("success") and data.get("data"):
                break
            time.sleep(0.4)
        d = (data or {}).get("data") or {}
        if not d:
            return {"list": []}
        play_from = d.get("vod_play_from", "") or "播放"
        play_url = self._fix_play_url(d.get("vod_play_url", "") or "")
        if not play_url and DETAIL_FALLBACK:
            alt = self._fallback_detail(src_key, d.get("vod_name", "") or "")
            if alt:
                return {"list": [alt]}
            return {"list": []}
        if not play_url:
            return {"list": []}
        vod = {
            "vod_id": self._enc_id(src_key, d.get("vod_id", real_id)),
            "vod_name": d.get("vod_name", ""),
            "vod_pic": d.get("vod_pic", "") or "",
            "type_name": SOURCE_NAME.get(src_key, ""),
            "vod_year": d.get("vod_year", ""),
            "vod_area": d.get("vod_area", ""),
            "vod_remarks": d.get("vod_remarks", "") or "HD",
            "vod_actor": d.get("vod_actor", ""),
            "vod_director": d.get("vod_director", ""),
            "vod_content": re.sub(r'<[^>]+>', '', d.get("vod_content", "") or "")[:500],
            "vod_play_from": play_from,
            "vod_play_url": play_url,
        }
        return {"list": [vod]}

    def _fallback_detail(self, src_key, name):
        if not name:
            return None
        cached = self._cache_get(self._search_cache, name)
        cands = []
        if cached:
            for c in cached:
                k, rid = self._dec_id(c.get("vod_id", ""))
                if k and k != src_key and k not in EXTRA_KEYS:
                    cands.append((k, rid))
        if not cands:
            for k in (SEARCH_ONLY + RECOMMEND_SOURCES):
                if k == src_key or k not in SOURCE_API:
                    continue
                data = self._post_json(API_SEARCH, {"api": SOURCE_API[k], "keyword": name}, timeout=SEARCH_TIMEOUT)
                for v in ((data or {}).get("data") or [])[:3]:
                    if v.get("vod_id"):
                        cands.append((k, str(v["vod_id"])))
        tried = 0
        for k, rid in cands:
            if tried >= FALLBACK_TRY:
                break
            tried += 1
            data = self._post_json(API_DETAIL, {"api": SOURCE_API[k], "ids": [rid]}, timeout=10)
            d = (data or {}).get("data") or {}
            url = self._fix_play_url(d.get("vod_play_url", "") or "")
            if url:
                return {
                    "vod_id": self._enc_id(k, d.get("vod_id", rid)),
                    "vod_name": d.get("vod_name", "") or name,
                    "vod_pic": d.get("vod_pic", "") or "",
                    "type_name": SOURCE_NAME.get(k, ""),
                    "vod_year": d.get("vod_year", ""),
                    "vod_area": d.get("vod_area", ""),
                    "vod_remarks": d.get("vod_remarks", "") or "HD",
                    "vod_actor": d.get("vod_actor", ""),
                    "vod_director": d.get("vod_director", ""),
                    "vod_content": re.sub(r'<[^>]+>', '', d.get("vod_content", "") or "")[:500],
                    "vod_play_from": d.get("vod_play_from", "") or "播放",
                    "vod_play_url": url,
                }
        return None

    # ===== 搜索 =====
    def searchContent(self, key, quick, pg="1"):
        self._multi_source = True
        try:
            page = int(pg or 1)
            if page < 1:
                page = 1
            if SEARCH_ALL:
                keys = [s["key"] for s in SOURCES]
            else:
                keys = [k for k in SEARCH_ONLY if k in SOURCE_API]
            cached = self._cache_get(self._search_cache, key)
            if cached is None:
                cached = self._search_all(keys, key)
                if cached:
                    self._cache_put(self._search_cache, key, cached)
            if page == 1:
                try:
                    q = self._qukkan.search(key, 1)
                    for c in q.get("list") or []:
                        cached.append(c)
                except Exception:
                    pass
                try:
                    q = self._qilin.search(key, 1)
                    for c in q.get("list") or []:
                        cached.append(c)
                except Exception:
                    pass
            total = len(cached)
            pagecount = max(1, (total + SEARCH_LIMIT - 1) // SEARCH_LIMIT)
            start = (page - 1) * SEARCH_LIMIT
            items = cached[start:start + SEARCH_LIMIT]
            return {"list": items, "page": page, "pagecount": pagecount,
                    "limit": SEARCH_LIMIT, "total": total}
        except Exception:
            return {"list": []}

    def _search_all(self, keys, key):
        results = []
        lock = threading.Lock() if threading else None

        def _one(k):
            data = self._post_json(API_SEARCH, {"api": SOURCE_API[k], "keyword": key}, timeout=SEARCH_TIMEOUT)
            lst = (data or {}).get("data") or []
            if lst:
                cards = [self._card(k, v) for v in lst[:SEARCH_PER_SRC]]
                if lock:
                    with lock:
                        results.append((k, cards))
                else:
                    results.append((k, cards))

        if threading:
            workers = []
            for k in keys:
                t = threading.Thread(target=_one, args=(k,))
                t.daemon = True
                t.start()
                workers.append(t)
                if len(workers) >= SEARCH_WORKERS:
                    for w in workers:
                        w.join()
                    workers = []
            for w in workers:
                w.join()
        else:
            for k in keys:
                _one(k)
        order = dict((k, i) for i, k in enumerate(keys))
        results.sort(key=lambda kv: order.get(kv[0], 99))
        merged = []
        seen = set()
        for _, cards in results:
            for c in cards:
                name = c.get("vod_name", "")
                if name in seen:
                    continue
                seen.add(name)
                merged.append(c)
        merged = self._rank(merged, key)
        return merged[:SEARCH_MAX]

    def _rank(self, cards, key):
        k = (key or "").lower().replace(" ", "")

        def score(c):
            n = (c.get("vod_name", "") or "").lower().replace(" ", "")
            if not n:
                return 900
            if n == k:
                return 0
            if n.startswith(k):
                return 1
            if k and k in n:
                return 2 + n.index(k)
            return 900

        if SEARCH_STRICT is True:
            cards = [c for c in cards if score(c) < 900]
        elif SEARCH_STRICT == "auto":
            hits = [c for c in cards if score(c) < 900]
            if len(hits) >= 5:
                cards = hits
        cards.sort(key=score)
        return cards

    # ===== 播放 =====
    def _is_media(self, url):
        u = (url or "").lower()
        return ".m3u8" in u or ".mp4" in u or ".flv" in u or ".mkv" in u or "m3u8" in u

    def _referer(self, url):
        try:
            if "://" in url:
                scheme = url.split("://")[0]
                host = url.split("://")[1].split("/")[0]
                return scheme + "://" + host + "/"
        except Exception:
            pass
        return HOST + "/"

    def playerContent(self, flag, id, vipFlags):
        if not id:
            return {"parse": 0, "playUrl": "", "url": ""}
        sid = str(id)

        # ---- 趣看看短剧：带前缀 或 纯 "albumId:seq" 格式 ----
        if sid.startswith("qukkan@"):
            return self._qukkan.player(sid[len("qukkan@"):])
        m = re.match(r"^(\d+):(\d+)$", sid.strip())
        if m:
            return self._qukkan.player("%s:%s" % (m.group(1), m.group(2)))

        # ---- 奇优影院 ----
        if "qiyou05.com" in sid:
            play_url = sid.split("$")[1] if "$" in sid else sid
            if "$" in str(play_url):
                play_url = play_url.split("$")[-1]
            return self._qiyou.player(play_url)

        # ---- 麒麟视频：qlys.cc 域名的 m3u8 直链 ----
        if "qlys.cc" in sid:
            return self._qilin.player(sid)

        play_url = self._abs_url(sid)
        play_url = self._resolve_play(play_url)
        if self._is_media(play_url):
            is_m3u8 = "m3u8" in play_url.lower()
            return {
                "parse": 0, "playUrl": "", "url": play_url,
                "header": {"User-Agent": UA, "Referer": self._referer(play_url)},
                "format": "application/x-mpegURL" if is_m3u8 else "video/mp4",
                "contentType": "application/x-mpegURL" if is_m3u8 else "video/mp4",
            }
        if HOST in play_url and ("/api/tvbox/play/" in play_url or "/api/tvbox/media/" in play_url):
            return {"parse": 0, "playUrl": "", "url": play_url,
                    "header": {"User-Agent": UA, "Referer": HOST + "/"}}
        return {"parse": 1, "playUrl": "", "url": play_url,
                "header": {"User-Agent": UA, "Referer": HOST + "/"}}

    # ===== 兼容方法 =====
    def isVideoFormat(self, url):
        return self._is_media(url)

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return [200, "video/MP2T", b"", ""]

    def destroy(self):
        pass

    def close(self):
        self.destroy()
