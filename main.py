import discord
import os
from discord.ext import commands
from keep_alive import keep_alive


class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=";",
            intents=discord.Intents.all()
)


    async def setup_hook(self):
        # Cargar todos los COGS automáticamente
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py") and filename != "__init__.py":
                await self.load_extension(f"cogs.{filename[:-3]}")

                print(f"✔ Cargado: {filename}")


bot = Bot()

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Slash commands sincronizados: {len(synced)}")
    except Exception as e:
        print(f"Error al sincronizar comandos: {e}")


keep_alive()
TOKEN = os.getenv("TOKEN")
bot.run(TOKEN)

