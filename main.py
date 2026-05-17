import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from pymongo import MongoClient
import datetime

from cogs.giveaways import GiveawayView
from cogs.version import load_versions, OWNER_ID
from dashboard import start_dashboard

BOT_VERSION = "v1.2"

load_dotenv()

# =============================================
# MONGODB — STATS EN TIEMPO REAL
# =============================================
try:
    _mongo = MongoClient(os.getenv("MONGODB_URI"))
    _db = _mongo[os.getenv("MONGODB_DB", "moddybot")]
    print("✔ MongoDB conectado")
except Exception as e:
    _db = None
    print(f"⚠️ MongoDB no disponible: {e}")


def update_bot_stats(bot: commands.Bot):
    """Actualiza las stats del bot en MongoDB para la landing page."""
    if _db is None:
        return
    try:
        now = datetime.datetime.utcnow()

        from datetime import date

        def last_sunday(year, month):
            d = date(year, month, 31 if month in [1, 3, 5, 7, 8, 10, 12] else 30)
            while d.weekday() != 6:
                d -= datetime.timedelta(days=1)
            return d

        year = now.year
        summer_start = datetime.datetime(year, 3, last_sunday(year, 3).day, 1, 0)
        summer_end = datetime.datetime(year, 10, last_sunday(year, 10).day, 1, 0)
        offset = 2 if summer_start <= now < summer_end else 1
        spain_time = now + datetime.timedelta(hours=offset)

        _db["stats"].replace_one(
            {"_id": "bot"},
            {
                "_id": "bot",
                "guilds": len(bot.guilds),
                "users": sum(g.member_count or 0 for g in bot.guilds),
                "latency": round(bot.latency * 1000),
                "commands": len(bot.tree.get_commands()),
                "updated": spain_time.strftime("%H:%M:%S"),
            },
            upsert=True,
        )
    except Exception as e:
        print(f"[STATS] Error: {e}")


# =============================================
# DASHBOARD
# =============================================
start_dashboard()

# =============================================
# VERSIONES Y MÓDULOS
# =============================================
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
    "v1.1": ["antialts", "blacklistglobal", "blacklistserver"],
    "v1.2": [
        "antiping", "statuspanel", "giveaways", "premium",
        "backups", "premiumcdms", "embed", "perfil", "lock"
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


# =============================================
# BOT
# =============================================
class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix=";", intents=intents)

    async def update_status(self):
        guild_count = len(self.guilds)
        text = f"¡/help para comenzar! | protegiendo a {guild_count} servidores"
        await self.change_presence(
            activity=discord.Game(name=text)
        )

    async def setup_hook(self):
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


@bot.event
async def on_ready():
    print(f"🤖 Bot conectado como {bot.user}")
    bot.add_view(GiveawayView(giveaway_id=None))
    await bot.update_status()
    update_bot_stats(bot)


@bot.event
async def on_guild_join(guild):
    await bot.update_status()
    update_bot_stats(bot)


@bot.event
async def on_guild_remove(guild):
    await bot.update_status()
    update_bot_stats(bot)


TOKEN = os.getenv("TOKEN")
bot.run(TOKEN) 
