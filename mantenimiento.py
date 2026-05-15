import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
from datetime import datetime, timedelta

MAINTENANCE_FILE = "maintenance.json"

ADMIN_WHITELIST = [1330486565528670284, 1394342273919225959]
USER_WHITELIST = [1330486565528670284]

COLOR_OFICIAL = discord.Color(0x0A3D62)
SOPORTE = "https://discord.gg/Q7XPqHSnCk"


class Mantenimiento(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = self.load_data()
        self.check_expiration.start()

    # ============================
    # JSON
    # ============================

    def load_data(self):
        try:
            with open(MAINTENANCE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "active": False,
                "reason": None,
                "activated_by": None,
                "expires_at": None
            }

    def save_data(self):
        with open(MAINTENANCE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

    # ============================
    # TAREA AUTOMÁTICA
    # ============================

    @tasks.loop(seconds=5)
    async def check_expiration(self):
        if self.data["active"] and self.data["expires_at"]:
            expires = datetime.fromisoformat(self.data["expires_at"])
            if datetime.now() >= expires:
                self.data["active"] = False
                self.data["expires_at"] = None
                self.save_data()
                print("🟢 Mantenimiento desactivado automáticamente por tiempo.")

    # ============================
    # BLOQUEO GLOBAL REAL
    # ============================

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.type == discord.InteractionType.application_command:
            return

        if self.data["active"] and interaction.user.id not in USER_WHITELIST:
            embed = self.build_default_embed()
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                pass
            return

    # ============================
    # EMBED POR DEFECTO
    # ============================

    def build_default_embed(self):
        embed = discord.Embed(
            title="🛠️ Mantenimiento 🛠️",
            description=(
                "ModdyBot está realizando tareas internas para mejorar su rendimiento, estabilidad y seguridad.\n"
                "Durante este proceso, algunas funciones permanecerán temporalmente deshabilitadas.\n\n"
                "Agradecemos tu paciencia mientras trabajamos para ofrecerte la mejor experiencia posible."
            ),
            color=COLOR_OFICIAL
        )

        if self.data.get("reason"):
            embed.add_field(
                name="📌 Razón del mantenimiento",
                value=f"```\n{self.data['reason']}\n```",
                inline=False
            )

        if self.data.get("expires_at"):
            expires = datetime.fromisoformat(self.data["expires_at"])
            restante = expires - datetime.now()
            minutos = int(restante.total_seconds() // 60)
            segundos = int(restante.total_seconds() % 60)
            embed.add_field(
                name="⏳ Tiempo restante",
                value=f"{minutos} minutos y {segundos} segundos",
                inline=False
            )

        embed.add_field(
            name="🔗 Soporte",
            value=f"[Haz clic aquí para entrar al servidor de soporte]({SOPORTE})",
            inline=False
        )

        return embed

    # ============================
    # COMANDO /mantenimiento
    # ============================

    @app_commands.command(name="mantenimiento", description="Control del modo mantenimiento de ModdyBot.")
    @app_commands.describe(
        accion="Acción a realizar",
        tiempo="Tiempo en minutos (opcional)",
        razon="Razón del mantenimiento (opcional)"
    )
    @app_commands.choices(accion=[
        app_commands.Choice(name="Activar", value="activar"),
        app_commands.Choice(name="Desactivar", value="desactivar"),
        app_commands.Choice(name="Estado", value="estado")
    ])
    async def mantenimiento(self, interaction: discord.Interaction, accion: app_commands.Choice[str], tiempo: int = None, razon: str = None):

        if interaction.user.id not in ADMIN_WHITELIST:
            return await interaction.response.send_message(
                "❌ No tienes permisos para usar este comando.",
                ephemeral=True
            )

        if accion.value == "estado":
            estado = "🟢 Desactivado" if not self.data["active"] else "🔴 Activado"

            embed = discord.Embed(
                title="📊 Estado del Mantenimiento",
                color=COLOR_OFICIAL
            )
            embed.add_field(name="Estado", value=estado, inline=False)
            embed.add_field(name="Activado por", value=self.data["activated_by"] or "Nadie", inline=False)
            embed.add_field(name="Expira", value=self.data["expires_at"] or "Sin tiempo", inline=False)

            if self.data["reason"]:
                embed.add_field(
                    name="Razón",
                    value=f"```\n{self.data['reason']}\n```",
                    inline=False
                )

            return await interaction.response.send_message(embed=embed, ephemeral=True)

        if accion.value == "activar":
            self.data["active"] = True
            self.data["activated_by"] = str(interaction.user)
            self.data["reason"] = razon

            if tiempo:
                expires_at = datetime.now() + timedelta(minutes=tiempo)
                self.data["expires_at"] = expires_at.isoformat()
            else:
                self.data["expires_at"] = None

            self.save_data()

            embed = discord.Embed(
                title="🔴 Mantenimiento Activado",
                color=COLOR_OFICIAL
            )
            embed.add_field(name="Activado por", value=str(interaction.user), inline=False)
            embed.add_field(name="Tiempo", value=f"{tiempo} minutos" if tiempo else "Indefinido", inline=False)

            if razon:
                embed.add_field(name="Razón", value=f"```\n{razon}\n```", inline=False)

            return await interaction.response.send_message(embed=embed, ephemeral=True)

        if accion.value == "desactivar":
            self.data["active"] = False
            self.data["expires_at"] = None
            self.data["reason"] = None
            self.save_data()

            embed = discord.Embed(
                title="🟢 Mantenimiento Desactivado",
                color=COLOR_OFICIAL
            )

            return await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Mantenimiento(bot)) 
