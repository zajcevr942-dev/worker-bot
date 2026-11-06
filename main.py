import asyncio
import os
import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

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

# --- НЕУБИВАЕМАЯ КРИПТА ЧЕРЕЗ ПУБЛИЧНЫЙ МИРРОР API ---
@dp.message(Command("crypto"))
async def cmd_crypto(message: Message):
    usd_rub = 96.50  # Средний курс доллара к рублю
    
    async with aiohttp.ClientSession() as session:
        try:
            # Используем открытый крипто-компар цен, который прощает запросы от хостингов
            async with session.get("https://cryptocompare.com") as r_btc:
                d_btc = await r_btc.json()
                btc_usd = float(d_btc['USD'])
            
            async with session.get("https://cryptocompare.com") as r_eth:
                d_eth = await r_eth.json()
                eth_usd = float(d_eth['USD'])
        except Exception as e:
            print(f"Ошибка API CryptoCompare: {e}")
            await message.answer("❌ Не удалось получить курсы. Попробуйте позже.")
            return

    text = f"📊 **Курсы криптовалют:**\n\n"
    text += f"🪙 **Bitcoin (BTC):** ${btc_usd:,.2f} (~{btc_usd * usd_rub:,.0f} ₽)\n"
    text += f"🔷 **Ethereum (ETH):** ${eth_usd:,.2f} (~{eth_usd * usd_rub:,.0f} ₽)\n"
    text += f"💵 **USDT:** $1.00 (~{usd_rub:.2f} ₽)"
    await message.answer(text, parse_mode="Markdown")

async def main():
    print("Бот запущен успешно!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
