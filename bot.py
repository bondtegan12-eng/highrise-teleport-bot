from __future__ import annotations
import asyncio
import http.server
import os
import sqlite3
import threading
from pathlib import Path
from highrise import BaseBot, Position, User, CurrencyItem, Item

# --- WEB SERVER WORKAROUND ---
class KeepAliveServer(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_web_server():
    server = http.server.HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 8080))), KeepAliveServer)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()

# --- CONFIGURATION ---
ROOM_ID = "YOUR_ROOM_ID"
VIP_TIP_THRESHOLD_GOLD = 500
TELEPORT_DESTINATIONS = {"!vip": Position(x=17, y=9, z=18, facing="FrontRight")}

# --- DATABASE SETUP ---
DB_PATH = Path(os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", ".")) / "bot_data.db"

class TeleportBot(BaseBot):
    def __init__(self) -> None:
        super().__init__()
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS tips (user_id TEXT PRIMARY KEY, gold_amount INTEGER DEFAULT 0)")
            conn.commit()

    def _add_tip(self, user_id: str, amount: int) -> int:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO tips (user_id, gold_amount) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET gold_amount = gold_amount + ?", (user_id, amount, amount))
            conn.commit()
            return cursor.execute("SELECT gold_amount FROM tips WHERE user_id = ?", (user_id,)).fetchone()[0]

    async def on_tip(self, sender: User, receiver: User, tip: CurrencyItem | Item) -> None:
        if isinstance(tip, CurrencyItem):
            new_total = self._add_tip(sender.id, tip.amount)
            if new_total >= VIP_TIP_THRESHOLD_GOLD:
                await self.highrise.chat(f"💎 Thanks @{sender.username}! You unlocked VIP! Type !vip.")
                await self.highrise.teleport(sender.id, TELEPORT_DESTINATIONS["!vip"])

    async def on_chat(self, user: User, message: str) -> None:
        if message.strip().lower() == "!vip":
            with sqlite3.connect(DB_PATH) as conn:
                row = conn.execute("SELECT gold_amount FROM tips WHERE user_id = ?", (user.id,)).fetchone()
                if row and row[0] >= VIP_TIP_THRESHOLD_GOLD:
                    await self.highrise.teleport(user.id, TELEPORT_DESTINATIONS["!vip"])









