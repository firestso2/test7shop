from aiogram import Router, F
from aiogram.types import CallbackQuery
from database import get_referral_stats
from keyboards import referral_kb
from config import REFERRAL_PERCENT

router = Router()

@router.callback_query(F.data == "referral")
async def referral_menu(call: CallbackQuery):
    user_id = call.from_user.id
    invited, earned = await get_referral_stats(user_id)
    bot_info = await call.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    text = (f"👥 <b>Реф€р@льн@я с1стем@</b>\n\n"
            f"🔗 <b>Ваша ссылка:</b>\n<code>{ref_link}</code>\n\n"
            f"📊 <b>Ст@тистик@:</b>\n"
            f"├ Пр0цент: <b>{REFERRAL_PERCENT}%</b>\n"
            f"├ Пригл@шено: <b>{invited}</b> чел.\n"
            f"└ З@р@б0тано: <b>${earned:.2f}</b>\n\n"
            f"ℹ️ Вы п0луч@ете {REFERRAL_PERCENT}% 0т к@жд0й п0купки п0 вашей ссылке.")
    try:
        await call.message.edit_text(text, reply_markup=referral_kb(), parse_mode="HTML")
    except:
        await call.message.answer(text, reply_markup=referral_kb(), parse_mode="HTML")
    await call.answer()
