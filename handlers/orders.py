from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import get_order_by_num
from keyboards import back_btn, cancel_kb
from utils import fmt_date

router = Router()

class OrderStates(StatesGroup):
    waiting_order_num = State()

@router.callback_query(F.data == "find_order")
async def find_order(call: CallbackQuery, state: FSMContext):
    await state.set_state(OrderStates.waiting_order_num)
    await call.message.edit_text("🔍 <b>П0иск з@к@з@</b>\n\nВведите н0мер заказа:", reply_markup=cancel_kb("back:profile"), parse_mode="HTML")
    await call.answer()

@router.message(OrderStates.waiting_order_num)
async def process_order_search(message: Message, state: FSMContext):
    await state.clear()
    try:
        order_num = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите корректный номер.", reply_markup=back_btn("back:profile"))
        return
    order = await get_order_by_num(order_num)
    if not order:
        await message.answer(f"❌ З@к@з <b>#{order_num}</b> не найден.", reply_markup=back_btn("back:profile"), parse_mode="HTML")
        return
    if order["user_id"] != message.from_user.id:
        await message.answer("❌ Это не ваш заказ.", reply_markup=back_btn("back:profile"))
        return
    await message.answer(
        f"📦 <b>З@к@з #{order['order_num']}</b>\n\n🏷 Тов@р: <b>{order['product_name']}</b>\n💲 Цен@: ${order['price']:.2f}\n📅 Д@т@: {fmt_date(order['created_at'])}\n\n📋 <b>Д@нные т0в@р@:</b>\n<code>{order['product_data']}</code>",
        reply_markup=back_btn("back:profile"), parse_mode="HTML"
    )
