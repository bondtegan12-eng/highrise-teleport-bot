import asyncio
import os
from aiohttp import web
from highrise import BaseBot, Position, CurrencyItem
from highrise.models import SessionMetadata, User

# --- ELIMINATE RENDER PORT CLASHES ---
async def start_web_server():
    app = web.Application()
    runner = web.AppRunner(app)
    await runner.setup()
    # Using port 0 forces Render to always pick a free open port, completely stopping clashing errors
    site = web.TCPSite(runner, '0.0.0.0', 0)
    await site.start()
    print("🌍 Keep-Alive web system securely active!")

# --- THE UN-CRASHABLE BOT LOGIC ---
class MyBot(BaseBot):
    def __init__(self):
        super().__init__()
        # Temporary memory to store who bought VIP during this session
        self.vip_users = set() 
        
        # Exact rounded integer coordinates to prevent Highrise server kicks
        self.mod_area = Position(x=7, y=9, z=24, facing="Front")
        self.dj_area = Position(x=16, y=0, z=24, facing="FrontRight")
        self.vip_area = Position(x=15, y=9, z=18, facing="Front")

    async def on_start(self, session_metadata: SessionMetadata) -> None:
        asyncio.create_task(start_web_server())

    async def on_chat(self, user: User, message: str) -> None:
        # Isolated execution: Wrap everything in a shield so errors CANNOT kick the bot
        try:
            username_clean = str(user.username).lower().strip()
            msg_clean = message.lower().strip()

            # --- 1. MODERATOR LOUNGE COMMAND ---
            if msg_clean == "!mod":
                # Direct check: Only you (the owner) can use this command. No complex server checks.
                if username_clean == "sexytegann" or username_clean == "bondtegan":
                    await self.highrise.teleport(user.id, self.mod_area)
                    await self.highrise.chat(f"Teleported Owner {user.username} to the Moderator Lounge!")
                else:
                    await self.highrise.chat(f"Sorry {user.username}, this command is strictly for the Owner.")

            # --- 2. DJ STAGE COMMAND ---
            elif msg_clean == "!dj":
                # Direct check: Only nxmb_ or yourself can use this command.
                if username_clean == "nxmb_" or username_clean == "sexytegann" or username_clean == "bondtegan":
                    await self.highrise.teleport(user.id, self.dj_area)
                    await self.highrise.chat(f" Welcome to the stage, DJ {user.username}!")
                else:
                    await self.highrise.chat(f"Sorry {user.username}, the DJ Booth is reserved exclusively for @nxmb_")

            # --- 3. VIP LOUNGE COMMAND ---
            elif msg_clean == "!vip":
                # If they tipped 500g or if they are you, let them in natively
                if user.id in self.vip_users or username_clean == "sexytegann" or username_clean == "bondtegan":
                    await self.highrise.teleport(user.id, self.vip_area)
                else:
                    await self.highrise.chat(f"You haven't unlocked VIP yet, {user.username}! Tip 500g to unlock.")

        except Exception as e:
            print(f"Safety caught a chat processing error: {e}")

    async def on_tip(self, sender: User, receiver: User, tip: CurrencyItem) -> None:
        try:
            if receiver.id == self.id and tip.type == "gold":
                if tip.amount >= 500:
                    self.vip_users.add(sender.id)
                    await self.highrise.send_whisper(sender.id, "🎉 Thank you for the tip! You have unlocked the !vip lounge for this session.")
                    await self.highrise.chat(f"🌟 {sender.username} just tipped 500g and unlocked VIP status! 🌟")
        except Exception as e:
            print(f"Safety caught a tip processing error: {e}")

if __name__ == "__main__":
    from highrise.__main__ import main, BotDefinition
    
    os.environ["api_token"] = "2c001cb06c4370e639be2d7a24cf4e7a0a860ef708d45d11cde0960653d0e8a6"
    os.environ["room_id"] = "64a094a74134ad0fd77b8734"
    
    loop = asyncio.get_event_loop()
    room = os.environ.get("room_id")
    token = os.environ.get("api_token")
        
    definitions = [BotDefinition(MyBot(), room, token)]
    loop.run_until_complete(main(definitions))
