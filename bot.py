# main.py — Рекламное Казино v6.1 (ИСПРАВЛЕНО)

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
MASTER_ADMINS = [6656110482, 8525294722]  # Оба админа здесь!

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
        "stats": {
            "total_attempts": 0,
            "total_wins": 0,
            "total_posts_sent": 0
        },
        "post_reactions": {}  # {post_id: {"likes": [user_ids], "dislikes": [user_ids], "complaints": [user_ids]}}
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
    """Возвращает имя пользователя для отображения"""
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
Друг = +1% к удаче навсегда (макс 10 друзей)

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

def send_post_to_users(post, admin_id):
    """Умная рассылка: 1% гарантированно + остальные по шансу"""
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
    
    guaranteed_count = max(1, int(total_users * 0.01))
    print_log("POST", f"Гарантированная доставка: {guaranteed_count} чел")
    
    random.shuffle(all_recipients)
    
    guaranteed_recipients = all_recipients[:guaranteed_count]
    chance_recipients = all_recipients[guaranteed_count:]
    
    sent_count = 0
    post_id = post["id"]
    
    # Инициализируем реакции для поста
    if str(post_id) not in data["post_reactions"]:
        data["post_reactions"][str(post_id)] = {
            "likes": [],
            "dislikes": [],
            "complaints": []
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
            
            bot.send_message(
                int(uid),
                f"📢 <b>Пост</b> от {get_user_display_name(from_user_id)}:\n\n{post['text']}",
                parse_mode="HTML",
                reply_markup=markup
            )
            sent_count += 1
            author["rating"] = min(95.0, author["rating"] + 0.1)
            print_log("SUCCESS", f"Пост доставлен {uid} (гарантия)")
        except Exception as e:
            print_log("ERROR", f"Ошибка отправки {uid}: {e}")
    
    chance_hits = 0
    for uid, user_data in chance_recipients:
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
                
                bot.send_message(
                    int(uid),
                    f"📢 <b>Пост</b> от {get_user_display_name(from_user_id)}:\n\n{post['text']}",
                    parse_mode="HTML",
                    reply_markup=markup
                )
                sent_count += 1
                chance_hits += 1
                author["rating"] = min(95.0, author["rating"] + 0.1)
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

def update_post_reactions_buttons(post_id, chat_id, message_id):
    """Обновляет кнопки с актуальными счетчиками реакций"""
    reactions = data["post_reactions"].get(str(post_id), {"likes": [], "dislikes": [], "complaints": []})
    likes_count = len(reactions["likes"])
    dislikes_count = len(reactions["dislikes"])
    
    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(
        InlineKeyboardButton(f"👍 {likes_count}", callback_data=f"like_{post_id}"),
        InlineKeyboardButton(f"👎 {dislikes_count}", callback_data=f"dislike_{post_id}"),
        InlineKeyboardButton("⚠️", callback_data=f"complaint_{post_id}")
    )
    
    # Проверяем, админ ли тот, кто видит это сообщение (сложно, поэтому пропускаем)
    # Кнопка удаления будет только при отправке нового поста
    
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

def admin_keyboard(post_id):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{post_id}"),
        InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{post_id}"),
        InlineKeyboardButton("🚫 Забанить", callback_data=f"ban_user_{post_id}"),
        InlineKeyboardButton("✅ Разбанить", callback_data=f"unban_user_{post_id}"),
        InlineKeyboardButton("🔔 Уведомления", callback_data="toggle_notify")
    )
    return markup

def cancel_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_post"))
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
                    if len(referrer["referrals"]) < 10:
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
                                    f"Рефералов: {len(referrer['referrals'])}/10"
                                )
                            except:
                                pass
                    else:
                        try:
                            bot.send_message(
                                int(referrer_id),
                                f"❌ У тебя уже максимальное количество рефералов (10)"
                            )
                        except:
                            pass
    
    user = get_user(user_id)
    if not user:
        return
    
    user["username"] = message.from_user.username
    user["first_name"] = message.from_user.first_name
    save_data(data)
    
    welcome = WELCOME_TEXT + f"\n\n📈 Рейтинг: {user['rating']:.1f}%\n🍀 Удача: {user['luck']:.1f}%"
    bot.send_message(user_id, welcome, parse_mode="HTML", reply_markup=main_keyboard())
    print_log("INFO", f"Пользователь {user_id} зашел в бота")

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, f"🚫 У вас нет прав администратора. Ваш ID: {user_id}")
        return
    
    # Всегда показываем админ-панель, даже если нет постов
    text = "👑 <b>АДМИН-ПАНЕЛЬ</b>\n\n"
    
    if not data["posts"]:
        text += "📭 Нет постов на модерации"
        bot.send_message(user_id, text, parse_mode="HTML")
        return
    
    post = data["posts"][0]
    markup = admin_keyboard(post['id'])
    
    author_banned = post['user_id'] in data["banned_users"]
    status = "🚫 ЗАБАНЕН" if author_banned else "✅ Активен"
    
    bot.send_message(
        user_id,
        f"📝 <b>Пост на модерацию</b>\n"
        f"От: {get_user_display_name(post['user_id'])} (ID: {post['user_id']})\n"
        f"Статус автора: {status}\n"
        f"Текст:\n{post['text']}",
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.message_handler(commands=['post'])
def cmd_post(message):
    user_id = message.from_user.id
    if is_banned(user_id):
        bot.send_message(user_id, "🚫 Вы забанены")
        return
    
    bot.send_message(
        user_id,
        "📝 Отправь текст поста (только текст, картинки не принимаем):",
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

/start - Запустить бота
/post - Написать пост
/casino - Инфо о казино
/spin - Дернуть ручку (играть)
/top - Топ-10 игроков
/convert - Конвертировать 5% рейтинга в 1% удачи
/admin - Панель модератора (для админов)

<b>👑 Админ-команды:</b>
/setrating [ID] [знач] - установить рейтинг любому игроку
/setluck [ID] [знач] - установить удачу любому игроку
/addadmin [ID] - назначить админа
/removeadmin [ID] - удалить админа
    """
    bot.send_message(message.from_user.id, help_text, parse_mode="HTML")

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
        
        if str(post_id) not in data["post_reactions"]:
            data["post_reactions"][str(post_id)] = {"likes": [], "dislikes": [], "complaints": []}
        
        reactions = data["post_reactions"][str(post_id)]
        
        if user_id_str not in reactions["complaints"]:
            reactions["complaints"].append(user_id_str)
            bot.answer_callback_query(call.id, "Жалоба отправлена администратору")
            
            # Уведомляем админов о жалобе
            for admin_id in data.get("admins", []):
                if admin_id != user_id_str:
                    try:
                        bot.send_message(
                            int(admin_id),
                            f"⚠️ Жалоба на пост {post_id} от {get_user_display_name(user_id)}"
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
        
        # Ищем пост в истории или в очереди
        # В реальном посте нужно хранить ID сообщений у каждого пользователя
        # Это сложно, поэтому пока просто удаляем из очереди и уведомляем
        for i, post in enumerate(data["posts"]):
            if str(post["id"]) == post_id:
                data["posts"].pop(i)
                save_data(data)
                break
        
        bot.answer_callback_query(call.id, "Пост удален у всех пользователей")
        # В реальности нужно пройтись по всем чатам и удалить сообщения
        # Но это технически сложно без хранения message_id
        return
    
    try:
        bot.delete_message(user_id, call.message.message_id)
    except:
        pass
    
    if data_cmd == "main_menu":
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
        bot.send_message(
            user_id,
            "📝 Отправь мне текст поста (только текст, картинки не принимаем):",
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
        
        text = f"""
👥 <b>РЕФЕРАЛЫ</b>

Приглашено: {ref_count}/10 друзей
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
        text = f"""
📊 <b>ТВОЯ СТАТИСТИКА</b>

📈 Рейтинг: {user['rating']:.1f}%
🍀 Удача: {user['luck']:.2f}%
📻 Прием: {user['incoming_chance']}%

📝 Постов: {user['total_posts']}
🎰 Игр: {user['total_casino_attempts']}
🏆 Побед: {user['total_wins']}
👥 Рефералов: {len(user['referrals'])}/10

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
    
    elif data_cmd.startswith("approve_"):
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "Не админ")
            return
        
        post_id = data_cmd.split("_")[1]
        for i, post in enumerate(data["posts"]):
            if str(post["id"]) == post_id:
                sent = send_post_to_users(post, user_id)
                
                bot.send_message(
                    user_id,
                    f"✅ Пост одобрен. Доставлено: {sent} пользователям"
                )
                
                data["posts"].pop(i)
                save_data(data)
                
                if data["posts"]:
                    next_post = data["posts"][0]
                    markup = admin_keyboard(next_post['id'])
                    bot.send_message(
                        user_id,
                        f"📝 Следующий пост:\nОт {get_user_display_name(next_post['user_id'])}\n{next_post['text']}",
                        reply_markup=markup
                    )
                break
    
    elif data_cmd.startswith("reject_"):
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "Не админ")
            return
        
        post_id = data_cmd.split("_")[1]
        for i, post in enumerate(data["posts"]):
            if str(post["id"]) == post_id:
                bot.send_message(user_id, f"❌ Пост отклонен")
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
    
    elif data_cmd.startswith("unban_user_"):
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "Не админ")
            return
        
        post_id = data_cmd.split("_")[2]
        for post in data["posts"]:
            if str(post["id"]) == post_id:
                unbanned_id = post["user_id"]
                if unbanned_id in data["banned_users"]:
                    data["banned_users"].remove(unbanned_id)
                    bot.send_message(
                        user_id,
                        f"✅ Пользователь {unbanned_id} ({get_user_display_name(unbanned_id)}) разбанен"
                    )
                    print_log("INFO", f"Разбанен {unbanned_id}")
                    save_data(data)
                break
    
    elif data_cmd == "toggle_notify":
        if is_admin(user_id):
            user["admin_notifications"] = not user.get("admin_notifications", True)
            save_data(data)
            bot.answer_callback_query(call.id, f"Уведомления: {'ВКЛ' if user['admin_notifications'] else 'ВЫКЛ'}")

# ========== ПРИЕМ ПОСТОВ ==========

def receive_post(message):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        bot.send_message(user_id, "🚫 Вы забанены")
        return
    
    user = get_user(user_id)
    if not user:
        return
    
    if message.text and message.text.lower() in ["отмена", "cancel", "/cancel"]:
        bot.send_message(user_id, "❌ Отправка отменена", reply_markup=main_keyboard())
        return
    
    if message.text:
        post = {
            "id": int(time.time() * 1000),
            "user_id": str(user_id),
            "username": user["username"],
            "text": message.text,
            "time": datetime.now().isoformat()
        }
        
        if is_admin(user_id):
            sent = send_post_to_users(post, user_id)
            bot.send_message(
                user_id,
                f"✅ Пост мгновенно разослан!\nДоставлено: {sent} пользователям",
                reply_markup=main_keyboard()
            )
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
    print("     LowHugh v1.0")
    print("="*50)
    print(f"{Colors.END}")
    
    print_log("INFO", f"Мастер-админы: {MASTER_ADMINS}")
    print_log("INFO", f"Всего админов: {len(data.get('admins', []))}")
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
