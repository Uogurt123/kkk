import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

# --- НАСТРОЙКИ ---
TOKEN = "8775506881:AAHvveG2ySiNSGxQDEy2ArEBuBraxJ7os88"
ADMIN_ID = 8065826973  # СЮДА_ВСТАВЬ_СВОЙ_ID (цифрами, без кавычек)
CARD_NUMBER = "4874070013423833"  # СЮДА_ВСТАВЬ_НОМЕР_КАРТЫ

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Состояния для ввода количества звёзд
class PurchaseState(StatesGroup):
    waiting_for_stars = State()

# --- КЛАВИАТУРЫ ---
def get_main_menu():
    buttons = [
        [InlineKeyboardButton(text="💎 Купить звёзды", callback_data="buy_stars")],
        [InlineKeyboardButton(text="💬 Написать напрямую", url="https://t.me/aquaee")],
        [InlineKeyboardButton(text="ℹ️ О боте", callback_data="about_bot")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_payment_keyboard():
    buttons = [
        [InlineKeyboardButton(text="✅ Я оплатила", callback_data="payment_done")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_payment")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- ХЕНДЛЕРЫ ---

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 Приветствуем! Здесь вы можете приобрести Telegram Stars напрямую.\n"
        "Выберите нужное действие в меню ниже:",
        reply_markup=get_main_menu()
    )

@dp.callback_query(F.data == "about_bot")
async def press_about(callback: CallbackQuery):
    await callback.message.answer("Этот бот ничего не умеет и вообще он не работает 🤫")
    await callback.answer()

@dp.callback_query(F.data == "buy_stars")
async def press_buy(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите количество звёзд, которое вы хотите приобрести (например: 50, 100, 250):")
    await state.set_state(PurchaseState.waiting_for_stars)
    await callback.answer()

@dp.message(PurchaseState.waiting_for_stars)
async def process_stars_amount(message: Message, state: FSMContext):
    stars_amount = message.text.strip()
    
    # Проверяем, что введено число
    if not stars_amount.isdigit():
        await message.answer("Пожалуйста, введите корректное число звёзд (только цифры):")
        return

    await state.update_data(amount=stars_amount)
    
    # Отправляем реквизиты
    await message.answer(
        f"Заявка на покупку: <b>{stars_amount} ⭐</b>\n\n"
        f"💳 Для оплаты переведите деньги на карту:\n"
        f"<code>{CARD_NUMBER}</code> <i>(нажмите, чтобы скопировать)</i>\n\n"
        f"После успешного перевода нажмите кнопку «Я оплатила» ниже. "
        f"Администратор сразу проверит платеж и начислит звёзды.",
        parse_mode="HTML",
        reply_markup=get_payment_keyboard()
    )

@dp.callback_query(F.data == "payment_done")
async def press_payment_done(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    stars_amount = user_data.get("amount", "Неизвестно")
    
    user_info = callback.from_user
    username = f"@{user_info.username}" if user_info.username else "Нет юзернейма"
    
    # 1. Отправляем уведомление тебе в личку
    try:
        notification_text = (
            f"🚨 <b>Уведомление о покупке!</b>\n\n"
            f"👤 <b>Пользователь:</b> {user_info.full_name} ({username})\n"
            f"🆔 <b>ID:</b> <code>{user_info.id}</code>\n"
            f"💎 <b>Количество звёзд:</b> {stars_amount}\n\n"
            f"Проверь банковское приложение на наличие перевода!"
        )
        await bot.send_message(chat_id=ADMIN_ID, text=notification_text, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Не удалось отправить уведомление админу: {e}")

    # 2. Отвечаем пользователю
    await callback.message.answer(
        "✨ Спасибо! Уведомление об оплате успешно отправлено администратору @aquaee.\n"
        "Ожидайте зачисления звёзд в ближайшее время."
    )
    
    await state.clear()
    await callback.answer()

@dp.callback_query(F.data == "cancel_payment")
async def press_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Покупка отменена.", reply_markup=get_main_menu())
    await callback.answer()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
