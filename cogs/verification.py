import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import random
import string
from PIL import Image, ImageDraw, ImageFont
import io

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
# GENERADOR CAPTCHA
# ============================

def generar_captcha():
    letras = string.ascii_letters  # mayúsculas y minúsculas
    codigo = ''.join(random.choice(letras) for _ in range(6))

    img = Image.new("RGB", (300, 120), "white")
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 48)
    except:
        font = ImageFont.load_default()

    draw.text((40, 30), codigo, font=font, fill="black")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return codigo, buffer


# ============================
# BOTÓN PERSISTENTE
# ============================

class VerifyButtonItem(discord.ui.Button):
    def __init__(self, panel_id, label):
        super().__init__(
            label=label,
            emoji="🔐",
            style=discord.ButtonStyle.primary,
            custom_id=f"verify_{panel_id}"
        )
        self.panel_id = panel_id

    async def callback(self, interaction: discord.Interaction):
        pass  # lo maneja on_interaction


class VerifyButton(discord.ui.View):
    def __init__(self, panel_id, label):
        super().__init__(timeout=None)
        self.add_item(VerifyButtonItem(panel_id, label))


# ============================
# MODAL CAPTCHA
# ============================

class CaptchaModal(discord.ui.Modal, title="Verificación con Captcha"):
    def __init__(self, codigo_correcto, rol_dar, rol_quitar):
        super().__init__()
        self.codigo_correcto = codigo_correcto
        self.rol_dar = rol_dar
        self.rol_quitar = rol_quitar

        self.input = discord.ui.TextInput(
            label="Introduce el código del captcha",
            placeholder="Escribe exactamente lo que ves en la imagen",
            required=True
        )
        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        if self.input.value == self.codigo_correcto:
            try:
                await interaction.user.remove_roles(self.rol_quitar)
                await interaction.user.add_roles(self.rol_dar)
                await interaction.response.send_message("✅ Verificación completada.", ephemeral=True)
            except:
                await interaction.response.send_message("❌ No pude asignar los roles.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Código incorrecto.", ephemeral=True)


# ============================
# COG PRINCIPAL
# ============================

class VerificationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.captcha_temp = {}  # user_id: codigo

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
        texto_boton="Texto del botón",
        texto_captcha="Texto que aparecerá encima del captcha"
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
        texto_boton: str = "Verificar",
        texto_captcha: str = "Verifícate por seguridad del servidor"
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
            "boton": texto_boton,
            "captcha_texto": texto_captcha
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

        # ============================
        # MOSTRAR OPCIONES AL USUARIO
        # ============================

        opciones = discord.ui.Select(
            placeholder="Elige método de verificación",
            options=[
                discord.SelectOption(label="Normal", value="normal"),
                discord.SelectOption(label="Captcha", value="captcha")
            ]
        )

        async def opciones_callback(select_interaction: discord.Interaction):
            metodo = opciones.values[0]

            if metodo == "normal":
                try:
                    await select_interaction.user.remove_roles(rol_quitar)
                    await select_interaction.user.add_roles(rol_dar)
                    await select_interaction.response.send_message("✅ Verificación completada.", ephemeral=True)
                except:
                    await select_interaction.response.send_message("❌ No pude asignar los roles.", ephemeral=True)

            else:
                codigo, imagen = generar_captcha()
                self.captcha_temp[select_interaction.user.id] = codigo

                embed = discord.Embed(
                    title="🔐 Verificación con Captcha",
                    description=cfg["captcha_texto"],
                    color=discord.Color.blue()
                )
                file = discord.File(imagen, filename="captcha.png")
                embed.set_image(url="attachment://captcha.png")

                await select_interaction.response.send_message(
                    embed=embed,
                    file=file,
                    ephemeral=True
                )

                await select_interaction.followup.send_modal(
                    CaptchaModal(codigo, rol_dar, rol_quitar)
                )

        opciones.callback = opciones_callback

        view = discord.ui.View()
        view.add_item(opciones)

        await interaction.response.send_message(
            "Selecciona un método de verificación:",
            view=view,
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(VerificationCog(bot))
