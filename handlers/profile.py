from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from database import get_user, register_user
from keyboards import profile_kb
from utils import fmt_date

router = Router()

async def show_profile(target, user_id):
    user = await get_user(user_id)
    if not user:
        await register_user(user_id, "")
        user = await get_user(user_id)
    text = (f"👤 <b>Ваш пр0ф1ль</b>\n\n"
            f"🆔 <b>ID:</b> <code>{user['tg_id']}</code>\n"
            f"💰 <b>Б@ланс:</b> ${user['balance']:.2f}\n"
            f"🛒 <b>П0купок:</b> {user['purchases_count']}\n"
            f"💸 <b>Потр@чено:</b> ${user['total_spent']:.2f}\n"
            f"📅 <b>Рег1стр@ция:</b> {fmt_date(user['registered_at'])}")
    if isinstance(target, Message):
        await target.answer(text, reply_markup=profile_kb(), parse_mode="HTML")
    else:
        try:
            await target.message.edit_text(text, reply_markup=profile_kb(), parse_mode="HTML")
        except:
            await target.message.answer(text, reply_markup=profile_kb(), parse_mode="HTML")

@router.message(F.text == "👤 Пр0ф1ль")
async def profile_menu(message: Message):
    await show_profile(message, message.from_user.id)

@router.callback_query(F.data == "back:profile")
async def back_profile(call: CallbackQuery):
    await show_profile(call, call.from_user.id)
    await call.answer()
