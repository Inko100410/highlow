# LowHigh v3.3 — ФИНАЛЬНАЯ ВЕРСИЯ (ВСЁ ИСПРАВЛЕНО)

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import random
import time
import json
import os
from datetime import datetime, timedelta
import threading
import re

# ========== НАСТРОЙКИ ==========
TOKEN = "8265086577:AAFqojYbFSIRE2FZg0jnJ0Qgzdh0w9_j6z4"
MASTER_ADMINS = [6656110482, 8525294722]  # твой ID и подруги
OWNER_USERNAME = "@nickelium"

bot = telebot.TeleBot(TOKEN)

# ========== ЦВЕТА ДЛЯ ЛОГОВ ==========
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_log(level, message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    if level == "INFO":
        print(f"{Colors.BLUE}[{timestamp}][INFO]{Colors.END} {message}")
    elif level == "SUCCESS":
        print(f"{Colors.GREEN}[{timestamp}][✓]{Colors.END} {message}")
    elif level == "WARNING":
        print(f"{Colors.YELLOW}[{timestamp}][⚠]{Colors.END} {message}")
    elif level == "ERROR":
        print(f"{Colors.RED}[{timestamp}][✗]{Colors.END} {message}")
    elif level == "POST":
        print(f"{Colors.HEADER}[{timestamp}][📢]{Colors.END} {message}")
    elif level == "CASINO":
        print(f"{Colors.BOLD}[{timestamp}][🎰]{Colors.END} {message}")

# ========== БАЗА ДАННЫХ ==========
DATA_FILE = "bot_data.json"

def save_data(data):
    temp_file = DATA_FILE + ".tmp"
    backup_file = DATA_FILE + ".backup"
    
    try:
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        if os.path.exists(DATA_FILE):
            os.replace(DATA_FILE, backup_file)
        
        os.replace(temp_file, DATA_FILE)
        
        if os.path.exists(backup_file):
            os.remove(backup_file)
            
        print_log("INFO", "Данные сохранены")
        return True
    except Exception as e:
        print_log("ERROR", f"Ошибка сохранения: {e}")
        if os.path.exists(backup_file):
            os.replace(backup_file, DATA_FILE)
        return False

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print_log("INFO", f"Загружено {len(data.get('users', {}))} пользователей")
                return data
        except:
            print_log("ERROR", "Основной файл повреждён")
    
    backup_file = DATA_FILE + ".backup"
    if os.path.exists(backup_file):
        try:
            with open(backup_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print_log("WARNING", "Загружено из бэкапа")
                with open(DATA_FILE, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                return data
        except:
            print_log("ERROR", "Бэкап повреждён")
    
    return {
        "users": {},
        "posts": [],
        "banned_users": [],
        "admins": MASTER_ADMINS.copy(),
        "vip_users": [],
        "verified_users": [],
        "post_history": {},
        "post_contents": {},
        "stats": {
            "total_attempts": 0,
            "total_wins": 0,
            "total_posts_sent": 0
        },
        "post_reactions": {},
        "global_reactions": {},
        "hotline_cooldown": {}  # для горячей линии
    }

data = load_data()

# ========== РАБОТА С ПОЛЬЗОВАТЕЛЯМИ ==========

def get_user(user_id):
    user_id = str(user_id)
    
    if user_id in data["banned_users"]:
        return None
    
    if user_id not in data["users"]:
        data["users"][user_id] = {
            "rating": 5.0,
            "luck": 1.0,
            "fail_counter": 0,
            "incoming_chance": 50.0,
            "last_casino": None,
            "last_post_time": None,
            "posts_count": 0,
            "last_convert": None,
            "last_hotline": None,  # для КД горячей линии
            "referrals": [],
            "referrer": None,
            "total_posts": 0,
            "total_casino_attempts": 0,
            "total_wins": 0,
            "username": None,
            "first_name": None,
            "admin_notifications": True,
            "join_date": datetime.now().isoformat(),
            "vip_until": None,
            "inventory": {
                "amulet": 0,
                "silencer": 0,
                "vip_pass": 0
            },
            "silencer_until": None,
            "weekly_activity": 0,
            "weekly_posts": 0,
            "weekly_likes": 0,
            "quests": {},
            "quest_bonus_ready": False,
            "my_posts": [],
            "post_history_data": {}
        }
        print_log("SUCCESS", f"Новый пользователь! ID: {user_id}")
        save_data(data)
    
    return data["users"][user_id]

def get_user_display_name(user_id):
    user_id = str(user_id)
    user = data["users"].get(user_id)
    if not user:
        return "Неизвестно"
    
    if user.get("username"):
        return user["username"]
    
    if user.get("first_name"):
        return user["first_name"]
    
    try:
        chat = bot.get_chat(int(user_id))
        name = chat.first_name or "Аноним"
        user["first_name"] = name
        save_data(data)
        return name
    except:
        return f"User_{user_id[-4:]}"

def get_user_status_emoji(user_id):
    user_id = str(user_id)
    if is_vip(user_id):
        return "👑"
    elif is_verified(user_id):
        return "✅"
    else:
        return "📝"

def get_max_referrals(user_id):
    user_id = str(user_id)
    if is_vip(user_id):
        return 50
    elif is_verified(user_id):
        return 25
    else:
        return 10

def get_post_cooldown(user_id):
    user_id = str(user_id)
    
    if is_vip(user_id):
        return 2
    
    user = get_user(user_id)
    if not user:
        return 8
    
    posts_count = user.get("posts_count", 0)
    
    if posts_count >= 37:
        return 4
    elif posts_count >= 22:
        return 5
    elif posts_count >= 12:
        return 6
    elif posts_count >= 5:
        return 7
    else:
        return 8

def check_post_cooldown(user):
    if not user["last_post_time"]:
        return True, 0
    
    last = datetime.fromisoformat(user["last_post_time"])
    cooldown_hours = get_post_cooldown(user)
    next_time = last + timedelta(hours=cooldown_hours)
    now = datetime.now()
    
    if now >= next_time:
        return True, 0
    return False, (next_time - now).total_seconds()

def check_hotline_cooldown(user):
    if not user.get("last_hotline"):
        return True, 0
    last = datetime.fromisoformat(user["last_hotline"])
    next_time = last + timedelta(hours=1)
    now = datetime.now()
    if now >= next_time:
        return True, 0
    return False, (next_time - now).total_seconds()

def get_max_post_length(user_id):
    user_id = str(user_id)
    if is_vip(user_id):
        return 500
    elif is_verified(user_id):
        return 300
    else:
        return 250

def check_casino_cooldown(user):
    if not user["last_casino"]:
        return True, 0
    last = datetime.fromisoformat(user["last_casino"])
    next_time = last + timedelta(hours=8)
    now = datetime.now()
    if now >= next_time:
        return True, 0
    return False, (next_time - now).total_seconds()

def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}ч {minutes}м"

def check_and_fix_rating(user_id):
    user = get_user(user_id)
    if not user:
        return False
    
    if (is_vip(user_id) or is_verified(user_id)) and user["rating"] < 10.0:
        user["rating"] = 10.0
        save_data(data)
        return True
    return False

# ========== ПРОВЕРКА ПРАВ ==========

def is_banned(user_id):
    return str(user_id) in data["banned_users"]

def is_admin(user_id):
    user_id_str = str(user_id)
    if user_id_str in [str(a) for a in MASTER_ADMINS]:
        return True
    return user_id_str in data.get("admins", [])

def is_master_admin(user_id):
    return str(user_id) in [str(a) for a in MASTER_ADMINS]

def is_vip(user_id):
    user_id = str(user_id)
    user = data["users"].get(user_id)
    if not user:
        return False
    
    if user.get("vip_until"):
        try:
            until = datetime.fromisoformat(user["vip_until"])
            if datetime.now() < until:
                return True
            else:
                user["vip_until"] = None
                save_data(data)
        except:
            user["vip_until"] = None
    
    return user_id in data.get("vip_users", [])

def is_verified(user_id):
    return str(user_id) in data.get("verified_users", [])

# ========== ПРИВЕТСТВИЕ ==========

WELCOME_TEXT = """
🎩 <b>LowHigh</b> 🎰

<b>Что это?</b>
Бесплатный бот для рассылки некоммерческой рекламы

<b>📝 Реклама:</b>
Пишешь пост → уходит другим пользователям
Шанс доставки зависит от рейтинга и удачи

<b>🎰 Казино:</b>
Крутка раз в 8 часов → выигрыш: предметы
Проиграл? Шанс растет: 0.01% → 0.02% → 0.03%...

<b>🔄 Конвертация:</b>
5% рейтинга → 1% удачи (раз в 24ч)

<b>👥 Рефералы:</b>
Друг = +1% к удаче навсегда

<b>📞 Горячая линия:</b>
Связь с админами (раз в час)

Погнали! 👇
"""

# ========== РАССЫЛКА ПОСТОВ ==========

def send_post_to_users(post, admin_id, force_all=False):
    from_user_id = post["user_id"]
    author = get_user(from_user_id)
    
    if not author:
        print_log("ERROR", f"Автор {from_user_id} не найден")
        return 0
    
    recipients = []
    for uid, user_data in data["users"].items():
        if uid == from_user_id or uid in data["banned_users"]:
            continue
        
        if user_data.get("silencer_until"):
            try:
                until = datetime.fromisoformat(user_data["silencer_until"])
                if datetime.now() < until:
                    continue
                else:
                    user_data["silencer_until"] = None
            except:
                user_data["silencer_until"] = None
        
        recipients.append((uid, user_data))
    
    if not recipients:
        try:
            bot.send_message(int(from_user_id), "😢 Пока нет других пользователей для рассылки")
        except:
            pass
        return 0
    
    total = len(recipients)
    print_log("POST", f"Рассылка от {get_user_display_name(from_user_id)}. Всего юзеров: {total}")
    
    if force_all:
        guaranteed = total
        chance_part = []
        print_log("POST", f"ИНТЕРПОЛ-РЕЖИМ: рассылка всем {total} пользователям")
    else:
        guaranteed = max(1, int(total * 0.01))
        print_log("POST", f"Гарантированная доставка: {guaranteed} чел")
        random.shuffle(recipients)
    
    guaranteed_recipients = recipients[:guaranteed]
    chance_recipients = recipients[guaranteed:]
    
    sent = 0
    post_id = post["id"]
    
    data["post_contents"][str(post_id)] = {
        "text": post["text"],
        "author_id": from_user_id,
        "author_name": get_user_display_name(from_user_id)
    }
    
    if str(post_id) not in data["post_reactions"]:
        data["post_reactions"][str(post_id)] = {"likes": [], "dislikes": [], "complaints": []}
    
    if str(post_id) not in data["post_history"]:
        data["post_history"][str(post_id)] = {}
    
    author_emoji = get_user_status_emoji(from_user_id)
    formatted_text = f"<i>{post['text']}</i>"
    
    if "my_posts" not in author:
        author["my_posts"] = []
    if post_id not in author["my_posts"]:
        author["my_posts"].append(post_id)
    
    if "post_history_data" not in author:
        author["post_history_data"] = {}
    author["post_history_data"][str(post_id)] = {
        "text": post["text"],
        "date": post["time"],
        "likes": 0,
        "dislikes": 0
    }
    
    for uid, user_data in guaranteed_recipients:
        try:
            markup = InlineKeyboardMarkup(row_width=3)
            markup.add(
                InlineKeyboardButton(f"👍 0", callback_data=f"like_{post_id}"),
                InlineKeyboardButton(f"👎 0", callback_data=f"dislike_{post_id}"),
                InlineKeyboardButton("⚠️", callback_data=f"complaint_{post_id}")
            )
            if is_admin(uid):
                markup.add(InlineKeyboardButton("🚫 УДАЛИТЬ У ВСЕХ", callback_data=f"global_delete_{post_id}"))
            
            msg = bot.send_message(
                int(uid),
                f"📢 <b>Пост</b> {author_emoji} от {get_user_display_name(from_user_id)}:\n\n{formatted_text}",
                parse_mode="HTML",
                reply_markup=markup
            )
            sent += 1
            author["rating"] = min(95.0, author["rating"] + 0.01)
            data["post_history"][str(post_id)][str(uid)] = msg.message_id
            author["weekly_activity"] = author.get("weekly_activity", 0) + 5
            author["weekly_posts"] = author.get("weekly_posts", 0) + 1
            print_log("SUCCESS", f"Пост доставлен {uid} (гарантия)")
        except:
            pass
    
    chance_hits = 0
    for uid, user_data in chance_recipients:
        if force_all:
            final = 100
        else:
            ref_bonus = 0
            if author.get("referrals"):
                total_ref = 0
                for rid in author["referrals"]:
                    ru = get_user(rid)
                    if ru:
                        total_ref += ru.get("rating", 0)
                ref_bonus = total_ref / 100
            
            final = user_data["incoming_chance"] + (author["rating"] / 2) + (author["luck"] / 10) + ref_bonus
            final = max(5, min(95, final))
        
        if random.uniform(0, 100) <= final:
            try:
                markup = InlineKeyboardMarkup(row_width=3)
                markup.add(
                    InlineKeyboardButton(f"👍 0", callback_data=f"like_{post_id}"),
                    InlineKeyboardButton(f"👎 0", callback_data=f"dislike_{post_id}"),
                    InlineKeyboardButton("⚠️", callback_data=f"complaint_{post_id}")
                )
                if is_admin(uid):
                    markup.add(InlineKeyboardButton("🚫 УДАЛИТЬ У ВСЕХ", callback_data=f"global_delete_{post_id}"))
                
                msg = bot.send_message(
                    int(uid),
                    f"📢 <b>Пост</b> {author_emoji} от {get_user_display_name(from_user_id)}:\n\n{formatted_text}",
                    parse_mode="HTML",
                    reply_markup=markup
                )
                sent += 1
                chance_hits += 1
                author["rating"] = min(95.0, author["rating"] + 0.01)
                data["post_history"][str(post_id)][str(uid)] = msg.message_id
                author["weekly_activity"] += 5
                author["weekly_posts"] += 1
            except:
                pass
    
    print_log("POST", f"✅ Пост доставлен {sent}/{total} юзерам (гарантия: {guaranteed}, шанс: {chance_hits})")
    
    try:
        bot.send_message(
            int(from_user_id),
            f"✅ <b>Твой пост разослан!</b>\n\n"
            f"📊 <b>Статистика доставки:</b>\n"
            f"👥 Всего пользователей: {total}\n"
            f"✅ Доставлено всего: {sent}\n"
            f"🎯 Гарантированно получили: {guaranteed}\n"
            f"🎲 По счастливому шансу: {chance_hits}\n\n"
            f"📈 Твой рейтинг вырос до: {author['rating']:.1f}%\n"
            f"🍀 Твоя удача: {author['luck']:.2f}%\n\n"
            f"🔥 Так держать!",
            parse_mode="HTML"
        )
    except:
        pass
    
    data["stats"]["total_posts_sent"] += 1
    save_data(data)
    return sent

def delete_post_globally(post_id):
    pid = str(post_id)
    if pid not in data["post_history"]:
        return 0
    cnt = 0
    for uid, mid in data["post_history"][pid].items():
        try:
            bot.delete_message(int(uid), mid)
            cnt += 1
        except:
            pass
    del data["post_history"][pid]
    if pid in data["post_contents"]:
        del data["post_contents"][pid]
    if pid in data["post_reactions"]:
        del data["post_reactions"][pid]
    save_data(data)
    return cnt

def update_post_reactions_buttons(post_id, chat_id, message_id):
    pid = str(post_id)
    react = data["post_reactions"].get(pid, {"likes": [], "dislikes": [], "complaints": []})
    likes = len(react["likes"])
    dislikes = len(react["dislikes"])
    
    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(
        InlineKeyboardButton(f"👍 {likes}", callback_data=f"like_{post_id}"),
        InlineKeyboardButton(f"👎 {dislikes}", callback_data=f"dislike_{post_id}"),
        InlineKeyboardButton("⚠️", callback_data=f"complaint_{post_id}")
    )
    
    try:
        bot.edit_message_reply_markup(chat_id, message_id, reply_markup=markup)
    except:
        pass

# ========== ТОП-10 (БЕЗ АДМИНОВ) ==========

def get_top_users():
    users = []
    for uid, u in data["users"].items():
        if uid not in data["banned_users"] and not is_admin(uid):  # админов не учитываем
            users.append({
                "name": get_user_display_name(uid),
                "rating": u.get("rating", 0),
                "luck": u.get("luck", 0),
                "posts": u.get("total_posts", 0)
            })
    return sorted(users, key=lambda x: x["rating"], reverse=True)[:10]

# ========== АНТИ-МАТ ==========

BAD_WORDS = ["хуй", "пизда", "ебать", "блядь", "сука", "гандон", "пидор", 
             "нахуй", "похуй", "залупа", "мудак", "долбоёб", "хуесос"]

def censor_text(text, user_id):
    if is_vip(user_id):
        return text
    censored = text
    for word in BAD_WORDS:
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        censored = pattern.sub("*" * len(word), censored)
    return censored

# ========== КВЕСТЫ ==========

QUEST_POOL = [
    {"desc": "Написать пост", "type": "post", "target": 1, "reward": "luck+1"},
    {"desc": "Написать 2 поста", "type": "post", "target": 2, "reward": "luck+2", "rare": True},
    {"desc": "Написать пост длиной >200 символов", "type": "post_length", "target": 200, "reward": "rating+1"},
    {"desc": "Получить 1 лайк", "type": "likes_recv", "target": 1, "reward": "rating+0.5"},
    {"desc": "Получить 3 лайка", "type": "likes_recv", "target": 3, "reward": "rating+1"},
    {"desc": "Получить 5 лайков", "type": "likes_recv", "target": 5, "reward": "luck+2", "rare": True},
    {"desc": "Поставить 1 лайк", "type": "likes_give", "target": 1, "reward": "luck+0.5"},
    {"desc": "Пригласить 1 друга", "type": "referral", "target": 1, "reward": "luck+1"},
    {"desc": "Пригласить 2 друзей", "type": "referral", "target": 2, "reward": "luck+2", "rare": True},
    {"desc": "Крутнуть казино 1 раз", "type": "casino", "target": 1, "reward": "luck+0.5"},
    {"desc": "Крутнуть казино 2 раза", "type": "casino", "target": 2, "reward": "luck+1", "rare": True},
    {"desc": "Выиграть в казино", "type": "casino_win", "target": 1, "reward": "luck+2"}
]

def generate_daily_quests(user_id):
    today = datetime.now().date().isoformat()
    user = get_user(user_id)
    if not user:
        return
    
    if user.get("quests") and user["quests"].get("date") == today:
        return
    
    available = [q for q in QUEST_POOL if not q.get("rare") or random.random() < 0.2]
    selected = random.sample(available, min(3, len(available)))
    
    quests = {
        "date": today,
        "tasks": [],
        "completed": [False] * 3,
        "progress": [0] * 3
    }
    
    for i, q in enumerate(selected):
        quests["tasks"].append({
            "desc": q["desc"],
            "type": q["type"],
            "target": q["target"],
            "reward": q["reward"]
        })
    
    user["quests"] = quests
    user["quest_bonus_ready"] = False
    save_data(data)

def update_quest_progress(user_id, qtype, value=1, extra=None):
    user = get_user(user_id)
    if not user or "quests" not in user:
        return
    
    quests = user["quests"]
    if quests.get("date") != datetime.now().date().isoformat():
        return
    
    changed = False
    for i, task in enumerate(quests["tasks"]):
        if quests["completed"][i]:
            continue
        
        match = False
        if task["type"] == qtype:
            match = True
        elif task["type"] == "post_length" and qtype == "post" and extra and extra > task["target"]:
            match = True
        
        if match:
            quests["progress"][i] += value
            if quests["progress"][i] >= task["target"]:
                quests["completed"][i] = True
                reward = task["reward"]
                if reward.startswith("luck+"):
                    user["luck"] = min(50.0, user["luck"] + float(reward[5:]))
                elif reward.startswith("rating+"):
                    user["rating"] = min(95.0, user["rating"] + float(reward[7:]))
                changed = True
    
    if changed:
        if all(quests["completed"]):
            user["quest_bonus_ready"] = True
        save_data(data)

# ========== ЕЖЕНЕДЕЛЬНАЯ АКТИВНОСТЬ ==========

def get_weekly_activity_top(limit=10):
    users = []
    for uid, u in data["users"].items():
        if uid not in data["banned_users"] and not is_admin(uid) and u.get("weekly_activity", 0) > 0:
            users.append({
                "id": uid,
                "name": get_user_display_name(uid),
                "activity": u.get("weekly_activity", 0)
            })
    return sorted(users, key=lambda x: x["activity"], reverse=True)[:limit]

def award_weekly_top():
    now = datetime.now()
    if now.weekday() != 4 or now.hour != 12 or now.minute != 0:
        return
    
    top = get_weekly_activity_top(1)
    if not top:
        return
    
    winner = top[0]
    try:
        bot.send_message(
            int(winner["id"]),
            f"🎁 <b>Ты стал самым активным на этой неделе!</b>\n\n"
            f"📊 Твоя активность: {winner['activity']} очков\n"
            f"⭐ Получи 15 звёзд от @nickelium\n\n"
            f"Поздравляем! 🎉",
            parse_mode="HTML"
        )
    except:
        pass

def reset_weekly_activity():
    now = datetime.now()
    if now.weekday() != 5:
        return
    
    for u in data["users"].values():
        u["weekly_activity"] = 0
        u["weekly_posts"] = 0
        u["weekly_likes"] = 0
    print_log("INFO", "Еженедельная активность сброшена")
    save_data(data)

# ========== НАЛОГ НА РЕЙТИНГ ==========

def apply_rating_tax():
    taxed = 0
    for uid, user in data["users"].items():
        if uid in data["banned_users"]:
            continue
        
        user["rating"] -= 1.0
        
        if is_vip(uid) or is_verified(uid):
            user["rating"] = max(10.0, user["rating"])
        else:
            user["rating"] = max(5.0, user["rating"])
        
        taxed += 1
    
    save_data(data)
    print_log("INFO", f"Налог: снят 1% у {taxed} пользователей")

# ========== КЛАВИАТУРЫ ==========

def main_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton("📝 Написать пост", callback_data="write_post"),
        InlineKeyboardButton("🎰 Бонус", callback_data="casino"),
        InlineKeyboardButton("👥 Рефералы", callback_data="referrals"),
        InlineKeyboardButton("📊 Статистика", callback_data="stats"),
        InlineKeyboardButton("🏆 Топ-10", callback_data="top"),
        InlineKeyboardButton("🔄 Конвертация", callback_data="convert"),
        InlineKeyboardButton("🎒 Инвентарь", callback_data="inventory"),
        InlineKeyboardButton("📋 Квесты", callback_data="quests"),
        InlineKeyboardButton("📋 История постов", callback_data="post_history"),
        InlineKeyboardButton("⭐ Магазин", callback_data="shop"),
        InlineKeyboardButton("📞 Горячая линия", callback_data="hotline"),
        InlineKeyboardButton("ℹ️ Инфо", callback_data="info")
    ]
    markup.add(*buttons)
    return markup

def casino_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🎲 Сделать крутку", callback_data="casino_spin"))
    markup.add(InlineKeyboardButton("◀️ Назад", callback_data="main_menu"))
    return markup

def cancel_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("❌ ОТМЕНА", callback_data="cancel_post"))
    return markup

def admin_main_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📝 Посты на модерации", callback_data="admin_posts_list"),
        InlineKeyboardButton("📢 Интерпол-рассылка", callback_data="admin_interpol"),
        InlineKeyboardButton("👑 VIP управление", callback_data="admin_vip_list"),
        InlineKeyboardButton("✅ Вериф управление", callback_data="admin_verified_list"),
        InlineKeyboardButton("👥 Админы", callback_data="admin_admins_list"),
        InlineKeyboardButton("🚫 Баны", callback_data="admin_bans_list"),
        InlineKeyboardButton("📊 Статистика бота", callback_data="admin_stats"),
        InlineKeyboardButton("📈 Активность", callback_data="admin_activity")
    )
    return markup

def admin_posts_list_keyboard(posts):
    markup = InlineKeyboardMarkup(row_width=1)
    for i, post in enumerate(posts[:5]):
        short = post['text'][:30] + "..." if len(post['text']) > 30 else post['text']
        markup.add(InlineKeyboardButton(f"{i+1}. {short}", callback_data=f"admin_post_{post['id']}"))
    markup.add(InlineKeyboardButton("◀️ Назад", callback_data="admin_main"))
    return markup

def admin_post_actions_keyboard(post_id):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("✅ ОДОБРИТЬ", callback_data=f"approve_{post_id}"),
        InlineKeyboardButton("❌ ОТКЛОНИТЬ", callback_data=f"reject_{post_id}"),
        InlineKeyboardButton("🚫 ЗАБАНИТЬ АВТОРА", callback_data=f"ban_user_{post_id}"),
        InlineKeyboardButton("📢 ИНТЕРПОЛ", callback_data=f"interpol_{post_id}"),
        InlineKeyboardButton("◀️ К списку", callback_data="admin_posts_list")
    )
    return markup

def admin_users_list_keyboard(users, prefix, back):
    markup = InlineKeyboardMarkup(row_width=1)
    for i, uid in enumerate(users[:10]):
        name = get_user_display_name(uid)
        markup.add(InlineKeyboardButton(f"{i+1}. {name}", callback_data=f"{prefix}_{uid}"))
    markup.add(InlineKeyboardButton("◀️ Назад", callback_data=back))
    return markup

def admin_user_actions_keyboard(uid, typ):
    markup = InlineKeyboardMarkup(row_width=2)
    if typ == "vip":
        markup.add(
            InlineKeyboardButton("❌ СНЯТЬ VIP", callback_data=f"remove_vip_{uid}"),
            InlineKeyboardButton("◀️ Назад", callback_data="admin_vip_list")
        )
    elif typ == "verified":
        markup.add(
            InlineKeyboardButton("❌ СНЯТЬ ВЕРИФ", callback_data=f"remove_verified_{uid}"),
            InlineKeyboardButton("◀️ Назад", callback_data="admin_verified_list")
        )
    elif typ == "admin" and uid not in [str(a) for a in MASTER_ADMINS]:
        markup.add(
            InlineKeyboardButton("❌ СНЯТЬ АДМИНА", callback_data=f"remove_admin_{uid}"),
            InlineKeyboardButton("◀️ Назад", callback_data="admin_admins_list")
        )
    elif typ == "banned":
        markup.add(
            InlineKeyboardButton("✅ РАЗБАНИТЬ", callback_data=f"unban_{uid}"),
            InlineKeyboardButton("◀️ Назад", callback_data="admin_bans_list")
        )
    return markup

def inventory_keyboard(user):
    markup = InlineKeyboardMarkup(row_width=2)
    inv = user.get("inventory", {})
    
    if inv.get("amulet", 0):
        markup.add(InlineKeyboardButton("🍀 Исп. амулет", callback_data="use_amulet"))
    
    if inv.get("silencer", 0):
        if user.get("silencer_until"):
            markup.add(InlineKeyboardButton("🔇 Выкл. глушитель", callback_data="deactivate_silencer"))
        else:
            markup.add(InlineKeyboardButton("🔇 Вкл. глушитель", callback_data="activate_silencer"))
    
    if inv.get("vip_pass", 0):
        markup.add(InlineKeyboardButton("👑 Исп. VIP-пропуск", callback_data="use_vippass"))
    
    markup.add(InlineKeyboardButton("◀️ Назад", callback_data="main_menu"))
    return markup

def post_history_keyboard(user):
    markup = InlineKeyboardMarkup(row_width=1)
    posts = user.get("my_posts", [])[-5:]
    for pid in posts:
        data = user.get("post_history_data", {}).get(str(pid), {})
        if data:
            short = data["text"][:30] + "..." if len(data["text"]) > 30 else data["text"]
            date = data["date"][:10] if data.get("date") else "?"
            markup.add(InlineKeyboardButton(
                f"📝 {short} [{data.get('likes',0)}👍] {date}",
                callback_data=f"history_post_{pid}"
            ))
    markup.add(InlineKeyboardButton("◀️ Назад", callback_data="main_menu"))
    return markup

def history_post_actions_keyboard(post_id):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🔁 Повторить", callback_data=f"retry_post_{post_id}"),
        InlineKeyboardButton("🗑 Удалить у всех", callback_data=f"history_delete_{post_id}"),
        InlineKeyboardButton("◀️ Назад", callback_data="post_history")
    )
    return markup

# ========== ОБРАБОТЧИКИ КОМАНД ==========

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        bot.send_message(user_id, "🚫 Вы забанены в этом боте.")
        return
    
    user = get_user(user_id)
    user["first_name"] = message.from_user.first_name
    
    args = message.text.split()
    if len(args) > 1:
        ref = args[1]
        if ref != str(user_id) and not user["referrer"]:
            referrer = get_user(ref)
            if referrer:
                max_ref = get_max_referrals(ref)
                if len(referrer["referrals"]) < max_ref and str(user_id) not in referrer["referrals"]:
                    user["referrer"] = ref
                    referrer["referrals"].append(str(user_id))
                    referrer["luck"] = min(50.0, referrer["luck"] + 1.0)
                    
                    try:
                        bot.send_message(
                            int(ref),
                            f"🎉 <b>У тебя новый реферал!</b>\n\n"
                            f"👤 {get_user_display_name(user_id)}\n"
                            f"🍀 Удача +1% (теперь {referrer['luck']:.1f}%)\n"
                            f"👥 Рефералов: {len(referrer['referrals'])}/{max_ref}",
                            parse_mode="HTML"
                        )
                        update_quest_progress(ref, "referral", 1)
                    except:
                        pass
                    save_data(data)
    
    user["username"] = message.from_user.username
    user["first_name"] = message.from_user.first_name
    
    generate_daily_quests(user_id)
    
    status = get_user_status_emoji(user_id)
    cd = get_post_cooldown(user_id)
    
    welcome = (WELCOME_TEXT + 
               f"\n\n<b>Твой профиль:</b>\n"
               f"Статус: {status}\n"
               f"📈 Рейтинг: {user['rating']:.1f}%\n"
               f"🍀 Удача: {user['luck']:.1f}%\n"
               f"⏱ КД на пост: {cd}ч\n\n"
               f"👇 Выбери действие:")
    
    bot.send_message(user_id, welcome, parse_mode="HTML", reply_markup=main_keyboard())
    print_log("INFO", f"Пользователь {user_id} зашёл в бота")

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, f"🚫 У тебя нет прав администратора.")
        return
    
    bot.send_message(
        user_id,
        "👑 <b>АДМИН-ПАНЕЛЬ</b>\n\n"
        "Выбери раздел:",
        parse_mode="HTML",
        reply_markup=admin_main_keyboard()
    )

@bot.message_handler(commands=['post'])
def cmd_post(message):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        bot.send_message(user_id, "🚫 Вы забанены")
        return
    
    user = get_user(user_id)
    can_post, cooldown = check_post_cooldown(user)
    
    if not can_post:
        bot.send_message(
            user_id,
            f"⏳ Подожди ещё {format_time(cooldown)} перед следующим постом",
            reply_markup=main_keyboard()
        )
        return
    
    prediction = user["rating"] / 2 + user["luck"] / 10
    prediction = max(5, min(95, prediction))
    max_len = get_max_post_length(user_id)
    
    bot.send_message(
        user_id,
        f"📊 <b>Прогноз доставки:</b> {prediction:.1f}%\n\n"
        f"📝 Отправь текст поста (максимум {max_len} символов, только текст):\n"
        f"✨ Постарайся написать что-то интересное!",
        parse_mode="HTML",
        reply_markup=cancel_keyboard()
    )
    bot.register_next_step_handler(message, receive_post)

@bot.message_handler(commands=['casino'])
def cmd_casino(message):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        return
    
    user = get_user(user_id)
    can_play, cooldown = check_casino_cooldown(user)
    
    status = f"🎰 <b>КАЗИНО LOWHIGH</b>\n\n"
    status += f"🍀 Твой шанс на победу: {user['luck']:.2f}%\n"
    
    if user.get("quest_bonus_ready"):
        status += f"🔥 Бонус +20% за квесты готов! 🔥\n"
    
    if can_play:
        status += f"\n✅ Можно играть! Нажми кнопку ниже.\n"
        status += f"\n💰 Возможные выигрыши:\n"
        status += f"• 🍀 Амулет удачи (+10% рейтинга)\n"
        status += f"• 🔇 Глушитель (8ч без рекламы)\n"
        status += f"• 👑 VIP-пропуск (3 дня VIP)\n"
        status += f"• Или +5% к рейтингу (если предмет уже есть)"
    else:
        status += f"\n⏳ Следующая попытка через: {format_time(cooldown)}"
    
    bot.send_message(user_id, status, parse_mode="HTML", reply_markup=casino_keyboard())

@bot.message_handler(commands=['spin'])
def cmd_spin(message):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        return
    
    user = get_user(user_id)
    can_play, cooldown = check_casino_cooldown(user)
    
    if not can_play:
        bot.send_message(
            user_id,
            f"⏳ Подожди ещё {format_time(cooldown)} до следующей крутки",
            reply_markup=casino_keyboard()
        )
        return
    
    old_rating = user["rating"]
    user["rating"] = max(5.0, user["rating"] - 1.0)
    if is_vip(user_id) or is_verified(user_id):
        user["rating"] = max(10.0, user["rating"])
    
    bonus = 20 if user.get("quest_bonus_ready") else 0
    if bonus:
        user["quest_bonus_ready"] = False
    
    roll = random.uniform(0, 100)
    won = roll <= (user["luck"] + bonus)
    
    if won:
        items = ["amulet", "silencer", "vip_pass"]
        item = random.choice(items)
        inv = user.get("inventory", {})
        
        if inv.get(item, 0) == 0:
            inv[item] = 1
            user["inventory"] = inv
            result = f"🎉 <b>ПОБЕДА!</b> 🎉\n\n"
            result += f"Ты выиграл предмет: {item}!\n"
            if item == "amulet":
                result += f"🍀 Амулет даст +10% к рейтингу при использовании"
            elif item == "silencer":
                result += f"🔇 Глушитель отключит рекламу на 8 часов"
            else:
                result += f"👑 VIP-пропуск даст 3 дня VIP"
        else:
            user["rating"] = min(95.0, user["rating"] + 5.0)
            result = f"🎉 <b>ПОБЕДА!</b> 🎉\n\n"
            result += f"+5% к рейтингу (предмет уже есть в инвентаре)"
        
        user["total_wins"] += 1
        user["fail_counter"] = 0
        data["stats"]["total_wins"] += 1
        update_quest_progress(user_id, "casino_win", 1)
    else:
        user["fail_counter"] += 1
        inc = user["fail_counter"] * 0.01
        user["luck"] = min(50.0, user["luck"] + inc)
        result = f"😢 <b>ПРОИГРЫШ</b>\n\n"
        result += f"Удача +{inc:.2f}% → {user['luck']:.2f}%\n"
        result += f"Рейтинг: {old_rating:.1f}% → {user['rating']:.1f}%\n"
        result += f"🍀 В следующий раз повезёт!"
    
    user["last_casino"] = datetime.now().isoformat()
    user["total_casino_attempts"] += 1
    user["weekly_activity"] += 1
    data["stats"]["total_attempts"] += 1
    update_quest_progress(user_id, "casino", 1)
    save_data(data)
    
    bot.send_message(
        user_id,
        result,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("🎰 Ещё раз", callback_data="casino"),
            InlineKeyboardButton("🏠 В меню", callback_data="main_menu")
        )
    )

@bot.message_handler(commands=['top'])
def cmd_top(message):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        return
    
    top = get_top_users()
    text = "🏆 <b>ТОП-10 ПО РЕЙТИНГУ</b> 🏆\n\n"
    
    if not top:
        text += "Пока нет участников"
    else:
        for i, u in enumerate(top, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
            text += f"{medal} <b>{i}.</b> {u['name']}\n"
            text += f"   📈 {u['rating']:.1f}% | 🍀 {u['luck']:.1f}% | 📝 {u['posts']}\n"
    
    bot.send_message(user_id, text, parse_mode="HTML")

@bot.message_handler(commands=['help'])
def cmd_help(message):
    help_text = """
<b>📚 КОМАНДЫ LOWHIGH</b>

<b>Основные команды:</b>
/post - Написать пост для рассылки
/casino - Информация о казино
/spin - Сделать крутку (доступно раз в 8ч)
/top - Топ-10 игроков по рейтингу
/convert - Обменять 5% рейтинга на 1% удачи
/start - Главное меню
/help - Это сообщение

<b>Дополнительно:</b>
В главном меню есть кнопки:
• 👥 Рефералы — приглашай друзей
• 📊 Статистика — твой профиль
• 🎒 Инвентарь — твои предметы
• 📋 Квесты — ежедневные задания
• 📋 История постов — твои посты
• ⭐ Магазин — покупки за звёзды
• 📞 Горячая линия — связь с админами
• ℹ️ Инфо — о проекте

<b>👑 Админ-команды:</b>
/admin - Панель администратора
/setrating ID знач - изменить рейтинг
/setluck ID знач - изменить удачу
/addadmin ID - назначить админа
/removeadmin ID - удалить админа
/addvip ID [дни] - выдать VIP
/vipinfo ID - инфо о VIP
/removevip ID - снять VIP
/addverified ID - верифицировать
/removeverified ID - снять верификацию
/ban ID - забанить
/unban ID - разбанить
/delpost ID - удалить пост у всех
/restime ID - сбросить КД
    """
    bot.send_message(message.from_user.id, help_text, parse_mode="HTML")

@bot.message_handler(commands=['convert'])
def cmd_convert(message):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        return
    
    user = get_user(user_id)
    
    if user.get("last_convert"):
        last = datetime.fromisoformat(user["last_convert"])
        if datetime.now().date() == last.date():
            bot.send_message(
                user_id,
                "❌ Ты уже конвертил сегодня! Завтра будет новая попытка.",
                reply_markup=main_keyboard()
            )
            return
    
    if user["rating"] < 5.1:
        bot.send_message(
            user_id,
            "❌ Мало рейтинга! Нужно минимум 5.1%",
            reply_markup=main_keyboard()
        )
        return
    
    old_rating = user["rating"]
    old_luck = user["luck"]
    
    user["rating"] -= 5.0
    user["luck"] = min(50.0, user["luck"] + 1.0)
    user["last_convert"] = datetime.now().isoformat()
    save_data(data)
    
    bot.send_message(
        user_id,
        f"✅ <b>Конвертация выполнена!</b>\n\n"
        f"📈 Рейтинг: {old_rating:.1f}% → {user['rating']:.1f}%\n"
        f"🍀 Удача: {old_luck:.1f}% → {user['luck']:.1f}%\n\n"
        f"Отлично!",
        parse_mode="HTML",
        reply_markup=main_keyboard()
    )

@bot.message_handler(commands=['restime'])
def restime(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "🚫 Не админ")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(user_id, "❌ Использование: /restime ID")
        return
    
    target_id = args[1]
    target = get_user(target_id)
    
    if not target:
        bot.send_message(user_id, "❌ Пользователь не найден")
        return
    
    target["last_casino"] = None
    target["last_post_time"] = None
    save_data(data)
    
    bot.send_message(
        user_id,
        f"✅ КД сброшены для пользователя {target_id}"
    )
    try:
        bot.send_message(
            int(target_id),
            f"🔄 Админ сбросил твои кулдауны! Можешь снова писать пост и крутить казино."
        )
    except:
        pass

# ========== АДМИН-КОМАНДЫ ==========

@bot.message_handler(commands=['setrating'])
def set_rating(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "🚫 Не админ")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(user_id, "❌ Использование: /setrating ID [значение] или /setrating значение")
        return
    
    try:
        if len(args) == 3:
            target_id = args[1]
            val = float(args[2])
        else:
            target_id = str(user_id)
            val = float(args[1])
        
        target = get_user(target_id)
        if not target:
            bot.send_message(user_id, "❌ Пользователь не найден")
            return
        
        old = target["rating"]
        target["rating"] = max(5.0, min(95.0, val))
        if is_vip(target_id) or is_verified(target_id):
            target["rating"] = max(10.0, target["rating"])
        save_data(data)
        
        bot.send_message(
            user_id,
            f"✅ Рейтинг изменён\n"
            f"👤 {get_user_display_name(target_id)}\n"
            f"📈 {old:.1f}% → {target['rating']:.1f}%"
        )
        
        if target_id != str(user_id):
            try:
                bot.send_message(
                    int(target_id),
                    f"👑 Админ изменил твой рейтинг\n"
                    f"📈 {old:.1f}% → {target['rating']:.1f}%"
                )
            except:
                pass
    except:
        bot.send_message(user_id, "❌ Ошибка. Используй /setrating ID 50")

@bot.message_handler(commands=['setluck'])
def set_luck(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "🚫 Не админ")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(user_id, "❌ Использование: /setluck ID [значение] или /setluck значение")
        return
    
    try:
        if len(args) == 3:
            target_id = args[1]
            val = float(args[2])
        else:
            target_id = str(user_id)
            val = float(args[1])
        
        target = get_user(target_id)
        if not target:
            bot.send_message(user_id, "❌ Пользователь не найден")
            return
        
        old = target["luck"]
        target["luck"] = max(1.0, min(50.0, val))
        save_data(data)
        
        bot.send_message(
            user_id,
            f"✅ Удача изменена\n"
            f"👤 {get_user_display_name(target_id)}\n"
            f"🍀 {old:.1f}% → {target['luck']:.1f}%"
        )
        
        if target_id != str(user_id):
            try:
                bot.send_message(
                    int(target_id),
                    f"👑 Админ изменил твою удачу\n"
                    f"🍀 {old:.1f}% → {target['luck']:.1f}%"
                )
            except:
                pass
    except:
        bot.send_message(user_id, "❌ Ошибка. Используй /setluck ID 25")

@bot.message_handler(commands=['addadmin'])
def add_admin(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "🚫 Не админ")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(user_id, "❌ Использование: /addadmin ID")
        return
    
    try:
        new_id = int(args[1])
        new_id_str = str(new_id)
        
        if new_id_str not in data["admins"]:
            data["admins"].append(new_id_str)
            save_data(data)
            bot.send_message(
                user_id,
                f"✅ Пользователь {new_id} назначен администратором"
            )
            try:
                bot.send_message(
                    new_id,
                    f"🎉 <b>Поздравляем!</b>\n\n"
                    f"Ты стал администратором бота LowHigh!\n"
                    f"Используй /admin для входа в панель управления.",
                    parse_mode="HTML"
                )
            except:
                pass
        else:
            bot.send_message(user_id, "⚠️ Уже администратор")
    except:
        bot.send_message(user_id, "❌ Неверный ID")

@bot.message_handler(commands=['removeadmin'])
def remove_admin(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "🚫 Не админ")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(user_id, "❌ Использование: /removeadmin ID")
        return
    
    try:
        rem_id = int(args[1])
        rem_id_str = str(rem_id)
        
        if rem_id_str == str(user_id):
            bot.send_message(user_id, "❌ Нельзя удалить самого себя")
            return
        
        if rem_id_str in [str(a) for a in MASTER_ADMINS]:
            bot.send_message(user_id, "❌ Нельзя удалить главного администратора")
            return
        
        if rem_id_str in data["admins"]:
            data["admins"].remove(rem_id_str)
            save_data(data)
            bot.send_message(
                user_id,
                f"✅ Администратор {rem_id} удалён"
            )
            try:
                bot.send_message(
                    rem_id,
                    f"❌ Твой статус администратора был удалён."
                )
            except:
                pass
        else:
            bot.send_message(user_id, "⚠️ Не администратор")
    except:
        bot.send_message(user_id, "❌ Неверный ID")

@bot.message_handler(commands=['addvip'])
def add_vip(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "🚫 Не админ")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(user_id, "❌ Использование: /addvip ID [дни]")
        return
    
    try:
        new_id = int(args[1])
        new_id_str = str(new_id)
        
        if len(args) >= 3:
            days = int(args[2])
            user = get_user(new_id_str)
            if user:
                until = datetime.now() + timedelta(days=days)
                user["vip_until"] = until.isoformat()
                check_and_fix_rating(new_id_str)
                save_data(data)
                bot.send_message(
                    user_id,
                    f"👑 VIP на {days} дней для {new_id}\n"
                    f"Действует до {until.strftime('%d.%m.%Y %H:%M')}"
                )
                try:
                    bot.send_message(
                        new_id,
                        f"👑 <b>Поздравляем!</b>\n\n"
                        f"Ты получил VIP статус на {days} дней!\n"
                        f"• КД на пост: 2 часа\n"
                        f"• Рефералов: до 50\n"
                        f"• Длина поста: 500 символов\n\n"
                        f"Твой рейтинг поднят до 10%",
                        parse_mode="HTML"
                    )
                except:
                    pass
        else:
            if new_id_str not in data.get("vip_users", []):
                if "vip_users" not in data:
                    data["vip_users"] = []
                data["vip_users"].append(new_id_str)
                check_and_fix_rating(new_id_str)
                save_data(data)
                bot.send_message(
                    user_id,
                    f"👑 Постоянный VIP для {new_id}"
                )
                try:
                    bot.send_message(
                        new_id,
                        f"👑 <b>Поздравляем!</b>\n\n"
                        f"Ты получил постоянный VIP статус!\n"
                        f"• КД на пост: 2 часа\n"
                        f"• Рефералов: до 50\n"
                        f"• Длина поста: 500 символов\n\n"
                        f"Твой рейтинг поднят до 10%",
                        parse_mode="HTML"
                    )
                except:
                    pass
            else:
                bot.send_message(user_id, "⚠️ Уже VIP")
    except:
        bot.send_message(user_id, "❌ Ошибка. Используй /addvip ID [дни]")

@bot.message_handler(commands=['vipinfo'])
def vipinfo(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "🚫 Не админ")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(user_id, "❌ Использование: /vipinfo ID")
        return
    
    try:
        target_id = args[1]
        target = get_user(target_id)
        
        if not target:
            bot.send_message(user_id, "❌ Пользователь не найден")
            return
        
        text = f"👑 <b>Информация о VIP</b>\n\n"
        text += f"ID: {target_id}\n"
        text += f"Имя: {get_user_display_name(target_id)}\n\n"
        
        if target.get("vip_until"):
            until = datetime.fromisoformat(target["vip_until"])
            if until > datetime.now():
                left = until - datetime.now()
                text += f"Статус: ✅ активен\n"
                text += f"До: {until.strftime('%d.%m.%Y %H:%M')}\n"
                text += f"Осталось: {left.days} дн. {left.seconds//3600} ч."
            else:
                text += f"Статус: ❌ истёк\n"
                text += f"Истёк: {until.strftime('%d.%m.%Y %H:%M')}"
                target["vip_until"] = None
                save_data(data)
        elif target_id in data.get("vip_users", []):
            text += f"Статус: ✅ постоянный VIP"
        else:
            text += f"Статус: ❌ не VIP"
        
        bot.send_message(user_id, text, parse_mode="HTML")
    except:
        bot.send_message(user_id, "❌ Ошибка")

@bot.message_handler(commands=['removevip'])
def remove_vip(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "🚫 Не админ")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(user_id, "❌ Использование: /removevip ID")
        return
    
    try:
        rem_id = int(args[1])
        rem_id_str = str(rem_id)
        
        user = get_user(rem_id_str)
        removed = False
        
        if user and user.get("vip_until"):
            user["vip_until"] = None
            removed = True
        
        if rem_id_str in data.get("vip_users", []):
            data["vip_users"].remove(rem_id_str)
            removed = True
        
        if removed:
            save_data(data)
            bot.send_message(
                user_id,
                f"✅ VIP статус удалён у {rem_id}"
            )
            try:
                bot.send_message(
                    rem_id,
                    f"❌ Твой VIP статус был удалён администратором."
                )
            except:
                pass
        else:
            bot.send_message(user_id, "⚠️ У пользователя нет VIP статуса")
    except:
        bot.send_message(user_id, "❌ Ошибка")

@bot.message_handler(commands=['addverified'])
def add_verified(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "🚫 Не админ")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(user_id, "❌ Использование: /addverified ID")
        return
    
    try:
        new_id = int(args[1])
        new_id_str = str(new_id)
        
        if new_id_str not in data.get("verified_users", []):
            if "verified_users" not in data:
                data["verified_users"] = []
            data["verified_users"].append(new_id_str)
            check_and_fix_rating(new_id_str)
            save_data(data)
            bot.send_message(
                user_id,
                f"✅ Пользователь {new_id} верифицирован"
            )
            try:
                bot.send_message(
                    new_id,
                    f"✅ <b>Поздравляем!</b>\n\n"
                    f"Ты получил статус верифицированного пользователя!\n"
                    f"• Посты без модерации\n"
                    f"• Рефералов: до 25\n"
                    f"• Длина поста: 300 символов\n\n"
                    f"Твой рейтинг поднят до 10%",
                    parse_mode="HTML"
                )
            except:
                pass
        else:
            bot.send_message(user_id, "⚠️ Уже верифицирован")
    except:
        bot.send_message(user_id, "❌ Ошибка")

@bot.message_handler(commands=['removeverified'])
def remove_verified(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "🚫 Не админ")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(user_id, "❌ Использование: /removeverified ID")
        return
    
    try:
        rem_id = int(args[1])
        rem_id_str = str(rem_id)
        
        if rem_id_str in data.get("verified_users", []):
            data["verified_users"].remove(rem_id_str)
            save_data(data)
            bot.send_message(
                user_id,
                f"✅ Верификация снята с {rem_id}"
            )
            try:
                bot.send_message(
                    rem_id,
                    f"❌ Твой статус верифицированного пользователя был снят."
                )
            except:
                pass
        else:
            bot.send_message(user_id, "⚠️ Не верифицирован")
    except:
        bot.send_message(user_id, "❌ Ошибка")

@bot.message_handler(commands=['ban'])
def ban_user(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "🚫 Не админ")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(user_id, "❌ Использование: /ban ID")
        return
    
    try:
        ban_id = int(args[1])
        ban_id_str = str(ban_id)
        
        if ban_id_str not in data["banned_users"]:
            data["banned_users"].append(ban_id_str)
            save_data(data)
            bot.send_message(
                user_id,
                f"🚫 Пользователь {ban_id} забанен"
            )
            try:
                bot.send_message(
                    ban_id,
                    f"🚫 Вы были забанены администратором."
                )
            except:
                pass
        else:
            bot.send_message(user_id, "⚠️ Уже в бане")
    except:
        bot.send_message(user_id, "❌ Ошибка")

@bot.message_handler(commands=['unban'])
def unban_user(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "🚫 Не админ")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(user_id, "❌ Использование: /unban ID")
        return
    
    try:
        unban_id = int(args[1])
        unban_id_str = str(unban_id)
        
        if unban_id_str in data["banned_users"]:
            data["banned_users"].remove(unban_id_str)
            save_data(data)
            bot.send_message(
                user_id,
                f"✅ Пользователь {unban_id} разбанен"
            )
            try:
                bot.send_message(
                    unban_id,
                    f"✅ Вы были разбанены администратором."
                )
            except:
                pass
        else:
            bot.send_message(user_id, "⚠️ Не в бане")
    except:
        bot.send_message(user_id, "❌ Ошибка")

@bot.message_handler(commands=['delpost'])
def delete_post(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "🚫 Не админ")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(user_id, "❌ Использование: /delpost ID_поста")
        return
    
    post_id = args[1]
    deleted = delete_post_globally(post_id)
    
    if deleted:
        bot.send_message(
            user_id,
            f"✅ Пост удалён у {deleted} пользователей"
        )
    else:
        bot.send_message(
            user_id,
            f"❌ Пост не найден или уже удалён"
        )

# ========== ОБРАБОТЧИКИ КОЛЛБЭКОВ ==========

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    user_id_str = str(user_id)
    
    if is_banned(user_id) and not call.data.startswith("unban_"):
        bot.answer_callback_query(call.id, "Вы забанены", show_alert=True)
        return
    
    user = get_user(user_id)
    if not user and not is_banned(user_id):
        return
    
    data_cmd = call.data
    
    # ===== РЕАКЦИИ НА ПОСТЫ =====
    if data_cmd.startswith("like_"):
        post_id = data_cmd.split("_")[1]
        
        if str(post_id) not in data["post_reactions"]:
            data["post_reactions"][str(post_id)] = {"likes": [], "dislikes": [], "complaints": []}
        
        reactions = data["post_reactions"][str(post_id)]
        post_info = data["post_contents"].get(str(post_id), {})
        author_id = post_info.get("author_id")
        
        if user_id_str in reactions["likes"]:
            reactions["likes"].remove(user_id_str)
            bot.answer_callback_query(call.id, "👍 Лайк убран")
        else:
            if user_id_str in reactions["dislikes"]:
                reactions["dislikes"].remove(user_id_str)
            reactions["likes"].append(user_id_str)
            bot.answer_callback_query(call.id, "👍 Лайк поставлен")
            
            if author_id and author_id != user_id_str:
                author = get_user(author_id)
                if author:
                    author["rating"] = min(95.0, author["rating"] + 0.05)
                    author["weekly_activity"] += 2
                    author["weekly_likes"] += 1
                    
                    if "post_history_data" in author and str(post_id) in author["post_history_data"]:
                        author["post_history_data"][str(post_id)]["likes"] += 1
                    
                    update_quest_progress(author_id, "likes_recv", 1)
            
            update_quest_progress(user_id, "likes_give", 1)
        
        save_data(data)
        update_post_reactions_buttons(post_id, call.message.chat.id, call.message.message_id)
        return
    
    elif data_cmd.startswith("dislike_"):
        post_id = data_cmd.split("_")[1]
        
        if str(post_id) not in data["post_reactions"]:
            data["post_reactions"][str(post_id)] = {"likes": [], "dislikes": [], "complaints": []}
        
        reactions = data["post_reactions"][str(post_id)]
        post_info = data["post_contents"].get(str(post_id), {})
        author_id = post_info.get("author_id")
        
        if user_id_str in reactions["dislikes"]:
            reactions["dislikes"].remove(user_id_str)
            bot.answer_callback_query(call.id, "👎 Дизлайк убран")
        else:
            if user_id_str in reactions["likes"]:
                reactions["likes"].remove(user_id_str)
            reactions["dislikes"].append(user_id_str)
            bot.answer_callback_query(call.id, "👎 Дизлайк поставлен")
            
            if author_id and author_id != user_id_str:
                author = get_user(author_id)
                if author:
                    author["rating"] = max(5.0, author["rating"] - 0.03)
                    if is_vip(author_id) or is_verified(author_id):
                        author["rating"] = max(10.0, author["rating"])
                    
                    if "post_history_data" in author and str(post_id) in author["post_history_data"]:
                        author["post_history_data"][str(post_id)]["dislikes"] += 1
        
        save_data(data)
        update_post_reactions_buttons(post_id, call.message.chat.id, call.message.message_id)
        return
    
    elif data_cmd.startswith("complaint_"):
        post_id = data_cmd.split("_")[1]
        post_info = data["post_contents"].get(str(post_id), {})
        post_text = post_info.get("text", "Текст не найден")
        author_name = post_info.get("author_name", "Неизвестно")
        author_id = post_info.get("author_id", "Неизвестно")
        
        if str(post_id) not in data["post_reactions"]:
            data["post_reactions"][str(post_id)] = {"likes": [], "dislikes": [], "complaints": []}
        
        reactions = data["post_reactions"][str(post_id)]
        
        if user_id_str not in reactions["complaints"]:
            reactions["complaints"].append(user_id_str)
            bot.answer_callback_query(call.id, "⚠️ Жалоба отправлена администраторам")
            
            for admin_id in data.get("admins", []):
                if admin_id != user_id_str:
                    try:
                        text = f"""
⚠️ <b>ЖАЛОБА НА ПОСТ</b>

<b>ID поста:</b> {post_id}
<b>Автор:</b> {author_name} (ID: {author_id})
<b>От:</b> {get_user_display_name(user_id)} (ID: {user_id})

<b>Текст поста:</b>
{post_text}

<b>Действия:</b>
/delpost {post_id} - удалить пост у всех
/ban {author_id} - забанить автора
                        """
                        bot.send_message(int(admin_id), text, parse_mode="HTML")
                    except:
                        pass
        else:
            bot.answer_callback_query(call.id, "Вы уже жаловались на этот пост")
        
        save_data(data)
        return
    
    elif data_cmd.startswith("global_delete_"):
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "Не админ")
            return
        
        post_id = data_cmd.split("_")[2]
        deleted = delete_post_globally(post_id)
        bot.answer_callback_query(call.id, f"🗑 Пост удалён у {deleted} пользователей")
        return
    
    # ===== АДМИНКА =====
    if data_cmd.startswith("admin_") or data_cmd in [
        "admin_main", "admin_posts_list", "approve_", "reject_", "ban_user_",
        "interpol_", "admin_vip_list", "admin_verified_list", "admin_admins_list",
        "admin_bans_list", "admin_stats", "admin_activity"
    ]:
        pass
    else:
        try:
            bot.delete_message(user_id, call.message.message_id)
        except:
            pass
    
    if data_cmd == "admin_main":
        if not is_admin(user_id):
            return
        bot.edit_message_text(
            "👑 <b>АДМИН-ПАНЕЛЬ</b>\n\nВыбери раздел:",
            user_id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=admin_main_keyboard()
        )
    
    elif data_cmd == "admin_posts_list":
        if not is_admin(user_id):
            return
        
        if not data["posts"]:
            bot.edit_message_text(
                "📭 Нет постов на модерации",
                user_id,
                call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("◀️ Назад", callback_data="admin_main")
                )
            )
            return
        
        bot.edit_message_text(
            f"📝 <b>Посты на модерации ({len(data['posts'])}):</b>",
            user_id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=admin_posts_list_keyboard(data["posts"])
        )
    
    elif data_cmd.startswith("admin_post_"):
        if not is_admin(user_id):
            return
        
        post_id = data_cmd.split("_")[2]
        for post in data["posts"]:
            if str(post["id"]) == post_id:
                author = get_user_display_name(post["user_id"])
                text = f"📝 <b>Пост от {author}</b>\n\n{post['text']}"
                bot.edit_message_text(
                    text,
                    user_id,
                    call.message.message_id,
                    parse_mode="HTML",
                    reply_markup=admin_post_actions_keyboard(post_id)
                )
                break
    
    elif data_cmd.startswith("approve_"):
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "Не админ")
            return
        
        post_id = data_cmd.split("_")[1]
        idx = -1
        post_data = None
        
        for i, p in enumerate(data["posts"]):
            if str(p["id"]) == post_id:
                idx = i
                post_data = p
                break
        
        if idx == -1:
            bot.answer_callback_query(call.id, "Пост не найден")
            return
        
        sent = send_post_to_users(post_data, user_id)
        data["posts"].pop(idx)
        save_data(data)
        
        admin = get_user(user_id)
        if admin and admin.get("admin_notifications", True):
            bot.send_message(
                user_id,
                f"✅ <b>Пост одобрен</b>\n\n"
                f"📊 Доставлено: {sent} пользователям\n"
                f"🎯 Гарантированно: {max(1, int((sent or 0) * 0.01))}\n"
                f"🎲 По шансу: остальные\n\n"
                f"👍 Отличная работа!",
                parse_mode="HTML"
            )
        
        try:
            bot.send_message(
                int(post_data["user_id"]),
                f"✅ <b>Твой пост одобрен и разослан!</b>\n\n"
                f"📊 Доставлен {sent} пользователям.\n"
                f"🔥 Твой рейтинг вырос!",
                parse_mode="HTML"
            )
        except:
            pass
        
        if data["posts"]:
            next_post = data["posts"][0]
            author = get_user_display_name(next_post["user_id"])
            text = f"✅ Пост одобрен. Доставлено: {sent}\n\n📝 <b>Следующий пост от {author}</b>\n\n{next_post['text']}"
            bot.edit_message_text(
                text,
                user_id,
                call.message.message_id,
                parse_mode="HTML",
                reply_markup=admin_post_actions_keyboard(next_post['id'])
            )
        else:
            bot.edit_message_text(
                f"✅ Пост одобрен. Доставлено: {sent}\n\n📭 Больше нет постов на модерации.",
                user_id,
                call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("◀️ В админ-панель", callback_data="admin_main")
                )
            )
        
        bot.answer_callback_query(call.id, "✅ Пост одобрен")
    
    elif data_cmd.startswith("reject_"):
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "Не админ")
            return
        
        post_id = data_cmd.split("_")[1]
        idx = -1
        post_data = None
        
        for i, p in enumerate(data["posts"]):
            if str(p["id"]) == post_id:
                idx = i
                post_data = p
                break
        
        if idx == -1:
            bot.answer_callback_query(call.id, "Пост не найден")
            return
        
        bot.send_message(
            user_id,
            "📝 Напиши причину отказа (или отправь '-' чтобы пропустить):"
        )
        bot.register_next_step_handler_by_chat_id(
            user_id,
            receive_reject_reason,
            post_data,
            idx
        )
    
    elif data_cmd.startswith("ban_user_"):
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "Не админ")
            return
        
        post_id = data_cmd.split("_")[2]
        for post in data["posts"]:
            if str(post["id"]) == post_id:
                banned = post["user_id"]
                if banned not in data["banned_users"]:
                    data["banned_users"].append(banned)
                    save_data(data)
                    bot.send_message(
                        user_id,
                        f"🚫 Пользователь {banned} ({get_user_display_name(banned)}) забанен"
                    )
                    try:
                        bot.send_message(
                            int(banned),
                            f"🚫 Вы были забанены администратором."
                        )
                    except:
                        pass
                break
    
    elif data_cmd.startswith("interpol_"):
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "Не админ")
            return
        
        post_id = data_cmd.split("_")[1]
        for i, p in enumerate(data["posts"]):
            if str(p["id"]) == post_id:
                sent = send_post_to_users(p, user_id, force_all=True)
                data["posts"].pop(i)
                save_data(data)
                bot.edit_message_text(
                    f"📢 <b>Интерпол-рассылка выполнена</b>\n\n"
                    f"✅ Доставлено: {sent} пользователям",
                    user_id,
                    call.message.message_id,
                    parse_mode="HTML"
                )
                break
    
    elif data_cmd == "admin_interpol":
        if not is_admin(user_id):
            return
        
        bot.edit_message_text(
            "📢 <b>Интерпол-рассылка</b>\n\n"
            "Отправь текст поста для рассылки <b>ВСЕМ</b> пользователям:",
            user_id,
            call.message.message_id,
            parse_mode="HTML"
        )
        bot.register_next_step_handler_by_chat_id(user_id, receive_interpol_post)
    
    elif data_cmd == "admin_vip_list":
        if not is_admin(user_id):
            return
        
        vip_list = []
        for uid, u in data["users"].items():
            if is_vip(uid) and uid not in vip_list:
                vip_list.append(uid)
        for uid in data.get("vip_users", []):
            if uid not in vip_list:
                vip_list.append(uid)
        
        if not vip_list:
            bot.edit_message_text(
                "👑 Нет VIP пользователей",
                user_id,
                call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("◀️ Назад", callback_data="admin_main")
                )
            )
            return
        
        bot.edit_message_text(
            f"👑 <b>VIP пользователи ({len(vip_list)}):</b>",
            user_id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=admin_users_list_keyboard(vip_list, "admin_vip", "admin_main")
        )
    
    elif data_cmd.startswith("admin_vip_"):
        if not is_admin(user_id):
            return
        
        target = data_cmd.split("_")[2]
        name = get_user_display_name(target)
        text = f"👑 <b>VIP пользователь</b>\n\nID: {target}\nИмя: {name}"
        bot.edit_message_text(
            text,
            user_id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=admin_user_actions_keyboard(target, "vip")
        )
    
    elif data_cmd == "admin_verified_list":
        if not is_admin(user_id):
            return
        
        ver_list = data.get("verified_users", [])
        if not ver_list:
            bot.edit_message_text(
                "✅ Нет верифицированных пользователей",
                user_id,
                call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("◀️ Назад", callback_data="admin_main")
                )
            )
            return
        
        bot.edit_message_text(
            f"✅ <b>Верифицированные пользователи ({len(ver_list)}):</b>",
            user_id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=admin_users_list_keyboard(ver_list, "admin_verified", "admin_main")
        )
    
    elif data_cmd.startswith("admin_verified_"):
        if not is_admin(user_id):
            return
        
        target = data_cmd.split("_")[2]
        name = get_user_display_name(target)
        text = f"✅ <b>Верифицированный пользователь</b>\n\nID: {target}\nИмя: {name}"
        bot.edit_message_text(
            text,
            user_id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=admin_user_actions_keyboard(target, "verified")
        )
    
    elif data_cmd == "admin_admins_list":
        if not is_admin(user_id):
            return
        
        adm_list = data.get("admins", [])
        bot.edit_message_text(
            f"👥 <b>Администраторы ({len(adm_list)}):</b>",
            user_id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=admin_users_list_keyboard(adm_list, "admin_admin", "admin_main")
        )
    
    elif data_cmd.startswith("admin_admin_"):
        if not is_admin(user_id):
            return
        
        target = data_cmd.split("_")[2]
        name = get_user_display_name(target)
        text = f"👥 <b>Администратор</b>\n\nID: {target}\nИмя: {name}"
        bot.edit_message_text(
            text,
            user_id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=admin_user_actions_keyboard(target, "admin")
        )
    
    elif data_cmd == "admin_bans_list":
        if not is_admin(user_id):
            return
        
        ban_list = data.get("banned_users", [])
        if not ban_list:
            bot.edit_message_text(
                "🚫 Нет забаненных пользователей",
                user_id,
                call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("◀️ Назад", callback_data="admin_main")
                )
            )
            return
        
        bot.edit_message_text(
            f"🚫 <b>Забаненные пользователи ({len(ban_list)}):</b>",
            user_id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=admin_users_list_keyboard(ban_list, "admin_banned", "admin_main")
        )
    
    elif data_cmd.startswith("admin_banned_"):
        if not is_admin(user_id):
            return
        
        target = data_cmd.split("_")[2]
        name = get_user_display_name(target)
        text = f"🚫 <b>Забаненный пользователь</b>\n\nID: {target}\nИмя: {name}"
        bot.edit_message_text(
            text,
            user_id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=admin_user_actions_keyboard(target, "banned")
        )
    
    elif data_cmd == "admin_stats":
        if not is_admin(user_id):
            return
        
        total_users = len(data["users"])
        total_banned = len(data["banned_users"])
        total_admins = len(data.get("admins", []))
        
        vip_cnt = 0
        for uid, u in data["users"].items():
            if is_vip(uid):
                vip_cnt += 1
        vip_cnt += len(data.get("vip_users", []))
        
        ver_cnt = len(data.get("verified_users", []))
        total_posts = data["stats"]["total_posts_sent"]
        total_games = data["stats"]["total_attempts"]
        total_wins = data["stats"]["total_wins"]
        
        text = f"""
📊 <b>СТАТИСТИКА БОТА</b>

👥 Всего пользователей: {total_users}
🚫 Забанено: {total_banned}
👑 VIP: {vip_cnt}
✅ Верифицировано: {ver_cnt}
👥 Админов: {total_admins}

📝 Всего постов: {total_posts}
🎰 Всего игр: {total_games}
🏆 Всего побед: {total_wins}
        """
        bot.edit_message_text(
            text,
            user_id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("◀️ Назад", callback_data="admin_main")
            )
        )
    
    elif data_cmd == "admin_activity":
        if not is_admin(user_id):
            return
        
        top = get_weekly_activity_top(10)
        text = "📈 <b>АКТИВНОСТЬ ЗА НЕДЕЛЮ</b>\n\n"
        if not top:
            text += "Пока нет данных"
        else:
            for i, u in enumerate(top, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
                text += f"{medal} {i}. {u['name']} — {u['activity']} очков\n"
            text += "\n🏆 В пятницу в 12:00 победитель получает 15 ⭐"
        
        bot.edit_message_text(
            text,
            user_id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("◀️ Назад", callback_data="admin_main")
            )
        )
    
    elif data_cmd.startswith("remove_vip_"):
        if not is_admin(user_id):
            return
        
        target = data_cmd.split("_")[2]
        user = get_user(target)
        removed = False
        
        if user and user.get("vip_until"):
            user["vip_until"] = None
            removed = True
        
        if target in data.get("vip_users", []):
            data["vip_users"].remove(target)
            removed = True
        
        if removed:
            save_data(data)
            bot.answer_callback_query(call.id, "VIP статус удалён")
            try:
                bot.send_message(
                    int(target),
                    f"❌ Твой VIP статус был удалён администратором."
                )
            except:
                pass
        
        vip_list = []
        for uid, u in data["users"].items():
            if is_vip(uid):
                vip_list.append(uid)
        for uid in data.get("vip_users", []):
            if uid not in vip_list:
                vip_list.append(uid)
        
        if vip_list:
            bot.edit_message_text(
                f"👑 <b>VIP пользователи ({len(vip_list)}):</b>",
                user_id,
                call.message.message_id,
                parse_mode="HTML",
                reply_markup=admin_users_list_keyboard(vip_list, "admin_vip", "admin_main")
            )
        else:
            bot.edit_message_text(
                "👑 Нет VIP пользователей",
                user_id,
                call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("◀️ Назад", callback_data="admin_main")
                )
            )
    
    elif data_cmd.startswith("remove_verified_"):
        if not is_admin(user_id):
            return
        
        target = data_cmd.split("_")[2]
        
        if target in data.get("verified_users", []):
            data["verified_users"].remove(target)
            save_data(data)
            bot.answer_callback_query(call.id, "Верификация снята")
            try:
                bot.send_message(
                    int(target),
                    f"❌ Твой статус верифицированного пользователя был снят."
                )
            except:
                pass
        
        ver_list = data.get("verified_users", [])
        if ver_list:
            bot.edit_message_text(
                f"✅ <b>Верифицированные пользователи ({len(ver_list)}):</b>",
                user_id,
                call.message.message_id,
                parse_mode="HTML",
                reply_markup=admin_users_list_keyboard(ver_list, "admin_verified", "admin_main")
            )
        else:
            bot.edit_message_text(
                "✅ Нет верифицированных пользователей",
                user_id,
                call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("◀️ Назад", callback_data="admin_main")
                )
            )
    
    elif data_cmd.startswith("remove_admin_"):
        if not is_admin(user_id):
            return
        
        target = data_cmd.split("_")[2]
        
        if target in data.get("admins", []) and target not in [str(a) for a in MASTER_ADMINS]:
            data["admins"].remove(target)
            save_data(data)
            bot.answer_callback_query(call.id, "Админ удалён")
            try:
                bot.send_message(
                    int(target),
                    f"❌ Твой статус администратора был удалён."
                )
            except:
                pass
        
        adm_list = data.get("admins", [])
        bot.edit_message_text(
            f"👥 <b>Администраторы ({len(adm_list)}):</b>",
            user_id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=admin_users_list_keyboard(adm_list, "admin_admin", "admin_main")
        )
    
    elif data_cmd.startswith("unban_"):
        if not is_admin(user_id):
            return
        
        target = data_cmd.split("_")[1]
        
        if target in data.get("banned_users", []):
            data["banned_users"].remove(target)
            save_data(data)
            bot.answer_callback_query(call.id, "Пользователь разбанен")
            try:
                bot.send_message(
                    int(target),
                    f"✅ Вы были разбанены администратором."
                )
            except:
                pass
        
        ban_list = data.get("banned_users", [])
        if ban_list:
            bot.edit_message_text(
                f"🚫 <b>Забаненные пользователи ({len(ban_list)}):</b>",
                user_id,
                call.message.message_id,
                parse_mode="HTML",
                reply_markup=admin_users_list_keyboard(ban_list, "admin_banned", "admin_main")
            )
        else:
            bot.edit_message_text(
                "🚫 Нет забаненных пользователей",
                user_id,
                call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("◀️ Назад", callback_data="admin_main")
                )
            )
    
    # ===== ОБЫЧНОЕ МЕНЮ =====
    elif data_cmd == "main_menu":
        bot.send_message(
            user_id,
            "🎩 <b>Главное меню</b>\n\nВыбери действие:",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )
    
    elif data_cmd == "casino":
        can_play, cd = check_casino_cooldown(user)
        text = f"🎰 <b>КАЗИНО LOWHIGH</b>\n\n"
        text += f"🍀 Твой шанс: {user['luck']:.2f}%\n"
        if user.get("quest_bonus_ready"):
            text += f"🔥 Бонус +20% готов!\n"
        text += f"\n"
        if can_play:
            text += f"✅ Можно играть! Нажми кнопку ниже."
        else:
            text += f"⏳ Следующая попытка через: {format_time(cd)}"
        bot.send_message(
            user_id,
            text,
            parse_mode="HTML",
            reply_markup=casino_keyboard()
        )
    
    elif data_cmd == "casino_spin":
        can_play, cd = check_casino_cooldown(user)
        if not can_play:
            bot.answer_callback_query(call.id, f"Жди ещё {format_time(cd)}")
            return
        
        old_rating = user["rating"]
        user["rating"] = max(5.0, user["rating"] - 1.0)
        if is_vip(user_id) or is_verified(user_id):
            user["rating"] = max(10.0, user["rating"])
        
        bonus = 20 if user.get("quest_bonus_ready") else 0
        if bonus:
            user["quest_bonus_ready"] = False
        
        roll = random.uniform(0, 100)
        won = roll <= (user["luck"] + bonus)
        
        if won:
            items = ["amulet", "silencer", "vip_pass"]
            item = random.choice(items)
            inv = user.get("inventory", {})
            
            if inv.get(item, 0) == 0:
                inv[item] = 1
                user["inventory"] = inv
                result = f"🎉 <b>ПОБЕДА!</b>\n\n"
                result += f"Ты выиграл: <b>{item}</b>!"
                if item == "amulet":
                    result += "\n🍀 Используй в инвентаре для +10% рейтинга"
                elif item == "silencer":
                    result += "\n🔇 Глушитель отключит рекламу на 8 часов"
                else:
                    result += "\n👑 VIP-пропуск даст 3 дня VIP"
            else:
                user["rating"] = min(95.0, user["rating"] + 5.0)
                result = f"🎉 <b>ПОБЕДА!</b>\n\n"
                result += f"+5% к рейтингу (предмет уже есть в инвентаре)"
            
            user["total_wins"] += 1
            user["fail_counter"] = 0
            data["stats"]["total_wins"] += 1
            update_quest_progress(user_id, "casino_win", 1)
        else:
            user["fail_counter"] += 1
            inc = user["fail_counter"] * 0.01
            user["luck"] = min(50.0, user["luck"] + inc)
            result = f"😢 <b>ПРОИГРЫШ</b>\n\n"
            result += f"Удача +{inc:.2f}% → {user['luck']:.2f}%\n"
            result += f"Рейтинг: {old_rating:.1f}% → {user['rating']:.1f}%\n"
            result += f"🍀 В следующий раз повезёт!"
        
        user["last_casino"] = datetime.now().isoformat()
        user["total_casino_attempts"] += 1
        user["weekly_activity"] += 1
        data["stats"]["total_attempts"] += 1
        update_quest_progress(user_id, "casino", 1)
        save_data(data)
        
        bot.edit_message_text(
            result,
            user_id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("🎰 Ещё раз", callback_data="casino"),
                InlineKeyboardButton("🏠 В меню", callback_data="main_menu")
            )
        )
    
    elif data_cmd == "write_post":
        can_post, cd = check_post_cooldown(user)
        if not can_post:
            bot.answer_callback_query(call.id, f"Жди ещё {format_time(cd)}")
            return
        
        pred = user["rating"] / 2 + user["luck"] / 10
        pred = max(5, min(95, pred))
        max_len = get_max_post_length(user_id)
        
        bot.send_message(
            user_id,
            f"📊 <b>Прогноз доставки:</b> {pred:.1f}%\n\n"
            f"📝 Отправь текст поста (максимум {max_len} символов):\n"
            f"✨ Постарайся написать что-то интересное!",
            parse_mode="HTML",
            reply_markup=cancel_keyboard()
        )
        bot.register_next_step_handler_by_chat_id(user_id, receive_post)
    
    elif data_cmd == "cancel_post":
        bot.clear_step_handler_by_chat_id(user_id)
        bot.send_message(
            user_id,
            "❌ Отправка отменена",
            reply_markup=main_keyboard()
        )
    
    elif data_cmd == "referrals":
        try:
            bot_username = bot.get_me().username
            link = f"https://t.me/{bot_username}?start={user_id}"
        except:
            link = "Ошибка получения ссылки"
        
        cnt = len(user.get("referrals", []))
        max_ref = get_max_referrals(user_id)
        
        text = f"""
👥 <b>РЕФЕРАЛЬНАЯ СИСТЕМА</b>

Ты пригласил: {cnt}/{max_ref} друзей
Каждый друг даёт +1% к удаче навсегда

🔗 Твоя ссылка:
<code>{link}</code>

Отправь её друзьям и получай бонусы!
        """
        bot.send_message(
            user_id,
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
            )
        )
    
    elif data_cmd == "stats":
        total_likes = 0
        total_dislikes = 0
        for pid, r in data["post_reactions"].items():
            total_likes += len(r.get("likes", []))
            total_dislikes += len(r.get("dislikes", []))
        
        ref_bonus = 0
        if user.get("referrals"):
            total_ref = 0
            for rid in user["referrals"]:
                ru = get_user(rid)
                if ru:
                    total_ref += ru.get("rating", 0)
            ref_bonus = total_ref / 100
        
        text = f"""
📊 <b>ТВОЯ СТАТИСТИКА</b>

📈 Рейтинг: {user['rating']:.1f}%
🍀 Удача: {user['luck']:.2f}%
📻 Приём: {user['incoming_chance']}%
💰 Бонус от рефералов: +{ref_bonus:.2f}%
⏱ КД на пост: {get_post_cooldown(user_id)}ч

📝 Постов написано: {user['total_posts']}
🎰 Игр сыграно: {user['total_casino_attempts']}
🏆 Побед в казино: {user['total_wins']}
👥 Рефералов: {len(user.get('referrals', []))}/{get_max_referrals(user_id)}

🌍 <b>Глобальная статистика:</b>
👍 Всего лайков: {total_likes}
👎 Всего дизлайков: {total_dislikes}
📨 Всего постов: {data['stats']['total_posts_sent']}
        """
        bot.send_message(
            user_id,
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
            )
        )
    
    elif data_cmd == "top":
        top = get_top_users()
        text = "🏆 <b>ТОП-10 ПО РЕЙТИНГУ</b>\n\n"
        if not top:
            text += "Пока нет участников"
        else:
            for i, u in enumerate(top, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
                text += f"{medal} <b>{i}.</b> {u['name']}\n"
                text += f"   📈 {u['rating']:.1f}% | 🍀 {u['luck']:.1f}% | 📝 {u['posts']}\n"
        bot.send_message(
            user_id,
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
            )
        )
    
    elif data_cmd == "convert":
        if user.get("last_convert"):
            last = datetime.fromisoformat(user["last_convert"])
            if datetime.now().date() == last.date():
                bot.answer_callback_query(call.id, "❌ Уже сегодня!")
                return
        if user["rating"] < 5.1:
            bot.answer_callback_query(call.id, "❌ Мало рейтинга (мин 5.1%)")
            return
        
        old_rating = user["rating"]
        old_luck = user["luck"]
        
        user["rating"] -= 5.0
        user["luck"] = min(50.0, user["luck"] + 1.0)
        user["last_convert"] = datetime.now().isoformat()
        save_data(data)
        
        bot.answer_callback_query(call.id, "✅ Конвертация выполнена!")
        bot.send_message(
            user_id,
            f"✅ <b>Конвертация выполнена!</b>\n\n"
            f"📈 Рейтинг: {old_rating:.1f}% → {user['rating']:.1f}%\n"
            f"🍀 Удача: {old_luck:.1f}% → {user['luck']:.1f}%",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )
    
    elif data_cmd == "inventory":
        inv = user.get("inventory", {})
        sil = ""
        if user.get("silencer_until"):
            try:
                until = datetime.fromisoformat(user["silencer_until"])
                if until > datetime.now():
                    sil = f" (активен до {until.strftime('%H:%M')})"
                else:
                    user["silencer_until"] = None
                    save_data(data)
            except:
                user["silencer_until"] = None
        
        text = f"""
🎒 <b>ТВОЙ ИНВЕНТАРЬ</b>

🍀 Амулет удачи: {inv.get('amulet', 0)}
🔇 Глушитель: {inv.get('silencer', 0)}{sil}
👑 VIP-пропуск: {inv.get('vip_pass', 0)}

Максимум 1 предмет каждого типа.
        """
        bot.send_message(
            user_id,
            text,
            parse_mode="HTML",
            reply_markup=inventory_keyboard(user)
        )
    
    elif data_cmd == "use_amulet":
        inv = user.get("inventory", {})
        if inv.get("amulet", 0) == 1:
            user["rating"] = min(95.0, user["rating"] + 10.0)
            inv["amulet"] = 0
            user["inventory"] = inv
            save_data(data)
            bot.answer_callback_query(call.id, "🍀 +10% рейтинга!")
            bot.send_message(
                user_id,
                f"🍀 <b>Амулет использован!</b>\n\n"
                f"📈 Рейтинг увеличен на 10%!\n"
                f"Текущий рейтинг: {user['rating']:.1f}%",
                parse_mode="HTML",
                reply_markup=main_keyboard()
            )
        else:
            bot.answer_callback_query(call.id, "У тебя нет амулета")
    
    elif data_cmd == "activate_silencer":
        inv = user.get("inventory", {})
        if inv.get("silencer", 0) == 1 and not user.get("silencer_until"):
            until = datetime.now() + timedelta(hours=8)
            user["silencer_until"] = until.isoformat()
            inv["silencer"] = 0
            user["inventory"] = inv
            save_data(data)
            bot.answer_callback_query(call.id, "🔇 Глушитель активирован")
            bot.send_message(
                user_id,
                f"🔇 <b>Глушитель активирован</b>\n\n"
                f"Ты не будешь получать чужие посты до {until.strftime('%H:%M')}.",
                parse_mode="HTML",
                reply_markup=main_keyboard()
            )
        else:
            bot.answer_callback_query(call.id, "Нельзя активировать")
    
    elif data_cmd == "deactivate_silencer":
        if user.get("silencer_until"):
            user["silencer_until"] = None
            save_data(data)
            bot.answer_callback_query(call.id, "🔇 Глушитель выключен")
            bot.send_message(
                user_id,
                "🔇 <b>Глушитель деактивирован</b>\n\n"
                "Теперь ты снова получаешь посты.",
                parse_mode="HTML",
                reply_markup=main_keyboard()
            )
        else:
            bot.answer_callback_query(call.id, "Глушитель не активен")
    
    elif data_cmd == "use_vippass":
        inv = user.get("inventory", {})
        if inv.get("vip_pass", 0) == 1:
            until = datetime.now() + timedelta(days=3)
            user["vip_until"] = until.isoformat()
            inv["vip_pass"] = 0
            user["inventory"] = inv
            check_and_fix_rating(user_id)
            save_data(data)
            bot.answer_callback_query(call.id, "👑 VIP на 3 дня!")
            bot.send_message(
                user_id,
                f"👑 <b>VIP-пропуск использован!</b>\n\n"
                f"Ты получил VIP статус до {until.strftime('%d.%m.%Y %H:%M')}\n"
                f"📈 Рейтинг поднят до 10%\n"
                f"• КД на пост: 2 часа\n"
                f"• Рефералов: до 50\n"
                f"• Длина поста: 500 символов",
                parse_mode="HTML",
                reply_markup=main_keyboard()
            )
        else:
            bot.answer_callback_query(call.id, "У тебя нет VIP-пропуска")
    
    elif data_cmd == "quests":
        generate_daily_quests(user_id)
        qd = user.get("quests", {})
        if not qd:
            bot.send_message(user_id, "❌ Ошибка загрузки квестов")
            return
        
        text = "📋 <b>КВЕСТЫ НА СЕГОДНЯ</b>\n\n"
        for i, t in enumerate(qd.get("tasks", [])):
            status = "✅" if qd["completed"][i] else "☐"
            prog = f"{qd['progress'][i]}/{t['target']}" if not qd["completed"][i] else ""
            text += f"{status} {t['desc']} {prog} — {t['reward']}\n"
        
        bonus = "🏆 <b>Бонус за все:</b> +20% к следующей крутке "
        bonus += "✅" if user.get("quest_bonus_ready") else "❌"
        text += f"\n{bonus}"
        
        bot.send_message(
            user_id,
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
            )
        )
    
    elif data_cmd == "post_history":
        if not user.get("my_posts"):
            bot.send_message(
                user_id,
                "📋 <b>ИСТОРИЯ ПОСТОВ</b>\n\nУ тебя пока нет постов.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
                )
            )
            return
        
        bot.send_message(
            user_id,
            "📋 <b>ИСТОРИЯ ПОСТОВ</b>\n\nВыбери пост:",
            parse_mode="HTML",
            reply_markup=post_history_keyboard(user)
        )
    
    elif data_cmd.startswith("history_post_"):
        post_id = data_cmd.split("_")[2]
        post_data = user.get("post_history_data", {}).get(str(post_id), {})
        
        if not post_data:
            bot.answer_callback_query(call.id, "Пост не найден")
            return
        
        text = f"""
📝 <b>Пост от {post_data.get('date', '?')[:10]}</b>

{post_data['text']}

👍 <b>Лайков:</b> {post_data.get('likes', 0)}
👎 <b>Дизлайков:</b> {post_data.get('dislikes', 0)}
        """
        bot.send_message(
            user_id,
            text,
            parse_mode="HTML",
            reply_markup=history_post_actions_keyboard(post_id)
        )
    
    elif data_cmd.startswith("retry_post_"):
        post_id = data_cmd.split("_")[2]
        post_data = user.get("post_history_data", {}).get(str(post_id), {})
        
        if not post_data:
            bot.answer_callback_query(call.id, "Пост не найден")
            return
        
        can_post, cd = check_post_cooldown(user)
        if not can_post:
            bot.answer_callback_query(call.id, f"Жди ещё {format_time(cd)}")
            return
        
        new_post = {
            "id": int(time.time() * 1000),
            "user_id": str(user_id),
            "username": user.get("username"),
            "text": post_data["text"],
            "time": datetime.now().isoformat()
        }
        
        user["last_post_time"] = datetime.now().isoformat()
        user["posts_count"] = user.get("posts_count", 0) + 1
        
        sent = send_post_to_users(new_post, user_id)
        user["total_posts"] += 1
        save_data(data)
        
        bot.send_message(
            user_id,
            f"✅ <b>Пост повторно разослан!</b>\n\n"
            f"📊 Доставлено: {sent} пользователям\n"
            f"🎯 Гарантированно: {max(1, int((sent or 0) * 0.01))}\n"
            f"🎲 По шансу: остальные",
            parse_mode="HTML"
        )
        bot.answer_callback_query(call.id, "✅ Пост отправлен")
    
    elif data_cmd.startswith("history_delete_"):
        post_id = data_cmd.split("_")[2]
        deleted = delete_post_globally(post_id)
        
        if deleted:
            bot.answer_callback_query(call.id, f"🗑 Удалено у {deleted}")
            bot.send_message(
                user_id,
                f"🗑 <b>Пост удалён</b>\n\n"
                f"Удалено у {deleted} пользователей.",
                parse_mode="HTML"
            )
        else:
            bot.answer_callback_query(call.id, "❌ Пост не найден")
    
    elif data_cmd == "hotline":
        can, cd = check_hotline_cooldown(user)
        if not can:
            bot.answer_callback_query(call.id, f"⏳ Подожди {format_time(cd)}")
            return
        
        bot.send_message(
            user_id,
            "📞 <b>ГОРЯЧАЯ ЛИНИЯ</b>\n\n"
            "Напиши сообщение для администраторов.\n"
            "Они ответят тебе в личку как только смогут.\n\n"
            "⚠️ Используй эту функцию только по делу!",
            parse_mode="HTML",
            reply_markup=cancel_keyboard()
        )
        bot.register_next_step_handler_by_chat_id(user_id, receive_hotline_message)
    
    elif data_cmd == "shop":
        text = f"""
⭐ <b>МАГАЗИН LOWHIGH</b>

Покупки только через личные сообщения.
Пиши {OWNER_USERNAME} и указывай, что хочешь купить.

💰 <b>ЦЕНЫ:</b>
• 👑 VIP на неделю — 100 ⭐
• 📈 +25% к рейтингу — 50 ⭐
• 🎰 +10% к удаче — 15 ⭐

📢 <b>ПЛАТНАЯ РЕКЛАМА:</b>
• 50 ⭐ — обычный пост (250 символов, без мата)
• 100 ⭐ — любой пост (400 символов, мат разрешён)
Рассылается ВСЕМ пользователям мгновенно!

После оплаты ты получишь товар в течение 5 минут.
        """
        bot.send_message(
            user_id,
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
            )
        )
    
    elif data_cmd == "info":
        text = f"""
ℹ️ <b>О ПРОЕКТЕ LOWHIGH</b>

👑 <b>Владелец:</b> {OWNER_USERNAME}
📌 <b>Тип:</b> Некоммерческая рассылка
🚫 <b>Важно:</b> Коммерческие проекты не рекламировать!

🎁 <b>КОНКУРС КАЖДУЮ ПЯТНИЦУ</b>
В 12:00 самый активный пользователь недели
получает подарок на 15 ⭐

🏆 <b>Активность считается по:</b>
• Написанным постам
• Полученным лайкам
• Приглашённым друзьям
• Играм в казино

📊 <b>Версия бота:</b> 3.3
        """
        bot.send_message(
            user_id,
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
            )
        )

# ========== ПРИЁМ СООБЩЕНИЙ ==========

def receive_post(message):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        bot.send_message(user_id, "🚫 Вы забанены")
        return
    
    user = get_user(user_id)
    if not user:
        return
    
    can_post, cd = check_post_cooldown(user)
    if not can_post:
        bot.send_message(
            user_id,
            f"⏳ Подожди ещё {format_time(cd)} перед следующим постом",
            reply_markup=main_keyboard()
        )
        return
    
    if message.text and message.text.lower() in ["отмена", "cancel"]:
        bot.send_message(user_id, "❌ Отправка отменена", reply_markup=main_keyboard())
        return
    
    if message.content_type != 'text':
        bot.send_message(
            user_id,
            "❌ Принимаем только текст! Картинки и другие файлы не поддерживаются.",
            reply_markup=main_keyboard()
        )
        return
    
    if not message.text:
        return
    
    max_len = get_max_post_length(user_id)
    if len(message.text) > max_len:
        bot.send_message(
            user_id,
            f"❌ Пост слишком длинный! Максимум {max_len} символов.\n"
            f"У тебя: {len(message.text)} символов",
            reply_markup=main_keyboard()
        )
        return
    
    text = censor_text(message.text, user_id)
    
    post = {
        "id": int(time.time() * 1000),
        "user_id": str(user_id),
        "username": user.get("username"),
        "text": text,
        "time": datetime.now().isoformat()
    }
    
    user["last_post_time"] = datetime.now().isoformat()
    user["posts_count"] = user.get("posts_count", 0) + 1
    
    update_quest_progress(user_id, "post", 1)
    if len(text) > 200:
        update_quest_progress(user_id, "post_length", 200, extra=len(text))
    
    if is_admin(user_id) or is_verified(user_id):
        sent = send_post_to_users(post, user_id)
        bot.send_message(
            user_id,
            f"✅ <b>Пост мгновенно разослан!</b>\n\n"
            f"📊 Доставлено: {sent} пользователям",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )
        user["total_posts"] += 1
        save_data(data)
    else:
        data["posts"].append(post)
        user["total_posts"] += 1
        save_data(data)
        
        bot.send_message(
            user_id,
            f"✅ <b>Пост отправлен на модерацию!</b>\n\n"
            f"Как только администратор одобрит, он уйдёт в рассылку.\n"
            f"Обычно это занимает не больше часа.",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )
        
        print_log("POST", f"Новый пост от {get_user_display_name(user_id)}")
        
        for admin_id in data.get("admins", []):
            if admin_id != str(user_id):
                admin = get_user(admin_id)
                if admin and admin.get("admin_notifications", True):
                    try:
                        bot.send_message(
                            int(admin_id),
                            f"🆕 <b>Новый пост от {get_user_display_name(user_id)}!</b>\n"
                            f"/admin - для модерации",
                            parse_mode="HTML"
                        )
                    except:
                        pass

def receive_reject_reason(message, post_data, post_index):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    reason = message.text if message.text and message.text != '-' else "Причина не указана"
    
    data["posts"].pop(post_index)
    save_data(data)
    
    try:
        bot.send_message(
            int(post_data["user_id"]),
            f"❌ <b>Твой пост отклонён</b>\n\n"
            f"📝 <b>Причина:</b> {reason}\n\n"
            f"Не расстраивайся, попробуй ещё раз!",
            parse_mode="HTML"
        )
    except:
        pass
    
    bot.send_message(
        user_id,
        f"❌ <b>Пост отклонён</b>\n\n"
        f"Причина отправлена автору.",
        parse_mode="HTML"
    )
    
    if data["posts"]:
        next_post = data["posts"][0]
        author = get_user_display_name(next_post["user_id"])
        text = f"📝 <b>Следующий пост от {author}</b>\n\n{next_post['text']}"
        bot.send_message(
            user_id,
            text,
            parse_mode="HTML",
            reply_markup=admin_post_actions_keyboard(next_post['id'])
        )
    else:
        bot.send_message(
            user_id,
            "📭 <b>Больше нет постов на модерации</b>",
            parse_mode="HTML",
            reply_markup=admin_main_keyboard()
        )

def receive_interpol_post(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    if message.content_type != 'text':
        bot.send_message(
            user_id,
            "❌ Принимаем только текст!",
            reply_markup=admin_main_keyboard()
        )
        return
    
    if message.text:
        post = {
            "id": int(time.time() * 1000),
            "user_id": str(user_id),
            "username": "ADMIN",
            "text": message.text,
            "time": datetime.now().isoformat()
        }
        
        sent = send_post_to_users(post, user_id, force_all=True)
        bot.send_message(
            user_id,
            f"📢 <b>Интерпол-рассылка выполнена!</b>\n\n"
            f"✅ Доставлено: {sent} пользователям",
            parse_mode="HTML",
            reply_markup=admin_main_keyboard()
        )

def receive_hotline_message(message):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        bot.send_message(user_id, "🚫 Вы забанены")
        return
    
    user = get_user(user_id)
    if not user:
        return
    
    if message.text and message.text.lower() in ["отмена", "cancel"]:
        bot.send_message(user_id, "❌ Отправка отменена", reply_markup=main_keyboard())
        return
    
    if message.content_type != 'text':
        bot.send_message(
            user_id,
            "❌ Принимаем только текст!",
            reply_markup=main_keyboard()
        )
        return
    
    user["last_hotline"] = datetime.now().isoformat()
    save_data(data)
    
    text = f"""
📞 <b>ГОРЯЧАЯ ЛИНИЯ</b>

<b>От:</b> {get_user_display_name(user_id)} (ID: {user_id})
<b>Время:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}

<b>Сообщение:</b>
{message.text}

Ответьте пользователю в личку.
    """
    
    for admin_id in data.get("admins", []):
        try:
            bot.send_message(int(admin_id), text, parse_mode="HTML")
        except:
            pass
    
    bot.send_message(
        user_id,
        "✅ <b>Сообщение отправлено администраторам!</b>\n\n"
        "Они ответят тебе в личку в ближайшее время.",
        parse_mode="HTML",
        reply_markup=main_keyboard()
    )

# ========== ФОНОВЫЕ ЗАДАЧИ ==========

def background_tasks():
    last_tax = None
    last_reset = None
    
    while True:
        time.sleep(60)
        now = datetime.now()
        
        if not last_tax or now.date() > last_tax.date():
            apply_rating_tax()
            last_tax = now
        
        if now.weekday() == 5 and (not last_reset or last_reset.date() != now.date()):
            reset_weekly_activity()
            last_reset = now
        
        if now.weekday() == 4 and now.hour == 12 and now.minute == 0:
            award_weekly_top()
        
        if now.minute % 5 == 0:
            save_data(data)

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    print(f"{Colors.BOLD}{Colors.HEADER}")
    print("="*50)
    print("     LowHigh v3.3")
    print("="*50)
    print(f"{Colors.END}")
    
    print_log("INFO", f"Мастер-админы: {MASTER_ADMINS}")
    print_log("INFO", f"Всего админов: {len(data.get('admins', []))}")
    print_log("INFO", f"Всего юзеров: {len(data['users'])}")
    print_log("INFO", f"Постов в очереди: {len(data['posts'])}")
    print_log("INFO", "Бот запущен...")
    
    threading.Thread(target=background_tasks, daemon=True).start()
    
    while True:
        try:
            bot.infinity_polling()
        except Exception as e:
            print_log("ERROR", f"Критическая ошибка: {e}")
            print_log("INFO", "Перезапуск через 10 секунд...")
            time.sleep(10)
