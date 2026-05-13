import re
from aiogram import Router, F, Bot
from aiogram.types import Message
from database import has_review_reward, mark_review_rewarded, create_coupon, get_all_admin_ids
import random, string
from config import REVIEWS_CHAT_ID

router = Router()

# Паттерн: "+реп @vorache777" в любом месте текста
REVIEW_PATTERN = re.compile(r"\+\s*реп\s+@vorache777", re.IGNORECASE)

def gen_code():
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
                "Перепишите отзыв и прикрепите скрин покупки/верификации.\n"
                "Формат: <code>+реп @vorache777, верифнул [сервис]...</code> + фото",
                parse_mode="HTML"
            )
        except:
            pass
        return

    if await has_review_reward(user_id):
        try:
            await message.reply("ℹ️ Вы уже получали купон за отзыв. Спасибо!")
        except:
            pass
        return

    code = gen_code()
    await create_coupon(code, discount_percent=10, uses=3, owner_id=user_id)
    await mark_review_rewarded(user_id)

    try:
        await bot.send_message(
            user_id,
            f"🎉 <b>Спасибо за отзыв!</b>\n\n"
            f"Ваш купон на скидку <b>10%</b> (3 использования):\n"
            f"<code>{code}</code>\n\n"
            f"Используйте в разделе «👤 Пр0ф1ль» → «🎫 М0и скидки».",
            parse_mode="HTML"
        )
        await message.react([{"type": "emoji", "emoji": "🔥"}])
    except:
        pass

    admin_ids = await get_all_admin_ids()
    for aid in admin_ids:
        try:
            await bot.send_message(
                aid,
                f"✅ Купон за отзыв выдан\nUser: <code>{user_id}</code>\nКупон: <code>{code}</code>",
                parse_mode="HTML"
            )
        except:
            pass
