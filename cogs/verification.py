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

def save_verification(data):
    with open(VERIFICATION_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_verification():
    if not os.path.exists(VERIFICATION_FILE):
        save_verification({})
        return {}

    try:
        with open(VERIFICATION_FILE, "r") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                save_verification({})
                return {}
            return data
    except:
        save_verification({})
        return {}

def sanitize_panel_id(panel_id: str) -> str:
    return panel_id.strip().replace(" ", "_")

# ============================
# CAPTCHA
# ============================

def generar_captcha():
    letras = string.ascii_uppercase + string.digits
    codigo = ''.join(random.choice(letras) for _ in range(6))

    width, height = 500, 200
    img = Image.new("RGB", (width, height), (20, 20, 20))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 120)
    except:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), codigo, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = (width - text_width) // 2
    y = (height - text_height) // 2

    draw.text((x, y), codigo, font=font, fill=(255, 255, 255))

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
            emoji="<:check:1476336175114354891>",
            style=discord.ButtonStyle.success,
            custom_id=f"verify_{panel_id}"
        )
        self.panel_id = panel_id

    async def callback(self, interaction: discord.Interaction):
        return

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
    @app_commands.choices(
        tipo=[
            app_commands.Choice(name="Botón", value="normal"),
            app_commands.Choice(name="Captcha", value="captcha")
        ]
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
        tipo: app_commands.Choice[str] = None,
        texto_captcha: str = "Verifícate por seguridad del servidor"
    ):

        tipo = tipo.value if tipo else "normal"
        guild_id = str(interaction.guild.id)
        data = load_verification()

        if guild_id not in data:
            data[guild_id] = {}

        panel_id = sanitize_panel_id(panel_id)

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
        await interaction.response.send_message("<:check:1476336175114354891> Panel creado correctamente.", ephemeral=True)

    # ============================
    # ENVIAR PANEL EXISTENTE
    # ============================

    @app_commands.command(
        name="verificacion_enviar",
        description="Enviar un panel de verificación ya creado"
    )
    async def verificacion_enviar(self, interaction: discord.Interaction, panel_id: str, canal: discord.TextChannel):

        guild_id = str(interaction.guild.id)
        data = load_verification()
        panel_id = sanitize_panel_id(panel_id)

        if guild_id not in data or panel_id not in data[guild_id]:
            return await interaction.response.send_message("<:X_:1476336151835967640> Ese panel no existe.", ephemeral=True)

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
        await interaction.response.send_message("<:check:1476336175114354891> Panel enviado correctamente.", ephemeral=True)

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

        panel_id = sanitize_panel_id(custom.split("_", 1)[1])
        guild_id = str(interaction.guild.id)
        data = load_verification()

        if guild_id not in data or panel_id not in data[guild_id]:
            return await interaction.response.send_message("<:X_:1476336151835967640> Panel no encontrado.", ephemeral=True)

        cfg = data[guild_id][panel_id]

        rol_dar = interaction.guild.get_role(cfg["rol_dar"]) if cfg.get("rol_dar") else None
        rol_quitar = interaction.guild.get_role(cfg["rol_quitar"]) if cfg.get("rol_quitar") else None
        tipo = cfg.get("tipo", "normal")
        canal_logs = interaction.guild.get_channel(cfg.get("canal_logs"))

        if rol_dar and rol_dar in interaction.user.roles:
            return await interaction.response.send_message("<:check:1476336175114354891> Ya estás verificado.", ephemeral=True)

        # ============================
        # VERIFICACIÓN NORMAL
        # ============================

        if tipo == "normal":
            try:
                if rol_quitar:
                    await interaction.user.remove_roles(rol_quitar)
                if rol_dar:
                    await interaction.user.add_roles(rol_dar)

                await interaction.response.send_message("<:check:1476336175114354891> Verificación completada.", ephemeral=True)

                await self.enviar_log_verificacion(
                    interaction.user,
                    interaction.guild,
                    canal_logs,
                    rol_dado=rol_dar,
                    rol_quitado=rol_quitar
                )

            except:
                return await interaction.response.send_message("<:X_:1476336151835967640> No pude asignar los roles.", ephemeral=True)

            return

        # ============================
        # VERIFICACIÓN CON CAPTCHA
        # ============================

        codigo, imagen = generar_captcha()

        embed = discord.Embed(
            title="<:escudo:1483506514399334441> Verificación con Captcha",
            description=cfg.get("captcha_texto", "Verifícate por seguridad del servidor"),
            color=discord.Color.blue()
        )

        file = discord.File(imagen, filename="captcha.png")
        embed.set_image(url="attachment://captcha.png")

        self_cog = self

        class CaptchaResponder(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=120)
                self.add_item(ResponderButton())

        class ResponderButton(discord.ui.Button):
            def __init__(self):
                super().__init__(
                    label="Responder",
                    style=discord.ButtonStyle.primary,
                    custom_id=f"captcha_reply_{panel_id}"
                )

            async def callback(self, i: discord.Interaction):

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

                                await modal_interaction.response.send_message(
                                    "<:check:1476336175114354891> Verificación completada.",
                                    ephemeral=True
                                )

                                await self_cog.enviar_log_verificacion(
                                    modal_interaction.user,
                                    modal_interaction.guild,
                                    canal_logs,
                                    rol_dado=rol_dar,
                                    rol_quitado=rol_quitar
                                )

                            except:
                                await modal_interaction.response.send_message(
                                    "<:X_:1476336151835967640> No pude asignar los roles.",
                                    ephemeral=True
                                )
                        else:
                            await modal_interaction.response.send_message(
                                "<:X_:1476336151835967640> Código incorrecto.",
                                ephemeral=True
                            )

                await i.response.send_modal(CaptchaModal())

        await interaction.response.send_message(
            embed=embed,
            file=file,
            view=CaptchaResponder(),
            ephemeral=True
        )

# ============================
# LOG DE VERIFICACIÓN
# ============================

async def enviar_log_verificacion(
    self,
    usuario: discord.Member,
    guild: discord.Guild,
    canal_logs: discord.TextChannel,
    rol_dado=None,
    rol_quitado=None
):

    if not canal_logs:
        return

    embed = discord.Embed(
        title="<:check:1476336175114354891> Usuario Verificado",
        color=discord.Color.green()
    )

    embed.add_field(
        name="<:anuncio:1483506577024614660> Usuario",
        value=f"{usuario.mention}",
        inline=False
    )

    embed.add_field(
        name="<:link:1483506560935268452> ID del usuario",
        value=str(usuario.id),
        inline=False
    )

    embed.add_field(
        name="<:escudo:1483506514399334441> Bot",
        value=self.bot.user.mention,
        inline=False
    )

    if rol_dado:
        embed.add_field(
            name="<:regalo:1483506548495093957> Rol asignado",
            value=rol_dado.mention,
            inline=False
        )
    else:
        embed.add_field(
            name="<:regalo:1483506548495093957> Rol asignado",
            value="Ninguno",
            inline=False
        )

    if rol_quitado:
        embed.add_field(
            name="<:basura:1483506530715439104> Rol retirado",
            value=rol_quitado.mention,
            inline=False
        )
    else:
        embed.add_field(
            name="<:basura:1483506530715439104> Rol retirado",
            value="Ninguno",
            inline=False
        )

    embed.add_field(
        name="<:discord:1483506738954244258> Servidor",
        value=guild.name,
        inline=False
    )

    if usuario.avatar:
        embed.set_thumbnail(url=usuario.avatar.url)

    await canal_logs.send(embed=embed)

async def setup(bot):
    await bot.add_cog(VerificationCog(bot))
