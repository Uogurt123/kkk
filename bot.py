import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0)) 
CARD_NUMBER = os.getenv("CARD_NUMBER", "0000 0000 0000 0000")

logging.basicConfig(level=logging.INFO)

if not TOKEN or not ADMIN_ID:
    raise ValueError("Переменные BOT_TOKEN или ADMIN_ID не заданы в настройках Railway!")

bot = Bot(token=TOKEN)
dp = Dispatcher()

class PurchaseState(StatesGroup):
    waiting_for_stars = State()

def get_main_menu():
    buttons = [
        [InlineKeyboardButton(text="💎 Купити зірки", callback_data="buy_stars")],
        [InlineKeyboardButton(text="💬 Написати Розробнику(генію тому хто сам тримає вогник і взагалі легенді найкращому другу)", url="https://t.me/aquaee")],
        [InlineKeyboardButton(text="ℹ️ Про бота", callback_data="about_bot")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_payment_keyboard():
    buttons = [
        [InlineKeyboardButton(text="✅ Я оплатив", callback_data="payment_done")],
        [InlineKeyboardButton(text="❌ Відміна", callback_data="cancel_payment")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 абжджа8ог98аолдаво звезди купи пж:",
        reply_markup=get_main_menu()
      )

@dp.callback_query(F.data == "about_bot")
async def press_about(callback: CallbackQuery):
    await callback.message.answer("бот нічого не вміє і вообще не працює 🤫")
    await callback.answer()

@dp.callback_query(F.data == "buy_stars")
async def press_buy(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Кількість зірок (наприклад: 50, 100, 250):")
    await state.set_state(PurchaseState.waiting_for_stars)
    await callback.answer()

@dp.message(PurchaseState.waiting_for_stars)
async def process_stars_amount(message: Message, state: FSMContext):
    stars_amount = message.text.strip()
    if not stars_amount.isdigit():
        await message.answer("тільки цифри :")
        return
    await state.update_data(amount=stars_amount)
    await message.answer(
        f"заявка на покупку: <b>{stars_amount} ⭐</b>\n\n"
        f"💳 для оплати скинь дєнєшку на карту:\n"
        f"<code>{CARD_NUMBER}</code> <i>(нажми щоб скопійувати)</i>\n\n"
        f"після переказу нажми Я оплатив. "
        f"Адміністратор (я) скоро перевірить платіж (не факт).",
        parse_mode="HTML",
        reply_markup=get_payment_keyboard()
    )

@dp.callback_query(F.data == "payment_done")
async def press_payment_done(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    stars_amount = user_data.get("amount", "Невідомо")
    user_info = callback.from_user
    username = f"@{user_info.username}" if user_info.username else "Немає Юзернейма"

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

    await callback.message.answer(
        "✨ Повідомлення про оплату успішно відправленне Адміністратору @aquaee.\n"
        "Очікуйте зарахування зірок найближчим часом."
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