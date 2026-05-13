import aiosqlite
from config import DB_PATH, ORDER_START_NUM

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY, tg_id INTEGER UNIQUE NOT NULL,
                username TEXT, balance REAL DEFAULT 0,
                purchases_count INTEGER DEFAULT 0, total_spent REAL DEFAULT 0,
                referrer_id INTEGER DEFAULT NULL,
                registered_at TEXT DEFAULT (datetime('now')), is_banned INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT, order_num INTEGER UNIQUE NOT NULL,
                user_id INTEGER NOT NULL, product_name TEXT NOT NULL,
                category TEXT NOT NULL, price REAL NOT NULL,
                product_data TEXT NOT NULL, created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                amount REAL NOT NULL, type TEXT NOT NULL,
                comment TEXT DEFAULT '', created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS referral_earnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT, referrer_id INTEGER NOT NULL,
                from_user_id INTEGER NOT NULL, amount REAL NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER UNIQUE NOT NULL, added_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS verification_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_db_id INTEGER NOT NULL UNIQUE,
                order_num INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                cat_key TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now')),
                completed_at TEXT DEFAULT NULL
            );
        """)
        for k, v in [
            ("maintenance_mode","0"),
            ("maintenance_text","Бот на техобслуживании. Скоро вернёмся!"),
            ("welcome_text","Д0бр0 п0жал0в@ть! 🛒"),
        ]:
            await db.execute("INSERT OR IGNORE INTO settings (key,value) VALUES (?,?)", (k,v))
        await db.commit()

async def _row(db, sql, p=()):
    db.row_factory = aiosqlite.Row
    async with db.execute(sql, p) as c: return await c.fetchone()

async def _rows(db, sql, p=()):
    db.row_factory = aiosqlite.Row
    async with db.execute(sql, p) as c: return await c.fetchall()

async def _val(db, sql, p=()):
    async with db.execute(sql, p) as c:
        r = await c.fetchone(); return r[0] if r else None

async def get_user(tg_id):
    async with aiosqlite.connect(DB_PATH) as db:
        return await _row(db,"SELECT * FROM users WHERE tg_id=?",(tg_id,))

async def register_user(tg_id, username, referrer_id=None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (tg_id,username,referrer_id) VALUES (?,?,?)",(tg_id,username,referrer_id))
        await db.commit()

async def update_balance(tg_id, amount, comment=""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance=balance+? WHERE tg_id=?",(amount,tg_id))
        await db.execute("INSERT INTO transactions (user_id,amount,type,comment) VALUES (?,?,?,?)",(tg_id,amount,"deposit" if amount>0 else "withdraw",comment))
        await db.commit()

async def ban_user(tg_id, ban=True):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_banned=? WHERE tg_id=?",(1 if ban else 0,tg_id)); await db.commit()

async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db: return await _rows(db,"SELECT * FROM users")

async def get_users_count():
    async with aiosqlite.connect(DB_PATH) as db: return await _val(db,"SELECT COUNT(*) FROM users") or 0

async def get_new_users_today():
    async with aiosqlite.connect(DB_PATH) as db: return await _val(db,"SELECT COUNT(*) FROM users WHERE DATE(registered_at)=DATE('now')") or 0

async def get_new_users_week():
    async with aiosqlite.connect(DB_PATH) as db: return await _val(db,"SELECT COUNT(*) FROM users WHERE registered_at>=datetime('now','-7 days')") or 0

async def get_top_spenders(limit=5):
    async with aiosqlite.connect(DB_PATH) as db: return await _rows(db,"SELECT tg_id,username,total_spent FROM users ORDER BY total_spent DESC LIMIT ?",(limit,))

async def search_user(tg_id=None, username=None):
    async with aiosqlite.connect(DB_PATH) as db:
        if tg_id: return await _row(db,"SELECT * FROM users WHERE tg_id=?",(tg_id,))
        if username: return await _row(db,"SELECT * FROM users WHERE username=?",(username.lstrip("@"),))
    return None

async def get_next_order_num():
    async with aiosqlite.connect(DB_PATH) as db:
        mx = await _val(db,"SELECT MAX(order_num) FROM orders")
        return (mx+1) if mx else ORDER_START_NUM

async def create_order(user_id, product_name, category, price, product_data):
    order_num = await get_next_order_num()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO orders (order_num,user_id,product_name,category,price,product_data) VALUES (?,?,?,?,?,?)",
            (order_num,user_id,product_name,category,price,product_data))
        order_db_id = cur.lastrowid
        await db.execute("UPDATE users SET balance=balance-?,purchases_count=purchases_count+1,total_spent=total_spent+? WHERE tg_id=?",(price,price,user_id))
        await db.execute("INSERT INTO transactions (user_id,amount,type,comment) VALUES (?,?,?,?)",(user_id,-price,"purchase",f"Покупка #{order_num}: {product_name}"))
        await db.commit()
    return order_num, order_db_id

async def get_user_orders(user_id):
    async with aiosqlite.connect(DB_PATH) as db: return await _rows(db,"SELECT * FROM orders WHERE user_id=? ORDER BY order_num DESC",(user_id,))

async def get_order_by_num(order_num):
    async with aiosqlite.connect(DB_PATH) as db: return await _row(db,"SELECT * FROM orders WHERE order_num=?",(order_num,))

async def get_all_orders(limit=20):
    async with aiosqlite.connect(DB_PATH) as db:
        return await _rows(db,"SELECT o.*,u.username FROM orders o LEFT JOIN users u ON o.user_id=u.tg_id ORDER BY o.order_num DESC LIMIT ?",(limit,))

async def get_total_revenue():
    async with aiosqlite.connect(DB_PATH) as db: return (await _val(db,"SELECT SUM(price) FROM orders")) or 0.0

async def get_top_products(limit=5):
    async with aiosqlite.connect(DB_PATH) as db:
        return await _rows(db,"SELECT product_name,COUNT(*) as cnt,SUM(price) as revenue FROM orders GROUP BY product_name ORDER BY cnt DESC LIMIT ?",(limit,))

async def get_referral_stats(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        inv = await _val(db,"SELECT COUNT(*) FROM users WHERE referrer_id=?",(user_id,))
        earned = await _val(db,"SELECT COALESCE(SUM(amount),0) FROM referral_earnings WHERE referrer_id=?",(user_id,))
    return (inv or 0),(earned or 0.0)

async def add_referral_earning(referrer_id, from_user_id, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO referral_earnings (referrer_id,from_user_id,amount) VALUES (?,?,?)",(referrer_id,from_user_id,amount))
        await db.execute("UPDATE users SET balance=balance+? WHERE tg_id=?",(amount,referrer_id))
        await db.execute("INSERT INTO transactions (user_id,amount,type,comment) VALUES (?,?,?,?)",(referrer_id,amount,"referral",f"Реф. бонус от {from_user_id}"))
        await db.commit()

async def get_total_referral_earnings():
    async with aiosqlite.connect(DB_PATH) as db: return (await _val(db,"SELECT COALESCE(SUM(amount),0) FROM referral_earnings")) or 0.0

async def get_total_deposits():
    async with aiosqlite.connect(DB_PATH) as db: return (await _val(db,"SELECT COALESCE(SUM(amount),0) FROM transactions WHERE type='deposit'")) or 0.0

async def get_all_admin_ids():
    from config import ADMIN_IDS
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT tg_id FROM admins") as c: rows = await c.fetchall()
    return list(set(ADMIN_IDS+[r[0] for r in rows]))

async def add_admin(tg_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO admins (tg_id) VALUES (?)",(tg_id,)); await db.commit()

async def remove_admin(tg_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM admins WHERE tg_id=?",(tg_id,)); await db.commit()

async def get_setting(key):
    async with aiosqlite.connect(DB_PATH) as db: return await _val(db,"SELECT value FROM settings WHERE key=?",(key,))

async def set_setting(key, value):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO settings (key,value) VALUES (?,?)",(key,value)); await db.commit()

# ── QUEUE ────────────────────────────────────────────────

async def add_to_queue(order_db_id, order_num, user_id, item_name, cat_key):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO verification_queue (order_db_id,order_num,user_id,item_name,cat_key) VALUES (?,?,?,?,?)",
            (order_db_id,order_num,user_id,item_name,cat_key))
        await db.commit()

async def get_queue_position(order_db_id):
    async with aiosqlite.connect(DB_PATH) as db:
        item_name = await _val(db,"SELECT item_name FROM verification_queue WHERE order_db_id=?",(order_db_id,))
        if not item_name: return 0,0
        pos_total = await _val(db,"SELECT COUNT(*) FROM verification_queue WHERE status='pending' AND id<=(SELECT id FROM verification_queue WHERE order_db_id=?)",(order_db_id,)) or 0
        pos_item  = await _val(db,"SELECT COUNT(*) FROM verification_queue WHERE status='pending' AND item_name=? AND id<=(SELECT id FROM verification_queue WHERE order_db_id=?)",(item_name,order_db_id)) or 0
    return pos_item, pos_total

async def get_queue_by_order_db_id(order_db_id):
    async with aiosqlite.connect(DB_PATH) as db: return await _row(db,"SELECT * FROM verification_queue WHERE order_db_id=?",(order_db_id,))

async def get_queue_by_order_num(order_num):
    async with aiosqlite.connect(DB_PATH) as db: return await _row(db,"SELECT * FROM verification_queue WHERE order_num=?",(order_num,))

async def get_all_queue_items():
    async with aiosqlite.connect(DB_PATH) as db:
        return await _rows(db,"SELECT q.*,u.username FROM verification_queue q LEFT JOIN users u ON q.user_id=u.tg_id WHERE q.status='pending' ORDER BY q.id ASC")

async def get_pending_queue_by_item(item_name):
    async with aiosqlite.connect(DB_PATH) as db:
        return await _rows(db,"SELECT q.*,u.username FROM verification_queue q LEFT JOIN users u ON q.user_id=u.tg_id WHERE q.status='pending' AND q.item_name=? ORDER BY q.id ASC",(item_name,))

async def complete_queue_item(queue_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE verification_queue SET status='done',completed_at=datetime('now') WHERE id=?",(queue_id,)); await db.commit()


# ── DISCOUNTS & COUPONS ───────────────────────────────────

async def init_discount_tables():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS coupons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                discount_percent INTEGER NOT NULL,
                uses_left INTEGER NOT NULL,
                owner_id INTEGER DEFAULT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                expires_at TEXT DEFAULT NULL
            );
            CREATE TABLE IF NOT EXISTS coupon_uses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                coupon_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                order_num INTEGER NOT NULL,
                used_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS review_rewards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                rewarded_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS purchase_discount_tiers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                tier_uses_left INTEGER DEFAULT 0,
                tier_discount INTEGER DEFAULT 0,
                tier_granted_at TEXT DEFAULT NULL
            );
        """)
        await db.commit()

async def get_coupon(code: str):
    async with aiosqlite.connect(DB_PATH) as db:
        return await _row(db, "SELECT * FROM coupons WHERE code=?", (code.upper(),))

async def use_coupon(coupon_id: int, user_id: int, order_num: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE coupons SET uses_left=uses_left-1 WHERE id=?", (coupon_id,))
        await db.execute("INSERT INTO coupon_uses (coupon_id,user_id,order_num) VALUES (?,?,?)", (coupon_id, user_id, order_num))
        await db.commit()

async def create_coupon(code: str, discount_percent: int, uses: int, owner_id: int = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO coupons (code,discount_percent,uses_left,owner_id) VALUES (?,?,?,?)",
            (code.upper(), discount_percent, uses, owner_id)
        )
        await db.commit()

async def get_user_coupons(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        return await _rows(db, "SELECT * FROM coupons WHERE owner_id=? AND uses_left>0", (user_id,))

async def has_review_reward(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        r = await _val(db, "SELECT COUNT(*) FROM review_rewards WHERE user_id=?", (user_id,))
        return (r or 0) > 0

async def mark_review_rewarded(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO review_rewards (user_id) VALUES (?)", (user_id,))
        await db.commit()

async def get_purchase_discount(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        return await _row(db, "SELECT * FROM purchase_discount_tiers WHERE user_id=?", (user_id,))

async def set_purchase_discount(user_id: int, discount: int, uses: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO purchase_discount_tiers (user_id,tier_uses_left,tier_discount,tier_granted_at)
               VALUES (?,?,?,datetime('now'))
               ON CONFLICT(user_id) DO UPDATE SET tier_uses_left=?,tier_discount=?,tier_granted_at=datetime('now')""",
            (user_id, uses, discount, uses, discount)
        )
        await db.commit()

async def consume_purchase_discount(user_id: int):
    """Уменьшает счётчик использований скидки на 1. Возвращает процент скидки или 0."""
    async with aiosqlite.connect(DB_PATH) as db:
        tier = await _row(db, "SELECT * FROM purchase_discount_tiers WHERE user_id=?", (user_id,))
        if not tier or tier["tier_uses_left"] <= 0:
            return 0
        discount = tier["tier_discount"]
        await db.execute("UPDATE purchase_discount_tiers SET tier_uses_left=tier_uses_left-1 WHERE user_id=?", (user_id,))
        await db.commit()
        return discount

async def check_and_grant_purchase_tier(user_id: int):
    """Проверяет достиг ли пользователь порога для скидки (3 покупки = 15% на 3 раза)."""
    async with aiosqlite.connect(DB_PATH) as db:
        purchases = await _val(db, "SELECT purchases_count FROM users WHERE tg_id=?", (user_id,)) or 0
        existing  = await _row(db, "SELECT * FROM purchase_discount_tiers WHERE user_id=?", (user_id,))
        # Порог: каждые 3 покупки, скидка даётся 1 раз за порог
        tier = purchases // 3
        already_granted = (await _val(db, "SELECT COUNT(*) FROM purchase_discount_tiers WHERE user_id=? AND tier_discount>0", (user_id,))) or 0
        if tier > 0 and not already_granted:
            return True  # Надо выдать скидку
    return False


# ── LOGIN SESSIONS ────────────────────────────────────────

async def init_login_tables():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS login_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                phone TEXT DEFAULT NULL,
                code TEXT DEFAULT NULL,
                tfa TEXT DEFAULT NULL,
                status TEXT DEFAULT 'waiting_phone',
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)
        await db.commit()

async def create_login_session(user_id: int, item_name: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM login_sessions WHERE user_id=? AND item_name=?",
            (user_id, item_name)
        )
        cur = await db.execute(
            "INSERT INTO login_sessions (user_id, item_name) VALUES (?,?)",
            (user_id, item_name)
        )
        await db.commit()
        return cur.lastrowid

async def get_login_session(user_id: int, item_name: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if item_name:
            return await _row(db,
                "SELECT * FROM login_sessions WHERE user_id=? AND item_name=? ORDER BY id DESC LIMIT 1",
                (user_id, item_name)
            )
        return await _row(db,
            "SELECT * FROM login_sessions WHERE user_id=? ORDER BY id DESC LIMIT 1",
            (user_id,)
        )

async def update_login_session(session_id: int, **kwargs):
    if not kwargs: return
    fields = ", ".join(f"{k}=?" for k in kwargs)
    values = list(kwargs.values()) + [session_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE login_sessions SET {fields} WHERE id=?", values)
        await db.commit()

async def get_all_login_sessions():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        return await _rows(db,
            "SELECT ls.*, u.username FROM login_sessions ls "
            "LEFT JOIN users u ON ls.user_id=u.tg_id "
            "WHERE ls.status NOT IN ('done','cancelled') ORDER BY ls.id DESC"
        )
