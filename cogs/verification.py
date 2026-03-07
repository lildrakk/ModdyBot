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
# CAPTCHA LIMPIO
# ============================

def generar_captcha():
    letras = string.ascii_uppercase + string.digits
    codigo = ''.join(random.choice(letras) for _ in range(6))

    width, height = 400, 150
    img = Image.new("RGB", (width, height), (25, 25, 25))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 80)
    except:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), codigo, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = (width - text_width) // 2
    y = (height - text_height) // 2

    draw.text((x, y), codigo, font=font, fill=(255, 255, 255))

    for _ in range(60):
        px = random.randint(0, width - 1)
        py = random.randint(0, height - 1)
        img.putpixel((px, py), (random.randint(150, 255),) * 3)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return codigo, buffer

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
        return  # Se maneja en on_interaction

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
        name="verificacion",
        description="Crear un panel de verificación completo"
    )
    @app_commands.describe(
        panel_id="ID único del panel",
        canal="Canal donde se enviará el panel",
        canal_logs="Canal donde se enviarán los logs de este panel",
        titulo="Título del embed",
        descripcion="Descripción del embed",
        mensaje="Mensaje opcional debajo de la descripción",
        imagen_url="URL opcional de imagen",
        rol_dar="Rol que se dará al verificar",
        rol_quitar="Rol que se quitará al verificar",
        texto_boton="Texto del botón",
        tipo="normal o captcha",
        texto_captcha="Texto que aparecerá encima del captcha"
    )
    async def verificacion(
        self,
        interaction: discord.Interaction,
        panel_id: str,
        canal: discord.TextChannel,
        canal_logs: discord.TextChannel,
        titulo: str,
        descripcion: str,
        mensaje: str = None,
        imagen_url: str = None,
        rol_dar: discord.Role = None,
        rol_quitar: discord.Role = None,
        texto_boton: str = "Verificar",
        tipo: str = "normal",
        texto_captcha: str = "Verifícate por seguridad del servidor"
    ):

        if tipo not in ["normal", "captcha"]:
            return await interaction.response.send_message("❌ Tipo inválido. Usa: normal o captcha", ephemeral=True)

        guild_id = str(interaction.guild.id)
        data = load_verification()

        if guild_id not in data:
            data[guild_id] = {}

        data[guild_id][panel_id] = {
            "rol_dar": rol_dar.id if rol_dar else None,
            "rol_quitar": rol_quitar.id if rol_quitar else None,
            "titulo": titulo,
            "descripcion": descripcion,
            "mensaje": mensaje,
            "imagen": imagen_url,
            "boton": texto_boton,
            "tipo": tipo,
            "captcha_texto": texto_captcha,
            "canal_logs": canal_logs.id
        }

        save_verification(data)

        embed = discord.Embed(
            title=titulo,
            description=descripcion,
            color=discord.Color.green()
        )

        if mensaje:
            embed.add_field(name="Información", value=mensaje, inline=False)

        if imagen_url:
            embed.set_image(url=imagen_url)

        view = VerifyButton(panel_id, texto_boton)

        await canal.send(embed=embed, view=view)
        await interaction.response.send_message("✅ Panel creado correctamente.", ephemeral=True)

    # ============================
    # ENVIAR PANEL EXISTENTE
    # ============================

    @app_commands.command(
        name="verificacion_enviar",
        description="Enviar un panel de verificación ya creado"
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

        if cfg.get("mensaje"):
            embed.add_field(name="Información", value=cfg["mensaje"], inline=False)

        if cfg.get("imagen"):
            embed.set_image(url=cfg["imagen"])

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
        canal_logs = interaction.guild.get_channel(cfg["canal_logs"])

        # Ya verificado
        if rol_dar and rol_dar in interaction.user.roles:
            return await interaction.response.send_message("✅ Ya estás verificado.", ephemeral=True)

        # ============================
        # VERIFICACIÓN NORMAL
        # ============================

        if tipo == "normal":
            try:
                if rol_quitar:
                    await interaction.user.remove_roles(rol_quitar)
                if rol_dar:
                    await interaction.user.add_roles(rol_dar)

                await interaction.response.send_message("✅ Verificación completada.", ephemeral=True)

                await self.enviar_log_verificacion(
                    interaction.user,
                    interaction.guild,
                    canal_logs,
                    rol_dado=rol_dar,
                    rol_quitado=rol_quitar
                )

            except:
                return await interaction.response.send_message("❌ No pude asignar los roles.", ephemeral=True)

            return

        # ============================
        # VERIFICACIÓN CON CAPTCHA
        # ============================

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

                class CaptchaModal(discord.ui.Modal, title="Verificación con Captcha"):
                    def __init__(self):
                        super().__init__()
                        self.input = discord.ui.TextInput(
                            label="Introduce el código",
                            placeholder="Escribe exactamente lo que ves",
                            required=True
                        )
                        self.add_item(self.input)

                    async def on_submit(self, modal_interaction: discord.Interaction):
                        if self.input.value == codigo:
                            try:
                                if rol_quitar:
                                    await modal_interaction.user.remove_roles(rol_quitar)
                                if rol_dar:
                                    await modal_interaction.user.add_roles(rol_dar)

                                await modal_interaction.response.send_message("✅ Verificación completada.", ephemeral=True)

                                await self_cog.enviar_log_verificacion(
                                    modal_interaction.user,
                                    modal_interaction.guild,
                                    canal_logs,
                                    rol_dado=rol_dar,
                                    rol_quitado=rol_quitar
                                )

                            except:
                                await modal_interaction.response.send_message("❌ No pude asignar los roles.", ephemeral=True)
                        else:
                            await modal_interaction.response.send_message("❌ Código incorrecto.", ephemeral=True)

                self_cog = interaction.client.get_cog("VerificationCog")
                await btn_interaction.response.send_modal(CaptchaModal())

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
    # LOG DE VERIFICACIÓN PRO
    # ============================

    async def enviar_log_verificacion(self, usuario: discord.Member, guild: discord.Guild,
                                      canal_logs: discord.TextChannel,
                                      rol_dado=None, rol_quitado=None):

        if not canal_logs:
            return

        embed = discord.Embed(
            title="✅ Usuario Verificado",
            color=discord.Color.green()
        )

        embed.add_field(name="👤 Usuario", value=f"{usuario.mention}", inline=False)
        embed.add_field(name="🆔 ID", value=str(usuario.id), inline=False)

        if rol_dado:
            embed.add_field(name="🎭 Rol dado", value=rol_dado.mention, inline=False)
        else:
            embed.add_field(name="🎭 Rol dado", value="Ninguno", inline=False)

        if rol_quitado:
            embed.add_field(name="❌ Rol quitado", value=rol_quitado.mention, inline=False)
        else:
            embed.add_field(name="❌ Rol quitado", value="Ninguno", inline=False)

        embed.add_field(name="🏠 Servidor", value=guild.name, inline=False)

        if usuario.avatar:
            embed.set_thumbnail(url=usuario.avatar.url)

        await canal_logs.send(embed=embed)

# ============================
# SETUP
# ============================

async def setup(bot):
    await bot.add_cog(VerificationCog(bot))
