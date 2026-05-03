import discord
from discord.ext import commands
from discord import app_commands
import json

# ============================
# CONFIGURACIÓN
# ============================

SERVER_ID = 1464575509785612380

ROL_FUNDADOR = 1466470725287284817
ROL_COFUNDADOR = 1498781522667376794
ROL_STAFF = 1466470478720925716
ROL_MOD = 1466470674477355081

EMOJI_USUARIO = "<:user:1488971290302877967>"
EMOJI_MOD = "<:moderador:1500474305837011095>"
EMOJI_STAFF = "<:moderacion:1483506627649994812>"
EMOJI_FUNDADOR = "<:corona:1494336904769044620>"
EMOJI_COFUNDADOR = "<:corona:1494336904769044620>"
EMOJI_OK = "<a:ao_Tick:1485072554879357089>"
EMOJI_ALERTA = "<a:alarmazul:1491858094043693177>"

BANNER_URL = "https://raw.githubusercontent.com/lildrakk/ModdyBot-web/eb6b1cb04336b0929a83cacad3b6834d11cedf8c/standard-3.gif"
BLACKLIST_FILE = "blacklist_global.json"

COLOR_OFICIAL = discord.Color(0x0A3D62)

# ============================
# LEER BLACKLIST
# ============================

def cargar_blacklist():
    try:
        with open(BLACKLIST_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

# ============================
# COG PRINCIPAL
# ============================

class Perfil(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="perfil",
        description="Muestra el perfil detallado de un usuario."
    )
    @app_commands.describe(
        usuario="Usuario del servidor",
        id="ID de un usuario que no esté en el servidor"
    )
    async def perfil(self, interaction: discord.Interaction, usuario: discord.Member = None, id: str = None):

        await interaction.response.defer(ephemeral=False)

        # ============================
        # OBTENER USUARIO
        # ============================

        if id is not None:
            try:
                usuario = await self.bot.fetch_user(int(id))
                miembro = None
            except:
                return await interaction.followup.send("❌ No se pudo encontrar un usuario con ese ID.")
        else:
            if usuario is None:
                usuario = interaction.user

            guild = self.bot.get_guild(SERVER_ID)
            miembro = guild.get_member(usuario.id)

        # ============================
        # RANGO E INSIGNIAS
        # ============================

        insignias = []
        rango = "Usuario normal"

        if miembro:
            roles = [r.id for r in miembro.roles]

            if ROL_FUNDADOR in roles:
                rango = "Fundador oficial de ModdyBot"
                insignias.append(EMOJI_FUNDADOR)

            elif ROL_COFUNDADOR in roles:
                rango = "Co fundador oficial de ModdyBot"
                insignias.append(EMOJI_COFUNDADOR)

            elif ROL_STAFF in roles:
                rango = "Staff oficial de ModdyBot"
                insignias.append(EMOJI_STAFF)

            elif ROL_MOD in roles:
                rango = "Moderador oficial de ModdyBot"
                insignias.append(EMOJI_MOD)

            else:
                insignias.append(EMOJI_USUARIO)
        else:
            insignias.append(EMOJI_USUARIO)

        # ============================
        # BLACKLIST GLOBAL
        # ============================

        blacklist = cargar_blacklist()
        user_id_str = str(usuario.id)

        if user_id_str in blacklist:
            datos = blacklist[user_id_str]
            estado_blacklist = (
                f"{EMOJI_ALERTA} **Este usuario presenta una sanción en la blacklist global.**\n"
                f"**Motivo:** {datos['razon']}\n"
                f"**Duración:** {datos['duracion']}\n"
                f"**Fecha:** {datos['fecha_ban']}"
            )
        else:
            estado_blacklist = (
                f"{EMOJI_OK} **Este usuario no presenta ninguna sanción, o cargos en la blacklist.**"
            )

        # ============================
        # FECHAS
        # ============================

        fecha_creacion = usuario.created_at.strftime("%d/%m/%Y %H:%M")

        if miembro and miembro.joined_at:
            fecha_union = miembro.joined_at.strftime("%d/%m/%Y %H:%M")
        else:
            fecha_union = "No disponible"

        try:
            servidores_comunes = len(usuario.mutual_guilds)
        except:
            servidores_comunes = 0

        # ============================
        # EMBED FINAL (FORMATO EXACTO)
        # ============================

        embed = discord.Embed(
            title=f"{rango}",
            description=f"Bienvenido al perfil de **{usuario.name}**.",
            color=COLOR_OFICIAL
        )

        embed.add_field(name="<:link:1483506560935268452> ID", value=str(usuario.id), inline=False)
        embed.add_field(name="<:calendario:1494340255996969091> Cuenta creada el", value=fecha_creacion, inline=True)
        embed.add_field(name="<a:flechazul:1492182951532826684> Miembro desde", value=fecha_union, inline=True)

        embed.add_field(name="<:candado:1491537429889552514> Estado de blacklist global", value=estado_blacklist, inline=False)

        embed.add_field(name="<:nose:1491491155198607440> Servidores en común", value=str(servidores_comunes), inline=False)
        embed.add_field(name="<:estrella:1494342514444996638> Insignias", value=" ".join(insignias), inline=False)

        embed.set_thumbnail(url=usuario.display_avatar.url)
        embed.set_image(url=BANNER_URL)

        await interaction.followup.send(embed=embed)

# ============================
# SETUP
# ============================

async def setup(bot):
    await bot.add_cog(Perfil(bot))
