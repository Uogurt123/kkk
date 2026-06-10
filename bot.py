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

# --- КУРС ЗВЕЗДЫ (1 звезда = 0.85 грн). Можешь поменять тут ---
STAR_PRICE = 0.85 

logging.basicConfig(level=logging.INFO)

if not TOKEN or not ADMIN_ID:
    raise ValueError("Переменные BOT_TOKEN или ADMIN_ID не заданы в настройках Railway!")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Обновили состояния: теперь ждем количество, а потом скриншот
class PurchaseState(StatesGroup):
    waiting_for_stars = State()
    waiting_for_receipt = State()

# --- КЛАВИАТУРЫ ---

def get_main_menu():
    buttons = [
        [InlineKeyboardButton(text="💎 Купити зірки", callback_data="buy_stars")],
        [InlineKeyboardButton(text="💬 Написати Розробнику(генію тому хто сам тримає вогник і взагалі legenda)", url="https://t.me/aquaee")],
        [InlineKeyboardButton(text="ℹ️ Про бота", callback_data="about_bot")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_cancel_keyboard():
    buttons = [[InlineKeyboardButton(text="❌ Відміна", callback_data="cancel_payment")]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Кнопки под фоткой чека для тебя (админа)
def get_admin_keyboard(user_id: int, stars: str, total_price: float):
    buttons = [
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{user_id}_{stars}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{user_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- ХЕНДЛЕРЫ ---

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 <b>#абжджа8ог98аолдаво звезди купи пж:</b>\n\n"
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
    await callback.message.answer(
        "🔢 <b>Кількість зірок (наприклад: 50, 100, 250):</b>", 
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(PurchaseState.waiting_for_stars)
    await callback.answer()

@dp.message(PurchaseState.waiting_for_stars)
async def process_stars_amount(message: Message, state: FSMContext):
    stars_amount = message.text.strip()
    if not stars_amount.isdigit():
        await message.answer("⚠️ <b>тільки цифри :</b>", parse_mode="HTML", reply_markup=get_cancel_keyboard())
        return
    
    # Считаем итоговую цену автоматический калькулятор
    total_price = round(int(stars_amount) * STAR_PRICE, 2)
    
    await state.update_data(amount=stars_amount, price=total_price)
    
    await message.answer(
        f"📝 <b>заявка на покупку:</b> <code>{stars_amount}</code> ⭐\n"
        f"💵 <b>до сплати:</b> <code>{total_price}</code> грн\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💳 <b>для оплати скинь дєнєшку на карту:</b>\n"
        f"<code>{CARD_NUMBER}</code> <i>(нажми щоб скопійувати)</i>\n\n"
        f"📸 <b>ПІСЛЯ ОПЛАТИ:</b> надішліть сюди <u>скріншот чека</u> (фоткою).\n"
        f"<i>Адміністратор (я) скоро перевірить платіж (не факт).</i>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    # Переводим бота в режим ожидания скриншота чека
    await state.set_state(PurchaseState.waiting_for_receipt)

# Хендлер, который ловит скриншот чека
@dp.message(PurchaseState.waiting_for_receipt, F.photo)
async def process_receipt(message: Message, state: FSMContext):
    user_data = await state.get_data()
    stars_amount = user_data.get("amount", "Невідомо")
    total_price = user_data.get("price", 0.0)
    
    user_info = message.from_user
    username = f"@{user_info.username}" if user_info.username else "Немає Юзернейма"
    
    # Самое большое разрешение фотки берем
    photo_id = message.photo[-1].file_id

    try:
        # Текст уведомления для тебя
        notification_text = (
            f"💰 <b>🚨 Новая заявка с ЧЕКОМ!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 <b>Пользователь:</b> {user_info.full_name} ({username})\n"
            f"🆔 <b>ID:</b> <code>{user_info.id}</code>\n"
            f"💎 <b>Количество звёзд:</b> <code>{stars_amount}</code> ⭐\n"
            f"💵 <b>Сумма в грн:</b> <code>{total_price}</code> грн\n\n"
            f"📋 <i>Чек прикреплен ниже. Проверь банк и нажми кнопку:</i>"
        )
        
        # Отправляем тебе ФОТОГРАФИЮ чека с текстом и пультиком управления
        await bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo_id,
            caption=notification_text,
            parse_mode="HTML",
            reply_markup=get_admin_keyboard(user_info.id, stars_amount, total_price)
        )
    except Exception as e:
        logging.error(f"Не удалось отправить чек админу: {e}")

    await message.answer(
        "✨ <b>Чек успішно завантажено та відправленно Адміністратору @aquaee.</b>\n\n"
        "⏳ Очікуйте перевірки та зарахування зірок найближчим часом.",
        parse_mode="HTML"
    )
    await state.clear()

# Если вместо фотки прислали текст, просим именно фото
@dp.message(PurchaseState.waiting_for_receipt)
async def process_receipt_wrong_format(message: Message):
    await message.answer("⚠️ Будь ласка, надішліть саме <b>скріншот чека фоткою</b>:", parse_mode="HTML", reply_markup=get_cancel_keyboard())

@dp.callback_query(F.data == "cancel_payment")
async def press_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("❌ <b>Покупка отмена.</b>", parse_mode="HTML", reply_markup=get_main_menu())
    await callback.answer()

# --- ОБРАБОТКА ДЕЙСТВИЙ АДМИНИСТРАТОРА (ТЕБЯ) ---

@dp.callback_query(F.data.startswith("confirm_"))
async def admin_confirm_payment(callback: CallbackQuery):
    # Разбираем callback: confirm_{user_id}_{stars}
    data_parts = callback.data.split("_")
    target_user_id = int(data_parts[1])
    stars = data_parts[2]
    
    try:
        await bot.send_message(
            chat_id=target_user_id,
            text=f"✨ <b>Ваш платёж успішно підтверджений!</b>\n\n"
                 f"🎉 Адміністратор нарахував вам <b>{stars} ⭐</b>. Дякуємо за покупку!",
            parse_mode="HTML"
        )
        # Меняем описание у фотки в твоем чате
        await bot.edit_message_caption(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            caption=callback.message.caption + f"\n\n✅ <b>Статус: Подтверждено! Начислено {stars} звёзд.</b>",
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
