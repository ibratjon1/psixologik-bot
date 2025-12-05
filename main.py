# main.py — 100% FINAL VERSIYA
# Murojaat tepasida + Javob berish bosilganda ham ISM + USERNAME HAR DOIM KO'RINADI!

import asyncio
import logging
import pandas as pd
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    FSInputFile
)
import aiosqlite
import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN topilmadi!")

# ADMINLAR — faqat ular murojaatlarni ko'radi va javob beradi
ADMINS = [2026280202,5348194727]  # <-- O'zingizning Telegram ID raqamingiz

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
dp["reply_mode"] = {}  # {admin_id: student_id}

DB_NAME = "students.db"
EXCEL_FILE = "talabalar_royxati.xlsx"

TEXTS = {
    "uz": {
        "choose_lang": "Tilni tanlang:",
        "faculty": "Fakultetni tanlang:",
        "group": "Guruhingizni yozing (masalan: K.AT-22-01):",
        "full_name": "Familiya va ismingizni kiriting (masalan: To‘rayev Jasurbek):",
        "registered": "Roʻyxatdan muvaffaqiyatli oʻtdingiz!",
        "welcome": "Xush kelibsiz!",
        "admin_welcome": "Salom, psixolog!",
        "appeal_btn": "Psixologga murojaat qilish",
        "send_appeal": "Murojaatingizni yuboring...\n\n(Maxfiylik saqlanadi)",
        "appeal_sent": "Murojaatingiz yuborildi!\n(Maxfiylik saqlanadi)",
        "new_appeal": "YANGI MUROJAAT",
        "excel_btn": "Roʻyxatni yuklab olish",
        "reply_sent": "Javob yuborildi!",
        "blocked": "Talaba botni bloklagan",
        "cancel": "Bekor qilish"
    },
    "ru": {
        "choose_lang": "Выберите язык:", "faculty": "Выберите факультет:", "group": "Напишите группу:",
        "full_name": "Введите фамилию и имя:", "registered": "Вы зарегистрированы!", "welcome": "Добро пожаловать!",
        "admin_welcome": "Здравствуйте, психолог!", "appeal_btn": "Обратиться к психологу",
        "send_appeal": "Отправьте ваше сообщение...\n\n(Конфиденциальность сохраняется)",
        "appeal_sent": "Сообщение отправлено!\n(Конфиденциальность сохраняется)",
        "new_appeal": "НОВОЕ ОБРАЩЕНИЕ", "excel_btn": "Скачать список", "reply_sent": "Ответ отправлен!",
        "blocked": "Студент заблокировал бота", "cancel": "Отмена"
    },
    "en": {
        "choose_lang": "Choose language:", "faculty": "Choose faculty:", "group": "Enter your group:",
        "full_name": "Enter your full name:", "registered": "Registration successful!", "welcome": "Welcome!",
        "admin_welcome": "Hello, psychologist!", "appeal_btn": "Contact psychologist",
        "send_appeal": "Send your message...\n\n(Privacy is protected)",
        "appeal_sent": "Message sent!\n(Privacy is protected)",
        "new_appeal": "NEW APPEAL", "excel_btn": "Download list", "reply_sent": "Reply sent!",
        "blocked": "Student blocked bot", "cancel": "Cancel"
    }
}

FACULTIES = [
    "Tibbiyot fakulteti", "Filologiya fakulteti",
    "Ijtimoiy fanlar va raqamli texnologiyalar fakulteti",
    "Iqtisodiyot fakulteti", "Maktabgacha va maktab ta'limi fakulteti"
]

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS students (
                user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT,
                faculty TEXT, group_name TEXT, lang TEXT DEFAULT 'uz'
            )
        ''')
        await db.commit()

def menu(lang: str, admin: bool = False):
    t = TEXTS[lang]
    kb = [[KeyboardButton(text=t["appeal_btn"])]]
    if admin:
        kb.append([KeyboardButton(text=t["excel_btn"])])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

class Reg(StatesGroup):
    faculty = State()
    group = State()
    full_name = State()

@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT lang FROM students WHERE user_id=?", (uid,)) as cur:
            row = await cur.fetchone()
    if row:
        lang = row[0]
        await message.answer(
            TEXTS[lang]["welcome"] if uid not in ADMINS else TEXTS[lang]["admin_welcome"],
            reply_markup=menu(lang, uid in ADMINS)
        )
        return

    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="O‘zbek tili")],
        [KeyboardButton(text="Русский язык")],
        [KeyboardButton(text="English")]
    ], resize_keyboard=True, one_time_keyboard=True)
    await message.answer("Tilni tanlang / Выберите язык / Choose language:", reply_markup=kb)

@dp.message(F.text.in_(["O‘zbek tili", "Русский язык", "English"]))
async def set_lang(message: types.Message, state: FSMContext):
    lmap = {"O‘zbek tili":"uz", "Русский язык":"ru", "English":"en"}
    lang = lmap[message.text]
    user = message.from_user
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR REPLACE INTO students (user_id, username, lang) VALUES (?,?,?)",
                        (user.id, user.username or "", lang))
        await db.commit()
    await message.answer(TEXTS[lang]["faculty"], reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=f)] for f in FACULTIES],
        resize_keyboard=True, one_time_keyboard=True))
    await state.update_data(lang=lang)
    await state.set_state(Reg.faculty)

@dp.message(Reg.faculty)
async def fac(message: types.Message, state: FSMContext):
    if message.text not in FACULTIES:
        data = await state.get_data()
        return await message.answer(TEXTS[data["lang"]]["faculty"])
    await state.update_data(faculty=message.text)
    data = await state.get_data()
    await message.answer(TEXTS[data["lang"]]["group"], reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(Reg.group)

@dp.message(Reg.group)
async def grp(message: types.Message, state: FSMContext):
    await state.update_data(group=message.text.strip().upper())
    data = await state.get_data()
    await message.answer(TEXTS[data["lang"]]["full_name"])
    await state.set_state(Reg.full_name)

@dp.message(Reg.full_name)
async def get_fullname(message: types.Message, state: FSMContext):
    full_name = message.text.strip().title()
    if len(full_name.split()) < 2:
        data = await state.get_data()
        return await message.answer("Iltimos, familiya va ismni to‘liq kiriting!")
    data = await state.get_data()
    lang, faculty, group = data["lang"], data["faculty"], data["group"]
    user = message.from_user

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE students SET full_name=?, faculty=?, group_name=? WHERE user_id=?",
                        (full_name, faculty, group, user.id))
        await db.commit()

    row = {"Familiya Ism": full_name, "Username": f"@{user.username}" if user.username else "—",
           "Fakultet": faculty, "Guruh": group, "Til": lang.upper(),
           "Vaqt": datetime.now().strftime("%d.%m.%Y %H:%M")}
    df = pd.DataFrame([row])
    if os.path.exists(EXCEL_FILE):
        df = pd.concat([pd.read_excel(EXCEL_FILE), df], ignore_index=True)
    df.to_excel(EXCEL_FILE, index=False)

    await message.answer(TEXTS[lang]["registered"], reply_markup=menu(lang))
    await state.clear()

@dp.message(F.text.regexp(r"(Psixologga murojaat qilish|Обратиться к психологу|Contact psychologist)"))
async def appeal_btn(message: types.Message):
    if message.from_user.id in ADMINS:
        return await message.answer("Siz psixologsiz.")
    lang = "uz"
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT lang FROM students WHERE user_id=?", (message.from_user.id,)) as cur:
            r = await cur.fetchone()
            if r: lang = r[0]
    await message.answer(TEXTS[lang]["send_appeal"])

# HAR QANDAY XABAR = MUROJAAT
@dp.message()
async def all_messages(message: types.Message):
    uid = message.from_user.id

    # ADMIN JAVOB REJIMIDA
    if uid in ADMINS and uid in dp["reply_mode"]:
        student_id = dp["reply_mode"][uid]
        try:
            async with aiosqlite.connect(DB_NAME) as db:
                async with db.execute("SELECT lang FROM students WHERE user_id=?", (student_id,)) as cur:
                    row = await cur.fetchone()
                    s_lang = row[0] if row else "uz"
            await bot.copy_message(
                chat_id=student_id, from_chat_id=message.chat.id, message_id=message.message_id,
                caption=f"Psixologdan javob:\n\n{message.caption or ''}",
                reply_markup=menu(s_lang)
            )
            await message.answer(TEXTS["uz"]["reply_sent"])
        except:
            await message.answer(TEXTS["uz"]["blocked"])
        del dp["reply_mode"][uid]
        return

    # TALABA MA'LUMOTLARI
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT full_name, faculty, group_name, lang FROM students WHERE user_id=?", (uid,)) as cur:
            row = await cur.fetchone()
            if not row:
                return await message.answer("Avval /start orqali roʻyxatdan oʻting.")
            full_name, faculty, group, lang = row

    # REAL VAQTDAGI USERNAME
    current_username = message.from_user.username
    username_display = f"@{current_username}" if current_username else "Username yoʻq"

    # MUROJAAT TEPASIDA KO'RINADIGAN MATN
    header = (
        f"<b>{TEXTS[lang]['new_appeal']}</b>\n\n"
        f"<b>Ism:</b> {full_name}\n"
        f"<b>Username:</b> {username_display}\n"
        f"<b>Fakultet:</b> {faculty}\n"
        f"<b>Guruh:</b> {group}\n"
        f"<b>ID:</b> <code>{uid}</code>"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Javob berish", callback_data=f"rep_{uid}")
    ]])

    for admin_id in ADMINS:
        try:
            await bot.send_message(admin_id, header, parse_mode="HTML", reply_markup=keyboard)
            if message.content_type == types.ContentType.TEXT:
                await bot.send_message(admin_id, message.text)
            else:
                await message.forward(admin_id)
        except Exception as e:
            print("Xato:", e)

    await message.answer(TEXTS[lang]["appeal_sent"], reply_markup=menu(lang))

# YANGI — JAVOB BERISH BOSILGANDA ISM YO'QOLMAYDI!
@dp.callback_query(F.data.startswith("rep_"))
async def reply(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMINS:
        return await callback.answer("Ruxsat yoʻq!", show_alert=True)

    student_id = int(callback.data.split("_")[1])
    dp["reply_mode"][callback.from_user.id] = student_id

    # Talaba ma'lumotlarini olish
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT full_name, faculty, group_name FROM students WHERE user_id=?", (student_id,)) as cur:
            row = await cur.fetchone()
            full_name = row[0] if row else "Noma'lum talaba"
            faculty = row[1] if row and row[1] else "—"
            group = row[2] if row and row[2] else "—"

    # Real vaqtda username
    try:
        user = await bot.get_chat(student_id)
        username_disp = f"@{user.username}" if user.username else "Username yoʻq"
    except:
        username_disp = "Username yoʻq"

    reply_text = (
        f"<b>Javob yozmoqdasiz:</b>\n\n"
        f"<b>Ism:</b> {full_name}\n"
        f"<b>Username:</b> {username_disp}\n"
        f"<b>Fakultet:</b> {faculty}\n"
        f"<b>Guruh:</b> {group}\n"
        f"<b>ID:</b> <code>{student_id}</code>\n\n"
        f"<i>Javobingizni yozing:</i>"
    )

    markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Bekor qilish", callback_data="cancel_rep")
    ]])

    try:
        await callback.message.edit_message_text(reply_text, parse_mode="HTML", reply_markup=markup)
    except:
        await bot.send_message(callback.from_user.id, reply_text, parse_mode="HTML", reply_markup=markup)

    await callback.answer("Javob rejimi yoqildi")

@dp.callback_query(F.data == "cancel_rep")
async def cancel(callback: types.CallbackQuery):
    if callback.from_user.id in dp["reply_mode"]:
        del dp["reply_mode"][callback.from_user.id]
    await callback.message.edit_text("Bekor qilindi.")
    await callback.answer()

@dp.message(F.text.regexp(r"(Roʻyxatni yuklab olish|Скачать список|Download list)"))
async def excel(message: types.Message):
    if message.from_user.id not in ADMINS:
        return
    if not os.path.exists(EXCEL_FILE):
        return await message.answer("Hali talabalar yoʻq")
    await bot.send_document(message.chat.id, FSInputFile(EXCEL_FILE), caption="Talabalar roʻyxati")

async def main():
    await init_db()
    print("BOT ISHGA TUSHDI → Murojaatda ham, javob berishda ham ISM + USERNAME HAR DOIM KO'RINADI!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())