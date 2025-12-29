from fastmcp import FastMCP
from typing import Optional, List
import aiosqlite
import sqlite3
import os
import tempfile
import json

# --- Setup ---
DB_PATH = os.path.join(tempfile.gettempdir(), "expenses.db")

mcp = FastMCP("ExpenseTracker")


# --- DB Init (sync, once) ---
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT,
                note TEXT
            )
        """)
        conn.commit()

init_db()


# --- Tools ---

@mcp.tool()
async def add_expense(
    date: str,
    amount: float,
    category: str,
    subcategory: Optional[str] = None,
    note: Optional[str] = None
) -> dict:
    """Add a new expense"""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO expenses(date, amount, category, subcategory, note) VALUES (?, ?, ?, ?, ?)",
            (date, amount, category, subcategory, note)
        )
        await db.commit()

    return {"status": "success", "id": cur.lastrowid}


@mcp.tool()
async def list_expenses(
    start_date: str,
    end_date: str
) -> List[dict]:
    """List expenses in a date range"""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            SELECT id, date, amount, category, subcategory, note
            FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY date DESC
            """,
            (start_date, end_date)
        )
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in await cur.fetchall()]


@mcp.tool()
async def summarize(
    start_date: str,
    end_date: str,
    category: Optional[str] = None
) -> List[dict]:
    """Summarize expenses by category"""
    query = """
        SELECT category, SUM(amount) AS total_amount, COUNT(*) AS count
        FROM expenses
        WHERE date BETWEEN ? AND ?
    """
    params = [start_date, end_date]

    if category:
        query += " AND category = ?"
        params.append(category)

    query += " GROUP BY category ORDER BY total_amount DESC"

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(query, params)
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in await cur.fetchall()]


# --- Resource ---

@mcp.resource("expense:///categories", mime_type="application/json")
def categories():
    return json.dumps({
        "categories": [
            "Food",
            "Travel",
            "Transport",
            "Shopping",
            "Bills",
            "Healthcare",
            "Education",
            "Business",
            "Other"
        ]
    }, indent=2)


# --- Run ---
if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
