from flask import Flask, request, jsonify, render_template
import requests
import re
import random
import base64
import json
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

# ─────────────────────────────────────────────
# 歌手识别 & 情绪分析
# ─────────────────────────────────────────────

KNOWN_ARTISTS = [
    "周杰伦","陈奕迅","林俊杰","薛之谦","毛不易","赵雷","李荣浩",
    "许巍","汪峰","朴树","张学友","刘德华","王力宏","光良","邓紫棋",
    "孙燕姿","蔡依林","梁静茹","王菲","张惠妹","田馥甄","莫文蔚",
    "五月天","苏打绿","告五人","beyond","伍佰","痛仰",
    "华晨宇","李宇春","邓丽君","凤凰传奇","金玟岐","张碧晨",
    "BTS","BLACKPINK","TWICE","IU","aespa","NewJeans","Stray Kids",
    "Taylor Swift","Ed Sheeran","Adele","Bruno Mars","Harry Styles",
    "Billie Eilish","Olivia Rodrigo","The Weeknd","Drake","Eminem",
    "Coldplay","Imagine Dragons","Linkin Park","Maroon 5","OneRepublic",
    "Justin Bieber","Ariana Grande","Dua Lipa","Shawn Mendes","Joji",
    "Post Malone","Khalid","SZA","Beyonce","Rihanna",
]

def detect_artist(text):
    patterns = [r"想听(.{2,10})的歌",r"来点(.{2,10})的",r"放(.{2,10})的歌",r"听(.{2,10})的歌",r"推荐(.{2,10})的歌"]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            candidate = match.group(1).strip()
            for artist in KNOWN_ARTISTS:
                if artist.lower() in candidate.lower() or candidate.lower() in artist.lower():
                    return artist
            if 2 <= len(candidate) <= 10:
                return candidate
    for artist in KNOWN_ARTISTS:
        if artist.lower() in text.lower():
            return artist
    return None

def analyze_mood(text):
    happy_words = ["开心","快乐","高兴","兴奋","棒","爽","好玩","哈哈","嘻嘻","幸福","满足","太好了","不错","开朗","愉快","激动","喜悦","元气","活力","嗨"]
    sad_words   = ["难过","伤心","哭","失落","痛苦","沮丧","心碎","绝望","委屈","想哭","悲","郁闷","低落","失望","孤独","分手","想念","思念","后悔","离别","心痛"]
    angry_words = ["生气","愤怒","烦","讨厌","气死","崩溃","无语","抓狂","暴躁","恼火","受不了","焦虑","压力","爆炸","憋屈","窝火","不爽","恨","怒"]
    chill_words = ["平静","放松","休息","累","睡觉","慵懒","发呆","无聊","还好","一般","随便","平淡","安静","躺平","摸鱼","冷静","佛系","宅","疲惫"]
    scores = {"happy":0,"sad":0,"angry":0,"chill":0}
    for w in happy_words:
        if w in text: scores["happy"] += 1
    for w in sad_words:
        if w in text: scores["sad"] += 1
    for w in angry_words:
        if w in text: scores["angry"] += 1
    for w in chill_words:
        if w in text: scores["chill"] += 1
    mood = max(scores, key=scores.get)
    if scores[mood] == 0: mood = "chill"
    reasons = {
        "happy": "你现在心情不错！推荐活力满满的流行歌曲～",
        "sad":   "听起来你有点难过，推荐能共鸣或治愈的歌曲。",
        "angry": "有点烦躁？来点有力量感的歌发泄一下吧！",
        "chill": "状态平和，推荐轻松流行歌曲陪你度过这段时光。"
    }
    return mood, reasons[mood]

MOOD_QUERIES = {
    "happy": ["周杰伦","邓紫棋","蔡依林","五月天","BTS","Taylor Swift","Bruno Mars","Dua Lipa","告五人","王力宏"],
    "sad":   ["陈奕迅","薛之谦","林俊杰","孙燕姿","毛不易","赵雷","Adele","Joji","Ed Sheeran","金玟岐"],
    "angry": ["五月天","痛仰","beyond","Imagine Dragons","Linkin Park","周杰伦 双截棍","汪峰","Green Day","华晨宇","苏打绿"],
    "chill": ["周杰伦","陈奕迅","邓紫棋","林俊杰","赵雷","毛不易","Ed Sheeran","Harry Styles","Shawn Mendes","卢广仲"],
}

# ─────────────────────────────────────────────
# iTunes 搜索（每个歌手最多1首）
# ─────────────────────────────────────────────

def search_itunes(query, limit=5, country="cn"):
    try:
        res = requests.get("https://itunes.apple.com/search",
            params={"term": query, "media": "music", "limit": limit, "country": country}, timeout=10)
        return res.json().get("results", [])
    except:
        return []

def build_songs(items, max_per_artist=1):
    seen_artists = {}
    results = []
    random.shuffle(items)
    for item in items:
        artist = item.get("artistName","").strip()
        count = seen_artists.get(artist, 0)
        if count >= max_per_artist:
            continue
        seen_artists[artist] = count + 1
        results.append({
            "title":   item.get("trackName",""),
            "artist":  artist,
            "album":   item.get("collectionName",""),
            "cover":   item.get("artworkUrl100","").replace("100x100","400x400"),
            "url":     item.get("trackViewUrl",""),
            "preview": item.get("previewUrl","") or ""
        })
    return results

def search_music_by_mood(mood, limit=8):
    pool = MOOD_QUERIES.get(mood, MOOD_QUERIES["chill"])
    queries = random.sample(pool, min(4, len(pool)))
    all_items = []
    for q in queries:
        all_items += search_itunes(q, limit=4)
        if len(all_items) >= 40: break
    return build_songs(all_items)[:limit]

# ─────────────────────────────────────────────
# 路由：主页面
# ─────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

# ─────────────────────────────────────────────
# 路由：情绪推荐
# ─────────────────────────────────────────────

@app.route("/recommend", methods=["POST"])
def recommend():
    data = request.get_json()
    text = data.get("mood","").strip()
    artist = detect_artist(text)
    if artist:
        items = search_itunes(artist, limit=10)
        random.shuffle(items)
        songs = build_songs(items, max_per_artist=3)[:8]
        return jsonify({"mood":"artist","reason":f"为你推荐「{artist}」的歌曲 🎵","songs":songs})
    mood, reason = analyze_mood(text)
    songs = search_music_by_mood(mood)
    return jsonify({"mood":mood,"reason":reason,"songs":songs})

# ─────────────────────────────────────────────
# 路由：天气配乐
# ─────────────────────────────────────────────

WEATHER_MOOD = {
    # WMO weather code ranges → mood + desc
    "sunny":  {"mood":"happy",  "desc":"☀️ 晴天","queries":["周杰伦 晴天","邓紫棋 光年之外","Bruno Mars","Taylor Swift","蔡依林"]},
    "cloudy": {"mood":"chill",  "desc":"☁️ 多云","queries":["陈奕迅","Ed Sheeran","赵雷","林俊杰","毛不易"]},
    "rainy":  {"mood":"sad",    "desc":"🌧️ 下雨","queries":["周杰伦 雨天的回忆","薛之谦","Adele","孙燕姿","金玟岐"]},
    "stormy": {"mood":"angry",  "desc":"⛈️ 雷暴","queries":["五月天","Imagine Dragons","Linkin Park","beyond","痛仰"]},
    "snowy":  {"mood":"chill",  "desc":"❄️ 下雪","queries":["许巍","王菲","Coldplay","Ed Sheeran","Joji"]},
    "foggy":  {"mood":"chill",  "desc":"🌫️ 雾","queries":["陈奕迅","毛不易","Joji","The Weeknd","赵雷"]},
    "windy":  {"mood":"chill",  "desc":"💨 大风","queries":["五月天","汪峰","Coldplay","许巍","苏打绿"]},
}

def wmo_to_type(code):
    code = int(code)
    if code in [0,1]: return "sunny"
    if code in [2,3]: return "cloudy"
    if code in [45,48]: return "foggy"
    if code in range(51,68): return "rainy"
    if code in range(71,78): return "snowy"
    if code in range(80,83): return "rainy"
    if code in range(95,100): return "stormy"
    return "cloudy"

@app.route("/weather", methods=["POST"])
def weather():
    data = request.get_json()
    lat = data.get("lat", 39.9)
    lon = data.get("lon", 116.4)
    try:
        r = requests.get("https://api.open-meteo.com/v1/forecast",
            params={"latitude":lat,"longitude":lon,"current":"weathercode,temperature_2m","timezone":"auto"}, timeout=8)
        wd = r.json()
        code = wd["current"]["weathercode"]
        temp = round(wd["current"]["temperature_2m"])
        wtype = wmo_to_type(code)
        meta = WEATHER_MOOD[wtype]
        queries = random.sample(meta["queries"], min(5, len(meta["queries"])))
        all_items = []
        for q in queries:
            all_items += search_itunes(q, limit=4)
        songs = build_songs(all_items)[:8]
        return jsonify({"weather":meta["desc"],"temp":temp,"mood":meta["mood"],"songs":songs,"wtype":wtype})
    except Exception as e:
        print("天气API失败:", e)
        songs = search_music_by_mood("chill")
        return jsonify({"weather":"🌤️ 获取天气失败","temp":"--","mood":"chill","songs":songs,"wtype":"cloudy"})

# ─────────────────────────────────────────────
# 路由：照片配乐
# ─────────────────────────────────────────────

@app.route("/photo", methods=["POST"])
def photo():
    data = request.get_json()
    b64 = data.get("image","")
    try:
        img_bytes = base64.b64decode(b64.split(",")[-1])
        # 采样像素分析颜色亮度
        from io import BytesIO
        try:
            from PIL import Image
            img = Image.open(BytesIO(img_bytes)).convert("RGB").resize((50,50))
            pixels = list(img.getdata())
            avg_r = sum(p[0] for p in pixels)/len(pixels)
            avg_g = sum(p[1] for p in pixels)/len(pixels)
            avg_b = sum(p[2] for p in pixels)/len(pixels)
            brightness = (avg_r*0.299 + avg_g*0.587 + avg_b*0.114)
            saturation = max(avg_r,avg_g,avg_b) - min(avg_r,avg_g,avg_b)
        except:
            avg_r,avg_g,avg_b,brightness,saturation = 128,128,128,128,30

        # 颜色分析逻辑
        if brightness > 180 and saturation > 40:
            mood,desc = "happy","画面明亮鲜艳，充满活力！"
        elif brightness < 80:
            mood,desc = "sad","画面偏暗，带点忧郁的美。"
        elif avg_r > avg_b + 30 and saturation > 50:
            mood,desc = "angry","暖红色调，有股热烈的能量！"
        elif avg_b > avg_r + 20:
            mood,desc = "chill","蓝色系画面，宁静又清澈。"
        elif brightness > 120 and saturation < 30:
            mood,desc = "chill","低饱和度的画面，极简又平和。"
        else:
            mood,desc = "chill","这张照片有种静谧的氛围。"

        songs = search_music_by_mood(mood)
        return jsonify({"mood":mood,"desc":desc,"songs":songs,
                        "colors":{"r":int(avg_r),"g":int(avg_g),"b":int(avg_b),"brightness":int(brightness)}})
    except Exception as e:
        print("照片分析失败:", e)
        songs = search_music_by_mood("chill")
        return jsonify({"mood":"chill","desc":"为你随机推荐一些歌曲～","songs":songs,"colors":{"r":128,"g":128,"b":128,"brightness":128}})

# ─────────────────────────────────────────────
# 路由：盲盒推歌
# ─────────────────────────────────────────────

@app.route("/blindbox", methods=["GET"])
def blindbox():
    all_queries = [q for qs in MOOD_QUERIES.values() for q in qs]
    q = random.choice(all_queries)
    items = search_itunes(q, limit=10)
    items = [i for i in items if i.get("previewUrl")]
    if not items:
        return jsonify({"error":"暂时没有可用的试听歌曲，再试一次！"})
    item = random.choice(items)
    return jsonify({
        "preview": item.get("previewUrl",""),
        "reveal": {
            "title":  item.get("trackName",""),
            "artist": item.get("artistName",""),
            "album":  item.get("collectionName",""),
            "cover":  item.get("artworkUrl100","").replace("100x100","400x400"),
            "url":    item.get("trackViewUrl","")
        }
    })

# ─────────────────────────────────────────────
# 路由：歌曲聊天室（存在服务器内存，重启清空）
# ─────────────────────────────────────────────

comments_db = {}   # key: "title::artist", value: [{"text","time"}]

@app.route("/comment", methods=["POST"])
def add_comment():
    data = request.get_json()
    key = f"{data.get('title','')}::{data.get('artist','')}"
    text = data.get("text","").strip()[:100]
    if not text:
        return jsonify({"ok":False})
    import datetime
    entry = {"text":text,"time":datetime.datetime.now().strftime("%m/%d %H:%M")}
    comments_db.setdefault(key,[]).append(entry)
    if len(comments_db[key]) > 30:
        comments_db[key] = comments_db[key][-30:]
    return jsonify({"ok":True,"comments":comments_db[key][-10:]})

@app.route("/comment", methods=["GET"])
def get_comments():
    key = request.args.get("key","")
    return jsonify({"comments": comments_db.get(key,[])[-10:]})

if __name__ == "__main__":
    app.run(debug=True, port=5001, host="0.0.0.0")