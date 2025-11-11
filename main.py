import asyncio
import os
from datetime import datetime

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
import sqlite3


load_dotenv()
dp = Dispatcher(storage=MemoryStorage())  # FSM для многошаговых операций (/add)


def init_db():
    conn = sqlite3.connect("consumables.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL CHECK(length(name) <= 100),
            start_date TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


class AddItem(StatesGroup):
    waiting_for_name = State()
    waiting_for_date = State()


@dp.message(CommandStart())
async def command_start_handler(message: Message):
    text = (
        "Привет! Давай немного помогу тебе с бытом.\n"
        "Команда /add — добавляет расходник.\n"
        "Команда /list — выводит список расходников с датами начала использования.\n"
        "Команда /remove — удаляет расходник из списка."
    )
    await message.answer(text)


@dp.message(Command("add"))
async def cmd_add(message: Message, state: FSMContext):
    await message.answer("Введи название расходника:")
    await state.set_state(AddItem.waiting_for_name)


@dp.message(AddItem.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.answer("Название не может быть пустым. Попробуй снова:")
        return
    if len(name) > 100:
        await message.answer("Слишком длинное название (макс. 100 симв.). Попробуй снова:")
        return

    await state.update_data(name=name)
    await message.answer("Введи дату начала использования (в формате ДД.ММ.ГГГГ):")
    await state.set_state(AddItem.waiting_for_date)


@dp.message(AddItem.waiting_for_date)
async def process_date(message: Message, state: FSMContext):
    date_str = message.text.strip()
    try:
        start_date = datetime.strptime(date_str, "%d.%m.%Y").date()
        if start_date > datetime.today().date():
            await message.answer("Дата не может быть в будущем. Введи корректную дату:")
            return
    except ValueError:
        await message.answer("Неверный формат даты. Используй: ДД.ММ.ГГГГ")
        return

    data = await state.get_data()
    name = data["name"]
    user_id = message.from_user.id

    conn = sqlite3.connect("consumables.db")
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO items (user_id, name, start_date) VALUES (?, ?, ?)",
        (user_id, name, start_date.isoformat())
    )  # параметризованный запрос — защита от SQL-инъекций
    conn.commit()
    conn.close()

    await message.answer(f"Добавлено: '{name}' с {date_str}")
    await state.clear()  # сброс состояния после завершения


@dp.message(Command("list"))
async def cmd_list(message: Message):
    user_id = message.from_user.id
    conn = sqlite3.connect("consumables.db")
    cur = conn.cursor()
    cur.execute(
        "SELECT name, start_date FROM items WHERE user_id = ? ORDER BY start_date",
        (user_id,)
    )
    items = cur.fetchall()
    conn.close()

    if not items:
        await message.answer("Список расходников пуст.")
        return

    lines = [f"• {name} → {start_date}" for name, start_date in items]
    await message.answer("Ваши расходники:\n" + "\n".join(lines))


@dp.message(Command("remove"))
async def cmd_remove(message: Message):
    args = message.text.split(maxsplit=1)  # /remove название → ["", "название"]
    if len(args) < 2:
        await message.answer("Укажи название расходника: /remove <название>")
        return

    name = args[1].strip()
    user_id = message.from_user.id

    conn = sqlite3.connect("consumables.db")
    cur = conn.cursor()
    cur.execute("DELETE FROM items WHERE user_id = ? AND name = ?", (user_id, name))
    deleted = cur.rowcount  # сколько строк удалено (0 или 1+)
    conn.commit()
    conn.close()

    if deleted:
        await message.answer(f"Удалено: '{name}'")
    else:
        await message.answer(f"Расходник '{name}' не найден.")


async def main():
    bot = Bot(token=os.getenv("TOKEN"))
    await dp.start_polling(bot)


if __name__ == "__main__":
    init_db()  # создаём БД при запуске
    asyncio.run(main())