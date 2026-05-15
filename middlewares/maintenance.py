from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from database import get_user, get_setting, get_all_admin_ids

class MaintenanceMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        admin_ids = await get_all_admin_ids()
        user = getattr(event, "from_user", None)
        if user and user.id in admin_ids:
            return await handler(event, data)
        if await get_setting("maintenance_mode") == "1":
            text = await get_setting("maintenance_text") or "🔧 Бот на техобслуживании."
            if isinstance(event, Message): await event.answer(text)
            elif isinstance(event, CallbackQuery): await event.answer(text, show_alert=True)
            return
        if user:
            db_user = await get_user(user.id)
            if db_user and db_user["is_banned"]:
                if isinstance(event, Message): await event.answer("🚫 Вы заблокированы.")
                elif isinstance(event, CallbackQuery): await event.answer("🚫 Вы заблокированы.", show_alert=True)
                return
        return await handler(event, data)
