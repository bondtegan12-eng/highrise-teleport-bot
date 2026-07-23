from __future__ import annotations

import asyncio
import http.server
import json
import os
import threading
import time
from pathlib import Path

from highrise import AnchorPosition, BaseBot, Position, User

# --- WEB SERVER WORKAROUND ---
class KeepAliveServer(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = http.server.HTTPServer(("0.0.0.0", port), KeepAliveServer)
    print(f"[Web Server] Keeping bot awake on port {port}")
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()

# --- HIGHRISE CONFIGURATION ---
ROOM_ID = "64a094a74134ad0fd77b8734"
OWNER_USER_ID = "61ccb2a0fa2db3178100252c"
CREW_ID = "69bf2d0c5654e2325acf9318" 
VIP_TIP_THRESHOLD_GOLD = 500
TARGET_DJ_USERNAME = "nxmb_"
OWNER_USERNAME = "sexytegann"

ANNOUNCEMENT_MESSAGE = "WELCOME TO BAMBS BDAY BASH JOIN THE PARTY -- tip me 500g for VIP!"

TELEPORT_DESTINATIONS: dict[str, Position] = {
    "!vip": Position(x=17, y=9, z=18, facing="FrontRight"),
    "!mod": Position(x=6, y=9, z=29, facing="FrontRight"),
    "!dj": Position(x=16, y=0, z=24, facing="FrontRight"),
    "!f1": Position(x=10, y=0, z=10, facing="FrontRight"),
}

class TeleportBot(BaseBot):
    def __init__(self) -> None:
        super().__init__()
        # In-memory tracking lists that handle room session joins cleanly
        self._tips_tracker: dict[str, int] = {}
        self._active_vip_users: set[str] = set()
        self._active_mod_users: set[str] = set()

    async def on_start(self, session_metadata) -> None:
        print(f"[TeleportBot] Connected to Highrise room {ROOM_ID}")
        asyncio.create_task(self._announcement_loop())

    async def _announcement_loop(self) -> None:
        while True:
            await asyncio.sleep(300)
            try:
                print("[Timer] Sending automated room announcement...")
                await self.highrise.chat(ANNOUNCEMENT_MESSAGE)
            except Exception as announce_err:
                print(f"[Timer Error] Could not send message: {announce_err}")

    async def on_user_join(self, user: User, position: Position | AnchorPosition) -> None:
        # Check active session zones immediately
        if user.id in self._active_mod_users or user.username.lower() == OWNER_USERNAME.lower() or user.id == OWNER_USER_ID:
            print(f"[Auto-Teleport] Returning Mod/Owner {user.username} back upstairs")
            await self._delayed_teleport(user, TELEPORT_DESTINATIONS["!mod"])
            return

        if user.id in self._active_vip_users:
            print(f"[Auto-Teleport] Returning VIP {user.username} back upstairs")
            await self._delayed_teleport(user, TELEPORT_DESTINATIONS["!vip"])
            return

        if user.username.lower() == TARGET_DJ_USERNAME.lower():
            await self._delayed_teleport(user, TELEPORT_DESTINATIONS["!dj"])
            return

        try:
            await self.highrise.chat(ANNOUNCEMENT_MESSAGE)
        except Exception as exc:
            print(f"[TeleportBot] Failed welcome message: {exc}")

    async def _delayed_teleport(self, user: User, position: Position, delay: float = 2.5) -> None:
        await asyncio.sleep(delay)
        try:
            await self.highrise.teleport(user.id, position)
        except Exception as exc:
            print(f"[TeleportBot] Teleport failed for {user.username}: {exc}")

    async def on_chat(self, user: User, message: str) -> None:
        try:
            command = message.strip().lower()
            is_owner = user.id == OWNER_USER_ID or user.username.lower() == OWNER_USERNAME.lower()
            
            if command == "!vip":
                total_tipped = self._tips_tracker.get(user.id, 0)
                if total_tipped >= VIP_TIP_THRESHOLD_GOLD or is_owner:
                    await self.highrise.teleport(user.id, TELEPORT_DESTINATIONS["!vip"])
                    self._active_vip_users.add(user.id)
                else:
                    await self.highrise.chat(f"@{user.username}, you need to tip {VIP_TIP_THRESHOLD_GOLD}g total for VIP access. You have tipped {total_tipped}g.")

            elif command == "!mod":
                is_crew_member = False
                if hasattr(user, 'crew_id') and getattr(user, 'crew_id') == CREW_ID:
                    is_crew_member = True

                if is_crew_member or is_owner:
                    await self.highrise.teleport(user.id, TELEPORT_DESTINATIONS["!mod"])
                    self._active_mod_users.add(user.id)
                else:
                    room_data = await self.highrise.get_room_users()
                    cached_user = next((u for u in room_data.content if u.id == user.id), None)
                    if cached_user and hasattr(cached_user, 'crew_id') and getattr(cached_user, 'crew_id') == CREW_ID:
                        await self.highrise.teleport(user.id, TELEPORT_DESTINATIONS["!mod"])
                        self._active_mod_users.add(user.id)
                    else:
                        await self.highrise.chat(f"@{user.username}, only members of our Crew can use !mod.")

            elif command == "!dj":
                if user.username.lower() == TARGET_DJ_USERNAME.lower() or is_owner:
                    await self.highrise.teleport(user.id, TELEPORT_DESTINATIONS["!dj"])
                else:
                    await self.highrise.chat(f"@{user.username}, only @{TARGET_DJ_USERNAME} can use !dj.")

            elif command == "!f1":
                await self.highrise.teleport(user.id, TELEPORT_DESTINATIONS["!f1"])
                self._active_mod_users.discard(user.id)
                self._active_vip_users.discard(user.id)
                    
        except Exception as chat_err:
            print(f"[Chat Handling Log] Caught entry: {chat_err}")

    async def on_tip(self, sender: User, receiver: User, tip: CurrencyItem) -> None:
        if receiver.id == self.highrise.my_id and isinstance(tip, CurrencyItem):
            current_total = self._tips_tracker.get(sender.id, 0) + tip.amount
            self._tips_tracker[sender.id] = current_total
            
            if current_total >= VIP_TIP_THRESHOLD_GOLD:
                await self.highrise.chat(f"🎉 @{sender.username} has unlocked permanent VIP access by reaching {current_total}g tipped!")

# --- PERSISTENT LOOP RUNNER ---
def start_bot_loop():
    from highrise.__main__ import BotDefinition, main as run_bots
    
    definitions = [
        BotDefinition(
            bot_class_path="bot:TeleportBot",
            room_id=ROOM_ID,
            api_token="2c001cb06c4370e639be2d7a24cf4e7a0a8600ef708d45d11cde0960653d0e8a6"
        )
    ]
    
    while True:
        try:
            print("[System] Launching bot connection framework...")
            asyncio.run(run_bots(definitions))
        except Exception as loop_err:
            print(f"[Connection Dropped] Room went empty or disconnected: {loop_err}")
            print("[System] Waiting 10 seconds before auto-rejoining...")
            time.sleep(10)

if __name__ == "__main__":
    start_bot_loop()




