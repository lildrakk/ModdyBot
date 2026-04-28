import discord
from discord.ext import commands
from discord import app_commands

COLOR = discord.Color(0x0A3D62)

# ============================================================
# SELECT MENU
# ============================================================

class HelpSelect(discord.ui.Select):
    def __init__(self):

        options = [
            discord.SelectOption(label="Moderación", emoji=discord.PartialEmoji(name="moderacion", id=1483506627649994812)),
            discord.SelectOption(label="Seguridad", emoji=discord.PartialEmoji(name="candado", id=1491537429889552514)),
            discord.SelectOption(label="Información", emoji=discord.PartialEmoji(name="iinfo", id=1491858536895090708)),
            discord.SelectOption(label="Utilidad", emoji=discord.PartialEmoji(name="anuncio", id=1483506577024614660)),
            discord.SelectOption(label="Verificación", emoji=discord.PartialEmoji(name="ao_Tick", id=1485072554879357089, animated=True)),
            discord.SelectOption(label="Blacklist", emoji=discord.PartialEmoji(name="ban", id=1483506748944810217)),
            discord.SelectOption(label="Giveaways", emoji=discord.PartialEmoji(name="giveaway", id=1494074344341639188)),
            discord.SelectOption(label="Backups", emoji=discord.PartialEmoji(name="estrella", id=1494342514444996638)),
        ]

        super().__init__(
            placeholder="Selecciona una categoría…",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):

        categoria = self.values[0]

        # ============================
        # EMBEDS POR CATEGORÍA
        # ============================

        if categoria == "Moderación":
            embed = discord.Embed(
                title="<:moderacion:1483506627649994812> Moderación",
                description=(
                    "**/ban** — Sistema de expulsión permanente.\n"
                    "**/unban** — Sistema para revertir expulsiones.\n"
                    "**/mute** — Sistema de silencio temporal.\n"
                    "**/unmute** — Sistema para retirar silencios.\n"
                    "**/warn** — Sistema de advertencias.\n"
                    "**/ver_warns** — Consulta de advertencias.\n"
                    "**/eliminar_warn** — Eliminación de advertencias.\n"
                    "**/eliminar_warns** — Limpieza total de advertencias.\n"
                    "**/purge** — Eliminación de mensajes.\n"
                    "**/purgeuser** — Eliminación de mensajes de un usuario.\n"
                    "**/purgebot** — Eliminación de mensajes de bots.\n"
                    "**/nick** — Gestión de nombres de usuario."
                ),
                color=COLOR
            )

        elif categoria == "Seguridad":
            embed = discord.Embed(
                title="<:candado:1491537429889552514> Seguridad",
                description=(
                    "**/antibots** — Sistema de bloqueo de bots no verificados.\n"
                    "**/antibots_config** — Configuración del sistema antibots.\n"
                    "**/antiflood** — Sistema de control de spam masivo.\n"
                    "**/antilinks** — Sistema de bloqueo de enlaces no permitidos.\n"
                    "**/antilinks_whitelist** — Gestión de usuarios y roles sin  restricciones.\n"
                    "**/antiraid** — Sistema de protección contra raids.\n"
                    "**/antiraid_config** — Configuración del sistema antiraid.\n"
                    "**/antialts** — Sistema contra cuentas alternativas.\n"
                    "**/antiping** — Sistema de control de menciones indeseadas.\n"
                    "**/antiping_objetivo** — Configuración del objetivo protegido.\n"
                    "**/antiping_whitelist** — Gestión de usuarios y roles permitidos.\n"
                    "**/securityscan** — Análisis de seguridad del servidor."
                ),
                color=COLOR
            )

        elif categoria == "Información":
            embed = discord.Embed(
                title="<:iinfo:1491858536895090708> Información",
                description=(
                    "**/botinfo** — Información del bot.\n"
                    "**/serverinfo** — Información del servidor.\n"
                    "**/userinfo** — Información de un usuario."
                ),
                color=COLOR
            )

        elif categoria == "Utilidad":
            embed = discord.Embed(
                title="<:anuncio:1483506577024614660> Utilidad",
                description=(
                    "**/say** — Enviar un mensaje mediante el bot.\n"
                    "**/spoiler** — Enviar un spoiler formateado.\n"
                    "**/dmwelcome** — Sistema de bienvenida por mensaje directo."
                ),
                color=COLOR
            )

        elif categoria == "Verificación":
            embed = discord.Embed(
                title="<a:ao_Tick:1485072554879357089> Verificación",
                description=(
                    "**/verificacion** — Sistema de verificación del servidor.\n"
                    "**/verificacion_enviar** — Enviar el panel de verificación."
                ),
                color=COLOR
            )

        elif categoria == "Blacklist":
            embed = discord.Embed(
                title="<:ban:1483506748944810217> Blacklist",
                description=(
                    "**/global_blacklist** — Gestión de la blacklist global.\n"
                    "**/blacklist** — Añadir usuarios a la blacklist.\n"
                    "**/unblacklist** — Eliminar usuarios de la blacklist.\n"
                    "**/blacklistlist** — Lista de usuarios bloqueados."
                ),
                color=COLOR
            )

        elif categoria == "Giveaways":
            embed = discord.Embed(
                title="<:giveaway:1494074344341639188> Giveaways",
                description=(
                    "**/giveaway** — Crear un sorteo.\n"
                    "**/reroll** — Repetir ganador."
                ),
                color=COLOR
            )

        elif categoria == "Backups":
            embed = discord.Embed(
                title="<:estrella:1494342514444996638> Backups",
                description=(
                    "**/backup_crear** — Crear una copia del servidor.\n"
                    "**/backup_restaurar** — Restaurar un backup.\n"
                    "**/backup_borrar** — Eliminar un backup.\n"
                    "**/backup_listar** — Listar backups disponibles.\n"
                    "**/backup_info** — Información detallada de un backup."
                ),
                color=COLOR
            )

        await interaction.response.edit_message(embed=embed)


# ============================================================
# VIEW DEL SELECT
# ============================================================

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(HelpSelect())


# ============================================================
# COG PRINCIPAL
# ============================================================

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Panel de ayuda del bot.")
    async def help(self, interaction: discord.Interaction):

        embed = discord.Embed(
            title="<:reglas:1494341139107418253> Panel de Ayuda — ModdyBot",
            description=(
                "Selecciona una categoría en el menú inferior para ver los comandos disponibles.\n\n"
                "ModdyBot ofrece sistemas avanzados de moderación, seguridad, verificación, backups y más."
            ),
            color=COLOR
        )

        await interaction.response.send_message(embed=embed, view=HelpView(), ephemeral=False)


async def setup(bot):
    await bot.add_cog(Help(bot))
