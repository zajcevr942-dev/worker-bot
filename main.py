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

# --- КЛАВИАТУРЫ ---

# Главное меню (Категории)
def get_main_keyboard():
    buttons = [
        [InlineKeyboardButton(text="📊 Статусы", callback_data="menu_statuses")],
        [InlineKeyboardButton(text="💰 Сдать профит", callback_data="menu_profit")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Подкатегория статусов
def get_status_keyboard():
    buttons = [
        [InlineKeyboardButton(text="🟢 Работаю", callback_data="set_work")],
        [InlineKeyboardButton(text="🟡 Занят", callback_data="set_busy")],
        [InlineKeyboardButton(text="🔴 Отдыхаю", callback_data="set_rest")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# --- ЛОГИКА БОТА ---

# Старт (Главное меню)
@dp.message(Command("start", "status"))
async def cmd_start(message: Message, state: FSMContext):
    if message.chat.type != "private":
        try:
            await message.delete()
        except Exception:
            pass
        return

    await state.clear()
    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
    
    if user_id not in users_db:
        users_db[user_id] = {"name": username, "status": "🔴 Отдыхает"}
        
    current_status = users_db[user_id]["status"]
    
    await message.answer(
        f"📋 **Главное меню**\n\nВаш текущий статус: **{current_status}**\nВыберите нужный раздел:",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

# Переход в категорию "Статусы"
@dp.callback_query(F.data == "menu_statuses")
async def view_statuses(callback: CallbackQuery):
    user_id = callback.from_user.id
    current_status = users_db.get(user_id, {}).get("status", "🔴 Отдыхает")
    
    await callback.message.edit_text(
        f"📊 **Управление статусом**\n\nТекущий статус: **{current_status}**\nВыберите новый статус ниже:",
        reply_markup=get_status_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

# Кнопка "Назад" в главное меню
@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    current_status = users_db.get(user_id, {}).get("status", "🔴 Отдыхает")
    
    await callback.message.edit_text(
        f"📋 **Главное меню**\n\nВаш текущий статус: **{current_status}**\nВыберите нужный раздел:",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

# Установка статуса
@dp.callback_query(F.data.startswith("set_"))
async def change_status(callback: CallbackQuery):
    user_id = callback.from_user.id
    username = f"@{callback.from_user.username}" if callback.from_user.username else callback.from_user.full_name
    status_key = callback.data.split("_")[1]
    new_status = STATUSES[status_key]
    
    users_db[user_id] = {"name": username, "status": new_status}
    
    try:
        await callback.message.edit_text(
            f"📊 **Управление статусом**\n\n✅ Статус успешно изменен на: **{new_status}**",
            reply_markup=get_status_keyboard(),
            parse_mode="Markdown"
        )
    except Exception:
        pass
        
    await callback.answer(f"Статус изменен на {new_status}")
    
    if GROUP_CHAT_ID:
        try:
            await bot.send_message(
                chat_id=GROUP_CHAT_ID,
                text=f"🔔 Воркер {username} изменил статус на: **{new_status}**",
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Ошибка отправки в чат: {e}")

# Категория "Сдать профит"
@dp.callback_query(F.data == "menu_profit")
async def start_profit_report(callback: CallbackQuery, state: FSMContext):
    # Изменяем сообщение меню на форму ввода
    await callback.message.edit_text(
        "💰 **Отчет о профите**\n\nВведите сумму и платформу одним сообщением.\n*Пример: 5000 руб казино Волна*\n\n_Для отмены нажмите кнопку «Назад» ниже_",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]]),
        parse_mode="Markdown"
    )
    await state.set_state(ProfitStates.waiting_for_details)
    await callback.answer()

# Прием данных профита и отправка строгого текста в чат
@dp.message(ProfitStates.waiting_for_details)
async def process_profit_report(message: Message, state: FSMContext):
    if message.chat.type != "private":
        return

    username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
    profit_info = message.text

    await state.clear()
    
    # После отправки возвращаем воркера в главное меню
    user_id = message.from_user.id
    current_status = users_db.get(user_id, {}).get("status", "🔴 Отдыхает")
    
    await message.answer(
        f"✅ Отчет успешно принят и отправлен в чат команды.\n\n📋 **Главное меню**\nВаш статус: **{current_status}**",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

    if GROUP_CHAT_ID:
        try:
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
