import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.filters import CommandObject

# Бот забирает токен и ID чата из настроек Render
TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")

bot = Bot(token=TOKEN)
dp = Dispatcher()
users_db = {}

# Глобальные переменные курсов по умолчанию (если нет интернета)
CURRENT_USD = 96.50
CURRENT_BTC = 74200.00
CURRENT_ETH = 2650.00

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
    status_key = callback.data.split("_")
    new_status = STATUSES[status_key]
    
    users_db[user_id] = {"name": username, "status": new_status}
    
    try:
        await callback.message.edit_text(
            f"Статус успешно обновлен на: **{new_status}**\nИзменить статус:",
            reply_markup=get_status_keyboard(),
            parse_mode="Markdown"
        )
    except Exception:
        pass
        
    await callback.answer("Статус обновлен!")
    
    if GROUP_CHAT_ID:
        try:
            await bot.send_message(
                chat_id=GROUP_CHAT_ID,
                text=f"🔔 Воркер {username} изменил статус на: **{new_status}**",
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Ошибка отправки в чат: {e}")

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

# --- АВТОНОМНАЯ КОМАНДА КРИПТЫ И КОНВЕРТЕР ---
@dp.message(Command("crypto"))
async def cmd_crypto(message: Message, command: CommandObject):
    global CURRENT_USD, CURRENT_BTC, CURRENT_ETH
    
    # Если ввели просто /crypto - выдаем текущую базу данных
    if not command.args:
        text = f"📊 **Курсы криптовалют (Автономный режим):**\n\n"
        text += f"🪙 **Bitcoin (BTC):** ${CURRENT_BTC:,.2f} (~{CURRENT_BTC * CURRENT_USD:,.0f} ₽)\n"
        text += f"🔷 **Ethereum (ETH):** ${CURRENT_ETH:,.2f} (~{CURRENT_ETH * CURRENT_USD:,.0f} ₽)\n"
        text += f"💵 **USDT:** $1.00 (~{CURRENT_USD:.2f} ₽)\n\n"
        text += "💡 *Чтобы перевести сумму, пиши:* `/crypto 150 usdt` *или* `/crypto 5000 rub`"
        await message.answer(text, parse_mode="Markdown")
        return

    # Разбор аргументов для встроенного конвертера
    args = command.args.lower().split()
    if len(args) < 2:
        await message.answer("⚠ Неверный формат. Используйте: `/crypto 100 usdt` или `/crypto 5000 rub`", parse_mode="Markdown")
        return

    try:
        amount = float(args[0])
        currency = args[1]
    except ValueError:
        await message.answer("❌ Первым аргументом должно быть число (сумма). Пример: `/crypto 50 usdt`", parse_mode="Markdown")
        return

    text = f"💱 **Результат конвертации ({amount:,.2f} {currency.upper()}):**\n\n"
    if currency in ["usdt", "usd"]:
        text += f"🔹 В рублях: **{amount * CURRENT_USD:,.2f} ₽**\n"
        text += f"🔹 В BTC: **{amount / CURRENT_BTC:.6f} BTC**"
    elif currency in ["rub", "rur"]:
        text += f"🔹 В USDT: **{amount / CURRENT_USD:,.2f} USDT**\n"
        text += f"🔹 В BTC: **{(amount / CURRENT_USD) / CURRENT_BTC:.6f} BTC**"
    elif currency == "btc":
        text += f"🔹 В USDT: **{amount * CURRENT_BTC:,.2f} USDT**\n"
        text += f"🔹 В рублях: **{amount * CURRENT_BTC * CURRENT_USD:,.2f} ₽**"
    else:
        text = "❌ Данная валюта не поддерживается. Доступны: `usdt`, `rub`, `btc`."

    await message.answer(text, parse_mode="Markdown")

# Административная команда для тебя, чтобы обновлять курс бакса при перепадах
@dp.message(Command("setusd"))
async def cmd_setusd(message: Message, command: CommandObject):
    global CURRENT_USD
    if not command.args:
        await message.answer("Укажите новый курс доллара. Пример: `/setusd 97.30`", parse_mode="Markdown")
        return
    try:
        CURRENT_USD = float(command.args)
        await message.answer(f"✅ Базовый курс доллара успешно изменен на: **{CURRENT_USD:.2f} ₽**", parse_mode="Markdown")
    except ValueError:
        await message.answer("❌ Курс должен быть числом.")

async def main():
    print("Бот запущен успешно!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
