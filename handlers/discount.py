from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import get_user_coupons, get_purchase_discount, get_coupon
from keyboards import back_btn, cancel_kb

router = Router()

class CouponStates(StatesGroup):
    waiting_code = State()

@router.callback_query(F.data == "my_discounts")
async def my_discounts(call: CallbackQuery):
    user_id = call.from_user.id
    coupons = await get_user_coupons(user_id)
    tier    = await get_purchase_discount(user_id)

    lines = ["🎫 <b>М0и скидки</b>\n"]

    # Скидка за покупки
    if tier and tier["tier_discount"] > 0 and tier["tier_uses_left"] > 0:
        lines.append(f"🏅 <b>Скидка за активность:</b> {tier['tier_discount']}% × {tier['tier_uses_left']} покупки")
        lines.append("  Применяется автоматически при следующей покупке\n")
    else:
        lines.append("🏅 <b>Скидка за активность:</b> нет активных")
        lines.append("  ℹ️ Каждые 3 покупки — скидка 15% на 3 следующих\n")

    # Купоны
    if coupons:
        lines.append("🎟 <b>Ваши купоны:</b>")
        for c in coupons:
            lines.append(f"  <code>{c['code']}</code> — {c['discount_percent']}% × {c['uses_left']} раз")
    else:
        lines.append("🎟 <b>Купонов нет</b>")

    lines.append("\nℹ️ Купон вводится при оформлении покупки.")

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎟 Ввести купон", callback_data="coupon:enter")],
        [InlineKeyboardButton(text="🔴 Н@з@д", callback_data="back:profile")]
    ])
    try:
        await call.message.edit_text("\n".join(lines), reply_markup=kb, parse_mode="HTML")
    except:
        await call.message.answer("\n".join(lines), reply_markup=kb, parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data == "coupon:enter")
async def enter_coupon(call: CallbackQuery, state: FSMContext):
    await state.set_state(CouponStates.waiting_code)
    await call.message.edit_text(
        "🎟 Введите к0д купона:",
        reply_markup=cancel_kb("my_discounts")
    )
    await call.answer()

@router.message(CouponStates.waiting_code)
async def check_coupon_code(message: Message, state: FSMContext):
    await state.clear()
    code = message.text.strip().upper()
    coupon = await get_coupon(code)
    if not coupon or coupon["uses_left"] <= 0:
        await message.answer("❌ Купон не найден или уже использован.", reply_markup=back_btn("my_discounts"))
        return
    # Сохраняем в state для применения при покупке
    await state.update_data(pending_coupon=code)
    await message.answer(
        f"✅ Купон <code>{code}</code> — {coupon['discount_percent']}% скидки\n"
        f"Осталось использований: {coupon['uses_left']}\n\n"
        f"Купон будет применён к вашей следующей покупке.",
        reply_markup=back_btn("back:catalog"),
        parse_mode="HTML"
    )
