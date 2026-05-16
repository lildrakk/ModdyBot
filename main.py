import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import json
from datetime import datetime, timedelta

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
# 🔥 SISTEMA DE MANTENIMIENTO
# ============================================================

MAINTENANCE_FILE = "maintenance.json"

ADMIN_WHITELIST = [1330486565528670284, 1394342273919225959]
USER_WHITELIST = [1330486565528670284]


def load_maintenance():
    try:
        with open(MAINTENANCE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"active": False, "reason": None, "expires_at": None}


def save_maintenance(data):
    with open(MAINTENANCE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# ============================================================
# 🔥 BLOQUEO GLOBAL UNIVERSAL (FUNCIONA EN TODAS LAS VERSIONES)
# ============================================================

@bot.listen("on_interaction")
async def maintenance_block(interaction: discord.Interaction):

    data = load_maintenance()

    # Si no hay mantenimiento → permitir
    if not data["active"]:
        return

    # Whitelist total
    if interaction.user.id in USER_WHITELIST:
        return

    # Permitir admins usar /mantenimiento
    if interaction.type == discord.InteractionType.application_command:
        if interaction.command.name == "mantenimiento":
            if interaction.user.id in ADMIN_WHITELIST:
                return

    # Bloquear todo lo demás
    embed = discord.Embed(
        title="🛠️ Mantenimiento activo",
        description="ModdyBot está realizando tareas internas.",
        color=discord.Color.orange()
    )

    try:
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except discord.InteractionResponded:
        await interaction.followup.send(embed=embed, ephemeral=True)

    # Detener ejecución del comando
    raise Exception("Bloqueado por mantenimiento")


# ============================================================
# 🔥 COMANDO /mantenimiento
# ============================================================

@bot.tree.command(name="mantenimiento")
async def mantenimiento(interaction: discord.Interaction, accion: str, tiempo: int = None, razon: str = None):

    if interaction.user.id not in ADMIN_WHITELIST:
        return await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)

    data = load_maintenance()

    if accion == "activar":
        data["active"] = True
        data["reason"] = razon
        if tiempo:
            data["expires_at"] = (datetime.now() + timedelta(minutes=tiempo)).isoformat()
        else:
            data["expires_at"] = None
        save_maintenance(data)
        return await interaction.response.send_message("🔴 Mantenimiento activado.", ephemeral=True)

    if accion == "desactivar":
        data["active"] = False
        data["reason"] = None
        data["expires_at"] = None
        save_maintenance(data)
        return await interaction.response.send_message("🟢 Mantenimiento desactivado.", ephemeral=True)

    if accion == "estado":
        estado = "🔴 Activado" if data["active"] else "🟢 Desactivado"
        embed = discord.Embed(title="📊 Estado del mantenimiento", color=discord.Color.blue())
        embed.add_field(name="Estado", value=estado, inline=False)
        embed.add_field(name="Razón", value=data["reason"] or "Ninguna", inline=False)
        embed.add_field(name="Expira", value=data["expires_at"] or "Sin tiempo", inline=False)
        return await interaction.response.send_message(embed=embed, ephemeral=True)


# ============================================================
# EVENTOS
# ============================================================

@bot.event
async def on_ready():
    print(f"🤖 Bot conectado como {bot.user}")
    bot.add_view(GiveawayView(giveaway_id=None))


TOKEN = os.getenv("TOKEN")
bot.run(TOKEN)
