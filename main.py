import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

# Бот сам заберет токен из переменной BOT_TOKEN на Render
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()
users_db = {}

STATUSES = {
    "work": "🟢 Работает",
    "busy": "🟡 Занят",
    "rest": "🔴 Отдыхает"
}

def get_status_keyboard():
    buttons = [
        [InlineKeyboardButton(text="🟢 Работаю", callback_data="set_work")],
        [InlineKeyboardButton(text="🟡 Занят", callback_data="set_busy")],
        [InlineKeyboardButton(text="🔴 Отдыхаю", callback_data="set_rest")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(Command("start", "status"))
async def cmd_status(message: Message):
    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
    if user_id not in users_db:
        users_db[user_id] = {"name": username, "status": "🔴 Отдыхает"}
    current_status = users_db[user_id]["status"]
    await message.answer(
        f"Привет! Твой текущий статус: **{current_status}**\nОбнови его кнопкой ниже:",
        reply_markup=get_status_keyboard(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("set_"))
async def change_status(callback: CallbackQuery):
    user_id = callback.from_user.id
    username = f"@{callback.from_user.username}" if callback.from_user.username else callback.from_user.full_name
    status_key = callback.data.split("_")[1]
    new_status = STATUSES[status_key]
    users_db[user_id] = {"name": username, "status": new_status}
    await callback.message.edit_text(
        f"Статус успешно обновлен на: **{new_status}**\nИзменить статус:",
        reply_markup=get_status_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer("Статус обновлен!")

@dp.message(Command("team"))
async def cmd_team(message: Message):
    if not users_db:
        await message.answer("В базе еще нет воркеров. Пусть все нажмут /start в боте.")
        return
    working, busy, resting = [], [], []
    for user_data in users_db.values():
        name = user_data["name"]
        status = user_data["status"]
        if "🟢" in status:
            working.append(f"• {name}")
        elif "🟡" in status:
            busy.append(f"• {name}")
        elif "🔴" in status:
            resting.append(f"• {name}")
    text = "📊 **Текущий статус команды:**\n\n"
    text += "🟢 **РАБОТАЮТ:**\n" + ("\n".join(working) if working else "_Никого нет_") + "\n\n"
    text += "🟡 **ЗАНЯТЫ:**\n" + ("\n".join(busy) if busy else "_Никого нет_") + "\n\n"
    text += "🔴 **ОТДЫХАЮТ:**\n" + ("\n".join(resting) if resting else "_Никого нет_")
    await message.answer(text, parse_mode="Markdown")

async def main():
    print("Бот запущен успешно!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
