# LowHigh v3.1 — ПОЛНЫЙ КОД (ВСЁ В ОДНОМ ФАЙЛЕ)

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
MASTER_ADMINS = [6656110482, 8525294722]
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
    t = datetime.now().strftime("%H:%M:%S")
    if level == "INFO":
        print(f"{Colors.BLUE}[{t}][INFO]{Colors.END} {message}")
    elif level == "SUCCESS":
        print(f"{Colors.GREEN}[{t}][✓]{Colors.END} {message}")
    elif level == "WARNING":
        print(f"{Colors.YELLOW}[{t}][⚠]{Colors.END} {message}")
    elif level == "ERROR":
        print(f"{Colors.RED}[{t}][✗]{Colors.END} {message}")
    elif level == "POST":
        print(f"{Colors.HEADER}[{t}][📢]{Colors.END} {message}")
    elif level == "CASINO":
        print(f"{Colors.BOLD}[{t}][🎰]{Colors.END} {message}")

# ========== БАЗА ДАННЫХ (НАДЁЖНОЕ СОХРАНЕНИЕ) ==========
DATA_FILE = "bot_data.json"

def save_data(data):
    temp = DATA_FILE + ".tmp"
    backup = DATA_FILE + ".backup"
    try:
        with open(temp, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        if os.path.exists(DATA_FILE):
            os.replace(DATA_FILE, backup)
        os.replace(temp, DATA_FILE)
        if os.path.exists(backup):
            os.remove(backup)
        print_log("INFO", "Данные сохранены")
    except Exception as e:
        print_log("ERROR", f"Ошибка сохранения: {e}")
        if os.path.exists(backup):
            os.replace(backup, DATA_FILE)

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print_log("INFO", f"Загружено {len(data.get('users', {}))} пользователей")
                return data
        except:
            print_log("ERROR", "Основной файл повреждён, пробуем бэкап")
    backup = DATA_FILE + ".backup"
    if os.path.exists(backup):
        try:
            with open(backup, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print_log("WARNING", "Загружено из бэкапа")
                with open(DATA_FILE, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                return data
        except:
            print_log("ERROR", "Бэкап тоже повреждён")
    return {
        "users": {},
        "posts": [],
        "banned_users": [],
        "admins": MASTER_ADMINS.copy(),
        "vip_users": [],
        "verified_users": [],
        "post_history": {},
        "post_contents": {},
        "stats": {"total_attempts": 0, "total_wins": 0, "total_posts_sent": 0},
        "post_reactions": {},
        "global_reactions": {}
    }

data = load_data()

# ========== РАБОТА С ПОЛЬЗОВАТЕЛЯМИ ==========
def get_user(user_id):
    uid = str(user_id)
    if uid in data["banned_users"]:
        return None
    if uid not in data["users"]:
        data["users"][uid] = {
            "rating": 5.0,
            "luck": 1.0,
            "fail_counter": 0,
            "incoming_chance": 50.0,
            "last_casino": None,
            "last_post_time": None,
            "posts_count": 0,
            "last_convert": None,
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
            "inventory": {"amulet": 0, "silencer": 0, "vip_pass": 0},
            "silencer_until": None,
            "weekly_activity": 0,
            "weekly_posts": 0,
            "weekly_likes": 0,
            "quests": {},
            "quest_bonus_ready": False,
            "my_posts": [],
            "post_history_data": {}
        }
        print_log("SUCCESS", f"Новый пользователь! ID: {uid}")
        save_data(data)
    return data["users"][uid]

def get_user_display_name(uid):
    uid = str(uid)
    user = data["users"].get(uid)
    if not user:
        return "Неизвестно"
    if user.get("username"):
        return user["username"]
    if user.get("first_name"):
        return user["first_name"]
    try:
        chat = bot.get_chat(int(uid))
        name = chat.first_name or "Аноним"
        user["first_name"] = name
        save_data(data)
        return name
    except:
        return f"User_{uid[-4:]}"

def get_user_status_emoji(uid):
    uid = str(uid)
    if is_vip(uid):
        return "👑"
    elif is_verified(uid):
        return "✅"
    else:
        return "📝"

def check_and_fix_rating(uid):
    user = get_user(uid)
    if not user:
        return False
    if (is_vip(uid) or is_verified(uid)) and user["rating"] < 10.0:
        user["rating"] = 10.0
        save_data(data)
        return True
    return False

def is_vip(uid):
    uid = str(uid)
    user = data["users"].get(uid)
    if not user:
        return False
    if user.get("vip_until"):
        try:
            until = datetime.fromisoformat(user["vip_until"])
            if datetime.now() < until:
                return True
            else:
                user["vip_until"] = None
        except:
            user["vip_until"] = None
    return uid in data.get("vip_users", [])

def is_verified(uid):
    return str(uid) in data.get("verified_users", [])

def is_admin(uid):
    uid = str(uid)
    if uid in [str(a) for a in MASTER_ADMINS]:
        return True
    return uid in data.get("admins", [])

def is_banned(uid):
    return str(uid) in data["banned_users"]

def is_master_admin(uid):
    return str(uid) in [str(a) for a in MASTER_ADMINS]

def get_max_referrals(uid):
    uid = str(uid)
    if is_vip(uid):
        return 50
    elif is_verified(uid):
        return 25
    else:
        return 10

def get_post_cooldown(uid):
    if is_vip(uid):
        return 2
    user = get_user(uid)
    if not user:
        return 8
    pc = user.get("posts_count", 0)
    if pc >= 37:
        return 4
    elif pc >= 22:
        return 5
    elif pc >= 12:
        return 6
    elif pc >= 5:
        return 7
    else:
        return 8

def check_post_cooldown(user):
    if not user["last_post_time"]:
        return True, 0
    last = datetime.fromisoformat(user["last_post_time"])
    cd = get_post_cooldown(user)
    nxt = last + timedelta(hours=cd)
    now = datetime.now()
    if now >= nxt:
        return True, 0
    return False, (nxt - now).total_seconds()

def get_max_post_length(uid):
    uid = str(uid)
    if is_vip(uid):
        return 500
    elif is_verified(uid):
        return 300
    else:
        return 250

def check_casino_cooldown(user):
    if not user["last_casino"]:
        return True, 0
    last = datetime.fromisoformat(user["last_casino"])
    nxt = last + timedelta(hours=8)
    now = datetime.now()
    if now >= nxt:
        return True, 0
    return False, (nxt - now).total_seconds()

def format_time(sec):
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    return f"{h}ч {m}м"

def apply_rating_min(user):
    if is_vip(user) or is_verified(user):
        return max(10.0, user["rating"])
    else:
        return max(5.0, user["rating"])

# ========== АНТИ-МАТ ==========
BAD_WORDS = ["хуй", "пизда", "ебать", "блядь", "сука", "гандон", "пидор", "нахуй", "похуй", "залупа", "мудак", "долбоёб", "хуесос"]

def censor_text(text, uid):
    if is_vip(uid):
        return text
    censored = text
    for w in BAD_WORDS:
        pattern = re.compile(re.escape(w), re.IGNORECASE)
        censored = pattern.sub("*" * len(w), censored)
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
    {"desc": "Поставить 3 лайка", "type": "likes_give", "target": 3, "reward": "luck+1", "rare": True},
    {"desc": "Пригласить 1 друга", "type": "referral", "target": 1, "reward": "luck+1"},
    {"desc": "Пригласить 2 друзей", "type": "referral", "target": 2, "reward": "luck+2", "rare": True},
    {"desc": "Чтобы реферал написал пост", "type": "ref_post", "target": 1, "reward": "rating+1"},
    {"desc": "Крутнуть казино 1 раз", "type": "casino", "target": 1, "reward": "luck+0.5"},
    {"desc": "Крутнуть казино 2 раза", "type": "casino", "target": 2, "reward": "luck+1", "rare": True},
    {"desc": "Выиграть в казино", "type": "casino_win", "target": 1, "reward": "luck+2"},
    {"desc": "Поднять рейтинг на 1%", "type": "rating_up", "target": 1, "reward": "rating+0.5"},
    {"desc": "Поднять рейтинг на 3%", "type": "rating_up", "target": 3, "reward": "rating+1", "rare": True},
    {"desc": "Заходить 3 дня подряд", "type": "streak", "target": 3, "reward": "luck+1"},
    {"desc": "Провести в боте >10 минут", "type": "time", "target": 600, "reward": "rating+1", "rare": True}
]

def generate_daily_quests(uid):
    today = datetime.now().date().isoformat()
    user = get_user(uid)
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

def update_quest_progress(uid, qtype, value=1, extra=None):
    user = get_user(uid)
    if not user or "quests" not in user:
        return
    qd = user["quests"]
    if qd.get("date") != datetime.now().date().isoformat():
        return
    changed = False
    for i, task in enumerate(qd["tasks"]):
        if qd["completed"][i]:
            continue
        match = False
        if task["type"] == qtype:
            match = True
        elif task["type"] == "post_length" and qtype == "post" and extra and extra > task["target"]:
            match = True
        elif task["type"] == "ref_post" and qtype == "referral_post":
            match = True
        if match:
            qd["progress"][i] += value
            if qd["progress"][i] >= task["target"]:
                qd["completed"][i] = True
                reward = task["reward"]
                if reward.startswith("luck+"):
                    user["luck"] = min(50.0, user["luck"] + float(reward[5:]))
                elif reward.startswith("rating+"):
                    user["rating"] = min(95.0, user["rating"] + float(reward[7:]))
                changed = True
    if changed:
        if all(qd["completed"]):
            user["quest_bonus_ready"] = True
        save_data(data)

# ========== РАССЫЛКА ПОСТОВ ==========
def send_post_to_users(post, admin_id, force_all=False):
    from_user_id = post["user_id"]
    author = get_user(from_user_id)
    if not author:
        return 0

    recipients = []
    for uid, ud in data["users"].items():
        if uid == from_user_id or uid in data["banned_users"]:
            continue
        if ud.get("silencer_until"):
            try:
                until = datetime.fromisoformat(ud["silencer_until"])
                if datetime.now() < until:
                    continue
                else:
                    ud["silencer_until"] = None
            except:
                ud["silencer_until"] = None
        recipients.append((uid, ud))

    if not recipients:
        try:
            bot.send_message(int(from_user_id), "😢 Нет получателей")
        except:
            pass
        return 0

    total = len(recipients)
    print_log("POST", f"Рассылка от {get_user_display_name(from_user_id)}. Всего: {total}")

    if force_all:
        guaranteed = total
        chance_part = []
    else:
        guaranteed = max(1, int(total * 0.01))
        random.shuffle(recipients)

    guaranteed_recipients = recipients[:guaranteed]
    chance_recipients = recipients[guaranteed:]

    sent = 0
    pid = post["id"]
    data["post_contents"][str(pid)] = {
        "text": post["text"],
        "author_id": from_user_id,
        "author_name": get_user_display_name(from_user_id)
    }
    if str(pid) not in data["post_reactions"]:
        data["post_reactions"][str(pid)] = {"likes": [], "dislikes": [], "complaints": []}
    if str(pid) not in data["post_history"]:
        data["post_history"][str(pid)] = {}

    author_emoji = get_user_status_emoji(from_user_id)
    formatted_text = f"<i>{post['text']}</i>"

    if "my_posts" not in author:
        author["my_posts"] = []
    if pid not in author["my_posts"]:
        author["my_posts"].append(pid)
    if "post_history_data" not in author:
        author["post_history_data"] = {}
    author["post_history_data"][str(pid)] = {
        "text": post["text"],
        "date": post["time"],
        "likes": 0,
        "dislikes": 0
    }

    for uid, ud in guaranteed_recipients:
        try:
            markup = InlineKeyboardMarkup(row_width=3)
            markup.add(
                InlineKeyboardButton(f"👍 0", callback_data=f"like_{pid}"),
                InlineKeyboardButton(f"👎 0", callback_data=f"dislike_{pid}"),
                InlineKeyboardButton("⚠️", callback_data=f"complaint_{pid}")
            )
            if is_admin(uid):
                markup.add(InlineKeyboardButton("🚫 УДАЛИТЬ У ВСЕХ", callback_data=f"global_delete_{pid}"))
            msg = bot.send_message(
                int(uid),
                f"📢 <b>Пост</b> {author_emoji} от {get_user_display_name(from_user_id)}:\n\n{formatted_text}",
                parse_mode="HTML",
                reply_markup=markup
            )
            sent += 1
            author["rating"] = min(95.0, author["rating"] + 0.01)
            data["post_history"][str(pid)][str(uid)] = msg.message_id
            author["weekly_activity"] = author.get("weekly_activity", 0) + 5
            author["weekly_posts"] = author.get("weekly_posts", 0) + 1
        except Exception as e:
            print_log("ERROR", f"Ошибка отправки {uid}: {e}")

    chance_hits = 0
    for uid, ud in chance_recipients:
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
            final = ud["incoming_chance"] + (author["rating"] / 2) + (author["luck"] / 10) + ref_bonus
            final = max(5, min(95, final))
        if random.uniform(0, 100) <= final:
            try:
                markup = InlineKeyboardMarkup(row_width=3)
                markup.add(
                    InlineKeyboardButton(f"👍 0", callback_data=f"like_{pid}"),
                    InlineKeyboardButton(f"👎 0", callback_data=f"dislike_{pid}"),
                    InlineKeyboardButton("⚠️", callback_data=f"complaint_{pid}")
                )
                if is_admin(uid):
                    markup.add(InlineKeyboardButton("🚫 УДАЛИТЬ У ВСЕХ", callback_data=f"global_delete_{pid}"))
                msg = bot.send_message(
                    int(uid),
                    f"📢 <b>Пост</b> {author_emoji} от {get_user_display_name(from_user_id)}:\n\n{formatted_text}",
                    parse_mode="HTML",
                    reply_markup=markup
                )
                sent += 1
                chance_hits += 1
                author["rating"] = min(95.0, author["rating"] + 0.01)
                data["post_history"][str(pid)][str(uid)] = msg.message_id
                author["weekly_activity"] += 5
                author["weekly_posts"] += 1
            except Exception as e:
                print_log("ERROR", f"Ошибка отправки {uid}: {e}")

    print_log("POST", f"✅ Пост доставлен {sent}/{total} (гарантия {guaranteed}, шанс {chance_hits})")
    try:
        bot.send_message(
            int(from_user_id),
            f"✅ <b>Твой пост разослан!</b>\n📊 Доставлено {sent}/{total}\n📈 Рейтинг +{0.01 * sent:.2f}%",
            parse_mode="HTML"
        )
    except:
        pass
    data["stats"]["total_posts_sent"] += 1
    save_data(data)
    return sent

def delete_post_globally(pid):
    pid = str(pid)
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

def update_post_reactions_buttons(pid, chat_id, msg_id):
    pid = str(pid)
    react = data["post_reactions"].get(pid, {"likes": [], "dislikes": [], "complaints": []})
    likes = len(react["likes"])
    dislikes = len(react["dislikes"])
    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(
        InlineKeyboardButton(f"👍 {likes}", callback_data=f"like_{pid}"),
        InlineKeyboardButton(f"👎 {dislikes}", callback_data=f"dislike_{pid}"),
        InlineKeyboardButton("⚠️", callback_data=f"complaint_{pid}")
    )
    try:
        bot.edit_message_reply_markup(chat_id, msg_id, reply_markup=markup)
    except:
        pass

def get_top_users():
    lst = []
    for uid, u in data["users"].items():
        if uid not in data["banned_users"]:
            lst.append({
                "name": get_user_display_name(uid),
                "rating": u.get("rating", 0),
                "luck": u.get("luck", 0)
            })
    return sorted(lst, key=lambda x: x["rating"], reverse=True)[:10]

def get_weekly_activity_top(limit=10):
    users = []
    for uid, u in data["users"].items():
        if uid not in data["banned_users"] and u.get("weekly_activity", 0) > 0:
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
            f"🎁 Ты стал самым активным на неделе!\nАктивность: {winner['activity']} очков\nПолучи 15 ⭐ от @nickelium"
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

# ========== КЛАВИАТУРЫ (ЦВЕТНЫЕ) ==========
def main_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📝 Написать пост", callback_data="write_post"),
        InlineKeyboardButton("🎰 Бонус", callback_data="casino"),
        InlineKeyboardButton("👥 Рефералы", callback_data="referrals"),
        InlineKeyboardButton("📊 Статистика", callback_data="stats"),
        InlineKeyboardButton("🏆 Топ-10", callback_data="top"),
        InlineKeyboardButton("🔄 Конвертация", callback_data="convert"),
        InlineKeyboardButton("🎒 Инвентарь", callback_data="inventory"),
        InlineKeyboardButton("📋 Квесты", callback_data="quests"),
        InlineKeyboardButton("⭐ Магазин", callback_data="shop"),
        InlineKeyboardButton("ℹ️ Инфо", callback_data="info"),
        InlineKeyboardButton("📋 История постов", callback_data="post_history")
    )
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
        InlineKeyboardButton("👑 Управление VIP", callback_data="admin_vip_list"),
        InlineKeyboardButton("✅ Управление Вериф", callback_data="admin_verified_list"),
        InlineKeyboardButton("👥 Управление админами", callback_data="admin_admins_list"),
        InlineKeyboardButton("🚫 Управление банами", callback_data="admin_bans_list"),
        InlineKeyboardButton("📊 Статистика бота", callback_data="admin_stats"),
        InlineKeyboardButton("📈 Активность", callback_data="admin_activity")
    )
    return markup

def admin_posts_list_keyboard(posts):
    markup = InlineKeyboardMarkup(row_width=1)
    for i, post in enumerate(posts[:5]):
        short_text = post['text'][:30] + "..." if len(post['text']) > 30 else post['text']
        markup.add(
            InlineKeyboardButton(f"{i + 1}. {short_text}", callback_data=f"admin_post_{post['id']}")
        )
    markup.add(InlineKeyboardButton("◀️ Назад", callback_data="admin_main"))
    return markup

def admin_post_actions_keyboard(pid):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("✅ ОДОБРИТЬ", callback_data=f"approve_{pid}"),
        InlineKeyboardButton("❌ ОТКЛОНИТЬ", callback_data=f"reject_{pid}"),
        InlineKeyboardButton("🚫 ЗАБАНИТЬ", callback_data=f"ban_user_{pid}"),
        InlineKeyboardButton("📢 ИНТЕРПОЛ", callback_data=f"interpol_{pid}"),
        InlineKeyboardButton("◀️ К списку", callback_data="admin_posts_list")
    )
    return markup

def admin_users_list_keyboard(users, prefix, back):
    markup = InlineKeyboardMarkup(row_width=1)
    for i, uid in enumerate(users[:10]):
        name = get_user_display_name(uid)
        markup.add(
            InlineKeyboardButton(f"{i + 1}. {name}", callback_data=f"{prefix}_{uid}")
        )
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
    my_posts = user.get("my_posts", [])[-5:]
    for pid in my_posts:
        pdata = user.get("post_history_data", {}).get(str(pid), {})
        text = pdata.get("text", "")[:20] + "..."
        likes = pdata.get("likes", 0)
        dislikes = pdata.get("dislikes", 0)
        date = pdata.get("date", "")[:10]
        markup.add(
            InlineKeyboardButton(f"📝 {text} [{likes}👍 {dislikes}👎] {date}",
                                 callback_data=f"post_detail_{pid}")
        )
    markup.add(InlineKeyboardButton("◀️ Назад", callback_data="main_menu"))
    return markup

def post_detail_keyboard(pid):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🔁 Повторить", callback_data=f"retry_post_{pid}"),
        InlineKeyboardButton("🗑 Удалить у всех", callback_data=f"delete_my_post_{pid}"),
        InlineKeyboardButton("◀️ Назад", callback_data="post_history")
    )
    return markup

# ========== ОБРАБОТЧИКИ КОМАНД ==========
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    if is_banned(uid):
        bot.send_message(uid, "🚫 Вы забанены.")
        return
    user = get_user(uid)
    user["first_name"] = message.from_user.first_name
    user["username"] = message.from_user.username

    args = message.text.split()
    if len(args) > 1:
        ref = args[1]
        if ref != str(uid) and not user["referrer"]:
            referrer = get_user(ref)
            if referrer:
                max_ref = get_max_referrals(ref)
                if len(referrer["referrals"]) < max_ref and str(uid) not in referrer["referrals"]:
                    user["referrer"] = ref
                    referrer["referrals"].append(str(uid))
                    referrer["luck"] = min(50.0, referrer["luck"] + 1.0)
                    try:
                        bot.send_message(int(ref), f"🎉 Новый реферал: {get_user_display_name(uid)}\nУдача +1%")
                    except:
                        pass
                    update_quest_progress(ref, "referral", 1)
                    save_data(data)

    generate_daily_quests(uid)
    status = get_user_status_emoji(uid)
    cd = get_post_cooldown(uid)
    welcome = f"""🎩 <b>LowHigh</b> 🎰

Статус: {status}
📈 Рейтинг: {user['rating']:.1f}%
🍀 Удача: {user['luck']:.1f}%
⏱ КД на пост: {cd}ч

Выбери действие:"""
    bot.send_message(uid, welcome, parse_mode="HTML", reply_markup=main_keyboard())
    print_log("INFO", f"Пользователь {uid} зашёл")

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    uid = message.from_user.id
    if not is_admin(uid):
        bot.send_message(uid, "🚫 Не админ")
        return
    bot.send_message(uid, "👑 <b>АДМИН-ПАНЕЛЬ</b>", parse_mode="HTML", reply_markup=admin_main_keyboard())

@bot.message_handler(commands=['post'])
def cmd_post(message):
    uid = message.from_user.id
    if is_banned(uid):
        bot.send_message(uid, "🚫 Вы забанены")
        return
    user = get_user(uid)
    ok, cd = check_post_cooldown(user)
    if not ok:
        bot.send_message(uid, f"⏳ Подожди ещё {format_time(cd)}")
        return
    max_len = get_max_post_length(uid)
    prediction = user["rating"] / 2 + user["luck"] / 10
    prediction = max(5, min(95, prediction))
    bot.send_message(
        uid,
        f"📊 Прогноз доставки: {prediction:.1f}%\n\n"
        f"📝 Отправь текст поста (максимум {max_len} символов, только текст):",
        reply_markup=cancel_keyboard()
    )
    bot.register_next_step_handler(message, receive_post)

@bot.message_handler(commands=['casino'])
def cmd_casino(message):
    uid = message.from_user.id
    if is_banned(uid):
        return
    user = get_user(uid)
    ok, cd = check_casino_cooldown(user)
    status = f"🎰 Твой шанс: {user['luck']:.2f}%\n"
    if user.get("quest_bonus_ready"):
        status += "🔥 Бонус +20% за квесты готов!\n"
    if ok:
        status += "✅ Можно играть!"
    else:
        status += f"⏳ Жди {format_time(cd)}"
    bot.send_message(uid, status, reply_markup=casino_keyboard())

@bot.message_handler(commands=['spin'])
def cmd_spin(message):
    uid = message.from_user.id
    if is_banned(uid):
        return
    user = get_user(uid)
    ok, cd = check_casino_cooldown(user)
    if not ok:
        bot.send_message(uid, f"⏳ Подожди ещё {format_time(cd)}")
        return
    old_rating = user["rating"]
    user["rating"] = max(5.0, user["rating"] - 1.0)
    if is_vip(uid) or is_verified(uid):
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
            res = f"🎉 ПОБЕДА! Ты выиграл предмет: {item}!"
        else:
            user["rating"] = min(95.0, user["rating"] + 5.0)
            res = "🎉 ПОБЕДА! +5% к рейтингу (предмет уже есть)"
        user["total_wins"] += 1
        user["fail_counter"] = 0
        data["stats"]["total_wins"] += 1
        update_quest_progress(uid, "casino_win", 1)
    else:
        user["fail_counter"] += 1
        inc = user["fail_counter"] * 0.01
        user["luck"] = min(50.0, user["luck"] + inc)
        res = f"😢 ПРОИГРЫШ\nУдача +{inc:.2f}%"
    user["last_casino"] = datetime.now().isoformat()
    user["total_casino_attempts"] += 1
    user["weekly_activity"] += 1
    data["stats"]["total_attempts"] += 1
    update_quest_progress(uid, "casino", 1)
    save_data(data)
    bot.send_message(uid, res, parse_mode="HTML")

@bot.message_handler(commands=['top'])
def cmd_top(message):
    uid = message.from_user.id
    if is_banned(uid):
        return
    top = get_top_users()
    text = "🏆 <b>ТОП-10 ПО РЕЙТИНГУ</b>\n\n"
    for i, u in enumerate(top, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
        text += f"{medal} {i}. {u['name']} — 📈 {u['rating']:.1f}% | 🍀 {u['luck']:.1f}%\n"
    bot.send_message(uid, text, parse_mode="HTML")

@bot.message_handler(commands=['help'])
def cmd_help(message):
    help_text = """
<b>📚 КОМАНДЫ БОТА</b>

post - Написать пост
casino - Инфо о казино
spin - Крутка
top - Топ-10
convert - Конвертация 5% рейтинга → 1% удачи
start - Главное меню
help - Это сообщение
/admin - Админка
    """
    bot.send_message(message.from_user.id, help_text, parse_mode="HTML")

@bot.message_handler(commands=['convert'])
def cmd_convert(message):
    uid = message.from_user.id
    if is_banned(uid):
        return
    user = get_user(uid)
    if user.get("last_convert"):
        last = datetime.fromisoformat(user["last_convert"])
        if datetime.now().date() == last.date():
            bot.send_message(uid, "❌ Уже сегодня")
            return
    if user["rating"] < 5.1:
        bot.send_message(uid, "❌ Мало рейтинга (мин 5.1%)")
        return
    user["rating"] -= 5.0
    user["luck"] = min(50.0, user["luck"] + 1.0)
    user["last_convert"] = datetime.now().isoformat()
    save_data(data)
    bot.send_message(uid, f"✅ Конвертация: рейтинг {user['rating']:.1f}%, удача {user['luck']:.1f}%")

# ========== АДМИН-КОМАНДЫ ==========
@bot.message_handler(commands=['setrating'])
def set_rating(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(uid, "❌ /setrating [ID] [знач] или /setrating [знач]")
        return
    try:
        if len(args) == 3:
            target = args[1]
            val = float(args[2])
        else:
            target = str(uid)
            val = float(args[1])
        user = get_user(target)
        if not user:
            bot.send_message(uid, "❌ Пользователь не найден")
            return
        old = user["rating"]
        user["rating"] = max(5.0, min(95.0, val))
        check_and_fix_rating(target)
        save_data(data)
        bot.send_message(uid, f"✅ Рейтинг {target}: {old:.1f}% → {user['rating']:.1f}%")
        if target != str(uid):
            try:
                bot.send_message(int(target), f"👑 Админ изменил твой рейтинг: {old:.1f}% → {user['rating']:.1f}%")
            except:
                pass
    except:
        bot.send_message(uid, "❌ Ошибка")

@bot.message_handler(commands=['setluck'])
def set_luck(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(uid, "❌ /setluck [ID] [знач] или /setluck [знач]")
        return
    try:
        if len(args) == 3:
            target = args[1]
            val = float(args[2])
        else:
            target = str(uid)
            val = float(args[1])
        user = get_user(target)
        if not user:
            bot.send_message(uid, "❌ Пользователь не найден")
            return
        old = user["luck"]
        user["luck"] = max(1.0, min(50.0, val))
        save_data(data)
        bot.send_message(uid, f"✅ Удача {target}: {old:.1f}% → {user['luck']:.1f}%")
        if target != str(uid):
            try:
                bot.send_message(int(target), f"👑 Админ изменил твою удачу: {old:.1f}% → {user['luck']:.1f}%")
            except:
                pass
    except:
        bot.send_message(uid, "❌ Ошибка")

@bot.message_handler(commands=['addadmin'])
def add_admin(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(uid, "❌ /addadmin ID")
        return
    try:
        new = str(int(args[1]))
        if new not in data["admins"]:
            data["admins"].append(new)
            save_data(data)
            bot.send_message(uid, f"✅ Админ {new} добавлен")
            try:
                bot.send_message(int(new), "🎉 Ты теперь админ! /admin")
            except:
                pass
        else:
            bot.send_message(uid, "⚠️ Уже админ")
    except:
        bot.send_message(uid, "❌ Неверный ID")

@bot.message_handler(commands=['removeadmin'])
def remove_admin(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(uid, "❌ /removeadmin ID")
        return
    try:
        rem = str(int(args[1]))
        if rem == str(uid):
            bot.send_message(uid, "❌ Нельзя удалить себя")
            return
        if rem in [str(a) for a in MASTER_ADMINS]:
            bot.send_message(uid, "❌ Нельзя удалить главного админа")
            return
        if rem in data["admins"]:
            data["admins"].remove(rem)
            save_data(data)
            bot.send_message(uid, f"✅ Админ {rem} удален")
            try:
                bot.send_message(int(rem), "❌ Ты больше не админ")
            except:
                pass
        else:
            bot.send_message(uid, "⚠️ Не админ")
    except:
        bot.send_message(uid, "❌ Неверный ID")

@bot.message_handler(commands=['addvip'])
def add_vip(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(uid, "❌ /addvip ID [дни]")
        return
    try:
        target = str(int(args[1]))
        user = get_user(target)
        if not user:
            bot.send_message(uid, "❌ Пользователь не найден")
            return
        if len(args) >= 3:
            days = int(args[2])
            until = datetime.now() + timedelta(days=days)
            user["vip_until"] = until.isoformat()
            bot.send_message(uid, f"✅ VIP на {days} дней до {until.strftime('%Y-%m-%d %H:%M')}")
            try:
                bot.send_message(int(target), f"👑 Ты VIP на {days} дней!")
            except:
                pass
        else:
            if target not in data.get("vip_users", []):
                if "vip_users" not in data:
                    data["vip_users"] = []
                data["vip_users"].append(target)
                bot.send_message(uid, f"✅ Постоянный VIP для {target}")
                try:
                    bot.send_message(int(target), f"👑 Ты постоянный VIP!")
                except:
                    pass
            else:
                bot.send_message(uid, "⚠️ Уже VIP")
        check_and_fix_rating(target)
        save_data(data)
    except Exception as e:
        bot.send_message(uid, f"❌ Ошибка: {e}")

@bot.message_handler(commands=['vipinfo'])
def vipinfo(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(uid, "❌ /vipinfo ID")
        return
    try:
        target = str(int(args[1]))
        user = get_user(target)
        if not user:
            bot.send_message(uid, "❌ Пользователь не найден")
            return
        if user.get("vip_until"):
            until = datetime.fromisoformat(user["vip_until"])
            if until > datetime.now():
                left = until - datetime.now()
                bot.send_message(uid, f"👑 VIP до {until.strftime('%Y-%m-%d %H:%M')}\nОсталось: {left.days} дн. {left.seconds // 3600} ч.")
            else:
                user["vip_until"] = None
                save_data(data)
                bot.send_message(uid, "👑 VIP истёк")
        elif target in data.get("vip_users", []):
            bot.send_message(uid, "👑 Постоянный VIP")
        else:
            bot.send_message(uid, "❌ Не VIP")
    except:
        bot.send_message(uid, "❌ Ошибка")

@bot.message_handler(commands=['removevip'])
def remove_vip(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(uid, "❌ /removevip ID")
        return
    try:
        target = str(int(args[1]))
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
            bot.send_message(uid, f"✅ VIP снят с {target}")
            try:
                bot.send_message(int(target), "❌ VIP статус снят")
            except:
                pass
        else:
            bot.send_message(uid, "⚠️ Не VIP")
    except:
        bot.send_message(uid, "❌ Ошибка")

@bot.message_handler(commands=['addverified'])
def add_verified(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(uid, "❌ /addverified ID")
        return
    try:
        target = str(int(args[1]))
        if target not in data.get("verified_users", []):
            if "verified_users" not in data:
                data["verified_users"] = []
            data["verified_users"].append(target)
            check_and_fix_rating(target)
            save_data(data)
            bot.send_message(uid, f"✅ Пользователь {target} верифицирован")
            try:
                bot.send_message(int(target), f"✅ Ты верифицирован! Посты без модерации.")
            except:
                pass
        else:
            bot.send_message(uid, "⚠️ Уже верифицирован")
    except:
        bot.send_message(uid, "❌ Ошибка")

@bot.message_handler(commands=['removeverified'])
def remove_verified(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(uid, "❌ /removeverified ID")
        return
    try:
        target = str(int(args[1]))
        if target in data.get("verified_users", []):
            data["verified_users"].remove(target)
            save_data(data)
            bot.send_message(uid, f"✅ Верификация снята с {target}")
            try:
                bot.send_message(int(target), "❌ Верификация снята")
            except:
                pass
        else:
            bot.send_message(uid, "⚠️ Не верифицирован")
    except:
        bot.send_message(uid, "❌ Ошибка")

@bot.message_handler(commands=['ban'])
def ban_user(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(uid, "❌ /ban ID")
        return
    try:
        target = str(int(args[1]))
        if target not in data["banned_users"]:
            data["banned_users"].append(target)
            save_data(data)
            bot.send_message(uid, f"🚫 Пользователь {target} забанен")
            try:
                bot.send_message(int(target), "🚫 Вы забанены")
            except:
                pass
        else:
            bot.send_message(uid, "⚠️ Уже в бане")
    except:
        bot.send_message(uid, "❌ Ошибка")

@bot.message_handler(commands=['unban'])
def unban_user(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(uid, "❌ /unban ID")
        return
    try:
        target = str(int(args[1]))
        if target in data["banned_users"]:
            data["banned_users"].remove(target)
            save_data(data)
            bot.send_message(uid, f"✅ Пользователь {target} разбанен")
            try:
                bot.send_message(int(target), "✅ Вы разбанены")
            except:
                pass
        else:
            bot.send_message(uid, "⚠️ Не в бане")
    except:
        bot.send_message(uid, "❌ Ошибка")

@bot.message_handler(commands=['delpost'])
def delete_post(message):
    uid = message.from_user.id
    if not is_admin(uid):
        bot.send_message(uid, "🚫 Не админ")
        return
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(uid, "❌ /delpost ID")
        return
    pid = args[1]
    deleted = delete_post_globally(pid)
    if deleted:
        bot.send_message(uid, f"✅ Пост удален у {deleted} пользователей")
    else:
        bot.send_message(uid, f"❌ Пост не найден")

# ========== КОЛЛБЭКИ ==========
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    uid = call.from_user.id
    user = get_user(uid)
    if not user and not is_banned(uid):
        return
    data_cmd = call.data

    # Реакции на посты
    if data_cmd.startswith("like_"):
        pid = data_cmd.split("_")[1]
        react = data["post_reactions"].setdefault(pid, {"likes": [], "dislikes": [], "complaints": []})
        suid = str(uid)
        author_id = data["post_contents"].get(pid, {}).get("author_id")
        if suid in react["likes"]:
            react["likes"].remove(suid)
            bot.answer_callback_query(call.id, "Лайк убран")
        else:
            if suid in react["dislikes"]:
                react["dislikes"].remove(suid)
            react["likes"].append(suid)
            bot.answer_callback_query(call.id, "Лайк поставлен")
            if author_id and author_id != suid:
                author = get_user(author_id)
                if author:
                    author["rating"] = min(95.0, author["rating"] + 0.05)
                    author["weekly_activity"] += 2
                    author["weekly_likes"] += 1
                    if "post_history_data" in author and pid in author["post_history_data"]:
                        author["post_history_data"][pid]["likes"] += 1
                    update_quest_progress(author_id, "likes_recv", 1)
            update_quest_progress(uid, "likes_give", 1)
        save_data(data)
        update_post_reactions_buttons(pid, call.message.chat.id, call.message.message_id)
        return

    elif data_cmd.startswith("dislike_"):
        pid = data_cmd.split("_")[1]
        react = data["post_reactions"].setdefault(pid, {"likes": [], "dislikes": [], "complaints": []})
        suid = str(uid)
        author_id = data["post_contents"].get(pid, {}).get("author_id")
        if suid in react["dislikes"]:
            react["dislikes"].remove(suid)
            bot.answer_callback_query(call.id, "Дизлайк убран")
        else:
            if suid in react["likes"]:
                react["likes"].remove(suid)
            react["dislikes"].append(suid)
            bot.answer_callback_query(call.id, "Дизлайк поставлен")
            if author_id and author_id != suid:
                author = get_user(author_id)
                if author:
                    author["rating"] = max(5.0, author["rating"] - 0.03)
                    if is_vip(author_id) or is_verified(author_id):
                        author["rating"] = max(10.0, author["rating"])
                    if "post_history_data" in author and pid in author["post_history_data"]:
                        author["post_history_data"][pid]["dislikes"] += 1
        save_data(data)
        update_post_reactions_buttons(pid, call.message.chat.id, call.message.message_id)
        return

    elif data_cmd.startswith("complaint_"):
        pid = data_cmd.split("_")[1]
        info = data["post_contents"].get(pid, {})
        text = info.get("text", "Текст не найден")
        aname = info.get("author_name", "Неизвестно")
        aid = info.get("author_id", "Неизвестно")
        react = data["post_reactions"].setdefault(pid, {"likes": [], "dislikes": [], "complaints": []})
        suid = str(uid)
        if suid not in react["complaints"]:
            react["complaints"].append(suid)
            bot.answer_callback_query(call.id, "Жалоба отправлена")
            for admin_id in data.get("admins", []):
                if admin_id != suid:
                    try:
                        bot.send_message(
                            int(admin_id),
                            f"⚠️ Жалоба на пост {pid}\nАвтор: {aname} ({aid})\nТекст: {text}\n/delpost {pid}",
                            parse_mode="HTML"
                        )
                    except:
                        pass
        else:
            bot.answer_callback_query(call.id, "Вы уже жаловались")
        save_data(data)
        return

    elif data_cmd.startswith("global_delete_"):
        if not is_admin(uid):
            bot.answer_callback_query(call.id, "Не админ")
            return
        pid = data_cmd.split("_")[2]
        deleted = delete_post_globally(pid)
        bot.answer_callback_query(call.id, f"Удалено у {deleted}")
        return

    # Админка
    if data_cmd.startswith("admin_") or data_cmd in ["approve_", "reject_", "ban_user_", "interpol_"]:
        pass
    else:
        try:
            bot.delete_message(uid, call.message.message_id)
        except:
            pass

    if data_cmd == "main_menu":
        bot.send_message(uid, "Главное меню:", reply_markup=main_keyboard())
        return

    if data_cmd == "casino":
        ok, cd = check_casino_cooldown(user)
        text = f"🎰 Шанс: {user['luck']:.2f}%\n"
        if user.get("quest_bonus_ready"):
            text += "🔥 Бонус +20% готов!\n"
        text += "✅ Можно" if ok else f"⏳ {format_time(cd)}"
        bot.send_message(uid, text, reply_markup=casino_keyboard())
        return

    if data_cmd == "casino_spin":
        ok, cd = check_casino_cooldown(user)
        if not ok:
            bot.answer_callback_query(call.id, f"Жди {format_time(cd)}")
            return
        old = user["rating"]
        user["rating"] = max(5.0, user["rating"] - 1.0)
        if is_vip(uid) or is_verified(uid):
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
                res = f"🎉 ПОБЕДА! Ты выиграл предмет: {item}!"
            else:
                user["rating"] = min(95.0, user["rating"] + 5.0)
                res = "🎉 ПОБЕДА! +5% к рейтингу"
            user["total_wins"] += 1
            user["fail_counter"] = 0
            data["stats"]["total_wins"] += 1
            update_quest_progress(uid, "casino_win", 1)
        else:
            user["fail_counter"] += 1
            inc = user["fail_counter"] * 0.01
            user["luck"] = min(50.0, user["luck"] + inc)
            res = f"😢 ПРОИГРЫШ\nУдача +{inc:.2f}%"
        user["last_casino"] = datetime.now().isoformat()
        user["total_casino_attempts"] += 1
        user["weekly_activity"] += 1
        data["stats"]["total_attempts"] += 1
        update_quest_progress(uid, "casino", 1)
        save_data(data)
        bot.edit_message_text(
            res,
            uid,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("🎰 Еще", callback_data="casino"),
                InlineKeyboardButton("🏠 Меню", callback_data="main_menu")
            )
        )
        return

    if data_cmd == "write_post":
        ok, cd = check_post_cooldown(user)
        if not ok:
            bot.answer_callback_query(call.id, f"Жди {format_time(cd)}")
            return
        max_len = get_max_post_length(uid)
        prediction = user["rating"] / 2 + user["luck"] / 10
        prediction = max(5, min(95, prediction))
        bot.send_message(
            uid,
            f"📊 Прогноз доставки: {prediction:.1f}%\n\n📝 Отправь текст (макс {max_len} символов):",
            reply_markup=cancel_keyboard()
        )
        bot.register_next_step_handler_by_chat_id(uid, receive_post)
        return

    if data_cmd == "cancel_post":
        bot.clear_step_handler_by_chat_id(uid)
        bot.send_message(uid, "❌ Отменено", reply_markup=main_keyboard())
        return

    if data_cmd == "referrals":
        try:
            ref_link = f"https://t.me/{bot.get_me().username}?start={uid}"
        except:
            ref_link = f"https://t.me/REKLAMNOEKAZINOBOT?start={uid}"
        cnt = len(user.get("referrals", []))
        max_ref = get_max_referrals(uid)
        text = f"👥 Рефералы: {cnt}/{max_ref}\nСсылка: {ref_link}"
        bot.send_message(
            uid,
            text,
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
            )
        )
        return

    if data_cmd == "stats":
        total_likes = sum(len(r.get("likes", [])) for r in data["post_reactions"].values())
        total_dislikes = sum(len(r.get("dislikes", [])) for r in data["post_reactions"].values())
        ref_bonus = 0
        if user.get("referrals"):
            total_ref = 0
            for rid in user["referrals"]:
                ru = get_user(rid)
                if ru:
                    total_ref += ru.get("rating", 0)
            ref_bonus = total_ref / 100
        text = f"""📊 Твоя статистика
📈 Рейтинг: {user['rating']:.1f}%
🍀 Удача: {user['luck']:.2f}%
📻 Приём: {user['incoming_chance']}%
💰 Бонус рефералов: +{ref_bonus:.2f}%
⏱ КД поста: {get_post_cooldown(uid)}ч
📝 Постов: {user['total_posts']}
🎰 Игр: {user['total_casino_attempts']}
🏆 Побед: {user['total_wins']}
👥 Рефералов: {len(user.get('referrals', []))}/{get_max_referrals(uid)}
🌍 Глобально: 👍 {total_likes} 👎 {total_dislikes} 📨 {data['stats']['total_posts_sent']}"""
        bot.send_message(
            uid,
            text,
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
            )
        )
        return

    if data_cmd == "top":
        top = get_top_users()
        text = "🏆 ТОП-10\n\n"
        for i, u in enumerate(top, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
            text += f"{medal} {i}. {u['name']} — {u['rating']:.1f}%\n"
        bot.send_message(
            uid,
            text,
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
            )
        )
        return

    if data_cmd == "convert":
        if user.get("last_convert"):
            last = datetime.fromisoformat(user["last_convert"])
            if datetime.now().date() == last.date():
                bot.answer_callback_query(call.id, "Уже сегодня")
                return
        if user["rating"] < 5.1:
            bot.answer_callback_query(call.id, "Мало рейтинга")
            return
        user["rating"] -= 5.0
        user["luck"] = min(50.0, user["luck"] + 1.0)
        user["last_convert"] = datetime.now().isoformat()
        save_data(data)
        bot.answer_callback_query(call.id, "✅ Конвертация")
        bot.send_message(uid, f"Рейтинг {user['rating']:.1f}%, удача {user['luck']:.1f}%", reply_markup=main_keyboard())
        return

    if data_cmd == "inventory":
        inv = user.get("inventory", {})
        sil = ""
        if user.get("silencer_until"):
            try:
                until = datetime.fromisoformat(user["silencer_until"])
                if until > datetime.now():
                    sil = f" (активен до {until.strftime('%H:%M')})"
                else:
                    user["silencer_until"] = None
            except:
                user["silencer_until"] = None
        text = f"🎒 Инвентарь\n🍀 Амулет: {inv.get('amulet', 0)}\n🔇 Глушитель: {inv.get('silencer', 0)}{sil}\n👑 VIP-пропуск: {inv.get('vip_pass', 0)}"
        bot.send_message(uid, text, reply_markup=inventory_keyboard(user))
        return

    if data_cmd == "use_amulet":
        inv = user.get("inventory", {})
        if inv.get("amulet", 0) == 1:
            user["rating"] = min(95.0, user["rating"] + 10.0)
            inv["amulet"] = 0
            user["inventory"] = inv
            save_data(data)
            bot.answer_callback_query(call.id, "🍀 +10% рейтинга")
            bot.send_message(uid, "Амулет использован!", reply_markup=main_keyboard())
        else:
            bot.answer_callback_query(call.id, "Нет амулета")
        return

    if data_cmd == "activate_silencer":
        inv = user.get("inventory", {})
        if inv.get("silencer", 0) == 1 and not user.get("silencer_until"):
            until = datetime.now() + timedelta(hours=8)
            user["silencer_until"] = until.isoformat()
            inv["silencer"] = 0
            user["inventory"] = inv
            save_data(data)
            bot.answer_callback_query(call.id, "🔇 Глушитель включён")
            bot.send_message(uid, f"Глушитель до {until.strftime('%H:%M')}", reply_markup=main_keyboard())
        else:
            bot.answer_callback_query(call.id, "Нельзя")
        return

    if data_cmd == "deactivate_silencer":
        if user.get("silencer_until"):
            user["silencer_until"] = None
            save_data(data)
            bot.answer_callback_query(call.id, "🔇 Глушитель выключен")
            bot.send_message(uid, "Глушитель деактивирован", reply_markup=main_keyboard())
        else:
            bot.answer_callback_query(call.id, "Не активен")
        return

    if data_cmd == "use_vippass":
        inv = user.get("inventory", {})
        if inv.get("vip_pass", 0) == 1:
            until = datetime.now() + timedelta(days=3)
            user["vip_until"] = until.isoformat()
            inv["vip_pass"] = 0
            user["inventory"] = inv
            save_data(data)
            bot.answer_callback_query(call.id, "👑 VIP на 3 дня")
            bot.send_message(uid, f"VIP до {until.strftime('%Y-%m-%d %H:%M')}", reply_markup=main_keyboard())
        else:
            bot.answer_callback_query(call.id, "Нет пропуска")
        return

    if data_cmd == "quests":
        generate_daily_quests(uid)
        qd = user.get("quests", {})
        if not qd:
            return
        text = "📋 КВЕСТЫ\n\n"
        for i, t in enumerate(qd.get("tasks", [])):
            status = "✅" if qd["completed"][i] else "☐"
            prog = f"{qd['progress'][i]}/{t['target']}" if not qd["completed"][i] else ""
            text += f"{status} {t['desc']} {prog} — {t['reward']}\n"
        bonus = "🏆 Бонус: +20% к след. крутке " + ("✅" if user.get("quest_bonus_ready") else "❌")
        text += f"\n{bonus}"
        bot.send_message(
            uid,
            text,
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
            )
        )
        return

    if data_cmd == "shop":
        text = f"""⭐ МАГАЗИН

Покупки через ЛС {OWNER_USERNAME}

👑 VIP на неделю — 100 ⭐
📈 +25% рейтинга — 50 ⭐
🎰 +10% удачи — 15 ⭐

📢 Реклама:
• 50 ⭐ — обычный пост (250 симв, без мата)
• 100 ⭐ — любой пост (400 симв, мат)
Рассылка ВСЕМ"""
        bot.send_message(
            uid,
            text,
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
            )
        )
        return

    if data_cmd == "info":
        text = f"""ℹ️ О ПРОЕКТЕ

👑 Владелец: {OWNER_USERNAME}
📌 Некоммерческая рассылка
🚫 Коммерцию не рекламировать!

🎁 Конкурс каждую пятницу в 12:00
Самый активный получает 15 ⭐"""
        bot.send_message(
            uid,
            text,
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
            )
        )
        return

    if data_cmd == "post_history":
        my_posts = user.get("my_posts", [])
        if not my_posts:
            bot.send_message(
                uid,
                "📭 У тебя пока нет постов",
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
                )
            )
            return
        bot.send_message(uid, "📋 ТВОИ ПОСТЫ", reply_markup=post_history_keyboard(user))
        return

    if data_cmd.startswith("post_detail_"):
        pid = data_cmd.split("_")[2]
        pdata = user.get("post_history_data", {}).get(pid, {})
        if not pdata:
            bot.answer_callback_query(call.id, "Пост не найден")
            return
        text = pdata.get("text", "Нет текста")
        likes = pdata.get("likes", 0)
        dislikes = pdata.get("dislikes", 0)
        date = pdata.get("date", "")[:10]
        full = f"📝 <b>Пост от {date}</b>\n\n{text}\n\n👍 {likes}  👎 {dislikes}"
        bot.edit_message_text(full, uid, call.message.message_id, parse_mode="HTML", reply_markup=post_detail_keyboard(pid))
        return

    if data_cmd.startswith("retry_post_"):
        pid = data_cmd.split("_")[2]
        pdata = user.get("post_history_data", {}).get(pid, {})
        if not pdata:
            bot.answer_callback_query(call.id, "Пост не найден")
            return
        ok, cd = check_post_cooldown(user)
        if not ok:
            bot.answer_callback_query(call.id, f"Жди {format_time(cd)}")
            return
        text = pdata.get("text", "")
        post = {
            "id": int(time.time() * 1000),
            "user_id": str(uid),
            "username": user.get("username"),
            "text": text,
            "time": datetime.now().isoformat()
        }
        user["last_post_time"] = datetime.now().isoformat()
        user["posts_count"] += 1
        sent = send_post_to_users(post, uid)
        user["total_posts"] += 1
        save_data(data)
        bot.answer_callback_query(call.id, f"✅ Пост повторно разослан! Доставлено: {sent}")
        bot.send_message(uid, f"✅ Пост повторно разослан!\nДоставлено: {sent}", reply_markup=main_keyboard())
        return

    if data_cmd.startswith("delete_my_post_"):
        pid = data_cmd.split("_")[3]
        deleted = delete_post_globally(pid)
        if deleted:
            if pid in user.get("my_posts", []):
                user["my_posts"].remove(pid)
            if pid in user.get("post_history_data", {}):
                del user["post_history_data"][pid]
            save_data(data)
            bot.answer_callback_query(call.id, f"🗑 Пост удален у {deleted} пользователей")
            my_posts = user.get("my_posts", [])
            if my_posts:
                bot.edit_message_text("📋 ТВОИ ПОСТЫ", uid, call.message.message_id, reply_markup=post_history_keyboard(user))
            else:
                bot.edit_message_text(
                    "📭 У тебя пока нет постов",
                    uid,
                    call.message.message_id,
                    reply_markup=InlineKeyboardMarkup().add(
                        InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
                    )
                )
        else:
            bot.answer_callback_query(call.id, "❌ Пост не найден")
        return

    # Админские коллбэки (сокращённо, но рабочие)
    if data_cmd == "admin_main":
        if not is_admin(uid):
            return
        bot.edit_message_text("👑 АДМИН-ПАНЕЛЬ", uid, call.message.message_id, reply_markup=admin_main_keyboard())
        return

    if data_cmd == "admin_posts_list":
        if not is_admin(uid):
            return
        if not data["posts"]:
            bot.edit_message_text(
                "📭 Нет постов",
                uid,
                call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("◀️ Назад", callback_data="admin_main")
                )
            )
            return
        bot.edit_message_text(
            f"📝 Посты ({len(data['posts'])}):",
            uid,
            call.message.message_id,
            reply_markup=admin_posts_list_keyboard(data["posts"])
        )
        return

    if data_cmd.startswith("admin_post_"):
        if not is_admin(uid):
            return
        pid = data_cmd.split("_")[2]
        for post in data["posts"]:
            if str(post["id"]) == pid:
                aname = get_user_display_name(post["user_id"])
                bot.edit_message_text(
                    f"📝 Пост от {aname}\n\n{post['text']}",
                    uid,
                    call.message.message_id,
                    parse_mode="HTML",
                    reply_markup=admin_post_actions_keyboard(pid)
                )
                break
        return

    if data_cmd.startswith("approve_"):
        if not is_admin(uid):
            bot.answer_callback_query(call.id, "Не админ")
            return
        pid = data_cmd.split("_")[1]
        for i, post in enumerate(data["posts"]):
            if str(post["id"]) == pid:
                sent = send_post_to_users(post, uid)
                data["posts"].pop(i)
                save_data(data)
                if data["posts"]:
                    nxt = data["posts"][0]
                    aname = get_user_display_name(nxt["user_id"])
                    bot.edit_message_text(
                        f"✅ Одобрено. Доставлено: {sent}\n\n📝 Следующий от {aname}\n\n{nxt['text']}",
                        uid,
                        call.message.message_id,
                        parse_mode="HTML",
                        reply_markup=admin_post_actions_keyboard(nxt['id'])
                    )
                else:
                    bot.edit_message_text(
                        f"✅ Одобрено. Доставлено: {sent}\n\n📭 Больше нет постов",
                        uid,
                        call.message.message_id,
                        reply_markup=InlineKeyboardMarkup().add(
                            InlineKeyboardButton("◀️ Назад", callback_data="admin_main")
                        )
                    )
                bot.answer_callback_query(call.id, "✅ Пост одобрен")
                break
        return

    if data_cmd.startswith("reject_"):
        if not is_admin(uid):
            bot.answer_callback_query(call.id, "Не админ")
            return
        pid = data_cmd.split("_")[1]
        for i, post in enumerate(data["posts"]):
            if str(post["id"]) == pid:
                data["posts"].pop(i)
                save_data(data)
                if data["posts"]:
                    nxt = data["posts"][0]
                    aname = get_user_display_name(nxt["user_id"])
                    bot.edit_message_text(
                        f"❌ Отклонено\n\n📝 Следующий от {aname}\n\n{nxt['text']}",
                        uid,
                        call.message.message_id,
                        parse_mode="HTML",
                        reply_markup=admin_post_actions_keyboard(nxt['id'])
                    )
                else:
                    bot.edit_message_text(
                        "❌ Отклонено\n\n📭 Больше нет постов",
                        uid,
                        call.message.message_id,
                        reply_markup=InlineKeyboardMarkup().add(
                            InlineKeyboardButton("◀️ Назад", callback_data="admin_main")
                        )
                    )
                bot.answer_callback_query(call.id, "❌ Пост отклонен")
                break
        return

    if data_cmd.startswith("ban_user_"):
        if not is_admin(uid):
            bot.answer_callback_query(call.id, "Не админ")
            return
        pid = data_cmd.split("_")[2]
        for post in data["posts"]:
            if str(post["id"]) == pid:
                bid = post["user_id"]
                if bid not in data["banned_users"]:
                    data["banned_users"].append(bid)
                    save_data(data)
                    bot.send_message(uid, f"🚫 {bid} забанен")
                break
        bot.answer_callback_query(call.id, "Готово")
        return

    if data_cmd.startswith("interpol_"):
        if not is_admin(uid):
            bot.answer_callback_query(call.id, "Не админ")
            return
        pid = data_cmd.split("_")[1]
        for i, post in enumerate(data["posts"]):
            if str(post["id"]) == pid:
                sent = send_post_to_users(post, uid, force_all=True)
                data["posts"].pop(i)
                save_data(data)
                bot.edit_message_text(f"📢 Интерпол: доставлено {sent}", uid, call.message.message_id)
                bot.answer_callback_query(call.id, f"✅ Разослано {sent}")
                break
        return

    if data_cmd == "admin_interpol":
        if not is_admin(uid):
            return
        bot.edit_message_text("📢 Отправь текст для рассылки ВСЕМ:", uid, call.message.message_id)
        bot.register_next_step_handler_by_chat_id(uid, receive_interpol_post)
        return

    if data_cmd == "admin_vip_list":
        if not is_admin(uid):
            return
        vip = []
        for u in data["users"]:
            if is_vip(u):
                vip.append(u)
        for u in data.get("vip_users", []):
            if u not in vip:
                vip.append(u)
        if not vip:
            bot.edit_message_text(
                "👑 Нет VIP",
                uid,
                call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("◀️ Назад", callback_data="admin_main")
                )
            )
            return
        bot.edit_message_text(
            f"👑 VIP ({len(vip)}):",
            uid,
            call.message.message_id,
            reply_markup=admin_users_list_keyboard(vip, "admin_vip", "admin_main")
        )
        return

    if data_cmd.startswith("admin_vip_"):
        if not is_admin(uid):
            return
        tid = data_cmd.split("_")[2]
        name = get_user_display_name(tid)
        bot.edit_message_text(
            f"👑 VIP\nID: {tid}\nИмя: {name}",
            uid,
            call.message.message_id,
            reply_markup=admin_user_actions_keyboard(tid, "vip")
        )
        return

    if data_cmd == "admin_verified_list":
        if not is_admin(uid):
            return
        ver = data.get("verified_users", [])
        if not ver:
            bot.edit_message_text(
                "✅ Нет верифицированных",
                uid,
                call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("◀️ Назад", callback_data="admin_main")
                )
            )
            return
        bot.edit_message_text(
            f"✅ Верифицированные ({len(ver)}):",
            uid,
            call.message.message_id,
            reply_markup=admin_users_list_keyboard(ver, "admin_verified", "admin_main")
        )
        return

    if data_cmd.startswith("admin_verified_"):
        if not is_admin(uid):
            return
        tid = data_cmd.split("_")[2]
        name = get_user_display_name(tid)
        bot.edit_message_text(
            f"✅ Вериф\nID: {tid}\nИмя: {name}",
            uid,
            call.message.message_id,
            reply_markup=admin_user_actions_keyboard(tid, "verified")
        )
        return

    if data_cmd == "admin_admins_list":
        if not is_admin(uid):
            return
        adm = data.get("admins", [])
        bot.edit_message_text(
            f"👥 Админы ({len(adm)}):",
            uid,
            call.message.message_id,
            reply_markup=admin_users_list_keyboard(adm, "admin_admin", "admin_main")
        )
        return

    if data_cmd.startswith("admin_admin_"):
        if not is_admin(uid):
            return
        tid = data_cmd.split("_")[2]
        name = get_user_display_name(tid)
        bot.edit_message_text(
            f"👥 Админ\nID: {tid}\nИмя: {name}",
            uid,
            call.message.message_id,
            reply_markup=admin_user_actions_keyboard(tid, "admin")
        )
        return

    if data_cmd == "admin_bans_list":
        if not is_admin(uid):
            return
        ban = data.get("banned_users", [])
        if not ban:
            bot.edit_message_text(
                "🚫 Нет банов",
                uid,
                call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("◀️ Назад", callback_data="admin_main")
                )
            )
            return
        bot.edit_message_text(
            f"🚫 Баны ({len(ban)}):",
            uid,
            call.message.message_id,
            reply_markup=admin_users_list_keyboard(ban, "admin_banned", "admin_main")
        )
        return

    if data_cmd.startswith("admin_banned_"):
        if not is_admin(uid):
            return
        tid = data_cmd.split("_")[2]
        name = get_user_display_name(tid)
        bot.edit_message_text(
            f"🚫 Бан\nID: {tid}\nИмя: {name}",
            uid,
            call.message.message_id,
            reply_markup=admin_user_actions_keyboard(tid, "banned")
        )
        return

    if data_cmd == "admin_stats":
        if not is_admin(uid):
            return
        text = f"""📊 СТАТИСТИКА
👥 Всего: {len(data['users'])}
🚫 Банов: {len(data['banned_users'])}
👑 VIP: {sum(1 for u in data['users'] if is_vip(u)) + len(data.get('vip_users', []))}
✅ Вериф: {len(data.get('verified_users', []))}
👥 Админов: {len(data.get('admins', []))}
📝 Постов всего: {data['stats']['total_posts_sent']}
🎰 Игр: {data['stats']['total_attempts']}
🏆 Побед: {data['stats']['total_wins']}"""
        bot.edit_message_text(
            text,
            uid,
            call.message.message_id,
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("◀️ Назад", callback_data="admin_main")
            )
        )
        return

    if data_cmd == "admin_activity":
        if not is_admin(uid):
            return
        top = get_weekly_activity_top(10)
        text = "📈 АКТИВНОСТЬ НЕДЕЛИ\n\n"
        if not top:
            text += "Нет данных"
        else:
            for i, u in enumerate(top, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
                text += f"{medal} {i}. {u['name']} — {u['activity']}\n"
            text += "\n🏆 Пятница 12:00 — 15 ⭐"
        bot.edit_message_text(
            text,
            uid,
            call.message.message_id,
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("◀️ Назад", callback_data="admin_main")
            )
        )
        return

    if data_cmd.startswith("remove_vip_"):
        if not is_admin(uid):
            return
        tid = data_cmd.split("_")[2]
        user = get_user(tid)
        removed = False
        if user and user.get("vip_until"):
            user["vip_until"] = None
            removed = True
        if tid in data.get("vip_users", []):
            data["vip_users"].remove(tid)
            removed = True
        if removed:
            save_data(data)
            bot.answer_callback_query(call.id, "VIP снят")
            try:
                bot.send_message(int(tid), "❌ VIP снят")
            except:
                pass
        vip = []
        for u in data["users"]:
            if is_vip(u):
                vip.append(u)
        for u in data.get("vip_users", []):
            if u not in vip:
                vip.append(u)
        if vip:
            bot.edit_message_text(
                f"👑 VIP ({len(vip)}):",
                uid,
                call.message.message_id,
                reply_markup=admin_users_list_keyboard(vip, "admin_vip", "admin_main")
            )
        else:
            bot.edit_message_text(
                "👑 Нет VIP",
                uid,
                call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("◀️ Назад", callback_data="admin_main")
                )
            )
        return

    if data_cmd.startswith("remove_verified_"):
        if not is_admin(uid):
            return
        tid = data_cmd.split("_")[2]
        if tid in data.get("verified_users", []):
            data["verified_users"].remove(tid)
            save_data(data)
            bot.answer_callback_query(call.id, "Вериф снят")
            try:
                bot.send_message(int(tid), "❌ Вериф снят")
            except:
                pass
        ver = data.get("verified_users", [])
        if ver:
            bot.edit_message_text(
                f"✅ Верифицированные ({len(ver)}):",
                uid,
                call.message.message_id,
                reply_markup=admin_users_list_keyboard(ver, "admin_verified", "admin_main")
            )
        else:
            bot.edit_message_text(
                "✅ Нет верифицированных",
                uid,
                call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("◀️ Назад", callback_data="admin_main")
                )
            )
        return

    if data_cmd.startswith("remove_admin_"):
        if not is_admin(uid):
            return
        tid = data_cmd.split("_")[2]
        if tid in data.get("admins", []) and tid not in [str(a) for a in MASTER_ADMINS]:
            data["admins"].remove(tid)
            save_data(data)
            bot.answer_callback_query(call.id, "Админ снят")
            try:
                bot.send_message(int(tid), "❌ Админ снят")
            except:
                pass
        adm = data.get("admins", [])
        bot.edit_message_text(
            f"👥 Админы ({len(adm)}):",
            uid,
            call.message.message_id,
            reply_markup=admin_users_list_keyboard(adm, "admin_admin", "admin_main")
        )
        return

    if data_cmd.startswith("unban_"):
        if not is_admin(uid):
            return
        tid = data_cmd.split("_")[1]
        if tid in data.get("banned_users", []):
            data["banned_users"].remove(tid)
            save_data(data)
            bot.answer_callback_query(call.id, "Разбанен")
            try:
                bot.send_message(int(tid), "✅ Вы разбанены")
            except:
                pass
        ban = data.get("banned_users", [])
        if ban:
            bot.edit_message_text(
                f"🚫 Баны ({len(ban)}):",
                uid,
                call.message.message_id,
                reply_markup=admin_users_list_keyboard(ban, "admin_banned", "admin_main")
            )
        else:
            bot.edit_message_text(
                "🚫 Нет банов",
                uid,
                call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("◀️ Назад", callback_data="admin_main")
                )
            )
        return

# ========== ПРИЁМ ПОСТОВ ==========
def receive_post(message):
    uid = message.from_user.id
    if is_banned(uid):
        bot.send_message(uid, "🚫 Вы забанены")
        return
    user = get_user(uid)
    if not user:
        return
    ok, cd = check_post_cooldown(user)
    if not ok:
        bot.send_message(uid, f"⏳ Жди {format_time(cd)}", reply_markup=main_keyboard())
        return
    if message.text and message.text.lower() in ["отмена", "cancel"]:
        bot.send_message(uid, "❌ Отменено", reply_markup=main_keyboard())
        return
    if message.content_type != 'text':
        bot.send_message(uid, "❌ Только текст!", reply_markup=main_keyboard())
        return
    if message.text:
        max_len = get_max_post_length(uid)
        if len(message.text) > max_len:
            bot.send_message(uid, f"❌ Максимум {max_len} символов", reply_markup=main_keyboard())
            return
        text = censor_text(message.text, uid)
        post = {
            "id": int(time.time() * 1000),
            "user_id": str(uid),
            "username": user.get("username"),
            "text": text,
            "time": datetime.now().isoformat()
        }
        user["last_post_time"] = datetime.now().isoformat()
        user["posts_count"] = user.get("posts_count", 0) + 1
        update_quest_progress(uid, "post", 1)
        if len(text) > 200:
            update_quest_progress(uid, "post_length", 200, extra=len(text))
        if is_admin(uid) or is_verified(uid):
            sent = send_post_to_users(post, uid)
            user["total_posts"] += 1
            save_data(data)
            bot.send_message(uid, f"✅ Пост разослан! Доставлено: {sent}", reply_markup=main_keyboard())
        else:
            data["posts"].append(post)
            user["total_posts"] += 1
            save_data(data)
            bot.send_message(uid, "✅ Пост на модерации", reply_markup=main_keyboard())
            print_log("POST", f"Новый пост от {get_user_display_name(uid)}")
            for aid in data.get("admins", []):
                if aid != str(uid):
                    try:
                        bot.send_message(int(aid), f"🆕 Новый пост от {get_user_display_name(uid)}!\n/admin")
                    except:
                        pass

def receive_interpol_post(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    if message.content_type != 'text':
        bot.send_message(uid, "❌ Только текст!", reply_markup=admin_main_keyboard())
        return
    if message.text:
        post = {
            "id": int(time.time() * 1000),
            "user_id": str(uid),
            "username": "ADMIN",
            "text": message.text,
            "time": datetime.now().isoformat()
        }
        sent = send_post_to_users(post, uid, force_all=True)
        bot.send_message(uid, f"📢 Интерпол: доставлено {sent}", reply_markup=admin_main_keyboard())

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
        if now.minute % 5 == 0 and now.second < 10:
            save_data(data)

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    print(f"{Colors.BOLD}{Colors.HEADER}")
    print("=" * 50)
    print("     LowHigh v3.1")
    print("=" * 50)
    print(f"{Colors.END}")
    print_log("INFO", f"Мастер-админы: {MASTER_ADMINS}")
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
