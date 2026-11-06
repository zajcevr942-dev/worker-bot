import asyncio
import os
import aiohttp
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
    
    await callback.message.edit_text(
        f"Статус успешно обновлен на: **{new_status}**\nИзменить статус:",
        reply_markup=get_status_keyboard(),
        parse_mode="Markdown"
    )
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
        await message.answer("В базе еще нет воркеров. Пусть все нажмут /start in боте.")
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

# --- НОВАЯ ФУНКЦИЯ: КРИПТО-ТРЕКЕР И КОНВЕРТЕР ---
@dp.message(Command("crypto"))
async def cmd_crypto(message: Message, command: CommandObject):
    async with aiohttp.ClientSession() as session:
        # Запрос актуальных курсов к бирже Bybit
        try:
            async with session.get("https://bybit.com") as r_btc:
                d_btc = await r_btc.json()
                btc_usd = float(d_btc['result']['list'][0]['lastPrice'])
            
            async with session.get("https://bybit.com") as r_eth:
                d_eth = await r_eth.json()
                eth_usd = float(d_eth['result']['list'][0]['lastPrice'])
                
            async with session.get("https://bybit.com") as r_rub:
                # Берем примерный средний курс доллара к рублю
                # Для стабильности берем фиксированный или вычисляемый биржевой курс
                usd_rub = 96.50 
        except Exception:
            await message.answer("❌ Не удалось получить свежие курсы с биржи. Попробуйте позже.")
            return

    # Если воркер ввел просто /crypto
    if not command.args:
        text = f"📊 **Курсы криптовалют Bybit:**\n\n"
        text += f"🪙 **Bitcoin (BTC):** ${btc_usd:,.2f} (~{btc_usd * usd_rub:,.0f} ₽)\n"
        text += f"🔷 **Ethereum (ETH):** ${eth_usd:,.2f} (~{eth_usd * usd_rub:,.0f} ₽)\n"
        text += f"💵 **USDT:** $1.00 (~{usd_rub:.2f} ₽)"
        await message.answer(text, parse_mode="Markdown")
        return

    # Разбор аргументов для конвертера (например: /crypto 100 usdt)
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
        text += f"🔹 В рублях: **{amount * usd_rub:,.2f} ₽**\n"
        text += f"🔹 В BTC: **{amount / btc_usd:.6f} BTC**"
    elif currency in ["rub", "rur"]:
        text += f"🔹 В USDT: **{amount / usd_rub:,.2f} USDT**\n"
        text += f"🔹 В BTC: **{(amount / usd_rub) / btc_usd:.6f} BTC**"
    elif currency == "btc":
        text += f"🔹 В USDT: **{amount * btc_usd:,.2f} USDT**\n"
        text += f"🔹 В рублях: **{amount * btc_usd * usd_rub:,.2f} ₽**"
    else:
        text = "❌ Данная валюта не поддерживается. Доступны: `usdt`, `rub`, `btc`."

    await message.answer(text, parse_mode="Markdown")

async def main():
    print("Бот запущен успешно!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
