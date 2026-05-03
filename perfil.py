import discord
from discord.ext import commands
from discord import app_commands
import json
import os

# ============================
# CONFIGURACIÓN
# ============================

OWNER_ID = 1394342273919225959
SERVER_ID = 1464575509785612380

ROL_FUNDADOR = 1466470725287284817
ROL_COFUNDADOR = 1498781522667376794
ROL_STAFF = 1466470478720925716
ROL_MOD = 1466470674477355081

# Emojis oficiales
EMOJI_USUARIO = "<:user:1488971290302877967>"
EMOJI_MOD = "<:moderador:1500474305837011095>"
EMOJI_STAFF = "<:moderacion:1483506627649994812>"
EMOJI_FUNDADOR = "<:corona:1494336904769044620>"
EMOJI_COFUNDADOR = "<:corona:1494336904769044620>"

# Emojis de blacklist
EMOJI_OK = "<a:ao_Tick:1485072554879357089>"
EMOJI_ALERTA = "<:no:1476336151835967640>"
EMOJI_BLACKLIST_BADGE = "<:blacklist:1500486222898790410>"

# Banner oficial
BANNER_URL = "https://raw.githubusercontent.com/lildrakk/ModdyBot-web/eb6b1cb04336b0929a83cacad3b6834d11cedf8c/standard-3.gif"

BLACKLIST_FILE = "blacklist_global.json"
INSIGNIAS_FILE = "insignias.json"

COLOR_OFICIAL = discord.Color(0x0A3D62)

# ============================
# ARCHIVOS
# ============================

def cargar_blacklist():
    try:
        with open(BLACKLIST_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def cargar_insignias():
    if not os.path.exists(INSIGNIAS_FILE):
        with open(INSIGNIAS_FILE, "w") as f:
            f.write("{}")
    with open(INSIGNIAS_FILE, "r") as f:
        return json.load(f)

def guardar_insignias(data):
    with open(INSIGNIAS_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ============================
# COG PRINCIPAL
# ============================

class Perfil(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ============================
    # PERFIL (SLASH)
    # ============================

    @app_commands.command(name="perfil", description="Muestra el perfil detallado de un usuario.")
    @app_commands.describe(usuario="Usuario del servidor", id="ID de un usuario fuera del servidor")
    async def perfil(self, interaction: discord.Interaction, usuario: discord.Member = None, id: str = None):

        await interaction.response.defer(ephemeral=False)

        # Obtener usuario
        if id:
            try:
                usuario = await self.bot.fetch_user(int(id))
                miembro = None
            except:
                return await interaction.followup.send("❌ No se encontró un usuario con ese ID.")
        else:
            if usuario is None:
                usuario = interaction.user
            guild = self.bot.get_guild(SERVER_ID)
            miembro = guild.get_member(usuario.id)

        # ============================
        # RANGO + INSIGNIAS AUTOMÁTICAS (PRIORIDAD)
        # ============================

        insignias_auto = []
        rango = "Usuario normal"
        rango_prioridad = 0  # 0 = usuario, 1 = staff, 2 = mod, 3 = cofundador, 4 = fundador

        if miembro:
            roles = [r.id for r in miembro.roles]

            # Orden de prioridad: Fundador > Cofundador > Moderador > Staff > Usuario
            # 1) Fundador
            if ROL_FUNDADOR in roles:
                insignias_auto.append(EMOJI_FUNDADOR)
                if rango_prioridad < 4:
                    rango_prioridad = 4
                    rango = "<:corona:1494336904769044620> Fundador oficial de ModdyBot"

            # 2) Cofundador
            if ROL_COFUNDADOR in roles:
                insignias_auto.append(EMOJI_COFUNDADOR)
                if rango_prioridad < 3:
                    rango_prioridad = 3
                    rango = "<:corona:1494336904769044620> Co fundador oficial de ModdyBot"

            # 3) Moderador
            if ROL_MOD in roles:
                insignias_auto.append(EMOJI_MOD)
                if rango_prioridad < 2:
                    rango_prioridad = 2
                    rango = "<:moderador:1500474305837011095> Moderador oficial de ModdyBot"

            # 4) Staff
            if ROL_STAFF in roles:
                insignias_auto.append(EMOJI_STAFF)
                if rango_prioridad < 1:
                    rango_prioridad = 1
                    rango = "<:moderacion:1483506627649994812> Staff oficial de ModdyBot"

            # Si no tiene ninguno de los rangos anteriores
            if not insignias_auto:
                insignias_auto.append(EMOJI_USUARIO)
                rango = "Usuario normal"
        else:
            insignias_auto.append(EMOJI_USUARIO)
            rango = "Usuario normal"

        # ============================
        # INSIGNIAS MANUALES
        # ============================

        insignias_data = cargar_insignias()
        insignias_manual = insignias_data.get(str(usuario.id), [])

        # ============================
        # BLACKLIST
        # ============================

        blacklist = cargar_blacklist()
        uid = str(usuario.id)

        esta_en_blacklist = uid in blacklist

        if esta_en_blacklist:
            datos = blacklist[uid]
            estado_blacklist = (
                f"{EMOJI_ALERTA} **Este usuario presenta una sanción en la blacklist global.**\n"
                f"**Motivo:** {datos['razon']}\n"
                f"**Duración:** {datos['duracion']}\n"
                f"**Fecha:** {datos['fecha_ban']}"
            )
        else:
            estado_blacklist = f"{EMOJI_OK} **Este usuario no presenta ninguna sanción, o cargos en la blacklist.**"

        # ============================
        # FECHAS
        # ============================

        fecha_creacion = usuario.created_at.strftime("%d/%m/%Y %H:%M")
        fecha_union = miembro.joined_at.strftime("%d/%m/%Y %H:%M") if miembro else "No disponible"
        servidores_comunes = len(usuario.mutual_guilds)

        # ============================
        # EMBED FINAL
        # ============================

        embed = discord.Embed(
            title=rango,
            description=f"Bienvenido al perfil de **{usuario.name}**.",
            color=COLOR_OFICIAL
        )

        embed.add_field(name="<:link:1483506560935268452> ID", value=str(usuario.id), inline=False)
        embed.add_field(name="<:calendario:1494340255996969091> Cuenta creada el", value=fecha_creacion, inline=True)
        embed.add_field(name="<a:flechazul:1492182951532826684> Miembro desde", value=fecha_union, inline=True)

        embed.add_field(name="<:candado:1491537429889552514> Estado de blacklist global", value=estado_blacklist, inline=False)

        embed.add_field(name="<:nose:1491491155198607440> Servidores en común", value=str(servidores_comunes), inline=False)

        # Insignias finales: automáticas (ya en orden) + manuales
        insignias_finales = insignias_auto + insignias_manual

        # Blacklist badge al final si está en blacklist
        if esta_en_blacklist:
            insignias_finales.append(EMOJI_BLACKLIST_BADGE)

        embed.add_field(name="<:estrella:1494342514444996638> Insignias", value=" ".join(insignias_finales), inline=False)

        embed.set_thumbnail(url=usuario.display_avatar.url)
        embed.set_image(url=BANNER_URL)

        await interaction.followup.send(embed=embed)

    # ============================
    # AÑADIR INSIGNIA (PREFIJO POR ID)
    # ============================

    @commands.command(name="ainsignia")
    async def ainsignia(self, ctx, user_id: int, insignia: str):

        if ctx.author.id != OWNER_ID:
            return await ctx.reply("❌ No tienes permiso para usar este comando.")

        try:
            usuario = await self.bot.fetch_user(user_id)
        except:
            return await ctx.reply("❌ No se encontró un usuario con ese ID.")

        data = cargar_insignias()
        uid = str(user_id)

        if uid not in data:
            data[uid] = []

        data[uid].append(insignia)
        guardar_insignias(data)

        await ctx.reply(f"✅ Insignia añadida a **{usuario.name}**.")

    # ============================
    # ELIMINAR INSIGNIA (PREFIJO POR ID)
    # ============================

    @commands.command(name="einsignia")
    async def einsignia(self, ctx, user_id: int, insignia: str):

        if ctx.author.id != OWNER_ID:
            return await ctx.reply("❌ No tienes permiso para usar este comando.")

        data = cargar_insignias()
        uid = str(user_id)

        if uid not in data or insignia not in data[uid]:
            return await ctx.reply("❌ Ese usuario no tiene esa insignia.")

        data[uid].remove(insignia)
        guardar_insignias(data)

        usuario = await self.bot.fetch_user(user_id)
        await ctx.reply(f"🗑️ Insignia eliminada de **{usuario.name}**.")

# ============================
# SETUP
# ============================

async def setup(bot):
    await bot.add_cog(Perfil(bot))
