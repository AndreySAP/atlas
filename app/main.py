from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path
from typing import List

from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
import uvicorn

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "data" / "atlas.db"
TARGET_EMERGENCY = 20000.0
MIN_INVESTMENT_RATE = 0.12

app = FastAPI(title="Atlas v0.4")
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))

VAULTS = [
    ("EMERGENCY", "Emergency Fund"),
    ("INVESTMENT", "Investment"),
    ("PLANNED", "Planned Expenses"),
    ("OPERATING", "Operating Cash"),
]

def conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def init_db() -> None:
    DB_PATH.parent.mkdir(exist_ok=True)
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS vaults (
            code TEXT PRIMARY KEY,
            name TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS ledger_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_date TEXT NOT NULL,
            vault_code TEXT NOT NULL,
            amount REAL NOT NULL,
            memo TEXT NOT NULL DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(vault_code) REFERENCES vaults(code)
        );
        """)
        c.executemany("INSERT OR IGNORE INTO vaults(code, name) VALUES (?, ?)", VAULTS)
        c.commit()

def balances() -> dict[str, float]:
    with conn() as c:
        rows = c.execute("""
            SELECT v.code, COALESCE(SUM(l.amount), 0) AS balance
            FROM vaults v
            LEFT JOIN ledger_entries l ON l.vault_code = v.code
            GROUP BY v.code
            ORDER BY v.code
        """).fetchall()
        return {r["code"]: round(float(r["balance"]), 2) for r in rows}

def ledger(limit: int = 50):
    with conn() as c:
        return c.execute("""
            SELECT id, entry_date, vault_code, amount, memo, created_at
            FROM ledger_entries
            ORDER BY id DESC
            LIMIT ?
        """, (limit,)).fetchall()

def post_entry(vault: str, amount: float, memo: str) -> None:
    with conn() as c:
        c.execute(
            "INSERT INTO ledger_entries(entry_date, vault_code, amount, memo) VALUES (?, ?, ?, ?)",
            (str(date.today()), vault, amount, memo),
        )
        c.commit()

def emergency_rate(current: float) -> float:
    if current >= TARGET_EMERGENCY:
        return 0.0
    progress = current / TARGET_EMERGENCY
    if progress < 0.50:
        return 0.35
    if progress < 0.80:
        return 0.25
    return 0.15

def generate_lines(income: float, emergency: float, planned_now: float) -> list[dict]:
    reserved = min(planned_now, income * 0.45)
    available = income - reserved
    gap = max(0.0, TARGET_EMERGENCY - emergency)
    to_emergency = min(gap, available * emergency_rate(emergency))
    to_investment = available * (0.35 if gap == 0 else MIN_INVESTMENT_RATE)
    to_operating = available - to_emergency - to_investment
    lines = []
    if reserved > 0:
        lines.append({"vault": "PLANNED", "amount": round(reserved, 2), "reason": "Reserve planned expenses first"})
    if to_emergency > 0:
        lines.append({"vault": "EMERGENCY", "amount": round(to_emergency, 2), "reason": "Emergency below EUR 20k target"})
    if to_investment > 0:
        lines.append({"vault": "INVESTMENT", "amount": round(to_investment, 2), "reason": "Maintain investment habit"})
    if to_operating > 0:
        lines.append({"vault": "OPERATING", "amount": round(to_operating, 2), "reason": "Remaining operating cash"})
    return lines

@app.on_event("startup")
def startup() -> None:
    init_db()

@app.get("/")
def index(request: Request):
    b = balances()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "balances": b,
        "ledger": ledger(),
        "target": TARGET_EMERGENCY,
        "progress": round((b.get("EMERGENCY", 0) / TARGET_EMERGENCY) * 100),
        "proposal": None,
        "income": 6000,
        "planned_now": 500,
        "error": None,
    })

@app.post("/seed")
def seed():
    b = balances()
    if b.get("EMERGENCY", 0) == 0:
        post_entry("EMERGENCY", 7000, "Initial Emergency balance")
    if b.get("OPERATING", 0) == 0:
        post_entry("OPERATING", 3000, "Initial Operating balance")
    return RedirectResponse("/", status_code=303)

@app.post("/generate")
def generate(request: Request, income: float = Form(...), planned_now: float = Form(0)):
    b = balances()
    error = None
    proposal = None
    if income <= 0:
        error = "Income must be positive."
    else:
        proposal = {"income": income, "lines": generate_lines(income, b.get("EMERGENCY", 0), planned_now)}
    return templates.TemplateResponse("index.html", {
        "request": request,
        "balances": b,
        "ledger": ledger(),
        "target": TARGET_EMERGENCY,
        "progress": round((b.get("EMERGENCY", 0) / TARGET_EMERGENCY) * 100),
        "proposal": proposal,
        "income": income,
        "planned_now": planned_now,
        "error": error,
    })

@app.post("/post")
async def post(request: Request):
    form = await request.form()
    income = float(form.get("income", 0))
    vaults: List[str] = form.getlist("vault")
    amounts: List[str] = form.getlist("amount")
    reasons: List[str] = form.getlist("reason")
    total = sum(float(a or 0) for a in amounts)
    if abs(total - income) > 0.01:
        b = balances()
        proposal = {"income": income, "lines": [{"vault": v, "amount": float(a or 0), "reason": r} for v, a, r in zip(vaults, amounts, reasons)]}
        return templates.TemplateResponse("index.html", {
            "request": request,
            "balances": b,
            "ledger": ledger(),
            "target": TARGET_EMERGENCY,
            "progress": round((b.get("EMERGENCY", 0) / TARGET_EMERGENCY) * 100),
            "proposal": proposal,
            "income": income,
            "planned_now": 0,
            "error": f"Proposal is not balanced. Total {total:.2f} != income {income:.2f}",
        })
    for v, a, r in zip(vaults, amounts, reasons):
        amount = float(a or 0)
        if amount:
            post_entry(v, amount, r)
    return RedirectResponse("/", status_code=303)

@app.post("/reset")
def reset():
    with conn() as c:
        c.execute("DELETE FROM ledger_entries")
        c.commit()
    return RedirectResponse("/", status_code=303)

if __name__ == "__main__":
    init_db()
    uvicorn.run(app, host="127.0.0.1", port=8000)
