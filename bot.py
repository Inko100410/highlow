# LowHigh v5.0 — ФИНАЛЬНАЯ ВЕРСИЯ С ГРУППАМИ (ИСПРАВЛЕНО)
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatMemberUpdated
import random
import time
import json
import os
from datetime import datetime, timedelta
import threading
import re

# ========== НАСТРОЙКИ ==========
TOKEN = "8265086577:AAFqojYbFSIRE2FZg0jnJ0Qgzdh0w9_j6z4"
MASTER_ADMINS = [6656110482, 8525294722]  # только твой ID и подруги
OWNER_USERNAME = "@nickelium"
MASTER_BACKUP = [6656110482, "nickelium", "@nickelium" ]  # только ты можешь делать бэкапы

# Путь для базы данных
DATA_FILE = "bot_data.json"

bot = telebot.TeleBot(TOKEN)

# ========== ВРЕМЯ (UTC+3 МСК) ==========
def msk_time(dt=None):
    """Конвертирует время в UTC+3 (МСК)"""
    if dt is None:
        dt = datetime.now()
    return dt + timedelta(hours=3)

def format_msk_time(dt):
    """Форматирует время в МСК"""
    return msk_time(dt).strftime("%d.%m.%Y %H:%M")

def now_msk():
    """Текущее время по МСК"""
    return msk_time()

# ========== КРАСИВЫЕ ПРИНТЫ ==========
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_log(level, message):
    timestamp = format_msk_time(datetime.now())[11:16]
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
    elif level == "ADMIN":
        print(f"{Colors.BOLD}{Colors.RED}[{timestamp}][👑]{Colors.END} {message}")
    elif level == "GROUP":
        print(f"{Colors.BOLD}{Colors.GREEN}[{timestamp}][👥]{Colors.END} {message}")
    elif level == "TAX":
        print(f"{Colors.BOLD}{Colors.YELLOW}[{timestamp}][💰]{Colors.END} {message}")

# ========== АУДИТ ДЕЙСТВИЙ ==========
audit_log = []

def log_admin_action(admin_id, action, details=""):
    admin_name = get_user_display_name(admin_id, hide_username=False)
    entry = {
        "time": format_msk_time(datetime.now()),
        "admin_id": admin_id,
        "admin_name": admin_name,
        "action": action,
        "details": details
    }
    audit_log.append(entry)
    if len(audit_log) > 100:
        audit_log.pop(0)
    print_log("ADMIN", f"{admin_name}: {action} {details}")

# ========== БАЗА ДАННЫХ ==========
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
                print_log("INFO", f"Загружено {len(data.get('users', {}))} пользователей, {len(data.get('groups', {}))} групп")
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
        except:
            print_log("ERROR", "Бэкап повреждён")
    
    return {
        "users": {},
        "groups": {},
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
            "total_posts_sent": 0,
            "daily_stats": {}
        },
        "post_reactions": {},
        "global_reactions": {}
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
            "incoming_chance": 5.0,
            "last_casino": None,
            "last_post_time": None,
            "posts_count": 0,
            "last_convert": None,
            "last_hotline": None,
            "last_seen": format_msk_time(datetime.now()),
            "join_date": format_msk_time(datetime.now()),
            "referrals": [],
            "referrer": None,
            "total_posts": 0,
            "total_casino_attempts": 0,
            "total_wins": 0,
            "username": None,
            "first_name": None,
            "admin_notifications": True,
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
        today = now_msk().strftime("%Y-%m-%d")
        if "daily_stats" not in data["stats"]:
            data["stats"]["daily_stats"] = {}
        if today not in data["stats"]["daily_stats"]:
            data["stats"]["daily_stats"][today] = {"joins": 0, "posts": 0, "active": 0}
        data["stats"]["daily_stats"][today]["joins"] += 1
        data["stats"]["daily_stats"][today]["active"] += 1
        
        print_log("SUCCESS", f"Новый пользователь! ID: {user_id}")
        save_data(data)
    
    user = data["users"][user_id]
    user["last_seen"] = format_msk_time(datetime.now())
    today = now_msk().strftime("%Y-%m-%d")
    if "daily_stats" not in data["stats"]:
        data["stats"]["daily_stats"] = {}
    if today not in data["stats"]["daily_stats"]:
        data["stats"]["daily_stats"][today] = {"joins": 0, "posts": 0, "active": 0}
    data["stats"]["daily_stats"][today]["active"] += 1
    
    return data["users"][user_id]

# ========== РАБОТА С ГРУППАМИ ==========

def get_group(chat_id):
    """Получает или создаёт группу"""
    chat_id = str(chat_id)
    
    if chat_id not in data["groups"]:
        data["groups"][chat_id] = {
            "title": None,
            "members_count": 0,
            "join_date": format_msk_time(datetime.now()),
            "last_activity": format_msk_time(datetime.now()),
            "owner_id": None,
            "admins": [],
            "vip": False,
            "stats": {
                "posts_sent": 0,
                "posts_received": 0
            }
        }
        print_log("GROUP", f"Новая группа! ID: {chat_id}")
        save_data(data)
    
    return data["groups"][chat_id]

def update_group_info(chat):
    """Обновляет информацию о группе"""
    chat_id = str(chat.id)
    group = get_group(chat_id)
    group["title"] = chat.title
    try:
        group["members_count"] = bot.get_chat_members_count(chat_id)
    except:
        pass
    group["last_activity"] = format_msk_time(datetime.now())
    save_data(data)
    return group

def is_group_admin(chat_id, user_id):
    """Проверяет, является ли пользователь админом группы"""
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except:
        return False

def resolve_target(target, create_if_not_exists=False):
    """Преобразует @username или ID в ID пользователя (с автосозданием)"""
    if target.startswith("@"):
        username = target[1:].lower()
        # Ищем по юзернейму (без учёта регистра)
        for uid, user in data["users"].items():
            if user.get("username") and user["username"].lower() == username:
                return uid
        
        # Если не нашли и нужно создать
        if create_if_not_exists:
            try:
                # Пробуем получить инфо из Telegram
                chat = bot.get_chat(username)
                uid = str(chat.id)
                # Создаём пользователя
                get_user(uid)
                # Обновляем юзернейм
                user = data["users"][uid]
                user["username"] = chat.username
                user["first_name"] = chat.first_name
                save_data(data)
                return uid
            except Exception as e:
                print_log("ERROR", f"Не удалось найти пользователя {target}: {e}")
                return None
    
    try:
        uid = str(int(target))
        if get_user(uid):
            return uid
        elif create_if_not_exists:
            # Создаём по ID
            get_user(uid)
            return uid
    except:
        pass
    return None

def get_user_display_name(user_id, hide_username=True):
    """Возвращает имя пользователя для отображения"""
    user_id = str(user_id)
    user = data["users"].get(user_id)
    if not user:
        return "Неизвестно"
    
    if hide_username:
        if user.get("first_name"):
            return user["first_name"]
        if user.get("username"):
            return user["username"]
        try:
            chat = bot.get_chat(int(user_id))
            name = chat.first_name or "Аноним"
            user["first_name"] = name
            save_data(data)
            return name
        except:
            return f"User_{user_id[-4:]}"
    else:
        if user.get("username"):
            return "@" + user["username"]
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
    
    last = datetime.fromisoformat(user["last_post_time"]) - timedelta(hours=3)
    cooldown_hours = get_post_cooldown(user)
    next_time = last + timedelta(hours=cooldown_hours)
    now = datetime.now()
    
    if now >= next_time:
        return True, 0
    return False, (next_time - now).total_seconds()

def check_hotline_cooldown(user):
    if not user.get("last_hotline"):
        return True, 0
    last = datetime.fromisoformat(user["last_hotline"]) - timedelta(hours=3)
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
    last = datetime.fromisoformat(user["last_casino"]) - timedelta(hours=3)
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

def is_backup_allowed(user_id):
    """Только мастер-админ может делать бэкапы"""
    return str(user_id) in [str(a) for a in MASTER_BACKUP]

def is_vip(user_id):
    user_id = str(user_id)
    user = data["users"].get(user_id)
    if not user:
        return False
    
    if user.get("vip_until"):
        try:
            until = datetime.fromisoformat(user["vip_until"]) - timedelta(hours=3)
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

<b>👥 Группы:</b>
Бота можно добавить в группы для кросс-постинга!

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
                until = datetime.fromisoformat(user_data["silencer_until"]) - timedelta(hours=3)
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
    print_log("POST", f"Рассылка от {get_user_display_name(from_user_id, hide_username=False)}. Всего юзеров: {total}")
    
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
        "author_name": get_user_display_name(from_user_id, hide_username=False)
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
        "date": format_msk_time(datetime.now()),
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
                f"📢 <b>Пост</b> {author_emoji} от {get_user_display_name(from_user_id, hide_username=False)}:\n\n{formatted_text}",
                parse_mode="HTML",
                reply_markup=markup
            )
            sent += 1
            author["rating"] = min(95.0, author["rating"] + 0.01)
            data["post_history"][str(post_id)][str(uid)] = msg.message_id
            author["weekly_activity"] = author.get("weekly_activity", 0) + 5
            author["weekly_posts"] = author.get("weekly_posts", 0) + 1
            print_log("SUCCESS", f"Пост доставлен {uid} (гарантия)")
        except Exception as e:
            print_log("ERROR", f"Ошибка отправки {uid}: {e}")
    
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
                    f"📢 <b>Пост</b> {author_emoji} от {get_user_display_name(from_user_id, hide_username=False)}:\n\n{formatted_text}",
                    parse_mode="HTML",
                    reply_markup=markup
                )
                sent += 1
                chance_hits += 1
                author["rating"] = min(95.0, author["rating"] + 0.01)
                data["post_history"][str(post_id)][str(uid)] = msg.message_id
                author["weekly_activity"] += 5
                author["weekly_posts"] += 1
            except Exception as e:
                print_log("ERROR", f"Ошибка отправки {uid}: {e}")
    
    percent_delivered = (sent / total) * 100 if total > 0 else 0
    
    print_log("POST", f"✅ Пост доставлен {sent}/{total} юзерам ({percent_delivered:.1f}%) (гарантия: {guaranteed}, шанс: {chance_hits})")
    
    try:
        bot.send_message(
            int(from_user_id),
            f"✅ <b>Твой пост разослан!</b>\n\n"
            f"📊 <b>Статистика доставки:</b>\n"
            f"👥 Всего пользователей: {total}\n"
            f"✅ Доставлено всего: {sent}\n"
            f"📈 Процент доставки: {percent_delivered:.1f}%\n"
            f"🎯 Гарантированно получили: {guaranteed}\n"
            f"🎲 По счастливому шансу: {chance_hits}\n\n"
            f"📈 Твой рейтинг вырос до: {author['rating']:.1f}%\n"
            f"🍀 Твоя удача: {author['luck']:.2f}%\n\n"
            f"🔥 Так держать!",
            parse_mode="HTML"
        )
    except:
        pass
    
    today = now_msk().strftime("%Y-%m-%d")
    if "daily_stats" not in data["stats"]:
        data["stats"]["daily_stats"] = {}
    if today not in data["stats"]["daily_stats"]:
        data["stats"]["daily_stats"][today] = {"joins": 0, "posts": 0, "active": 0}
    data["stats"]["daily_stats"][today]["posts"] += 1
    
    data["stats"]["total_posts_sent"] += 1
    save_data(data)
    return sent

def send_post_to_groups(post, admin_id):
    """Рассылка по группам (только для админов)"""
    from_user_id = post["user_id"]
    author = get_user(from_user_id)
    
    if not author:
        print_log("ERROR", f"Автор {from_user_id} не найден")
        return 0
    
    if not data["groups"]:
        try:
            bot.send_message(int(from_user_id), "😢 Нет групп для рассылки")
        except:
            pass
        return 0
    
    # Определяем шанс доставки в зависимости от VIP автора
    base_chance = 5 if is_vip(from_user_id) else 1
    guaranteed_min = max(1, int(len(data["groups"]) * 0.01))  # минимум 1 группа или 1%
    
    all_groups = list(data["groups"].items())
    random.shuffle(all_groups)
    
    guaranteed_groups = all_groups[:guaranteed_min]
    chance_groups = all_groups[guaranteed_min:]
    
    sent = 0
    post_id = post["id"]
    
    # Сохраняем содержимое поста
    data["post_contents"][str(post_id)] = {
        "text": post["text"],
        "author_id": from_user_id,
        "author_name": get_user_display_name(from_user_id, hide_username=False),
        "type": "group"
    }
    
    # Гарантированная часть
    for gid, group_data in guaranteed_groups:
        try:
            bot.send_message(
                int(gid),
                f"📢 <b>Пост для групп</b> от {get_user_display_name(from_user_id, hide_username=False)}:\n\n{post['text']}"
            )
            sent += 1
            group_data["stats"]["posts_received"] = group_data["stats"].get("posts_received", 0) + 1
            print_log("GROUP", f"Пост доставлен в группу {group_data.get('title', gid)} (гарантия)")
        except Exception as e:
            print_log("ERROR", f"Ошибка отправки в группу {gid}: {e}")
    
    # По шансу
    chance_hits = 0
    for gid, group_data in chance_groups:
        if random.uniform(0, 100) <= base_chance:
            try:
                bot.send_message(
                    int(gid),
                    f"📢 <b>Пост для групп</b> от {get_user_display_name(from_user_id, hide_username=False)}:\n\n{post['text']}"
                )
                sent += 1
                chance_hits += 1
                group_data["stats"]["posts_received"] = group_data["stats"].get("posts_received", 0) + 1
            except Exception as e:
                print_log("ERROR", f"Ошибка отправки в группу {gid}: {e}")
    
    print_log("GROUP", f"✅ Пост доставлен в {sent}/{len(data['groups'])} групп (гарантия: {guaranteed_min}, шанс: {chance_hits})")
    
    try:
        bot.send_message(
            int(from_user_id),
            f"✅ <b>Твой пост разослан по группам!</b>\n\n"
            f"👥 Всего групп: {len(data['groups'])}\n"
            f"✅ Доставлено: {sent}\n"
            f"🎯 Гарантированно: {guaranteed_min}\n"
            f"🎲 По шансу ({base_chance}%): {chance_hits}",
            parse_mode="HTML"
        )
    except:
        pass
    
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

# ========== ТОП-10 ==========

def get_top_users():
    users = []
    for uid, u in data["users"].items():
        if uid not in data["banned_users"] and not is_admin(uid):
            name = get_user_display_name(uid, hide_username=True)
            users.append({
                "id": uid,
                "name": name,
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
    today = now_msk().date().isoformat()
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
    if quests.get("date") != now_msk().date().isoformat():
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

# ========== НАЛОГ НА РЕЙТИНГ ==========

def apply_rating_tax():
    """Снимает 1% рейтинга у всех (по МСК)"""
    taxed = 0
    notified = 0
    
    for uid, user in data["users"].items():
        if uid in data["banned_users"]:
            continue
        
        old_rating = user["rating"]
        user["rating"] -= 1.0
        
        if is_vip(uid) or is_verified(uid):
            user["rating"] = max(10.0, user["rating"])
        else:
            user["rating"] = max(5.0, user["rating"])
        
        taxed += 1
        
        # Уведомление о налоге (только если рейтинг изменился)
        if old_rating != user["rating"] and user.get("admin_notifications", True):
            try:
                bot.send_message(
                    int(uid),
                    f"💰 <b>Ежедневный налог</b>\n\n"
                    f"Снят 1% рейтинга.\n"
                    f"Твой рейтинг: {old_rating:.1f}% → {user['rating']:.1f}%\n\n"
                    f"Чтобы рейтинг не падал, пиши посты и получай лайки!",
                    parse_mode="HTML"
                )
                notified += 1
            except:
                pass
    
    save_data(data)
    print_log("TAX", f"Снят 1% у {taxed} пользователей, уведомлено {notified}")

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
        InlineKeyboardButton("👥 Групповая рассылка", callback_data="admin_group_post"),
        InlineKeyboardButton("👑 VIP управление", callback_data="admin_vip_list"),
        InlineKeyboardButton("✅ Вериф управление", callback_data="admin_verified_list"),
        InlineKeyboardButton("👥 Админы", callback_data="admin_admins_list"),
        InlineKeyboardButton("🚫 Баны", callback_data="admin_bans_list"),
        InlineKeyboardButton("📊 Статистика бота", callback_data="admin_stats"),
        InlineKeyboardButton("📈 Активность", callback_data="admin_activity"),
        InlineKeyboardButton("📋 Аудит действий", callback_data="admin_audit"),
        InlineKeyboardButton("👀 Поиск юзера", callback_data="admin_search_user"),
        InlineKeyboardButton("💾 Бэкап", callback_data="admin_backup_menu")
    )
    return markup

def admin_backup_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📤 Скачать бэкап", callback_data="admin_backup_save"),
        InlineKeyboardButton("📥 Загрузить бэкап", callback_data="admin_backup_load"),
        InlineKeyboardButton("📋 Список бэкапов", callback_data="admin_backup_list"),
        InlineKeyboardButton("◀️ Назад", callback_data="admin_main")
    )
    return markup

def admin_users_list_keyboard(users, prefix, back):
    markup = InlineKeyboardMarkup(row_width=1)
    for i, (uid, name) in enumerate(users[:10]):
        display = name if isinstance(name, str) else get_user_display_name(uid, hide_username=False)
        markup.add(InlineKeyboardButton(f"{i+1}. {display}", callback_data=f"{prefix}_{uid}"))
    markup.add(InlineKeyboardButton("◀️ Назад", callback_data=back))
    return markup

def admin_user_profile_keyboard(uid):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📈 +5% рейтинга", callback_data=f"admin_add_rating_{uid}_5"),
        InlineKeyboardButton("📈 -5% рейтинга", callback_data=f"admin_add_rating_{uid}_-5"),
        InlineKeyboardButton("🍀 +5% удачи", callback_data=f"admin_add_luck_{uid}_5"),
        InlineKeyboardButton("🍀 -5% удачи", callback_data=f"admin_add_luck_{uid}_-5"),
        InlineKeyboardButton("👑 Сделать VIP", callback_data=f"admin_make_vip_{uid}"),
        InlineKeyboardButton("✅ Сделать вериф", callback_data=f"admin_make_verified_{uid}"),
        InlineKeyboardButton("🚫 Забанить", callback_data=f"admin_ban_{uid}"),
        InlineKeyboardButton("◀️ Назад", callback_data="admin_search_user")
    )
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

def admin_posts_list_keyboard(posts):
    markup = InlineKeyboardMarkup(row_width=1)
    for i, post in enumerate(posts[:5]):
        short = post['text'][:30] + "..." if len(post['text']) > 30 else post['text']
        author = get_user_display_name(post['user_id'], hide_username=False)
        markup.add(InlineKeyboardButton(f"{i+1}. {author}: {short}", callback_data=f"admin_post_{post['id']}"))
    markup.add(InlineKeyboardButton("◀️ Назад", callback_data="admin_main"))
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

# ========== БЭКАПЫ (ТОЛЬКО ДЛЯ МАСТЕРА) ==========

@bot.message_handler(commands=['backupsave'])
def backup_save(message):
    user_id = message.from_user.id
    
    if not is_backup_allowed(user_id):
        bot.send_message(user_id, "🚫 Только для владельца бота")
        return
    
    try:
        with open(DATA_FILE, 'rb') as f:
            bot.send_document(
                user_id, 
                f, 
                visible_file_name=f'backup_{now_msk().strftime("%Y%m%d_%H%M%S")}.json',
                caption="✅ Бэкап базы данных"
            )
        log_admin_action(user_id, "Скачал бэкап")
    except Exception as e:
        bot.send_message(user_id, f"❌ Ошибка: {e}")

@bot.message_handler(commands=['backupload'])
def backup_upload_start(message):
    user_id = message.from_user.id
    
    if not is_backup_allowed(user_id):
        bot.send_message(user_id, "🚫 Только для владельца бота")
        return
    
    msg = bot.send_message(
        user_id,
        "📤 Отправь мне JSON-файл с бэкапом.\n"
        "❗ После загрузки текущие данные будут ЗАМЕНЕНЫ."
    )
    bot.register_next_step_handler(msg, receive_backup_file)

def safe_merge_data(old_data, new_data):
    """Безопасно объединяет старую и новую структуру данных"""
    merged = old_data.copy()
    
    # Копируем пользователей
    if "users" in new_data:
        merged["users"] = new_data["users"]
    
    # Копируем группы
    if "groups" in new_data:
        merged["groups"] = new_data["groups"]
    else:
        merged["groups"] = {}
    
    # Копируем посты
    if "posts" in new_data:
        merged["posts"] = new_data["posts"]
    
    # Копируем баны
    if "banned_users" in new_data:
        merged["banned_users"] = new_data["banned_users"]
    
    # Копируем админов (но мастер-админы защищены)
    if "admins" in new_data:
        merged["admins"] = list(set(new_data["admins"] + MASTER_ADMINS))
    
    # Копируем VIP
    if "vip_users" in new_data:
        merged["vip_users"] = new_data["vip_users"]
    
    # Копируем верифицированных
    if "verified_users" in new_data:
        merged["verified_users"] = new_data["verified_users"]
    
    # Копируем статистику
    if "stats" in new_data:
        merged["stats"] = new_data["stats"]
    
    # Копируем историю постов
    if "post_history" in new_data:
        merged["post_history"] = new_data["post_history"]
    
    if "post_contents" in new_data:
        merged["post_contents"] = new_data["post_contents"]
    
    if "post_reactions" in new_data:
        merged["post_reactions"] = new_data["post_reactions"]
    
    return merged

def receive_backup_file(message):
    user_id = message.from_user.id
    
    if not is_backup_allowed(user_id):
        return
    
    if message.document:
        file_info = bot.get_file(message.document.file_id)
        
        if not message.document.file_name.endswith('.json'):
            bot.send_message(user_id, "❌ Файл должен быть JSON")
            return
        
        downloaded_file = bot.download_file(file_info.file_path)
        
        try:
            new_data = json.loads(downloaded_file.decode('utf-8'))
            
            if "users" not in new_data:
                bot.send_message(user_id, "❌ Непохоже на файл базы данных")
                return
            
            # Делаем бэкап текущей базы
            temp_backup = DATA_FILE + ".pre_restore"
            if os.path.exists(DATA_FILE):
                os.replace(DATA_FILE, temp_backup)
            
            # Безопасно объединяем данные
            global data
            data = safe_merge_data(data, new_data)
            
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            bot.send_message(
                user_id,
                f"✅ База восстановлена!\n"
                f"👥 Пользователей: {len(data['users'])}\n"
                f"👥 Групп: {len(data.get('groups', {}))}\n"
                f"📝 Постов в очереди: {len(data['posts'])}"
            )
            log_admin_action(user_id, "Восстановил базу из бэкапа")
            
        except json.JSONDecodeError:
            bot.send_message(user_id, "❌ Файл повреждён (не JSON)")
        except Exception as e:
            bot.send_message(user_id, f"❌ Ошибка: {e}")
            if os.path.exists(temp_backup):
                os.replace(temp_backup, DATA_FILE)
                load_data()
    else:
        bot.send_message(user_id, "❌ Отправь файл, а не текст")

# ========== ОБРАБОТЧИКИ КОМАНД ==========

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    
    if message.chat.type != 'private':
        # Бота добавили в группу
        if message.chat.type in ['group', 'supergroup']:
            group = get_group(message.chat.id)
            update_group_info(message.chat)
            bot.reply_to(message, "✅ Бот добавлен в группу! Теперь админы могут делать рассылки по группам.")
        return
    
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
                            f"👤 {get_user_display_name(user_id, hide_username=False)}\n"
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
        "👑 <b>АДМИН-ПАНЕЛЬ</b>\n\nВыбери раздел:",
        parse_mode="HTML",
        reply_markup=admin_main_keyboard()
    )
    log_admin_action(user_id, "Вошёл в админ-панель")

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
    
    status = f"🎰 <b>КАЗИНО LOWHIGH</b>\n\n"
    status += f"🍀 Твой шанс на победу: {user['luck']:.2f}%\n"
    
    if user.get("quest_bonus_ready"):
        status += f"🔥 Бонус +20% за квесты готов!\n"
    
    if can_play:
        status += f"\n✅ Можно играть! Нажми кнопку ниже."
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
        bot.send_message(user_id, f"⏳ Жди ещё {format_time(cooldown)}", reply_markup=casino_keyboard())
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
            result = f"🎉 <b>ПОБЕДА!</b>\n\nТы выиграл: <b>{item}</b>!"
        else:
            user["rating"] = min(95.0, user["rating"] + 5.0)
            result = f"🎉 <b>ПОБЕДА!</b>\n\n+5% к рейтингу (предмет уже есть)"
        
        user["total_wins"] += 1
        user["fail_counter"] = 0
        data["stats"]["total_wins"] += 1
        update_quest_progress(user_id, "casino_win", 1)
    else:
        user["fail_counter"] += 1
        inc = user["fail_counter"] * 0.01
        user["luck"] = min(50.0, user["luck"] + inc)
        result = f"😢 <b>ПРОИГРЫШ</b>\n\nУдача +{inc:.2f}% → {user['luck']:.2f}%\nРейтинг: {old_rating:.1f}% → {user['rating']:.1f}%"
    
    user["last_casino"] = format_msk_time(datetime.now())
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
    text = "🏆 <b>ТОП-10 ПО РЕЙТИНГУ</b>\n\n"
    
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
В главном меню есть кнопки для всех функций.

<b>👑 Админ-команды:</b>
/admin - Панель администратора
/setrating @user 50 - изменить рейтинг
/setluck @user 25 - изменить удачу
/addadmin @user - назначить админа
/removeadmin @user - удалить админа
/addvip @user [дни] - выдать VIP
/vipinfo @user - инфо о VIP
/removevip @user - снять VIP
/addverified @user - верифицировать
/removeverified @user - снять верификацию
/ban @user - забанить
/unban @user - разбанить
/delpost ID - удалить пост у всех
/restime @user - сбросить КД
/profile @user - просмотр профиля
/backupsave - скачать бэкап базы (только для владельца)
/backupload - загрузить бэкап базы (только для владельца)
    """
    bot.send_message(message.from_user.id, help_text, parse_mode="HTML")

@bot.message_handler(commands=['convert'])
def cmd_convert(message):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        return
    
    user = get_user(user_id)
    
    if user.get("last_convert"):
        last = datetime.fromisoformat(user["last_convert"]) - timedelta(hours=3)
        if now_msk().date() == (last + timedelta(hours=3)).date():
            bot.send_message(user_id, "❌ Уже конвертил сегодня! Завтра будет новая попытка.")
            return
    
    if user["rating"] < 5.1:
        bot.send_message(user_id, "❌ Мало рейтинга! Нужно минимум 5.1%")
        return
    
    old_rating = user["rating"]
    old_luck = user["luck"]
    
    user["rating"] -= 5.0
    user["luck"] = min(50.0, user["luck"] + 1.0)
    user["last_convert"] = format_msk_time(datetime.now())
    save_data(data)
    
    bot.send_message(
        user_id,
        f"✅ <b>Конвертация выполнена!</b>\n\n"
        f"📈 Рейтинг: {old_rating:.1f}% → {user['rating']:.1f}%\n"
        f"🍀 Удача: {old_luck:.1f}% → {user['luck']:.1f}%",
        parse_mode="HTML"
    )

# ========== АДМИН-КОМАНДЫ ==========

@bot.message_handler(commands=['setrating'])
def set_rating(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "🚫 Не админ")
        return
    
    args = message.text.split()
    if len(args) < 3:
        bot.send_message(user_id, "❌ Использование: /setrating @user значение")
        return
    
    target_username = args[1]
    try:
        value = float(args[2])
    except:
        bot.send_message(user_id, "❌ Значение должно быть числом")
        return
    
    target_id = resolve_target(target_username, create_if_not_exists=True)
    if not target_id:
        bot.send_message(user_id, "❌ Пользователь не найден")
        return
    
    target = get_user(target_id)
    old = target["rating"]
    target["rating"] = max(5.0, min(95.0, value))
    if is_vip(target_id) or is_verified(target_id):
        target["rating"] = max(10.0, target["rating"])
    save_data(data)
    
    bot.send_message(
        user_id,
        f"✅ Рейтинг изменён\n"
        f"👤 {get_user_display_name(target_id, hide_username=False)}\n"
        f"📈 {old:.1f}% → {target['rating']:.1f}%"
    )
    log_admin_action(user_id, f"Изменил рейтинг", f"{get_user_display_name(target_id, hide_username=False)}: {old}% → {target['rating']}%")
    
    try:
        bot.send_message(
            int(target_id),
            f"👑 Админ изменил твой рейтинг\n"
            f"📈 {old:.1f}% → {target['rating']:.1f}%"
        )
    except:
        pass

@bot.message_handler(commands=['setluck'])
def set_luck(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "🚫 Не админ")
        return
    
    args = message.text.split()
    if len(args) < 3:
        bot.send_message(user_id, "❌ Использование: /setluck @user значение")
        return
    
    target_username = args[1]
    try:
        value = float(args[2])
    except:
        bot.send_message(user_id, "❌ Значение должно быть числом")
        return
    
    target_id = resolve_target(target_username, create_if_not_exists=True)
    if not target_id:
        bot.send_message(user_id, "❌ Пользователь не найден")
        return
    
    target = get_user(target_id)
    old = target["luck"]
    target["luck"] = max(1.0, min(50.0, value))
    save_data(data)
    
    bot.send_message(
        user_id,
        f"✅ Удача изменена\n"
        f"👤 {get_user_display_name(target_id, hide_username=False)}\n"
        f"🍀 {old:.1f}% → {target['luck']:.1f}%"
    )
    log_admin_action(user_id, f"Изменил удачу", f"{get_user_display_name(target_id, hide_username=False)}: {old}% → {target['luck']}%")
    
    try:
        bot.send_message(
            int(target_id),
            f"👑 Админ изменил твою удачу\n"
            f"🍀 {old:.1f}% → {target['luck']:.1f}%"
        )
    except:
        pass

@bot.message_handler(commands=['addadmin'])
def add_admin(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "🚫 Не админ")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(user_id, "❌ Использование: /addadmin @user")
        return
    
    target_username = args[1]
    target_id = resolve_target(target_username, create_if_not_exists=True)
    
    if not target_id:
        bot.send_message(user_id, "❌ Пользователь не найден")
        return
    
    if target_id not in data["admins"]:
        data["admins"].append(target_id)
        save_data(data)
        bot.send_message(
            user_id,
            f"✅ {get_user_display_name(target_id, hide_username=False)} назначен администратором"
        )
        log_admin_action(user_id, "Назначил админа", get_user_display_name(target_id, hide_username=False))
        try:
            bot.send_message(
                int(target_id),
                f"🎉 <b>Поздравляем!</b>\n\nТы стал администратором бота LowHigh!\nИспользуй /admin для входа в панель управления.",
                parse_mode="HTML"
            )
        except:
            pass
    else:
        bot.send_message(user_id, "⚠️ Уже администратор")

@bot.message_handler(commands=['removeadmin'])
def remove_admin(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "🚫 Не админ")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(user_id, "❌ Использование: /removeadmin @user")
        return
    
    target_username = args[1]
    target_id = resolve_target(target_username)
    
    if not target_id:
        bot.send_message(user_id, "❌ Пользователь не найден")
        return
    
    if target_id == str(user_id):
        bot.send_message(user_id, "❌ Нельзя удалить самого себя")
        return
    
    if target_id in [str(a) for a in MASTER_ADMINS]:
        bot.send_message(user_id, "❌ Нельзя удалить главного администратора")
        return
    
    if target_id in data["admins"]:
        data["admins"].remove(target_id)
        save_data(data)
        bot.send_message(
            user_id,
            f"✅ Администратор {get_user_display_name(target_id, hide_username=False)} удалён"
        )
        log_admin_action(user_id, "Удалил админа", get_user_display_name(target_id, hide_username=False))
        try:
            bot.send_message(
                int(target_id),
                f"❌ Твой статус администратора был удалён."
            )
        except:
            pass
    else:
        bot.send_message(user_id, "⚠️ Не администратор")

@bot.message_handler(commands=['addvip'])
def add_vip(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "🚫 Не админ")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(user_id, "❌ Использование: /addvip @user [дни]")
        return
    
    target_username = args[1]
    target_id = resolve_target(target_username, create_if_not_exists=True)
    
    if not target_id:
        bot.send_message(user_id, "❌ Пользователь не найден")
        return
    
    if len(args) >= 3:
        try:
            days = int(args[2])
        except:
            bot.send_message(user_id, "❌ Дни должны быть числом")
            return
        
        user = get_user(target_id)
        until = now_msk() + timedelta(days=days)
        user["vip_until"] = format_msk_time(until)
        check_and_fix_rating(target_id)
        save_data(data)
        bot.send_message(
            user_id,
            f"👑 VIP на {days} дней для {get_user_display_name(target_id, hide_username=False)}\nДействует до {until.strftime('%d.%m.%Y %H:%M')}"
        )
        log_admin_action(user_id, f"Выдал VIP на {days} дней", get_user_display_name(target_id, hide_username=False))
        try:
            bot.send_message(
                int(target_id),
                f"👑 <b>Поздравляем!</b>\n\nТы получил VIP статус на {days} дней!\nТвой рейтинг поднят до 10%",
                parse_mode="HTML"
            )
        except:
            pass
    else:
        if target_id not in data.get("vip_users", []):
            if "vip_users" not in data:
                data["vip_users"] = []
            data["vip_users"].append(target_id)
            check_and_fix_rating(target_id)
            save_data(data)
            bot.send_message(
                user_id,
                f"👑 Постоянный VIP для {get_user_display_name(target_id, hide_username=False)}"
            )
            log_admin_action(user_id, "Выдал постоянный VIP", get_user_display_name(target_id, hide_username=False))
            try:
                bot.send_message(
                    int(target_id),
                    f"👑 <b>Поздравляем!</b>\n\nТы получил постоянный VIP статус!\nТвой рейтинг поднят до 10%",
                    parse_mode="HTML"
                )
            except:
                pass
        else:
            bot.send_message(user_id, "⚠️ Уже VIP")

@bot.message_handler(commands=['vipinfo'])
def vipinfo(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "🚫 Не админ")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(user_id, "❌ Использование: /vipinfo @user")
        return
    
    target_username = args[1]
    target_id = resolve_target(target_username)
    
    if not target_id:
        bot.send_message(user_id, "❌ Пользователь не найден")
        return
    
    target = get_user(target_id)
    
    text = f"👑 <b>Информация о VIP</b>\n\n"
    text += f"👤 {get_user_display_name(target_id, hide_username=False)}\n"
    text += f"ID: {target_id}\n\n"
    
    if target.get("vip_until"):
        until = datetime.fromisoformat(target["vip_until"]) - timedelta(hours=3)
        if datetime.now() < until:
            left = until - datetime.now()
            text += f"Статус: ✅ активен\n"
            text += f"До: {(until + timedelta(hours=3)).strftime('%d.%m.%Y %H:%M')}\n"
            text += f"Осталось: {left.days} дн. {left.seconds//3600} ч."
        else:
            text += f"Статус: ❌ истёк\n"
            target["vip_until"] = None
            save_data(data)
    elif target_id in data.get("vip_users", []):
        text += f"Статус: ✅ постоянный VIP"
    else:
        text += f"Статус: ❌ не VIP"
    
    bot.send_message(user_id, text, parse_mode="HTML")

@bot.message_handler(commands=['removevip'])
def remove_vip(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "🚫 Не админ")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(user_id, "❌ Использование: /removevip @user")
        return
    
    target_username = args[1]
    target_id = resolve_target(target_username)
    
    if not target_id:
        bot.send_message(user_id, "❌ Пользователь не найден")
        return
    
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
        bot.send_message(
            user_id,
            f"✅ VIP статус удалён у {get_user_display_name(target_id, hide_username=False)}"
        )
        log_admin_action(user_id, "Снял VIP", get_user_display_name(target_id, hide_username=False))
        try:
            bot.send_message(
                int(target_id),
                f"❌ Твой VIP статус был удалён администратором."
            )
        except:
            pass
    else:
        bot.send_message(user_id, "⚠️ У пользователя нет VIP статуса")

@bot.message_handler(commands=['addverified'])
def add_verified(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "🚫 Не админ")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(user_id, "❌ Использование: /addverified @user")
        return
    
    target_username = args[1]
    target_id = resolve_target(target_username, create_if_not_exists=True)
    
    if not target_id:
        bot.send_message(user_id, "❌ Пользователь не найден")
        return
    
    if target_id not in data.get("verified_users", []):
        if "verified_users" not in data:
            data["verified_users"] = []
        data["verified_users"].append(target_id)
        check_and_fix_rating(target_id)
        save_data(data)
        bot.send_message(
            user_id,
            f"✅ {get_user_display_name(target_id, hide_username=False)} верифицирован"
        )
        log_admin_action(user_id, "Верифицировал", get_user_display_name(target_id, hide_username=False))
        try:
            bot.send_message(
                int(target_id),
                f"✅ <b>Поздравляем!</b>\n\nТы получил статус верифицированного пользователя!\nТвой рейтинг поднят до 10%",
                parse_mode="HTML"
            )
        except:
            pass
    else:
        bot.send_message(user_id, "⚠️ Уже верифицирован")

@bot.message_handler(commands=['removeverified'])
def remove_verified(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "🚫 Не админ")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(user_id, "❌ Использование: /removeverified @user")
        return
    
    target_username = args[1]
    target_id = resolve_target(target_username)
    
    if not target_id:
        bot.send_message(user_id, "❌ Пользователь не найден")
        return
    
    if target_id in data.get("verified_users", []):
        data["verified_users"].remove(target_id)
        save_data(data)
        bot.send_message(
            user_id,
            f"✅ Верификация снята с {get_user_display_name(target_id, hide_username=False)}"
        )
        log_admin_action(user_id, "Снял верификацию", get_user_display_name(target_id, hide_username=False))
        try:
            bot.send_message(
                int(target_id),
                f"❌ Твой статус верифицированного пользователя был снят."
            )
        except:
            pass
    else:
        bot.send_message(user_id, "⚠️ Не верифицирован")

@bot.message_handler(commands=['ban'])
def ban_user(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "🚫 Не админ")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(user_id, "❌ Использование: /ban @user")
        return
    
    target_username = args[1]
    target_id = resolve_target(target_username)
    
    if not target_id:
        bot.send_message(user_id, "❌ Пользователь не найден")
        return
    
    if target_id not in data["banned_users"]:
        data["banned_users"].append(target_id)
        save_data(data)
        bot.send_message(
            user_id,
            f"🚫 {get_user_display_name(target_id, hide_username=False)} забанен"
        )
        log_admin_action(user_id, "Забанил", get_user_display_name(target_id, hide_username=False))
        try:
            bot.send_message(
                int(target_id),
                f"🚫 Вы были забанены администратором."
            )
        except:
            pass
    else:
        bot.send_message(user_id, "⚠️ Уже в бане")

@bot.message_handler(commands=['unban'])
def unban_user(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "🚫 Не админ")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(user_id, "❌ Использование: /unban @user")
        return
    
    target_username = args[1]
    target_id = resolve_target(target_username)
    
    if not target_id:
        bot.send_message(user_id, "❌ Пользователь не найден")
        return
    
    if target_id in data["banned_users"]:
        data["banned_users"].remove(target_id)
        save_data(data)
        bot.send_message(
            user_id,
            f"✅ {get_user_display_name(target_id, hide_username=False)} разбанен"
        )
        log_admin_action(user_id, "Разбанил", get_user_display_name(target_id, hide_username=False))
        try:
            bot.send_message(
                int(target_id),
                f"✅ Вы были разбанены администратором."
            )
        except:
            pass
    else:
        bot.send_message(user_id, "⚠️ Не в бане")

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
        log_admin_action(user_id, "Удалил пост", f"ID {post_id}, у {deleted} юзеров")
    else:
        bot.send_message(
            user_id,
            f"❌ Пост не найден или уже удалён"
        )

@bot.message_handler(commands=['restime'])
def restime(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "🚫 Не админ")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(user_id, "❌ Использование: /restime @user")
        return
    
    target_username = args[1]
    target_id = resolve_target(target_username)
    
    if not target_id:
        bot.send_message(user_id, "❌ Пользователь не найден")
        return
    
    target = get_user(target_id)
    target["last_casino"] = None
    target["last_post_time"] = None
    save_data(data)
    
    bot.send_message(
        user_id,
        f"✅ КД сброшены для {get_user_display_name(target_id, hide_username=False)}"
    )
    log_admin_action(user_id, "Сбросил КД", get_user_display_name(target_id, hide_username=False))
    try:
        bot.send_message(
            int(target_id),
            f"🔄 Админ сбросил твои кулдауны!"
        )
    except:
        pass

@bot.message_handler(commands=['profile'])
def profile(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "🚫 Не админ")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(user_id, "❌ Использование: /profile @user")
        return
    
    target_username = args[1]
    target_id = resolve_target(target_username)
    
    if not target_id:
        bot.send_message(user_id, "❌ Пользователь не найден")
        return
    
    target = get_user(target_id)
    
    status = "Обычный"
    if is_vip(target_id):
        status = "👑 VIP"
    elif is_verified(target_id):
        status = "✅ Вериф"
    
    vip_info = ""
    if target.get("vip_until"):
        until = datetime.fromisoformat(target["vip_until"]) - timedelta(hours=3)
        if until > datetime.now():
            left = until - datetime.now()
            vip_info = f"\nVIP до: {(until + timedelta(hours=3)).strftime('%d.%m.%Y')} (осталось {left.days} дн.)"
    
    last_seen = "давно"
    if target.get("last_seen"):
        last = datetime.fromisoformat(target["last_seen"]) - timedelta(hours=3)
        delta = datetime.now() - last
        if delta.days > 0:
            last_seen = f"{delta.days} дн. назад"
        elif delta.seconds > 3600:
            last_seen = f"{delta.seconds//3600} ч. назад"
        else:
            last_seen = f"{delta.seconds//60} мин. назад"
    
    text = f"""
👤 <b>ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ</b>

👤 Имя: {get_user_display_name(target_id, hide_username=False)}
🆔 ID: {target_id}
📊 Статус: {status}{vip_info}

📈 Рейтинг: {target['rating']:.1f}%
🍀 Удача: {target['luck']:.2f}%
📻 Приём: {target['incoming_chance']}%

📝 Постов: {target['total_posts']}
🎰 Игр: {target['total_casino_attempts']}
🏆 Побед: {target['total_wins']}
👥 Рефералов: {len(target.get('referrals', []))}/{get_max_referrals(target_id)}

📅 Зарегистрирован: {target['join_date'][:10]}
🕐 Последний визит: {last_seen}
    """
    
    bot.send_message(user_id, text, parse_mode="HTML", reply_markup=admin_user_profile_keyboard(target_id))
    log_admin_action(user_id, "Просмотрел профиль", get_user_display_name(target_id, hide_username=False))

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
            bot.answer_callback_query(call.id, "⚠️ Жалоба отправлена")
            
            for admin_id in data.get("admins", []):
                if admin_id != user_id_str:
                    try:
                        text = f"""
⚠️ <b>ЖАЛОБА НА ПОСТ</b>

<b>ID поста:</b> {post_id}
<b>Автор:</b> {author_name} (ID: {author_id})
<b>От:</b> {get_user_display_name(user_id, hide_username=False)} (ID: {user_id})

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
            bot.answer_callback_query(call.id, "Вы уже жаловались")
        
        save_data(data)
        return
    
    elif data_cmd.startswith("global_delete_"):
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "Не админ")
            return
        
        post_id = data_cmd.split("_")[2]
        deleted = delete_post_globally(post_id)
        bot.answer_callback_query(call.id, f"🗑 Удалено у {deleted}")
        log_admin_action(user_id, "Удалил пост (кнопка)", f"ID {post_id}, у {deleted}")
        return
    
    # ===== АДМИНКА =====
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
    
    elif data_cmd == "admin_group_post":
        if not is_admin(user_id):
            return
        
        bot.edit_message_text(
            "👥 <b>ГРУППОВАЯ РАССЫЛКА</b>\n\n"
            "Отправь текст поста для рассылки по группам.\n"
            f"Всего групп: {len(data.get('groups', {}))}\n"
            f"Шанс доставки: 1% (5% для VIP)",
            user_id,
            call.message.message_id,
            parse_mode="HTML"
        )
        bot.register_next_step_handler_by_chat_id(user_id, receive_group_post)
    
    elif data_cmd == "admin_backup_menu":
        if not is_admin(user_id):
            return
        bot.edit_message_text(
            "💾 <b>УПРАВЛЕНИЕ БЭКАПАМИ</b>\n\n"
            "Выбери действие:",
            user_id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=admin_backup_keyboard()
        )
    
    elif data_cmd == "admin_backup_save":
        if not is_backup_allowed(user_id):
            bot.answer_callback_query(call.id, "❌ Только для владельца")
            return
        
        try:
            with open(DATA_FILE, 'rb') as f:
                bot.send_document(
                    user_id, 
                    f, 
                    visible_file_name=f'backup_{now_msk().strftime("%Y%m%d_%H%M%S")}.json',
                    caption="✅ Бэкап базы данных"
                )
            log_admin_action(user_id, "Скачал бэкап")
            bot.answer_callback_query(call.id, "✅ Бэкап отправлен")
        except Exception as e:
            bot.answer_callback_query(call.id, f"❌ Ошибка: {e}")
    
    elif data_cmd == "admin_backup_load":
        if not is_backup_allowed(user_id):
            bot.answer_callback_query(call.id, "❌ Только для владельца")
            return
        
        bot.edit_message_text(
            "📤 <b>ЗАГРУЗКА БЭКАПА</b>\n\n"
            "Отправь мне JSON-файл с бэкапом.\n"
            "❗ После загрузки текущие данные будут ЗАМЕНЕНЫ.",
            user_id,
            call.message.message_id,
            parse_mode="HTML"
        )
        bot.register_next_step_handler_by_chat_id(user_id, receive_backup_file)
    
    elif data_cmd == "admin_backup_list":
        if not is_admin(user_id):
            return
        
        text = "📋 <b>СПИСОК БЭКАПОВ</b>\n\n"
        text += "Автоматические бэкапы создаются при каждом сохранении.\n"
        text += f"Текущий файл: {DATA_FILE}\n"
        text += f"Размер: {os.path.getsize(DATA_FILE) if os.path.exists(DATA_FILE) else 0} байт\n\n"
        text += "Используй /backupsave для скачивания."
        
        bot.edit_message_text(
            text,
            user_id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("◀️ Назад", callback_data="admin_backup_menu")
            )
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
                author = get_user_display_name(post["user_id"], hide_username=False)
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
        
        if user.get("admin_notifications", True):
            bot.send_message(
                user_id,
                f"✅ <b>Пост одобрен</b>\n\n📊 Доставлено: {sent} пользователям"
            )
        
        try:
            bot.send_message(
                int(post_data["user_id"]),
                f"✅ <b>Твой пост одобрен и разослан!</b>\n\n📊 Доставлен {sent} пользователям."
            )
        except:
            pass
        
        log_admin_action(user_id, "Одобрил пост", f"ID {post_id}, доставлено {sent}")
        
        if data["posts"]:
            next_post = data["posts"][0]
            author = get_user_display_name(next_post["user_id"], hide_username=False)
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
                f"✅ Пост одобрен. Доставлено: {sent}\n\n📭 Больше нет постов.",
                user_id,
                call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("◀️ В админ-панель", callback_data="admin_main")
                )
            )
        
        bot.answer_callback_query(call.id, "✅ Одобрено")
    
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
                        f"🚫 {get_user_display_name(banned, hide_username=False)} забанен"
                    )
                    log_admin_action(user_id, "Забанил (из поста)", get_user_display_name(banned, hide_username=False))
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
                    f"📢 <b>Интерпол-рассылка выполнена</b>\n\n✅ Доставлено: {sent} пользователям",
                    user_id,
                    call.message.message_id,
                    parse_mode="HTML"
                )
                log_admin_action(user_id, "Интерпол-рассылка", f"доставлено {sent}")
                break
    
    elif data_cmd == "admin_interpol":
        if not is_admin(user_id):
            return
        
        bot.edit_message_text(
            "📢 <b>Интерпол-рассылка</b>\n\nОтправь текст поста для рассылки <b>ВСЕМ</b> пользователям:",
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
            if is_vip(uid):
                vip_list.append((uid, get_user_display_name(uid, hide_username=False)))
        
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
        
        target_id = data_cmd.split("_")[2]
        name = get_user_display_name(target_id, hide_username=False)
        text = f"👑 <b>VIP пользователь</b>\n\nID: {target_id}\nИмя: {name}"
        bot.edit_message_text(
            text,
            user_id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=admin_user_profile_keyboard(target_id)
        )
    
    elif data_cmd == "admin_verified_list":
        if not is_admin(user_id):
            return
        
        ver_list = [(uid, get_user_display_name(uid, hide_username=False)) for uid in data.get("verified_users", [])]
        
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
        
        target_id = data_cmd.split("_")[2]
        name = get_user_display_name(target_id, hide_username=False)
        text = f"✅ <b>Верифицированный пользователь</b>\n\nID: {target_id}\nИмя: {name}"
        bot.edit_message_text(
            text,
            user_id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=admin_user_profile_keyboard(target_id)
        )
    
    elif data_cmd == "admin_admins_list":
        if not is_admin(user_id):
            return
        
        adm_list = [(uid, get_user_display_name(uid, hide_username=False)) for uid in data.get("admins", [])]
        
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
        
        target_id = data_cmd.split("_")[2]
        name = get_user_display_name(target_id, hide_username=False)
        text = f"👥 <b>Администратор</b>\n\nID: {target_id}\nИмя: {name}"
        bot.edit_message_text(
            text,
            user_id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=admin_user_profile_keyboard(target_id)
        )
    
    elif data_cmd == "admin_bans_list":
        if not is_admin(user_id):
            return
        
        ban_list = [(uid, get_user_display_name(uid, hide_username=False)) for uid in data.get("banned_users", [])]
        
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
        
        target_id = data_cmd.split("_")[2]
        name = get_user_display_name(target_id, hide_username=False)
        text = f"🚫 <b>Забаненный пользователь</b>\n\nID: {target_id}\nИмя: {name}"
        bot.edit_message_text(
            text,
            user_id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=admin_user_profile_keyboard(target_id)
        )
    
    elif data_cmd == "admin_stats":
        if not is_admin(user_id):
            return
        
        total_users = len(data["users"])
        total_banned = len(data["banned_users"])
        total_admins = len(data.get("admins", []))
        total_groups = len(data.get("groups", {}))
        
        vip_cnt = 0
        for uid, u in data["users"].items():
            if is_vip(uid):
                vip_cnt += 1
        
        ver_cnt = len(data.get("verified_users", []))
        total_posts = data["stats"]["total_posts_sent"]
        total_games = data["stats"]["total_attempts"]
        total_wins = data["stats"]["total_wins"]
        
        today = now_msk().strftime("%Y-%m-%d")
        daily = data["stats"].get("daily_stats", {}).get(today, {"joins": 0, "posts": 0, "active": 0})
        
        text = f"""
📊 <b>СТАТИСТИКА БОТА</b>

👥 Всего пользователей: {total_users}
👥 Групп: {total_groups}
🚫 Забанено: {total_banned}
👑 VIP: {vip_cnt}
✅ Верифицировано: {ver_cnt}
👥 Админов: {total_admins}

📝 Всего постов: {total_posts}
🎰 Всего игр: {total_games}
🏆 Всего побед: {total_wins}

📅 <b>За сегодня ({today}):</b>
👥 Новых: {daily['joins']}
📝 Постов: {daily['posts']}
👀 Активных: {daily['active']}
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
        
        active_users = []
        for uid, u in data["users"].items():
            if uid not in data["banned_users"] and u.get("weekly_activity", 0) > 0:
                active_users.append({
                    "id": uid,
                    "name": get_user_display_name(uid, hide_username=False),
                    "activity": u.get("weekly_activity", 0)
                })
        
        top = sorted(active_users, key=lambda x: x["activity"], reverse=True)[:10]
        
        text = "📈 <b>АКТИВНОСТЬ ЗА НЕДЕЛЮ</b>\n\n"
        if not top:
            text += "Пока нет данных"
        else:
            for i, u in enumerate(top, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
                text += f"{medal} {i}. {u['name']} — {u['activity']} очков\n"
        
        bot.edit_message_text(
            text,
            user_id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("◀️ Назад", callback_data="admin_main")
            )
        )
    
    elif data_cmd == "admin_audit":
        if not is_admin(user_id):
            return
        
        text = "📋 <b>ПОСЛЕДНИЕ ДЕЙСТВИЯ АДМИНОВ</b>\n\n"
        if not audit_log:
            text += "Пока нет записей"
        else:
            for entry in audit_log[-10:]:
                text += f"[{entry['time']}] {entry['admin_name']}: {entry['action']} {entry['details']}\n"
        
        bot.edit_message_text(
            text,
            user_id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("◀️ Назад", callback_data="admin_main")
            )
        )
    
    elif data_cmd == "admin_search_user":
        if not is_admin(user_id):
            return
        
        bot.edit_message_text(
            "👀 <b>ПОИСК ПОЛЬЗОВАТЕЛЯ</b>\n\nВведи @username или ID пользователя:",
            user_id,
            call.message.message_id,
            parse_mode="HTML"
        )
        bot.register_next_step_handler_by_chat_id(user_id, admin_search_user)
    
    elif data_cmd.startswith("admin_add_rating_"):
        if not is_admin(user_id):
            return
        
        parts = data_cmd.split("_")
        target_id = parts[3]
        change = float(parts[4])
        
        target = get_user(target_id)
        if not target:
            bot.answer_callback_query(call.id, "Пользователь не найден")
            return
        
        old = target["rating"]
        target["rating"] = max(5.0, min(95.0, target["rating"] + change))
        if is_vip(target_id) or is_verified(target_id):
            target["rating"] = max(10.0, target["rating"])
        save_data(data)
        
        bot.answer_callback_query(call.id, f"Рейтинг изменён")
        bot.send_message(
            user_id,
            f"✅ Рейтинг {get_user_display_name(target_id, hide_username=False)}: {old:.1f}% → {target['rating']:.1f}%"
        )
        log_admin_action(user_id, f"Изменил рейтинг на {change:+.1f}%", get_user_display_name(target_id, hide_username=False))
    
    elif data_cmd.startswith("admin_add_luck_"):
        if not is_admin(user_id):
            return
        
        parts = data_cmd.split("_")
        target_id = parts[3]
        change = float(parts[4])
        
        target = get_user(target_id)
        if not target:
            bot.answer_callback_query(call.id, "Пользователь не найден")
            return
        
        old = target["luck"]
        target["luck"] = max(1.0, min(50.0, target["luck"] + change))
        save_data(data)
        
        bot.answer_callback_query(call.id, f"Удача изменена")
        bot.send_message(
            user_id,
            f"✅ Удача {get_user_display_name(target_id, hide_username=False)}: {old:.1f}% → {target['luck']:.1f}%"
        )
        log_admin_action(user_id, f"Изменил удачу на {change:+.1f}%", get_user_display_name(target_id, hide_username=False))
    
    elif data_cmd.startswith("admin_make_vip_"):
        if not is_admin(user_id):
            return
        
        target_id = data_cmd.split("_")[3]
        target = get_user(target_id)
        
        if not target:
            bot.answer_callback_query(call.id, "Пользователь не найден")
            return
        
        if target_id in data.get("vip_users", []):
            bot.answer_callback_query(call.id, "Уже VIP")
            return
        
        if "vip_users" not in data:
            data["vip_users"] = []
        data["vip_users"].append(target_id)
        check_and_fix_rating(target_id)
        save_data(data)
        
        bot.answer_callback_query(call.id, "VIP назначен")
        bot.send_message(
            user_id,
            f"👑 {get_user_display_name(target_id, hide_username=False)} теперь VIP"
        )
        log_admin_action(user_id, "Назначил VIP (кнопка)", get_user_display_name(target_id, hide_username=False))
    
    elif data_cmd.startswith("admin_make_verified_"):
        if not is_admin(user_id):
            return
        
        target_id = data_cmd.split("_")[3]
        target = get_user(target_id)
        
        if not target:
            bot.answer_callback_query(call.id, "Пользователь не найден")
            return
        
        if target_id in data.get("verified_users", []):
            bot.answer_callback_query(call.id, "Уже верифицирован")
            return
        
        if "verified_users" not in data:
            data["verified_users"] = []
        data["verified_users"].append(target_id)
        check_and_fix_rating(target_id)
        save_data(data)
        
        bot.answer_callback_query(call.id, "Верифицирован")
        bot.send_message(
            user_id,
            f"✅ {get_user_display_name(target_id, hide_username=False)} теперь верифицирован"
        )
        log_admin_action(user_id, "Верифицировал (кнопка)", get_user_display_name(target_id, hide_username=False))
    
    elif data_cmd.startswith("admin_ban_"):
        if not is_admin(user_id):
            return
        
        target_id = data_cmd.split("_")[2]
        
        if target_id in data["banned_users"]:
            bot.answer_callback_query(call.id, "Уже в бане")
            return
        
        data["banned_users"].append(target_id)
        save_data(data)
        
        bot.answer_callback_query(call.id, "Забанен")
        bot.send_message(
            user_id,
            f"🚫 {get_user_display_name(target_id, hide_username=False)} забанен"
        )
        log_admin_action(user_id, "Забанил (кнопка)", get_user_display_name(target_id, hide_username=False))
    
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
                result = f"🎉 <b>ПОБЕДА!</b>\n\nТы выиграл: <b>{item}</b>!"
            else:
                user["rating"] = min(95.0, user["rating"] + 5.0)
                result = f"🎉 <b>ПОБЕДА!</b>\n\n+5% к рейтингу (предмет уже есть)"
            
            user["total_wins"] += 1
            user["fail_counter"] = 0
            data["stats"]["total_wins"] += 1
            update_quest_progress(user_id, "casino_win", 1)
        else:
            user["fail_counter"] += 1
            inc = user["fail_counter"] * 0.01
            user["luck"] = min(50.0, user["luck"] + inc)
            result = f"😢 <b>ПРОИГРЫШ</b>\n\nУдача +{inc:.2f}% → {user['luck']:.2f}%\nРейтинг: {old_rating:.1f}% → {user['rating']:.1f}%"
        
        user["last_casino"] = format_msk_time(datetime.now())
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
            f"📝 Отправь текст поста (максимум {max_len} символов):",
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
                text += f"   📈 {u['rating']:.1f}% | 🍀 {u['luck']:.1f}%\n"
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
            last = datetime.fromisoformat(user["last_convert"]) - timedelta(hours=3)
            if now_msk().date() == (last + timedelta(hours=3)).date():
                bot.answer_callback_query(call.id, "❌ Уже сегодня!")
                return
        if user["rating"] < 5.1:
            bot.answer_callback_query(call.id, "❌ Мало рейтинга (мин 5.1%)")
            return
        
        old_rating = user["rating"]
        old_luck = user["luck"]
        
        user["rating"] -= 5.0
        user["luck"] = min(50.0, user["luck"] + 1.0)
        user["last_convert"] = format_msk_time(datetime.now())
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
                until = datetime.fromisoformat(user["silencer_until"]) - timedelta(hours=3)
                if datetime.now() < until:
                    sil = f" (активен до {(until + timedelta(hours=3)).strftime('%H:%M')})"
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
                f"🍀 <b>Амулет использован!</b>\n\n📈 Рейтинг увеличен на 10%!\nТекущий рейтинг: {user['rating']:.1f}%",
                parse_mode="HTML",
                reply_markup=main_keyboard()
            )
        else:
            bot.answer_callback_query(call.id, "У тебя нет амулета")
    
    elif data_cmd == "activate_silencer":
        inv = user.get("inventory", {})
        if inv.get("silencer", 0) == 1 and not user.get("silencer_until"):
            until = now_msk() + timedelta(hours=8)
            user["silencer_until"] = format_msk_time(until)
            inv["silencer"] = 0
            user["inventory"] = inv
            save_data(data)
            bot.answer_callback_query(call.id, "🔇 Глушитель активирован")
            bot.send_message(
                user_id,
                f"🔇 <b>Глушитель активирован</b>\n\nТы не будешь получать чужие посты до {until.strftime('%H:%M')}.",
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
                "🔇 <b>Глушитель деактивирован</b>\n\nТеперь ты снова получаешь посты.",
                parse_mode="HTML",
                reply_markup=main_keyboard()
            )
        else:
            bot.answer_callback_query(call.id, "Глушитель не активен")
    
    elif data_cmd == "use_vippass":
        inv = user.get("inventory", {})
        if inv.get("vip_pass", 0) == 1:
            until = now_msk() + timedelta(days=3)
            user["vip_until"] = format_msk_time(until)
            inv["vip_pass"] = 0
            user["inventory"] = inv
            check_and_fix_rating(user_id)
            save_data(data)
            bot.answer_callback_query(call.id, "👑 VIP на 3 дня!")
            bot.send_message(
                user_id,
                f"👑 <b>VIP-пропуск использован!</b>\n\nТы получил VIP статус до {until.strftime('%d.%m.%Y %H:%M')}\n📈 Рейтинг поднят до 10%",
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
            "time": format_msk_time(datetime.now())
        }
        
        user["last_post_time"] = format_msk_time(datetime.now())
        user["posts_count"] = user.get("posts_count", 0) + 1
        
        sent = send_post_to_users(new_post, user_id)
        user["total_posts"] += 1
        save_data(data)
        
        total_users = len(data["users"]) - 1
        percent = (sent / total_users * 100) if total_users > 0 else 0
        
        bot.send_message(
            user_id,
            f"✅ <b>Пост повторно разослан!</b>\n\n📊 Доставлено: {sent} пользователям\n📈 Процент доставки: {percent:.1f}%",
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
                f"🗑 <b>Пост удалён</b>\n\nУдалено у {deleted} пользователей.",
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
            "📞 <b>ГОРЯЧАЯ ЛИНИЯ</b>\n\nНапиши сообщение для администраторов.\nОни ответят тебе в личку как только смогут.\n\n⚠️ Используй эту функцию только по делу!",
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

📊 <b>Версия бота:</b> 5.0
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
            f"❌ Пост слишком длинный! Максимум {max_len} символов.\nУ тебя: {len(message.text)} символов",
            reply_markup=main_keyboard()
        )
        return
    
    text = censor_text(message.text, user_id)
    
    post = {
        "id": int(time.time() * 1000),
        "user_id": str(user_id),
        "username": user.get("username"),
        "text": text,
        "time": format_msk_time(datetime.now())
    }
    
    user["last_post_time"] = format_msk_time(datetime.now())
    user["posts_count"] = user.get("posts_count", 0) + 1
    
    update_quest_progress(user_id, "post", 1)
    if len(text) > 200:
        update_quest_progress(user_id, "post_length", 200, extra=len(text))
    
    if is_admin(user_id) or is_verified(user_id):
        sent = send_post_to_users(post, user_id)
        bot.send_message(
            user_id,
            f"✅ <b>Пост мгновенно разослан!</b>\n\n📊 Доставлено: {sent} пользователям",
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
            f"✅ <b>Пост отправлен на модерацию!</b>\n\nКак только администратор одобрит, он уйдёт в рассылку.",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )
        
        print_log("POST", f"Новый пост от {get_user_display_name(user_id, hide_username=False)}")
        
        for admin_id in data.get("admins", []):
            if admin_id != str(user_id):
                admin = get_user(admin_id)
                if admin and admin.get("admin_notifications", True):
                    try:
                        bot.send_message(
                            int(admin_id),
                            f"🆕 <b>Новый пост от {get_user_display_name(user_id, hide_username=False)}!</b>\n/admin - для модерации",
                            parse_mode="HTML"
                        )
                    except:
                        pass

def receive_group_post(message):
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
    
    if not data.get("groups"):
        bot.send_message(
            user_id,
            "😢 Нет групп для рассылки",
            reply_markup=admin_main_keyboard()
        )
        return
    
    text = message.text
    
    post = {
        "id": int(time.time() * 1000),
        "user_id": str(user_id),
        "username": user.get("username"),
        "text": text,
        "time": format_msk_time(datetime.now())
    }
    
    sent = send_post_to_groups(post, user_id)
    
    bot.send_message(
        user_id,
        f"👥 <b>Групповая рассылка выполнена!</b>\n\n✅ Доставлено в {sent} групп",
        parse_mode="HTML",
        reply_markup=admin_main_keyboard()
    )
    log_admin_action(user_id, "Групповая рассылка", f"доставлено в {sent} групп")

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
            f"❌ <b>Твой пост отклонён</b>\n\n📝 <b>Причина:</b> {reason}\n\nНе расстраивайся, попробуй ещё раз!",
            parse_mode="HTML"
        )
    except:
        pass
    
    bot.send_message(
        user_id,
        f"❌ <b>Пост отклонён</b>\n\nПричина отправлена автору.",
        parse_mode="HTML"
    )
    log_admin_action(user_id, "Отклонил пост", f"Причина: {reason}")
    
    if data["posts"]:
        next_post = data["posts"][0]
        author = get_user_display_name(next_post["user_id"], hide_username=False)
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
            "time": format_msk_time(datetime.now())
        }
        
        sent = send_post_to_users(post, user_id, force_all=True)
        bot.send_message(
            user_id,
            f"📢 <b>Интерпол-рассылка выполнена!</b>\n\n✅ Доставлено: {sent} пользователям",
            parse_mode="HTML",
            reply_markup=admin_main_keyboard()
        )
        log_admin_action(user_id, "Интерпол-рассылка", f"доставлено {sent}")

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
    
    user["last_hotline"] = format_msk_time(datetime.now())
    save_data(data)
    
    text = f"""
📞 <b>ГОРЯЧАЯ ЛИНИЯ</b>

<b>От:</b> {get_user_display_name(user_id, hide_username=False)} (ID: {user_id})
<b>Время:</b> {format_msk_time(datetime.now())}

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
        "✅ <b>Сообщение отправлено администраторам!</b>\n\nОни ответят тебе в личку в ближайшее время.",
        parse_mode="HTML",
        reply_markup=main_keyboard()
    )

def admin_search_user(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    query = message.text.strip()
    target_id = resolve_target(query)
    
    if not target_id:
        bot.send_message(
            user_id,
            "❌ Пользователь не найден",
            reply_markup=admin_main_keyboard()
        )
        return
    
    target = get_user(target_id)
    
    status = "Обычный"
    if is_vip(target_id):
        status = "👑 VIP"
    elif is_verified(target_id):
        status = "✅ Вериф"
    
    vip_info = ""
    if target.get("vip_until"):
        until = datetime.fromisoformat(target["vip_until"]) - timedelta(hours=3)
        if until > datetime.now():
            left = until - datetime.now()
            vip_info = f"\nVIP до: {(until + timedelta(hours=3)).strftime('%d.%m.%Y')} (осталось {left.days} дн.)"
    
    last_seen = "давно"
    if target.get("last_seen"):
        last = datetime.fromisoformat(target["last_seen"]) - timedelta(hours=3)
        delta = datetime.now() - last
        if delta.days > 0:
            last_seen = f"{delta.days} дн. назад"
        elif delta.seconds > 3600:
            last_seen = f"{delta.seconds//3600} ч. назад"
        else:
            last_seen = f"{delta.seconds//60} мин. назад"
    
    text = f"""
👤 <b>ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ</b>

👤 Имя: {get_user_display_name(target_id, hide_username=False)}
🆔 ID: {target_id}
📊 Статус: {status}{vip_info}

📈 Рейтинг: {target['rating']:.1f}%
🍀 Удача: {target['luck']:.2f}%
📻 Приём: {target['incoming_chance']}%

📝 Постов: {target['total_posts']}
🎰 Игр: {target['total_casino_attempts']}
🏆 Побед: {target['total_wins']}
👥 Рефералов: {len(target.get('referrals', []))}/{get_max_referrals(target_id)}

📅 Зарегистрирован: {target['join_date'][:10]}
🕐 Последний визит: {last_seen}
    """
    
    bot.send_message(
        user_id,
        text,
        parse_mode="HTML",
        reply_markup=admin_user_profile_keyboard(target_id)
    )
    log_admin_action(user_id, "Искал пользователя", get_user_display_name(target_id, hide_username=False))

# ========== ОБРАБОТЧИК ДОБАВЛЕНИЯ В ГРУППУ ==========

@bot.my_chat_member_handler()
def handle_group_join(update: ChatMemberUpdated):
    if update.new_chat_member.status in ['member', 'administrator']:
        # Бота добавили в группу
        chat = update.chat
        if chat.type in ['group', 'supergroup']:
            group = get_group(chat.id)
            update_group_info(chat)
            print_log("GROUP", f"Бот добавлен в группу {chat.title} (ID: {chat.id})")

# ========== ФОНОВЫЕ ЗАДАЧИ ==========

def background_tasks():
    last_tax = None
    last_reset = None
    
    while True:
        time.sleep(60)
        now = now_msk()
        now_utc = datetime.now()
        
        # Налог раз в сутки (по МСК)
        if not last_tax or now.date() > last_tax.date():
            apply_rating_tax()
            last_tax = now
        
        # Сброс активности в субботу (по МСК)
        if now.weekday() == 5 and (not last_reset or last_reset.date() != now.date()):
            for u in data["users"].values():
                u["weekly_activity"] = 0
                u["weekly_posts"] = 0
                u["weekly_likes"] = 0
            print_log("INFO", "Еженедельная активность сброшена")
            last_reset = now
            save_data(data)
        
        if now_utc.minute % 5 == 0:
            save_data(data)

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    print(f"{Colors.BOLD}{Colors.HEADER}")
    print("="*50)
    print("     LowHigh v5.0")
    print("="*50)
    print(f"{Colors.END}")
    
    print_log("INFO", f"Мастер-админы: {MASTER_ADMINS}")
    print_log("INFO", f"Мастер-бэкапов: {MASTER_BACKUP}")
    print_log("INFO", f"Всего админов: {len(data.get('admins', []))}")
    print_log("INFO", f"Всего юзеров: {len(data['users'])}")
    print_log("INFO", f"Всего групп: {len(data.get('groups', {}))}")
    print_log("INFO", f"Постов в очереди: {len(data['posts'])}")
    print_log("INFO", f"Файл базы: {DATA_FILE}")
    print_log("INFO", "Бот запущен...")
    
    threading.Thread(target=background_tasks, daemon=True).start()
    
    while True:
        try:
            bot.infinity_polling()
        except Exception as e:
            print_log("ERROR", f"Критическая ошибка: {e}")
            print_log("INFO", "Перезапуск через 10 секунд...")
            time.sleep(10)
