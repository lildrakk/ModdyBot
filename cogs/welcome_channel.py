import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import io
import aiohttp

WELCOME_FILE = "welcome.json"

def load_welcome():
    if not os.path.exists(WELCOME_FILE):
        with open(WELCOME_FILE, "w") as f:
            json.dump({}, f, indent=4)

    with open(WELCOME_FILE, "r") as f:
        return json.load(f)

def save_welcome(data):
    with open(WELCOME_FILE, "w") as f:
        json.dump(data, f, indent=4)


class WelcomeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ============================
    # PANEL — PÁGINA 1
    # ============================

    @app_commands.command(name="welcome", description="Abrir panel de bienvenida")
    async def welcome(self, interaction: discord.Interaction):

        guild_id = str(interaction.guild.id)
        data = load_welcome()

        if guild_id not in data:
            data[guild_id] = {
                "enabled": False,
                "canal": None,
                "logs": None,
                "mensaje": "Bienvenido {user} a {server}!",
                "imagen": None
            }
            save_welcome(data)

        cfg = data[guild_id]

        embed = discord.Embed(
            title="🎉 Panel de Bienvenida — Página 1",
            description="Configura el sistema de bienvenida.",
            color=discord.Color.green()
        )

        estado = "🟢 Activado" if cfg["enabled"] else "🔴 Desactivado"
        canal = f"<#{cfg['canal']}>" if cfg["canal"] else "❌ No configurado"
        logs = f"<#{cfg['logs']}>" if cfg["logs"] else "❌ No configurado"

        embed.add_field(name="Estado", value=estado, inline=False)
        embed.add_field(name="Canal", value=canal, inline=False)
        embed.add_field(name="Logs", value=logs, inline=False)

        view = WelcomePage1(self.bot, interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class WelcomePage1(discord.ui.View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=120)
        self.bot = bot
        self.user_id = user_id

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user_id

    @discord.ui.button(label="Activar/Desactivar", style=discord.ButtonStyle.primary)
    async def toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = str(interaction.guild.id)
        data = load_welcome()

        data[guild_id]["enabled"] = not data[guild_id]["enabled"]
        save_welcome(data)

        estado = "🟢 Activado" if data[guild_id]["enabled"] else "🔴 Desactivado"
        await interaction.response.send_message(f"Estado cambiado a: **{estado}**", ephemeral=True)

    @discord.ui.button(label="Cambiar canal", style=discord.ButtonStyle.secondary)
    async def cambiar_canal(self, interaction: discord.Interaction, button: discord.ui.Button):

        class CanalModal(discord.ui.Modal, title="Cambiar canal de bienvenida"):
            canal = discord.ui.TextInput(label="ID del canal")

            async def on_submit(self, modal_interaction: discord.Interaction):
                guild_id = str(modal_interaction.guild.id)
                data = load_welcome()

                try:
                    canal_id = int(self.canal.value)
                    canal = modal_interaction.guild.get_channel(canal_id)
                    if not canal:
                        raise ValueError

                    data[guild_id]["canal"] = canal_id
                    save_welcome(data)

                    await modal_interaction.response.send_message(
                        f"Canal cambiado a <#{canal_id}>",
                        ephemeral=True
                    )
                except:
                    await modal_interaction.response.send_message("❌ Canal inválido.", ephemeral=True)

        await interaction.response.send_modal(CanalModal())

    @discord.ui.button(label="Cambiar logs", style=discord.ButtonStyle.secondary)
    async def cambiar_logs(self, interaction: discord.Interaction, button: discord.ui.Button):

        class LogsModal(discord.ui.Modal, title="Cambiar canal de logs"):
            canal = discord.ui.TextInput(label="ID del canal")

            async def on_submit(self, modal_interaction: discord.Interaction):
                guild_id = str(modal_interaction.guild.id)
                data = load_welcome()

                try:
                    canal_id = int(self.canal.value)
                    canal = modal_interaction.guild.get_channel(canal_id)
                    if not canal:
                        raise ValueError

                    data[guild_id]["logs"] = canal_id
                    save_welcome(data)

                    await modal_interaction.response.send_message(
                        f"Logs cambiados a <#{canal_id}>",
                        ephemeral=True
                    )
                except:
                    await modal_interaction.response.send_message("❌ Canal inválido.", ephemeral=True)

        await interaction.response.send_modal(LogsModal())

    @discord.ui.button(label="Página 2 → Mensaje", style=discord.ButtonStyle.success)
    async def pagina2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Cargando página 2...", ephemeral=True)


# ============================
# PÁGINA 2 — MENSAJE
# ============================

class WelcomePage2(discord.ui.View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=120)
        self.bot = bot
        self.user_id = user_id

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user_id

    @discord.ui.button(label="Cambiar mensaje", style=discord.ButtonStyle.primary)
    async def cambiar_mensaje(self, interaction: discord.Interaction, button: discord.ui.Button):

        class MensajeModal(discord.ui.Modal, title="Cambiar mensaje de bienvenida"):
            mensaje = discord.ui.TextInput(
                label="Mensaje",
                placeholder="Ej: Bienvenido {user} a {server}!",
                style=discord.TextStyle.paragraph
            )

            async def on_submit(self, modal_interaction: discord.Interaction):
                guild_id = str(modal_interaction.guild.id)
                data = load_welcome()

                data[guild_id]["mensaje"] = self.mensaje.value
                save_welcome(data)

                await modal_interaction.response.send_message(
                    "Mensaje actualizado correctamente.",
                    ephemeral=True
                )

        await interaction.response.send_modal(MensajeModal())

    @discord.ui.button(label="Página 3 → Imagen", style=discord.ButtonStyle.success)
    async def pagina3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Cargando página 3...", ephemeral=True)


# ============================
# PÁGINA 3 — IMAGEN
# ============================

class WelcomePage3(discord.ui.View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=120)
        self.bot = bot
        self.user_id = user_id

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user_id

    @discord.ui.button(label="Poner URL", style=discord.ButtonStyle.primary)
    async def poner_url(self, interaction: discord.Interaction, button: discord.ui.Button):

        class URLModal(discord.ui.Modal, title="Poner URL de imagen"):
            url = discord.ui.TextInput(label="URL de la imagen")

            async def on_submit(self, modal_interaction: discord.Interaction):
                guild_id = str(modal_interaction.guild.id)
                data = load_welcome()

                data[guild_id]["imagen"] = self.url.value
                save_welcome(data)

                await modal_interaction.response.send_message(
                    "Imagen actualizada correctamente.",
                    ephemeral=True
                )

        await interaction.response.send_modal(URLModal())

    @discord.ui.button(label="Adjuntar imagen", style=discord.ButtonStyle.secondary)
    async def adjuntar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Adjunta una imagen en tu siguiente mensaje.",
            ephemeral=True
        )

        def check(msg):
            return msg.author.id == interaction.user.id and msg.attachments

        msg = await self.bot.wait_for("message", check=check)
        imagen_url = msg.attachments[0].url

        guild_id = str(interaction.guild.id)
        data = load_welcome()
        data[guild_id]["imagen"] = imagen_url
        save_welcome(data)

        await interaction.followup.send("Imagen guardada correctamente.", ephemeral=True)

    @discord.ui.button(label="Quitar imagen", style=discord.ButtonStyle.danger)
    async def quitar(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = str(interaction.guild.id)
        data = load_welcome()

        data[guild_id]["imagen"] = None
        save_welcome(data)

        await interaction.response.send_message("Imagen eliminada.", ephemeral=True)

    @discord.ui.button(label="Página 4 → Vista previa", style=discord.ButtonStyle.success)
    async def pagina4(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Cargando vista previa...", ephemeral=True)


# ============================
# PÁGINA 4 — VISTA PREVIA
# ============================

class WelcomePage4(discord.ui.View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=120)
        self.bot = bot
        self.user_id = user_id

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user_id

    @discord.ui.button(label="Ver vista previa", style=discord.ButtonStyle.primary)
    async def preview(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = str(interaction.guild.id)
        data = load_welcome()
        cfg = data[guild_id]

        mensaje = cfg["mensaje"]
        mensaje = mensaje.replace("{user}", interaction.user.mention)
        mensaje = mensaje.replace("{server}", interaction.guild.name)
        mensaje = mensaje.replace("{membercount}", str(interaction.guild.member_count))

        if cfg["imagen"]:
            async with aiohttp.ClientSession() as session:
                async with session.get(cfg["imagen"]) as resp:
                    img = await resp.read()
                    file = discord.File(io.BytesIO(img), filename="preview.png")
                    await interaction.response.send_message(mensaje, file=file, ephemeral=True)
        else:
            await interaction.response.send_message(mensaje, ephemeral=True)


# ============================
# EVENTO REAL DE BIENVENIDA
# ============================

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        data = load_welcome()
        guild_id = str(member.guild.id)

        if guild_id not in data:
            return

        cfg = data[guild_id]

        if not cfg["enabled"] or not cfg["canal"]:
            return

        canal = member.guild.get_channel(cfg["canal"])
        if not canal:
            return

        mensaje = cfg["mensaje"]
        mensaje = mensaje.replace("{user}", member.mention)
        mensaje = mensaje.replace("{server}", member.guild.name)
        mensaje = mensaje.replace("{membercount}", str(member.guild.member_count))

        if cfg["imagen"]:
            async with aiohttp.ClientSession() as session:
                async with session.get(cfg["imagen"]) as resp:
                    img = await resp.read()
                    file = discord.File(io.BytesIO(img), filename="welcome.png")
                    await canal.send(mensaje, file=file)
        else:
            await canal.send(mensaje)



# ============================
# SETUP FINAL DEL COG
# ============================

async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeCog(bot))

    # Registrar vistas persistentes
    bot.add_view(WelcomePage1(bot, 0))
    bot.add_view(WelcomePage2(bot, 0))
    bot.add_view(WelcomePage3(bot, 0))
    bot.add_view(WelcomePage4(bot, 0))
