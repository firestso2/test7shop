from aiogram import Router, F
from aiogram.types import Message
from config import SUPPORT_CONTACT

router = Router()

@router.message(F.text == "🆘 П0ддержк@")
async def support_menu(message: Message):
    await message.answer(
        f"🆘 <b>П0ддержк@</b>\n\nЕсть вопр0сы или пр0блемы?\nНап1ш1те нам — 0тветим быстро!\n\n👤 {SUPPORT_CONTACT}",
        parse_mode="HTML"
    )
