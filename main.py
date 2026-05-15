import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# IMPORTANTE: importar la View persistente
from cogs.giveaways import GiveawayView

# -----------------------------
# SISTEMA DE VERSIONES
# -----------------------------
from cogs.version import load_versions, OWNER_ID

BOT_VERSION = "v1.2"  # Versión real del código


def version_permitida(user_id: int):
    versions = load_versions()
    if user_id == OWNER_ID:
        return versions["dev"]
    return versions["public"]


# -----------------------------
# SISTEMA DE MÓDULOS POR VERSIÓN
# -----------------------------
VERSION_NEW = {
    "v1.0": [
        "antibots",
        "antiflood",
        "antilinks",
        "antiraid",
        "info",
        "logs",
        "moderacion",
        "securityscan",
        "utilidad",
        "verification",
        "version",
        "welcome_dm",
        "help"
    ],

    "v1.1": ["antialts",
             "blacklistglobal",
             "blacklistserver"
    ],
    "v1.2": ["antiping",
             "statuspanel",
             "giveaways",
             "premium",
             "backups",
             "premiumcdms",
             "embed",
             "perfil",
             "lock",
             "mantenimiento"
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


# -----------------------------
# Cargar variables del .env
# -----------------------------
load_dotenv()


# =============================================
# DASHBOARD — ARRANCAR EN HILO SEPARADO
# =============================================
from dashboard import start_dashboard
start_dashboard()


class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=";",
            intents=discord.Intents.all()
        )

    async def setup_hook(self):
        versions = load_versions()
        owner_version = versions["dev"]

        print(f"\n🔧 Cargando módulos para versión {owner_version}...\n")

        modules = get_modules_for_version(owner_version)

        for module in modules:
            try:
                await self.load_extension(f"cogs.{module}")
                print(f"✔ Cargado: {module}.py")
            except Exception as e:
                print(f"❌ Error cargando {module}: {e}")

        print("\n✅ Módulos cargados correctamente.\n")

        print("==============================")
        print(f"📦 Versión del código: {BOT_VERSION}")
        print(f"🌍 Versión pública: {versions['public']}")
        print(f"🛠️ Versión dev: {versions['dev']}")
        print("==============================\n")

        print("\n🔍 Verificando comandos slash...\n")

        try:
            synced = await self.tree.sync()
            print(f"🌐 Comandos sincronizados: {len(synced)}")
        except Exception as e:
            print("❌ ERROR SINCRONIZANDO COMANDOS:")
            print(e)

        print("\n🔍 Revisando errores internos de comandos...\n")

        for cmd in self.tree.walk_commands():
            try:
                _ = cmd.name
            except Exception as e:
                print(f"❌ ERROR en el comando {cmd.name}: {e}")


bot = Bot()


# ============================
# CHECK GLOBAL DE MANTENIMIENTO
# ============================

async def global_maintenance_check(interaction: discord.Interaction):
    import json
    from datetime import datetime

    try:
        with open("maintenance.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except:
        return True  # si no existe, no bloquear

    # Si no está activo → permitir
    if not data.get("active"):
        return True

    # Whitelist de usuarios permitidos
    USER_WHITELIST = [1330486565528670284]
    ADMIN_WHITELIST = [1330486565528670284, 1394342273919225959]

    # Permitir a usuarios whitelisted
    if interaction.user.id in USER_WHITELIST:
        return True

    # Permitir a admins usar /mantenimiento
    if interaction.command and interaction.command.name == "mantenimiento":
        if interaction.user.id in ADMIN_WHITELIST:
            return True

    # Bloquear el resto
    from cogs.mantenimiento import Mantenimiento
    embed = Mantenimiento.build_default_embed(Mantenimiento)

    try:
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except discord.InteractionResponded:
        await interaction.followup.send(embed=embed, ephemeral=True)

    return False


bot.tree.add_check(global_maintenance_check)


# ============================
# ESTADO DINÁMICO
# ============================
async def actualizar_estado():
    servidores = len(bot.guilds)
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.playing,
            name=f"¡/help para comenzar! — protegiendo a {servidores} servidores"
        )
    )
    print(f"✔ Estado actualizado: protegiendo a {servidores} servidores")


# ============================
# EVENTOS
# ============================
@bot.event
async def on_ready():
    print(f"🤖 Bot conectado como {bot.user}")

    bot.add_view(GiveawayView(giveaway_id=None))

    try:
        synced = await bot.tree.sync()
        print(f"📘 Slash commands sincronizados: {len(synced)}")
    except Exception as e:
        print(f"❌ Error al sincronizar comandos: {e}")

    await actualizar_estado()


@bot.event
async def on_guild_join(guild):
    await actualizar_estado()


@bot.event
async def on_guild_remove(guild):
    await actualizar_estado()


# ============================
# INICIAR BOT
# ============================
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    print("❌ ERROR: No se encontró la variable TOKEN en el .env")
else:
    print("✔ TOKEN encontrado, iniciando bot...")

bot.run(TOKEN) 
