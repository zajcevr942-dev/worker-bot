import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Бот забирает настройки из Render
TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
ADMIN_ID = os.getenv("ADMIN_ID")

bot = Bot(token=TOKEN)
dp = Dispatcher()
users_db = {}

# Состояния для сдачи профита
class ProfitStates(StatesGroup):
    waiting_for_details = State()

STATUSES = {
    "work": "🟢 Работает",
    "busy": "🟡 Занят",
    "rest": "🔴 Отдыхает"
}

# Клавиатура ТУТ ТОЛЬКО СТАТУСЫ, ничего лишнего
def get_status_keyboard():
    buttons = [
        [InlineKeyboardButton(text="🟢 Работаю", callback_data="set_work")],
        [InlineKeyboardButton(text="🟡 Занят", callback_data="set_busy")],
        [InlineKeyboardButton(text="🔴 Отдыхаю", callback_data="set_rest")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Команды /start и /status работают ТОЛЬКО в личке
@dp.message(Command("start", "status"))
async def cmd_status(message: Message):
    if message.chat.type != "private":
        try:
            await message.delete()
        except Exception:
            pass
        return

    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
    if user_id not in users_db:
        users_db[user_id] = {"name": username, "status": "🔴 Отдыхает"}
    current_status = users_db[user_id]["status"]
    
    await message.answer(
        f"Ваш текущий статус: **{current_status}**\nДля изменения выберите кнопку ниже:",
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
    
    try:
        await callback.message.edit_text(
            f"Статус успешно обновлен на: **{new_status}**",
            reply_markup=get_status_keyboard(),
            parse_mode="Markdown"
        )
    except Exception:
        pass
        
    await callback.answer("Статус обновлен")
    
    if GROUP_CHAT_ID:
        try:
            await bot.send_message(
                chat_id=GROUP_CHAT_ID,
                text=f"🔔 Воркер {username} изменил статус на: **{new_status}**",
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Ошибка отправки в чат: {e}")

# Отдельная команда /profit для сдачи отчетов (работает только в личке)
@dp.message(Command("profit"))
async def cmd_profit(message: Message, state: FSMContext):
    if message.chat.type != "private":
        try:
            await message.delete()
        except Exception:
            pass
        return

    await message.answer(
        "💰 **Отчет о профите**\n\nВведите сумму и платформу одним сообщением.\n*Пример: 5000 руб казино Волна*",
        parse_mode="Markdown"
    )
    await state.set_state(ProfitStates.waiting_for_details)

# Прием данных профита и отправка строгого текста в чат
@dp.message(ProfitStates.waiting_for_details)
async def process_profit_report(message: Message, state: FSMContext):
    username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
    profit_info = message.text

    await state.clear()
    await message.answer("✅ Отчет принят и отправлен в чат команды.")

    if GROUP_CHAT_ID:
        try:
            # Полностью строгий и чистый текст без кринжа
            text = f"💰 **Новый профит**\n\n"
            text += f"👤 Воркер: **{username}**\n"
            text += f"📊 Информация: **{profit_info}**"
            
            await bot.send_message(
                chat_id=GROUP_CHAT_ID,
                text=text,
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Ошибка отправки профита в чат: {e}")

# Защищенная команда /team для Тимлида
@dp.message(Command("team"))
async def cmd_team(message: Message):
    if ADMIN_ID and str(message.from_user.id) != str(ADMIN_ID):
        try:
            await message.delete()
        except Exception:
            pass
        return

    if not users_db:
        await message.answer("В базе еще нет воркеров. Пусть все нажмут /start в личке у бота.")
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
