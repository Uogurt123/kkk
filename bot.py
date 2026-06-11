import asyncio
import logging
import os
import re
import sqlite3
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0)) 
CARD_NUMBER = os.getenv("CARD_NUMBER", "0000 0000 0000 0000")

# --- КУРС ЗІРКИ (1 зірка = 0.85 грн) ---
STAR_PRICE = 0.85 

logging.basicConfig(level=logging.INFO)

if not TOKEN or not ADMIN_ID:
    raise ValueError("Переміннные BOT_TOKEN или ADMIN_ID не заданы в настройках Railway!")

bot = Bot(token=TOKEN)
dp = Dispatcher()

class PurchaseState(StatesGroup):
    waiting_for_amount = State()
    waiting_for_receipt = State()

# --- РОБОТА З БАЗОЮ ДАНИХ ---
DB_PATH = "/tmp/bot_database.db"

def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                total_stars INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Помилка ініціалізації БД: {e}")

def get_user_stars(user_id: int) -> int:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT total_stars FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else 0
    except Exception as e:
        logging.error(f"Помилка отримання зірок: {e}")
        return 0

def add_user_stars(user_id: int, stars_to_add: int):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (user_id, total_stars) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET total_stars = total_stars + ?", (user_id, stars_to_add, stars_to_add))
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Помилка додавання зірок в БД: {e}")

# Ініціалізуємо БД
init_db()

# --- КЛАВІАТУРИ ---

def get_main_menu():
    buttons = [
        [InlineKeyboardButton(text="💎 Купити зірки", callback_data="buy_stars"),
         InlineKeyboardButton(text="👤 Мій профіль", callback_data="user_profile")],
        [InlineKeyboardButton(text="💬 Написати Розробнику(найкращому другу)", url="https://t.me/aquaee")],
        [InlineKeyboardButton(text="ℹ️ Про бота", callback_data="about_bot")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_cancel_keyboard():
    buttons = [[InlineKeyboardButton(text="❌ Відміна", callback_data="cancel_payment")]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_keyboard(user_id: int, stars: int):
    buttons = [
        [
            InlineKeyboardButton(text="✅ Підтвердити", callback_data=f"confirm_{user_id}_{stars}"),
            InlineKeyboardButton(text="❌ Відхилити", callback_data=f"reject_{user_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- ХЕНДЛЕРИ ---

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 <b>звеззди бот купити платно:</b>\n\n"
        "⚡ <i>Виберіть потрібну опцію в меню нижче:</i>",
        parse_mode="HTML",
        reply_markup=get_main_menu()
    )

@dp.callback_query(F.data == "user_profile")
async def press_profile(callback: CallbackQuery):
    user_info = callback.from_user
    username = f"@{user_info.username}" if user_info.username else "немає"
    total_stars = get_user_stars(user_info.id)
    
    profile_text = (
        f"👤 <b>Мій профіль у боті:</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✨ <b>Ім'я:</b> {user_info.full_name}\n"
        f"🆔 <b>ID:</b> <code>{user_info.id}</code>\n"
        f"🏷️ <b>Юзернейм:</b> {username}\n\n"
        f"📊 <b>Куплено зірок за весь час:</b> <code>{total_stars}</code> ⭐\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    await callback.message.answer(profile_text, parse_mode="HTML", reply_markup=get_main_menu())
    await callback.answer()

@dp.callback_query(F.data == "about_bot")
async def press_about(callback: CallbackQuery):
    await callback.message.answer("<b>ℹ️ Інформація:</b>\n\бот зробленний для марк67148816 та настя67148818 ❤️", parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "buy_stars")
async def press_buy(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "🔢 <b>Введіть кількість зірок або суму в гривнях:</b>\n\n"
        "💡 <i>Приклади введення:</i>\n"
        "• <code>100</code> — бот порахує ціну в зірках \n"
        "• <code>150 грн</code> або <code>150 uah</code> — бот порахує ціну в гривнях ", 
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(PurchaseState.waiting_for_amount)
    await callback.answer()

@dp.message(PurchaseState.waiting_for_amount)
async def process_amount_input(message: Message, state: FSMContext):
    user_input = message.text.strip().lower()
    
    is_uah = False
    if "грн" in user_input or "uah" in user_input or "грв" in user_input:
        is_uah = True
    
    digits = re.findall(r'\d+', user_input)
    if not digits:
        await message.answer("⚠️ <b>Помилка! Будь ласка, введіть числове значення:</b>", parse_mode="HTML", reply_markup=get_cancel_keyboard())
        return
        
    value = int(digits[0])
    if value <= 0:
        await message.answer("⚠️ <b>Число має бути більшим за 0!</b>", parse_mode="HTML", reply_markup=get_cancel_keyboard())
        return

    if is_uah:
        total_price = float(value)
        stars_amount = int(total_price / STAR_PRICE)
        if stars_amount <= 0:
            await message.answer(f"⚠️ <b>Цієї суми замало навіть для 1 зірки!</b> (1 ⭐ = {STAR_PRICE} грн)", parse_mode="HTML", reply_markup=get_cancel_keyboard())
            return
    else:
        stars_amount = value
        total_price = round(stars_amount * STAR_PRICE, 2)
    
    await state.update_data(amount=stars_amount, price=total_price)
    
    await message.answer(
        f"📝 <b>заявка на покупку:</b> <code>{stars_amount}</code> ⭐\n"
        f"💵 <b>до сплати:</b> <code>{total_price}</code> грн\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💳 <b>для оплати скинь дєнєшку на карту:</b>\n"
        f"<code>{CARD_NUMBER}</code> <i>(нажми щоб скопійувати)</i>\n\n"
        f"📸 <b>ПІСЛЯ ОПЛАТИ:</b> надішліть сюди <u>скріншот чека</u>.\n"
        f"<i>Адміністратор (я) скоро перевірить платіж (не факт).</i>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(PurchaseState.waiting_for_receipt)

@dp.message(PurchaseState.waiting_for_receipt, F.photo)
async def process_receipt(message: Message, state: FSMContext):
    user_data = await state.get_data()
    stars_amount = user_data.get("amount", 0)
    total_price = user_data.get("price", 0.0)
    
    user_info = message.from_user
    username = f"@{user_info.username}" if user_info.username else "Немає Юзернейма"
    photo_id = message.photo[-1].file_id

    try:
        notification_text = (
            f"💰 <b>🚨 Новая заявка с ЧЕКОМ!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 <b>Пользователь:</b> {user_info.full_name} ({username})\n"
            f"🆔 <b>ID:</b> <code>{user_info.id}</code>\n"
            f"💎 <b>Количество звёзд:</b> <code>{stars_amount}</code> ⭐\n"
            f"💵 <b>Сумма в грн:</b> <code>{total_price}</code> грн\n\n"
            f"📋 <i>Чек прикреплен ниже. Проверь банк и нажми кнопку:</i>"
        )
        
        await bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo_id,
            caption=notification_text,
            parse_mode="HTML",
            reply_markup=get_admin_keyboard(user_info.id, stars_amount)
        )
    except Exception as e:
        logging.error(f"Не удалось отправить чек админу: {e}")

    await message.answer(
        "✨ <b>Чек успішно завантажено та відправленно Адміністратору @aquaee.</b>\n\n"
        "⏳ Очікуйте перевірки та зарахування зірок найближчим часом.",
        parse_mode="HTML"
    )
    await state.clear()

@dp.message(PurchaseState.waiting_for_receipt)
async def process_receipt_wrong_format(message: Message):
    await message.answer("⚠️ Будь ласка, надішліть саме <b>скріншот чека фоткою</b>:", parse_mode="HTML", reply_markup=get_cancel_keyboard())

@dp.callback_query(F.data == "cancel_payment")
async def press_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("❌ <b>Покупка отмена.</b>", parse_mode="HTML", reply_markup=get_main_menu())
    await callback.answer()

# --- ОБРАБОТКА ДЕЙСТВИЙ АДМИНИСТРАТОРА ---

@dp.callback_query(F.data.startswith("confirm_"))
async def admin_confirm_payment(callback: CallbackQuery):
    data_parts = callback.data.split("_")
    target_user_id = int(data_parts[1])
    stars = int(data_parts[2])
    
    try:
        add_user_stars(target_user_id, stars)
        
        await bot.send_message(
            chat_id=target_user_id,
            text=f"✨ <b>Ваш платёж успішно підтверджений!</b>\n\n"
                 f"🎉 Адміністратор нарахував вам <b>{stars} ⭐</b>. Дякуємо за покупку!",
            parse_mode="HTML"
        )
        await bot.edit_message_caption(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            caption=callback.message.caption + f"\n\n✅ <b>Статус: Подтверждено! В базу зачислено {stars} звёзд.</b>",
            parse_mode="HTML"
        )
    except Exception as e:
        await callback.message.answer(f"Ошибка отправки пользователю: {e}")
    
    await callback.answer()

@dp.callback_query(F.data.startswith("reject_"))
async def admin_reject_payment(callback: CallbackQuery):
    target_user_id = int(callback.data.split("_")[1])
    
    try:
        await bot.send_message(
            chat_id=target_user_id,
            text="⚠️ <b>Помилка підтвердження платежу!</b>\n\n"
                 "Администратор отклонил заявку. Перевірте чек или напишіть в підтримку.",
            parse_mode="HTML"
        )
        await bot.edit_message_caption(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            caption=callback.message.caption + "\n\n❌ <b>Статус: Отклонено тобой!</b>",
            parse_mode="HTML"
        )
    except Exception as e:
        await callback.message.answer(f"Ошибка отправки пользователю: {e}")
        
    await callback.answer()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
