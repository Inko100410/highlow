# main.py — LowHugh v2.1 (ИСПРАВЛЕНО)

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import random
import time
import json
import os
from datetime import datetime, timedelta
import threading

# ========== НАСТРОЙКИ ==========
TOKEN = "8265086577:AAFqojYbFSIRE2FZg0jnJ0Qgzdh0w9_j6z4"

# ТВОЙ ID - 8525294722
# ID подруги - 6656110482
MASTER_ADMINS = [6656110482, 8525294722]

bot = telebot.TeleBot(TOKEN)

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

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print_log("INFO", f"Загружено {len(data.get('users', {}))} пользователей")
            return data
    return {
        "users": {},
        "posts": [],
        "banned_users": [],
        "admins": MASTER_ADMINS.copy(),
        "vip_users": [],
        "verified_users": [],
        "post_history": {},
        "post_contents": {},  # Сохраняем текст поста для жалоб
        "stats": {
            "total_attempts": 0,
            "total_wins": 0,
            "total_posts_sent": 0
        },
        "post_reactions": {},
        "global_reactions": {}
    }

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print_log("INFO", "Данные сохранены")

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
            "referrals": [],
            "referrer": None,
            "total_posts": 0,
            "total_casino_attempts": 0,
            "total_wins": 0,
            "username": None,
            "first_name": None,
            "admin_notifications": True,
            "join_date": datetime.now().isoformat()
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
    user_id_str = str(user_id)
    if user_id_str in data.get("vip_users", []):
        return "👑"
    elif user_id_str in data.get("verified_users", []):
        return "✅"
    else:
        return "📝"

def get_max_referrals(user_id):
    user_id_str = str(user_id)
    if user_id_str in data.get("vip_users", []):
        return 50
    elif user_id_str in data.get("verified_users", []):
        return 25
    else:
        return 10

def get_post_cooldown(user_id):
    user_id_str = str(user_id)
    
    if user_id_str in data.get("vip_users", []):
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

def get_max_post_length(user_id):
    user_id_str = str(user_id)
    if user_id_str in data.get("vip_users", []):
        return 500
    elif user_id_str in data.get("verified_users", []):
        return 300
    else:
        return 250

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
    return str(user_id) in data.get("vip_users", [])

def is_verified(user_id):
    return str(user_id) in data.get("verified_users", [])

# ========== ПРИВЕТСТВИЕ ==========

WELCOME_TEXT = """
🎩 <b>LowHugh</b> 🎰

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

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}ч {minutes}м"

def check_casino_cooldown(user):
    if not user["last_casino"]:
        return True, 0
    last = datetime.fromisoformat(user["last_casino"])
    next_time = last + timedelta(hours=8)
    now = datetime.now()
    if now >= next_time:
        return True, 0
    return False, (next_time - now).total_seconds()

# ========== РАССЫЛКА ПОСТОВ С КНОПКАМИ ==========

def send_post_to_users(post, admin_id, force_all=False):
    from_user_id = post["user_id"]
    author = get_user(from_user_id)
    
    if not author:
        print_log("ERROR", f"Автор {from_user_id} не найден или забанен")
        return 0
    
    all_recipients = []
    for uid, user_data in data["users"].items():
        if uid != from_user_id and uid not in data["banned_users"]:
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
                f"📢 <b>Пост</b> {author_emoji} от {get_user_display_name(from_user_id)}:\n\n{post['text']}",
                parse_mode="HTML",
                reply_markup=markup
            )
            sent_count += 1
            author["rating"] = min(95.0, author["rating"] + 0.1)
            data["post_history"][str(post_id)][str(uid)] = sent_msg.message_id
            print_log("SUCCESS", f"Пост доставлен {uid} (гарантия)")
        except Exception as e:
            print_log("ERROR", f"Ошибка отправки {uid}: {e}")
    
    chance_hits = 0
    for uid, user_data in chance_recipients:
        if force_all:
            final_chance = 100
        else:
            final_chance = (
                user_data["incoming_chance"] + 
                (author["rating"] / 2) + 
                (author["luck"] / 10)
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
                    f"📢 <b>Пост</b> {author_emoji} от {get_user_display_name(from_user_id)}:\n\n{post['text']}",
                    parse_mode="HTML",
                    reply_markup=markup
                )
                sent_count += 1
                chance_hits += 1
                author["rating"] = min(95.0, author["rating"] + 0.1)
                data["post_history"][str(post_id)][str(uid)] = sent_msg.message_id
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
    save_data(data)
    
    return deleted_count

def update_post_reactions_buttons(post_id, chat_id, message_id):
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

# ========== КЛАВИАТУРЫ ==========

def main_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton("📝 Написать пост", callback_data="write_post"),
        InlineKeyboardButton("🎰 Бонус", callback_data="casino"),
        InlineKeyboardButton("👥 Рефералы", callback_data="referrals"),
        InlineKeyboardButton("📊 Статистика", callback_data="stats"),
        InlineKeyboardButton("🏆 Топ-10", callback_data="top"),
        InlineKeyboardButton("🔄 Конвертация", callback_data="convert")
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
    markup.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_post"))
    return markup

def admin_main_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📝 Посты на модерации", callback_data="admin_posts_list"),
        InlineKeyboardButton("📢 Интерпол-рассылка", callback_data="admin_interpol"),
        InlineKeyboardButton("👑 Управление VIP", callback_data="admin_vip"),
        InlineKeyboardButton("✅ Управление Вериф", callback_data="admin_verified"),
        InlineKeyboardButton("👥 Управление админами", callback_data="admin_admins"),
        InlineKeyboardButton("🚫 Управление банами", callback_data="admin_bans"),
        InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
        InlineKeyboardButton("🔔 Настройки уведомлений", callback_data="toggle_notify")
    )
    return markup

def admin_posts_list_keyboard(posts):
    markup = InlineKeyboardMarkup(row_width=1)
    for i, post in enumerate(posts[:5]):
        short_text = post['text'][:30] + "..." if len(post['text']) > 30 else post['text']
        markup.add(
            InlineKeyboardButton(f"{i+1}. {short_text}", callback_data=f"admin_post_{post['id']}")
        )
    markup.add(InlineKeyboardButton("◀️ Назад", callback_data="admin_main"))
    return markup

def admin_post_actions_keyboard(post_id):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{post_id}"),
        InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{post_id}"),
        InlineKeyboardButton("🚫 Забанить автора", callback_data=f"ban_user_{post_id}"),
        InlineKeyboardButton("📢 Интерпол", callback_data=f"interpol_{post_id}"),
        InlineKeyboardButton("◀️ К списку", callback_data="admin_posts_list")
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
    if user:
        user["first_name"] = message.from_user.first_name
    
    args = message.text.split()
    if len(args) > 1:
        referrer_id = args[1]
        if referrer_id != str(user_id):
            user = get_user(user_id)
            if user and not user["referrer"]:
                referrer = get_user(referrer_id)
                if referrer:
                    max_ref = get_max_referrals(referrer_id)
                    if len(referrer["referrals"]) < max_ref:
                        if str(user_id) not in referrer["referrals"]:
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
                            except:
                                pass
                    else:
                        try:
                            bot.send_message(
                                int(referrer_id),
                                f"❌ У тебя уже максимальное количество рефералов ({max_ref})"
                            )
                        except:
                            pass
    
    user = get_user(user_id)
    if not user:
        return
    
    user["username"] = message.from_user.username
    user["first_name"] = message.from_user.first_name
    save_data(data)
    
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
    
    max_len = get_max_post_length(user_id)
    bot.send_message(
        user_id,
        f"📝 Отправь текст поста (максимум {max_len} символов, только текст):",
        reply_markup=cancel_keyboard()
    )
    bot.register_next_step_handler(message, receive_post)

@bot.message_handler(commands=['casino'])
def cmd_casino(message):
    user_id = message.from_user.id
    if is_banned(user_id):
        return
    user = get_user(user_id)
    if not user:
        return
    
    can_play, cooldown = check_casino_cooldown(user)
    status = f"🎰 Твой шанс: {user['luck']:.2f}%\n"
    if can_play:
        status += "✅ Можно играть! Нажми /spin"
    else:
        status += f"⏳ Жди: {format_time(cooldown)}"
    bot.send_message(user_id, status)

@bot.message_handler(commands=['spin'])
def cmd_spin(message):
    user_id = message.from_user.id
    if is_banned(user_id):
        return
    user = get_user(user_id)
    if not user:
        return
    
    can_play, cooldown = check_casino_cooldown(user)
    if not can_play:
        bot.send_message(user_id, f"⏳ Подожди еще {format_time(cooldown)}")
        return
    
    old_rating = user["rating"]
    user["rating"] = max(5.0, user["rating"] - 1.0)
    
    roll = random.uniform(0, 100)
    won = roll <= user["luck"]
    
    if won:
        bonus = 10
        user["rating"] = min(95.0, user["rating"] + bonus)
        user["total_wins"] += 1
        user["fail_counter"] = 0
        data["stats"]["total_wins"] += 1
        
        result_text = f"""
🎉 <b>ПОБЕДА!</b>

Ты выиграл +{bonus}% к рейтингу!
Рейтинг: {old_rating:.1f}% → {user['rating']:.1f}%

Шанс был: {user['luck']:.2f}%
        """
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
    data["stats"]["total_attempts"] += 1
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

start - Запустить бота и показать главное меню
post - Написать пост для рассылки
casino - Информация о казино и текущем шансе
spin - Сделать крутку в казино (доступно раз в 8 часов)
top - Топ-10 игроков по рейтингу
convert - Обменять 5% рейтинга на 1% удачи (раз в 24ч)
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
    if not user:
        return
    
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
            "Пример: /setrating 123456789 50"
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
            "Пример: /setluck 123456789 25"
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
        
        if new_vip_id_str not in data.get("vip_users", []):
            if "vip_users" not in data:
                data["vip_users"] = []
            data["vip_users"].append(new_vip_id_str)
            save_data(data)
            bot.send_message(user_id, f"👑 Пользователь {new_vip_id} назначен VIP")
            
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
        bot.send_message(user_id, "❌ Неверный ID")

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
        
        if remove_id_str in data.get("vip_users", []):
            data["vip_users"].remove(remove_id_str)
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
            bot.send_message(user_id, "⚠️ Не VIP")
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
        
        if user_id_str in reactions["likes"]:
            reactions["likes"].remove(user_id_str)
            bot.answer_callback_query(call.id, "Лайк убран")
        else:
            if user_id_str in reactions["dislikes"]:
                reactions["dislikes"].remove(user_id_str)
            reactions["likes"].append(user_id_str)
            bot.answer_callback_query(call.id, "Лайк поставлен")
        
        save_data(data)
        update_post_reactions_buttons(post_id, call.message.chat.id, call.message.message_id)
        return
    
    elif data_cmd.startswith("dislike_"):
        post_id = data_cmd.split("_")[1]
        
        if str(post_id) not in data["post_reactions"]:
            data["post_reactions"][str(post_id)] = {"likes": [], "dislikes": [], "complaints": []}
        
        reactions = data["post_reactions"][str(post_id)]
        
        if user_id_str in reactions["dislikes"]:
            reactions["dislikes"].remove(user_id_str)
            bot.answer_callback_query(call.id, "Дизлайк убран")
        else:
            if user_id_str in reactions["likes"]:
                reactions["likes"].remove(user_id_str)
            reactions["dislikes"].append(user_id_str)
            bot.answer_callback_query(call.id, "Дизлайк поставлен")
        
        save_data(data)
        update_post_reactions_buttons(post_id, call.message.chat.id, call.message.message_id)
        return
    
    elif data_cmd.startswith("complaint_"):
        post_id = data_cmd.split("_")[1]
        
        # Получаем информацию о посте
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
            
            # Уведомляем админов о жалобе с текстом поста
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
    
    # ===== АДМИН-МЕНЮ (НЕ УДАЛЯЕМ СООБЩЕНИЯ) =====
    if data_cmd.startswith("admin_") or data_cmd in ["admin_main", "admin_posts_list", "approve_", "reject_", "ban_user_", "interpol_"]:
        # Не удаляем админские сообщения
        pass
    else:
        # Удаляем только обычные сообщения
        try:
            bot.delete_message(user_id, call.message.message_id)
        except:
            pass
    
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
        
        text = f"📝 <b>Посты на модерации ({len(data['posts'])}):</b>\n\n"
        bot.edit_message_text(
            text,
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
        for i, post in enumerate(data["posts"]):
            if str(post["id"]) == post_id:
                sent = send_post_to_users(post, user_id)
                
                bot.edit_message_text(
                    f"✅ Пост одобрен. Доставлено: {sent} пользователям",
                    user_id,
                    call.message.message_id
                )
                
                data["posts"].pop(i)
                save_data(data)
                break
    
    elif data_cmd.startswith("reject_"):
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "Не админ")
            return
        
        post_id = data_cmd.split("_")[1]
        for i, post in enumerate(data["posts"]):
            if str(post["id"]) == post_id:
                bot.edit_message_text(
                    f"❌ Пост отклонен",
                    user_id,
                    call.message.message_id
                )
                data["posts"].pop(i)
                save_data(data)
                break
    
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
    
    elif data_cmd == "toggle_notify":
        if is_admin(user_id):
            user["admin_notifications"] = not user.get("admin_notifications", True)
            save_data(data)
            bot.answer_callback_query(call.id, f"Уведомления: {'ВКЛ' if user['admin_notifications'] else 'ВЫКЛ'}")
    
    elif data_cmd == "main_menu":
        bot.send_message(
            user_id,
            "Главное меню:",
            reply_markup=main_keyboard()
        )
    
    elif data_cmd == "casino":
        can_play, cooldown = check_casino_cooldown(user)
        status = f"🎰 <b>КАЗИНО</b>\n\nТвой шанс: {user['luck']:.2f}%\n"
        
        if can_play:
            status += "✅ Можно играть!"
        else:
            status += f"⏳ Следующая попытка через: {format_time(cooldown)}"
        
        status += f"\n\n⚠️ Каждое вращение уменьшает рейтинг на 1%"
        status += f"\n\n💰 Выигрыш: +10% к рейтингу"
        
        bot.send_message(
            user_id,
            status,
            parse_mode="HTML",
            reply_markup=casino_keyboard()
        )
    
    elif data_cmd == "casino_spin":
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
        
        roll = random.uniform(0, 100)
        won = roll <= user["luck"]
        
        print_log("CASINO", f"Юзер {user_id}: шанс {user['luck']:.2f}%, roll {roll:.2f}%, выигрыш: {won}")
        
        if won:
            bonus = 10
            user["rating"] = min(95.0, user["rating"] + bonus)
            user["total_wins"] += 1
            user["fail_counter"] = 0
            data["stats"]["total_wins"] += 1
            
            result_text = f"""
🎉 <b>ПОБЕДА!</b>

Ты выиграл +{bonus}% к рейтингу!
Рейтинг: {old_rating:.1f}% → {user['rating']:.1f}%

Шанс был: {user['luck']:.2f}%
            """
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
        data["stats"]["total_attempts"] += 1
        save_data(data)
        
        bot.send_message(
            user_id,
            result_text,
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
        bot.send_message(
            user_id,
            f"📝 Отправь мне текст поста (максимум {max_len} символов, только текст):",
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
        
        ref_count = len(user["referrals"])
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
        
        text = f"""
📊 <b>ТВОЯ СТАТИСТИКА</b>

📈 Рейтинг: {user['rating']:.1f}%
🍀 Удача: {user['luck']:.2f}%
📻 Прием: {user['incoming_chance']}%
⏱ КД на пост: {get_post_cooldown(user_id)}ч

📝 Постов: {user['total_posts']}
🎰 Игр: {user['total_casino_attempts']}
🏆 Побед: {user['total_wins']}
👥 Рефералов: {len(user['referrals'])}/{get_max_referrals(user_id)}

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

# ========== ПРИЕМ ПОСТОВ ==========

def receive_post(message):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        bot.send_message(user_id, "🚫 Вы забанены")
        return
    
    user = get_user(user_id)
    if not user:
        return
    
    # ===== ПРОВЕРКА КД (ДОБАВИТЬ ЭТОТ БЛОК) =====
    can_post, cooldown = check_post_cooldown(user)
    if not can_post:
        bot.send_message(
            user_id, 
            f"⏳ Подожди еще {format_time(cooldown)} перед следующим постом",
            reply_markup=main_keyboard()
        )
        return
    # ===========================================
    
    if message.text and message.text.lower() in ["отмена", "cancel", "/cancel"]:
        bot.send_message(user_id, "❌ Отправка отменена", reply_markup=main_keyboard())
        return
        
        if len(message.text) > max_len:
            bot.send_message(
                user_id,
                f"❌ Пост слишком длинный! Максимум {max_len} символов.\n"
                f"У тебя: {len(message.text)} символов",
                reply_markup=main_keyboard()
            )
            return
        
        post = {
            "id": int(time.time() * 1000),
            "user_id": str(user_id),
            "username": user["username"],
            "text": message.text,
            "time": datetime.now().isoformat()
        }
        
        user["last_post_time"] = datetime.now().isoformat()
        user["posts_count"] = user.get("posts_count", 0) + 1
        
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
            
            print_log("POST", f"Новый пост от {get_user_display_name(user_id)}: {message.text[:50]}...")
            
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
    else:
        bot.send_message(user_id, "❌ Принимаем только текст без картинок")

def receive_interpol_post(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
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

# ========== АВТОСОХРАНЕНИЕ ==========

def auto_save():
    while True:
        time.sleep(300)
        save_data(data)
        print_log("INFO", "Автосохранение выполнено")

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    print(f"{Colors.BOLD}{Colors.HEADER}")
    print("="*50)
    print("     LowHugh v2.1")
    print("="*50)
    print(f"{Colors.END}")
    
    print_log("INFO", f"Мастер-админы: {MASTER_ADMINS}")
    print_log("INFO", f"Всего админов: {len(data.get('admins', []))}")
    print_log("INFO", f"VIP пользователей: {len(data.get('vip_users', []))}")
    print_log("INFO", f"Верифицированных: {len(data.get('verified_users', []))}")
    print_log("INFO", f"Всего юзеров: {len(data['users'])}")
    print_log("INFO", f"Постов в очереди: {len(data['posts'])}")
    print_log("INFO", "Бот запущен...")
    
    threading.Thread(target=auto_save, daemon=True).start()
    
    while True:
        try:
            bot.infinity_polling()
        except Exception as e:
            print_log("ERROR", f"Критическая ошибка: {e}")
            print_log("INFO", "Перезапуск через 10 секунд...")
            time.sleep(10)
