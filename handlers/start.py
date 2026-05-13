from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from database import get_user, register_user, get_setting
from keyboards import main_menu_kb
from config import WELCOME_PHOTO, SHOP_NAME
from utils import log_event

router = Router()

async def send_main_menu(message: Message):
    welcome_text = await get_setting("welcome_text") or "Добро пожаловать! 🛒"
    text = f"🏪 <b>{SHOP_NAME}</b>\n\n{welcome_text}"
    if WELCOME_PHOTO:
        await message.answer_photo(photo=WELCOME_PHOTO, caption=text, reply_markup=main_menu_kb(), parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=main_menu_kb(), parse_mode="HTML")

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            ref = int(args[1][4:])
            if ref != user.id: referrer_id = ref
        except ValueError: pass
    if not await get_user(user.id):
        await register_user(user.id, user.username or "", referrer_id)
        log_event("NEW_USER", user.id, f"ref={referrer_id}")
    await send_main_menu(message)

@router.message(F.text == "🏠 Гл@вн0е мен@")
async def go_main(message: Message, state: FSMContext):
    await state.clear()
    await send_main_menu(message)

@router.callback_query(F.data == "main_menu")
async def cb_main_menu(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.delete()
    await send_main_menu(call.message)
    await call.answer()
