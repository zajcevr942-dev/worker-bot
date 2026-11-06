import asyncio
import os
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Включаем логирование, чтобы видеть ошибки в панели Render
logging.basicConfig(level=logging.INFO)

# Бот забирает настройки из Render
TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
ADMIN_ID = os.getenv("ADMIN_ID")
TEAM_PASSWORD = os.getenv("TEAM_PASSWORD") # Секретный пароль для воркеров

bot = Bot(token=TOKEN)
dp = Dispatcher()

users_db = {}
# Список ID пользователей, которые успешно прошли проверку пароля (сбрасывается при перезапуске Render)
authorized_users = set()

# Состояния для сдачи профита и ввода пароля
class BotStates(StatesGroup):
    waiting_for_password = State()
    waiting_for_details = State()

STATUSES = {
    "work": "🟢 Работает",
    "busy": "🟡 Занят",
    "rest": "🔴 Отдыхает"
}

# --- КЛАВИАТУРЫ ---

def get_main_keyboard():
    buttons = [
        [InlineKeyboardButton(text="📊 Статусы", callback_data="menu_statuses")],
        [InlineKeyboardButton(text="💰 Сдать профит", callback_data="menu_profit")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_status_keyboard():
    buttons = [
        [InlineKeyboardButton(text="🟢 Работаю", callback_data="set_work")],
        [InlineKeyboardButton(text="🟡 Занят", callback_data="set_busy")],
        [InlineKeyboardButton(text="🔴 Отдыхаю", callback_data="set_rest")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# --- ЛОГИКА БОТА ---

# Проверка авторизации
def is_authorized(user_id):
    # Тимлид всегда авторизован автоматически
    if ADMIN_ID and str(user_id) == str(ADMIN_ID):
        return True
    return user_id in authorized_users

# Старт (Главное меню или Ввод пароля)
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
    
    # Если пароль задан в Render и юзер еще не авторизован
    if TEAM_PASSWORD and not is_authorized(user_id):
        await message.answer("🔒 **Вход закрыт.**\n\nВведите секретный код команды для доступа к боту:")
        await state.set_state(BotStates.waiting_for_password)
        return

    if user_id not in users_db:
        users_db[user_id] = {"name": username, "status": "🔴 Отдыхает"}
        
    current_status = users_db[user_id]["status"]
    
    await message.answer(
        f"📋 **Главное меню**\n\nВаш текущий статус: **{current_status}**\nВыберите нужный раздел:",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

# Прием и проверка пароля
@dp.message(BotStates.waiting_for_password)
async def process_password(message: Message, state: FSMContext):
    if message.chat.type != "private":
        return

    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
    
    if message.text == TEAM_PASSWORD:
        authorized_users.add(user_id)
        await state.clear()
        
        if user_id not in users_db:
            users_db[user_id] = {"name": username, "status": "🔴 Отдыхает"}
            
        await message.answer(
            f"✅ **Доступ успешно открыт!**\n\n📋 **Главное меню**\nВаш текущий статус: **🔴 Отдыхает**\nВыберите нужный раздел:",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await message.answer("❌ **Неверный код команды.** Доступ запрещен. Попробуйте еще раз:")

# Переход в категорию "Статусы"
@dp.callback_query(F.data == "menu_statuses")
async def view_statuses(callback: CallbackQuery):
    user_id = callback.from_user.id
    if not is_authorized(user_id):
        await callback.answer("🔒 Требуется авторизация", show_alert=True)
        return
        
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
    user_id = callback.from_user.id
    if not is_authorized(user_id):
        await callback.answer("🔒 Требуется авторизация", show_alert=True)
        return
        
    await state.clear()
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
    if not is_authorized(user_id):
        await callback.answer("🔒 Требуется авторизация", show_alert=True)
        return
        
    username = f"@{callback.from_user.username}" if callback.from_user.username else callback.from_user.full_name
    status_key = callback.data.split("_")[1] # Исправлено: берем именно ключ статуса (work/busy/rest)
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
        
    await callback.answer(f"Статус изменен")
    
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
    user_id = callback.from_user.id
    if not is_authorized(user_id):
        await callback.answer("🔒 Требуется авторизация", show_alert=True)
        return
        
    await callback.message.edit_text(
        "💰 **Отчет о профите**\n\nВведите сумму и платформу одним сообщением.\n*Пример: 5000 руб казино Волна*\n\n_Для отмены нажмите кнопку «Назад» ниже_",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]]),
        parse_mode="Markdown"
    )
    await state.set_state(BotStates.waiting_for_details)
    await callback.answer()

# Прием данных профита
@dp.message(BotStates.waiting_for_details)
async def process_profit_report(message: Message, state: FSMContext):
    if message.chat.type != "private":
        return
    user_id = message.from_user.id
    if not is_authorized(user_id):
        return

    username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
    profit_info = message.text
    await state.clear()
    
    current_status = users_db.get(user_id, {}).get("status", "🔴 Отдыхает")
    await message.answer(
        f"✅ Отчет успешно принят и отправлен в чат команды.\n\n📋 **Главное меню**\nВаш статус: **{current_status}**",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

    if GROUP_CHAT_ID:
        try:
            text = f"💰 **Новый профит**\n\n👤 Воркер: **{username}**\n📊 Информация: **{profit_info}**"
            await bot.send_message(chat_id=GROUP_CHAT_ID, text=text, parse_mode="Markdown")
        except Exception as e:
            print(f"Ошибка отправки профита в чат: {e}")

# Точка входа для запуска бота
async def main():
    if not TOKEN:
        print("Ошибка: Токен бота (BOT_TOKEN) не задан в переменных окружения Render!")
        return
    print("Бот успешно запущен и готов к работе...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
