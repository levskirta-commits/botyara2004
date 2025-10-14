import asyncio
import logging
import sqlite3
import random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

logging.basicConfig(level=logging.INFO)

# === Настройки ===
BOT_TOKEN = "7990184193:AAFNGY0LhBz8Cb7bmH8BukCFSnlTFNC4OPE"
ADMIN_ID = 620224188  # Твой Telegram ID

# === База данных ===
def init_db():
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS films (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            review TEXT,
            url TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS serials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            review TEXT,
            url TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_user(user):
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO users (user_id, username, first_name, last_name) VALUES (?, ?, ?, ?)",
        (user.id, user.username, user.first_name, user.last_name),
    )
    conn.commit()
    conn.close()

def is_favorite_exists(user_id, title):
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM favorites WHERE user_id = ? AND title = ?", (user_id, title))
    exists = cur.fetchone() is not None
    conn.close()
    return exists

def add_favorite(user_id, title):
    if not is_favorite_exists(user_id, title):
        conn = sqlite3.connect("users.db")
        cur = conn.cursor()
        cur.execute("INSERT INTO favorites (user_id, title) VALUES (?, ?)", (user_id, title))
        conn.commit()
        conn.close()
        return True
    return False

def clear_favorites(user_id):
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("DELETE FROM favorites WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_favorites(user_id):
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT title FROM favorites WHERE user_id = ?", (user_id,))
    favorites = cur.fetchall()
    conn.close()
    return [favorite[0] for favorite in favorites]

def get_user_info(user_id):
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cur.fetchone()
    conn.close()
    return user

# === FSM (состояния) ===
class AddContent(StatesGroup):
    film = State()
    serial = State()
    delete_film = State()
    delete_serial = State()

# === Настройка бота ===
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# === Клавиатура ===
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🎬 Случайный фильм"),
            KeyboardButton(text="📺 Случайный сериал"),
        ],
        [
            KeyboardButton(text="❤️ Избранное"),
            KeyboardButton(text="ℹ️ Мой профиль"),
        ],
    ],
    resize_keyboard=True,
)

# === Команды администратора ===
@dp.message(Command("add_film"))
async def cmd_add_film(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Эта команда доступна только администратору.")
        return
    await message.answer("📽 Введите фильм в формате:\nНазвание | Краткая рецензия | Ссылка")
    await state.set_state(AddContent.film)

@dp.message(AddContent.film)
async def process_add_film(message: types.Message, state: FSMContext):
    parts = message.text.split("|")
    if len(parts) != 3:
        await message.answer("⚠️ Неверный формат. Используй: Название | Рецензия | Ссылка")
        return
    title, review, url = [p.strip() for p in parts]
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO films (title, review, url) VALUES (?, ?, ?)", (title, review, url))
    conn.commit()
    conn.close()
    await message.answer(f"✅ Фильм *{title}* успешно добавлен!", parse_mode="Markdown")
    await state.clear()

@dp.message(Command("add_serial"))
async def cmd_add_serial(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Эта команда доступна только администратору.")
        return
    await message.answer("📺 Введите сериал в формате:\nНазвание | Краткая рецензия | Ссылка")
    await state.set_state(AddContent.serial)

@dp.message(AddContent.serial)
async def process_add_serial(message: types.Message, state: FSMContext):
    parts = message.text.split("|")
    if len(parts) != 3:
        await message.answer("⚠️ Неверный формат. Используй: Название | Рецензия | Ссылка")
        return
    title, review, url = [p.strip() for p in parts]
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO serials (title, review, url) VALUES (?, ?, ?)", (title, review, url))
    conn.commit()
    conn.close()
    await message.answer(f"✅ Сериал *{title}* успешно добавлен!", parse_mode="Markdown")
    await state.clear()

# === Удаление фильмов и сериалов (только админ) ===
@dp.message(Command("delete_film"))
async def cmd_delete_film(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У тебя нет прав для удаления фильмов.")
        return
    await message.answer("🗑 Введите название фильма, который хотите удалить:")
    await state.set_state(AddContent.delete_film)

@dp.message(AddContent.delete_film)
async def process_delete_film(message: types.Message, state: FSMContext):
    title = message.text.strip()
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("DELETE FROM films WHERE title = ?", (title,))
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    if deleted > 0:
        await message.answer(f"✅ Фильм '{title}' успешно удалён!")
    else:
        await message.answer(f"⚠️ Фильм '{title}' не найден в базе.")
    await state.clear()

@dp.message(Command("delete_serial"))
async def cmd_delete_serial(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У тебя нет прав для удаления сериалов.")
        return
    await message.answer("🗑 Введите название сериала, который хотите удалить:")
    await state.set_state(AddContent.delete_serial)

@dp.message(AddContent.delete_serial)
async def process_delete_serial(message: types.Message, state: FSMContext):
    title = message.text.strip()
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("DELETE FROM serials WHERE title = ?", (title,))
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    if deleted > 0:
        await message.answer(f"✅ Сериал '{title}' успешно удалён!")
    else:
        await message.answer(f"⚠️ Сериал '{title}' не найден в базе.")
    await state.clear()

# === Просмотр всех пользователей и их избранного ===
@dp.message(Command("all_users"))
async def cmd_all_users(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет прав для просмотра всех пользователей.")
        return

    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT user_id, username, first_name, last_name FROM users")
    users = cur.fetchall()
    conn.close()

    if not users:
        await message.answer("База пользователей пока пуста.")
        return

    response = "📋 Список всех пользователей:\n\n"
    for user_id, username, first_name, last_name in users:
        favorites = get_favorites(user_id)
        favorites_str = "\n• ".join(favorites) if favorites else "—"
        response += (
            f"🆔 {user_id} | 👤 {first_name or ''} {last_name or ''} | "
            f"🏷️ @{username or '—'}\n"
            f"💖 Избранное:\n• {favorites_str}\n\n"
        )

    for i in range(0, len(response), 4000):
        await message.answer(response[i:i+4000])

# === Остальные команды ===
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    add_user(message.from_user)
    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\nВыбери действие:",
        reply_markup=main_kb,
    )

@dp.message(Command("info"))
async def cmd_info(message: types.Message):
    user = get_user_info(message.from_user.id)
    if user:
        user_id, username, first_name, last_name = user
        await message.answer(
            f"🧾 Твоя информация:\n"
            f"🆔 ID: {user_id}\n"
            f"👤 Имя: {first_name}\n"
            f"🏷️ Логин: @{username if username else '—'}"
        )
    else:
        await message.answer("😕 Тебя нет в базе. Напиши /start, чтобы я тебя запомнил!")

# === Обработчик текстовых сообщений ===
@dp.message()
async def text_handler(message: types.Message):
    text = message.text.lower()
    if text == "🎬 случайный фильм":
        conn = sqlite3.connect("users.db")
        cur = conn.cursor()
        cur.execute("SELECT title, review, url FROM films ORDER BY RANDOM() LIMIT 1")
        film = cur.fetchone()
        conn.close()
        if film:
            title, review, url = film
            inline_kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="➕ Добавить в избранное", callback_data=f"add_favorite_{title}")],
                    [InlineKeyboardButton(text="🔗 Смотреть", url=url)],
                ]
            )
            await message.answer(f"🎬 *{title}*\n\n_{review}_", parse_mode="Markdown", reply_markup=inline_kb)
        else:
            await message.answer("😢 В базе пока нет фильмов.")
    elif text == "📺 случайный сериал":
        conn = sqlite3.connect("users.db")
        cur = conn.cursor()
        cur.execute("SELECT title, review, url FROM serials ORDER BY RANDOM() LIMIT 1")
        serial = cur.fetchone()
        conn.close()
        if serial:
            title, review, url = serial
            inline_kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="➕ Добавить в избранное", callback_data=f"add_favorite_{title}")],
                    [InlineKeyboardButton(text="🔗 Смотреть", url=url)],
                ]
            )
            await message.answer(f"📺 *{title}*\n\n_{review}_", parse_mode="Markdown", reply_markup=inline_kb)
        else:
            await message.answer("😢 В базе пока нет сериалов.")
    elif text == "❤️ избранное":
        favorites = get_favorites(message.from_user.id)
        if favorites:
            favorites_kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🗑️ Очистить избранное", callback_data="clear_favorites")]
                ]
            )
            await message.answer(f"💖 Твоё избранное:\n• " + "\n• ".join(favorites), reply_markup=favorites_kb)
        else:
            await message.answer("Твоё избранное пусто 😢")
    elif text == "ℹ️ мой профиль":
        await cmd_info(message)
    else:
        await message.answer("Я тебя не понял 😅\nВыбери кнопку: фильм, сериал, избранное или профиль.")

# === Callback ===
@dp.callback_query()
async def callback_handler(callback: types.CallbackQuery):
    if callback.data.startswith("add_favorite_"):
        title = callback.data.replace("add_favorite_", "")
        if add_favorite(callback.from_user.id, title):
            await callback.answer(f"✅ '{title}' добавлено в избранное!")
        else:
            await callback.answer(f"⚠️ '{title}' уже в избранном!")
        await callback.message.edit_reply_markup(reply_markup=None)
    elif callback.data == "clear_favorites":
        clear_favorites(callback.from_user.id)
        await callback.answer("🗑️ Избранное очищено!")
        await callback.message.edit_text("Твоё избранное пусто 😢")

# === Точка входа ===
async def main():
    init_db()
    logging.info("Бот запущен..")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())