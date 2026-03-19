import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
import asyncio
import re
import random
from datetime import datetime, timedelta

# Ruta correcta para Render
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
GIVEAWAY_FILE = os.path.join(BASE_DIR, "giveaways.json")

# ============================
# JSON LOADER
# ============================

def load_giveaways():
    if not os.path.exists(GIVEAWAY_FILE):
        with open(GIVEAWAY_FILE, "w") as f:
            json.dump({}, f, indent=4)

    with open(GIVEAWAY_FILE, "r") as f:
        return json.load(f)


def save_giveaways(data):
    with open(GIVEAWAY_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ============================
# PARSEADOR DE TIEMPO
# ============================

def parse_time(tiempo: str):
    tiempo = tiempo.lower()
    pattern = r"(\d+)([smhd])"
    matches = re.findall(pattern, tiempo)

    if not matches:
        return None

    total = 0
    for cantidad, unidad in matches:
        cantidad = int(cantidad)
        if unidad == "s":
            total += cantidad
        elif unidad == "m":
            total += cantidad * 60
        elif unidad == "h":
            total += cantidad * 3600
        elif unidad == "d":
            total += cantidad * 86400

    return total


# ============================
# BOTÓN DE PARTICIPAR
# ============================

class JoinButton(discord.ui.Button):
    def __init__(self, giveaway_id):
        super().__init__(label="🎉 Participar", style=discord.ButtonStyle.green)
        self.giveaway_id = giveaway_id

    async def callback(self, interaction: discord.Interaction):
        data = load_giveaways()

        if self.giveaway_id not in data:
            return await interaction.response.send_message("❌ Este giveaway ya no existe.", ephemeral=True)

        participantes = data[self.giveaway_id]["participantes"]

        if interaction.user.id in participantes:
            return await interaction.response.send_message("❌ Ya estás participando.", ephemeral=True)

        participantes.append(interaction.user.id)
        save_giveaways(data)

        await interaction.response.send_message("🎉 ¡Estás participando!", ephemeral=True)


class JoinView(discord.ui.View):
    def __init__(self, giveaway_id):
        super().__init__(timeout=None)
        self.add_item(JoinButton(giveaway_id))


# ============================
# COG PRINCIPAL
# ============================

class GiveawayCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_giveaways.start()

        data = load_giveaways()
        for g_id in data:
            bot.add_view(JoinView(g_id))

    # ============================
    # COMANDO PARA CREAR GIVEAWAY
    # ============================

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(
        name="gstart",
        description="Crear un giveaway"
    )
    @app_commands.describe(
        titulo="Título del giveaway",
        descripcion="Descripción del giveaway",
        tiempo="Duración (ej: 10s, 5m, 2h, 1d)",
        premio="Premio del giveaway",
        ganadores="Cantidad de ganadores",
        imagen_url="URL de la imagen (opcional)",
        imagen_archivo="Adjunta una imagen (opcional)"
    )
    async def gstart(
        self,
        interaction: discord.Interaction,
        titulo: str,
        descripcion: str,
        tiempo: str,
        premio: str,
        ganadores: int,
        imagen_url: str = None,
        imagen_archivo: discord.Attachment = None
    ):

        segundos = parse_time(tiempo)
        if not segundos:
            return await interaction.response.send_message("❌ Tiempo inválido.", ephemeral=True)

        fin = datetime.utcnow() + timedelta(seconds=segundos)

        giveaway_id = str(random.randint(100000, 999999))

        data = load_giveaways()
        data[giveaway_id] = {
            "canal": interaction.channel.id,
            "premio": premio,
            "fin": fin.timestamp(),
            "ganadores": ganadores,
            "participantes": [],
            "mensaje_id": None,
            "imagen": None
        }

        # Imagen por URL
        if imagen_url:
            data[giveaway_id]["imagen"] = imagen_url

        # Imagen adjunta
        if imagen_archivo:
            data[giveaway_id]["imagen"] = imagen_archivo.url

        save_giveaways(data)

        embed = discord.Embed(
            title=titulo,
            description=f"{descripcion}\n\n**Premio:** {premio}\n**Ganadores:** {ganadores}\n**Termina en:** {tiempo}",
            color=discord.Color.random()
        )

        if data[giveaway_id]["imagen"]:
            embed.set_image(url=data[giveaway_id]["imagen"])

        view = JoinView(giveaway_id)
        msg = await interaction.channel.send(embed=embed, view=view)

        data[giveaway_id]["mensaje_id"] = msg.id
        save_giveaways(data)

        await interaction.response.send_message("🎉 Giveaway creado.", ephemeral=True)

    # ============================
    # CHECK AUTOMÁTICO
    # ============================

    @tasks.loop(seconds=5)
    async def check_giveaways(self):
        data = load_giveaways()
        ahora = datetime.utcnow().timestamp()

        for g_id, info in list(data.items()):
            if ahora >= info["fin"]:
                canal = self.bot.get_channel(info["canal"])
                if not canal:
                    del data[g_id]
                    save_giveaways(data)
                    continue

                participantes = info["participantes"]

                if not participantes:
                    await canal.send("❌ Nadie participó en el giveaway.")
                    del data[g_id]
                    save_giveaways(data)
                    continue

                ganadores = min(info["ganadores"], len(participantes))
                seleccionados = random.sample(participantes, ganadores)

                texto = "🎉 **Ganadores del giveaway:**\n"
                for uid in seleccionados:
                    user = canal.guild.get_member(uid)
                    texto += f"• {user.mention}\n"

                texto += f"\n**Premio:** {info['premio']}"

                await canal.send(texto)

                del data[g_id]
                save_giveaways(data)

    # ============================
    # REROLL
    # ============================

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(
        name="greroll",
        description="Hacer reroll de un giveaway terminado"
    )
    @app_commands.describe(
        participantes="Lista de IDs separados por coma"
    )
    async def greroll(self, interaction: discord.Interaction, participantes: str):

        ids = [int(x.strip()) for x in participantes.split(",")]

        if not ids:
            return await interaction.response.send_message("❌ Lista inválida.", ephemeral=True)

        ganador_id = random.choice(ids)
        ganador = interaction.guild.get_member(ganador_id)

        await interaction.response.send_message(f"🔄 Nuevo ganador: {ganador.mention}")


async def setup(bot):
    await bot.add_cog(GiveawayCog(bot))
