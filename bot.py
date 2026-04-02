# LowHigh v5.1 — ОПТИМИЗИРОВАННАЯ ВЕРСИЯ
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import random, time, json, os, threading, re, socket, sys
from datetime import datetime, timedelta

# ========== НАСТРОЙКИ ==========
TOKEN = "8265086577:AAFqojYbFSIRE2FZg0jnJ0Qgzdh0w9_j6z4"
MASTER_ADMINS = [6656110482, 8525294722, 7760222795, 6618330805]
OWNER_USERNAME = "@nickelium"
OWNER_ID = 8525294722
DATA_FILE = "bot_data.json"

bot = telebot.TeleBot(TOKEN)
maintenance_mode = False
user_post_states = {}

# ========== ВРЕМЯ (МСК) ==========
def msk_time(dt=None): return (dt or datetime.now()) + timedelta(hours=3)
def format_msk(dt): return msk_time(dt).strftime("%d.%m.%Y %H:%M")
def now_msk(): return msk_time()
def parse_date(s):
    if not s: return None
    try: return datetime.strptime(s, "%d.%m.%Y %H:%M")
    except: return None

# ========== ЛОГИ ==========
class Colors: HEADER,BLUE,GREEN,YELLOW,RED,END,BOLD = '\033[95m','\033[94m','\033[92m','\033[93m','\033[91m','\033[0m','\033[1m'
def log(level, msg):
    t = format_msk(datetime.now())[11:16]
    c = {'INFO':Colors.BLUE,'SUCCESS':Colors.GREEN,'WARNING':Colors.YELLOW,'ERROR':Colors.RED,'POST':Colors.HEADER,'ADMIN':Colors.BOLD+Colors.RED}.get(level, Colors.END)
    print(f"{c}[{t}][{level[0]}]{Colors.END} {msg}")

audit_log = []
def log_admin(admin_id, action, details=""):
    name = get_name(admin_id, hide_username=False)
    audit_log.append({"time": format_msk(datetime.now()), "admin_id": admin_id, "admin_name": name, "action": action, "details": details})
    if len(audit_log) > 100: audit_log.pop(0)
    log("ADMIN", f"{name}: {action} {details}")

# ========== БАЗА ДАННЫХ ==========
def save_data(data):
    try:
        with open(DATA_FILE+".tmp", 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        if os.path.exists(DATA_FILE): os.replace(DATA_FILE, DATA_FILE+".backup")
        os.replace(DATA_FILE+".tmp", DATA_FILE)
        os.remove(DATA_FILE+".backup") if os.path.exists(DATA_FILE+".backup") else None
        return True
    except Exception as e: log("ERROR", f"Сохранение: {e}"); return False

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: log("ERROR", "Файл повреждён")
    if os.path.exists(DATA_FILE+".backup"):
        try:
            with open(DATA_FILE+".backup", 'r', encoding='utf-8') as f: data = json.load(f)
            with open(DATA_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2)
            return data
        except: log("ERROR", "Бэкап повреждён")
    return {"users": {}, "posts": [], "banned_users": [], "admins": MASTER_ADMINS.copy(), "vip_users": [], "verified_users": [], "groups": {}, "post_history": {}, "post_contents": {}, "stats": {"total_attempts": 0, "total_wins": 0, "total_posts_sent": 0, "daily_stats": {}}, "post_reactions": {}, "deleted_users_log": [], "last_tax_date": None, "first_post_quests": {}, "delivery_coefficient": 0, "group_delivery_coefficient": 0}

data = load_data()

# ========== ПОЛЬЗОВАТЕЛИ ==========
def get_user(uid):
    uid = str(uid)
    if uid in data["banned_users"]: return None
    if uid not in data["users"]:
        deadline = now_msk() + timedelta(hours=24)
        data.setdefault("first_post_quests", {})[uid] = {"deadline": format_msk(deadline), "completed": False, "reminder_sent": False}
        data["users"][uid] = {"rating": 5.0, "luck": 1.0, "fail_counter": 0, "incoming_chance": 5.0, "last_casino": None, "last_post_time": None, "posts_count": 0, "last_convert": None, "last_hotline": None, "last_seen": format_msk(datetime.now()), "join_date": format_msk(datetime.now()), "referrals": [], "referrer": None, "total_posts": 0, "total_casino_attempts": 0, "total_wins": 0, "username": None, "first_name": None, "admin_notifications": True, "vip_until": None, "inventory": {"amulet": 0, "silencer": 0, "vip_pass": 0}, "silencer_until": None, "weekly_activity": 0, "weekly_posts": 0, "weekly_likes": 0, "quests": {}, "quest_bonus_ready": False, "my_posts": [], "post_history_data": {}, "last_post_notification_sent": False, "last_casino_notification_sent": False, "last_activity": now_msk(), "is_active": True, "first_post_quest_completed": False, "guaranteed_win_used": False}
        today = now_msk().strftime("%Y-%m-%d")
        data["stats"].setdefault("daily_stats", {}).setdefault(today, {"joins": 0, "posts": 0, "active": 0})
        data["stats"]["daily_stats"][today]["joins"] += 1
        data["stats"]["daily_stats"][today]["active"] += 1
        save_data(data)
    user = data["users"][uid]
    user["last_seen"] = format_msk(datetime.now())
    user["last_activity"] = now_msk()
    user["is_active"] = True
    return user

def get_name(uid, hide_username=True):
    user = data["users"].get(str(uid))
    if not user: return "Неизвестно"
    if hide_username: return user.get("first_name") or user.get("username") or f"User_{str(uid)[-4:]}"
    return f"@{user['username']}" if user.get("username") else user.get("first_name") or f"User_{str(uid)[-4:]}"

def resolve_target(target):
    if not target: return None
    target = target.strip()
    try: return str(int(target)) if str(int(target)) in data["users"] else None
    except: pass
    if target.startswith('@'): target = target[1:]
    for uid, u in data["users"].items():
        if u.get("username") and u["username"].lower() == target.lower(): return uid
    return None

def is_banned(uid): return str(uid) in data["banned_users"]
def is_admin(uid): return str(uid) in [str(a) for a in MASTER_ADMINS] or str(uid) in data.get("admins", [])
def is_master(uid): return str(uid) in [str(a) for a in MASTER_ADMINS]
def is_vip(uid):
    uid = str(uid); user = data["users"].get(uid)
    if user and user.get("vip_until"):
        until = parse_date(user["vip_until"])
        if until and datetime.now() < until: return True
        user["vip_until"] = None
    return uid in data.get("vip_users", [])
def is_verified(uid): return str(uid) in data.get("verified_users", [])
def get_status_emoji(uid):
    if is_vip(uid): return "👑"
    return "✅" if is_verified(uid) else "📝"
def get_post_cooldown(uid): return 1 if is_vip(uid) else 2
def get_max_post_len(uid):
    if is_vip(uid): return 500
    return 300 if is_verified(uid) else 250
def get_max_refs(uid):
    if is_vip(uid): return 50
    return 25 if is_verified(uid) else 10

def check_post_cd(user):
    if not user.get("last_post_time"): return True, 0
    last = parse_date(user["last_post_time"])
    if not last: return True, 0
    last = last - timedelta(hours=3)
    next_time = last + timedelta(hours=get_post_cooldown(user))
    now = datetime.now()
    return (True, 0) if now >= next_time else (False, (next_time - now).total_seconds())

def check_casino_cd(user):
    if not user.get("last_casino"): return True, 0
    last = parse_date(user["last_casino"])
    if not last: return True, 0
    last = last - timedelta(hours=3)
    next_time = last + timedelta(hours=8)
    now = datetime.now()
    return (True, 0) if now >= next_time else (False, (next_time - now).total_seconds())

def format_time(sec):
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    return f"{h}ч {m}м"

# ========== ГРУППЫ ==========
def add_group(chat_id, title, added_by):
    chat_id = str(chat_id)
    if chat_id not in data.setdefault("groups", {}):
        data["groups"][chat_id] = {"title": title, "added_by": added_by, "added_by_name": get_name(added_by, hide_username=False), "added_date": format_msk(datetime.now()), "owner_vip": False, "total_posts": 0}
        save_data(data)
        return True
    return False

def remove_group(chat_id):
    if str(chat_id) in data.get("groups", {}):
        del data["groups"][str(chat_id)]
        save_data(data)
        return True
    return False

# ========== РАССЫЛКА ==========
def send_post_to_users(post, admin_id, force_all=False, media=None):
    from_uid = post["user_id"]
    author = get_user(from_uid)
    if not author: return 0
    
    recipients = [(uid, u) for uid, u in data["users"].items() if uid != from_uid and uid not in data["banned_users"] and u.get("is_active", True) and not (u.get("silencer_until") and parse_date(u["silencer_until"]) and datetime.now() < parse_date(u["silencer_until"]))]
    if not recipients: return 0
    
    total = len(recipients)
    guaranteed = total if force_all else max(1, int(total * 0.01))
    if not force_all: random.shuffle(recipients)
    
    sent = 0
    pid = post["id"]
    data["post_contents"][str(pid)] = {"text": post["text"], "author_id": from_uid, "author_name": get_name(from_uid, hide_username=False), "has_media": media is not None, "link_url": post.get("link_url", ""), "link_text": post.get("link_text", "")}
    data.setdefault("post_reactions", {})[str(pid)] = data["post_reactions"].get(str(pid), {"likes": [], "dislikes": [], "complaints": []})
    data.setdefault("post_history", {})[str(pid)] = {}
    author.setdefault("my_posts", []).append(pid)
    author.setdefault("post_history_data", {})[str(pid)] = {"text": post["text"], "date": format_msk(datetime.now()), "likes": 0, "dislikes": 0, "link_url": post.get("link_url", ""), "link_text": post.get("link_text", "")}
    
    delivery_coeff = data.get("delivery_coefficient", 0)
    
    for uid, ud in recipients[:guaranteed]:
        try:
            markup = InlineKeyboardMarkup(row_width=3)
            btns = [InlineKeyboardButton(f"👍 0", callback_data=f"like_{pid}"), InlineKeyboardButton(f"👎 0", callback_data=f"dislike_{pid}"), InlineKeyboardButton("⚠️", callback_data=f"complaint_{pid}")]
            if is_admin(uid): btns.append(InlineKeyboardButton("🚫 УДАЛИТЬ", callback_data=f"global_delete_{pid}"))
            if post.get("link_url") and post.get("link_text"): btns.append(InlineKeyboardButton(post["link_text"], url=post["link_url"]))
            markup.add(*btns)
            caption = f"📢 {get_status_emoji(from_uid)} от {get_name(from_uid, hide_username=False)}:\n\n{post['text']}"
            if media: bot.send_photo(int(uid), media, caption=caption, parse_mode="HTML", reply_markup=markup)
            else: bot.send_message(int(uid), caption, parse_mode="HTML", reply_markup=markup)
            sent += 1
            author["rating"] = min(95.0, author["rating"] + 0.01)
            data["post_history"][str(pid)][str(uid)] = True
            author["weekly_activity"] = author.get("weekly_activity", 0) + 5
            author["weekly_posts"] = author.get("weekly_posts", 0) + 1
        except: pass
    
    chance_hits = 0
    for uid, ud in recipients[guaranteed:]:
        if force_all:
            final = 100
        else:
            ref_bonus = sum((get_user(rid).get("rating", 0) for rid in author.get("referrals", []) if get_user(rid)), 0) / 100
            final = min(95, max(5, ud["incoming_chance"] + author["rating"]/2 + author["luck"]/10 + ref_bonus + delivery_coeff))
        if random.uniform(0, 100) <= final:
            try:
                markup = InlineKeyboardMarkup(row_width=3)
                btns = [InlineKeyboardButton(f"👍 0", callback_data=f"like_{pid}"), InlineKeyboardButton(f"👎 0", callback_data=f"dislike_{pid}"), InlineKeyboardButton("⚠️", callback_data=f"complaint_{pid}")]
                if is_admin(uid): btns.append(InlineKeyboardButton("🚫 УДАЛИТЬ", callback_data=f"global_delete_{pid}"))
                if post.get("link_url") and post.get("link_text"): btns.append(InlineKeyboardButton(post["link_text"], url=post["link_url"]))
                markup.add(*btns)
                caption = f"📢 {get_status_emoji(from_uid)} от {get_name(from_uid, hide_username=False)}:\n\n{post['text']}"
                if media: bot.send_photo(int(uid), media, caption=caption, parse_mode="HTML", reply_markup=markup)
                else: bot.send_message(int(uid), caption, parse_mode="HTML", reply_markup=markup)
                sent += 1; chance_hits += 1
                author["rating"] = min(95.0, author["rating"] + 0.01)
                data["post_history"][str(pid)][str(uid)] = True
                author["weekly_activity"] += 5
                author["weekly_posts"] += 1
            except: pass
    
    try:
        bot.send_message(int(from_uid), f"✅ Пост разослан!\n👥 Всего: {total}\n✅ Доставлено: {sent}\n📈 Процент: {sent/total*100:.1f}%\n🎯 Гарантия: {guaranteed}\n🎲 Шанс: {chance_hits}\n📈 Рейтинг: {author['rating']:.1f}%")
    except: pass
    
    data["stats"]["total_posts_sent"] += 1
    save_data(data)
    return sent

def delete_post_globally(pid):
    pid = str(pid)
    if pid not in data.get("post_history", {}): return 0
    cnt = len(data["post_history"][pid])
    del data["post_history"][pid]
    data["post_contents"].pop(pid, None)
    data["post_reactions"].pop(pid, None)
    save_data(data)
    return cnt

# ========== КЛАВИАТУРЫ ==========
def main_kb():
    mk = InlineKeyboardMarkup(row_width=2)
    btns = ["📝 Пост в личку", "👥 Пост в группы", "🎮 Развлечения", "👥 Рефералы", "📊 Статистика", "🏆 Топ-10", "🔄 Конвертация", "🎒 Инвентарь", "📋 Квесты", "📋 История", "⭐ Магазин", "📞 Горячая линия", "ℹ️ Инфо"]
    for b in btns: mk.add(InlineKeyboardButton(b, callback_data=b.split()[0].lower() + ("_post" if b.startswith("📝") else "")))
    return mk

def admin_kb():
    mk = InlineKeyboardMarkup(row_width=2)
    btns = ["📝 Посты на модерации", "📢 Интерпол-рассылка", "👑 VIP управление", "✅ Вериф управление", "👥 Админы", "🚫 Баны", "👥 Управление группами", "📊 Статистика бота", "📈 Активность", "📋 Аудит действий", "👀 Поиск юзера", "📋 Список юзеров", "🎁 VIP всем", "💾 Бэкап", "🗑 Неактивные юзеры", "⚙️ Коэффициенты", "🔧 Тех. работы"]
    for b in btns: mk.add(InlineKeyboardButton(b, callback_data=f"admin_{b.split()[0].lower()}" + ("_list" if b.startswith("📝") else "")))
    return mk

def cancel_kb(): return InlineKeyboardMarkup().add(InlineKeyboardButton("❌ ОТМЕНА", callback_data="cancel_post"))

# ========== ОБРАБОТКА ПОСТОВ ==========
def receive_post_text(msg):
    uid = msg.from_user.id
    if maintenance_mode and not is_admin(uid): return
    if is_banned(uid): return bot.send_message(uid, "🚫 Вы забанены")
    if msg.text and msg.text.lower() in ["отмена","cancel"]: return cancel_post(uid)
    state = user_post_states.get(str(uid), {})
    text = msg.caption if msg.content_type == 'photo' else (msg.text if msg.content_type == 'text' else None)
    if text is None: return bot.send_message(uid, "❌ Только текст или текст+картинка!", reply_markup=main_kb())
    if len(text) > get_max_post_len(uid): return bot.send_message(uid, f"❌ Максимум {get_max_post_len(uid)} символов!", reply_markup=main_kb())
    state["text"] = text if not is_vip(uid) else text
    state["media"] = msg.photo[-1].file_id if msg.content_type == 'photo' else None
    state["step"] = "link"
    user_post_states[str(uid)] = state
    bot.send_message(uid, "✅ Текст принят!\n\n📎 ШАГ 2/3: Отправь ССЫЛКУ (или '-' если не нужна):", reply_markup=cancel_kb())
    bot.register_next_step_handler(msg, receive_post_link)

def receive_post_link(msg):
    uid = msg.from_user.id
    if msg.text and msg.text.lower() in ["отмена","cancel"]: return cancel_post(uid)
    state = user_post_states.get(str(uid), {})
    link = msg.text.strip() if msg.text else ""
    state["link_url"] = "" if link == "-" else link
    state["step"] = "link_text"
    user_post_states[str(uid)] = state
    bot.send_message(uid, "✅ Ссылка принята!\n\n📝 ШАГ 3/3: Отправь ТЕКСТ КНОПКИ (или '-'):", reply_markup=cancel_kb())
    bot.register_next_step_handler(msg, receive_post_btn)

def receive_post_btn(msg):
    uid = msg.from_user.id
    if msg.text and msg.text.lower() in ["отмена","cancel"]: return cancel_post(uid)
    state = user_post_states.get(str(uid), {})
    btn = msg.text.strip() if msg.text else ""
    state["link_text"] = "" if btn == "-" else btn[:30]
    if is_vip(uid):
        state["step"] = "vip_media"
        user_post_states[str(uid)] = state
        bot.send_message(uid, "✅ Текст кнопки принят!\n\n🎬 ШАГ 4/4 (VIP): Отправь СТИКЕР или GIF (или '-'):", reply_markup=cancel_kb())
        bot.register_next_step_handler(msg, receive_vip_media)
    else:
        finalize_post(uid, state)
        del user_post_states[str(uid)]

def receive_vip_media(msg):
    uid = msg.from_user.id
    if msg.text and msg.text.lower() in ["отмена","cancel"]: return cancel_post(uid)
    state = user_post_states.get(str(uid), {})
    if msg.text and msg.text.strip() == "-":
        state["vip_media"] = None
    elif msg.content_type == 'sticker':
        state["vip_media"] = msg.sticker.file_id
        state["vip_media_type"] = 'sticker'
    elif msg.content_type == 'animation' or (msg.content_type == 'document' and msg.document.mime_type == 'image/gif'):
        state["vip_media"] = msg.animation.file_id if msg.content_type == 'animation' else msg.document.file_id
        state["vip_media_type"] = 'gif'
    else:
        return bot.send_message(uid, "❌ Принимаются только стикеры или GIF! Или '-' чтобы пропустить.", reply_markup=cancel_kb())
    finalize_post(uid, state)
    del user_post_states[str(uid)]

def finalize_post(uid, state):
    user = get_user(uid)
    if not user: return
    can, cd = check_post_cd(user)
    if not can: return bot.send_message(uid, f"⏳ Жди {format_time(cd)}", reply_markup=main_kb())
    
    post = {"id": int(time.time()*1000), "user_id": str(uid), "username": user.get("username"), "text": state.get("text",""), "time": format_msk(datetime.now()), "media": state.get("media"), "link_url": state.get("link_url",""), "link_text": state.get("link_text",""), "vip_media": state.get("vip_media"), "vip_media_type": state.get("vip_media_type")}
    user["last_post_time"] = format_msk(datetime.now())
    user["posts_count"] = user.get("posts_count", 0) + 1
    if is_admin(uid) or is_verified(uid):
        sent = send_post_to_users(post, uid, media=post["media"])
        if post.get("vip_media"):
            try:
                if post["vip_media_type"] == 'sticker': bot.send_sticker(uid, post["vip_media"])
                else: bot.send_animation(uid, post["vip_media"])
            except: pass
        bot.send_message(uid, f"✅ Пост разослан! Доставлено: {sent}", reply_markup=main_kb())
    else:
        data["posts"].append(post)
        bot.send_message(uid, "✅ Пост на модерации!", reply_markup=main_kb())
        for aid in data.get("admins", []):
            if aid != str(uid):
                try: bot.send_message(int(aid), f"🆕 Новый пост от {get_name(uid, False)}!\n\n{post['text'][:300]}...\n/admin", parse_mode="HTML")
                except: pass
    user["total_posts"] += 1
    save_data(data)

def cancel_post(uid):
    if str(uid) in user_post_states: del user_post_states[str(uid)]
    bot.send_message(uid, "❌ Отменено", reply_markup=main_kb())

# ========== КАЗИНО ==========
def casino_spin(uid):
    user = get_user(uid)
    can, cd = check_casino_cd(user)
    if not can: return bot.send_message(uid, f"⏳ Жди {format_time(cd)}", reply_markup=casino_kb())
    
    old_rating = user["rating"]
    user["rating"] = max(5.0, user["rating"] - 1.0)
    if is_vip(uid) or is_verified(uid): user["rating"] = max(10.0, user["rating"])
    
    bonus = 20 if user.get("quest_bonus_ready") else 0
    if bonus: user["quest_bonus_ready"] = False
    
    guaranteed = not user.get("guaranteed_win_used", False) and user.get("referrer")
    if guaranteed:
        user["guaranteed_win_used"] = True
        won = True
        bonus_text = " (ГАРАНТИРОВАННО!)"
    else:
        won = random.uniform(0, 100) <= (user["luck"] + bonus)
        bonus_text = ""
    
    if won:
        item = random.choice(["amulet", "silencer", "vip_pass"])
        inv = user.get("inventory", {})
        if inv.get(item, 0) == 0:
            inv[item] = 1
            user["inventory"] = inv
            result = f"🎉 ПОБЕДА!{bonus_text}\n\nВыиграл: {item}!"
        else:
            user["rating"] = min(95.0, user["rating"] + 5.0)
            result = f"🎉 ПОБЕДА!{bonus_text}\n\n+5% к рейтингу"
        user["total_wins"] += 1
        user["fail_counter"] = 0
        data["stats"]["total_wins"] += 1
    else:
        user["fail_counter"] += 1
        inc = user["fail_counter"] * 0.01
        user["luck"] = min(50.0, user["luck"] + inc)
        result = f"😢 ПРОИГРЫШ\n\nУдача +{inc:.2f}% → {user['luck']:.2f}%\nРейтинг: {old_rating:.1f}% → {user['rating']:.1f}%"
    
    user["last_casino"] = format_msk(datetime.now())
    user["total_casino_attempts"] += 1
    user["weekly_activity"] += 1
    data["stats"]["total_attempts"] += 1
    save_data(data)
    bot.send_message(uid, result, parse_mode="HTML", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🎰 Ещё", callback_data="casino"), InlineKeyboardButton("🏠 Меню", callback_data="main_menu")))

def casino_kb():
    mk = InlineKeyboardMarkup()
    mk.add(InlineKeyboardButton("🎲 Крутить", callback_data="casino_spin"))
    mk.add(InlineKeyboardButton("◀️ Назад", callback_data="fun_menu"))
    return mk

# ========== КВЕСТЫ ==========
QUEST_POOL = [{"desc": "Написать пост", "type": "post", "target": 1, "reward": "luck+1"}, {"desc": "Написать 2 поста", "type": "post", "target": 2, "reward": "luck+2", "rare": True}, {"desc": "Пост >200 символов", "type": "post_length", "target": 200, "reward": "rating+1"}, {"desc": "Получить 1 лайк", "type": "likes_recv", "target": 1, "reward": "rating+0.5"}, {"desc": "Получить 3 лайка", "type": "likes_recv", "target": 3, "reward": "rating+1"}, {"desc": "Получить 5 лайков", "type": "likes_recv", "target": 5, "reward": "luck+2", "rare": True}, {"desc": "Поставить 1 лайк", "type": "likes_give", "target": 1, "reward": "luck+0.5"}, {"desc": "Пригласить друга", "type": "referral", "target": 1, "reward": "luck+1"}, {"desc": "Пригласить 2 друзей", "type": "referral", "target": 2, "reward": "luck+2", "rare": True}, {"desc": "Крутнуть казино", "type": "casino", "target": 1, "reward": "luck+0.5"}, {"desc": "Крутнуть 2 раза", "type": "casino", "target": 2, "reward": "luck+1", "rare": True}, {"desc": "Выиграть в казино", "type": "casino_win", "target": 1, "reward": "luck+2"}]

def gen_quests(uid):
    today = now_msk().date().isoformat()
    user = get_user(uid)
    if not user or (user.get("quests") and user["quests"].get("date") == today): return
    available = [q for q in QUEST_POOL if not q.get("rare") or random.random() < 0.2]
    selected = random.sample(available, min(3, len(available)))
    user["quests"] = {"date": today, "tasks": [{"desc": q["desc"], "type": q["type"], "target": q["target"], "reward": q["reward"]} for q in selected], "completed": [False]*3, "progress": [0]*3}
    user["quest_bonus_ready"] = False
    save_data(data)

def update_quest(uid, qtype, val=1, extra=None):
    user = get_user(uid)
    if not user or "quests" not in user or user["quests"].get("date") != now_msk().date().isoformat(): return
    changed = False
    for i, t in enumerate(user["quests"]["tasks"]):
        if user["quests"]["completed"][i]: continue
        if t["type"] == qtype or (t["type"] == "post_length" and qtype == "post" and extra and extra > t["target"]):
            user["quests"]["progress"][i] += val
            if user["quests"]["progress"][i] >= t["target"]:
                user["quests"]["completed"][i] = True
                r = t["reward"]
                if r.startswith("luck+"): user["luck"] = min(50.0, user["luck"] + float(r[5:]))
                elif r.startswith("rating+"): user["rating"] = min(95.0, user["rating"] + float(r[7:]))
                changed = True
    if changed:
        if all(user["quests"]["completed"]): user["quest_bonus_ready"] = True
        save_data(data)

# ========== КОМАНДЫ ==========
@bot.message_handler(commands=['start'])
def start(msg):
    uid = msg.from_user.id
    if maintenance_mode and not is_admin(uid): return bot.send_message(uid, "🔧 Техработы!")
    if is_banned(uid): return bot.send_message(uid, "🚫 Вы забанены")
    user = get_user(uid)
    user["first_name"] = msg.from_user.first_name
    user["username"] = msg.from_user.username
    if msg.chat.type in ["group","supergroup"]:
        if add_group(msg.chat.id, msg.chat.title, uid):
            bot.send_message(msg.chat.id, "👋 Привет! Я бот LowHigh\n📢 Посты в группы через /grouppost\n📊 Шанс: 5% (VIP 10%)\nПриятного пользования!")
            bot.send_message(uid, f"✅ Группа '{msg.chat.title}' добавлена!")
        return
    args = msg.text.split()
    if len(args) > 1 and args[1] != str(uid) and not user["referrer"]:
        ref = get_user(args[1])
        if ref and len(ref["referrals"]) < get_max_refs(args[1]) and str(uid) not in ref["referrals"]:
            user["referrer"] = args[1]
            ref["referrals"].append(str(uid))
            ref["luck"] = min(50.0, ref["luck"] + 1.0)
            user["guaranteed_win_used"] = False
            try:
                bot.send_message(int(args[1]), f"🎉 Новый реферал! {get_name(uid, False)}\n🍀 Удача +1%")
                bot.send_message(uid, "🎁 БОНУС! Гарантированный выигрыш в казино!")
            except: pass
            save_data(data)
    gen_quests(uid)
    cd = get_post_cooldown(uid)
    bot.send_message(uid, f"🎩 LowHigh 🎰\n\nТвой профиль:\n{get_status_emoji(uid)} Рейтинг: {user['rating']:.1f}%\n🍀 Удача: {user['luck']:.1f}%\n⏱ КД поста: {cd}ч\n\n👇 Выбери действие:", parse_mode="HTML", reply_markup=main_kb())

@bot.message_handler(commands=['post'])
def cmd_post(msg):
    uid = msg.from_user.id
    if maintenance_mode and not is_admin(uid): return bot.send_message(uid, "🔧 Техработы!")
    if is_banned(uid): return
    user = get_user(uid)
    can, cd = check_post_cd(user)
    if not can: return bot.send_message(uid, f"⏳ Жди {format_time(cd)}", reply_markup=main_kb())
    pred = min(95, max(5, user["rating"]/2 + user["luck"]/10))
    bot.send_message(uid, f"📊 Прогноз доставки: {pred:.1f}%\n\n📝 ШАГ 1/3: Отправь текст (можно с картинкой):", reply_markup=cancel_kb())
    bot.register_next_step_handler(msg, receive_post_text)

@bot.message_handler(commands=['grouppost'])
def cmd_group_post(msg):
    uid = msg.from_user.id
    cid = msg.chat.id
    if msg.chat.type not in ["group","supergroup"]: return bot.send_message(uid, "🚫 Только в группах!")
    if maintenance_mode and not is_admin(uid): return bot.send_message(cid, "🔧 Техработы!")
    if is_banned(uid): return
    try:
        if not any(a.user.id == uid for a in bot.get_chat_administrators(cid)): return bot.send_message(cid, "🚫 Только админы!")
    except: return bot.send_message(cid, "❌ Ошибка прав")
    user = get_user(uid)
    can, cd = check_post_cd(user)
    if not can: return bot.send_message(cid, f"⏳ Жди {format_time(cd)}")
    coeff = data.get("group_delivery_coefficient", 0)
    chance = min(100, (10 if is_vip(uid) else 5) + coeff)
    bot.send_message(cid, f"👥 Пост в группы\nШанс: {chance}%\n\n📝 Отправь текст (можно с картинкой):")
    bot.register_next_step_handler(msg, receive_group_post)

def receive_group_post(msg):
    uid = msg.from_user.id
    cid = msg.chat.id
    if msg.text and msg.text.lower() in ["отмена","cancel"]: return
    media = msg.photo[-1].file_id if msg.content_type == 'photo' else None
    text = msg.caption if msg.content_type == 'photo' else (msg.text if msg.content_type == 'text' else None)
    if text is None: return bot.send_message(cid, "❌ Только текст или текст+картинка!")
    if len(text) > 500: return bot.send_message(cid, f"❌ Максимум 500 символов!")
    if not is_vip(uid): text = censor_text(text, uid)
    user = get_user(uid)
    post = {"id": int(time.time()*1000), "user_id": str(uid), "username": user.get("username"), "text": text, "time": format_msk(datetime.now()), "type": "group", "media": media}
    user["last_post_time"] = format_msk(datetime.now())
    user["posts_count"] = user.get("posts_count",0)+1
    update_quest(uid, "post", 1)
    if len(text) > 200: update_quest(uid, "post_length", 200, extra=len(text))
    sent = send_group_post(post, uid, media)
    user["total_posts"] += 1
    save_data(data)
    bot.send_message(cid, f"✅ Разослан! Доставлено: {sent} группам")

def send_group_post(post, admin_id, media=None):
    from_uid = post["user_id"]
    author = get_user(from_uid)
    if not author or not data.get("groups"): return 0
    groups = list(data["groups"].items())
    total = len(groups)
    coeff = data.get("group_delivery_coefficient", 0)
    base = min(100, (10 if is_vip(from_uid) else 5) + coeff)
    guaranteed = max(1, int(total * 0.05))
    random.shuffle(groups)
    sent = 0
    pid = post["id"]
    data["post_contents"][str(pid)] = {"text": post.get("text",""), "author_id": from_uid, "author_name": get_name(from_uid, False), "has_media": media is not None}
    for gid, gd in groups[:guaranteed]:
        try:
            markup = InlineKeyboardMarkup().add(InlineKeyboardButton(post.get("link_text","Перейти"), url=post.get("link_url","#"))) if post.get("link_url") and post.get("link_text") else None
            caption = f"📢 {get_status_emoji(from_uid)} от {get_name(from_uid, False)}:\n\n{post.get('text','')}"
            if media: bot.send_photo(int(gid), media, caption=caption, parse_mode="HTML", reply_markup=markup)
            else: bot.send_message(int(gid), caption, parse_mode="HTML", reply_markup=markup)
            sent += 1
            author["rating"] = min(95.0, author["rating"] + 0.01)
            data["groups"][gid]["total_posts"] += 1
        except: pass
    for gid, gd in groups[guaranteed:]:
        if random.uniform(0,100) <= base:
            try:
                markup = InlineKeyboardMarkup().add(InlineKeyboardButton(post.get("link_text","Перейти"), url=post.get("link_url","#"))) if post.get("link_url") and post.get("link_text") else None
                caption = f"📢 {get_status_emoji(from_uid)} от {get_name(from_uid, False)}:\n\n{post.get('text','')}"
                if media: bot.send_photo(int(gid), media, caption=caption, parse_mode="HTML", reply_markup=markup)
                else: bot.send_message(int(gid), caption, parse_mode="HTML", reply_markup=markup)
                sent += 1
                author["rating"] = min(95.0, author["rating"] + 0.01)
                data["groups"][gid]["total_posts"] += 1
            except: pass
    try: bot.send_message(int(from_uid), f"✅ Групповой пост разослан!\n👥 Всего групп: {total}\n✅ Доставлено: {sent}\n📈 Процент: {sent/total*100:.1f}%")
    except: pass
    save_data(data)
    return sent

@bot.message_handler(commands=['casino','spin'])
def cmd_casino(msg):
    uid = msg.from_user.id
    if msg.text.startswith('/spin'): return casino_spin(uid)
    user = get_user(uid)
    can, cd = check_casino_cd(user)
    text = f"🎰 КАЗИНО\n🍀 Шанс: {user['luck']:.2f}%\n"
    if user.get("quest_bonus_ready"): text += "🔥 +20% за квесты!\n"
    if not user.get("guaranteed_win_used", True) and user.get("referrer"): text += "🎁 ГАРАНТИРОВАННЫЙ ВЫИГРЫШ!\n"
    text += "\n✅ Можно играть!" if can else f"\n⏳ Жди {format_time(cd)}"
    bot.send_message(uid, text, parse_mode="HTML", reply_markup=casino_kb())

@bot.message_handler(commands=['admin'])
def admin_panel(msg):
    if not is_admin(msg.from_user.id): return bot.send_message(msg.from_user.id, "🚫 Нет прав")
    bot.send_message(msg.from_user.id, "👑 АДМИН-ПАНЕЛЬ", reply_markup=admin_kb())
    log_admin(msg.from_user.id, "Вошёл в админку")

@bot.message_handler(commands=['setrating','setluck','addadmin','removeadmin','addvip','removevip','addverified','removeverified','ban','unban','delpost','restime','profile'])
def admin_cmds(msg):
    if not is_admin(msg.from_user.id): return
    cmd = msg.text.split()[0][1:]
    args = msg.text.split()
    if len(args) < 2: return bot.send_message(msg.from_user.id, f"❌ /{cmd} @user [значение]")
    target = resolve_target(args[1])
    if not target: return bot.send_message(msg.from_user.id, "❌ Пользователь не найден")
    user = get_user(target)
    if cmd == "setrating":
        try: val = float(args[2]); old = user["rating"]; user["rating"] = max(5.0, min(95.0, val)); user["rating"] = max(10.0, user["rating"]) if is_vip(target) or is_verified(target) else user["rating"]; save_data(data); bot.send_message(msg.from_user.id, f"✅ Рейтинг: {old:.1f}% → {user['rating']:.1f}%")
        except: bot.send_message(msg.from_user.id, "❌ Число")
    elif cmd == "setluck":
        try: val = float(args[2]); old = user["luck"]; user["luck"] = max(1.0, min(50.0, val)); save_data(data); bot.send_message(msg.from_user.id, f"✅ Удача: {old:.1f}% → {user['luck']:.1f}%")
        except: bot.send_message(msg.from_user.id, "❌ Число")
    elif cmd == "addadmin":
        if target not in data["admins"]: data["admins"].append(target); save_data(data); bot.send_message(msg.from_user.id, f"✅ {get_name(target, False)} назначен админом")
    elif cmd == "removeadmin":
        if target in data["admins"] and target not in [str(a) for a in MASTER_ADMINS] and target != str(msg.from_user.id): data["admins"].remove(target); save_data(data); bot.send_message(msg.from_user.id, f"✅ Админ удалён")
    elif cmd == "addvip":
        if len(args) >= 3:
            try: days = int(args[2]); user["vip_until"] = format_msk(now_msk() + timedelta(days=days)); save_data(data); bot.send_message(msg.from_user.id, f"👑 VIP на {days} дней")
            except: pass
        elif target not in data.get("vip_users",[]): data.setdefault("vip_users",[]).append(target); save_data(data); bot.send_message(msg.from_user.id, f"👑 Постоянный VIP")
    elif cmd == "removevip":
        if user.get("vip_until"): user["vip_until"] = None
        if target in data.get("vip_users",[]): data["vip_users"].remove(target)
        save_data(data); bot.send_message(msg.from_user.id, f"✅ VIP снят")
    elif cmd == "addverified":
        if target not in data.get("verified_users",[]): data.setdefault("verified_users",[]).append(target); check_and_fix_rating(target); save_data(data); bot.send_message(msg.from_user.id, f"✅ Верифицирован")
    elif cmd == "removeverified":
        if target in data.get("verified_users",[]): data["verified_users"].remove(target); save_data(data); bot.send_message(msg.from_user.id, f"✅ Верификация снята")
    elif cmd == "ban":
        if target not in data["banned_users"]: data["banned_users"].append(target); save_data(data); bot.send_message(msg.from_user.id, f"🚫 Забанен")
    elif cmd == "unban":
        if target in data["banned_users"]: data["banned_users"].remove(target); save_data(data); bot.send_message(msg.from_user.id, f"✅ Разбанен")
    elif cmd == "delpost":
        deleted = delete_post_globally(args[1]); bot.send_message(msg.from_user.id, f"✅ Удалено у {deleted}")
    elif cmd == "restime":
        user["last_casino"] = None; user["last_post_time"] = None; save_data(data); bot.send_message(msg.from_user.id, f"✅ КД сброшены")
    elif cmd == "profile":
        text = f"👤 {get_name(target, False)}\nID: {target}\n📈 Рейтинг: {user['rating']:.1f}%\n🍀 Удача: {user['luck']:.2f}%\n📝 Постов: {user['total_posts']}\n👥 Рефералов: {len(user.get('referrals',[]))}"
        bot.send_message(msg.from_user.id, text)

def check_and_fix_rating(uid):
    user = get_user(uid)
    if user and (is_vip(uid) or is_verified(uid)) and user["rating"] < 10.0:
        user["rating"] = 10.0
        save_data(data)
        return True
    return False

def censor_text(text, uid): return text if is_vip(uid) else re.sub('|'.join(re.escape(w) for w in ["хуй","пизда","ебать","блядь","сука","гандон","пидор","нахуй","похуй","залупа","мудак","долбоёб","хуесос"]), lambda m: '*'*len(m.group()), text, flags=re.IGNORECASE)

def get_top(): return sorted([{"name": get_name(uid, True), "rating": u.get("rating",0), "luck": u.get("luck",0), "posts": u.get("total_posts",0)} for uid, u in data["users"].items() if uid not in data["banned_users"] and not is_admin(uid) and u.get("is_active",True)], key=lambda x: x["rating"], reverse=True)[:10]

# ========== КОЛЛБЭКИ ==========
@bot.callback_query_handler(func=lambda c: True)
def callback(c):
    uid = c.from_user.id
    if is_banned(uid) and not c.data.startswith("unban_"): return bot.answer_callback_query(c.id, "Забанен", show_alert=True)
    user = get_user(uid) if not is_banned(uid) else None
    
    # Реакции
    if c.data.startswith(("like_","dislike_","complaint_")):
        pid = c.data.split("_")[1]
        r = data["post_reactions"].setdefault(pid, {"likes":[],"dislikes":[],"complaints":[]})
        if c.data.startswith("like_"):
            if str(uid) in r["likes"]: r["likes"].remove(str(uid)); bot.answer_callback_query(c.id, "👍 Лайк убран")
            else:
                if str(uid) in r["dislikes"]: r["dislikes"].remove(str(uid))
                r["likes"].append(str(uid)); bot.answer_callback_query(c.id, "👍 Лайк поставлен")
                aid = data["post_contents"].get(pid,{}).get("author_id")
                if aid and aid != str(uid):
                    a = get_user(aid)
                    if a: a["rating"] = min(95.0, a["rating"]+0.05); update_quest(aid, "likes_recv", 1)
                update_quest(uid, "likes_give", 1)
        elif c.data.startswith("dislike_"):
            if str(uid) in r["dislikes"]: r["dislikes"].remove(str(uid)); bot.answer_callback_query(c.id, "👎 Дизлайк убран")
            else:
                if str(uid) in r["likes"]: r["likes"].remove(str(uid))
                r["dislikes"].append(str(uid)); bot.answer_callback_query(c.id, "👎 Дизлайк поставлен")
        elif c.data.startswith("complaint_") and str(uid) not in r["complaints"]:
            r["complaints"].append(str(uid)); bot.answer_callback_query(c.id, "⚠️ Жалоба отправлена")
            for aid in data.get("admins",[]):
                try: bot.send_message(int(aid), f"⚠️ ЖАЛОБА\nПост: {pid}\nОт: {get_name(uid, False)}")
                except: pass
        save_data(data)
        try:
            likes, dislikes = len(r["likes"]), len(r["dislikes"])
            mk = InlineKeyboardMarkup(row_width=3)
            btns = [InlineKeyboardButton(f"👍 {likes}", callback_data=f"like_{pid}"), InlineKeyboardButton(f"👎 {dislikes}", callback_data=f"dislike_{pid}"), InlineKeyboardButton("⚠️", callback_data=f"complaint_{pid}")]
            if data["post_contents"].get(pid,{}).get("link_url"): btns.append(InlineKeyboardButton(data["post_contents"][pid]["link_text"], url=data["post_contents"][pid]["link_url"]))
            mk.add(*btns)
            bot.edit_message_reply_markup(c.message.chat.id, c.message.message_id, reply_markup=mk)
        except: pass
        return
    
    if c.data == "global_delete_" + c.data.split("_")[2] if c.data.startswith("global_delete_") else None:
        if not is_admin(uid): return bot.answer_callback_query(c.id, "Не админ")
        pid = c.data.split("_")[2]
        bot.answer_callback_query(c.id, f"🗑 Удалено у {delete_post_globally(pid)}")
        return
    
    # Админка
    if c.data.startswith("admin_"):
        if not is_admin(uid): return
        act = c.data[6:]
        
        if act == "main": return bot.edit_message_text("👑 АДМИН-ПАНЕЛЬ", uid, c.message.message_id, reply_markup=admin_kb())
        if act == "posts_list":
            if not data["posts"]: return bot.edit_message_text("📭 Нет постов", uid, c.message.message_id, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("◀️ Назад", callback_data="admin_main")))
            mk = InlineKeyboardMarkup(row_width=1)
            for i, p in enumerate(data["posts"][:5]):
                has_vip = "🎬" if p.get("vip_media") else ""
                mk.add(InlineKeyboardButton(f"{i+1}. {has_vip} {get_name(p['user_id'], False)}: {p['text'][:30]}...", callback_data=f"admin_post_{p['id']}"))
            mk.add(InlineKeyboardButton("◀️ Назад", callback_data="admin_main"))
            bot.edit_message_text(f"📝 Посты ({len(data['posts'])}):", uid, c.message.message_id, reply_markup=mk)
        
        elif act.startswith("post_"):
            pid = act.split("_")[1]
            for p in data["posts"]:
                if str(p["id"]) == pid:
                    text = f"📝 От {get_name(p['user_id'], False)}\n\n{p['text']}"
                    mk = InlineKeyboardMarkup(row_width=2)
                    mk.add(InlineKeyboardButton("✅ ОДОБРИТЬ", callback_data=f"approve_{pid}"), InlineKeyboardButton("❌ ОТКЛОНИТЬ", callback_data=f"reject_{pid}"))
                    mk.add(InlineKeyboardButton("🚫 ЗАБАНИТЬ", callback_data=f"ban_user_{pid}"), InlineKeyboardButton("📢 ИНТЕРПОЛ", callback_data=f"interpol_{pid}"))
                    mk.add(InlineKeyboardButton("◀️ Назад", callback_data="admin_posts_list"))
                    # Отправляем VIP-медиа если есть
                    if p.get("vip_media"):
                        try:
                            if p["vip_media_type"] == 'sticker': bot.send_sticker(uid, p["vip_media"])
                            else: bot.send_animation(uid, p["vip_media"])
                        except: pass
                    bot.edit_message_text(text, uid, c.message.message_id, parse_mode="HTML", reply_markup=mk)
                    break
        
        elif act == "interpol":
            bot.edit_message_text("📢 Интерпол-рассылка\n\nОтправь текст поста (или 'отмена'):", uid, c.message.message_id)
            bot.register_next_step_handler_by_chat_id(uid, receive_interpol_post)
        
        elif act == "vip_all":
            mk = InlineKeyboardMarkup(row_width=2)
            mk.add(InlineKeyboardButton("✅ ДА", callback_data="admin_vip_all_confirm"), InlineKeyboardButton("❌ НЕТ", callback_data="admin_main"))
            bot.edit_message_text("🎁 Выдать VIP всем на сутки + бонус?", uid, c.message.message_id, reply_markup=mk)
        
        elif act == "vip_all_confirm":
            cnt, bonus = give_vip_to_all_with_bonus()
            bot.edit_message_text(f"✅ VIP выдан {cnt} пользователям!\n🎁 Бонус: {bonus}", uid, c.message.message_id, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("◀️ Назад", callback_data="admin_main")))
        
        elif act == "coefficients":
            d = data.get("delivery_coefficient", 0)
            g = data.get("group_delivery_coefficient", 0)
            mk = InlineKeyboardMarkup(row_width=2)
            mk.add(InlineKeyboardButton(f"📨 Личка: {d}%", callback_data="admin_coeff_delivery"), InlineKeyboardButton(f"👥 Группы: {g}%", callback_data="admin_coeff_group"))
            mk.add(InlineKeyboardButton("◀️ Назад", callback_data="admin_main"))
            bot.edit_message_text("⚙️ КОЭФФИЦИЕНТЫ ДОСТАВКИ", uid, c.message.message_id, reply_markup=mk)
        
        elif act == "coeff_delivery":
            bot.send_message(uid, f"📨 Введи значение (0-100):\nТекущее: {data.get('delivery_coefficient',0)}%")
            bot.register_next_step_handler_by_chat_id(uid, set_delivery)
        
        elif act == "coeff_group":
            bot.send_message(uid, f"👥 Введи значение (0-100):\nТекущее: {data.get('group_delivery_coefficient',0)}%")
            bot.register_next_step_handler_by_chat_id(uid, set_group_delivery)
        
        elif act == "maintenance":
            global maintenance_mode
            maintenance_mode = not maintenance_mode
            status = "ВКЛЮЧЁН" if maintenance_mode else "ВЫКЛЮЧЁН"
            bot.answer_callback_query(c.id, f"Режим тех. работ {status}")
            bot.edit_message_text(f"🔧 Тех. работы: {status}", uid, c.message.message_id, reply_markup=admin_kb())
            log_admin(uid, f"Тех. работы {status}")
        
        elif act == "backup_menu":
            mk = InlineKeyboardMarkup(row_width=2)
            mk.add(InlineKeyboardButton("📤 Скачать", callback_data="admin_backup_save"), InlineKeyboardButton("📥 Загрузить", callback_data="admin_backup_load"))
            mk.add(InlineKeyboardButton("◀️ Назад", callback_data="admin_main"))
            bot.edit_message_text("💾 БЭКАПЫ", uid, c.message.message_id, reply_markup=mk)
        
        elif act == "backup_save":
            try:
                with open(DATA_FILE, 'rb') as f: bot.send_document(uid, f, visible_file_name=f'backup_{now_msk().strftime("%Y%m%d_%H%M%S")}.json')
                bot.answer_callback_query(c.id, "✅ Бэкап отправлен")
            except: bot.answer_callback_query(c.id, "❌ Ошибка")
        
        elif act == "backup_load":
            if not is_master(uid): return bot.answer_callback_query(c.id, "❌ Только мастер-админ")
            bot.send_message(uid, "📤 Отправь JSON-файл бэкапа:")
            bot.register_next_step_handler_by_chat_id(uid, receive_backup_file)
        
        elif act == "all_users":
            users = [(uid, get_name(uid, False)) for uid in data["users"] if uid not in data["banned_users"]]
            if not users: return bot.edit_message_text("📋 Нет пользователей", uid, c.message.message_id, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("◀️ Назад", callback_data="admin_main")))
            per_page = 20
            pages = (len(users) + per_page - 1) // per_page
            mk = InlineKeyboardMarkup()
            if pages > 1: mk.add(InlineKeyboardButton("▶️ Далее", callback_data="admin_users_page_1"))
            mk.add(InlineKeyboardButton("◀️ Назад", callback_data="admin_main"))
            text = f"📋 ПОЛЬЗОВАТЕЛИ ({len(users)})\n\n"
            for i, (uid, name) in enumerate(users[:per_page], 1): text += f"{i}. {name} (ID: {uid})\n"
            bot.edit_message_text(text, uid, c.message.message_id, reply_markup=mk)
        
        elif act.startswith("users_page_"):
            page = int(act.split("_")[2])
            users = [(uid, get_name(uid, False)) for uid in data["users"] if uid not in data["banned_users"]]
            per_page = 20
            pages = (len(users) + per_page - 1) // per_page
            start = page * per_page
            mk = InlineKeyboardMarkup(row_width=2)
            if page > 0: mk.add(InlineKeyboardButton("◀️ Назад", callback_data=f"admin_users_page_{page-1}"))
            if page < pages-1: mk.add(InlineKeyboardButton("Вперёд ▶️", callback_data=f"admin_users_page_{page+1}"))
            mk.add(InlineKeyboardButton("◀️ В админку", callback_data="admin_main"))
            text = f"📋 ПОЛЬЗОВАТЕЛИ ({len(users)}) Стр. {page+1}/{pages}\n\n"
            for i, (uid, name) in enumerate(users[start:start+per_page], start+1): text += f"{i}. {name} (ID: {uid})\n"
            bot.edit_message_text(text, uid, c.message.message_id, reply_markup=mk)
        
        else:
            # Списки (vip_list, verified_list, admins_list, bans_list)
            lists = {"vip": [(uid, get_name(uid, False)) for uid in data.get("vip_users",[]) if uid in data["users"]],
                     "verified": [(uid, get_name(uid, False)) for uid in data.get("verified_users",[])],
                     "admins": [(uid, get_name(uid, False)) for uid in data.get("admins",[])],
                     "bans": [(uid, get_name(uid, False)) for uid in data.get("banned_users",[])]}
            for key in lists:
                if act == f"{key}_list":
                    items = lists[key]
                    if not items: return bot.edit_message_text(f"📭 Нет {'VIP' if key=='vip' else 'верифицированных' if key=='verified' else 'админов' if key=='admins' else 'забаненных'}", uid, c.message.message_id, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("◀️ Назад", callback_data="admin_main")))
                    mk = InlineKeyboardMarkup(row_width=1)
                    for i, (iid, name) in enumerate(items[:10]): mk.add(InlineKeyboardButton(f"{i+1}. {name}", callback_data=f"admin_{key}_{iid}"))
                    mk.add(InlineKeyboardButton("◀️ Назад", callback_data="admin_main"))
                    bot.edit_message_text(f"👑 {'VIP' if key=='vip' else 'Вериф' if key=='verified' else 'Админы' if key=='admins' else 'Баны'} ({len(items)}):", uid, c.message.message_id, reply_markup=mk)
                    break
            else:
                # Другие кнопки
                if act == "stats":
                    total = len(data["users"])
                    today = now_msk().strftime("%Y-%m-%d")
                    daily = data["stats"].get("daily_stats", {}).get(today, {"joins":0,"posts":0,"active":0})
                    text = f"📊 СТАТИСТИКА\n👥 Всего: {total}\n🚫 Бан: {len(data['banned_users'])}\n👑 VIP: {len(data.get('vip_users',[]))}\n✅ Вериф: {len(data.get('verified_users',[]))}\n👥 Групп: {len(data.get('groups',{}))}\n📝 Постов: {data['stats']['total_posts_sent']}\n🎰 Игр: {data['stats']['total_attempts']}\n🏆 Побед: {data['stats']['total_wins']}\n📅 За сегодня: +{daily['joins']} юзеров, {daily['posts']} постов"
                    bot.edit_message_text(text, uid, c.message.message_id, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("◀️ Назад", callback_data="admin_main")))
                elif act == "activity":
                    top = sorted([(get_name(uid, False), u.get("weekly_activity",0)) for uid,u in data["users"].items() if uid not in data["banned_users"] and not is_admin(uid) and u.get("is_active",True) and u.get("weekly_activity",0)>0], key=lambda x: x[1], reverse=True)[:10]
                    text = "📈 АКТИВНОСТЬ ЗА НЕДЕЛЮ\n\n" + ("\n".join([f"{i+1}. {n} — {a} очков" for i,(n,a) in enumerate(top)]) if top else "Нет данных")
                    bot.edit_message_text(text, uid, c.message.message_id, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("◀️ Назад", callback_data="admin_main")))
                elif act == "audit":
                    text = "📋 АУДИТ\n\n" + "\n".join([f"[{e['time']}] {e['admin_name']}: {e['action']}" for e in audit_log[-10:]])
                    bot.edit_message_text(text, uid, c.message.message_id, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("◀️ Назад", callback_data="admin_main")))
                elif act == "search_user":
                    bot.send_message(uid, "👀 Введи @username или ID:")
                    bot.register_next_step_handler_by_chat_id(uid, admin_search_user)
                elif act == "inactive_users":
                    logs = data.get("deleted_users_log", [])
                    text = "🗑 НЕАКТИВНЫЕ\n\n" + "\n".join([f"👤 {e['name']} — {e['deactivated_at']}" for e in logs[-10:]]) if logs else "Нет записей"
                    bot.edit_message_text(text, uid, c.message.message_id, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("◀️ Назад", callback_data="admin_main")))
    
    # Одобрение/отклонение поста
    elif c.data.startswith("approve_"):
        if not is_admin(uid): return
        pid = c.data.split("_")[1]
        for i, p in enumerate(data["posts"]):
            if str(p["id"]) == pid:
                sent = send_post_to_users(p, uid, media=p.get("media"))
                # Отправляем VIP-медиа автору отдельно
                if p.get("vip_media"):
                    try:
                        if p["vip_media_type"] == 'sticker': bot.send_sticker(int(p["user_id"]), p["vip_media"])
                        else: bot.send_animation(int(p["user_id"]), p["vip_media"])
                    except: pass
                data["posts"].pop(i)
                save_data(data)
                bot.answer_callback_query(c.id, "✅ Одобрено")
                bot.send_message(uid, f"✅ Пост одобрен! Доставлено: {sent}")
                try: bot.send_message(int(p["user_id"]), f"✅ Пост одобрен! Доставлен {sent} пользователям.")
                except: pass
                # Показать следующий пост
                if data["posts"]:
                    nxt = data["posts"][0]
                    mk = InlineKeyboardMarkup(row_width=2)
                    mk.add(InlineKeyboardButton("✅ ОДОБРИТЬ", callback_data=f"approve_{nxt['id']}"), InlineKeyboardButton("❌ ОТКЛОНИТЬ", callback_data=f"reject_{nxt['id']}"))
                    mk.add(InlineKeyboardButton("◀️ К списку", callback_data="admin_posts_list"))
                    bot.edit_message_text(f"📝 Следующий пост от {get_name(nxt['user_id'], False)}\n\n{nxt['text'][:300]}", uid, c.message.message_id, parse_mode="HTML", reply_markup=mk)
                else: bot.edit_message_text("📭 Постов больше нет", uid, c.message.message_id, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("◀️ Назад", callback_data="admin_main")))
                break
    
    elif c.data.startswith("reject_"):
        if not is_admin(uid): return
        pid = c.data.split("_")[1]
        for i, p in enumerate(data["posts"]):
            if str(p["id"]) == pid:
                data["posts"].pop(i)
                save_data(data)
                bot.answer_callback_query(c.id, "❌ Отклонён")
                bot.send_message(uid, "📝 Напиши причину (или '-'):")
                bot.register_next_step_handler_by_chat_id(uid, lambda m: reject_with_reason(m, p))
                break
    
    elif c.data.startswith("ban_user_"):
        if not is_admin(uid): return
        pid = c.data.split("_")[2]
        for p in data["posts"]:
            if str(p["id"]) == pid:
                banned = p["user_id"]
                if banned not in data["banned_users"]:
                    data["banned_users"].append(banned)
                    save_data(data)
                    bot.answer_callback_query(c.id, "🚫 Забанен")
                    bot.send_message(uid, f"🚫 {get_name(banned, False)} забанен")
                break
    
    elif c.data.startswith("interpol_"):
        if not is_admin(uid): return
        pid = c.data.split("_")[1]
        for i, p in enumerate(data["posts"]):
            if str(p["id"]) == pid:
                sent = send_post_to_users(p, uid, force_all=True, media=p.get("media"))
                data["posts"].pop(i)
                save_data(data)
                bot.edit_message_text(f"📢 Интерпол! Доставлено: {sent}", uid, c.message.message_id)
                break
    
    # Обычное меню
    elif c.data == "main_menu": bot.edit_message_text("🎩 Главное меню", uid, c.message.message_id, reply_markup=main_kb())
    elif c.data == "fun_menu": bot.edit_message_text("🎮 Развлечения", uid, c.message.message_id, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🎲 Случайный пост", callback_data="random_post"), InlineKeyboardButton("🎰 Казино", callback_data="casino"), InlineKeyboardButton("◀️ Назад", callback_data="main_menu")))
    elif c.data == "casino": bot.edit_message_text("🎰 Казино", uid, c.message.message_id, reply_markup=casino_kb())
    elif c.data == "casino_spin": casino_spin(uid)
    elif c.data == "random_post":
        rp = get_random_post()
        if rp: bot.send_message(uid, f"📖 СЛУЧАЙНЫЙ ПОСТ\n\n👤 {rp['author_name']}\n📅 {rp['date']}\n👍 {rp['likes']}\n\n{rp['text']}", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🎲 Ещё", callback_data="random_post"), InlineKeyboardButton("◀️ Назад", callback_data="fun_menu")))
        else: bot.answer_callback_query(c.id, "Нет постов")
    elif c.data == "write_post": cmd_post(c.message)
    elif c.data == "write_group_post": bot.send_message(uid, "👥 /grouppost работает только в группах!")
    elif c.data == "cancel_post": cancel_post(uid)
    elif c.data == "referrals":
        link = f"https://t.me/{bot.get_me().username}?start={uid}"
        bot.send_message(uid, f"👥 РЕФЕРАЛЫ\n\nПригласил: {len(user.get('referrals',[]))}/{get_max_refs(uid)}\n🔗 {link}", parse_mode="HTML", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("◀️ Назад", callback_data="main_menu")))
    elif c.data == "stats":
        ref_bonus = sum((get_user(rid).get("rating",0) for rid in user.get("referrals",[]) if get_user(rid)), 0) / 100
        bot.send_message(uid, f"📊 ТВОЯ СТАТИСТИКА\n\n📈 Рейтинг: {user['rating']:.1f}%\n🍀 Удача: {user['luck']:.2f}%\n💰 Бонус рефералов: +{ref_bonus:.2f}%\n⏱ КД поста: {get_post_cooldown(uid)}ч\n\n📝 Постов: {user['total_posts']}\n🎰 Игр: {user['total_casino_attempts']}\n🏆 Побед: {user['total_wins']}\n👥 Рефералов: {len(user.get('referrals',[]))}", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("◀️ Назад", callback_data="main_menu")))
    elif c.data == "top":
        top = get_top()
        text = "🏆 ТОП-10\n\n" + "\n".join([f"{'🥇' if i==0 else '🥈' if i==1 else '🥉' if i==2 else '▫️'} {i+1}. {u['name']}\n   📈 {u['rating']:.1f}% 🍀 {u['luck']:.1f}%" for i,u in enumerate(top)]) if top else "Нет участников"
        bot.send_message(uid, text, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("◀️ Назад", callback_data="main_menu")))
    elif c.data == "convert":
        if user.get("last_convert") and parse_date(user["last_convert"]) and now_msk().date() == (parse_date(user["last_convert"]) + timedelta(hours=3)).date(): return bot.answer_callback_query(c.id, "❌ Уже сегодня!")
        if user["rating"] < 5.1: return bot.answer_callback_query(c.id, "❌ Нужно 5.1% рейтинга")
        user["rating"] -= 5.0
        user["luck"] = min(50.0, user["luck"] + 1.0)
        user["last_convert"] = format_msk(datetime.now())
        save_data(data)
        bot.answer_callback_query(c.id, "✅ Конвертация!")
    elif c.data == "inventory":
        inv = user.get("inventory", {})
        sil = f" (активен до {parse_date(user['silencer_until']).strftime('%H:%M')})" if user.get("silencer_until") and parse_date(user["silencer_until"]) and datetime.now() < parse_date(user["silencer_until"]) else ""
        bot.send_message(uid, f"🎒 ИНВЕНТАРЬ\n\n🍀 Амулет: {inv.get('amulet',0)}\n🔇 Глушитель: {inv.get('silencer',0)}{sil}\n👑 VIP-пропуск: {inv.get('vip_pass',0)}", reply_markup=inventory_kb(user))
    elif c.data == "use_amulet":
        if user.get("inventory",{}).get("amulet",0) > 0:
            user["rating"] = min(95.0, user["rating"] + 10.0)
            user["inventory"]["amulet"] -= 1
            save_data(data)
            bot.answer_callback_query(c.id, "🍀 +10% рейтинга!")
        else: bot.answer_callback_query(c.id, "Нет амулета")
    elif c.data == "activate_silencer":
        if user.get("inventory",{}).get("silencer",0) > 0 and not user.get("silencer_until"):
            user["silencer_until"] = format_msk(now_msk() + timedelta(hours=8))
            user["inventory"]["silencer"] -= 1
            save_data(data)
            bot.answer_callback_query(c.id, "🔇 Глушитель активирован")
        else: bot.answer_callback_query(c.id, "Нельзя активировать")
    elif c.data == "deactivate_silencer":
        if user.get("silencer_until"):
            user["silencer_until"] = None
            save_data(data)
            bot.answer_callback_query(c.id, "🔇 Глушитель выключен")
    elif c.data == "use_vippass":
        if user.get("inventory",{}).get("vip_pass",0) > 0:
            user["vip_until"] = format_msk(now_msk() + timedelta(days=3))
            user["inventory"]["vip_pass"] -= 1
            check_and_fix_rating(uid)
            save_data(data)
            bot.answer_callback_query(c.id, "👑 VIP на 3 дня!")
        else: bot.answer_callback_query(c.id, "Нет VIP-пропуска")
    elif c.data == "quests":
        gen_quests(uid)
        q = user.get("quests", {})
        text = "📋 КВЕСТЫ\n\n" + "\n".join([f"{'✅' if q.get('completed',[False])[i] else '☐'} {t['desc']} ({q.get('progress',[0])[i]}/{t['target']}) — {t['reward']}" for i,t in enumerate(q.get("tasks",[]))]) + f"\n\n🏆 Бонус: {'✅' if user.get('quest_bonus_ready') else '❌'}"
        bot.send_message(uid, text, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("◀️ Назад", callback_data="main_menu")))
    elif c.data == "post_history":
        if not user.get("my_posts"): return bot.send_message(uid, "📋 Нет постов", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("◀️ Назад", callback_data="main_menu")))
        mk = InlineKeyboardMarkup(row_width=1)
        for pid in user["my_posts"][-5:]:
            pd = user.get("post_history_data",{}).get(str(pid),{})
            if pd: mk.add(InlineKeyboardButton(f"📝 {pd['text'][:30]}... [{pd.get('likes',0)}👍]", callback_data=f"history_post_{pid}"))
        mk.add(InlineKeyboardButton("◀️ Назад", callback_data="main_menu"))
        bot.send_message(uid, "📋 ИСТОРИЯ ПОСТОВ", reply_markup=mk)
    elif c.data.startswith("history_post_"):
        pid = c.data.split("_")[2]
        pd = user.get("post_history_data",{}).get(pid,{})
        if pd:
            mk = InlineKeyboardMarkup(row_width=2)
            mk.add(InlineKeyboardButton("🔁 Повторить", callback_data=f"retry_post_{pid}"), InlineKeyboardButton("🗑 Удалить", callback_data=f"history_delete_{pid}"))
            mk.add(InlineKeyboardButton("◀️ Назад", callback_data="post_history"))
            bot.send_message(uid, f"📝 Пост\n\n{pd['text']}\n\n👍 {pd.get('likes',0)} 👎 {pd.get('dislikes',0)}", reply_markup=mk)
    elif c.data.startswith("retry_post_"):
        pid = c.data.split("_")[2]
        pd = user.get("post_history_data",{}).get(pid,{})
        if pd:
            can, cd = check_post_cd(user)
            if not can: return bot.answer_callback_query(c.id, f"Жди {format_time(cd)}")
            post = {"id": int(time.time()*1000), "user_id": str(uid), "text": pd["text"], "time": format_msk(datetime.now()), "link_url": pd.get("link_url",""), "link_text": pd.get("link_text","")}
            user["last_post_time"] = format_msk(datetime.now())
            user["posts_count"] = user.get("posts_count",0)+1
            sent = send_post_to_users(post, uid)
            user["total_posts"] += 1
            save_data(data)
            bot.answer_callback_query(c.id, f"✅ Отправлено {sent}")
    elif c.data.startswith("history_delete_"):
        pid = c.data.split("_")[2]
        deleted = delete_post_globally(pid)
        bot.answer_callback_query(c.id, f"🗑 Удалено у {deleted}")
    elif c.data == "hotline":
        if user.get("last_hotline") and parse_date(user["last_hotline"]) and datetime.now() < parse_date(user["last_hotline"]) + timedelta(hours=1):
            return bot.answer_callback_query(c.id, "⏳ Раз в час")
        bot.send_message(uid, "📞 Напиши сообщение для админов:", reply_markup=cancel_kb())
        bot.register_next_step_handler_by_chat_id(uid, receive_hotline)
    elif c.data == "shop":
        bot.send_message(uid, f"⭐ МАГАЗИН\n\n👑 VIP на неделю — 100 ⭐\n📈 +25% рейтинга — 50 ⭐\n🎰 +10% удачи — 15 ⭐\n\nПиши {OWNER_USERNAME}", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("◀️ Назад", callback_data="main_menu")))
    elif c.data == "info":
        bot.send_message(uid, f"ℹ️ LowHigh v5.1\n👑 Владелец: {OWNER_USERNAME}\n📌 Некоммерческая рассылка", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("◀️ Назад", callback_data="main_menu")))

def inventory_kb(user):
    mk = InlineKeyboardMarkup(row_width=2)
    if user.get("inventory",{}).get("amulet",0): mk.add(InlineKeyboardButton("🍀 Исп. амулет", callback_data="use_amulet"))
    if user.get("inventory",{}).get("silencer",0):
        if user.get("silencer_until"): mk.add(InlineKeyboardButton("🔇 Выкл. глушитель", callback_data="deactivate_silencer"))
        else: mk.add(InlineKeyboardButton("🔇 Вкл. глушитель", callback_data="activate_silencer"))
    if user.get("inventory",{}).get("vip_pass",0): mk.add(InlineKeyboardButton("👑 Исп. VIP-пропуск", callback_data="use_vippass"))
    mk.add(InlineKeyboardButton("◀️ Назад", callback_data="main_menu"))
    return mk

def set_delivery(msg):
    if not is_admin(msg.from_user.id): return
    try:
        val = int(msg.text.strip())
        if 0 <= val <= 100:
            data["delivery_coefficient"] = val
            save_data(data)
            bot.send_message(msg.from_user.id, f"✅ Коэффициент лички: {val}%", reply_markup=admin_kb())
        else: bot.send_message(msg.from_user.id, "❌ От 0 до 100")
    except: bot.send_message(msg.from_user.id, "❌ Число")

def set_group_delivery(msg):
    if not is_admin(msg.from_user.id): return
    try:
        val = int(msg.text.strip())
        if 0 <= val <= 100:
            data["group_delivery_coefficient"] = val
            save_data(data)
            bot.send_message(msg.from_user.id, f"✅ Коэффициент групп: {val}%", reply_markup=admin_kb())
        else: bot.send_message(msg.from_user.id, "❌ От 0 до 100")
    except: bot.send_message(msg.from_user.id, "❌ Число")

def receive_backup_file(msg):
    if not is_master(msg.from_user.id): return
    if msg.document and msg.document.file_name.endswith('.json'):
        try:
            new = json.loads(bot.download_file(bot.get_file(msg.document.file_id).file_path).decode('utf-8'))
            if "users" in new:
                global data
                data = new
                with open(DATA_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2)
                bot.send_message(msg.from_user.id, f"✅ Восстановлено! Пользователей: {len(data['users'])}")
            else: bot.send_message(msg.from_user.id, "❌ Не похоже на базу")
        except: bot.send_message(msg.from_user.id, "❌ Ошибка")
    else: bot.send_message(msg.from_user.id, "❌ Отправь JSON-файл")

def receive_interpol_post(msg):
    uid = msg.from_user.id
    if msg.text and msg.text.lower() in ["отмена","cancel"]: return bot.send_message(uid, "❌ Отменено", reply_markup=admin_kb())
    media = msg.photo[-1].file_id if msg.content_type == 'photo' else None
    text = msg.caption if msg.content_type == 'photo' else (msg.text if msg.content_type == 'text' else None)
    if not text: return bot.send_message(uid, "❌ Текст или текст+картинка")
    bot.send_message(uid, "📎 Отправь ссылку (или '-'):")
    bot.register_next_step_handler_by_chat_id(uid, lambda m: receive_interpol_link(m, media, text))

def receive_interpol_link(msg, media, text):
    uid = msg.from_user.id
    if msg.text and msg.text.lower() in ["отмена","cancel"]: return bot.send_message(uid, "❌ Отменено", reply_markup=admin_kb())
    link = "" if msg.text.strip() == "-" else msg.text.strip()
    bot.send_message(uid, "📝 Текст кнопки (или '-'):")
    bot.register_next_step_handler_by_chat_id(uid, lambda m: send_interpol_post(m, media, text, link))

def send_interpol_post(msg, media, text, link):
    uid = msg.from_user.id
    if msg.text and msg.text.lower() in ["отмена","cancel"]: return bot.send_message(uid, "❌ Отменено", reply_markup=admin_kb())
    btn = "" if msg.text.strip() == "-" else msg.text.strip()[:30]
    post = {"id": int(time.time()*1000), "user_id": str(uid), "username": "ADMIN", "text": text, "time": format_msk(datetime.now()), "media": media, "link_url": link, "link_text": btn}
    sent = send_post_to_users(post, uid, force_all=True, media=media)
    bot.send_message(uid, f"📢 Интерпол! Доставлено: {sent}", reply_markup=admin_kb())
    log_admin(uid, "Интерпол-рассылка", f"доставлено {sent}")

def reject_with_reason(msg, post):
    uid = msg.from_user.id
    reason = msg.text if msg.text and msg.text != '-' else "Не указана"
    try: bot.send_message(int(post["user_id"]), f"❌ Пост отклонён\nПричина: {reason}")
    except: pass
    bot.send_message(uid, f"❌ Отклонён\nПричина отправлена автору", reply_markup=admin_kb())

def receive_hotline(msg):
    uid = msg.from_user.id
    if msg.text and msg.text.lower() in ["отмена","cancel"]: return bot.send_message(uid, "❌ Отменено", reply_markup=main_kb())
    user = get_user(uid)
    user["last_hotline"] = format_msk(datetime.now())
    save_data(data)
    for aid in data.get("admins",[]):
        try: bot.send_message(int(aid), f"📞 ГОРЯЧАЯ ЛИНИЯ\nОт: {get_name(uid, False)} (ID: {uid})\n\n{msg.text}")
        except: pass
    bot.send_message(uid, "✅ Отправлено админам!", reply_markup=main_kb())

def admin_search_user(msg):
    uid = msg.from_user.id
    target = resolve_target(msg.text.strip())
    if not target: return bot.send_message(uid, "❌ Не найден", reply_markup=admin_kb())
    user = get_user(target)
    text = f"👤 {get_name(target, False)}\nID: {target}\n📈 Рейтинг: {user['rating']:.1f}%\n🍀 Удача: {user['luck']:.2f}%\n📝 Постов: {user['total_posts']}\n👥 Рефералов: {len(user.get('referrals',[]))}"
    mk = InlineKeyboardMarkup(row_width=2)
    mk.add(InlineKeyboardButton("📈 +5%", callback_data=f"admin_add_rating_{target}_5"), InlineKeyboardButton("📈 -5%", callback_data=f"admin_add_rating_{target}_-5"))
    mk.add(InlineKeyboardButton("🍀 +5%", callback_data=f"admin_add_luck_{target}_5"), InlineKeyboardButton("🍀 -5%", callback_data=f"admin_add_luck_{target}_-5"))
    mk.add(InlineKeyboardButton("👑 VIP", callback_data=f"admin_make_vip_{target}"), InlineKeyboardButton("✅ Вериф", callback_data=f"admin_make_verified_{target}"))
    mk.add(InlineKeyboardButton("🚫 Бан", callback_data=f"admin_ban_{target}"), InlineKeyboardButton("◀️ Назад", callback_data="admin_main"))
    bot.send_message(uid, text, reply_markup=mk)

def give_vip_to_all_with_bonus():
    count = 0
    until = now_msk() + timedelta(days=1)
    bonus = random.choice(["📈 +5% рейтинга", "🍀 +1% удачи", "🎰 Бесплатная крутка", "🔇 Глушитель", "🍀 Амулет"])
    for uid in data["users"]:
        if uid in data["banned_users"]: continue
        user = get_user(uid)
        user["vip_until"] = format_msk(until)
        check_and_fix_rating(uid)
        count += 1
    save_data(data)
    return count, bonus

def get_random_post():
    all_posts = []
    for uid, u in data["users"].items():
        if uid in data["banned_users"]: continue
        for pid, pd in u.get("post_history_data", {}).items():
            if pd.get("text"): all_posts.append({"author_name": get_name(uid, False), "text": pd["text"], "likes": pd.get("likes",0), "date": pd.get("date","?")[:10]})
    return random.choice(all_posts) if all_posts else None

# ========== ФОН ==========
def background():
    last_tax, last_reset, last_clean, last_backup = None, None, None, None
    while True:
        time.sleep(60)
        now = now_msk()
        if not data.get("last_tax_date") or now.date() > parse_date(data["last_tax_date"]).date():
            for u in data["users"].values():
                if u.get("rating",0) > 5.0:
                    u["rating"] = max(5.0, u["rating"] - 1.0)
                    if is_vip(u) or is_verified(u): u["rating"] = max(10.0, u["rating"])
            data["last_tax_date"] = format_msk(now)
            save_data(data)
        if now.weekday() == 5 and (not last_reset or last_reset.date() != now.date()):
            for u in data["users"].values(): u["weekly_activity"] = u["weekly_posts"] = u["weekly_likes"] = 0
            last_reset = now
        if not last_clean or now.date() > last_clean.date():
            deactivate_inactive_users()
            cleanup_old_posts()
            last_clean = now
        if not last_backup or now.hour != last_backup.hour:
            send_auto_backup()
            last_backup = now
        if now.minute % 5 == 0: save_data(data)

def deactivate_inactive_users():
    now = now_msk()
    cutoff = now - timedelta(days=7)
    for uid, u in data["users"].items():
        if u.get("last_activity") and parse_date(u["last_activity"]) and parse_date(u["last_activity"]) < cutoff and u.get("is_active", True):
            u["is_active"] = False
            data["deleted_users_log"].append({"id": uid, "name": get_name(uid, False), "deactivated_at": format_msk(now), "reason": "Неактивность"})
    save_data(data)

def cleanup_old_posts():
    cutoff = now_msk() - timedelta(days=7)
    for uid, u in data["users"].items():
        if "my_posts" in u:
            u["my_posts"] = [pid for pid in u["my_posts"] if u.get("post_history_data",{}).get(str(pid),{}).get("date") and parse_date(u["post_history_data"][str(pid)]["date"]) and parse_date(u["post_history_data"][str(pid)]["date"]) > cutoff]
    save_data(data)

def send_auto_backup():
    try:
        with open(DATA_FILE, 'rb') as f: bot.send_document(OWNER_ID, f, visible_file_name=f'backup_{now_msk().strftime("%Y%m%d_%H%M%S")}.json')
    except: pass

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try: sock.bind(("localhost", 9999))
    except: print("❌ Бот уже запущен!"); sys.exit(1)
    sock.close()
    print("="*50 + "\n     LowHigh v5.1\n" + "="*50)
    log("INFO", f"Загружено {len(data['users'])} пользователей, {len(data.get('groups',{}))} групп")
    threading.Thread(target=background, daemon=True).start()
    while True:
        try: bot.infinity_polling()
        except Exception as e: log("ERROR", str(e)); time.sleep(10)
