# V0r@che's St0re — Telegram Bot

## Быстрый старт

```bash
pip install -r requirements.txt
python bot.py
```

## Настройка config.py

| Параметр | Описание |
|---|---|
| `BOT_TOKEN` | Токен от @BotFather |
| `CRYPTO_PAY_TOKEN` | Токен от @CryptoBot → My Apps |
| `ADMIN_IDS` | Список Telegram ID администраторов |
| `REVIEWS_CHAT_ID` | Числовой ID чата @chat_vorache777 |
| `MANUAL_LINK` | Ссылка на общий мануал |

## Как получить REVIEWS_CHAT_ID
Добавь @userinfobot в чат, он покажет числовой ID (отрицательное число).

## Структура файлов
```
vorache_bot/
├── bot.py
├── config.py
├── database.py
├── products.py
├── keyboards.py
├── utils.py
├── requirements.txt
├── products.json        # создаётся автоматически
├── vorache.db           # создаётся автоматически
├── logs.txt             # создаётся автоматически
├── handlers/
│   ├── start.py
│   ├── catalog.py
│   ├── profile.py
│   ├── support.py
│   ├── balance.py
│   ├── purchases.py
│   ├── referral.py
│   ├── orders.py
│   ├── queue.py
│   ├── discount.py
│   ├── reviews.py
│   ├── admin.py
│   └── admin_queue.py
└── middlewares/
    └── maintenance.py
```

## Команды
- `/start` — запуск бота
- `/admin` — панель администратора

## Система скидок
- **За активность**: каждые 3 покупки → скидка 15% на следующие 3 покупки (автоматически)
- **За отзыв**: купон REV-XXXXXXX → 10% на 3 покупки (выдаётся боту после отзыва в чате)
- **Купоны**: вводятся в разделе «Профиль» → «Мои скидки»

## Формат отзыва
Покупатель пишет в @rewiews_vorache777 (под вторым закреплённым постом):
```
+реп @vorache777, верифнул [сервис]... [любой текст]
```
+ прикрепляет скриншот. Бот автоматически выдаёт купон.

## Очередь верификации
Работает для категорий crypto и bookmakers.
Покупатель видит своё место в очереди и кнопку «Обновить».
Админ выполняет заказы через /admin → «Очередь верификации».

## Добавление товаров
Через /admin → «Управление товарами» → «Пополнить товар»:
```
1. данные первой единицы
2. данные второй единицы
3. и т.д.
```
