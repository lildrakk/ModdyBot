import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import aiohttp
import io

WELCOME_FILE = "welcome.json"

# ============================
# JSON
# ============================

def load_welcome():
    if not os.path.exists(WELCOME_FILE):
        with open(WELCOME_FILE, "w") as f:
            json.dump({}, f, indent=4)

    with open(WELCOME_FILE, "r") as f:
        return json.load(f)

def save_welcome(data):
    with open(WELCOME_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ============================
# COG PRINCIPAL
# ============================

class WelcomeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ============================
    # /welcome estado
    # ============================

    @app_commands.command(name="welcome_estado", description="Activa o desactiva la bienvenida")
    async def welcome_estado(self, interaction: discord.Interaction, estado: str):

        estado = estado.lower()
        if estado not in ["activar", "desactivar"]:
            return await interaction.response.send_message("Usa: activar / desactivar", ephemeral=True)

        data = load_welcome()
        gid = str(interaction.guild.id)

        if gid not in data:
            data[gid] = {
                "enabled": False,
                "canal": None,
                "mensaje": "Bienvenido {user} a {server}!",
                "imagen": None
            }

        data[gid]["enabled"] = (estado == "activar")
        save_welcome(data)

        await interaction.response.send_message(
            f"🎉 Bienvenida **{estado.upper()}**.",
            ephemeral=True
        )

    # ============================
    # /welcome canal
    # ============================

    @app_commands.command(name="welcome_canal", description="Establece el canal de bienvenida")
    async def welcome_canal(self, interaction: discord.Interaction, canal: discord.TextChannel):

        data = load_welcome()
        gid = str(interaction.guild.id)

        if gid not in data:
            data[gid] = {
                "enabled": False,
                "canal": None,
                "mensaje": "Bienvenido {user} a {server}!",
                "imagen": None
            }

        data[gid]["canal"] = canal.id
        save_welcome(data)

        await interaction.response.send_message(
            f"📌 Canal de bienvenida establecido en {canal.mention}",
            ephemeral=True
        )

    # ============================
    # /welcome mensaje
    # ============================

    @app_commands.command(name="welcome_mensaje", description="Cambia el mensaje de bienvenida")
    async def welcome_mensaje(self, interaction: discord.Interaction, *, mensaje: str):

        data = load_welcome()
        gid = str(interaction.guild.id)

        if gid not in data:
            data[gid] = {
                "enabled": False,
                "canal": None,
                "mensaje": "Bienvenido {user} a {server}!",
                "imagen": None
            }

        data[gid]["mensaje"] = mensaje
        save_welcome(data)

        await interaction.response.send_message(
            "📝 Mensaje de bienvenida actualizado.",
            ephemeral=True
        )

    # ============================
    # /welcome imagen (opcional)
    # ============================

    @app_commands.command(name="welcome_imagen", description="Establece o quita la imagen de bienvenida")
    async def welcome_imagen(self, interaction: discord.Interaction, url: str = None):

        data = load_welcome()
        gid = str(interaction.guild.id)

        if gid not in data:
            data[gid] = {
                "enabled": False,
                "canal": None,
                "mensaje": "Bienvenido {user} a {server}!",
                "imagen": None
            }

        data[gid]["imagen"] = url
        save_welcome(data)

        if url:
            msg = "🖼️ Imagen establecida correctamente."
        else:
            msg = "🗑️ Imagen eliminada."

        await interaction.response.send_message(msg, ephemeral=True)

    # ============================
    # EVENTO REAL
    # ============================

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):

        data = load_welcome()
        gid = str(member.guild.id)

        if gid not in data:
            return

        cfg = data[gid]

        if not cfg["enabled"] or not cfg["canal"]:
            return

        canal = member.guild.get_channel(cfg["canal"])
        if not canal:
            return

        mensaje = cfg["mensaje"]
        mensaje = mensaje.replace("{user}", member.mention)
        mensaje = mensaje.replace("{server}", member.guild.name)
        mensaje = mensaje.replace("{membercount}", str(member.guild.member_count))

        # Imagen opcional
        if cfg["imagen"]:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(cfg["imagen"]) as resp:
                        img = await resp.read()
                        file = discord.File(io.BytesIO(img), filename="welcome.png")
                        await canal.send(mensaje, file=file)
            except:
                await canal.send(mensaje)
        else:
            await canal.send(mensaje)


# ============================
# SETUP
# ============================

async def setup(bot):
    await bot.add_cog(WelcomeCog(bot)) 
