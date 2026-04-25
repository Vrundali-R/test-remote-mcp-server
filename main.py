from fastmcp import FastMCP
import sqlite3
import os

# Create MCP server
mcp = FastMCP("ExpenseTracker")

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), "expenses.db")


# Initialize DB (NO on_event here)
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                category TEXT,
                amount REAL,
                description TEXT
            )
        """)
        # One-time migration: add description column if it doesn't exist
        try:
            conn.execute("ALTER TABLE expenses ADD COLUMN description TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists, ignore

# Call init manually (important)
init_db()


# TOOL 1: Add expense
@mcp.tool()
def add_expense(date: str, category: str, amount: float, description: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO expenses (date, category, amount, description) VALUES (?, ?, ?, ?)",
            (date, category, amount, description),
        )
    return "Expense added successfully"


# TOOL 2: Get all expenses
@mcp.tool()
def get_expenses():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("SELECT * FROM expenses")
        rows = cursor.fetchall()
    return rows


# TOOL 3: Delete expense
@mcp.tool()
def delete_expense(expense_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    return f"Deleted expense {expense_id}"


# Run server
if __name__ == "__main__":
    mcp.run()