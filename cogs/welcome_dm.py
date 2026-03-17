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
    # /dmwelcome (ACTIVAR / DESACTIVAR)
    # ============================

    @app_commands.command(
        name="dmwelcome",
        description="Activa o desactiva la bienvenida por DM"
    )
    @app_commands.describe(
        estado="activar / desactivar"
    )
    @app_commands.choices(
        estado=[
            app_commands.Choice(name="Activar", value="activar"),
            app_commands.Choice(name="Desactivar", value="desactivar")
        ]
    )
    async def dmwelcome(self, interaction: discord.Interaction, estado: app_commands.Choice[str]):

        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(
                "<:error:1000011241> No tienes permisos para usar este comando.",
                ephemeral=True
            )

        self.dm_config = load_dm()
        guild_id = str(interaction.guild.id)

        if guild_id not in self.dm_config["servers"]:
            self.dm_config["servers"][guild_id] = {}

        activar = (estado.value == "activar")
        self.dm_config["servers"][guild_id]["enabled"] = activar
        save_dm(self.dm_config)

        await interaction.response.send_message(
            f"<:check:1000011237> Bienvenida por DM **{estado.name.upper()}** correctamente.",
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
            f"<:gift:1000008822> **¡Hey {user.name}!**\n"
            f"Te doy la bienvenida a **{guild.name}** ✨\n\n"

            f"<:announce:1000008820> Actualmente somos **{guild.member_count} personas** formando parte de esta comunidad.\n"
            "Es un placer tenerte por aquí, de verdad.\n\n"

            f"<:shield:1000008818> **¿Qué es ModdyBot?**\n"
            "**ModdyBot** es tu compañero de seguridad y organización dentro del servidor.\n"
            "Estoy aquí para ayudarte a tener una experiencia cómoda, segura y sin complicaciones.\n\n"

            f"<:shield:1000008818> **ModdyBot te acompaña**\n"
            "Mi misión es mantener el servidor seguro, organizado y funcionando sin problemas.\n"
            "Si necesitas algo, no dudes en contactar con el staff.\n\n"

            f"<:warning:1000008817> **Consejos para empezar**\n"
            "• Échale un vistazo a las normas del servidor 📜\n"
            "• Respeta a los demás miembros 🤝\n"
            "• Y sobre todo… ¡pásalo bien! 😄\n\n"

            f"<:alert:1000011234> **¿Necesitas ayuda?**\n"
            "Puedes entrar a nuestro servidor oficial de soporte:\n"
            "[🔗 Servidor de soporte](https://discord.gg/u8W4jv7NXx)\n\n"

            "🚀 **¿Quieres usar ModdyBot en tus servidores?**\n"
            "[✨ Invitar ModdyBot](https://discord.com/oauth2/authorize?client_id=1450924184606740642&permissions=8&integration_type=0&scope=bot)\n\n"

            f"<:check:1000011237> **¡Gracias por unirte!**\n"
            "Estoy seguro de que encajarás genial aquí."
        )

        embed = discord.Embed(description=descripcion, color=discord.Color.blue())

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.set_image(url="https://cdn.discordapp.com/attachments/1478441871712849962/1483495094534541312/standard.gif")

        try:
            await user.send(embed=embed)
            await interaction.response.send_message(
                "<:check:1000011237> Te envié el mensaje de bienvenida por DM.",
                ephemeral=True
            )
        except:
            await interaction.response.send_message(
                "<:error:1000011241> No pude enviarte el DM. Puede que tengas los mensajes privados desactivados.",
                ephemeral=True
            )

    # ============================
    # Evento real: on_member_join
    # ============================

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):

        self.dm_config = load_dm()
        guild_id = str(member.guild.id)

        if guild_id not in self.dm_config["servers"]:
            return

        server_cfg = self.dm_config["servers"][guild_id]

        if not server_cfg.get("enabled", False):
            return

        descripcion = (
            f"<:gift:1000008822> **¡Hey {member.name}!**\n"
            f"Te doy la bienvenida a **{member.guild.name}** ✨\n\n"

            f"<:announce:1000008820> Actualmente somos **{member.guild.member_count} personas** formando parte de esta comunidad.\n"
            "Es un placer tenerte por aquí, de verdad.\n\n"

            f"<:shield:1000008818> **¿Qué es ModdyBot?**\n"
            "**ModdyBot** es tu compañero de seguridad y organización dentro del servidor.\n"
            "Estoy aquí para ayudarte a tener una experiencia cómoda, segura y sin complicaciones.\n\n"

            f"<:shield:1000008818> **ModdyBot te acompaña**\n"
            "Mi misión es mantener el servidor seguro, organizado y funcionando sin problemas.\n"
            "Si necesitas algo, no dudes en contactar con el staff.\n\n"

            f"<:warning:1000008817> **Consejos para empezar**\n"
            "• Échale un vistazo a las normas del servidor 📜\n"
            "• Respeta a los demás miembros 🤝\n"
            "• Y sobre todo… ¡pásalo bien! 😄\n\n"

            f"<:alert:1000011234> **¿Necesitas ayuda?**\n"
            "Puedes entrar a nuestro servidor oficial de soporte:\n"
            "[🔗 Servidor de soporte](https://discord.gg/u8W4jv7NXx)\n\n"

            "🚀 **¿Quieres usar ModdyBot en tus servidores?**\n"
            "[✨ Invitar ModdyBot](https://discord.com/oauth2/authorize?client_id=1450924184606740642&permissions=8&integration_type=0&scope=bot)\n\n"

            f"<:check:1000011237> **¡Gracias por unirte!**\n"
            "Estoy seguro de que encajarás genial aquí."
        )

        embed = discord.Embed(description=descripcion, color=discord.Color.blue())

        if member.guild.icon:
            embed.set_thumbnail(url=member.guild.icon.url)

        embed.set_image(url="https://cdn.discordapp.com/attachments/1478441871712849962/1483495094534541312/standard.gif")

        try:
            await member.send(embed=embed)
        except:
            pass


async def setup(bot):
    await bot.add_cog(WelcomeDMCog(bot))
