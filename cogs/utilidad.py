import discord
from discord.ext import commands
from discord import app_commands


class Utilidad(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ============================
    # SAY
    # ============================

    @app_commands.command(name="say", description="El bot repite un mensaje")
    @app_commands.describe(mensaje="El mensaje que quieres que el bot diga")
    async def say(self, interaction: discord.Interaction, mensaje: str):

        # Evitar abusos como @everyone o @here
        mensaje_filtrado = mensaje.replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere")

        await interaction.response.send_message("📢 Mensaje enviado.", ephemeral=True)
        await interaction.channel.send(mensaje_filtrado)

    # ============================
    # SPOILER
    # ============================

    @app_commands.command(name="spoiler", description="Envuelve un texto en spoiler")
    @app_commands.describe(texto="El texto que quieres ocultar")
    async def spoiler(self, interaction: discord.Interaction, texto: str):

        texto_filtrado = texto.replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere")

        await interaction.response.send_message(f"||{texto_filtrado}||")


async def setup(bot):
    await bot.add_cog(Utilidad(bot))
