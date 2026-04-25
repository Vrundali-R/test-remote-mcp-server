from fastmcp import FastMCP
import os
import aiosqlite
import tempfile
import json
import asyncio

# -------------------- PATHS --------------------
DB_PATH = os.path.join(tempfile.gettempdir(), "expenses.db")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

print(f"Database path: {DB_PATH}")

mcp = FastMCP("ExpenseTracker")

# -------------------- INIT DB --------------------
async def init_db():
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("PRAGMA journal_mode=WAL")

            await db.execute("""
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    subcategory TEXT DEFAULT '',
                    note TEXT DEFAULT ''
                )
            """)

            # test write
            await db.execute("""
                INSERT OR IGNORE INTO expenses (date, amount, category)
                VALUES ('2000-01-01', 0, 'test')
            """)

            await db.execute("DELETE FROM expenses WHERE category = 'test'")
            await db.commit()

        print("Database initialized successfully")

    except Exception as e:
        print(f"Database init error: {e}")
        raise


# ✅ FIX: Proper startup hook (NO asyncio.run)
@mcp.on_event("startup")
async def startup():
    await init_db()


# -------------------- ADD EXPENSE --------------------
@mcp.tool()
async def add_expense(date, amount, category, subcategory="", note=""):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                """
                INSERT INTO expenses (date, amount, category, subcategory, note)
                VALUES (?, ?, ?, ?, ?)
                """,
                (date, amount, category, subcategory, note)
            )
            await db.commit()
            return {"status": "success", "id": cur.lastrowid}

    except aiosqlite.OperationalError as e:
        if "readonly" in str(e).lower():
            return {"status": "error", "message": "Database is read-only"}
        return {"status": "error", "message": str(e)}

    except Exception as e:
        return {"status": "error", "message": str(e)}


# -------------------- LIST EXPENSES --------------------
@mcp.tool()
async def list_expenses(start_date, end_date):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                """
                SELECT id, date, amount, category, subcategory, note
                FROM expenses
                WHERE date BETWEEN ? AND ?
                ORDER BY date DESC, id DESC
                """,
                (start_date, end_date)
            )

            rows = await cur.fetchall()
            cols = [d[0] for d in cur.description]

            return [dict(zip(cols, r)) for r in rows]

    except Exception as e:
        return {"status": "error", "message": str(e)}


# -------------------- SUMMARIZE --------------------
@mcp.tool()
async def summarize(start_date, end_date, category=None):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            query = """
                SELECT category, SUM(amount) AS total_amount, COUNT(*) as count
                FROM expenses
                WHERE date BETWEEN ? AND ?
            """
            params = [start_date, end_date]

            if category:
                query += " AND category = ?"
                params.append(category)

            query += " GROUP BY category ORDER BY total_amount DESC"

            cur = await db.execute(query, params)
            rows = await cur.fetchall()
            cols = [d[0] for d in cur.description]

            return [dict(zip(cols, r)) for r in rows]

    except Exception as e:
        return {"status": "error", "message": str(e)}


# -------------------- CATEGORIES --------------------
@mcp.resource("expense://categories", mime_type="application/json")
async def categories():
    try:
        if os.path.exists(CATEGORIES_PATH):
            return await asyncio.to_thread(
                lambda: open(CATEGORIES_PATH, "r", encoding="utf-8").read()
            )
        else:
            default = {
                "categories": [
                    "Food & Dining",
                    "Transportation",
                    "Shopping",
                    "Entertainment",
                    "Bills & Utilities",
                    "Healthcare",
                    "Travel",
                    "Education",
                    "Business",
                    "Other"
                ]
            }
            return json.dumps(default)

    except Exception as e:
        return json.dumps({"error": str(e)})


# -------------------- RUN SERVER --------------------
if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8000)