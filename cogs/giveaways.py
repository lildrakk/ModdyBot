import discord
from discord.ext import commands
import asyncio
import random
import datetime
import json
import os

RUTA_JSON = "giveaways.json"

# ============================
# CARGAR / GUARDAR JSON
# ============================

def cargar_giveaways():
    if not os.path.exists(RUTA_JSON):
        with open(RUTA_JSON, "w") as f:
            json.dump({}, f)
    with open(RUTA_JSON, "r") as f:
        return json.load(f)

def guardar_giveaways(data):
    with open(RUTA_JSON, "w") as f:
        json.dump(data, f, indent=4)

giveaways = cargar_giveaways()

# ============================
# VIEW DEL BOTÓN DE PARTICIPAR (PERSISTENTE)
# ============================

class GiveawayView(discord.ui.View):
    def __init__(self, giveaway_id):
        super().__init__(timeout=None)
        self.giveaway_id = str(giveaway_id)

    @discord.ui.button(label="🎉 Participar", style=discord.ButtonStyle.blurple, custom_id="giveaway_participar")
    async def participar(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = giveaways.get(self.giveaway_id)

        if not data:
            return await interaction.response.send_message(
                "❌ Este sorteo ya no existe.",
                ephemeral=True
            )

        user = interaction.user

        if str(user.id) in data["participantes"]:
            return await interaction.response.send_message(
                "❗ Ya estabas participando en este sorteo.",
                ephemeral=True
            )

        data["participantes"].append(str(user.id))
        guardar_giveaways(giveaways)

        await interaction.response.send_message(
            "🎉 ¡Has entrado correctamente al sorteo!",
            ephemeral=True
        )

# ============================
# COG PRINCIPAL
# ============================

class Giveaways(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ============================
    # /giveaway
    # ============================

    @discord.app_commands.command(
        name="giveaway",
        description="Crea un sorteo (10s, 5m, 2h, 1d)."
    )
    @discord.app_commands.describe(
        tiempo="Duración del sorteo (10s, 5m, 2h, 1d)",
        ganadores="Cantidad de ganadores",
        premio="Premio del sorteo"
    )
    async def giveaway(self, interaction: discord.Interaction, tiempo: str, ganadores: int, premio: str):

        unidades = {"s": 1, "m": 60, "h": 3600, "d": 86400}

        if tiempo[-1].lower() not in unidades:
            return await interaction.response.send_message(
                "❌ Formato inválido. Usa: 10s, 5m, 2h, 1d",
                ephemeral=True
            )

        try:
            cantidad = int(tiempo[:-1])
        except ValueError:
            return await interaction.response.send_message(
                "❌ El tiempo debe empezar con un número. Ejemplo: 10s",
                ephemeral=True
            )

        duracion = cantidad * unidades[tiempo[-1].lower()]
        fin = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=duracion)
        timestamp = int(fin.timestamp())

        giveaway_id = random.randint(100000, 999999)

        giveaways[str(giveaway_id)] = {
            "host": interaction.user.id,
            "premio": premio,
            "fin": timestamp,
            "participantes": [],
            "canal": interaction.channel.id,
            "ganadores": ganadores
        }

        guardar_giveaways(giveaways)

        embed = discord.Embed(
            title="<:giveaway:1494074344341639188> **SORTEO ACTIVO** <:giveaway:1494074344341639188>",
            description=(
                "<:regalo:1483506548495093957> ¡Un nuevo sorteo ha comenzado en el servidor!\n\n"
                "**<a:fuegoazul:1483506592325439540> Cómo participar:**\n"
                "**1.** Pulsa el botón **Participar** de abajo\n"
                "**2.** Quédate en el servidor durante todo el sorteo\n"
                "**3.** Espera a que termine el tiempo\n\n"
            ),
            color=discord.Color(0x0A3D62)
        )

        embed.add_field(name="<a:flechazul:1492182951532826684> Premio", value=premio, inline=False)
        embed.add_field(name="<a:fuegoazul:1483506592325439540> Ganadores", value=str(ganadores), inline=True)
        embed.add_field(name="<:user:1488971290302877967> Organizado por", value=interaction.user.mention, inline=True)
        embed.add_field(name="<:cronometro:1493972193598509056> Finaliza", value=f"<t:{timestamp}:R>", inline=False)
        embed.set_footer(text=f"ID del sorteo: {giveaway_id}")
        embed.set_image(url="https://raw.githubusercontent.com/lildrakk/ModdyBot-web/eb6b1cb04336b0929a83cacad3b6834d11cedf8c/standard-3.gif")

        view = GiveawayView(giveaway_id)
        mensaje = await interaction.response.send_message(embed=embed, view=view)
        mensaje_obj = await interaction.original_response()

        # Esperar a que termine
        await asyncio.sleep(duracion)

        data = giveaways.get(str(giveaway_id))
        if not data:
            return

        # Filtrar participantes válidos
        guild = interaction.guild
        participantes_validos = [uid for uid in data["participantes"] if guild.get_member(int(uid)) is not None]
        data["participantes"] = participantes_validos
        guardar_giveaways(giveaways)

        if len(participantes_validos) == 0:
            await interaction.channel.send(f"<:no:1476336151835967640> Nadie participó en el sorteo **{giveaway_id}**.")
            del giveaways[str(giveaway_id)]
            guardar_giveaways(giveaways)
            return

        ganadores_finales = random.sample(participantes_validos, min(len(participantes_validos), data["ganadores"]))

        # Construir texto según número de ganadores
        if len(ganadores_finales) == 1:
            texto_ganadores = f"<@{ganadores_finales[0]}>"
        else:
            texto_ganadores = " y ".join([f"<@{g}>" for g in ganadores_finales])

        resultado = discord.Embed(
            title="<:giveaway:1494074344341639188> **SORTEO FINALIZADO** <:giveaway:1494074344341639188>",
            description="¡Aquí están los ganadores!",
            color=discord.Color(0x0A3D62)
        )
        resultado.add_field(name="<:regalo:1483506548495093957> Premio", value=data["premio"], inline=False)
        resultado.add_field(
            name="<a:flechazul:1492182951532826684> Ganadores",
            value="\n".join([f"<@{g}>" for g in ganadores_finales]),
            inline=False
        )
        resultado.set_footer(text=f"ID del sorteo: {giveaway_id}")
        resultado.set_image(url="https://raw.githubusercontent.com/lildrakk/ModdyBot-web/eb6b1cb04336b0929a83cacad3b6834d11cedf8c/standard-3.gif")

        # Responder al mensaje original del sorteo
        await mensaje_obj.reply(
            content=f"🎉 <@{interaction.user.id}> los ganadores del sorteo fueron {texto_ganadores}",
            embed=resultado
        )

    # ============================
    # /giveaway_info
    # ============================

    @discord.app_commands.command(
        name="giveaway_info",
        description="Muestra información detallada de un sorteo."
    )
    @discord.app_commands.describe(
        giveaway_id="ID del sorteo (lo ves en el embed)"
    )
    async def giveaway_info(self, interaction: discord.Interaction, giveaway_id: int):

        data = giveaways.get(str(giveaway_id))
        if not data:
            return await interaction.response.send_message("❌ Ese ID de sorteo no existe.", ephemeral=True)

        guild = interaction.guild

        # Participantes válidos
        participantes_validos = [uid for uid in data["participantes"] if guild.get_member(int(uid))]

        # Tiempo restante
        ahora = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        fin = data["fin"]
        restante = fin - ahora

        estado = "🟢 Activo" if restante > 0 else "🔴 Finalizado"

        embed = discord.Embed(
            title="<a:alarmazul:1491858094043693177> Información del sorteo",
            color=discord.Color(0x0A3D62)
        )

        embed.add_field(name="🎁 Premio", value=data["premio"], inline=False)
        embed.add_field(name="👤 Host", value=f"<@{data['host']}>", inline=True)
        embed.add_field(name="🏆 Ganadores configurados", value=str(data["ganadores"]), inline=True)
        embed.add_field(name="📌 Estado", value=estado, inline=False)
        embed.add_field(name="📅 Finaliza", value=f"<t:{data['fin']}:F>", inline=False)

        if restante > 0:
            embed.add_field(name="⏳ Tiempo restante", value=f"<t:{data['fin']}:R>", inline=False)

        embed.add_field(name="📨 Canal", value=f"<#{data['canal']}>", inline=False)
        embed.add_field(name="🆔 ID del sorteo", value=str(giveaway_id), inline=False)

        if participantes_validos:
            lista = "\n".join([f"• <@{uid}>" for uid in participantes_validos])
        else:
            lista = "Nadie ha participado aún."

        embed.add_field(name="👥 Participantes", value=lista, inline=False)

        embed.set_thumbnail(url="https://raw.githubusercontent.com/lildrakk/ModdyBot-web/eb6b1cb04336b0929a83cacad3b6834d11cedf8c/standard-3.gif")

        await interaction.response.send_message(embed=embed, ephemeral=False)

    # ============================
    # /reroll
    # ============================

    @discord.app_commands.command(
        name="reroll",
        description="Elige nuevos ganadores usando el ID del sorteo."
    )
    @discord.app_commands.describe(
        giveaway_id="ID del sorteo (lo ves en el embed)"
    )
    async def reroll(self, interaction: discord.Interaction, giveaway_id: int):
        data = giveaways.get(str(giveaway_id))
        if not data:
            return await interaction.response.send_message("❌ Ese ID de sorteo no existe.", ephemeral=True)
        if interaction.user.id != data["host"]:
            return await interaction.response.send_message("❌ Solo el creador del sorteo puede hacer reroll.", ephemeral=True)

        guild = interaction.guild
        participantes_validos = [uid for uid in data["participantes"] if guild.get_member(int(uid)) is not None]
        data["participantes"] = participantes_validos
        guardar_giveaways(giveaways)

        if len(participantes_validos) == 0:
            return await interaction.response.send_message("❌ No hay participantes válidos para reroll.", ephemeral=True)

        ganadores_finales = random.sample(participantes_validos, min(len(participantes_validos), data["ganadores"]))

        # Construir texto según número de ganadores
        if len(ganadores_finales) == 1:
            texto_ganadores = f"<@{ganadores_finales[0]}>"
        else:
            texto_ganadores = " y ".join([f"<@{g}>" for g in ganadores_finales])

        embed = discord.Embed(
            title="<a:alarmazul:1491858094043693177> **REROLL REALIZADO**",
            description="Se han elegido nuevos ganadores",
            color=discord.Color(0x0A3D62)
        )

        embed.add_field(name="<:regalo:1483506548495093957> Premio", value=data["premio"], inline=False)
        embed.add_field(
            name="<a:flechazul:1491858094043693177> Nuevos ganadores",
            value="\n".join([f"<@{g}>" for g in ganadores_finales]),
            inline=False
        )

        embed.set_footer(text=f"ID del sorteo: {giveaway_id}")
        embed.set_image(url="https://raw.githubusercontent.com/lildrakk/ModdyBot-web/eb6b1cb04336b0929a83cacad3b6834d11cedf8c/standard-3.gif")

        canal = self.bot.get_channel(data["canal"])

        await canal.send(
            content=f"<:giveaway:1494074344341639188> <@{data['host']}> los nuevos ganadores del sorteo son {texto_ganadores}",
            embed=embed
        )

# ============================
# SETUP
# ============================

async def setup(bot):
    await bot.add_cog(Giveaways(bot))
