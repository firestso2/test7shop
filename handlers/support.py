from aiogram import Router, F
from aiogram.types import Message
from config import SUPPORT_CONTACT

router = Router()


@router.message(F.text == "🆘 Поддержка")
async def support_menu(message: Message):
    await message.answer(
        f"🆘 <b>Поддержка</b>\n\n"
        f"Есть вопросы или проблемы?\n"
        f"Напишите нам — ответим быстро!\n\n"
        f"👤 {SUPPORT_CONTACT}",
        parse_mode="HTML"
    )
