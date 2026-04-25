from fastmcp import FastMCP
import os
import sqlite3
import tempfile
import json

# ✅ Always writable location
DB_PATH = os.path.join(tempfile.gettempdir(), "expenses.db")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

print(f"Database path: {DB_PATH}")

mcp = FastMCP("ExpenseTracker")


# -------------------- INIT DB --------------------
def init_db():
    try:
        with sqlite3.connect(DB_PATH) as c:
            c.execute("PRAGMA journal_mode=WAL")

            c.execute("""
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    subcategory TEXT DEFAULT '',
                    note TEXT DEFAULT ''
                )
            """)

            # test write access
            c.execute("""
                INSERT OR IGNORE INTO expenses (date, amount, category)
                VALUES ('2000-01-01', 0, 'test')
            """)
            c.execute("DELETE FROM expenses WHERE category = 'test'")

        print("Database initialized successfully")

    except Exception as e:
        print(f"Database init error: {e}")
        raise


init_db()


# -------------------- ADD EXPENSE --------------------
@mcp.tool()
def add_expense(date, amount, category, subcategory="", note=""):
    try:
        with sqlite3.connect(DB_PATH) as c:
            cur = c.execute(
                """
                INSERT INTO expenses (date, amount, category, subcategory, note)
                VALUES (?, ?, ?, ?, ?)
                """,
                (date, amount, category, subcategory, note)
            )
            return {"status": "success", "id": cur.lastrowid}

    except sqlite3.OperationalError as e:
        if "readonly" in str(e).lower():
            return {"status": "error", "message": "Database is read-only"}
        return {"status": "error", "message": str(e)}

    except Exception as e:
        return {"status": "error", "message": str(e)}


# -------------------- LIST EXPENSES --------------------
@mcp.tool()
def list_expenses(start_date, end_date):
    try:
        with sqlite3.connect(DB_PATH) as c:
            cur = c.execute(
                """
                SELECT id, date, amount, category, subcategory, note
                FROM expenses
                WHERE date BETWEEN ? AND ?
                ORDER BY date DESC, id DESC
                """,
                (start_date, end_date)
            )

            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]

    except Exception as e:
        return {"status": "error", "message": str(e)}


# -------------------- SUMMARIZE --------------------
@mcp.tool()
def summarize(start_date, end_date, category=None):
    try:
        with sqlite3.connect(DB_PATH) as c:
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

            cur = c.execute(query, params)
            cols = [d[0] for d in cur.description]

            return [dict(zip(cols, r)) for r in cur.fetchall()]

    except Exception as e:
        return {"status": "error", "message": str(e)}


# -------------------- CATEGORIES --------------------
@mcp.resource("expense://categories", mime_type="application/json")
def categories():
    try:
        if os.path.exists(CATEGORIES_PATH):
            with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
                return f.read()
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