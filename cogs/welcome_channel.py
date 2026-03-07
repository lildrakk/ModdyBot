import discord
from discord.ext import commands
from discord import app_commands
import json
import os


WELCOME_FILE = "welcome.json"


# ============================
# JSON LOADER
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
# COG DE BIENVENIDA
# ============================

class WelcomeChannelCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.welcome_config = load_welcome()

    # ============================
    # COMANDO /setwelcome
    # ============================

    @app_commands.command(
        name="setwelcome",
        description="Configura la bienvenida del servidor"
    )
    @app_commands.describe(
        canal="Canal donde se enviará la bienvenida",
        mensaje="Mensaje de bienvenida (usa {user} y {server})",
        imagen_url="URL de la imagen de bienvenida",
        imagen_archivo="Adjunta una imagen de bienvenida"
    )
    async def setwelcome(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel = None,
        mensaje: str = None,
        imagen_url: str = None,
        imagen_archivo: discord.Attachment = None
    ):

        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(
                "❌ No tienes permisos para usar este comando.",
                ephemeral=True
            )

        # Recargar JSON siempre
        self.welcome_config = load_welcome()

        guild_id = str(interaction.guild.id)

        if guild_id not in self.welcome_config:
            self.welcome_config[guild_id] = {}

        # Canal
        if canal:
            self.welcome_config[guild_id]["welcome_channel"] = str(canal.id)

        # Mensaje
        if mensaje:
            self.welcome_config[guild_id]["welcome_message"] = mensaje

        # Imagen por URL
        if imagen_url:
            self.welcome_config[guild_id]["welcome_image"] = imagen_url

        # Imagen adjunta
        if imagen_archivo:
            self.welcome_config[guild_id]["welcome_image"] = imagen_archivo.url

        save_welcome(self.welcome_config)

        await interaction.response.send_message(
            "✅ Configuración de bienvenida actualizada.",
            ephemeral=True
        )

    # ============================
    # EVENTO: on_member_join
    # ============================

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):

        # Recargar JSON SIEMPRE
        self.welcome_config = load_welcome()

        guild_id = str(member.guild.id)

        if guild_id not in self.welcome_config:
            return

        config = self.welcome_config[guild_id]

        canal_id = config.get("welcome_channel")
        if not canal_id:
            return

        canal = member.guild.get_channel(int(canal_id))
        if not canal:
            return

        mensaje = config.get(
            "welcome_message",
            "🎉 Bienvenido {user} a **{server}**!"
        )

        mensaje = mensaje.replace("{user}", member.mention)
        mensaje = mensaje.replace("{server}", member.guild.name)

        imagen = config.get("welcome_image")

        try:
            if imagen:
                await canal.send(mensaje)
                await canal.send(imagen)
            else:
                await canal.send(mensaje)
        except:
            pass


# ============================
# SETUP DEL COG
# ============================

async def setup(bot):
    await bot.add_cog(WelcomeChannelCog(bot))
