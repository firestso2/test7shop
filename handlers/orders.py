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
    await call.message.edit_text(
        "🔍 <b>Поиск заказа</b>\n\nВведите номер заказа:",
        reply_markup=cancel_kb("back:profile"),
        parse_mode="HTML"
    )
    await call.answer()


@router.message(OrderStates.waiting_order_num)
async def process_order_search(message: Message, state: FSMContext):
    await state.clear()
    try:
        order_num = int(message.text.strip())
    except ValueError:
        await message.answer(
            "❌ Введите корректный номер.",
            reply_markup=back_btn("back:profile")
        )
        return

    order = await get_order_by_num(order_num)
    if not order:
        await message.answer(
            f"❌ Заказ <b>#{order_num}</b> не найден.",
            reply_markup=back_btn("back:profile"),
            parse_mode="HTML"
        )
        return

    if order["user_id"] != message.from_user.id:
        await message.answer(
            "❌ Это не ваш заказ.",
            reply_markup=back_btn("back:profile")
        )
        return

    # Не показываем данные для верификационных заказов
    product_data = order["product_data"]
    if product_data.startswith("verification:"):
        data_text = "<i>Верификационный заказ — данные передаются через бота</i>"
    else:
        data_text = f"<code>{product_data}</code>"

    await message.answer(
        f"📦 <b>Заказ #{order['order_num']}</b>\n\n"
        f"🏷 Товар: <b>{order['product_name']}</b>\n"
        f"💲 Цена: ${order['price']:.2f}\n"
        f"📅 Дата: {fmt_date(order['created_at'])}\n\n"
        f"📋 <b>Данные товара:</b>\n{data_text}",
        reply_markup=back_btn("back:profile"),
        parse_mode="HTML"
    )
