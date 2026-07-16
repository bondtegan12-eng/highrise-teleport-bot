from typing import Union
import asyncio
from highrise import BaseBot, Position
from highrise.models import User, CurrencyItem, Item

class TeleportBot(BaseBot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vip_users = set()
        self.my_crew = {"sexytegann"}
        self.designated_dj = "dj_username_here"

    async def on_chat(self, user: User, message: str) -> None:
        command = message.strip().lower()
        username_lower = user.username.lower()
        
        if command == "!crewjoin":
            self.my_crew.add(username_lower)
            await self.highrise.send_whisper(user.id, "✅ Added! You can now use !mod to teleport.")
            return

        if command == "!mod":
            if username_lower in self.my_crew:
                # 🚨 TESTING GROUND LOCATION 🚨
                # This moves you safely to the main room floor grid center
                test_spot = Position(x=8.0, y=0.0, z=8.0, facing="Front")
                asyncio.create_task(self.teleport_user(user, test_spot))
            else:
                await self.highrise.send_whisper(user.id, "❌ Please type !crewjoin first.")

    async def teleport_user(self, user: User, position: Position) -> None:
        try:
            await asyncio.sleep(0.1)
            await self.highrise.teleport(user.id, position)
            await self.highrise.send_whisper(user.id, "Teleported successfully!")
        except Exception as e:
            print(f"Error executing teleport: {e}")
