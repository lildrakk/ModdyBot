import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import random
import string
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import math

VERIFICATION_FILE = "verification.json"

# ============================
# JSON
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
# CAPTCHA MEJORADO PRO
# ============================

def generar_captcha():
    letras = string.ascii_letters + string.digits
    codigo = ''.join(random.choice(letras) for _ in range(6))

    width, height = 420, 160
    img = Image.new("RGB", (width, height))

    # Fondo degradado
    base_color = random.randint(40, 80)
    for y in range(height):
        for x in range(width):
            img.putpixel((x, y), (
                base_color + random.randint(-10, 10),
                base_color + random.randint(-10, 10),
                base_color + random.randint(-10, 10)
            ))

    draw = ImageDraw.Draw(img)

    # Líneas curvas
    for _ in range(4):
        points = []
        for i in range(6):
            points.append((random.randint(0, width), random.randint(0, height)))
        draw.line(points, fill=(random.randint(100, 200), random.randint(100, 200), random.randint(100, 200)), width=3)

    # Fuente
    try:
        font = ImageFont.truetype("arial.ttf", 60)
    except:
        font = ImageFont.load_default()

    # Dibujar cada letra con rotación
    x_offset = 40
    for char in codigo:
        angle = random.randint(-25, 25)

        # Crear imagen temporal para rotar
        temp = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
        temp_draw = ImageDraw.Draw(temp)

        bbox = temp_draw.textbbox((0, 0), char, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]

        temp_draw.text((50 - w//2, 50 - h//2), char, font=font, fill=(255, 255, 255))

        rotated = temp.rotate(angle, expand=1)

        img.paste(rotated, (x_offset, (height // 2) - 40), rotated)
        x_offset += 55

    # Ruido
    for _ in range(350):
        px = random.randint(0, width - 1)
        py = random.randint(0, height - 1)
        img.putpixel((px, py), (
            random.randint(150, 255),
            random.randint(150, 255),
            random.randint(150, 255)
        ))

    # Suavizado ligero
    img = img.filter(ImageFilter.SMOOTH_MORE)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return codigo, buffer

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
            placeholder="Escribe exactamente lo que ves",
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
# BOTÓN DE VERIFICACIÓN
# ============================

class VerifyButtonItem(discord.ui.Button):
    def __init__(self, panel_id, label):
        super().__init__(
            label=label,
            emoji="🔐",
            style=discord.ButtonStyle.success,
            custom_id=f"verify_{panel_id}"
        )
        self.panel_id = panel_id

    async def callback(self, interaction: discord.Interaction):
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

        data = load_verification()
        for guild_id in data:
            for panel_id, cfg in data[guild_id].items():
                label = cfg.get("boton", "Verificar")
                bot.add_view(VerifyButton(panel_id, label))

    # ============================
    # CREAR PANEL
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
        tipo="normal o captcha",
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
        texto_boton: str,
        tipo: str,
        texto_captcha: str = "Verifícate por seguridad del servidor"
    ):

        if tipo not in ["normal", "captcha"]:
            return await interaction.response.send_message("❌ Tipo inválido. Usa: normal o captcha", ephemeral=True)

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
            "tipo": tipo,
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
    # ENVIAR PANEL EXISTENTE
    # ============================

    @app_commands.command(
        name="verificacion_enviar",
        description="Enviar un panel de verificación ya existente"
    )
    async def verificacion_enviar(
        self,
        interaction: discord.Interaction,
        panel_id: str,
        canal: discord.TextChannel
    ):

        guild_id = str(interaction.guild.id)
        data = load_verification()

        if guild_id not in data or panel_id not in data[guild_id]:
            return await interaction.response.send_message("❌ Ese panel no existe.", ephemeral=True)

        cfg = data[guild_id][panel_id]

        embed = discord.Embed(
            title=cfg["titulo"],
            description=cfg["descripcion"],
            color=discord.Color.green()
        )

        boton = cfg.get("boton", "Verificar")
        view = VerifyButton(panel_id, boton)

        await canal.send(embed=embed, view=view)
        await interaction.response.send_message("✅ Panel enviado correctamente.", ephemeral=True)

    # ============================
    # INTERACCIÓN DEL BOTÓN
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
            return await interaction.response.send_message("❌ Panel no encontrado.", ephemeral=True)

        cfg = data[guild_id][panel_id]

        rol_dar = interaction.guild.get_role(cfg["rol_dar"])
        rol_quitar = interaction.guild.get_role(cfg["rol_quitar"])
        tipo = cfg["tipo"]

        # Ya verificado
        if rol_dar in interaction.user.roles:
            return await interaction.response.send_message("✅ Ya estás verificado.", ephemeral=True)

        # Verificación normal
        if tipo == "normal":
            try:
                await interaction.user.remove_roles(rol_quitar)
                await interaction.user.add_roles(rol_dar)
                return await interaction.response.send_message("✅ Verificación completada.", ephemeral=True)
            except:
                return await interaction.response.send_message("❌ No pude asignar los roles.", ephemeral=True)

        # Verificación con CAPTCHA
        codigo, imagen = generar_captcha()

        embed = discord.Embed(
            title="🔐 Verificación con Captcha",
            description=cfg["captcha_texto"],
            color=discord.Color.blue()
        )

        file = discord.File(imagen, filename="captcha.png")
        embed.set_image(url="attachment://captcha.png")

        select = discord.ui.Select(
            placeholder="Selecciona una opción",
            options=[discord.SelectOption(label="Responder", value="responder")]
        )

        async def select_callback(select_interaction: discord.Interaction):
            if select_interaction.user.id != interaction.user.id:
                return await select_interaction.response.send_message("❌ No puedes usar este menú.", ephemeral=True)

            responder_btn = discord.ui.Button(
                label="Responder",
                style=discord.ButtonStyle.primary
            )

            async def responder_callback(btn_interaction: discord.Interaction):
                if btn_interaction.user.id != interaction.user.id:
                    return await btn_interaction.response.send_message("❌ No puedes usar este botón.", ephemeral=True)

                await btn_interaction.response.send_modal(
                    CaptchaModal(codigo, rol_dar, rol_quitar)
                )

            responder_btn.callback = responder_callback

            view2 = discord.ui.View()
            view2.add_item(responder_btn)

            await select_interaction.response.send_message(
                "Pulsa **Responder** para escribir el código:",
                view=view2,
                ephemeral=True
            )

        select.callback = select_callback

        view = discord.ui.View()
        view.add_item(select)

        await interaction.response.send_message(
            embed=embed,
            file=file,
            view=view,
            ephemeral=True
        )

# ============================
# SETUP
# ============================

async def setup(bot):
    await bot.add_cog(VerificationCog(bot))
