import re
import random
import string
from aiogram import Router, F, Bot
from aiogram.types import Message
from database import has_review_reward, mark_review_rewarded, create_coupon, get_all_admin_ids
from config import REVIEWS_CHAT_ID

router = Router()

REVIEW_PATTERN = re.compile(r"\+\s*реп\s+@vorache777", re.IGNORECASE)


def gen_code() -> str:
    return "REV-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=7))


@router.message(F.chat.id == REVIEWS_CHAT_ID)
async def handle_chat_review(message: Message, bot: Bot):
    text = message.text or message.caption or ""
    if not REVIEW_PATTERN.search(text):
        return

    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return

    has_photo = bool(message.photo)

    if not has_photo:
        try:
            await message.reply(
                "⚠️ <b>Отзыв без скриншота не засчитывается!</b>\n\n"
                "Перепишите отзыв и прикрепите скриншот покупки или верификации.\n\n"
                "Формат:\n"
                "<code>+реп @vorache777, верифнул [сервис]...</code> + фото",
                parse_mode="HTML"
            )
        except Exception:
            pass
        return

    if await has_review_reward(user_id):
        try:
            await message.reply("ℹ️ Вы уже получали купон за отзыв. Спасибо!")
        except Exception:
            pass
        return

    code = gen_code()
    await create_coupon(code, discount_percent=10, uses=3, owner_id=user_id)
    await mark_review_rewarded(user_id)

    try:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎫 Использовать купон", callback_data="my_discounts")]
        ])
        await bot.send_message(
            user_id,
            f"🎉 <b>Спасибо за отзыв!</b>\n\n"
            f"Ваш купон на скидку <b>10%</b> (3 использования):\n"
            f"<code>{code}</code>\n\n"
            f"Используйте в разделе «Профиль» → «Мои скидки».",
            reply_markup=kb,
            parse_mode="HTML"
        )
        await message.react([{"type": "emoji", "emoji": "🔥"}])
    except Exception:
        pass

    admin_ids = await get_all_admin_ids()
    for aid in admin_ids:
        try:
            await bot.send_message(
                aid,
                f"✅ Купон за отзыв выдан\n"
                f"User: <code>{user_id}</code>\n"
                f"Купон: <code>{code}</code>",
                parse_mode="HTML"
            )
        except Exception:
            pass
