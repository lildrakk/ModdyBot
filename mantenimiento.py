import discord
from discord.ext import commands
import json
from datetime import datetime, timedelta
import os

MAINTENANCE_FILE = "maintenance.json"

ADMIN_WHITELIST = [1394342273919225959]
USER_WHITELIST = []


def load_maintenance():
    if not os.path.exists(MAINTENANCE_FILE):
        data = {
            "active": False,
            "reason": None,
            "expires_at": None,
            "title": "🛠️ Mantenimiento activo",
            "message": "ModdyBot está realizando tareas internas."
        }
        with open(MAINTENANCE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return data

    try:
        with open(MAINTENANCE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {
            "active": False,
            "reason": None,
            "expires_at": None,
            "title": "🛠️ Mantenimiento activo",
            "message": "ModdyBot está realizando tareas internas."
        }


def save_maintenance(data):
    with open(MAINTENANCE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


class Mantenimiento(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # ============================================================
        # 🔥 CHECK GLOBAL (bloqueo real antes de ejecutar comandos)
        # ============================================================

        async def global_before_command(interaction: discord.Interaction):
            data = load_maintenance()

            # AUTO-DESACTIVACIÓN SI EL TIEMPO EXPIRÓ
            if data.get("expires_at"):
                try:
                    exp = datetime.fromisoformat(data["expires_at"])
                    if datetime.now() >= exp:
                        data["active"] = False
                        data["reason"] = None
                        data["expires_at"] = None
                        save_maintenance(data)
                        return True
                except:
                    pass

            # Si no hay mantenimiento → permitir
            if not data.get("active"):
                return True

            # Whitelist de usuarios
            if interaction.user.id in USER_WHITELIST:
                return True

            # Permitir a admins usar /mantenimiento
            if interaction.command and interaction.command.name == "mantenimiento":
                if interaction.user.id in ADMIN_WHITELIST:
                    return True

            # ============================================================
            # 🔥 EMBED PERSONALIZADO
            # ============================================================

            embed = discord.Embed(
                title=data.get("title") or "🛠️ Mantenimiento activo",
                description=data.get("message") or "ModdyBot está realizando tareas internas.",
                color=discord.Color(0x0A3D62)
            )

            # Razón
            if data.get("reason"):
                embed.add_field(name="Razón", value=data["reason"], inline=False)

            # Tiempo restante
            if data.get("expires_at"):
                try:
                    exp = datetime.fromisoformat(data["expires_at"])
                    restante = exp - datetime.now()
                    minutos = int(restante.total_seconds() // 60)
                    embed.add_field(name="Tiempo restante", value=f"{minutos} minutos", inline=False)
                except:
                    pass

            # Footer con soporte
            embed.set_footer(text="Si necesitas ayuda, abre un ticket en el servidor soporte:\nhttps://discord.gg/Q7XPqHSnCk")

            # Enviar mensaje si no se ha respondido
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed, ephemeral=True)

            return False  # BLOQUEA EL COMANDO

        bot.tree.interaction_check = global_before_command

    # ============================================================
    # 🔥 COMANDO /mantenimiento
    # ============================================================

    @discord.app_commands.command(name="mantenimiento")
    async def mantenimiento(
        self,
        interaction: discord.Interaction,
        accion: str,
        tiempo: int = None,
        razon: str = None,
        titulo: str = None,
        mensaje: str = None
    ):
        if interaction.user.id not in ADMIN_WHITELIST:
            return await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)

        data = load_maintenance()

        if accion == "activar":
            data["active"] = True
            data["reason"] = razon
            data["title"] = titulo or "🛠️ Mantenimiento activo"
            data["message"] = mensaje or "ModdyBot está realizando tareas internas."

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
            embed = discord.Embed(title="📊 Estado del mantenimiento", color=discord.Color(0x0A3D62))
            embed.add_field(name="Estado", value=estado, inline=False)
            embed.add_field(name="Razón", value=data["reason"] or "Ninguna", inline=False)
            embed.add_field(name="Expira", value=data["expires_at"] or "Sin tiempo", inline=False)
            embed.add_field(name="Título", value=data["title"], inline=False)
            embed.add_field(name="Mensaje", value=data["message"], inline=False)
            return await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Mantenimiento(bot))
