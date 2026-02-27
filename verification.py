import discord
from discord.ext import commands
from discord import app_commands
import json
import os

VERIFICATION_FILE = "verification.json"


# ============================
# JSON LOADER
# ============================

def load_verification():
    if not os.path.exists(VERIFICATION_FILE):
        with open(VERIFICATION_FILE, "w") as f:
            json.dump({}, f, indent=4)
    with open(VERIFICATION_FILE, "r") as f:
        return json.load(f)


def save_verification(data):
    with open(VERIFICATION_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ============================
# BOTÓN PERSISTENTE
# ============================

class VerifyButtonItem(discord.ui.Button):
    def __init__(self, panel_id, label):
        super().__init__(
            label=label,
            emoji="✅",
            style=discord.ButtonStyle.success,
            custom_id=f"verify_{panel_id}"
        )
        self.panel_id = panel_id

    async def callback(self, interaction: discord.Interaction):
        # NO responder aquí
        # on_interaction maneja todo
        pass


class VerifyButton(discord.ui.View):
    def __init__(self, panel_id, label):
        super().__init__(timeout=None)
        self.add_item(VerifyButtonItem(panel_id, label))


# ============================
# COG PRINCIPAL
# ============================

class VerificationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Registrar botones persistentes al iniciar
        data = load_verification()
        for guild_id in data:
            for panel_id, cfg in data[guild_id].items():
                label = cfg.get("boton", "Verificar")
                bot.add_view(VerifyButton(panel_id, label))

    # ============================
    # COMANDO PARA CREAR PANEL
    # ============================

    @app_commands.command(
        name="verificacion_crear",
        description="Crear un panel de verificación"
    )
    @app_commands.describe(
        panel_id="ID del panel",
        canal="Canal donde se enviará el panel",
        titulo="Título del embed",
        descripcion="Descripción del embed",
        rol_dar="Rol que se dará al verificar",
        rol_quitar="Rol que se quitará al verificar",
        texto_boton="Texto que aparecerá en el botón"
    )
    async def verificacion_crear(
        self,
        interaction: discord.Interaction,
        panel_id: str,
        canal: discord.TextChannel,
        titulo: str,
        descripcion: str,
        rol_dar: discord.Role,
        rol_quitar: discord.Role,
        texto_boton: str = "Verificar"
    ):

        guild_id = str(interaction.guild.id)
        data = load_verification()

        if guild_id not in data:
            data[guild_id] = {}

        data[guild_id][panel_id] = {
            "rol_dar": rol_dar.id,
            "rol_quitar": rol_quitar.id,
            "titulo": titulo,
            "descripcion": descripcion,
            "boton": texto_boton
        }

        save_verification(data)

        embed = discord.Embed(
            title=titulo,
            description=descripcion,
            color=discord.Color.green()
        )

        view = VerifyButton(panel_id, texto_boton)

        await canal.send(embed=embed, view=view)
        await interaction.response.send_message("✅ Panel creado.", ephemeral=True)

    # ============================
    # ON INTERACTION
    # ============================

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):

        if not interaction.data:
            return

        custom = interaction.data.get("custom_id", "")
        if not custom.startswith("verify_"):
            return

        panel_id = custom.split("_", 1)[1]
        guild_id = str(interaction.guild.id)

        data = load_verification()

        if guild_id not in data or panel_id not in data[guild_id]:
            return await interaction.response.send_message(
                "❌ Panel no encontrado.", ephemeral=True)

        cfg = data[guild_id][panel_id]

        rol_dar = interaction.guild.get_role(cfg["rol_dar"])
        rol_quitar = interaction.guild.get_role(cfg["rol_quitar"])

        if rol_dar is None:
            return await interaction.response.send_message(
                "❌ El rol que debo dar ya no existe.", ephemeral=True)

        if rol_quitar is None:
            return await interaction.response.send_message(
                "❌ El rol que debo quitar ya no existe.", ephemeral=True)

        if rol_dar in interaction.user.roles:
            return await interaction.response.send_message(
                "✅ Ya estás verificado.", ephemeral=True)

        try:
            await interaction.user.remove_roles(rol_quitar, reason="Verificación")
        except:
            return await interaction.response.send_message(
                "❌ No pude quitar el rol.", ephemeral=True)

        try:
            await interaction.user.add_roles(rol_dar, reason="Verificación")
        except:
            return await interaction.response.send_message(
                "❌ No pude asignar el rol.", ephemeral=True)

        return await interaction.response.send_message(
            "✅ Verificación completada.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(VerificationCog(bot))