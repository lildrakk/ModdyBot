import discord
from discord.ext import commands
from discord import app_commands

COLOR_DEFAULT = discord.Color(0x0A3D62)

# ============================
# MODAL PARA CREAR EMBED (4 CAMPOS)
# ============================

class EmbedCreator(discord.ui.Modal, title="Crear un embed personalizado"):
    titulo = discord.ui.TextInput(
        label="Título",
        placeholder="Escribe un título claro y llamativo",
        required=False,
        max_length=256
    )

    descripcion = discord.ui.TextInput(
        label="Descripción",
        placeholder="Contenido principal del embed",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=4000
    )

    color = discord.ui.TextInput(
        label="Color (HEX opcional)",
        placeholder="Ejemplo: #0A3D62 — déjalo vacío para usar el color por defecto",
        required=False,
        max_length=7
    )

    footer = discord.ui.TextInput(
        label="Pie de página (opcional)",
        placeholder="Texto pequeño al final del embed",
        required=False,
        max_length=256
    )

    async def on_submit(self, interaction: discord.Interaction):

        # Color
        if self.color.value:
            try:
                color = discord.Color(int(self.color.value.replace("#", ""), 16))
            except:
                color = COLOR_DEFAULT
        else:
            color = COLOR_DEFAULT

        embed = discord.Embed(
            title=self.titulo.value if self.titulo.value else None,
            description=self.descripcion.value,
            color=color
        )

        if self.footer.value:
            embed.set_footer(text=self.footer.value)

        await interaction.response.send_message(embed=embed)

# ============================
# COG PRINCIPAL
# ============================

class EmbedCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="embed",
        description="Crea un embed personalizado con un formulario sencillo."
    )
    async def embed(self, interaction: discord.Interaction):
        modal = EmbedCreator()
        await interaction.response.send_modal(modal)

# ============================
# SETUP
# ============================

async def setup(bot):
    await bot.add_cog(EmbedCommand(bot))
