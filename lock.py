import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import re
from datetime import datetime, timedelta
import pytz

COLOR_OFICIAL = discord.Color(0x0A3D62)

# Emojis que me diste
EMOJI_CANDADO = "<:candado:1491537429889552514>"
EMOJI_USER = "<:user:1488971290302877967>"
EMOJI_RAZON = "<:papel:1494026710503657534>"
EMOJI_DURACION = "<:cronometro:1493972193598509056>"
EMOJI_UNLOCK = "<a:ao_Tick:1485072554879357089>"
EMOJI_WARN = "<:no:1476336151835967640>"  # Para errores

# Zona horaria España
TZ = pytz.timezone("Europe/Madrid")

def parse_time(time_str):
    match = re.match(r"(\d+)(s|m|h|d)", time_str)
    if not match:
        return None

    value, unit = match.groups()
    value = int(value)

    if unit == "s":
        return value
    if unit == "m":
        return value * 60
    if unit == "h":
        return value * 3600
    if unit == "d":
        return value * 86400

    return None

class Lock(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.lock_times = {}  # Guardar cuándo se bloqueó cada canal

    @app_commands.command(
        name="lock",
        description="Bloquea el canal con tiempo opcional y razón."
    )
    @app_commands.describe(
        tiempo="Ejemplo: 10m, 1h, 30s (opcional)",
        razon="Razón del bloqueo (opcional)"
    )
    async def lock(self, interaction: discord.Interaction, tiempo: str = None, razon: str = "No especificada"):

        canal = interaction.channel

        # Verificar permisos
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message(
                f"{EMOJI_WARN} No tienes permisos para bloquear canales.",
                ephemeral=True
            )

        # Parsear tiempo
        segundos = None
        if tiempo:
            segundos = parse_time(tiempo)
            if segundos is None:
                return await interaction.response.send_message(
                    f"{EMOJI_WARN} Formato de tiempo inválido. Usa: 10m, 1h, 30s, 2d",
                    ephemeral=True
                )

        # Bloquear canal
        overwrite = canal.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = False
        await canal.set_permissions(interaction.guild.default_role, overwrite=overwrite)

        # Guardar hora de bloqueo
        self.lock_times[canal.id] = datetime.now(TZ)

        # Embed de bloqueo
        embed = discord.Embed(
            title=f"{EMOJI_CANDADO} Canal bloqueado",
            color=COLOR_OFICIAL
        )

        embed.add_field(name=f"{EMOJI_CANDADO} Canal", value=canal.mention, inline=False)
        embed.add_field(name=f"{EMOJI_USER} Bloqueado por", value=interaction.user.mention, inline=False)
        embed.add_field(name=f"{EMOJI_RAZON} Razón", value=razon, inline=False)

        if segundos:
            embed.add_field(name=f"{EMOJI_DURACION} Duración", value=tiempo, inline=False)

        await interaction.response.send_message(embed=embed)

        # Si hay tiempo → desbloquear después
        if segundos:
            await asyncio.sleep(segundos)

            overwrite.send_messages = None
            await canal.set_permissions(interaction.guild.default_role, overwrite=overwrite)

            embed2 = discord.Embed(
                title=f"{EMOJI_UNLOCK} Canal desbloqueado",
                description=f"El canal {canal.mention} ha sido desbloqueado automáticamente.",
                color=COLOR_OFICIAL
            )

            await canal.send(embed=embed2)

    # ============================
    # DESBLOQUEO MANUAL
    # ============================

    @app_commands.command(
        name="unlock",
        description="Desbloquea el canal manualmente."
    )
    async def unlock(self, interaction: discord.Interaction):

        canal = interaction.channel

        # Verificar permisos
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message(
                f"{EMOJI_WARN} No tienes permisos para desbloquear canales.",
                ephemeral=True
            )

        # Desbloquear
        overwrite = canal.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = None
        await canal.set_permissions(interaction.guild.default_role, overwrite=overwrite)

        # Calcular cuánto tiempo estuvo bloqueado
        if canal.id in self.lock_times:
            inicio = self.lock_times[canal.id]
            ahora = datetime.now(TZ)
            diferencia = ahora - inicio

            horas, resto = divmod(diferencia.seconds, 3600)
            minutos, segundos = divmod(resto, 60)

            tiempo_bloqueado = f"{horas}h {minutos}m {segundos}s"
        else:
            tiempo_bloqueado = "Desconocido"

        # Embed de desbloqueo manual
        embed = discord.Embed(
            title=f"{EMOJI_UNLOCK} Canal desbloqueado manualmente",
            color=COLOR_OFICIAL
        )

        embed.add_field(name=f"{EMOJI_CANDADO} Canal", value=canal.mention, inline=False)
        embed.add_field(name=f"{EMOJI_USER} Desbloqueado por", value=interaction.user.mention, inline=False)
        embed.add_field(name=f"{EMOJI_DURACION} Tiempo bloqueado", value=f"||{tiempo_bloqueado}||", inline=False)

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Lock(bot))
