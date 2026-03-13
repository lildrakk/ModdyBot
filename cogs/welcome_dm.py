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
        self.dm_config = load_dm()  # Carga inicial


    # ============================
    # /dmwelcome
    # ============================

    @app_commands.command(
        name="dmwelcome",
        description="Activa o desactiva la bienvenida por DM"
    )
    async def dmwelcome(self, interaction: discord.Interaction, estado: str):

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

        # Recargar JSON SIEMPRE
        self.dm_config = load_dm()

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
    # /dmprueba
    # ============================

    @app_commands.command(
    name="dmprueba",
    description="Prueba el mensaje de bienvenida por DM."
)
async def dmprueba(self, interaction: discord.Interaction):

    guild = interaction.guild
    user = interaction.user

    descripcion = (
        f"👋 **Hola {user.name}**, bienvenido a **{guild.name}**.\n\n"
        f"Actualmente somos **{guild.member_count} miembros** en esta comunidad.\n\n"
        "Gracias por unirte a un servidor que utiliza nuestro sistema de seguridad.\n"
        "Disfruta tu estancia y recuerda seguir las normas del servidor. 📋\n\n"

        "🤖 **Sobre ModdyBot**\n"
        "ModdyBot es un sistema avanzado de seguridad y gestión diseñado para mantener los servidores protegidos, organizados y funcionando sin problemas.\n"
        "Incluye herramientas automáticas de moderación, protección contra raids y utilidades para la administración diaria.\n\n"

        "🛠️ **Soporte de ModdyBot**\n"
        "Si necesitas ayuda, soporte técnico o tienes dudas sobre las funciones del bot, puedes acceder a nuestro servidor oficial de soporte.\n"
        "[Entrar al soporte](https://discord.gg/u8W4jv7NXx)\n\n"

        "✨ **Añade ModdyBot a tu servidor**\n"
        "¿Quieres utilizar ModdyBot en tu propio servidor? Puedes invitarlo desde el siguiente enlace:\n"
        "[Invitar ModdyBot](https://discord.com/oauth2/authorize?client_id=1450924184606740642&permissions=8&integration_type=0&scope=bot)\n\n"

        "¡Nos alegra tenerte aquí!"
    )

    embed = discord.Embed(
        description=descripcion,
        color=discord.Color.blue()
    )

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    try:
        await user.send(embed=embed)
        await interaction.response.send_message(
            "📨 Te envié el mensaje de bienvenida por DM.",
            ephemeral=True
        )
    except:
        await interaction.response.send_message(
            "❌ No pude enviarte el DM. Puede que tengas los mensajes privados desactivados.",
            ephemeral=True
        ) 


    # ============================
    # Evento real: on_member_join
    # ============================

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):

        # Recargar JSON SIEMPRE
        self.dm_config = load_dm()

        guild_id = str(member.guild.id)

        if guild_id not in self.dm_config["servers"]:
            return

        server_cfg = self.dm_config["servers"][guild_id]

        if not server_cfg.get("enabled", False):
            return

        descripcion = (
            f"👋 **Hola {member.name}**, bienvenido a **{member.guild.name}**.\n\n"
f"Actualmente somos **{member.guild.member_count} miembros** en esta comunidad.\n\n"
"Gracias por unirte a un servidor que utiliza nuestro sistema de seguridad.\n"
"Disfruta tu estancia y recuerda seguir las normas del servidor. 📋\n\n"

"🤖 **Sobre ModdyBot**\n"
"ModdyBot es un sistema avanzado de seguridad y gestión diseñado para mantener los servidores protegidos, organizados y funcionando sin problemas.\n"
"Cuenta con herramientas automáticas de moderación, protección contra raids y funciones útiles para la administración diaria.\n\n"

"🛠️ **Soporte de ModdyBot**\n"
"Si necesitas ayuda, tienes dudas o quieres aprender más sobre las funciones del bot, puedes acceder a nuestro servidor oficial de soporte.\n"
"[Entrar al soporte](https://discord.gg/u8W4jv7NXx)\n\n"

"✨ **Añade ModdyBot a tu servidor**\n"
"¿Quieres utilizar ModdyBot en tu propio servidor? Puedes invitarlo desde el siguiente enlace:\n"
"[Invitar ModdyBot](https://discord.com/oauth2/authorize?client_id=1450924184606740642&permissions=8&integration_type=0&scope=bot)\n\n"

"¡Nos alegra tenerte aquí!"
        )

        embed = discord.Embed(
            description=descripcion,
            color=discord.Color.blue()
        )

        if member.guild.icon:
            embed.set_thumbnail(url=member.guild.icon.url)

        try:
            await member.send(embed=embed)
        except:
            pass


async def setup(bot):
    await bot.add_cog(WelcomeDMCog(bot))
