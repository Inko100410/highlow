# main.py — Рекламное Казино v2.0
# Все твои 7 пунктов выполнены!

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import random
import time
import json
import os
from datetime import datetime, timedelta
import threading

# ========== НАСТРОЙКИ ==========
TOKEN = "ТОКЕН_БОТА_СЮДА"

# Админы и модераторы (ты и подруга)
ADMIN_IDS = [6656110482, 123456789]  # ВСТАВЬ СВОЙ ID ВМЕСТО 123456789!

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
    """Красивый вывод в консоль"""
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
        "banned_users": [],  # список забаненных ID
        "stats": {
            "total_attempts": 0,
            "total_wins": 0,
            "total_stars_given": 0,
            "total_posts_sent": 0
        }
    }

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print_log("INFO", "Данные сохранены")

data = load_data()
bot = telebot.TeleBot(TOKEN)

# ========== РАБОТА С ПОЛЬЗОВАТЕЛЯМИ ==========

def get_user(user_id):
    user_id = str(user_id)
    
    # Проверка на бан
    if user_id in data["banned_users"]:
        return None
    
    if user_id not in data["users"]:
        data["users"][user_id] = {
            "rating": 5.0,           # Стартовый шанс на пост 5% (пункт 5)
            "luck": 1.0,
            "stars": 0,
            "reputation": 0,
            "fail_counter": 0,
            "incoming_chance": 50.0,  # % получения чужих постов
            "last_casino": None,
            "last_daily_choice": None,
            "referrals": [],
            "referrer": None,
            "total_posts": 0,
            "total_casino_attempts": 0,
            "total_wins": 0,
            "username": None,
            "join_date": datetime.now().isoformat()
        }
        print_log("SUCCESS", f"Новый пользователь! ID: {user_id}")
        save_data(data)
    return data["users"][user_id]

# ========== ПРИВЕТСТВИЕ (пункт 6) ==========

WELCOME_TEXT = """
🎩 <b>РЕКЛАМНОЕ КАЗИНО</b> 🎰

<b>Что это?</b>
Два в одном: рекламная сеть + лотерея.

<b>📝 Реклама:</b>
Пишешь пост → он уходит в рассылку.
Шанс доставки зависит от твоего рейтинга и удачи.
Каждый пост = -1% удачи.

<b>🎰 Казино:</b>
Крутишь ручку → шанс выиграть 15 ⭐ (≈25₽).
Проиграл? Шанс растет: 0.01% → 0.02% → 0.03%...
Каждая попытка = -1% рейтинга.

<b>⚖️ Баланс:</b>
Каждый день выбирай фокус:
• Игрок (+1% удачи, -5% рейтинга)
• Маркетолог (+5% рейтинга, -1% удачи)

<b>👥 Рефералы:</b>
Друг = +1% к удаче навсегда.

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

def is_banned(user_id):
    return str(user_id) in data["banned_users"]

# ========== РАССЫЛКА ПОСТОВ (пункты 1 и 2) ==========

def send_post_to_users(post, admin_id):
    """Умная рассылка: 1% гарантированно + остальные по шансу"""
    from_user_id = post["user_id"]
    author = get_user(from_user_id)
    
    if not author:
        print_log("ERROR", f"Автор {from_user_id} не найден или забанен")
        return 0
    
    # Собираем всех НЕзабаненных пользователей, кроме автора
    all_recipients = []
    for uid, user_data in data["users"].items():
        if uid != from_user_id and uid not in data["banned_users"]:
            all_recipients.append((uid, user_data))
    
    if not all_recipients:
        print_log("WARNING", "Нет получателей для рассылки")
        bot.send_message(int(from_user_id), "😢 Пока нет других пользователей для рассылки")
        return 0
    
    total_users = len(all_recipients)
    print_log("POST", f"Начинаем рассылку поста от @{post['username']}. Всего юзеров: {total_users}")
    
    # ===== ГАРАНТИРОВАННАЯ ЧАСТЬ (1% или минимум 1 человек) =====
    guaranteed_count = max(1, int(total_users * 0.01))  # 1% но не меньше 1
    print_log("POST", f"Гарантированная доставка: {guaranteed_count} чел")
    
    # Перемешиваем список, чтобы гарантированная часть была случайной
    random.shuffle(all_recipients)
    
    guaranteed_recipients = all_recipients[:guaranteed_count]
    chance_recipients = all_recipients[guaranteed_count:]
    
    sent_count = 0
    sent_to = []  # для статистики (пункт 2)
    
    # 1. Отправляем гарантированную часть
    for uid, user_data in guaranteed_recipients:
        try:
            bot.send_message(
                int(uid),
                f"📢 <b>Рекламный пост</b> от @{post['username']}:\n\n{post['text']}",
                parse_mode="HTML"
            )
            sent_count += 1
            sent_to.append(uid)
            
            # Автор получает +0.1% рейтинга за доставку
            author["rating"] = min(95.0, author["rating"] + 0.1)
            
            print_log("SUCCESS", f"Пост доставлен {uid} (гарантия)")
        except Exception as e:
            print_log("ERROR", f"Ошибка отправки {uid}: {e}")
    
    # 2. Отправляем остальным по шансу
    chance_hits = 0
    for uid, user_data in chance_recipients:
        # Шанс = шанс получателя + (рейтинг автора/2) + (удача автора/10)
        final_chance = (
            user_data["incoming_chance"] + 
            (author["rating"] / 2) + 
            (author["luck"] / 10)
        )
        final_chance = max(5, min(95, final_chance))  # ограничиваем
        
        if random.uniform(0, 100) <= final_chance:
            try:
                bot.send_message(
                    int(uid),
                    f"📢 <b>Рекламный пост</b> от @{post['username']}:\n\n{post['text']}",
                    parse_mode="HTML"
                )
                sent_count += 1
                chance_hits += 1
                sent_to.append(uid)
                
                # Автор получает +0.1% за каждую доставку
                author["rating"] = min(95.0, author["rating"] + 0.1)
                
            except Exception as e:
                print_log("ERROR", f"Ошибка отправки {uid}: {e}")
    
    # Статистика поста (пункт 2)
    post_stats = {
        "post_id": post["id"],
        "author": post["username"],
        "total_recipients": total_users,
        "guaranteed": guaranteed_count,
        "chance_hits": chance_hits,
        "total_sent": sent_count,
        "timestamp": datetime.now().isoformat(),
        "text_preview": post["text"][:50] + "..."
    }
    
    # Сохраняем статистику в отдельный файл (можно потом смотреть)
    stats_file = "post_stats.json"
    if os.path.exists(stats_file):
        with open(stats_file, 'r') as f:
            all_stats = json.load(f)
    else:
        all_stats = []
    
    all_stats.append(post_stats)
    with open(stats_file, 'w') as f:
        json.dump(all_stats, f, indent=2)
    
    # Логируем результат
    print_log("POST", f"✅ Пост доставлен {sent_count}/{total_users} юзерам (гарантия: {guaranteed_count}, шанс: {chance_hits})")
    
    # Уведомляем автора
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
    
    # Обновляем глобальную статистику
    data["stats"]["total_posts_sent"] += 1
    save_data(data)
    
    return sent_count

# ========== КЛАВИАТУРЫ ==========

def main_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📝 Написать пост", callback_data="write_post"),
        InlineKeyboardButton("🎰 Казино", callback_data="casino"),
        InlineKeyboardButton("👥 Рефералы", callback_data="referrals"),
        InlineKeyboardButton("📊 Статистика", callback_data="stats"),
        InlineKeyboardButton("⚖️ Фокус дня", callback_data="daily_choice"),
        InlineKeyboardButton("📻 Настройки", callback_data="settings")
    )
    return markup

def casino_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🎲 Дернуть ручку", callback_data="casino_spin"))
    markup.add(InlineKeyboardButton("◀️ Назад", callback_data="main_menu"))
    return markup

def settings_keyboard(user):
    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(
        InlineKeyboardButton("🔽 30%", callback_data="set_chance_30"),
        InlineKeyboardButton("⚖️ 50%", callback_data="set_chance_50"),
        InlineKeyboardButton("🔼 70%", callback_data="set_chance_70")
    )
    markup.add(
        InlineKeyboardButton("🔽 10%", callback_data="set_chance_10"),
        InlineKeyboardButton("⚖️ 90%", callback_data="set_chance_90"),
        InlineKeyboardButton("🔼 100%", callback_data="set_chance_100")
    )
    markup.add(InlineKeyboardButton("◀️ Назад", callback_data="main_menu"))
    return markup

def daily_choice_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🎰 Игрок (+1% удачи, -5% рейтинга)", callback_data="focus_casino"),
        InlineKeyboardButton("📝 Маркетолог (+5% рейтинга, -1% удачи)", callback_data="focus_marketing")
    )
    markup.add(InlineKeyboardButton("◀️ Назад", callback_data="main_menu"))
    return markup

def admin_keyboard(post_id):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{post_id}"),
        InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{post_id}"),
        InlineKeyboardButton("🚫 Забанить юзера", callback_data=f"ban_user_{post_id}"),
        InlineKeyboardButton("✅ Разбанить", callback_data=f"unban_user_{post_id}")
    )
    return markup

# ========== ОБРАБОТЧИКИ КОМАНД ==========

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    
    # Проверка на бан
    if is_banned(user_id):
        bot.send_message(user_id, "🚫 Вы забанены в этом боте.")
        return
    
    # Реферальная система
    args = message.text.split()
    if len(args) > 1:
        referrer_id = args[1]
        if referrer_id != str(user_id):
            user = get_user(user_id)
            if user and not user["referrer"]:
                user["referrer"] = referrer_id
                referrer = get_user(referrer_id)
                if referrer and str(user_id) not in referrer["referrals"]:
                    referrer["referrals"].append(str(user_id))
                    referrer["luck"] = min(50.0, referrer["luck"] + 1.0)
                    print_log("SUCCESS", f"Реферал: {user_id} от {referrer_id}")
                    save_data(data)
    
    user = get_user(user_id)
    if not user:
        return
    
    user["username"] = message.from_user.username
    save_data(data)
    
    # Приветствие + статистика
    welcome = WELCOME_TEXT + f"\n\n📈 Рейтинг: {user['rating']:.1f}%\n🍀 Удача: {user['luck']:.1f}%\n⭐ Звезды: {user['stars']}"
    bot.send_message(user_id, welcome, parse_mode="HTML", reply_markup=main_keyboard())
    print_log("INFO", f"Пользователь {user_id} зашел в бота")

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return
    
    if not data["posts"]:
        bot.send_message(user_id, "📭 Нет постов на модерации")
        return
    
    post = data["posts"][0]
    markup = admin_keyboard(post['id'])
    
    # Проверяем, забанен ли автор
    author_banned = post['user_id'] in data["banned_users"]
    status = "🚫 ЗАБАНЕН" if author_banned else "✅ Активен"
    
    bot.send_message(
        user_id,
        f"📝 <b>Пост на модерацию</b>\n"
        f"От: @{post['username']} (ID: {post['user_id']})\n"
        f"Статус автора: {status}\n"
        f"Текст:\n{post['text']}",
        parse_mode="HTML",
        reply_markup=markup
    )

# ========== ОБРАБОТЧИКИ КОЛЛБЭКОВ ==========

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    
    # Проверка на бан
    if is_banned(user_id) and call.data not in ["unban_user"]:
        bot.answer_callback_query(call.id, "Вы забанены", show_alert=True)
        return
    
    user = get_user(user_id)
    if not user and not is_banned(user_id):
        return
    
    data_cmd = call.data
    
    if data_cmd == "main_menu":
        bot.edit_message_text(
            "Главное меню:",
            user_id,
            call.message.message_id,
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
        
        bot.edit_message_text(
            status,
            user_id,
            call.message.message_id,
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
        
        # Уменьшаем рейтинг
        old_rating = user["rating"]
        user["rating"] = max(5.0, user["rating"] - 1.0)
        
        # Проверяем выигрыш
        roll = random.uniform(0, 100)
        won = roll <= user["luck"]
        
        print_log("CASINO", f"Юзер {user_id}: шанс {user['luck']:.2f}%, roll {roll:.2f}%, выигрыш: {won}")
        
        if won:
            stars_won = 15
            user["stars"] += stars_won
            user["total_wins"] += 1
            user["fail_counter"] = 0
            data["stats"]["total_wins"] += 1
            data["stats"]["total_stars_given"] += stars_won
            
            result_text = f"""
🎉 <b>ПОБЕДА!</b>

Ты выиграл {stars_won} ⭐
Баланс: {user['stars']} ⭐

Шанс был: {user['luck']:.2f}%
Рейтинг: {old_rating:.1f}% → {user['rating']:.1f}%
            """
        else:
            user["fail_counter"] += 1
            # Прогрессия: 0.01, 0.02, 0.03...
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
        bot.edit_message_text(
            "📝 Отправь мне текст поста (можно с картинкой):",
            user_id,
            call.message.message_id
        )
        bot.register_next_step_handler(call.message, receive_post)
    
    elif data_cmd == "referrals":
        ref_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
        ref_count = len(user["referrals"])
        
        text = f"""
👥 <b>РЕФЕРАЛЫ</b>

Приглашено: {ref_count} друзей
Каждый друг = +1% к удаче навсегда

Твоя ссылка:
<code>{ref_link}</code>

Отправь ее друзьям!
        """
        bot.edit_message_text(
            text,
            user_id,
            call.message.message_id,
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
⭐ Звезд: {user['stars']}
📻 Прием: {user['incoming_chance']}%

📝 Постов: {user['total_posts']}
🎰 Игр: {user['total_casino_attempts']}
🏆 Побед: {user['total_wins']}
👥 Рефералов: {len(user['referrals'])}

📊 <b>Глобально:</b>
Всего постов: {data['stats']['total_posts_sent']}
Выдано звезд: {data['stats']['total_stars_given']}
        """
        bot.edit_message_text(
            text,
            user_id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
            )
        )
    
    elif data_cmd == "settings":
        text = f"""
📻 <b>НАСТРОЙКИ ПРИЕМА</b>

Сейчас: {user['incoming_chance']}%

Чем выше %, тем больше рекламы ты видишь.
Чем ниже %, тем меньше спама.
        """
        bot.edit_message_text(
            text,
            user_id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=settings_keyboard(user)
        )
    
    elif data_cmd.startswith("set_chance_"):
        new_chance = int(data_cmd.split("_")[2])
        user["incoming_chance"] = float(new_chance)
        save_data(data)
        bot.answer_callback_query(call.id, f"Шанс приема = {new_chance}%")
        
        bot.edit_message_text(
            "✅ Настройки сохранены",
            user_id,
            call.message.message_id,
            reply_markup=main_keyboard()
        )
    
    elif data_cmd == "daily_choice":
        if user["last_daily_choice"]:
            last = datetime.fromisoformat(user["last_daily_choice"])
            if datetime.now().date() == last.date():
                bot.answer_callback_query(call.id, "Уже выбрал сегодня! Завтра снова", show_alert=True)
                return
        
        bot.edit_message_text(
            "⚖️ <b>ВЫБЕРИ ФОКУС ДНЯ</b>",
            user_id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=daily_choice_keyboard()
        )
    
    elif data_cmd == "focus_casino":
        old_luck = user["luck"]
        old_rating = user["rating"]
        
        user["luck"] = min(50.0, user["luck"] + 1.0)
        user["rating"] = max(5.0, user["rating"] - 5.0)
        user["last_daily_choice"] = datetime.now().isoformat()
        save_data(data)
        
        bot.edit_message_text(
            f"✅ <b>Фокус: КАЗИНО</b>\n\n"
            f"Удача: {old_luck:.1f}% → {user['luck']:.1f}%\n"
            f"Рейтинг: {old_rating:.1f}% → {user['rating']:.1f}%",
            user_id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )
    
    elif data_cmd == "focus_marketing":
        old_luck = user["luck"]
        old_rating = user["rating"]
        
        user["rating"] = min(95.0, user["rating"] + 5.0)
        user["luck"] = max(1.0, user["luck"] - 1.0)
        user["last_daily_choice"] = datetime.now().isoformat()
        save_data(data)
        
        bot.edit_message_text(
            f"✅ <b>Фокус: РЕКЛАМА</b>\n\n"
            f"Рейтинг: {old_rating:.1f}% → {user['rating']:.1f}%\n"
            f"Удача: {old_luck:.1f}% → {user['luck']:.1f}%",
            user_id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )
    
    # ===== АДМИН-ФУНКЦИИ (пункт 3) =====
    elif data_cmd.startswith("approve_"):
        if user_id not in ADMIN_IDS:
            return
        
        post_id = data_cmd.split("_")[1]
        for i, post in enumerate(data["posts"]):
            if str(post["id"]) == post_id:
                # Отправляем в рассылку
                sent = send_post_to_users(post, user_id)
                
                bot.send_message(
                    user_id,
                    f"✅ Пост одобрен. Доставлено: {sent} пользователям"
                )
                
                # Удаляем из очереди
                data["posts"].pop(i)
                save_data(data)
                
                # Если есть еще посты, показываем следующий
                if data["posts"]:
                    next_post = data["posts"][0]
                    markup = admin_keyboard(next_post['id'])
                    bot.send_message(
                        user_id,
                        f"📝 Следующий пост:\nОт @{next_post['username']}\n{next_post['text']}",
                        reply_markup=markup
                    )
                break
    
    elif data_cmd.startswith("reject_"):
        if user_id not in ADMIN_IDS:
            return
        
        post_id = data_cmd.split("_")[1]
        for i, post in enumerate(data["posts"]):
            if str(post["id"]) == post_id:
                bot.send_message(user_id, f"❌ Пост отклонен")
                data["posts"].pop(i)
                save_data(data)
                break
    
    elif data_cmd.startswith("ban_user_"):
        if user_id not in ADMIN_IDS:
            return
        
        post_id = data_cmd.split("_")[2]
        for post in data["posts"]:
            if str(post["id"]) == post_id:
                banned_id = post["user_id"]
                if banned_id not in data["banned_users"]:
                    data["banned_users"].append(banned_id)
                    bot.send_message(
                        user_id,
                        f"🚫 Пользователь {banned_id} (@{post['username']}) забанен"
                    )
                    print_log("WARNING", f"Забанен {banned_id}")
                    save_data(data)
                break
    
    elif data_cmd.startswith("unban_user_"):
        if user_id not in ADMIN_IDS:
            return
        
        post_id = data_cmd.split("_")[2]
        for post in data["posts"]:
            if str(post["id"]) == post_id:
                unbanned_id = post["user_id"]
                if unbanned_id in data["banned_users"]:
                    data["banned_users"].remove(unbanned_id)
                    bot.send_message(
                        user_id,
                        f"✅ Пользователь {unbanned_id} (@{post['username']}) разбанен"
                    )
                    print_log("INFO", f"Разбанен {unbanned_id}")
                    save_data(data)
                break

# ========== ПРИЕМ ПОСТОВ ==========

def receive_post(message):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        bot.send_message(user_id, "🚫 Вы забанены")
        return
    
    user = get_user(user_id)
    if not user:
        return
    
    if message.text:
        post = {
            "id": int(time.time() * 1000),
            "user_id": str(user_id),
            "username": user["username"],
            "text": message.text,
            "time": datetime.now().isoformat()
        }
        
        data["posts"].append(post)
        user["total_posts"] += 1
        user["luck"] = max(1.0, user["luck"] - 1.0)  # -1% удачи за пост
        save_data(data)
        
        bot.send_message(
            user_id,
            f"✅ Пост отправлен на модерацию!\n"
            f"Удача: {user['luck']:.1f}%\n"
            f"Как одобрят — уйдет в рассылку",
            reply_markup=main_keyboard()
        )
        
        print_log("POST", f"Новый пост от @{user['username']}: {message.text[:50]}...")
        
        # Уведомляем админов
        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(
                    admin_id,
                    f"🆕 Новый пост от @{user['username']}!\n/admin"
                )
            except:
                pass

# ========== АВТОСОХРАНЕНИЕ ==========

def auto_save():
    while True:
        time.sleep(300)  # 5 минут
        save_data(data)
        print_log("INFO", "Автосохранение выполнено")

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    print(f"{Colors.BOLD}{Colors.HEADER}")
    print("="*50)
    print("     РЕКЛАМНОЕ КАЗИНО v2.0")
    print("="*50)
    print(f"{Colors.END}")
    
    print_log("INFO", f"Админы: {ADMIN_IDS}")
    print_log("INFO", f"Всего юзеров: {len(data['users'])}")
    print_log("INFO", f"Постов в очереди: {len(data['posts'])}")
    print_log("INFO", "Бот запущен...")
    
    threading.Thread(target=auto_save, daemon=True).start()
    
    try:
        bot.infinity_polling()
    except Exception as e:
        print_log("ERROR", f"Критическая ошибка: {e}")
