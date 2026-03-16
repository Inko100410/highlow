# LowHigh v3.0 — ПОЛНЫЙ КОД
# Все фичи, все админ-команды, всё что просил

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

# ========== БАЗА ДАННЫХ (НАДЁЖНОЕ СОХРАНЕНИЕ) ==========
DATA_FILE = "bot_data.json"

def save_data(data):
    """Атомарное сохранение с бэкапом"""
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
            
        print_log("INFO", "Данные сохранены (атомарно)")
        return True
    except Exception as e:
        print_log("ERROR", f"Ошибка сохранения: {e}")
        if os.path.exists(backup_file):
            os.replace(backup_file, DATA_FILE)
        return False

def load_data():
    """Загрузка с восстановлением из бэкапа при повреждении"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print_log("INFO", f"Загружено {len(data.get('users', {}))} пользователей")
                return data
        except Exception as e:
            print_log("ERROR", f"Основной файл повреждён: {e}")
    
    backup_file = DATA_FILE + ".backup"
    if os.path.exists(backup_file):
        try:
            with open(backup_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print_log("WARNING", "Загружено из бэкапа")
                with open(DATA_FILE, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                return data
        except Exception as e:
            print_log("ERROR", f"Бэкап тоже повреждён: {e}")
    
    # Создаём новую базу
    print_log("WARNING", "Создана новая база данных")
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
        "global_reactions": {}
    }

data = load_data()

# ========== РАБОТА С ПОЛЬЗОВАТЕЛЯМИ ==========

def get_user(user_id):
    """Получить или создать пользователя"""
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
            "quest_bonus_ready": False
        }
        print_log("SUCCESS", f"Новый пользователь! ID: {user_id}")
        save_data(data)
    
    return data["users"][user_id]

def get_user_display_name(user_id):
    """Получить имя для отображения"""
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
    """Эмодзи статуса"""
    user_id = str(user_id)
    if is_vip(user_id):
        return "👑"
    elif is_verified(user_id):
        return "✅"
    else:
        return "📝"

def get_max_referrals(user_id):
    """Макс рефералов в зависимости от статуса"""
    user_id = str(user_id)
    if is_vip(user_id):
        return 50
    elif is_verified(user_id):
        return 25
    else:
        return 10

def get_post_cooldown(user_id):
    """КД на пост в часах"""
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
    """Проверка КД на пост"""
    if not user["last_post_time"]:
        return True, 0
    
    last = datetime.fromisoformat(user["last_post_time"])
    cooldown_hours = get_post_cooldown(user)
    next_time = last + timedelta(hours=cooldown_hours)
    now = datetime.now()
    
    if now >= next_time:
        return True, 0
    return False, (next_time - now).total_seconds()

def get_max_post_length(user_id):
    """Макс длина поста"""
    user_id = str(user_id)
    if is_vip(user_id):
        return 500
    elif is_verified(user_id):
        return 300
    else:
        return 250

def check_casino_cooldown(user):
    """Проверка КД казино"""
    if not user["last_casino"]:
        return True, 0
    last = datetime.fromisoformat(user["last_casino"])
    next_time = last + timedelta(hours=8)
    now = datetime.now()
    if now >= next_time:
        return True, 0
    return False, (next_time - now).total_seconds()

def format_time(seconds):
    """Форматирование времени"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}ч {minutes}м"

def apply_rating_min(user):
    """Применить минимальный рейтинг"""
    if is_vip(user) or is_verified(user):
        return max(10.0, user["rating"])
    else:
        return max(5.0, user["rating"])

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
    """Проверка VIP с учётом срока"""
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
Бесплатный бот для рассылки некоммерческой рекламы проектов и каналов/групп

<b>📝 Реклама:</b>
Пишешь пост который далее уходит остальным пользователям бота
Дойдёт пост или нет зависит от Вашего шанса и рейтинга юзера, к которому пост должен прийти

<b>🎰 Бонус-Казино:</b>
Делаешь крутку и если победил - бонус на +10% успеха доставки поста
Проиграл? Шанс растет: 0.01% → 0.02% → 0.03%...
Каждая попытка = -1% рейтинга.
Попытка раз в 8 часов

<b>🔄 Конвертация (раз в 24ч):</b>
Меняешь 5% рейтинга на 1% удачи в крутке

<b>👥 Рефералы:</b>
Друг = +1% к удаче навсегда

Погнали! 👇
"""

# ========== РАССЫЛКА ПОСТОВ С КНОПКАМИ ==========

def send_post_to_users(post, admin_id, force_all=False):
    """Умная рассылка: 1% гарантированно + остальные по шансу + бонус рефералов"""
    from_user_id = post["user_id"]
    author = get_user(from_user_id)
    
    if not author:
        print_log("ERROR", f"Автор {from_user_id} не найден или забанен")
        return 0
    
    # Собираем получателей (кроме автора, забаненных и с активным глушителем)
    all_recipients = []
    for uid, user_data in data["users"].items():
        if uid == from_user_id or uid in data["banned_users"]:
            continue
        
        # Проверка глушителя
        if user_data.get("silencer_until"):
            try:
                until = datetime.fromisoformat(user_data["silencer_until"])
                if datetime.now() < until:
                    continue
                else:
                    user_data["silencer_until"] = None
            except:
                user_data["silencer_until"] = None
        
        all_recipients.append((uid, user_data))
    
    if not all_recipients:
        print_log("WARNING", "Нет получателей для рассылки")
        try:
            bot.send_message(int(from_user_id), "😢 Пока нет других пользователей для рассылки")
        except:
            pass
        return 0
    
    total_users = len(all_recipients)
    print_log("POST", f"Начинаем рассылку поста от {get_user_display_name(from_user_id)}. Всего юзеров: {total_users}")
    
    if force_all:
        guaranteed_count = total_users
        chance_recipients = []
        print_log("POST", f"ИНТЕРПОЛ-РЕЖИМ: рассылка всем {total_users} пользователям")
    else:
        guaranteed_count = max(1, int(total_users * 0.01))
        print_log("POST", f"Гарантированная доставка: {guaranteed_count} чел")
        random.shuffle(all_recipients)
    
    guaranteed_recipients = all_recipients[:guaranteed_count]
    chance_recipients = all_recipients[guaranteed_count:]
    
    sent_count = 0
    post_id = post["id"]
    
    # Сохраняем содержимое поста для жалоб
    data["post_contents"][str(post_id)] = {
        "text": post['text'],
        "author_id": from_user_id,
        "author_name": get_user_display_name(from_user_id)
    }
    
    if str(post_id) not in data["post_reactions"]:
        data["post_reactions"][str(post_id)] = {
            "likes": [],
            "dislikes": [],
            "complaints": []
        }
    
    if str(post_id) not in data["post_history"]:
        data["post_history"][str(post_id)] = {}
    
    author_emoji = get_user_status_emoji(from_user_id)
    formatted_text = f"<i>{post['text']}</i>"
    
    # Рассылка гарантированной части
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
            
            sent_msg = bot.send_message(
                int(uid),
                f"📢 <b>Пост</b> {author_emoji} от {get_user_display_name(from_user_id)}:\n\n{formatted_text}",
                parse_mode="HTML",
                reply_markup=markup
            )
            sent_count += 1
            author["rating"] = min(95.0, author["rating"] + 0.01)
            data["post_history"][str(post_id)][str(uid)] = sent_msg.message_id
            author["weekly_activity"] = author.get("weekly_activity", 0) + 5
            author["weekly_posts"] = author.get("weekly_posts", 0) + 1
            print_log("SUCCESS", f"Пост доставлен {uid} (гарантия)")
        except Exception as e:
            print_log("ERROR", f"Ошибка отправки {uid}: {e}")
    
    # Рассылка по шансу
    chance_hits = 0
    for uid, user_data in chance_recipients:
        if force_all:
            final_chance = 100
        else:
            # Бонус от рефералов
            referral_bonus = 0
            if author.get("referrals"):
                total_ref_rating = 0
                for ref_id in author["referrals"]:
                    ref_user = get_user(ref_id)
                    if ref_user:
                        total_ref_rating += ref_user.get("rating", 0)
                referral_bonus = total_ref_rating / 100
            
            final_chance = (
                user_data["incoming_chance"] + 
                (author["rating"] / 2) + 
                (author["luck"] / 10) +
                referral_bonus
            )
            final_chance = max(5, min(95, final_chance))
        
        if random.uniform(0, 100) <= final_chance:
            try:
                markup = InlineKeyboardMarkup(row_width=3)
                markup.add(
                    InlineKeyboardButton(f"👍 0", callback_data=f"like_{post_id}"),
                    InlineKeyboardButton(f"👎 0", callback_data=f"dislike_{post_id}"),
                    InlineKeyboardButton("⚠️", callback_data=f"complaint_{post_id}")
                )
                if is_admin(uid):
                    markup.add(InlineKeyboardButton("🚫 УДАЛИТЬ У ВСЕХ", callback_data=f"global_delete_{post_id}"))
                
                sent_msg = bot.send_message(
                    int(uid),
                    f"📢 <b>Пост</b> {author_emoji} от {get_user_display_name(from_user_id)}:\n\n{formatted_text}",
                    parse_mode="HTML",
                    reply_markup=markup
                )
                sent_count += 1
                chance_hits += 1
                author["rating"] = min(95.0, author["rating"] + 0.01)
                data["post_history"][str(post_id)][str(uid)] = sent_msg.message_id
                author["weekly_activity"] += 5
                author["weekly_posts"] += 1
            except Exception as e:
                print_log("ERROR", f"Ошибка отправки {uid}: {e}")
    
    print_log("POST", f"✅ Пост доставлен {sent_count}/{total_users} юзерам (гарантия: {guaranteed_count}, шанс: {chance_hits})")
    
    try:
        bot.send_message(
            int(from_user_id),
            f"✅ <b>Твой пост разослан!</b>\n\n"
            f"📊 <b>Статистика:</b>\n"
            f"Всего пользователей: {total_users}\n"
            f"Доставлено: {sent_count}\n"
            f"🎯 Гарантированно: {guaranteed_count}\n"
            f"🎲 По шансу: {chance_hits}\n\n"
            f"📈 Твой рейтинг вырос до: {author['rating']:.1f}%",
            parse_mode="HTML"
        )
    except:
        pass
    
    data["stats"]["total_posts_sent"] += 1
    save_data(data)
    
    return sent_count

def delete_post_globally(post_id):
    """Удаление поста у всех пользователей"""
    if str(post_id) not in data["post_history"]:
        return 0
    
    deleted_count = 0
    for uid, msg_id in data["post_history"][str(post_id)].items():
        try:
            bot.delete_message(int(uid), msg_id)
            deleted_count += 1
        except:
            pass
    
    del data["post_history"][str(post_id)]
    if str(post_id) in data["post_contents"]:
        del data["post_contents"][str(post_id)]
    if str(post_id) in data["post_reactions"]:
        del data["post_reactions"][str(post_id)]
    save_data(data)
    
    return deleted_count

def update_post_reactions_buttons(post_id, chat_id, message_id):
    """Обновление кнопок с актуальными счётчиками"""
    reactions = data["post_reactions"].get(str(post_id), {"likes": [], "dislikes": [], "complaints": []})
    likes_count = len(reactions["likes"])
    dislikes_count = len(reactions["dislikes"])
    
    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(
        InlineKeyboardButton(f"👍 {likes_count}", callback_data=f"like_{post_id}"),
        InlineKeyboardButton(f"👎 {dislikes_count}", callback_data=f"dislike_{post_id}"),
        InlineKeyboardButton("⚠️", callback_data=f"complaint_{post_id}")
    )
    
    try:
        bot.edit_message_reply_markup(chat_id, message_id, reply_markup=markup)
    except:
        pass

# ========== ТОП-10 ==========

def get_top_users():
    """Возвращает топ-10 пользователей по рейтингу"""
    users_list = []
    for uid, u in data["users"].items():
        if uid not in data["banned_users"]:
            name = get_user_display_name(uid)
            users_list.append({
                "id": uid,
                "name": name,
                "rating": u.get("rating", 0),
                "luck": u.get("luck", 0),
                "posts": u.get("total_posts", 0)
            })
    
    return sorted(users_list, key=lambda x: x["rating"], reverse=True)[:10]

# ========== АНТИ-МАТ ==========

BAD_WORDS = [
    "хуй", "пизда", "ебать", "блядь", "сука", "гандон", "пидор", 
    "нахуй", "похуй", "залупа", "мудак", "долбоёб", "хуесос"
]

def censor_text(text, user_id):
    """Замена мата на звёздочки (VIP могут писать всё)"""
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

def generate_daily_quests(user_id):
    """Генерация 3 случайных квестов на день"""
    today = datetime.now().date().isoformat()
    user = get_user(user_id)
    if not user:
        return
    
    if user.get("quests") and user["quests"].get("date") == today:
        return
    
    # Выбираем 3 случайных квеста (с учётом редкости)
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
    """Обновление прогресса квеста"""
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
        elif task["type"] == "ref_post" and qtype == "referral_post":
            match = True
        
        if match:
            quests["progress"][i] += value
            if quests["progress"][i] >= task["target"]:
                quests["completed"][i] = True
                # Выдаём награду
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
    """Топ пользователей по активности за неделю"""
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
    """Награждение самого активного в пятницу в 12:00"""
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
            f"🎁 Ты стал самым активным на этой неделе!\n"
            f"Твоя активность: {winner['activity']} очков\n"
            f"Получи 15 ⭐ от @nickelium"
        )
        # Здесь нужно отправить звёзды через Telegram API
        # Пока только уведомление
    except:
        pass

def reset_weekly_activity():
    """Сброс еженедельной активности (суббота)"""
    now = datetime.now()
    if now.weekday() != 5:  # суббота
        return
    
    for u in data["users"].values():
        u["weekly_activity"] = 0
        u["weekly_posts"] = 0
        u["weekly_likes"] = 0
    print_log("INFO", "Еженедельная активность сброшена")
    save_data(data)

# ========== НАЛОГ НА РЕЙТИНГ ==========

def apply_rating_tax():
    """Снятие 1% рейтинга у всех раз в сутки"""
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
    """Главное меню"""
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
        InlineKeyboardButton("⭐ Магазин", callback_data="shop"),
        InlineKeyboardButton("ℹ️ Инфо", callback_data="info")
    ]
    markup.add(*buttons)
    return markup

def casino_keyboard():
    """Кнопки казино"""
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🎲 Сделать крутку", callback_data="casino_spin"))
    markup.add(InlineKeyboardButton("◀️ Назад", callback_data="main_menu"))
    return markup

def cancel_keyboard():
    """Кнопка отмены"""
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("❌ ОТМЕНА", callback_data="cancel_post"))
    return markup

def admin_main_keyboard():
    """Главное меню админки"""
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
    """Список постов на модерации"""
    markup = InlineKeyboardMarkup(row_width=1)
    for i, post in enumerate(posts[:5]):
        short_text = post['text'][:30] + "..." if len(post['text']) > 30 else post['text']
        markup.add(
            InlineKeyboardButton(f"{i+1}. {short_text}", callback_data=f"admin_post_{post['id']}")
        )
    markup.add(InlineKeyboardButton("◀️ Назад", callback_data="admin_main"))
    return markup

def admin_post_actions_keyboard(post_id):
    """Действия с постом"""
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("✅ ОДОБРИТЬ", callback_data=f"approve_{post_id}"),
        InlineKeyboardButton("❌ ОТКЛОНИТЬ", callback_data=f"reject_{post_id}"),
        InlineKeyboardButton("🚫 ЗАБАНИТЬ АВТОРА", callback_data=f"ban_user_{post_id}"),
        InlineKeyboardButton("📢 ИНТЕРПОЛ", callback_data=f"interpol_{post_id}"),
        InlineKeyboardButton("◀️ К списку", callback_data="admin_posts_list")
    )
    return markup

def admin_users_list_keyboard(users, action_prefix, back_callback):
    """Список пользователей"""
    markup = InlineKeyboardMarkup(row_width=1)
    for i, uid in enumerate(users[:10]):
        name = get_user_display_name(uid)
        markup.add(
            InlineKeyboardButton(f"{i+1}. {name}", callback_data=f"{action_prefix}_{uid}")
        )
    markup.add(InlineKeyboardButton("◀️ Назад", callback_data=back_callback))
    return markup

def admin_user_actions_keyboard(uid, user_type):
    """Действия с пользователем"""
    markup = InlineKeyboardMarkup(row_width=2)
    
    if user_type == "vip":
        markup.add(
            InlineKeyboardButton("❌ СНЯТЬ VIP", callback_data=f"remove_vip_{uid}"),
            InlineKeyboardButton("◀️ Назад", callback_data="admin_vip_list")
        )
    elif user_type == "verified":
        markup.add(
            InlineKeyboardButton("❌ СНЯТЬ ВЕРИФ", callback_data=f"remove_verified_{uid}"),
            InlineKeyboardButton("◀️ Назад", callback_data="admin_verified_list")
        )
    elif user_type == "admin":
        if uid not in [str(a) for a in MASTER_ADMINS]:
            markup.add(
                InlineKeyboardButton("❌ СНЯТЬ АДМИНА", callback_data=f"remove_admin_{uid}"),
                InlineKeyboardButton("◀️ Назад", callback_data="admin_admins_list")
            )
    elif user_type == "banned":
        markup.add(
            InlineKeyboardButton("✅ РАЗБАНИТЬ", callback_data=f"unban_{uid}"),
            InlineKeyboardButton("◀️ Назад", callback_data="admin_bans_list")
        )
    
    return markup

def inventory_keyboard(user):
    """Клавиатура инвентаря"""
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

# ========== ОБРАБОТЧИКИ КОМАНД ==========

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        bot.send_message(user_id, "🚫 Вы забанены в этом боте.")
        return
    
    user = get_user(user_id)
    user["first_name"] = message.from_user.first_name
    
    # Реферальная система
    args = message.text.split()
    if len(args) > 1:
        referrer_id = args[1]
        if referrer_id != str(user_id):
            if not user["referrer"]:
                referrer = get_user(referrer_id)
                if referrer:
                    max_ref = get_max_referrals(referrer_id)
                    if len(referrer["referrals"]) < max_ref and str(user_id) not in referrer["referrals"]:
                        user["referrer"] = referrer_id
                        referrer["referrals"].append(str(user_id))
                        referrer["luck"] = min(50.0, referrer["luck"] + 1.0)
                        
                        print_log("SUCCESS", f"Реферал: {user_id} от {referrer_id}")
                        save_data(data)
                        
                        try:
                            bot.send_message(
                                int(referrer_id),
                                f"🎉 У тебя новый реферал: {get_user_display_name(user_id)}\n"
                                f"Удача +1% (теперь {referrer['luck']:.1f}%)\n"
                                f"Рефералов: {len(referrer['referrals'])}/{max_ref}"
                            )
                            # Квест
                            update_quest_progress(referrer_id, "referral", 1)
                        except:
                            pass
    
    user["username"] = message.from_user.username
    user["first_name"] = message.from_user.first_name
    
    # Генерация квестов на день
    generate_daily_quests(user_id)
    
    status_emoji = get_user_status_emoji(user_id)
    cooldown = get_post_cooldown(user_id)
    
    welcome = (WELCOME_TEXT + 
               f"\n\nСтатус: {status_emoji}\n"
               f"📈 Рейтинг: {user['rating']:.1f}%\n"
               f"🍀 Удача: {user['luck']:.1f}%\n"
               f"⏱ КД на пост: {cooldown}ч")
    
    bot.send_message(user_id, welcome, parse_mode="HTML", reply_markup=main_keyboard())
    print_log("INFO", f"Пользователь {user_id} зашел в бота")

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, f"🚫 У вас нет прав администратора.")
        return
    
    text = "👑 <b>АДМИН-ПАНЕЛЬ</b>\n\nВыберите действие:"
    bot.send_message(user_id, text, parse_mode="HTML", reply_markup=admin_main_keyboard())

@bot.message_handler(commands=['post'])
def cmd_post(message):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        bot.send_message(user_id, "🚫 Вы забанены")
        return
    
    user = get_user(user_id)
    can_post, cooldown = check_post_cooldown(user)
    
    if not can_post:
        bot.send_message(user_id, f"⏳ Подожди еще {format_time(cooldown)} перед следующим постом")
        return
    
    # Прогноз успеха
    prediction = user["rating"] / 2 + user["luck"] / 10
    prediction = max(5, min(95, prediction))
    
    max_len = get_max_post_length(user_id)
    
    bot.send_message(
        user_id,
        f"📊 <b>Прогноз доставки:</b> {prediction:.1f}%\n"
        f"⏱ <b>Лучшее время:</b> 20:00-22:00\n"
        f"🕐 <b>Сейчас:</b> {datetime.now().strftime('%H:%M')}\n\n"
        f"📝 Отправь текст поста (максимум {max_len} символов, только текст):",
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
    
    status = f"🎰 Твой шанс: {user['luck']:.2f}%\n"
    
    if user.get("quest_bonus_ready"):
        status += "🔥 Бонус +20% за квесты готов!\n"
    
    if can_play:
        status += "✅ Можно играть! Нажми /spin"
    else:
        status += f"⏳ Жди: {format_time(cooldown)}"
    
    bot.send_message(user_id, status, reply_markup=casino_keyboard())

@bot.message_handler(commands=['spin'])
def cmd_spin(message):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        return
    
    user = get_user(user_id)
    can_play, cooldown = check_casino_cooldown(user)
    
    if not can_play:
        bot.send_message(user_id, f"⏳ Подожди еще {format_time(cooldown)}")
        return
    
    # Уменьшаем рейтинг
    old_rating = user["rating"]
    user["rating"] = max(5.0, user["rating"] - 1.0)
    if is_vip(user_id) or is_verified(user_id):
        user["rating"] = max(10.0, user["rating"])
    
    # Бонус от квестов
    bonus = 0
    if user.get("quest_bonus_ready"):
        bonus = 20
        user["quest_bonus_ready"] = False
    
    roll = random.uniform(0, 100)
    won = roll <= (user["luck"] + bonus)
    
    if won:
        # Выигрыш: случайный предмет
        items = ["amulet", "silencer", "vip_pass"]
        item = random.choice(items)
        inv = user.get("inventory", {})
        
        if inv.get(item, 0) == 0:
            inv[item] = 1
            user["inventory"] = inv
            result_text = f"🎉 <b>ПОБЕДА!</b>\n\nТы выиграл предмет: {item}!"
        else:
            # Если предмет уже есть, даём +5% рейтинга
            user["rating"] = min(95.0, user["rating"] + 5.0)
            result_text = f"🎉 <b>ПОБЕДА!</b>\n\n+5% к рейтингу (предмет уже есть)"
        
        user["total_wins"] += 1
        user["fail_counter"] = 0
        data["stats"]["total_wins"] += 1
        update_quest_progress(user_id, "casino_win", 1)
    else:
        user["fail_counter"] += 1
        luck_increase = user["fail_counter"] * 0.01
        user["luck"] = min(50.0, user["luck"] + luck_increase)
        
        result_text = f"""
😢 <b>ПРОИГРЫШ</b>

Удача +{luck_increase:.2f}% → {user['luck']:.2f}%
Рейтинг: {old_rating:.1f}% → {user['rating']:.1f}%
        """
    
    user["last_casino"] = datetime.now().isoformat()
    user["total_casino_attempts"] += 1
    user["weekly_activity"] += 1
    data["stats"]["total_attempts"] += 1
    update_quest_progress(user_id, "casino", 1)
    save_data(data)
    
    bot.send_message(user_id, result_text, parse_mode="HTML")

@bot.message_handler(commands=['top'])
def cmd_top(message):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        return
    
    top = get_top_users()
    text = "🏆 <b>ТОП-10 ПО РЕЙТИНГУ</b>\n\n"
    
    for i, u in enumerate(top, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
        text += f"{medal} {i}. {u['name']} — 📈 {u['rating']:.1f}% | 🍀 {u['luck']:.1f}% | 📝 {u['posts']}\n"
    
    bot.send_message(user_id, text, parse_mode="HTML")

@bot.message_handler(commands=['help'])
def cmd_help(message):
    help_text = """
<b>📚 КОМАНДЫ БОТА</b>

post - Написать пост для рассылки
casino - Информация о казино и текущем шансе
spin - Сделать крутку в казино (доступно раз в 8 часов)
top - Топ-10 игроков по рейтингу
convert - Обменять 5% рейтинга на 1% удачи (раз в 24ч)
start - Запустить бота и показать главное меню
help - Показать этот список команд
/admin - Панель администратора (только для админов)
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
            bot.send_message(user_id, "❌ Уже конвертил сегодня! Завтра снова")
            return
    
    if user["rating"] < 5.1:
        bot.send_message(user_id, "❌ Мало рейтинга (мин 5.1%)")
        return
    
    user["rating"] -= 5.0
    user["luck"] = min(50.0, user["luck"] + 1.0)
    user["last_convert"] = datetime.now().isoformat()
    save_data(data)
    
    bot.send_message(
        user_id,
        f"✅ <b>Конвертация выполнена!</b>\n\n"
        f"Рейтинг -5% → {user['rating']:.1f}%\n"
        f"Удача +1% → {user['luck']:.1f}%",
        parse_mode="HTML"
    )

# ========== АДМИН-КОМАНДЫ ==========

@bot.message_handler(commands=['setrating'])
def set_rating(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "🚫 Недоступно. Только для админов.")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(
            user_id, 
            "❌ Использование:\n"
            "/setrating [ID] [значение] - установить рейтинг любому игроку\n"
            "/setrating [значение] - себе"
        )
        return
    
    try:
        if len(args) == 3:
            target_id = args[1]
            new_rating = float(args[2])
        else:
            target_id = str(user_id)
            new_rating = float(args[1])
        
        target = get_user(target_id)
        if not target:
            bot.send_message(user_id, "❌ Пользователь не найден")
            return
        
        old_rating = target["rating"]
        target["rating"] = max(5.0, min(95.0, new_rating))
        if is_vip(target_id) or is_verified(target_id):
            target["rating"] = max(10.0, target["rating"])
        save_data(data)
        
        bot.send_message(
            user_id,
            f"✅ Рейтинг изменен\n"
            f"Пользователь: {get_user_display_name(target_id)} (ID: {target_id})\n"
            f"Было: {old_rating:.1f}% → Стало: {target['rating']:.1f}%"
        )
        
        if target_id != str(user_id):
            try:
                bot.send_message(
                    int(target_id),
                    f"👑 Админ изменил твой рейтинг\n"
                    f"{old_rating:.1f}% → {target['rating']:.1f}%"
                )
            except:
                pass
                
    except ValueError:
        bot.send_message(user_id, "❌ Значение должно быть числом")
    except Exception as e:
        bot.send_message(user_id, f"❌ Ошибка: {e}")

@bot.message_handler(commands=['setluck'])
def set_luck(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "🚫 Недоступно. Только для админов.")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(
            user_id,
            "❌ Использование:\n"
            "/setluck [ID] [значение] - установить удачу любому игроку\n"
            "/setluck [значение] - себе"
        )
        return
    
    try:
        if len(args) == 3:
            target_id = args[1]
            new_luck = float(args[2])
        else:
            target_id = str(user_id)
            new_luck = float(args[1])
        
        target = get_user(target_id)
        if not target:
            bot.send_message(user_id, "❌ Пользователь не найден")
            return
        
        old_luck = target["luck"]
        target["luck"] = max(1.0, min(50.0, new_luck))
        save_data(data)
        
        bot.send_message(
            user_id,
            f"✅ Удача изменена\n"
            f"Пользователь: {get_user_display_name(target_id)} (ID: {target_id})\n"
            f"Было: {old_luck:.1f}% → Стало: {target['luck']:.1f}%"
        )
        
        if target_id != str(user_id):
            try:
                bot.send_message(
                    int(target_id),
                    f"👑 Админ изменил твою удачу\n"
                    f"{old_luck:.1f}% → {target['luck']:.1f}%"
                )
            except:
                pass
                
    except ValueError:
        bot.send_message(user_id, "❌ Значение должно быть числом")
    except Exception as e:
        bot.send_message(user_id, f"❌ Ошибка: {e}")

@bot.message_handler(commands=['addadmin'])
def add_admin(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "🚫 Недостаточно прав")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(user_id, "❌ Укажи ID пользователя: /addadmin 123456789")
        return
    
    try:
        new_admin_id = int(args[1])
        new_admin_id_str = str(new_admin_id)
        
        if new_admin_id_str not in data["admins"]:
            data["admins"].append(new_admin_id_str)
            save_data(data)
            bot.send_message(user_id, f"✅ Пользователь {new_admin_id} назначен админом")
            
            try:
                bot.send_message(
                    new_admin_id,
                    f"🎉 Теперь ты админ! Используй /admin для модерации"
                )
            except:
                pass
        else:
            bot.send_message(user_id, "⚠️ Уже админ")
    except:
        bot.send_message(user_id, "❌ Неверный ID")

@bot.message_handler(commands=['removeadmin'])
def remove_admin(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "🚫 Недостаточно прав")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(user_id, "❌ Укажи ID пользователя: /removeadmin 123456789")
        return
    
    try:
        remove_id = int(args[1])
        remove_id_str = str(remove_id)
        
        if remove_id_str == str(user_id):
            bot.send_message(user_id, "❌ Нельзя удалить себя")
            return
        if remove_id_str in [str(a) for a in MASTER_ADMINS]:
            bot.send_message(user_id, "❌ Нельзя удалить главного админа")
            return
        
        if remove_id_str in data["admins"]:
            data["admins"].remove(remove_id_str)
            save_data(data)
            bot.send_message(user_id, f"✅ Админ {remove_id} удален")
        else:
            bot.send_message(user_id, "⚠️ Не админ")
    except:
        bot.send_message(user_id, "❌ Неверный ID")

@bot.message_handler(commands=['addvip'])
def add_vip(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "🚫 Недостаточно прав")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(user_id, "❌ Укажи ID пользователя: /addvip 123456789")
        return
    
    try:
        new_vip_id = int(args[1])
        new_vip_id_str = str(new_vip_id)
        
        if len(args) >= 3:
            # Временный VIP
            days = int(args[2])
            user = get_user(new_vip_id_str)
            if user:
                until = datetime.now() + timedelta(days=days)
                user["vip_until"] = until.isoformat()
                save_data(data)
                bot.send_message(
                    user_id,
                    f"👑 Пользователь {new_vip_id} назначен VIP на {days} дней\n"
                    f"Действует до: {until.strftime('%Y-%m-%d %H:%M')}"
                )
                try:
                    bot.send_message(
                        new_vip_id,
                        f"👑 Поздравляем! Теперь ты VIP на {days} дней!\n"
                        f"Привилегии:\n"
                        f"• КД на пост: 2 часа\n"
                        f"• Рефералов: до 50\n"
                        f"• Длина поста: 500 символов"
                    )
                except:
                    pass
        else:
            # Постоянный VIP (старая система)
            if new_vip_id_str not in data.get("vip_users", []):
                if "vip_users" not in data:
                    data["vip_users"] = []
                data["vip_users"].append(new_vip_id_str)
                save_data(data)
                bot.send_message(user_id, f"👑 Пользователь {new_vip_id} назначен VIP (постоянно)")
                
                try:
                    bot.send_message(
                        new_vip_id,
                        f"👑 Поздравляем! Теперь ты VIP пользователь!\n"
                        f"Привилегии:\n"
                        f"• КД на пост: 2 часа\n"
                        f"• Рефералов: до 50\n"
                        f"• Длина поста: 500 символов"
                    )
                except:
                    pass
            else:
                bot.send_message(user_id, "⚠️ Уже VIP")
    except:
        bot.send_message(user_id, "❌ Неверный ID или формат. Используй /addvip ID [дни]")

@bot.message_handler(commands=['vipinfo'])
def vipinfo(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "🚫 Недостаточно прав")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(user_id, "❌ Укажи ID пользователя: /vipinfo 123456789")
        return
    
    try:
        target_id = args[1]
        target_id_str = str(target_id)
        user = get_user(target_id_str)
        
        if not user:
            bot.send_message(user_id, "❌ Пользователь не найден")
            return
        
        text = f"👑 <b>Информация о VIP</b>\n\nID: {target_id_str}\n"
        
        if user.get("vip_until"):
            until = datetime.fromisoformat(user["vip_until"])
            if until > datetime.now():
                left = until - datetime.now()
                text += f"Статус: ✅ активен\nДо: {until.strftime('%Y-%m-%d %H:%M')}\nОсталось: {left.days} дн. {left.seconds//3600} ч."
            else:
                text += f"Статус: ❌ истёк\nИстёк: {until.strftime('%Y-%m-%d %H:%M')}"
                user["vip_until"] = None
                save_data(data)
        elif target_id_str in data.get("vip_users", []):
            text += "Статус: ✅ постоянный VIP"
        else:
            text += "Статус: ❌ не VIP"
        
        bot.send_message(user_id, text, parse_mode="HTML")
        
    except Exception as e:
        bot.send_message(user_id, f"❌ Ошибка: {e}")

@bot.message_handler(commands=['removevip'])
def remove_vip(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "🚫 Недостаточно прав")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(user_id, "❌ Укажи ID пользователя: /removevip 123456789")
        return
    
    try:
        remove_id = int(args[1])
        remove_id_str = str(remove_id)
        
        user = get_user(remove_id_str)
        removed = False
        
        if user and user.get("vip_until"):
            user["vip_until"] = None
            removed = True
        
        if remove_id_str in data.get("vip_users", []):
            data["vip_users"].remove(remove_id_str)
            removed = True
        
        if removed:
            save_data(data)
            bot.send_message(user_id, f"✅ VIP статус удален у {remove_id}")
            
            try:
                bot.send_message(
                    remove_id,
                    f"❌ Ваш VIP статус был удален администратором"
                )
            except:
                pass
        else:
            bot.send_message(user_id, "⚠️ Пользователь не имеет VIP статуса")
    except:
        bot.send_message(user_id, "❌ Неверный ID")

@bot.message_handler(commands=['addverified'])
def add_verified(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "🚫 Недостаточно прав")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(user_id, "❌ Укажи ID пользователя: /addverified 123456789")
        return
    
    try:
        new_ver_id = int(args[1])
        new_ver_id_str = str(new_ver_id)
        
        if new_ver_id_str not in data.get("verified_users", []):
            if "verified_users" not in data:
                data["verified_users"] = []
            data["verified_users"].append(new_ver_id_str)
            save_data(data)
            bot.send_message(user_id, f"✅ Пользователь {new_ver_id} верифицирован")
            
            try:
                bot.send_message(
                    new_ver_id,
                    f"✅ Поздравляем! Теперь ты верифицированный пользователь!\n"
                    f"Привилегии:\n"
                    f"• Посты без модерации\n"
                    f"• Рефералов: до 25\n"
                    f"• Длина поста: 300 символов"
                )
            except:
                pass
        else:
            bot.send_message(user_id, "⚠️ Уже верифицирован")
    except:
        bot.send_message(user_id, "❌ Неверный ID")

@bot.message_handler(commands=['removeverified'])
def remove_verified(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "🚫 Недостаточно прав")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(user_id, "❌ Укажи ID пользователя: /removeverified 123456789")
        return
    
    try:
        remove_id = int(args[1])
        remove_id_str = str(remove_id)
        
        if remove_id_str in data.get("verified_users", []):
            data["verified_users"].remove(remove_id_str)
            save_data(data)
            bot.send_message(user_id, f"✅ Верификация удалена у {remove_id}")
            
            try:
                bot.send_message(
                    remove_id,
                    f"❌ Ваш верифицированный статус был удален администратором"
                )
            except:
                pass
        else:
            bot.send_message(user_id, "⚠️ Не верифицирован")
    except:
        bot.send_message(user_id, "❌ Неверный ID")

@bot.message_handler(commands=['delpost'])
def delete_post(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "🚫 Не админ")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(user_id, "❌ Укажи ID поста: /delpost 1234567890")
        return
    
    post_id = args[1]
    deleted = delete_post_globally(post_id)
    
    if deleted:
        bot.send_message(user_id, f"✅ Пост удален у {deleted} пользователей")
    else:
        bot.send_message(user_id, f"❌ Пост не найден или уже удален")

@bot.message_handler(commands=['ban'])
def ban_user(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "🚫 Не админ")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(user_id, "❌ Укажи ID пользователя: /ban 123456789")
        return
    
    try:
        target_id = args[1]
        target_id_str = str(target_id)
        
        if target_id_str not in data["banned_users"]:
            data["banned_users"].append(target_id_str)
            save_data(data)
            bot.send_message(user_id, f"🚫 Пользователь {target_id} забанен")
            
            try:
                bot.send_message(
                    int(target_id),
                    f"🚫 Вы были забанены администратором"
                )
            except:
                pass
        else:
            bot.send_message(user_id, "⚠️ Уже забанен")
    except:
        bot.send_message(user_id, "❌ Неверный ID")

@bot.message_handler(commands=['unban'])
def unban_user(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "🚫 Не админ")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(user_id, "❌ Укажи ID пользователя: /unban 123456789")
        return
    
    try:
        target_id = args[1]
        target_id_str = str(target_id)
        
        if target_id_str in data["banned_users"]:
            data["banned_users"].remove(target_id_str)
            save_data(data)
            bot.send_message(user_id, f"✅ Пользователь {target_id} разбанен")
            
            try:
                bot.send_message(
                    int(target_id),
                    f"✅ Вы были разбанены администратором"
                )
            except:
                pass
        else:
            bot.send_message(user_id, "⚠️ Не в бане")
    except:
        bot.send_message(user_id, "❌ Неверный ID")

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
    
    # ===== ОБРАБОТКА РЕАКЦИЙ НА ПОСТЫ =====
    if data_cmd.startswith("like_"):
        post_id = data_cmd.split("_")[1]
        
        if str(post_id) not in data["post_reactions"]:
            data["post_reactions"][str(post_id)] = {"likes": [], "dislikes": [], "complaints": []}
        
        reactions = data["post_reactions"][str(post_id)]
        
        # Находим автора поста
        post_info = data["post_contents"].get(str(post_id), {})
        author_id = post_info.get("author_id")
        
        if user_id_str in reactions["likes"]:
            reactions["likes"].remove(user_id_str)
            bot.answer_callback_query(call.id, "Лайк убран")
        else:
            if user_id_str in reactions["dislikes"]:
                reactions["dislikes"].remove(user_id_str)
            reactions["likes"].append(user_id_str)
            bot.answer_callback_query(call.id, "Лайк поставлен")
            
            # Автор получает +0.05% рейтинга
            if author_id and author_id != user_id_str:
                author = get_user(author_id)
                if author:
                    author["rating"] = min(95.0, author["rating"] + 0.05)
                    author["weekly_activity"] += 2
                    author["weekly_likes"] += 1
                    update_quest_progress(author_id, "likes_recv", 1)
            
            # Тот, кто поставил лайк, получает прогресс квеста
            update_quest_progress(user_id, "likes_give", 1)
        
        save_data(data)
        update_post_reactions_buttons(post_id, call.message.chat.id, call.message.message_id)
        return
    
    elif data_cmd.startswith("dislike_"):
        post_id = data_cmd.split("_")[1]
        
        if str(post_id) not in data["post_reactions"]:
            data["post_reactions"][str(post_id)] = {"likes": [], "dislikes": [], "complaints": []}
        
        reactions = data["post_reactions"][str(post_id)]
        
        # Находим автора поста
        post_info = data["post_contents"].get(str(post_id), {})
        author_id = post_info.get("author_id")
        
        if user_id_str in reactions["dislikes"]:
            reactions["dislikes"].remove(user_id_str)
            bot.answer_callback_query(call.id, "Дизлайк убран")
        else:
            if user_id_str in reactions["likes"]:
                reactions["likes"].remove(user_id_str)
            reactions["dislikes"].append(user_id_str)
            bot.answer_callback_query(call.id, "Дизлайк поставлен")
            
            # Автор теряет 0.03% рейтинга
            if author_id and author_id != user_id_str:
                author = get_user(author_id)
                if author:
                    author["rating"] = max(5.0, author["rating"] - 0.03)
                    if is_vip(author_id) or is_verified(author_id):
                        author["rating"] = max(10.0, author["rating"])
        
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
            bot.answer_callback_query(call.id, "Жалоба отправлена администратору")
            
            # Уведомляем админов
            for admin_id in data.get("admins", []):
                if admin_id != user_id_str:
                    try:
                        complaint_text = f"""
⚠️ <b>ЖАЛОБА НА ПОСТ</b>

<b>Пост ID:</b> {post_id}
<b>Автор:</b> {author_name} (ID: {author_id})
<b>Жалобу отправил:</b> {get_user_display_name(user_id)} (ID: {user_id})

<b>Текст поста:</b>
{post_text}

<b>Действия:</b>
• /delpost {post_id} - удалить пост у всех
• /ban {author_id} - забанить автора
                        """
                        bot.send_message(
                            int(admin_id),
                            complaint_text,
                            parse_mode="HTML"
                        )
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
        
        bot.answer_callback_query(call.id, f"Пост удален у {deleted} пользователей")
        return
    
    # ===== АДМИН-МЕНЮ =====
    if data_cmd.startswith("admin_") or data_cmd in [
        "admin_main", "admin_posts_list", "approve_", "reject_", "ban_user_", 
        "interpol_", "admin_vip_list", "admin_verified_list", "admin_admins_list", 
        "admin_bans_list", "admin_stats", "admin_activity"
    ]:
        # Не удаляем админские сообщения
        pass
    else:
        try:
            bot.delete_message(user_id, call.message.message_id)
        except:
            pass
    
    # ===== АДМИН-ПАНЕЛЬ =====
    if data_cmd == "admin_main":
        if not is_admin(user_id):
            return
        bot.edit_message_text(
            "👑 <b>АДМИН-ПАНЕЛЬ</b>\n\nВыберите действие:",
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
                author_name = get_user_display_name(post["user_id"])
                text = f"📝 <b>Пост от {author_name}</b>\n\n{post['text']}"
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
        post_index = -1
        post_data = None
        
        for i, post in enumerate(data["posts"]):
            if str(post["id"]) == post_id:
                post_index = i
                post_data = post
                break
        
        if post_index == -1:
            bot.answer_callback_query(call.id, "Пост не найден")
            return
        
        # Отправляем пост
        sent = send_post_to_users(post_data, user_id)
        
        # Удаляем из очереди
        data["posts"].pop(post_index)
        save_data(data)
        
        # Обновляем сообщение
        if not data["posts"]:
            bot.edit_message_text(
                f"✅ Пост одобрен. Доставлено: {sent} пользователям\n\n📭 Больше нет постов",
                user_id,
                call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("◀️ В админ-панель", callback_data="admin_main")
                )
            )
        else:
            next_post = data["posts"][0]
            author_name = get_user_display_name(next_post["user_id"])
            text = f"✅ Пост одобрен. Доставлено: {sent}\n\n📝 <b>Следующий пост от {author_name}</b>\n\n{next_post['text']}"
            bot.edit_message_text(
                text,
                user_id,
                call.message.message_id,
                parse_mode="HTML",
                reply_markup=admin_post_actions_keyboard(next_post['id'])
            )
        
        bot.answer_callback_query(call.id, "✅ Пост одобрен")
    
    elif data_cmd.startswith("reject_"):
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "Не админ")
            return
        
        post_id = data_cmd.split("_")[1]
        post_index = -1
        
        for i, post in enumerate(data["posts"]):
            if str(post["id"]) == post_id:
                post_index = i
                break
        
        if post_index == -1:
            bot.answer_callback_query(call.id, "Пост не найден")
            return
        
        # Удаляем из очереди
        data["posts"].pop(post_index)
        save_data(data)
        
        # Обновляем сообщение
        if not data["posts"]:
            bot.edit_message_text(
                "❌ Пост отклонен\n\n📭 Больше нет постов",
                user_id,
                call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("◀️ В админ-панель", callback_data="admin_main")
                )
            )
        else:
            next_post = data["posts"][0]
            author_name = get_user_display_name(next_post["user_id"])
            text = f"❌ Пост отклонен\n\n📝 <b>Следующий пост от {author_name}</b>\n\n{next_post['text']}"
            bot.edit_message_text(
                text,
                user_id,
                call.message.message_id,
                parse_mode="HTML",
                reply_markup=admin_post_actions_keyboard(next_post['id'])
            )
        
        bot.answer_callback_query(call.id, "❌ Пост отклонен")
    
    elif data_cmd.startswith("ban_user_"):
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "Не админ")
            return
        
        post_id = data_cmd.split("_")[2]
        for post in data["posts"]:
            if str(post["id"]) == post_id:
                banned_id = post["user_id"]
                if banned_id not in data["banned_users"]:
                    data["banned_users"].append(banned_id)
                    bot.send_message(
                        user_id,
                        f"🚫 Пользователь {banned_id} ({get_user_display_name(banned_id)}) забанен"
                    )
                    print_log("WARNING", f"Забанен {banned_id}")
                    save_data(data)
                break
    
    elif data_cmd.startswith("interpol_"):
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "Не админ")
            return
        
        post_id = data_cmd.split("_")[1]
        for i, post in enumerate(data["posts"]):
            if str(post["id"]) == post_id:
                sent = send_post_to_users(post, user_id, force_all=True)
                
                bot.edit_message_text(
                    f"📢 Интерпол-рассылка выполнена. Доставлено: {sent} пользователям",
                    user_id,
                    call.message.message_id
                )
                
                data["posts"].pop(i)
                save_data(data)
                break
    
    elif data_cmd == "admin_interpol":
        if not is_admin(user_id):
            return
        
        bot.edit_message_text(
            "📢 <b>Интерпол-рассылка</b>\n\nОтправь текст поста для рассылки ВСЕМ пользователям:",
            user_id,
            call.message.message_id,
            parse_mode="HTML"
        )
        bot.register_next_step_handler_by_chat_id(user_id, receive_interpol_post)
    
    elif data_cmd == "admin_vip_list":
        if not is_admin(user_id):
            return
        
        # Собираем всех VIP (включая временных)
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
        
        text = f"👑 <b>VIP пользователи ({len(vip_list)}):</b>"
        bot.edit_message_text(
            text,
            user_id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=admin_users_list_keyboard(vip_list, "admin_vip", "admin_main")
        )
    
    elif data_cmd.startswith("admin_vip_"):
        if not is_admin(user_id):
            return
        
        target_id = data_cmd.split("_")[2]
        name = get_user_display_name(target_id)
        user = get_user(target_id)
        
        text = f"👑 <b>VIP пользователь</b>\n\nID: {target_id}\nИмя: {name}\n"
        
        if user and user.get("vip_until"):
            until = datetime.fromisoformat(user["vip_until"])
            text += f"Тип: временный\nДо: {until.strftime('%Y-%m-%d %H:%M')}"
        else:
            text += "Тип: постоянный"
        
        bot.edit_message_text(
            text,
            user_id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=admin_user_actions_keyboard(target_id, "vip")
        )
    
    elif data_cmd == "admin_verified_list":
        if not is_admin(user_id):
            return
        
        verified_list = data.get("verified_users", [])
        
        if not verified_list:
            bot.edit_message_text(
                "✅ Нет верифицированных пользователей",
                user_id,
                call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("◀️ Назад", callback_data="admin_main")
                )
            )
            return
        
        text = f"✅ <b>Верифицированные пользователи ({len(verified_list)}):</b>"
        bot.edit_message_text(
            text,
            user_id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=admin_users_list_keyboard(verified_list, "admin_verified", "admin_main")
        )
    
    elif data_cmd.startswith("admin_verified_"):
        if not is_admin(user_id):
            return
        
        target_id = data_cmd.split("_")[2]
        name = get_user_display_name(target_id)
        text = f"✅ <b>Верифицированный пользователь</b>\n\nID: {target_id}\nИмя: {name}"
        bot.edit_message_text(
            text,
            user_id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=admin_user_actions_keyboard(target_id, "verified")
        )
    
    elif data_cmd == "admin_admins_list":
        if not is_admin(user_id):
            return
        
        admin_list = data.get("admins", [])
        text = f"👥 <b>Администраторы ({len(admin_list)}):</b>"
        bot.edit_message_text(
            text,
            user_id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=admin_users_list_keyboard(admin_list, "admin_admin", "admin_main")
        )
    
    elif data_cmd.startswith("admin_admin_"):
        if not is_admin(user_id):
            return
        
        target_id = data_cmd.split("_")[2]
        name = get_user_display_name(target_id)
        text = f"👥 <b>Администратор</b>\n\nID: {target_id}\nИмя: {name}"
        bot.edit_message_text(
            text,
            user_id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=admin_user_actions_keyboard(target_id, "admin")
        )
    
    elif data_cmd == "admin_bans_list":
        if not is_admin(user_id):
            return
        
        banned_list = data.get("banned_users", [])
        
        if not banned_list:
            bot.edit_message_text(
                "🚫 Нет забаненных пользователей",
                user_id,
                call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("◀️ Назад", callback_data="admin_main")
                )
            )
            return
        
        text = f"🚫 <b>Забаненные пользователи ({len(banned_list)}):</b>"
        bot.edit_message_text(
            text,
            user_id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=admin_users_list_keyboard(banned_list, "admin_banned", "admin_main")
        )
    
    elif data_cmd.startswith("admin_banned_"):
        if not is_admin(user_id):
            return
        
        target_id = data_cmd.split("_")[2]
        name = get_user_display_name(target_id)
        text = f"🚫 <b>Забаненный пользователь</b>\n\nID: {target_id}\nИмя: {name}"
        bot.edit_message_text(
            text,
            user_id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=admin_user_actions_keyboard(target_id, "banned")
        )
    
    elif data_cmd == "admin_stats":
        if not is_admin(user_id):
            return
        
        total_users = len(data["users"])
        total_banned = len(data["banned_users"])
        total_admins = len(data.get("admins", []))
        
        vip_count = 0
        for uid, u in data["users"].items():
            if is_vip(uid):
                vip_count += 1
        vip_count += len(data.get("vip_users", []))
        
        total_verified = len(data.get("verified_users", []))
        total_posts = data["stats"]["total_posts_sent"]
        total_games = data["stats"]["total_attempts"]
        total_wins = data["stats"]["total_wins"]
        
        text = f"""
📊 <b>СТАТИСТИКА БОТА</b>

👥 Всего пользователей: {total_users}
🚫 Забанено: {total_banned}
👑 VIP: {vip_count}
✅ Верифицировано: {total_verified}
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
        
        target_id = data_cmd.split("_")[2]
        user = get_user(target_id)
        removed = False
        
        if user and user.get("vip_until"):
            user["vip_until"] = None
            removed = True
        
        if target_id in data.get("vip_users", []):
            data["vip_users"].remove(target_id)
            removed = True
        
        if removed:
            save_data(data)
            bot.answer_callback_query(call.id, "VIP статус удален")
            
            try:
                bot.send_message(
                    int(target_id),
                    f"❌ Ваш VIP статус был удален администратором"
                )
            except:
                pass
        
        # Возвращаемся к списку
        vip_list = []
        for uid, u in data["users"].items():
            if is_vip(uid):
                vip_list.append(uid)
        for uid in data.get("vip_users", []):
            if uid not in vip_list:
                vip_list.append(uid)
        
        if vip_list:
            text = f"👑 <b>VIP пользователи ({len(vip_list)}):</b>"
            bot.edit_message_text(
                text,
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
        
        target_id = data_cmd.split("_")[2]
        
        if target_id in data.get("verified_users", []):
            data["verified_users"].remove(target_id)
            save_data(data)
            bot.answer_callback_query(call.id, "Верификация удалена")
            
            try:
                bot.send_message(
                    int(target_id),
                    f"❌ Ваш верифицированный статус был удален администратором"
                )
            except:
                pass
        
        verified_list = data.get("verified_users", [])
        if verified_list:
            text = f"✅ <b>Верифицированные пользователи ({len(verified_list)}):</b>"
            bot.edit_message_text(
                text,
                user_id,
                call.message.message_id,
                parse_mode="HTML",
                reply_markup=admin_users_list_keyboard(verified_list, "admin_verified", "admin_main")
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
        
        target_id = data_cmd.split("_")[2]
        
        if target_id in data.get("admins", []) and target_id not in [str(a) for a in MASTER_ADMINS]:
            data["admins"].remove(target_id)
            save_data(data)
            bot.answer_callback_query(call.id, "Админ удален")
            
            try:
                bot.send_message(
                    int(target_id),
                    f"❌ Ваш статус администратора был удален"
                )
            except:
                pass
        
        admin_list = data.get("admins", [])
        text = f"👥 <b>Администраторы ({len(admin_list)}):</b>"
        bot.edit_message_text(
            text,
            user_id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=admin_users_list_keyboard(admin_list, "admin_admin", "admin_main")
        )
    
    elif data_cmd.startswith("unban_"):
        if not is_admin(user_id):
            return
        
        target_id = data_cmd.split("_")[1]
        
        if target_id in data.get("banned_users", []):
            data["banned_users"].remove(target_id)
            save_data(data)
            bot.answer_callback_query(call.id, "Пользователь разбанен")
            
            try:
                bot.send_message(
                    int(target_id),
                    f"✅ Вы были разбанены администратором"
                )
            except:
                pass
        
        banned_list = data.get("banned_users", [])
        if banned_list:
            text = f"🚫 <b>Забаненные пользователи ({len(banned_list)}):</b>"
            bot.edit_message_text(
                text,
                user_id,
                call.message.message_id,
                parse_mode="HTML",
                reply_markup=admin_users_list_keyboard(banned_list, "admin_banned", "admin_main")
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
            "Главное меню:",
            reply_markup=main_keyboard()
        )
    
    elif data_cmd == "casino":
        can_play, cooldown = check_casino_cooldown(user)
        status = f"🎰 <b>КАЗИНО</b>\n\nТвой шанс: {user['luck']:.2f}%\n"
        
        if user.get("quest_bonus_ready"):
            status += "🔥 Бонус +20% за квесты готов!\n"
        
        if can_play:
            status += "✅ Можно играть!"
        else:
            status += f"⏳ Следующая попытка через: {format_time(cooldown)}"
        
        status += f"\n\n⚠️ Каждое вращение уменьшает рейтинг на 1%"
        status += f"\n\n💰 Выигрыш: предмет или +5% к рейтингу"
        
        bot.send_message(
            user_id,
            status,
            parse_mode="HTML",
            reply_markup=casino_keyboard()
        )
    
    elif data_cmd == "casino_spin":
        # Аналогично cmd_spin, но с edit
        can_play, cooldown = check_casino_cooldown(user)
        if not can_play:
            bot.answer_callback_query(
                call.id,
                f"Подожди еще {format_time(cooldown)}",
                show_alert=True
            )
            return
        
        old_rating = user["rating"]
        user["rating"] = max(5.0, user["rating"] - 1.0)
        if is_vip(user_id) or is_verified(user_id):
            user["rating"] = max(10.0, user["rating"])
        
        bonus = 0
        if user.get("quest_bonus_ready"):
            bonus = 20
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
                result_text = f"🎉 <b>ПОБЕДА!</b>\n\nТы выиграл предмет: {item}!"
            else:
                user["rating"] = min(95.0, user["rating"] + 5.0)
                result_text = f"🎉 <b>ПОБЕДА!</b>\n\n+5% к рейтингу (предмет уже есть)"
            
            user["total_wins"] += 1
            user["fail_counter"] = 0
            data["stats"]["total_wins"] += 1
            update_quest_progress(user_id, "casino_win", 1)
        else:
            user["fail_counter"] += 1
            luck_increase = user["fail_counter"] * 0.01
            user["luck"] = min(50.0, user["luck"] + luck_increase)
            
            result_text = f"""
😢 <b>ПРОИГРЫШ</b>

Удача +{luck_increase:.2f}% → {user['luck']:.2f}%
Рейтинг: {old_rating:.1f}% → {user['rating']:.1f}%
            """
        
        user["last_casino"] = datetime.now().isoformat()
        user["total_casino_attempts"] += 1
        user["weekly_activity"] += 1
        data["stats"]["total_attempts"] += 1
        update_quest_progress(user_id, "casino", 1)
        save_data(data)
        
        bot.edit_message_text(
            result_text,
            user_id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("🎰 Еще", callback_data="casino"),
                InlineKeyboardButton("🏠 Меню", callback_data="main_menu")
            )
        )
    
    elif data_cmd == "write_post":
        can_post, cooldown = check_post_cooldown(user)
        if not can_post:
            bot.answer_callback_query(
                call.id,
                f"Подожди еще {format_time(cooldown)}",
                show_alert=True
            )
            return
        
        max_len = get_max_post_length(user_id)
        
        # Прогноз
        prediction = user["rating"] / 2 + user["luck"] / 10
        prediction = max(5, min(95, prediction))
        
        bot.send_message(
            user_id,
            f"📊 <b>Прогноз доставки:</b> {prediction:.1f}%\n"
            f"⏱ <b>Лучшее время:</b> 20:00-22:00\n"
            f"🕐 <b>Сейчас:</b> {datetime.now().strftime('%H:%M')}\n\n"
            f"📝 Отправь текст поста (максимум {max_len} символов, только текст):",
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
            ref_link = f"https://t.me/{bot_username}?start={user_id}"
        except:
            ref_link = f"https://t.me/REKLAMNOEKAZINOBOT?start={user_id}"
        
        ref_count = len(user.get("referrals", []))
        max_ref = get_max_referrals(user_id)
        
        text = f"""
👥 <b>РЕФЕРАЛЫ</b>

Приглашено: {ref_count}/{max_ref} друзей
Каждый друг = +1% к удаче навсегда

Твоя ссылка:
<code>{ref_link}</code>

Отправь ее друзьям!
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
        for pid, reactions in data["post_reactions"].items():
            total_likes += len(reactions.get("likes", []))
            total_dislikes += len(reactions.get("dislikes", []))
        
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
📻 Прием: {user['incoming_chance']}%
💰 Бонус от рефералов: +{ref_bonus:.2f}%
⏱ КД на пост: {get_post_cooldown(user_id)}ч

📝 Постов: {user['total_posts']}
🎰 Игр: {user['total_casino_attempts']}
🏆 Побед: {user['total_wins']}
👥 Рефералов: {len(user.get('referrals', []))}/{get_max_referrals(user_id)}

🌍 <b>Глобальные реакции:</b>
👍 Всего лайков: {total_likes}
👎 Всего дизлайков: {total_dislikes}

📊 <b>Глобально:</b>
Всего постов: {data['stats']['total_posts_sent']}
Всего игр: {data['stats']['total_attempts']}
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
        
        for i, u in enumerate(top, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
            text += f"{medal} {i}. {u['name']} — 📈 {u['rating']:.1f}% | 🍀 {u['luck']:.1f}%\n"
        
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
                bot.answer_callback_query(call.id, "Уже конвертил сегодня! Завтра снова", show_alert=True)
                return
        
        if user["rating"] < 5.1:
            bot.answer_callback_query(call.id, "Мало рейтинга (мин 5.1%)", show_alert=True)
            return
        
        user["rating"] -= 5.0
        user["luck"] = min(50.0, user["luck"] + 1.0)
        user["last_convert"] = datetime.now().isoformat()
        save_data(data)
        
        bot.send_message(
            user_id,
            f"✅ <b>Конвертация выполнена!</b>\n\n"
            f"Рейтинг -5% → {user['rating']:.1f}%\n"
            f"Удача +1% → {user['luck']:.1f}%",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )
    
    elif data_cmd == "inventory":
        inv = user.get("inventory", {})
        silencer_status = ""
        if user.get("silencer_until"):
            try:
                until = datetime.fromisoformat(user["silencer_until"])
                if until > datetime.now():
                    silencer_status = f" (активен до {until.strftime('%H:%M')})"
                else:
                    user["silencer_until"] = None
                    save_data(data)
            except:
                user["silencer_until"] = None
        
        text = f"""
🎒 <b>ИНВЕНТАРЬ</b>

🍀 Амулет удачи: {inv.get('amulet', 0)}
🔇 Глушитель: {inv.get('silencer', 0)}{silencer_status}
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
                "🍀 Амулет использован! +10% к рейтингу",
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
            bot.answer_callback_query(call.id, "🔇 Глушитель включён на 8ч")
            bot.send_message(
                user_id,
                f"🔇 Глушитель активирован до {until.strftime('%H:%M')}. Ты не будешь получать посты.",
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
                "🔇 Глушитель деактивирован. Теперь ты снова получаешь посты.",
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
            save_data(data)
            bot.answer_callback_query(call.id, "👑 VIP на 3 дня!")
            bot.send_message(
                user_id,
                f"👑 VIP-пропуск использован! Ты VIP до {until.strftime('%Y-%m-%d %H:%M')}",
                reply_markup=main_keyboard()
            )
        else:
            bot.answer_callback_query(call.id, "У тебя нет VIP-пропуска")
    
    elif data_cmd == "quests":
        generate_daily_quests(user_id)
        quests = user.get("quests", {})
        
        if not quests or quests.get("date") != datetime.now().date().isoformat():
            bot.send_message(user_id, "❌ Ошибка загрузки квестов")
            return
        
        text = "📋 <b>КВЕСТЫ НА СЕГОДНЯ</b>\n\n"
        for i, task in enumerate(quests.get("tasks", [])):
            status = "✅" if quests["completed"][i] else "☐"
            progress = f"{quests['progress'][i]}/{task['target']}" if not quests["completed"][i] else ""
            text += f"{status} {task['desc']} {progress} — {task['reward']}\n"
        
        bonus = "🏆 Бонус за все: +20% к следующей крутке "
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
    
    elif data_cmd == "shop":
        text = f"""
⭐ <b>МАГАЗИН LOWHIGH</b>

Покупки через ЛС {OWNER_USERNAME}

💰 <b>ЦЕНЫ:</b>
👑 VIP на неделю — 100 ⭐
📈 +25% к рейтингу — 50 ⭐
🎰 +10% к удаче — 15 ⭐

📢 <b>ПЛАТНАЯ РЕКЛАМА:</b>
• 50 ⭐ — обычный пост (250 символов, без мата)
• 100 ⭐ — любой пост (400 символов, мат разрешён)
Рассылается ВСЕМ пользователям мгновенно!

После оплаты напиши @nickelium и укажи, что хочешь купить.
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

👑 Владелец: {OWNER_USERNAME}
📌 Некоммерческая рассылка
🚫 Коммерческие проекты не рекламировать!

🎁 <b>КОНКУРС КАЖДУЮ ПЯТНИЦУ В 12:00</b>
Самый активный пользователь недели получает 15 ⭐

🏆 Активность считается по:
• Написанным постам
• Полученным лайкам
• Приглашённым друзьям
• Играм в казино
        """
        bot.send_message(
            user_id,
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
            )
        )

# ========== ПРИЕМ ПОСТОВ ==========

def receive_post(message):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        bot.send_message(user_id, "🚫 Вы забанены")
        return
    
    user = get_user(user_id)
    if not user:
        return
    
    # Проверка КД
    can_post, cooldown = check_post_cooldown(user)
    if not can_post:
        bot.send_message(
            user_id, 
            f"⏳ Подожди еще {format_time(cooldown)} перед следующим постом",
            reply_markup=main_keyboard()
        )
        return
    
    # Отмена
    if message.text and message.text.lower() in ["отмена", "cancel", "/cancel"]:
        bot.send_message(user_id, "❌ Отправка отменена", reply_markup=main_keyboard())
        return
    
    # Проверка типа
    if message.content_type != 'text':
        bot.send_message(
            user_id, 
            "❌ Принимаем только текст! Картинки, видео и другие файлы не поддерживаются.",
            reply_markup=main_keyboard()
        )
        return
    
    if message.text:
        max_len = get_max_post_length(user_id)
        if len(message.text) > max_len:
            bot.send_message(
                user_id,
                f"❌ Пост слишком длинный! Максимум {max_len} символов.\n"
                f"У тебя: {len(message.text)} символов",
                reply_markup=main_keyboard()
            )
            return
        
        # Цензура
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
        
        # Квесты
        update_quest_progress(user_id, "post", 1)
        if len(text) > 200:
            update_quest_progress(user_id, "post_length", 200, extra=len(text))
        
        if is_admin(user_id) or is_verified(user_id):
            sent = send_post_to_users(post, user_id)
            bot.send_message(
                user_id,
                f"✅ Пост мгновенно разослан!\nДоставлено: {sent} пользователям",
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
                f"✅ Пост отправлен на модерацию!\n"
                f"Как одобрят — уйдет в рассылку",
                reply_markup=main_keyboard()
            )
            
            print_log("POST", f"Новый пост от {get_user_display_name(user_id)}: {text[:50]}...")
            
            # Уведомление админам
            for admin_id in data.get("admins", []):
                if admin_id == str(user_id):
                    continue
                admin = get_user(admin_id)
                if admin and admin.get("admin_notifications", True):
                    try:
                        bot.send_message(
                            int(admin_id),
                            f"🆕 Новый пост от {get_user_display_name(user_id)}!\n/admin"
                        )
                    except:
                        pass

def receive_interpol_post(message):
    """Прием поста для интерпол-рассылки"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    if message.content_type != 'text':
        bot.send_message(
            user_id, 
            "❌ Принимаем только текст! Картинки не поддерживаются.",
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
            f"📢 Интерпол-рассылка выполнена!\nДоставлено: {sent} пользователям",
            reply_markup=admin_main_keyboard()
        )

# ========== ФОНОВЫЕ ЗАДАЧИ ==========

def background_tasks():
    """Фоновые задачи: налог, сброс активности, награждение"""
    last_tax_date = None
    last_weekly_reset = None
    
    while True:
        time.sleep(60)  # проверяем каждую минуту
        now = datetime.now()
        
        # Налог раз в сутки
        if not last_tax_date or now.date() > last_tax_date.date():
            apply_rating_tax()
            last_tax_date = now
        
        # Сброс активности в субботу
        if now.weekday() == 5 and (not last_weekly_reset or last_weekly_reset.date() != now.date()):
            reset_weekly_activity()
            last_weekly_reset = now
        
        # Награждение в пятницу в 12:00
        if now.weekday() == 4 and now.hour == 12 and now.minute == 0:
            award_weekly_top()
        
        # Автосохранение раз в 5 минут
        if now.minute % 5 == 0 and now.second < 10:
            save_data(data)

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    print(f"{Colors.BOLD}{Colors.HEADER}")
    print("="*50)
    print("     LowHigh v3.0")
    print("="*50)
    print(f"{Colors.END}")
    
    print_log("INFO", f"Мастер-админы: {MASTER_ADMINS}")
    print_log("INFO", f"Всего админов: {len(data.get('admins', []))}")
    print_log("INFO", f"Всего юзеров: {len(data['users'])}")
    print_log("INFO", f"Постов в очереди: {len(data['posts'])}")
    print_log("INFO", "Бот запущен...")
    
    # Запуск фоновых задач
    threading.Thread(target=background_tasks, daemon=True).start()
    
    # Основной цикл с перезапуском при ошибках
    while True:
        try:
            bot.infinity_polling()
        except Exception as e:
            print_log("ERROR", f"Критическая ошибка: {e}")
            print_log("INFO", "Перезапуск через 10 секунд...")
            time.sleep(10)
