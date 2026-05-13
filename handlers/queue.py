from aiogram import Router, F
from aiogram.types import CallbackQuery
from database import get_queue_position, get_queue_by_order_num, get_order_by_num
from keyboards import queue_refresh_kb

router = Router()

@router.callback_query(F.data.startswith("queue_refresh:"))
async def refresh_queue(call: CallbackQuery):
    order_num = int(call.data.split(":")[1])
    order = await get_order_by_num(order_num)
    if not order or order["user_id"] != call.from_user.id:
        await call.answer("❌ Заказ не найден.", show_alert=True)
        return

    q = await get_queue_by_order_num(order_num)
    if not q:
        await call.answer("Заказ не в очереди.", show_alert=True)
        return

    if q["status"] == "done":
        await call.message.edit_text(
            f"✅ <b>Ваша верификация по заказу #{order_num} выполнена!</b>\n\n"
            f"Если есть вопросы — обратитесь в поддержку.",
            parse_mode="HTML"
        )
        await call.answer("✅ Выполнено!", show_alert=True)
        return

    pos_item, pos_total = await get_queue_position(q["id"])
    text = (
        f"📋 <b>З@к@з #{order_num}</b> — {order['product_name']}\n\n"
        f"📊 <b>Ваша позиция в очереди:</b>\n"
        f"├ По сервису «{order['product_name']}»: <b>#{pos_item}</b>\n"
        f"└ 0бщ@я очередь: <b>#{pos_total}</b>\n\n"
        f"⏳ @дминистратор выполняет заказы в порядке очереди."
    )
    try:
        await call.message.edit_text(text, reply_markup=queue_refresh_kb(order_num), parse_mode="HTML")
    except:
        pass
    await call.answer("🔄 Обновлено")
