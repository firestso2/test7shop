from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import get_user, update_balance
from keyboards import cancel_kb, invoice_kb, profile_kb
from utils import create_invoice, check_invoice, log_event
from config import COMMISSION

router = Router()

class BalanceStates(StatesGroup):
    waiting_amount  = State()
    waiting_payment = State()

@router.callback_query(F.data == "balance:add")
async def ask_amount(call: CallbackQuery, state: FSMContext):
    await state.set_state(BalanceStates.waiting_amount)
    await call.message.edit_text(
        "💰 <b>П0п0лнение б@ланс@</b>\n\nВведите желаемую сумму в $ (например: <code>10</code>):\n\nℹ️ Мин. сумма: $1",
        reply_markup=cancel_kb("back:profile"), parse_mode="HTML"
    )
    await call.answer()

@router.message(BalanceStates.waiting_amount)
async def process_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", ".").strip())
        if amount < 1:
            await message.answer("❌ Минимальная сумма: $1", reply_markup=cancel_kb("back:profile"))
            return
    except ValueError:
        await message.answer("❌ Введите корректное число.", reply_markup=cancel_kb("back:profile"))
        return
    invoice_amount = round(amount / COMMISSION, 2)
    await message.answer("⏳ Создаём счёт...")
    invoice = await create_invoice(invoice_amount, f"Пополнение баланса на ${amount}")
    if not invoice:
        await message.answer("❌ Ошибка создания счёта.", reply_markup=cancel_kb("back:profile"))
        await state.clear()
        return
    await state.update_data(amount=amount, invoice_id=invoice["invoice_id"])
    await state.set_state(BalanceStates.waiting_payment)
    await message.answer(
        f"💳 <b>Счёт н@ 0плату</b>\n\nК з@числению: <b>${amount:.2f}</b>\nК 0плате (с к0миссией): <b>${invoice_amount:.2f}</b>\n\nНажмите «💳 0пл@тить» и вернитесь после оплаты.",
        reply_markup=invoice_kb(invoice["bot_invoice_url"]), parse_mode="HTML"
    )

@router.callback_query(F.data == "balance:check")
async def check_payment(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("invoice_id"):
        await call.answer("Сессия истекла. Начните заново.", show_alert=True)
        await state.clear()
        return
    await call.answer("⏳ Проверяем...")
    invoice = await check_invoice(data["invoice_id"])
    if not invoice:
        await call.answer("❌ Ошибка проверки.", show_alert=True)
        return
    if invoice.get("status") == "paid":
        amount = data["amount"]
        await update_balance(call.from_user.id, amount, f"CryptoPay invoice#{data['invoice_id']}")
        log_event("DEPOSIT", call.from_user.id, f"amount={amount}")
        await state.clear()
        user = await get_user(call.from_user.id)
        await call.message.edit_text(
            f"✅ <b>Б@ланс п0п0лнен!</b>\n\nЗачислено: <b>${amount:.2f}</b>\nТекущий б@ланс: <b>${user['balance']:.2f}</b>",
            reply_markup=profile_kb(), parse_mode="HTML"
        )
    elif invoice.get("status") == "expired":
        await state.clear()
        await call.message.edit_text("❌ Счёт истёк. Создайте новый.", reply_markup=profile_kb())
    else:
        await call.answer("⏳ Оплата ещё не поступила.", show_alert=True)
