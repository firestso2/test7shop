from aiogram import Router, F
from aiogram.types import CallbackQuery
from database import get_user_orders
from keyboards import back_btn
from utils import fmt_date

router = Router()


@router.callback_query(F.data == "my_purchases")
async def my_purchases(call: CallbackQuery):
    orders = await get_user_orders(call.from_user.id)
    if not orders:
        await call.message.edit_text(
            "📦 <b>Мои покупки</b>\n\nПокупок пока нет.",
            reply_markup=back_btn("back:profile"),
            parse_mode="HTML"
        )
        await call.answer()
        return

    lines = ["📦 <b>Мои покупки:</b>\n"]
    for o in orders:
        lines.append(
            f"<b>#{o['order_num']}</b> • {o['product_name']} • "
            f"${o['price']:.2f} • {fmt_date(o['created_at'])}"
        )

    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:3900] + "\n\n..."

    await call.message.edit_text(
        text,
        reply_markup=back_btn("back:profile"),
        parse_mode="HTML"
    )
    await call.answer()
