# LowHigh v3.2 — ПОЛНАЯ ВЕРСИЯ (ОПТИМИЗИРОВАНО)

import telebot
from telebot.types import InlineKeyboardMarkup as MK, InlineKeyboardButton as KB
import random, time, json, os, re, threading
from datetime import datetime, timedelta

# ========== НАСТРОЙКИ ==========
TOKEN = "8265086577:AAFqojYbFSIRE2FZg0jnJ0Qgzdh0w9_j6z4"
MASTER_ADMINS = [6656110482, 8525294722]
OWNER = "@nickelium"
bot = telebot.TeleBot(TOKEN)

# ========== ЦВЕТА ==========
class C:
    H = '\033[95m'; B = '\033[94m'; G = '\033[92m'; Y = '\033[93m'; R = '\033[91m'; E = '\033[0m'; BO = '\033[1m'

def log(lvl, msg):
    t = datetime.now().strftime("%H:%M:%S")
    p = f"{C.B}[{t}][INFO]{C.E} {msg}" if lvl=="INFO" else \
        f"{C.G}[{t}][✓]{C.E} {msg}" if lvl=="SUCCESS" else \
        f"{C.Y}[{t}][⚠]{C.E} {msg}" if lvl=="WARNING" else \
        f"{C.R}[{t}][✗]{C.E} {msg}" if lvl=="ERROR" else \
        f"{C.H}[{t}][📢]{C.E} {msg}" if lvl=="POST" else \
        f"{C.BO}[{t}][🎰]{C.E} {msg}"
    print(p)

# ========== БАЗА (НАДЁЖНО) ==========
DB_FILE = "bot_data.json"
def save():
    tmp = DB_FILE+".tmp"; bak = DB_FILE+".backup"
    try:
        with open(tmp, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2)
        if os.path.exists(DB_FILE): os.replace(DB_FILE, bak)
        os.replace(tmp, DB_FILE)
        if os.path.exists(bak): os.remove(bak)
        log("INFO", "Сохранено")
    except Exception as e:
        log("ERROR", f"Ошибка: {e}")
        if os.path.exists(bak): os.replace(bak, DB_FILE)

def load():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f: d = json.load(f)
            log("INFO", f"Загружено {len(d.get('users',{}))} юзеров"); return d
        except: log("ERROR", "Файл битый, пробуем бэкап")
    if os.path.exists(DB_FILE+".backup"):
        try:
            with open(DB_FILE+".backup", 'r', encoding='utf-8') as f: d = json.load(f)
            log("WARNING", "Восстановлено из бэкапа")
            with open(DB_FILE, 'w', encoding='utf-8') as f: json.dump(d, f)
            return d
        except: log("ERROR", "Бэкап тоже битый")
    return {"users":{},"posts":[],"banned":[],"admins":MASTER_ADMINS.copy(),"vip":[],"verified":[],
            "post_history":{},"post_contents":{},"stats":{"attempts":0,"wins":0,"posts_sent":0},
            "reactions":{}}

data = load()

# ========== ЮЗЕРЫ ==========
def get_user(uid):
    uid = str(uid)
    if uid in data["banned"]: return None
    if uid not in data["users"]:
        data["users"][uid] = {
            "rating":5.0, "luck":1.0, "fails":0, "incoming":50.0,
            "last_casino":None, "last_post":None, "posts_count":0, "last_convert":None,
            "refs":[], "referrer":None, "total_posts":0, "total_casino":0, "wins":0,
            "username":None, "first_name":None, "notify":True, "joined":datetime.now().isoformat(),
            "vip_until":None, "inv":{"amulet":0,"silencer":0,"vip_pass":0}, "silencer_until":None,
            "weekly":0, "weekly_posts":0, "weekly_likes":0, "quests":{}, "bonus_ready":False,
            "my_posts":[], "posts_data":{}
        }
        log("SUCCESS", f"Новый юзер: {uid}"); save()
    return data["users"][uid]

def name(uid):
    uid = str(uid); u = data["users"].get(uid)
    if not u: return "?"
    if u.get("username"): return u["username"]
    if u.get("first_name"): return u["first_name"]
    try:
        chat = bot.get_chat(int(uid))
        name = chat.first_name or "Аноним"
        u["first_name"] = name; save(); return name
    except: return f"User_{uid[-4:]}"

def emoji(uid):
    uid = str(uid)
    if is_vip(uid): return "👑"
    if is_verified(uid): return "✅"
    return "📝"

def fix_rating(uid):
    u = get_user(uid)
    if not u: return
    if (is_vip(uid) or is_verified(uid)) and u["rating"] < 10.0:
        u["rating"] = 10.0; save(); return True
    return False

def is_vip(uid):
    uid = str(uid); u = data["users"].get(uid)
    if u and u.get("vip_until"):
        try:
            if datetime.now() < datetime.fromisoformat(u["vip_until"]): return True
            else: u["vip_until"] = None
        except: u["vip_until"] = None
    return uid in data.get("vip", [])

def is_verified(uid): return str(uid) in data.get("verified", [])
def is_admin(uid): return str(uid) in [str(a) for a in MASTER_ADMINS] or str(uid) in data.get("admins", [])
def is_banned(uid): return str(uid) in data["banned"]
def max_refs(uid): return 50 if is_vip(uid) else 25 if is_verified(uid) else 10

def post_cd(uid):
    if is_vip(uid): return 2
    u = get_user(uid); pc = u.get("posts_count",0) if u else 0
    return 4 if pc>=37 else 5 if pc>=22 else 6 if pc>=12 else 7 if pc>=5 else 8

def check_post_cd(u):
    if not u["last_post"]: return True,0
    last = datetime.fromisoformat(u["last_post"])
    nxt = last + timedelta(hours=post_cd(u))
    return (True,0) if datetime.now()>=nxt else (False,(nxt-datetime.now()).total_seconds())

def max_len(uid): return 500 if is_vip(uid) else 300 if is_verified(uid) else 250
def casino_cd(u):
    if not u["last_casino"]: return True,0
    last = datetime.fromisoformat(u["last_casino"])
    nxt = last + timedelta(hours=8)
    return (True,0) if datetime.now()>=nxt else (False,(nxt-datetime.now()).total_seconds())

def fmt(sec): return f"{int(sec//3600)}ч {int((sec%3600)//60)}м"

# ========== АНТИ-МАТ ==========
BAD = ["хуй","пизда","ебать","блядь","сука","гандон","пидор","нахуй","похуй","залупа","мудак","долбоёб","хуесос"]
def censor(text, uid):
    if is_vip(uid): return text
    for w in BAD: text = re.sub(re.escape(w), "*"*len(w), text, flags=re.IGNORECASE)
    return text

# ========== КВЕСТЫ ==========
POOL = [
    {"d":"Написать пост","t":"post","n":1,"r":"luck+1"},
    {"d":"Написать 2 поста","t":"post","n":2,"r":"luck+2","rare":1},
    {"d":"Пост >200 символов","t":"len","n":200,"r":"rating+1"},
    {"d":"Получить 1 лайк","t":"likes_recv","n":1,"r":"rating+0.5"},
    {"d":"Получить 3 лайка","t":"likes_recv","n":3,"r":"rating+1"},
    {"d":"Получить 5 лайков","t":"likes_recv","n":5,"r":"luck+2","rare":1},
    {"d":"Поставить 1 лайк","t":"likes_give","n":1,"r":"luck+0.5"},
    {"d":"Поставить 3 лайка","t":"likes_give","n":3,"r":"luck+1","rare":1},
    {"d":"Пригласить друга","t":"ref","n":1,"r":"luck+1"},
    {"d":"2 друга","t":"ref","n":2,"r":"luck+2","rare":1},
    {"d":"Реферал написал пост","t":"ref_post","n":1,"r":"rating+1"},
    {"d":"Крутнуть казино","t":"casino","n":1,"r":"luck+0.5"},
    {"d":"2 крутки","t":"casino","n":2,"r":"luck+1","rare":1},
    {"d":"Выиграть в казино","t":"casino_win","n":1,"r":"luck+2"},
    {"d":"Поднять рейтинг на 1%","t":"rating_up","n":1,"r":"rating+0.5"},
    {"d":"Поднять на 3%","t":"rating_up","n":3,"r":"rating+1","rare":1},
    {"d":"Заходить 3 дня","t":"streak","n":3,"r":"luck+1"},
    {"d":">10 минут","t":"time","n":600,"r":"rating+1","rare":1}
]

def gen_quests(uid):
    today = datetime.now().date().isoformat()
    u = get_user(uid)
    if not u or (u.get("quests") and u["quests"].get("date")==today): return
    avail = [q for q in POOL if not q.get("rare") or random.random()<0.2]
    sel = random.sample(avail, min(3, len(avail)))
    q = {"date":today, "tasks":[], "done":[False]*3, "prog":[0]*3}
    for i,qq in enumerate(sel):
        q["tasks"].append({"d":qq["d"],"t":qq["t"],"n":qq["n"],"r":qq["r"]})
    u["quests"] = q; u["bonus_ready"] = False; save()

def upd_quest(uid, typ, val=1, extra=None):
    u = get_user(uid)
    if not u or "quests" not in u: return
    q = u["quests"]
    if q.get("date") != datetime.now().date().isoformat(): return
    changed = False
    for i,t in enumerate(q["tasks"]):
        if q["done"][i]: continue
        match = False
        if t["t"] == typ: match = True
        elif t["t"]=="len" and typ=="post" and extra and extra>t["n"]: match = True
        elif t["t"]=="ref_post" and typ=="referral_post": match = True
        if match:
            q["prog"][i] += val
            if q["prog"][i] >= t["n"]:
                q["done"][i] = True
                if t["r"].startswith("luck+"): u["luck"] = min(50.0, u["luck"]+float(t["r"][5:]))
                elif t["r"].startswith("rating+"): u["rating"] = min(95.0, u["rating"]+float(t["r"][7:]))
                changed = True
    if changed:
        if all(q["done"]): u["bonus_ready"] = True
        save()

# ========== РАССЫЛКА ==========
def send_post(post, admin_id, force=False):
    aid = post["user_id"]; author = get_user(aid)
    if not author: return 0
    recipients = []
    for uid,ud in data["users"].items():
        if uid==aid or uid in data["banned"]: continue
        if ud.get("silencer_until"):
            try:
                if datetime.now() < datetime.fromisoformat(ud["silencer_until"]): continue
                else: ud["silencer_until"] = None
            except: ud["silencer_until"] = None
        recipients.append((uid,ud))
    if not recipients:
        try: bot.send_message(int(aid), "😢 Нет получателей")
        except: pass
        return 0
    total = len(recipients); log("POST", f"Рассылка от {name(aid)}. Всего: {total}")
    if force: guaranteed = total
    else:
        guaranteed = max(1, int(total*0.01))
        random.shuffle(recipients)
    g_recip = recipients[:guaranteed]; c_recip = recipients[guaranteed:]
    sent = 0; pid = post["id"]
    data["post_contents"][str(pid)] = {"text":post["text"],"author_id":aid,"author_name":name(aid)}
    if str(pid) not in data["reactions"]: data["reactions"][str(pid)] = {"likes":[],"dislikes":[],"complaints":[]}
    if str(pid) not in data["post_history"]: data["post_history"][str(pid)] = {}
    em = emoji(aid); ftext = f"<i>{post['text']}</i>"
    if "my_posts" not in author: author["my_posts"] = []
    if pid not in author["my_posts"]: author["my_posts"].append(pid)
    if "posts_data" not in author: author["posts_data"] = {}
    author["posts_data"][str(pid)] = {"text":post["text"],"date":post["time"],"likes":0,"dislikes":0}

    for uid,ud in g_recip:
        try:
            mk = MK(row_width=3)
            mk.add(KB(f"👍 0", callback_data=f"like_{pid}"), KB(f"👎 0", callback_data=f"dislike_{pid}"), KB("⚠️", callback_data=f"complaint_{pid}"))
            if is_admin(uid): mk.add(KB("🚫 УДАЛИТЬ У ВСЕХ", callback_data=f"global_delete_{pid}"))
            msg = bot.send_message(int(uid), f"📢 <b>Пост</b> {em} от {name(aid)}:\n\n{ftext}", parse_mode="HTML", reply_markup=mk)
            sent += 1
            author["rating"] = min(95.0, author["rating"]+0.01)
            data["post_history"][str(pid)][str(uid)] = msg.message_id
            author["weekly"] += 5; author["weekly_posts"] += 1
        except Exception as e: log("ERROR", f"Ошибка {uid}: {e}")

    chance_hits = 0
    for uid,ud in c_recip:
        if force: final = 100
        else:
            ref_bonus = 0
            if author.get("refs"):
                total_ref = sum(get_user(rid).get("rating",0) for rid in author["refs"] if get_user(rid))
                ref_bonus = total_ref/100
            final = ud["incoming"] + (author["rating"]/2) + (author["luck"]/10) + ref_bonus
            final = max(5, min(95, final))
        if random.uniform(0,100) <= final:
            try:
                mk = MK(row_width=3)
                mk.add(KB(f"👍 0", callback_data=f"like_{pid}"), KB(f"👎 0", callback_data=f"dislike_{pid}"), KB("⚠️", callback_data=f"complaint_{pid}"))
                if is_admin(uid): mk.add(KB("🚫 УДАЛИТЬ У ВСЕХ", callback_data=f"global_delete_{pid}"))
                msg = bot.send_message(int(uid), f"📢 <b>Пост</b> {em} от {name(aid)}:\n\n{ftext}", parse_mode="HTML", reply_markup=mk)
                sent += 1; chance_hits += 1
                author["rating"] = min(95.0, author["rating"]+0.01)
                data["post_history"][str(pid)][str(uid)] = msg.message_id
                author["weekly"] += 5; author["weekly_posts"] += 1
            except Exception as e: log("ERROR", f"Ошибка {uid}: {e}")

    log("POST", f"✅ Доставлено {sent}/{total} (гарантия {guaranteed}, шанс {chance_hits})")
    try:
        bot.send_message(int(aid), f"✅ <b>Твой пост разослан!</b>\n📊 Доставлено {sent}/{total}\n📈 Рейтинг +{0.01*sent:.2f}%", parse_mode="HTML")
    except: pass
    data["stats"]["posts_sent"] += 1; save()
    return sent

def del_global(pid):
    pid = str(pid)
    if pid not in data["post_history"]: return 0
    cnt = 0
    for uid,mid in data["post_history"][pid].items():
        try: bot.delete_message(int(uid), mid); cnt += 1
        except: pass
    del data["post_history"][pid]
    for k in ["post_contents","reactions"]:
        if pid in data[k]: del data[k][pid]
    save(); return cnt

def upd_react(pid, cid, mid):
    r = data["reactions"].get(str(pid), {"likes":[],"dislikes":[],"complaints":[]})
    mk = MK(row_width=3).add(KB(f"👍 {len(r['likes'])}", callback_data=f"like_{pid}"),
                            KB(f"👎 {len(r['dislikes'])}", callback_data=f"dislike_{pid}"),
                            KB("⚠️", callback_data=f"complaint_{pid}"))
    try: bot.edit_message_reply_markup(cid, mid, reply_markup=mk)
    except: pass

def top_users():
    lst = [{"name":name(uid),"rating":u["rating"],"luck":u["luck"]} for uid,u in data["users"].items() if uid not in data["banned"]]
    return sorted(lst, key=lambda x: x["rating"], reverse=True)[:10]

def top_weekly(lim=10):
    users = [{"id":uid,"name":name(uid),"act":u.get("weekly",0)} for uid,u in data["users"].items() if uid not in data["banned"] and u.get("weekly",0)>0]
    return sorted(users, key=lambda x: x["act"], reverse=True)[:lim]

def award_weekly():
    now = datetime.now()
    if not (now.weekday()==4 and now.hour==12 and now.minute==0): return
    top = top_weekly(1)
    if top:
        try: bot.send_message(int(top[0]["id"]), f"🎁 Ты самый активный! Получи 15 ⭐ от {OWNER}")
        except: pass

def reset_weekly():
    if datetime.now().weekday()!=5: return
    for u in data["users"].values(): u["weekly"] = u["weekly_posts"] = u["weekly_likes"] = 0
    log("INFO", "Активность сброшена"); save()

def tax():
    cnt = 0
    for uid,u in data["users"].items():
        if uid in data["banned"]: continue
        u["rating"] -= 1.0
        u["rating"] = max(10.0 if (is_vip(uid) or is_verified(uid)) else 5.0, u["rating"])
        cnt += 1
    log("INFO", f"Налог -1% у {cnt}"); save()

# ========== КЛАВИАТУРЫ ==========
def main_kb(): return MK(row_width=2).add(
    KB("📝 Написать пост","write_post"), KB("🎰 Бонус","casino"),
    KB("👥 Рефералы","referrals"), KB("📊 Статистика","stats"),
    KB("🏆 Топ-10","top"), KB("🔄 Конвертация","convert"),
    KB("🎒 Инвентарь","inventory"), KB("📋 Квесты","quests"),
    KB("⭐ Магазин","shop"), KB("ℹ️ Инфо","info"),
    KB("📋 История постов","post_history")
)
def casino_kb(): return MK().add(KB("🎲 Крутка","casino_spin"), KB("◀️ Назад","main_menu"))
def cancel_kb(): return MK().add(KB("❌ ОТМЕНА","cancel_post"))

def admin_kb(): return MK(row_width=2).add(
    KB("📝 Посты","admin_posts_list"), KB("📢 Интерпол","admin_interpol"),
    KB("👑 VIP","admin_vip_list"), KB("✅ Вериф","admin_verified_list"),
    KB("👥 Админы","admin_admins_list"), KB("🚫 Баны","admin_bans_list"),
    KB("📊 Статистика","admin_stats"), KB("📈 Активность","admin_activity")
)

def admin_posts_kb(posts):
    mk = MK(row_width=1)
    for i,p in enumerate(posts[:5]):
        short = p['text'][:30]+"..." if len(p['text'])>30 else p['text']
        mk.add(KB(f"{i+1}. {short}", f"admin_post_{p['id']}"))
    mk.add(KB("◀️ Назад","admin_main")); return mk

def admin_post_kb(pid): return MK(row_width=2).add(
    KB("✅ ОДОБРИТЬ",f"approve_{pid}"), KB("❌ ОТКЛОНИТЬ",f"reject_{pid}"),
    KB("🚫 ЗАБАНИТЬ",f"ban_user_{pid}"), KB("📢 ИНТЕРПОЛ",f"interpol_{pid}"),
    KB("◀️ К списку","admin_posts_list")
)

def users_kb(users, pref, back):
    mk = MK(row_width=1)
    for i,uid in enumerate(users[:10]): mk.add(KB(f"{i+1}. {name(uid)}", f"{pref}_{uid}"))
    mk.add(KB("◀️ Назад", back)); return mk

def user_act_kb(uid, typ):
    mk = MK(row_width=2)
    if typ=="vip": mk.add(KB("❌ СНЯТЬ VIP",f"remove_vip_{uid}"), KB("◀️ Назад","admin_vip_list"))
    elif typ=="verified": mk.add(KB("❌ СНЯТЬ ВЕРИФ",f"remove_verified_{uid}"), KB("◀️ Назад","admin_verified_list"))
    elif typ=="admin" and uid not in [str(a) for a in MASTER_ADMINS]:
        mk.add(KB("❌ СНЯТЬ АДМИНА",f"remove_admin_{uid}"), KB("◀️ Назад","admin_admins_list"))
    elif typ=="banned": mk.add(KB("✅ РАЗБАНИТЬ",f"unban_{uid}"), KB("◀️ Назад","admin_bans_list"))
    return mk

def inv_kb(u):
    mk = MK(row_width=2); inv = u.get("inv",{})
    if inv.get("amulet"): mk.add(KB("🍀 Амулет","use_amulet"))
    if inv.get("silencer"):
        if u.get("silencer_until"): mk.add(KB("🔇 Выкл. глушитель","deactivate_silencer"))
        else: mk.add(KB("🔇 Вкл. глушитель","activate_silencer"))
    if inv.get("vip_pass"): mk.add(KB("👑 VIP-пропуск","use_vippass"))
    mk.add(KB("◀️ Назад","main_menu")); return mk

def history_kb(u):
    mk = MK(row_width=1)
    for pid in u.get("my_posts",[])[-5:]:
        d = u.get("posts_data",{}).get(str(pid),{})
        txt = d.get("text","")[:20]+"..."; likes = d.get("likes",0); dis = d.get("dislikes",0); date = d.get("date","")[:10]
        mk.add(KB(f"📝 {txt} [{likes}👍 {dis}👎] {date}", f"post_detail_{pid}"))
    mk.add(KB("◀️ Назад","main_menu")); return mk

def post_detail_kb(pid): return MK(row_width=2).add(
    KB("🔁 Повторить",f"retry_post_{pid}"), KB("🗑 Удалить у всех",f"delete_my_post_{pid}"),
    KB("◀️ Назад","post_history")
)

# ========== КОМАНДЫ ==========
@bot.message_handler(commands=['start'])
def start(msg):
    uid = msg.from_user.id
    if is_banned(uid): return bot.send_message(uid, "🚫 Вы забанены.")
    u = get_user(uid); u["first_name"] = msg.from_user.first_name; u["username"] = msg.from_user.username
    args = msg.text.split()
    if len(args)>1:
        ref = args[1]
        if ref!=str(uid) and not u["referrer"]:
            ref_u = get_user(ref)
            if ref_u and len(ref_u["refs"])<max_refs(ref) and str(uid) not in ref_u["refs"]:
                u["referrer"] = ref
                ref_u["refs"].append(str(uid))
                ref_u["luck"] = min(50.0, ref_u["luck"]+1.0)
                try: bot.send_message(int(ref), f"🎉 Новый реферал: {name(uid)}\nУдача +1%")
                except: pass
                upd_quest(ref, "ref", 1); save()
    gen_quests(uid)
    bot.send_message(uid, f"🎩 <b>LowHigh</b> 🎰\n\nСтатус: {emoji(uid)}\n📈 Рейтинг: {u['rating']:.1f}%\n🍀 Удача: {u['luck']:.1f}%\n⏱ КД: {post_cd(uid)}ч",
                     parse_mode="HTML", reply_markup=main_kb())
    log("INFO", f"Юзер {uid} зашёл")

@bot.message_handler(commands=['admin'])
def admin_panel(msg):
    uid = msg.from_user.id
    if not is_admin(uid): return bot.send_message(uid, "🚫 Не админ")
    bot.send_message(uid, "👑 <b>АДМИН-ПАНЕЛЬ</b>", parse_mode="HTML", reply_markup=admin_kb())

@bot.message_handler(commands=['post'])
def cmd_post(msg):
    uid = msg.from_user.id
    if is_banned(uid): return bot.send_message(uid, "🚫 Забанен")
    u = get_user(uid)
    ok,cd = check_post_cd(u)
    if not ok: return bot.send_message(uid, f"⏳ Подожди {fmt(cd)}")
    pred = max(5, min(95, u["rating"]/2 + u["luck"]/10))
    bot.send_message(uid, f"📊 Прогноз: {pred:.1f}%\n\n📝 Отправь текст (макс {max_len(uid)} символов):", reply_markup=cancel_kb())
    bot.register_next_step_handler(msg, receive_post)

@bot.message_handler(commands=['casino'])
def cmd_casino(msg):
    uid = msg.from_user.id
    if is_banned(uid): return
    u = get_user(uid)
    ok,cd = casino_cd(u)
    txt = f"🎰 Шанс: {u['luck']:.2f}%\n"
    if u.get("bonus_ready"): txt += "🔥 Бонус +20% готов!\n"
    txt += "✅ Можно играть!" if ok else f"⏳ Жди {fmt(cd)}"
    bot.send_message(uid, txt, reply_markup=casino_kb())

@bot.message_handler(commands=['spin'])
def cmd_spin(msg):
    uid = msg.from_user.id
    if is_banned(uid): return
    u = get_user(uid)
    ok,cd = casino_cd(u)
    if not ok: return bot.send_message(uid, f"⏳ Подожди {fmt(cd)}")
    old = u["rating"]
    u["rating"] = max(5.0, u["rating"]-1.0)
    if is_vip(uid) or is_verified(uid): u["rating"] = max(10.0, u["rating"])
    bonus = 20 if u.get("bonus_ready") else 0
    if bonus: u["bonus_ready"] = False
    if random.uniform(0,100) <= (u["luck"]+bonus):
        item = random.choice(["amulet","silencer","vip_pass"])
        inv = u.get("inv",{})
        if inv.get(item,0)==0:
            inv[item]=1; u["inv"]=inv
            res = f"🎉 ПОБЕДА! Ты выиграл предмет: {item}!"
        else:
            u["rating"] = min(95.0, u["rating"]+5.0)
            res = "🎉 ПОБЕДА! +5% к рейтингу (предмет уже есть)"
        u["wins"] += 1; u["fails"] = 0; data["stats"]["wins"] += 1
        upd_quest(uid, "casino_win", 1)
    else:
        u["fails"] += 1
        inc = u["fails"]*0.01
        u["luck"] = min(50.0, u["luck"]+inc)
        res = f"😢 ПРОИГРЫШ\nУдача +{inc:.2f}%"
    u["last_casino"] = datetime.now().isoformat()
    u["total_casino"] += 1; u["weekly"] += 1; data["stats"]["attempts"] += 1
    upd_quest(uid, "casino", 1); save()
    bot.send_message(uid, res, parse_mode="HTML")

@bot.message_handler(commands=['top'])
def cmd_top(msg):
    uid = msg.from_user.id
    if is_banned(uid): return
    top = top_users()
    txt = "🏆 <b>ТОП-10</b>\n\n"
    for i,u in enumerate(top,1):
        medal = "🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else "▫️"
        txt += f"{medal} {i}. {u['name']} — 📈 {u['rating']:.1f}% | 🍀 {u['luck']:.1f}%\n"
    bot.send_message(uid, txt, parse_mode="HTML")

@bot.message_handler(commands=['help'])
def cmd_help(msg):
    bot.send_message(msg.from_user.id, """
<b>КОМАНДЫ</b>
post - Написать пост
casino - Инфо о казино
spin - Крутка
top - Топ-10
convert - 5% рейтинга → 1% удачи
start - Меню
help - Справка
/admin - Админка
""", parse_mode="HTML")

@bot.message_handler(commands=['convert'])
def cmd_convert(msg):
    uid = msg.from_user.id
    if is_banned(uid): return
    u = get_user(uid)
    if u.get("last_convert"):
        if datetime.now().date() == datetime.fromisoformat(u["last_convert"]).date():
            return bot.send_message(uid, "❌ Уже сегодня")
    if u["rating"] < 5.1: return bot.send_message(uid, "❌ Мало рейтинга (мин 5.1%)")
    u["rating"] -= 5.0; u["luck"] = min(50.0, u["luck"]+1.0)
    u["last_convert"] = datetime.now().isoformat(); save()
    bot.send_message(uid, f"✅ Конвертация: рейтинг {u['rating']:.1f}%, удача {u['luck']:.1f}%")

# ========== АДМИН-КОМАНДЫ ==========
@bot.message_handler(commands=['setrating'])
def set_rating(msg):
    uid = msg.from_user.id
    if not is_admin(uid): return
    args = msg.text.split()
    if len(args)<2: return bot.send_message(uid, "❌ /setrating [ID] [знач]")
    try:
        if len(args)==3: target,val = args[1],float(args[2])
        else: target,val = str(uid),float(args[1])
        u = get_user(target)
        if not u: return bot.send_message(uid, "❌ Нет юзера")
        old = u["rating"]; u["rating"] = max(5.0, min(95.0, val)); fix_rating(target); save()
        bot.send_message(uid, f"✅ Рейтинг {target}: {old:.1f}% → {u['rating']:.1f}%")
        if target!=str(uid):
            try: bot.send_message(int(target), f"👑 Админ изменил рейтинг: {old:.1f}% → {u['rating']:.1f}%")
            except: pass
    except: bot.send_message(uid, "❌ Ошибка")

@bot.message_handler(commands=['setluck'])
def set_luck(msg):
    uid = msg.from_user.id
    if not is_admin(uid): return
    args = msg.text.split()
    if len(args)<2: return bot.send_message(uid, "❌ /setluck [ID] [знач]")
    try:
        if len(args)==3: target,val = args[1],float(args[2])
        else: target,val = str(uid),float(args[1])
        u = get_user(target)
        if not u: return bot.send_message(uid, "❌ Нет юзера")
        old = u["luck"]; u["luck"] = max(1.0, min(50.0, val)); save()
        bot.send_message(uid, f"✅ Удача {target}: {old:.1f}% → {u['luck']:.1f}%")
        if target!=str(uid):
            try: bot.send_message(int(target), f"👑 Админ изменил удачу: {old:.1f}% → {u['luck']:.1f}%")
            except: pass
    except: bot.send_message(uid, "❌ Ошибка")

@bot.message_handler(commands=['addadmin'])
def add_admin(msg):
    uid = msg.from_user.id
    if not is_admin(uid): return
    args = msg.text.split()
    if len(args)<2: return bot.send_message(uid, "❌ /addadmin ID")
    try:
        new = str(int(args[1]))
        if new not in data["admins"]:
            data["admins"].append(new); save()
            bot.send_message(uid, f"✅ Админ {new} добавлен")
            try: bot.send_message(int(new), "🎉 Ты теперь админ! /admin")
            except: pass
        else: bot.send_message(uid, "⚠️ Уже админ")
    except: bot.send_message(uid, "❌ Неверный ID")

@bot.message_handler(commands=['removeadmin'])
def remove_admin(msg):
    uid = msg.from_user.id
    if not is_admin(uid): return
    args = msg.text.split()
    if len(args)<2: return bot.send_message(uid, "❌ /removeadmin ID")
    try:
        rem = str(int(args[1]))
        if rem==str(uid): return bot.send_message(uid, "❌ Нельзя себя")
        if rem in [str(a) for a in MASTER_ADMINS]: return bot.send_message(uid, "❌ Нельзя главного")
        if rem in data["admins"]:
            data["admins"].remove(rem); save()
            bot.send_message(uid, f"✅ Админ {rem} удален")
            try: bot.send_message(int(rem), "❌ Ты больше не админ")
            except: pass
        else: bot.send_message(uid, "⚠️ Не админ")
    except: bot.send_message(uid, "❌ Ошибка")

@bot.message_handler(commands=['addvip'])
def add_vip(msg):
    uid = msg.from_user.id
    if not is_admin(uid): return
    args = msg.text.split()
    if len(args)<2: return bot.send_message(uid, "❌ /addvip ID [дни]")
    try:
        target = str(int(args[1]))
        u = get_user(target)
        if not u: return bot.send_message(uid, "❌ Нет юзера")
        if len(args)>=3:
            days = int(args[2])
            until = datetime.now()+timedelta(days=days)
            u["vip_until"] = until.isoformat()
            bot.send_message(uid, f"✅ VIP на {days} дней до {until.strftime('%Y-%m-%d %H:%M')}")
            try: bot.send_message(int(target), f"👑 Поздравляем! Теперь ты VIP на {days} дней!\nКД 2ч, рефералов 50, посты 500 символов")
            except: pass
        else:
            if target not in data.get("vip",[]):
                if "vip" not in data: data["vip"] = []
                data["vip"].append(target)
                bot.send_message(uid, f"✅ Постоянный VIP для {target}")
                try: bot.send_message(int(target), f"👑 Поздравляем! Теперь ты VIP!\nКД 2ч, рефералов 50, посты 500 символов")
                except: pass
            else: bot.send_message(uid, "⚠️ Уже VIP")
        fix_rating(target); save()
    except Exception as e: bot.send_message(uid, f"❌ Ошибка: {e}")

@bot.message_handler(commands=['vipinfo'])
def vipinfo(msg):
    uid = msg.from_user.id
    if not is_admin(uid): return
    args = msg.text.split()
    if len(args)<2: return bot.send_message(uid, "❌ /vipinfo ID")
    try:
        target = str(int(args[1]))
        u = get_user(target)
        if not u: return bot.send_message(uid, "❌ Нет юзера")
        if u.get("vip_until"):
            until = datetime.fromisoformat(u["vip_until"])
            if until>datetime.now():
                left = until-datetime.now()
                bot.send_message(uid, f"👑 VIP до {until.strftime('%Y-%m-%d %H:%M')}\nОсталось: {left.days} дн. {left.seconds//3600} ч.")
            else: u["vip_until"] = None; save(); bot.send_message(uid, "👑 VIP истёк")
        elif target in data.get("vip",[]): bot.send_message(uid, "👑 Постоянный VIP")
        else: bot.send_message(uid, "❌ Не VIP")
    except: bot.send_message(uid, "❌ Ошибка")

@bot.message_handler(commands=['removevip'])
def remove_vip(msg):
    uid = msg.from_user.id
    if not is_admin(uid): return
    args = msg.text.split()
    if len(args)<2: return bot.send_message(uid, "❌ /removevip ID")
    try:
        target = str(int(args[1]))
        u = get_user(target); removed = False
        if u and u.get("vip_until"): u["vip_until"] = None; removed = True
        if target in data.get("vip",[]): data["vip"].remove(target); removed = True
        if removed:
            save(); bot.send_message(uid, f"✅ VIP снят с {target}")
            try: bot.send_message(int(target), "❌ VIP статус снят")
            except: pass
        else: bot.send_message(uid, "⚠️ Не VIP")
    except: bot.send_message(uid, "❌ Ошибка")

@bot.message_handler(commands=['addverified'])
def add_verified(msg):
    uid = msg.from_user.id
    if not is_admin(uid): return
    args = msg.text.split()
    if len(args)<2: return bot.send_message(uid, "❌ /addverified ID")
    try:
        target = str(int(args[1]))
        if target not in data.get("verified",[]):
            if "verified" not in data: data["verified"] = []
            data["verified"].append(target)
            fix_rating(target); save()
            bot.send_message(uid, f"✅ Пользователь {target} верифицирован")
            try: bot.send_message(int(target), f"✅ Поздравляем! Теперь ты верифицирован!\nПосты без модерации, рефералов 25, посты 300 символов")
            except: pass
        else: bot.send_message(uid, "⚠️ Уже верифицирован")
    except: bot.send_message(uid, "❌ Ошибка")

@bot.message_handler(commands=['removeverified'])
def remove_verified(msg):
    uid = msg.from_user.id
    if not is_admin(uid): return
    args = msg.text.split()
    if len(args)<2: return bot.send_message(uid, "❌ /removeverified ID")
    try:
        target = str(int(args[1]))
        if target in data.get("verified",[]):
            data["verified"].remove(target); save()
            bot.send_message(uid, f"✅ Верификация снята с {target}")
            try: bot.send_message(int(target), "❌ Верификация снята")
            except: pass
        else: bot.send_message(uid, "⚠️ Не верифицирован")
    except: bot.send_message(uid, "❌ Ошибка")

@bot.message_handler(commands=['ban'])
def ban(msg):
    uid = msg.from_user.id
    if not is_admin(uid): return
    args = msg.text.split()
    if len(args)<2: return bot.send_message(uid, "❌ /ban ID")
    try:
        target = str(int(args[1]))
        if target not in data["banned"]:
            data["banned"].append(target); save()
            bot.send_message(uid, f"🚫 Пользователь {target} забанен")
            try: bot.send_message(int(target), "🚫 Вы забанены")
            except: pass
        else: bot.send_message(uid, "⚠️ Уже в бане")
    except: bot.send_message(uid, "❌ Ошибка")

@bot.message_handler(commands=['unban'])
def unban(msg):
    uid = msg.from_user.id
    if not is_admin(uid): return
    args = msg.text.split()
    if len(args)<2: return bot.send_message(uid, "❌ /unban ID")
    try:
        target = str(int(args[1]))
        if target in data["banned"]:
            data["banned"].remove(target); save()
            bot.send_message(uid, f"✅ Пользователь {target} разбанен")
            try: bot.send_message(int(target), "✅ Вы разбанены")
            except: pass
        else: bot.send_message(uid, "⚠️ Не в бане")
    except: bot.send_message(uid, "❌ Ошибка")

@bot.message_handler(commands=['delpost'])
def del_post(msg):
    uid = msg.from_user.id
    if not is_admin(uid): return bot.send_message(uid, "🚫 Не админ")
    args = msg.text.split()
    if len(args)<2: return bot.send_message(uid, "❌ /delpost ID")
    cnt = del_global(args[1])
    bot.send_message(uid, f"✅ Удалено у {cnt}" if cnt else "❌ Пост не найден")

# ========== КОЛЛБЭКИ ==========
@bot.callback_query_handler(func=lambda c: True)
def callback(c):
    uid = c.from_user.id
    u = get_user(uid)
    if not u and not is_banned(uid): return
    cmd = c.data

    # Реакции
    if cmd.startswith("like_"):
        pid = cmd.split("_")[1]
        r = data["reactions"].setdefault(pid, {"likes":[],"dislikes":[],"complaints":[]})
        suid = str(uid); aid = data["post_contents"].get(pid,{}).get("author_id")
        if suid in r["likes"]:
            r["likes"].remove(suid); bot.answer_callback_query(c.id, "Лайк убран")
        else:
            if suid in r["dislikes"]: r["dislikes"].remove(suid)
            r["likes"].append(suid); bot.answer_callback_query(c.id, "Лайк поставлен")
            if aid and aid!=suid:
                a = get_user(aid)
                if a:
                    a["rating"] = min(95.0, a["rating"]+0.05)
                    a["weekly"] += 2; a["weekly_likes"] += 1
                    if "posts_data" in a and pid in a["posts_data"]: a["posts_data"][pid]["likes"] += 1
                    upd_quest(aid, "likes_recv", 1)
            upd_quest(uid, "likes_give", 1)
        save(); upd_react(pid, c.message.chat.id, c.message.message_id); return

    if cmd.startswith("dislike_"):
        pid = cmd.split("_")[1]
        r = data["reactions"].setdefault(pid, {"likes":[],"dislikes":[],"complaints":[]})
        suid = str(uid); aid = data["post_contents"].get(pid,{}).get("author_id")
        if suid in r["dislikes"]:
            r["dislikes"].remove(suid); bot.answer_callback_query(c.id, "Дизлайк убран")
        else:
            if suid in r["likes"]: r["likes"].remove(suid)
            r["dislikes"].append(suid); bot.answer_callback_query(c.id, "Дизлайк поставлен")
            if aid and aid!=suid:
                a = get_user(aid)
                if a:
                    a["rating"] = max(5.0, a["rating"]-0.03)
                    if is_vip(aid) or is_verified(aid): a["rating"] = max(10.0, a["rating"])
                    if "posts_data" in a and pid in a["posts_data"]: a["posts_data"][pid]["dislikes"] += 1
        save(); upd_react(pid, c.message.chat.id, c.message.message_id); return

    if cmd.startswith("complaint_"):
        pid = cmd.split("_")[1]
        info = data["post_contents"].get(pid,{})
        txt = info.get("text","?"); aname = info.get("author_name","?"); aid = info.get("author_id","?")
        r = data["reactions"].setdefault(pid, {"likes":[],"dislikes":[],"complaints":[]})
        suid = str(uid)
        if suid not in r["complaints"]:
            r["complaints"].append(suid)
            bot.answer_callback_query(c.id, "Жалоба отправлена")
            for admin_id in data.get("admins",[]):
                if admin_id!=suid:
                    try: bot.send_message(int(admin_id), f"⚠️ Жалоба на {pid}\nАвтор: {aname} ({aid})\n{txt}\n/delpost {pid}")
                    except: pass
        else: bot.answer_callback_query(c.id, "Уже жаловался")
        save(); return

    if cmd.startswith("global_delete_"):
        if not is_admin(uid): return bot.answer_callback_query(c.id, "Не админ")
        cnt = del_global(cmd.split("_")[2]); bot.answer_callback_query(c.id, f"Удалено у {cnt}"); return

    # Удаление обычных сообщений
    if not cmd.startswith("admin_") and cmd not in ["approve_","reject_","ban_user_","interpol_"]:
        try: bot.delete_message(uid, c.message.message_id)
        except: pass

    # Навигация
    if cmd=="main_menu": return bot.send_message(uid, "Главное меню:", reply_markup=main_kb())
    if cmd=="casino":
        ok,cd = casino_cd(u)
        txt = f"🎰 Шанс: {u['luck']:.2f}%\n"
        if u.get("bonus_ready"): txt += "🔥 Бонус +20% готов!\n"
        txt += "✅ Можно" if ok else f"⏳ {fmt(cd)}"
        return bot.send_message(uid, txt, reply_markup=casino_kb())

    if cmd=="casino_spin":
        ok,cd = casino_cd(u)
        if not ok: return bot.answer_callback_query(c.id, f"Жди {fmt(cd)}")
        old = u["rating"]; u["rating"] = max(5.0, u["rating"]-1.0)
        if is_vip(uid) or is_verified(uid): u["rating"] = max(10.0, u["rating"])
        bonus = 20 if u.get("bonus_ready") else 0
        if bonus: u["bonus_ready"] = False
        if random.uniform(0,100) <= (u["luck"]+bonus):
            item = random.choice(["amulet","silencer","vip_pass"])
            inv = u.get("inv",{})
            if inv.get(item,0)==0:
                inv[item]=1; u["inv"]=inv
                res = f"🎉 ПОБЕДА! Ты выиграл предмет: {item}!"
            else:
                u["rating"] = min(95.0, u["rating"]+5.0)
                res = "🎉 ПОБЕДА! +5% к рейтингу"
            u["wins"] += 1; u["fails"] = 0; data["stats"]["wins"] += 1
            upd_quest(uid, "casino_win", 1)
        else:
            u["fails"] += 1; inc = u["fails"]*0.01
            u["luck"] = min(50.0, u["luck"]+inc)
            res = f"😢 ПРОИГРЫШ\nУдача +{inc:.2f}%"
        u["last_casino"] = datetime.now().isoformat()
        u["total_casino"] += 1; u["weekly"] += 1; data["stats"]["attempts"] += 1
        upd_quest(uid, "casino", 1); save()
        return bot.edit_message_text(res, uid, c.message.message_id, parse_mode="HTML",
            reply_markup=MK().add(KB("🎰 Еще","casino"), KB("🏠 Меню","main_menu")))

    if cmd=="write_post":
        ok,cd = check_post_cd(u)
        if not ok: return bot.answer_callback_query(c.id, f"Жди {fmt(cd)}")
        pred = max(5, min(95, u["rating"]/2+u["luck"]/10))
        bot.send_message(uid, f"📊 Прогноз: {pred:.1f}%\n\n📝 Отправь текст (макс {max_len(uid)}):", reply_markup=cancel_kb())
        bot.register_next_step_handler_by_chat_id(uid, receive_post); return

    if cmd=="cancel_post":
        bot.clear_step_handler_by_chat_id(uid)
        return bot.send_message(uid, "❌ Отменено", reply_markup=main_kb())

    if cmd=="referrals":
        try: link = f"https://t.me/{bot.get_me().username}?start={uid}"
        except: link = "?"
        cnt = len(u.get("refs",[])); m = max_refs(uid)
        return bot.send_message(uid, f"👥 Рефералы: {cnt}/{m}\nСсылка: {link}",
            reply_markup=MK().add(KB("◀️ Назад","main_menu")))

    if cmd=="stats":
        likes = sum(len(r.get("likes",[])) for r in data["reactions"].values())
        dis = sum(len(r.get("dislikes",[])) for r in data["reactions"].values())
        ref_bonus = sum(get_user(rid).get("rating",0) for rid in u.get("refs",[]) if get_user(rid))/100 if u.get("refs") else 0
        txt = f"""📊 Твоя статистика
📈 Рейтинг: {u['rating']:.1f}%
🍀 Удача: {u['luck']:.2f}%
📻 Приём: {u['incoming']}%
💰 Бонус рефералов: +{ref_bonus:.2f}%
⏱ КД поста: {post_cd(uid)}ч
📝 Постов: {u['total_posts']}
🎰 Игр: {u['total_casino']}
🏆 Побед: {u['wins']}
👥 Рефералов: {len(u.get('refs',[]))}/{max_refs(uid)}
🌍 Глобально: 👍 {likes} 👎 {dis} 📨 {data['stats']['posts_sent']}"""
        return bot.send_message(uid, txt, reply_markup=MK().add(KB("◀️ Назад","main_menu")))

    if cmd=="top":
        t = top_users()
        txt = "🏆 ТОП-10\n\n"
        for i,u in enumerate(t,1):
            medal = "🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else "▫️"
            txt += f"{medal} {i}. {u['name']} — {u['rating']:.1f}%\n"
        return bot.send_message(uid, txt, reply_markup=MK().add(KB("◀️ Назад","main_menu")))

    if cmd=="convert":
        if u.get("last_convert") and datetime.now().date()==datetime.fromisoformat(u["last_convert"]).date():
            return bot.answer_callback_query(c.id, "Уже сегодня")
        if u["rating"]<5.1: return bot.answer_callback_query(c.id, "Мало рейтинга")
        u["rating"] -= 5.0; u["luck"] = min(50.0, u["luck"]+1.0)
        u["last_convert"] = datetime.now().isoformat(); save()
        bot.answer_callback_query(c.id, "✅ Конвертация")
        return bot.send_message(uid, f"Рейтинг {u['rating']:.1f}%, удача {u['luck']:.1f}%", reply_markup=main_kb())

    if cmd=="inventory":
        inv = u.get("inv",{}); sil = ""
        if u.get("silencer_until"):
            try:
                until = datetime.fromisoformat(u["silencer_until"])
                if until>datetime.now(): sil = f" (активен до {until.strftime('%H:%M')})"
                else: u["silencer_until"] = None
            except: u["silencer_until"] = None
        txt = f"🎒 Инвентарь\n🍀 Амулет: {inv.get('amulet',0)}\n🔇 Глушитель: {inv.get('silencer',0)}{sil}\n👑 VIP-пропуск: {inv.get('vip_pass',0)}"
        return bot.send_message(uid, txt, reply_markup=inv_kb(u))

    if cmd=="use_amulet":
        inv = u.get("inv",{})
        if inv.get("amulet",0):
            u["rating"] = min(95.0, u["rating"]+10.0)
            inv["amulet"] = 0; u["inv"] = inv; save()
            bot.answer_callback_query(c.id, "🍀 +10% рейтинга")
            return bot.send_message(uid, "Амулет использован!", reply_markup=main_kb())
        return bot.answer_callback_query(c.id, "Нет амулета")

    if cmd=="activate_silencer":
        inv = u.get("inv",{})
        if inv.get("silencer",0) and not u.get("silencer_until"):
            until = datetime.now()+timedelta(hours=8)
            u["silencer_until"] = until.isoformat()
            inv["silencer"] = 0; u["inv"] = inv; save()
            bot.answer_callback_query(c.id, "🔇 Глушитель включён")
            return bot.send_message(uid, f"Глушитель до {until.strftime('%H:%M')}", reply_markup=main_kb())
        return bot.answer_callback_query(c.id, "Нельзя")

    if cmd=="deactivate_silencer":
        if u.get("silencer_until"):
            u["silencer_until"] = None; save()
            bot.answer_callback_query(c.id, "🔇 Глушитель выключен")
            return bot.send_message(uid, "Глушитель деактивирован", reply_markup=main_kb())
        return bot.answer_callback_query(c.id, "Не активен")

    if cmd=="use_vippass":
        inv = u.get("inv",{})
        if inv.get("vip_pass",0):
            until = datetime.now()+timedelta(days=3)
            u["vip_until"] = until.isoformat()
            inv["vip_pass"] = 0; u["inv"] = inv; save()
            bot.answer_callback_query(c.id, "👑 VIP на 3 дня")
            return bot.send_message(uid, f"VIP до {until.strftime('%Y-%m-%d %H:%M')}", reply_markup=main_kb())
        return bot.answer_callback_query(c.id, "Нет пропуска")

    if cmd=="quests":
        gen_quests(uid); q = u.get("quests",{})
        if not q: return
        txt = "📋 КВЕСТЫ\n\n"
        for i,t in enumerate(q.get("tasks",[])):
            status = "✅" if q["done"][i] else "☐"
            prog = f"{q['prog'][i]}/{t['n']}" if not q["done"][i] else ""
            txt += f"{status} {t['d']} {prog} — {t['r']}\n"
        txt += f"\n🏆 Бонус: +20% к след. крутке " + ("✅" if u.get("bonus_ready") else "❌")
        return bot.send_message(uid, txt, reply_markup=MK().add(KB("◀️ Назад","main_menu")))

    if cmd=="shop":
        return bot.send_message(uid, f"""⭐ МАГАЗИН

Покупки через ЛС {OWNER}

👑 VIP на неделю — 100 ⭐
📈 +25% рейтинга — 50 ⭐
🎰 +10% удачи — 15 ⭐

📢 Реклама:
• 50 ⭐ — обычный пост (250 симв, без мата)
• 100 ⭐ — любой пост (400 симв, мат)
Рассылка ВСЕМ""", reply_markup=MK().add(KB("◀️ Назад","main_menu")))

    if cmd=="info":
        return bot.send_message(uid, f"""ℹ️ О ПРОЕКТЕ

👑 Владелец: {OWNER}
📌 Некоммерческая рассылка
🚫 Коммерцию не рекламировать!

🎁 Конкурс каждую пятницу в 12:00
Самый активный получает 15 ⭐""", reply_markup=MK().add(KB("◀️ Назад","main_menu")))

    if cmd=="post_history":
        posts = u.get("my_posts",[])
        if not posts: return bot.send_message(uid, "📭 У тебя пока нет постов", reply_markup=MK().add(KB("◀️ Назад","main_menu")))
        return bot.send_message(uid, "📋 ТВОИ ПОСТЫ", reply_markup=history_kb(u))

    if cmd.startswith("post_detail_"):
        pid = cmd.split("_")[2]
        pd = u.get("posts_data",{}).get(pid,{})
        if not pd: return bot.answer_callback_query(c.id, "Пост не найден")
        txt = pd.get("text","?"); likes = pd.get("likes",0); dis = pd.get("dislikes",0); date = pd.get("date","")[:10]
        return bot.edit_message_text(f"📝 <b>Пост от {date}</b>\n\n{txt}\n\n👍 {likes}  👎 {dis}",
            uid, c.message.message_id, parse_mode="HTML", reply_markup=post_detail_kb(pid))

    if cmd.startswith("retry_post_"):
        pid = cmd.split("_")[2]
        pd = u.get("posts_data",{}).get(pid,{})
        if not pd: return bot.answer_callback_query(c.id, "Пост не найден")
        ok,cd = check_post_cd(u)
        if not ok: return bot.answer_callback_query(c.id, f"Жди {fmt(cd)}")
        txt = pd.get("text","")
        post = {"id":int(time.time()*1000), "user_id":str(uid), "username":u.get("username"), "text":txt, "time":datetime.now().isoformat()}
        u["last_post"] = datetime.now().isoformat(); u["posts_count"] += 1
        sent = send_post(post, uid)
        u["total_posts"] += 1; save()
        bot.answer_callback_query(c.id, f"✅ Пост повторно разослан! Доставлено: {sent}")
        return bot.send_message(uid, f"✅ Пост повторно разослан!\nДоставлено: {sent}", reply_markup=main_kb())

    if cmd.startswith("delete_my_post_"):
        pid = cmd.split("_")[3]
        cnt = del_global(pid)
        if cnt:
            if pid in u.get("my_posts",[]): u["my_posts"].remove(pid)
            if pid in u.get("posts_data",{}): del u["posts_data"][pid]
            save()
            bot.answer_callback_query(c.id, f"🗑 Удалено у {cnt}")
            if u.get("my_posts"):
                return bot.edit_message_text("📋 ТВОИ ПОСТЫ", uid, c.message.message_id, reply_markup=history_kb(u))
            else:
                return bot.edit_message_text("📭 У тебя пока нет постов", uid, c.message.message_id,
                    reply_markup=MK().add(KB("◀️ Назад","main_menu")))
        return bot.answer_callback_query(c.id, "❌ Пост не найден")

    # ===== АДМИН-КОЛЛБЭКИ =====
    if not is_admin(uid): return

    if cmd=="admin_main":
        return bot.edit_message_text("👑 АДМИН-ПАНЕЛЬ", uid, c.message.message_id, reply_markup=admin_kb())

    if cmd=="admin_posts_list":
        if not data["posts"]:
            return bot.edit_message_text("📭 Нет постов", uid, c.message.message_id,
                reply_markup=MK().add(KB("◀️ Назад","admin_main")))
        return bot.edit_message_text(f"📝 Посты ({len(data['posts'])}):", uid, c.message.message_id,
            reply_markup=admin_posts_kb(data["posts"]))

    if cmd.startswith("admin_post_"):
        pid = cmd.split("_")[2]
        for p in data["posts"]:
            if str(p["id"])==pid:
                an = name(p["user_id"])
                return bot.edit_message_text(f"📝 Пост от {an}\n\n{p['text']}", uid, c.message.message_id,
                    parse_mode="HTML", reply_markup=admin_post_kb(pid))
        return

    if cmd.startswith("approve_"):
        pid = cmd.split("_")[1]
        for i,p in enumerate(data["posts"]):
            if str(p["id"])==pid:
                sent = send_post(p, uid)
                data["posts"].pop(i); save()
                # Уведомление админу (если включены)
                if u.get("notify", True):
                    bot.send_message(uid, f"✅ Пост одобрен. Доставлено: {sent}")
                if data["posts"]:
                    nxt = data["posts"][0]; an = name(nxt["user_id"])
                    bot.edit_message_text(f"✅ Одобрено. Доставлено: {sent}\n\n📝 Следующий от {an}\n\n{nxt['text']}",
                        uid, c.message.message_id, parse_mode="HTML", reply_markup=admin_post_kb(nxt['id']))
                else:
                    bot.edit_message_text(f"✅ Одобрено. Доставлено: {sent}\n\n📭 Больше нет постов",
                        uid, c.message.message_id, reply_markup=MK().add(KB("◀️ Назад","admin_main")))
                bot.answer_callback_query(c.id, "✅ Пост одобрен"); break
        return

    if cmd.startswith("reject_"):
        pid = cmd.split("_")[1]
        for i,p in enumerate(data["posts"]):
            if str(p["id"])==pid:
                data["posts"].pop(i); save()
                if u.get("notify", True):
                    bot.send_message(uid, "❌ Пост отклонен")
                if data["posts"]:
                    nxt = data["posts"][0]; an = name(nxt["user_id"])
                    bot.edit_message_text(f"❌ Отклонено\n\n📝 Следующий от {an}\n\n{nxt['text']}",
                        uid, c.message.message_id, parse_mode="HTML", reply_markup=admin_post_kb(nxt['id']))
                else:
                    bot.edit_message_text("❌ Отклонено\n\n📭 Больше нет постов",
                        uid, c.message.message_id, reply_markup=MK().add(KB("◀️ Назад","admin_main")))
                bot.answer_callback_query(c.id, "❌ Пост отклонен"); break
        return

    if cmd.startswith("ban_user_"):
        pid = cmd.split("_")[2]
        for p in data["posts"]:
            if str(p["id"])==pid:
                bid = p["user_id"]
                if bid not in data["banned"]:
                    data["banned"].append(bid); save()
                    bot.send_message(uid, f"🚫 {bid} ({name(bid)}) забанен")
                break
        return bot.answer_callback_query(c.id, "Готово")

    if cmd.startswith("interpol_"):
        pid = cmd.split("_")[1]
        for i,p in enumerate(data["posts"]):
            if str(p["id"])==pid:
                sent = send_post(p, uid, force=True)
                data["posts"].pop(i); save()
                bot.edit_message_text(f"📢 Интерпол: доставлено {sent}", uid, c.message.message_id)
                bot.answer_callback_query(c.id, f"✅ Разослано {sent}"); break
        return

    if cmd=="admin_interpol":
        bot.edit_message_text("📢 Отправь текст для рассылки ВСЕМ:", uid, c.message.message_id)
        bot.register_next_step_handler_by_chat_id(uid, receive_interpol_post); return

    # Списки
    if cmd=="admin_vip_list":
        vip = []
        for uu in data["users"]:
            if is_vip(uu): vip.append(uu)
        for uu in data.get("vip",[]):
            if uu not in vip: vip.append(uu)
        if not vip: return bot.edit_message_text("👑 Нет VIP", uid, c.message.message_id, reply_markup=MK().add(KB("◀️ Назад","admin_main")))
        return bot.edit_message_text(f"👑 VIP ({len(vip)}):", uid, c.message.message_id, reply_markup=users_kb(vip, "admin_vip", "admin_main"))

    if cmd.startswith("admin_vip_"):
        tid = cmd.split("_")[2]
        return bot.edit_message_text(f"👑 VIP\nID: {tid}\nИмя: {name(tid)}", uid, c.message.message_id,
            reply_markup=user_act_kb(tid, "vip"))

    if cmd=="admin_verified_list":
        ver = data.get("verified",[])
        if not ver: return bot.edit_message_text("✅ Нет верифицированных", uid, c.message.message_id, reply_markup=MK().add(KB("◀️ Назад","admin_main")))
        return bot.edit_message_text(f"✅ Верифицированные ({len(ver)}):", uid, c.message.message_id, reply_markup=users_kb(ver, "admin_verified", "admin_main"))

    if cmd.startswith("admin_verified_"):
        tid = cmd.split("_")[2]
        return bot.edit_message_text(f"✅ Вериф\nID: {tid}\nИмя: {name(tid)}", uid, c.message.message_id,
            reply_markup=user_act_kb(tid, "verified"))

    if cmd=="admin_admins_list":
        adm = data.get("admins",[])
        return bot.edit_message_text(f"👥 Админы ({len(adm)}):", uid, c.message.message_id, reply_markup=users_kb(adm, "admin_admin", "admin_main"))

    if cmd.startswith("admin_admin_"):
        tid = cmd.split("_")[2]
        return bot.edit_message_text(f"👥 Админ\nID: {tid}\nИмя: {name(tid)}", uid, c.message.message_id,
            reply_markup=user_act_kb(tid, "admin"))

    if cmd=="admin_bans_list":
        ban = data.get("banned",[])
        if not ban: return bot.edit_message_text("🚫 Нет банов", uid, c.message.message_id, reply_markup=MK().add(KB("◀️ Назад","admin_main")))
        return bot.edit_message_text(f"🚫 Баны ({len(ban)}):", uid, c.message.message_id, reply_markup=users_kb(ban, "admin_banned", "admin_main"))

    if cmd.startswith("admin_banned_"):
        tid = cmd.split("_")[2]
        return bot.edit_message_text(f"🚫 Бан\nID: {tid}\nИмя: {name(tid)}", uid, c.message.message_id,
            reply_markup=user_act_kb(tid, "banned"))

    if cmd=="admin_stats":
        txt = f"""📊 СТАТИСТИКА
👥 Всего: {len(data['users'])}
🚫 Банов: {len(data['banned'])}
👑 VIP: {sum(1 for u in data['users'] if is_vip(u)) + len(data.get('vip',[]))}
✅ Вериф: {len(data.get('verified',[]))}
👥 Админов: {len(data.get('admins',[]))}
📝 Постов: {data['stats']['posts_sent']}
🎰 Игр: {data['stats']['attempts']}
🏆 Побед: {data['stats']['wins']}"""
        return bot.edit_message_text(txt, uid, c.message.message_id, reply_markup=MK().add(KB("◀️ Назад","admin_main")))

    if cmd=="admin_activity":
        top = top_weekly(10)
        txt = "📈 АКТИВНОСТЬ НЕДЕЛИ\n\n"
        if not top: txt += "Нет данных"
        else:
            for i,u in enumerate(top,1):
                medal = "🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else "▫️"
                txt += f"{medal} {i}. {u['name']} — {u['act']}\n"
            txt += "\n🏆 Пятница 12:00 — 15 ⭐"
        return bot.edit_message_text(txt, uid, c.message.message_id, reply_markup=MK().add(KB("◀️ Назад","admin_main")))

    # Действия с пользователями
    if cmd.startswith("remove_vip_"):
        tid = cmd.split("_")[2]; uu = get_user(tid); removed = False
        if uu and uu.get("vip_until"): uu["vip_until"] = None; removed = True
        if tid in data.get("vip",[]): data["vip"].remove(tid); removed = True
        if removed:
            save(); bot.answer_callback_query(c.id, "VIP снят")
            try: bot.send_message(int(tid), "❌ VIP статус снят")
            except: pass
        vip = []
        for uu in data["users"]:
            if is_vip(uu): vip.append(uu)
        for uu in data.get("vip",[]):
            if uu not in vip: vip.append(uu)
        if vip:
            bot.edit_message_text(f"👑 VIP ({len(vip)}):", uid, c.message.message_id, reply_markup=users_kb(vip, "admin_vip", "admin_main"))
        else:
            bot.edit_message_text("👑 Нет VIP", uid, c.message.message_id, reply_markup=MK().add(KB("◀️ Назад","admin_main")))
        return

    if cmd.startswith("remove_verified_"):
        tid = cmd.split("_")[2]
        if tid in data.get("verified",[]):
            data["verified"].remove(tid); save()
            bot.answer_callback_query(c.id, "Вериф снят")
            try: bot.send_message(int(tid), "❌ Верификация снята")
            except: pass
        ver = data.get("verified",[])
        if ver:
            bot.edit_message_text(f"✅ Верифицированные ({len(ver)}):", uid, c.message.message_id, reply_markup=users_kb(ver, "admin_verified", "admin_main"))
        else:
            bot.edit_message_text("✅ Нет верифицированных", uid, c.message.message_id, reply_markup=MK().add(KB("◀️ Назад","admin_main")))
        return

    if cmd.startswith("remove_admin_"):
        tid = cmd.split("_")[2]
        if tid in data.get("admins",[]) and tid not in [str(a) for a in MASTER_ADMINS]:
            data["admins"].remove(tid); save()
            bot.answer_callback_query(c.id, "Админ снят")
            try: bot.send_message(int(tid), "❌ Статус админа снят")
            except: pass
        adm = data.get("admins",[])
        bot.edit_message_text(f"👥 Админы ({len(adm)}):", uid, c.message.message_id, reply_markup=users_kb(adm, "admin_admin", "admin_main"))
        return

    if cmd.startswith("unban_"):
        tid = cmd.split("_")[1]
        if tid in data.get("banned",[]):
            data["banned"].remove(tid); save()
            bot.answer_callback_query(c.id, "Разбанен")
            try: bot.send_message(int(tid), "✅ Вы разбанены")
            except: pass
        ban = data.get("banned",[])
        if ban:
            bot.edit_message_text(f"🚫 Баны ({len(ban)}):", uid, c.message.message_id, reply_markup=users_kb(ban, "admin_banned", "admin_main"))
        else:
            bot.edit_message_text("🚫 Нет банов", uid, c.message.message_id, reply_markup=MK().add(KB("◀️ Назад","admin_main")))
        return

# ========== ПРИЁМ ПОСТОВ ==========
def receive_post(msg):
    uid = msg.from_user.id
    if is_banned(uid): return bot.send_message(uid, "🚫 Забанен")
    u = get_user(uid)
    ok,cd = check_post_cd(u)
    if not ok: return bot.send_message(uid, f"⏳ Жди {fmt(cd)}", reply_markup=main_kb())
    if msg.text and msg.text.lower() in ["отмена","cancel"]: return bot.send_message(uid, "❌ Отменено", reply_markup=main_kb())
    if msg.content_type!='text': return bot.send_message(uid, "❌ Только текст!", reply_markup=main_kb())
    if msg.text:
        ml = max_len(uid)
        if len(msg.text)>ml: return bot.send_message(uid, f"❌ Максимум {ml} символов", reply_markup=main_kb())
        txt = censor(msg.text, uid)
        post = {"id":int(time.time()*1000), "user_id":str(uid), "username":u.get("username"), "text":txt, "time":datetime.now().isoformat()}
        u["last_post"] = datetime.now().isoformat()
        u["posts_count"] += 1
        upd_quest(uid, "post", 1)
        if len(txt)>200: upd_quest(uid, "len", 200, extra=len(txt))
        if is_admin(uid) or is_verified(uid):
            sent = send_post(post, uid)
            u["total_posts"] += 1; save()
            bot.send_message(uid, f"✅ Пост разослан! Доставлено: {sent}", reply_markup=main_kb())
        else:
            data["posts"].append(post)
            u["total_posts"] += 1; save()
            bot.send_message(uid, "✅ Пост на модерации", reply_markup=main_kb())
            log("POST", f"Новый пост от {name(uid)}")
            for aid in data.get("admins",[]):
                if aid!=str(uid):
                    ad = get_user(aid)
                    if ad and ad.get("notify", True):
                        try: bot.send_message(int(aid), f"🆕 Новый пост от {name(uid)}!\n/admin")
                        except: pass

def receive_interpol_post(msg):
    uid = msg.from_user.id
    if not is_admin(uid): return
    if msg.content_type!='text': return bot.send_message(uid, "❌ Только текст!", reply_markup=admin_kb())
    if msg.text:
        post = {"id":int(time.time()*1000), "user_id":str(uid), "username":"ADMIN", "text":msg.text, "time":datetime.now().isoformat()}
        sent = send_post(post, uid, force=True)
        bot.send_message(uid, f"📢 Интерпол: доставлено {sent}", reply_markup=admin_kb())

# ========== ФОН ==========
def bg():
    last_tax = last_reset = None
    while True:
        time.sleep(60); now = datetime.now()
        if not last_tax or now.date()>last_tax.date(): tax(); last_tax = now
        if now.weekday()==5 and (not last_reset or last_reset.date()!=now.date()): reset_weekly(); last_reset = now
        if now.weekday()==4 and now.hour==12 and now.minute==0: award_weekly()
        if now.minute%5==0 and now.second<10: save()

# ========== СТАРТ ==========
if __name__ == "__main__":
    print(f"{C.BO}{C.H}"); print("="*50); print("     LowHigh v3.2"); print("="*50); print(f"{C.E}")
    log("INFO", f"Админы: {MASTER_ADMINS}")
    log("INFO", f"Юзеров: {len(data['users'])}")
    log("INFO", f"Постов в очереди: {len(data['posts'])}")
    log("INFO", "Бот запущен...")
    threading.Thread(target=bg, daemon=True).start()
    while True:
        try: bot.infinity_polling()
        except Exception as e: log("ERROR", f"Ошибка: {e}, рестарт..."); time.sleep(10)
