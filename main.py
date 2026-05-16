import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

from cogs.giveaways import GiveawayView
from cogs.version import load_versions, OWNER_ID

BOT_VERSION = "v1.2"

load_dotenv()

# ============================================================
# SISTEMA DE VERSIONES
# ============================================================

def version_permitida(user_id: int):
    versions = load_versions()
    if user_id == OWNER_ID:
        return versions["dev"]
    return versions["public"]


VERSION_NEW = {
    "v1.0": [
        "antibots", "antiflood", "antilinks", "antiraid", "info",
        "logs", "moderacion", "securityscan", "utilidad",
        "verification", "version", "welcome_dm", "help"
    ],

    "v1.1": [
        "antialts", "blacklistglobal", "blacklistserver"
    ],

    "v1.2": [
        "antiping", "statuspanel", "giveaways", "premium",
        "backups", "premiumcdms", "embed", "perfil",
        "lock"
    ]
}

VERSION_REMOVED = {}

def get_modules_for_version(version):
    versions = list(VERSION_NEW.keys())
    index = versions.index(version)
    modules = []
    for i in range(index + 1):
        modules.extend(VERSION_NEW[versions[i]])
    for i in range(index + 1):
        removed = VERSION_REMOVED.get(versions[i], [])
        for r in removed:
            if r in modules:
                modules.remove(r)
    return modules


# ============================================================
# BOT
# ============================================================

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=";",
            intents=discord.Intents.all()
        )

    async def setup_hook(self):

        # 🔥 Cargar PRIMERO el COG de mantenimiento
        await self.load_extension("cogs.mantenimiento")

        versions = load_versions()
        owner_version = versions["dev"]

        modules = get_modules_for_version(owner_version)

        for module in modules:
            try:
                await self.load_extension(f"cogs.{module}")
                print(f"✔ Cargado: {module}.py")
            except Exception as e:
                print(f"❌ Error cargando {module}: {e}")

        try:
            await self.tree.sync()
            print("✔ Slash commands sincronizados")
        except Exception as e:
            print(f"❌ Error sincronizando: {e}")


bot = Bot()


# ============================================================
# EVENTOS
# ============================================================

@bot.event
async def on_ready():
    print(f"🤖 Bot conectado como {bot.user}")
    bot.add_view(GiveawayView(giveaway_id=None))


TOKEN = os.getenv("TOKEN")
bot.run(TOKEN)
