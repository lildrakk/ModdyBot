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

        print(f"\n🔧 Cargando módulos para versión {owner_version}...\n")

        modules = get_modules_for_version(owner_version)

        for module in modules:
            try:
                await self.load_extension(f"cogs.{module}")
                print(f"✔ Cargado: {module}.py")
            except Exception as e:
                print(f"❌ Error cargando {module}: {e}")

        print("\n🌐 Sincronizando comandos...")
        try:
            synced = await self.tree.sync()
            print(f"✔ Comandos sincronizados: {len(synced)}")
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
        return {
            "active": False,
            "reason": None,
            "activated_by": None,
            "expires_at": None
        }


def save_maintenance(data):
    with open(MAINTENANCE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# ============================================================
# 🔥 CHECK GLOBAL (FUNCIONA EN 2.3.2)
# ============================================================

async def maintenance_check(interaction: discord.Interaction):

    data = load_maintenance()

    # Si no hay mantenimiento → permitir
    if not data["active"]:
        return True

    # Whitelist total
    if interaction.user.id in USER_WHITELIST:
        return True

    # Permitir admins usar /mantenimiento
    if interaction.command and interaction.command.name == "mantenimiento":
        if interaction.user.id in ADMIN_WHITELIST:
            return True

    # Bloquear el resto
    embed = discord.Embed(
        title="🛠️ Mantenimiento activo",
        description="ModdyBot está realizando tareas internas. Inténtalo más tarde.",
        color=discord.Color(0x0A3D62)
    )

    if data["reason"]:
        embed.add_field(
            name="📌 Razón",
            value=f"```\n{data['reason']}\n```",
            inline=False
        )

    if data["expires_at"]:
        expires = datetime.fromisoformat(data["expires_at"])
        restante = expires - datetime.now()
        if restante.total_seconds() > 0:
            minutos = int(restante.total_seconds() // 60)
            segundos = int(restante.total_seconds() % 60)
            embed.add_field(
                name="⏳ Tiempo restante",
                value=f"{minutos} minutos y {segundos} segundos",
                inline=False
            )

    await interaction.response.send_message(embed=embed, ephemeral=True)
    return False


# AÑADIR CHECK GLOBAL AL ÁRBOL (ESTO ES LO QUE 2.3.2 SÍ SOPORTA)
bot.tree.add_check(maintenance_check)


# ============================================================
# 🔥 COMANDO /mantenimiento
# ============================================================

@bot.tree.command(name="mantenimiento", description="Control del modo mantenimiento del bot.")
async def mantenimiento(
    interaction: discord.Interaction,
    accion: str,
    tiempo: int = None,
    razon: str = None
):

    if interaction.user.id not in ADMIN_WHITELIST:
        return await interaction.response.send_message(
            "❌ No tienes permisos para usar este comando.",
            ephemeral=True
        )

    data = load_maintenance()

    if accion.lower() == "estado":
        estado = "🟢 Desactivado" if not data["active"] else "🔴 Activado"

        embed = discord.Embed(
            title="📊 Estado del mantenimiento",
            color=discord.Color(0x0A3D62)
        )
        embed.add_field(name="Estado", value=estado, inline=False)
        embed.add_field(name="Activado por", value=data["activated_by"] or "Nadie", inline=False)
        embed.add_field(name="Expira", value=data["expires_at"] or "Sin tiempo", inline=False)

        if data["reason"]:
            embed.add_field(name="Razón", value=f"```\n{data['reason']}\n```", inline=False)

        return await interaction.response.send_message(embed=embed, ephemeral=True)

    if accion.lower() == "activar":
        data["active"] = True
        data["activated_by"] = str(interaction.user)
        data["reason"] = razon

        if tiempo:
            expires_at = datetime.now() + timedelta(minutes=tiempo)
            data["expires_at"] = expires_at.isoformat()
        else:
            data["expires_at"] = None

        save_maintenance(data)

        return await interaction.response.send_message(
            f"🔴 Mantenimiento activado.\nTiempo: {tiempo or 'Indefinido'} minutos.",
            ephemeral=True
        )

    if accion.lower() == "desactivar":
        data["active"] = False
        data["expires_at"] = None
        data["reason"] = None
        save_maintenance(data)

        return await interaction.response.send_message(
            "🟢 Mantenimiento desactivado.",
            ephemeral=True
        )


# ============================================================
# EVENTOS
# ============================================================

@bot.event
async def on_ready():
    print(f"🤖 Bot conectado como {bot.user}")
    bot.add_view(GiveawayView(giveaway_id=None))

    try:
        await bot.tree.sync()
    except:
        pass


# ============================================================
# INICIAR BOT
# ============================================================

TOKEN = os.getenv("TOKEN")
bot.run(TOKEN) 
