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

# --- КЛАВИАТУРЫ ---

def get_main_menu():
    buttons = [
        [InlineKeyboardButton(text="💎 Купити зірки", callback_data="buy_stars")],
        [InlineKeyboardButton(text="💬 Написати Розробнику(генію тому хто сам тримає вогник
        і взагалі легенді найкращому другу)", url="https://t.me/aquaee")],
        [InlineKeyboardButton(text="ℹ️ Про бота", callback_data="about_bot")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_payment_keyboard():
    buttons = [
        [InlineKeyboardButton(text="✅ Я оплатив", callback_data="payment_done")],
        [InlineKeyboardButton(text="❌ Відміна", callback_data="cancel_payment")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Клавиатура для тебя (админа), чтобы управлять заявкой в один клик
def get_admin_keyboard(user_id: int):
    buttons = [
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{user_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{user_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- ХЕНДЛЕРЫ ---

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 <b>абжджа8ог98аолдаво звезди купи пж:</b>\n\n"
        "⚡ <i>Виберіть потрібну опцію в меню нижче:</i>",
        parse_mode="HTML",
        reply_markup=get_main_menu()
    )

@dp.callback_query(F.data == "about_bot")
async def press_about(callback: CallbackQuery):
    await callback.message.answer("<b>ℹ️ Інформація:</b>\n\nбот нічого не вміє і вообще не працює 🤫", parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "buy_stars")
async def press_buy(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("🔢 <b>Кількість зірок (наприклад: 50, 100, 250):</b>", parse_mode="HTML")
    await state.set_state(PurchaseState.waiting_for_stars)
    await callback.answer()

@dp.message(PurchaseState.waiting_for_stars)
async def process_stars_amount(message: Message, state: FSMContext):
    stars_amount = message.text.strip()
    if not stars_amount.isdigit():
        await message.answer("⚠️ <b>тільки цифри :</b>", parse_mode="HTML")
        return
    
    await state.update_data(amount=stars_amount)
    await message.answer(
        f"📝 <b>заявка на покупку:</b> <code>{stars_amount}</code> ⭐\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💳 <b>для оплати скинь дєнєшку на карту:</b>\n"
        f"<code>{CARD_NUMBER}</code> <i>(нажми щоб скопійувати)</i>\n\n"
        f"📌 <b>після переказу нажми Я оплатив.</b>\n"
        f"<i>Адміністратор (я) скоро перевірить платіж (не факт).</i>",
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
        # Отправляем уведомление тебе с кнопками действий
        notification_text = (
            f"💰 <b>🚨 Уведомление о покупке!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 <b>Пользователь:</b> {user_info.full_name} ({username})\n"
            f"🆔 <b>ID:</b> <code>{user_info.id}</code>\n"
            f"💎 <b>Количество звёзд:</b> <code>{stars_amount}</code> ⭐\n\n"
            f"💵 <i>Проверь банковское приложение на наличие перевода!</i>"
        )
        await bot.send_message(
            chat_id=ADMIN_ID, 
            text=notification_text, 
            parse_mode="HTML",
            reply_markup=get_admin_keyboard(user_info.id) # Привязываем твой пульт управления
        )
    except Exception as e:
        logging.error(f"Не удалось отправить уведомление админу: {e}")

    await callback.message.answer(
        "✨ <b>Повідомлення про оплату успішно відправленне Адміністратору @aquaee.</b>\n\n"
        "⏳ Очікуйте зарахування зірок найближчим часом.",
        parse_mode="HTML"
    )
    await state.clear()
    await callback.answer()

@dp.callback_query(F.data == "cancel_payment")
async def press_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("❌ <b>Покупка отменена.</b>", parse_mode="HTML", reply_markup=get_main_menu())
    await callback.answer()

# --- ОБРАБОТКА ДЕЙСТВИЙ АДМИНИСТРАТОРА (ТЕБЯ) ---

@dp.callback_query(F.data.startswith("confirm_"))
async def admin_confirm_payment(callback: CallbackQuery):
    # Достаем ID пользователя из callback_data
    target_user_id = int(callback.data.split("_")[1])
    
    try:
        # Отправляем пользователю сообщение об успехе
        await bot.send_message(
            chat_id=target_user_id,
            text="✨ <b>Ваш платёж успішно підтверджений!</b>\n\n"
                 "🎉 Адміністратор нарахував вам зірки. Дякуємо за покупку!",
            parse_mode="HTML"
        )
        # Обновляем сообщение у тебя в чате, чтобы ты видел, что нажал
        await callback.message.edit_text(
            callback.message.text + "\n\n✅ <b>Статус: Подтверждено тобой!</b>",
            parse_mode="HTML"
        )
    except Exception as e:
        await callback.message.answer(f"Ошибка отправки пользователю: {e}")
    
    await callback.answer()

@dp.callback_query(F.data.startswith("reject_"))
async def admin_reject_payment(callback: CallbackQuery):
    target_user_id = int(callback.data.split("_")[1])
    
    try:
        # Отправляем пользователю сообщение об отказе
        await bot.send_message(
            chat_id=target_user_id,
            text="⚠️ <b>Помилка підтвердження платежу!</b>\n\n"
                 "Адміністратор не знайшов ваш переказ. Перевірте чек або напишіть в підтримку.",
            parse_mode="HTML"
        )
        # Обновляем сообщение у тебя
        await callback.message.edit_text(
            callback.message.text + "\n\n❌ <b>Статус: Отклонено тобой!</b>",
            parse_mode="HTML"
        )
    except Exception as e:
        await callback.message.answer(f"Ошибка отправки пользователю: {e}")
        
    await callback.answer()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
