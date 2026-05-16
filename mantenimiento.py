import discord
from discord.ext import commands
import json
from datetime import datetime, timedelta

MAINTENANCE_FILE = "maintenance.json"

ADMIN_WHITELIST = [1394342273919225959]
USER_WHITELIST = []


def load_maintenance():
    try:
        with open(MAINTENANCE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"active": False, "reason": None, "expires_at": None}


def save_maintenance(data):
    with open(MAINTENANCE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


class Mantenimiento(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ============================================================
    # 🔥 BLOQUEO GLOBAL (ANTES DE EJECUTAR CUALQUIER COMANDO)
    # ============================================================

    @commands.Cog.listener("on_interaction")
    async def mantenimiento_block(self, interaction: discord.Interaction):

        data = load_maintenance()

        # Si no hay mantenimiento → permitir
        if not data.get("active"):
            return

        # Whitelist total
        if interaction.user.id in USER_WHITELIST:
            return

        # Permitir admins usar /mantenimiento
        if interaction.type == discord.InteractionType.application_command:
            if interaction.command.name == "mantenimiento":
                if interaction.user.id in ADMIN_WHITELIST:
                    return

        # Si el comando ya respondió → no bloquear
        if interaction.response.is_done():
            return

        # Bloquear el resto
        embed = discord.Embed(
            title="🛠️ Mantenimiento activo",
            description="ModdyBot está realizando tareas internas.",
            color=discord.Color.orange()
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

        # Detener ejecución del comando
        raise Exception("Bloqueado por mantenimiento")

    # ============================================================
    # 🔥 COMANDO /mantenimiento
    # ============================================================

    @discord.app_commands.command(name="mantenimiento")
    async def mantenimiento(self, interaction: discord.Interaction, accion: str, tiempo: int = None, razon: str = None):

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


async def setup(bot):
    await bot.add_cog(Mantenimiento(bot)) 
