import discord
from discord.ext import commands
from discord import app_commands
import json
import os


DM_FILE = "dm.json"


# ============================
# JSON LOADER
# ============================

def load_dm():
    if not os.path.exists(DM_FILE):
        data = {"servers": {}}
        with open(DM_FILE, "w") as f:
            json.dump(data, f, indent=4)
        return data

    with open(DM_FILE, "r") as f:
        data = json.load(f)
        if "servers" not in data:
            data["servers"] = {}
        return data


def save_dm(data):
    with open(DM_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ============================
# COG DE BIENVENIDA POR DM
# ============================

class WelcomeDMCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dm_config = load_dm()


    # ============================
    # COMANDO /dmwelcome
    # ============================

    @app_commands.command(
        name="dmwelcome",
        description="Activa o desactiva la bienvenida por DM"
    )
    @app_commands.describe(
        estado="Escribe 'on' o 'off'"
    )
    async def dmwelcome(
        self,
        interaction: discord.Interaction,
        estado: str
    ):

        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(
                "❌ No tienes permisos.",
                ephemeral=True
            )

        estado = estado.lower()
        if estado not in ["on", "off"]:
            return await interaction.response.send_message(
                "❌ Usa: on / off",
                ephemeral=True
            )

        guild_id = str(interaction.guild.id)

        if guild_id not in self.dm_config["servers"]:
            self.dm_config["servers"][guild_id] = {}

        self.dm_config["servers"][guild_id]["enabled"] = (estado == "on")
        save_dm(self.dm_config)

        await interaction.response.send_message(
            f"✅ Bienvenida por DM **{estado.upper()}**.",
            ephemeral=True
        )


# ============================
    # EVENTO: on_member_join
    # ============================

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):

        guild_id = str(member.guild.id)

        # Si el servidor no tiene configuración, no hacemos nada
        if guild_id not in self.dm_config["servers"]:
            return

        server_cfg = self.dm_config["servers"][guild_id]

        # Si la bienvenida DM no está activada, no hacemos nada
        if not server_cfg.get("enabled", False):
            return

        # Mensaje DM por defecto
        mensaje_dm = f"""
👋 **Hola {member.name}**, bienvenido a **{member.guild.name}**.

Actualmente somos **{member.guild.member_count} miembros** en esta comunidad.

Gracias por unirte a un servidor que utiliza nuestro sistema de seguridad.  
Disfruta tu estancia y recuerda seguir las normas del servidor.📋

**📌 Servidor de soporte**
https://discord.gg/u8W4jv7NXx

🤖 **Invita a ModdyBot**
https://discord.com/oauth2/authorize?client_id=1450924184606740642&permissions=8&integration_type=0&scope=bot

✨ ¡Nos alegra tenerte aquí!
"""

        # Si el servidor tiene un mensaje personalizado, lo usamos
        if "mensaje" in server_cfg:
            mensaje_dm = server_cfg["mensaje"]
            mensaje_dm = mensaje_dm.replace("{user}", member.name)
            mensaje_dm = mensaje_dm.replace("{server}", member.guild.name)

        # Enviar DM
        try:
            await member.send(mensaje_dm)
        except:
            pass


# ============================
# SETUP DEL COG
# ============================

async def setup(bot):
    await bot.add_cog(WelcomeDMCog(bot))