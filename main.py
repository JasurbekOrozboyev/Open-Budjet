import asyncio
import sqlite3
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import ReplyKeyboardBuilder, KeyboardButton, InlineKeyboardBuilder

BOT_TOKEN = "8432580679:AAFMQ8vnRdE4Wi1TWvnAmT8IzuDtu7SZlIg" 

conn = sqlite3.connect('users.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    phone_number TEXT,
    voted BOOLEAN DEFAULT 0
)
''')
cursor.execute('''
CREATE TABLE IF NOT EXISTS cards (
    user_id INTEGER PRIMARY KEY,
    card_number TEXT
)
''')
conn.commit()

# State machine for user input
class UserState(StatesGroup):
    waiting_for_phone = State()
    waiting_for_vote_confirmation = State()
    waiting_for_card_number = State()

# Bot and Dispatcher objects
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Function to create the main menu (Reply Keyboard)
def get_main_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="🗳️ Ovoz berish"))
    builder.row(
        KeyboardButton(text="💰 Balans"),
        KeyboardButton(text="💸 Pulni yechib olish")
    )
    builder.row(KeyboardButton(text="🔗 Referral ssilka"))
    return builder.as_markup(resize_keyboard=True)

# Function to create the confirmation menu (Reply Keyboard)
def get_confirmation_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="✅ Ovoz berdim"),
        KeyboardButton(text="❌ Bekor qilish")
    )
    return builder.as_markup(resize_keyboard=True)

# /start command handler
@dp.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    welcome_message = (
        "Assalomu alaykum!👋 Botimizga xush kelibsiz.\n\n"
        "✅Open Budjet"
    )
    await message.answer(
        welcome_message,
        reply_markup=get_main_menu()
    )

# "Ovoz berish" button handler
@dp.message(F.text == "🗳️ Ovoz berish")
async def vote_handler(message: types.Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    
    cursor.execute("SELECT voted FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()

    if user_data and user_data[0]:
        await message.answer("✅Siz allaqachon ovoz bergansiz!")
    else:
        await message.answer("Iltimos, ovoz berish uchun telefon raqamingizni yuboring (masalan, 998901234567):")
        await state.set_state(UserState.waiting_for_phone)

# "Balans" button handler with card number request
@dp.message(F.text == "💰 Balans")
async def balance_handler(message: types.Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    
    # Check if user has a card number saved
    cursor.execute("SELECT card_number FROM cards WHERE user_id = ?", (user_id,))
    card_data = cursor.fetchone()

    if card_data:
        await message.answer(f"Pul berilmaydi mahalla uchun ovoz bering! (Ohunboboyev) "
                             f"")
    else:
        await message.answer("Pul berilmaydi mahalla uchun ovoz bering! (Ohunboboyev)")
        await state.set_state(UserState.waiting_for_card_number)

# Handler for "Pulni yechib olish"
@dp.message(F.text == "💸 Pulni yechib olish")
async def withdraw_handler(message: types.Message) -> None:
    await message.answer("⚠️ Pul berilmaydi mahalla uchun ovoz bering! (Ohunboboyev)!")

# "Referral ssilka" button handler with corrected bot username
@dp.message(F.text == "🔗 Referral ssilka")
async def referral_handler(message: types.Message) -> None:
    user_id = message.from_user.id
    # Updated bot username
    # referral_link = f"https://t.me/ochiqbudjet_5_bot?start={user_id}" 
    await message.answer(f"Referal ssilka yo'q!")

# Handler to process the user's phone number
@dp.message(UserState.waiting_for_phone, F.text)
async def process_phone_number(message: types.Message, state: FSMContext) -> None:
    phone_number = message.text.strip()
    user_id = message.from_user.id

    if re.fullmatch(r"998\d{9}", phone_number):
        try:
            # Store phone number in FSM context
            await state.update_data(phone=phone_number)
            
            # Create inline keyboard with two buttons
            builder = InlineKeyboardBuilder()
            builder.row(
                types.InlineKeyboardButton(text="🤖 Bot orqali ovoz berish", url="https://t.me/ochiqbudjet_4_bot?start=052404808012")
               
            )
            builder.row(
                 types.InlineKeyboardButton(text="🌐 Sayt orqali ovoz berish", url="https://openbudget.uz/boards/initiatives/initiative/52/70475793-5177-4730-9293-5cb56d941661"),
            )

            await message.answer(
                "Pastdagi 🌐 Sayt orqali yoki 🤖 Bot orqali ovoz berish tugmasini bosib ovozingizni bering.\n\n"
                "Ovoz berib bo'lgandan so'ng botga qayting va '✅ Ovoz berdim' tugmasini bosing!",
                reply_markup=builder.as_markup()
            )
            await state.set_state(UserState.waiting_for_vote_confirmation)

        except Exception as e:
            await message.answer(f"Xatolik yuz berdi: {e}")
            await state.clear()
    else:
        await message.answer("Noto'g'ri raqam formati. Iltimos, raqamni 998901234567 shaklida to'g'ri kiriting.")
        await state.set_state(UserState.waiting_for_phone)

# Handler for card number input
@dp.message(UserState.waiting_for_card_number, F.text)
async def process_card_number(message: types.Message, state: FSMContext) -> None:
    card_number = message.text.strip()
    user_id = message.from_user.id

    if re.fullmatch(r"\d{16}", card_number):
        try:
            cursor.execute("INSERT OR REPLACE INTO cards (user_id, card_number) VALUES (?, ?)", (user_id, card_number))
            conn.commit()
            await message.answer("Karta raqamingiz muvaffaqiyatli saqlandi!", reply_markup=get_main_menu())
            await state.clear()
        except sqlite3.Error as e:
            await message.answer(f"Xatolik yuz berdi: {e}", reply_markup=get_main_menu())
            await state.clear()
    else:
        await message.answer("Noto'g'ri karta raqami formati. Iltimos, 16 xonali raqam kiriting.")
        await state.set_state(UserState.waiting_for_card_number)

# Handler for "Ovoz berdim" button
@dp.message(F.text == "✅ Ovoz berdim", UserState.waiting_for_vote_confirmation)
async def confirm_vote_handler(message: types.Message, state: FSMContext) -> None:
    user_data = await state.get_data()
    phone_number = user_data.get("phone")
    user_id = message.from_user.id

    if phone_number:
        try:
            cursor.execute("INSERT OR REPLACE INTO users (user_id, phone_number, voted) VALUES (?, ?, ?)", (user_id, phone_number, 1))
            conn.commit()
            await message.answer("Rahmat, ovozingiz qabul qilindi!")
        except sqlite3.Error as e:
            await message.answer(f"Xatolik yuz berdi: {e}")
    else:
        await message.answer("Ma'lumot topilmadi. Qaytadan urinib ko'ring.")
    
    await state.clear()
    await message.answer("Bosh menyuga qaytishingiz mumkin.", reply_markup=get_main_menu())

# Handler for "Bekor qilish" button
@dp.message(F.text == "❌ Bekor qilish", UserState.waiting_for_vote_confirmation)
async def cancel_vote_handler(message: types.Message, state: FSMContext) -> None:
    await message.answer("Ovoz berish bekor qilindi.", reply_markup=get_main_menu())
    await state.clear()

# Main function to run the bot
async def main() -> None:
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        conn.close() 
